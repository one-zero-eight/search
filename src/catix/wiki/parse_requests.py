"""Requests to update a source of the wiki (POST /{section}/parse): the API queues them in Redis, the wiki's own run takes
them and asks the named sources with its checks and its commit (autopilot.py). The API never writes the wiki: its checkout is
read-only there (docker-compose.prod.yml), and only what passed the checks reaches the `wiki` branch.

    ctx:wiki:parse:<id>               a request (hash): its source, sites, status, and what the run that served it did
    ctx:wiki:parse:queued             the ids waiting for a run (list, oldest first)
    ctx:wiki:parse:running            the ids the current run took; a run that died leaves them here, the next one takes them again
    ctx:wiki:parse:waiting:<request>  the id of the same request still waiting: asking twice queues it once

A request is `queued`, `running` while a run serves it, then `done` (`outcome`: committed, review or unchanged, and the run's
line in `result`) or `failed` (the run raised; `result` says what). Requests that wait together are served by one run.
"""

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

import redis

from catix.settings import settings

PREFIX = "ctx:wiki:parse"
QUEUED = f"{PREFIX}:queued"
RUNNING = f"{PREFIX}:running"
NEXT = f"{PREFIX}:next"
KEEP = 30 * 24 * 3600  # seconds a finished request keeps its status
ATTEMPTS = 3  # runs that may die while serving a request before it fails (a request that brings the run down is not taken for ever)
SOURCES = ("eduwiki", "sites")  # the sources a request may name (sources/__init__.py)


class Unavailable(RuntimeError):
    """No queue: REDIS_URL is not set, or Redis does not answer."""


@dataclass
class Request:
    id: str
    section: str  # the path it was asked by: 'sites', 'resources', 'hotel', 'eduwiki', ...
    source: str  # 'eduwiki' or 'sites'
    sites: list[str] = field(default_factory=list)  # the sites `sites` reads (names of the catalog)
    parsing: bool = True  # False: no source is asked, the run builds and checks what the data already holds
    status: str = "queued"  # queued | running | done | failed
    outcome: str = ""  # committed | review | unchanged (done), error (failed)
    result: str = ""  # the run's line: 'committed 1a2b3c: 12 files and pushed', 'checks failed, changes sent to wiki-review/...'
    created_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    attempts: int = 0

    def key(self) -> str:
        return f"{PREFIX}:{self.id}"

    def waiting_key(self) -> str:
        what = json.dumps([self.source, sorted(self.sites), self.parsing])
        return f"{PREFIX}:waiting:{hashlib.sha1(what.encode()).hexdigest()[:16]}"

    def fields(self) -> dict[str, str]:
        out = {k: str(v) for k, v in asdict(self).items()}
        out.update(sites=json.dumps(self.sites, ensure_ascii=False), parsing="1" if self.parsing else "0")
        return out

    @classmethod
    def of(cls, fields: dict[str, str]) -> "Request":
        return cls(**{**fields, "sites": json.loads(fields.get("sites") or "[]"), "parsing": fields.get("parsing") == "1",
                      "attempts": int(fields.get("attempts") or 0)})

    def describe(self) -> str:
        what = "build only" if not self.parsing else self.source + (f" ({', '.join(self.sites)})" if self.sites else "")
        return f"#{self.id} {what}"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


_client: redis.Redis | None = None


def connect() -> redis.Redis:
    """The queue's Redis (REDIS_URL): the API's and the wiki's run must name the same one."""
    global _client
    if not settings.redis_url:
        raise Unavailable("REDIS_URL is not set: there is no queue for the wiki's run")
    if _client is None:
        _client = redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=10, socket_connect_timeout=5)
    return _client


def submit(section: str, source: str, sites: list[str], parsing: bool = True) -> Request:
    """Queue a request, or the same one if it still waits. Raises Unavailable without Redis."""
    if source not in SOURCES:
        raise ValueError(f"no source {source!r} for a request: {', '.join(SOURCES)}")
    request = Request(id="", section=section, source=source, sites=list(dict.fromkeys(sites)) if source == "sites" else [],
                      parsing=parsing, created_at=now())
    try:
        r = connect()
        if (same := r.get(request.waiting_key())) and (old := _get(r, same)) and old.status == "queued":
            return old
        request.id = str(r.incr(NEXT))
        with r.pipeline() as pipe:
            pipe.hset(request.key(), mapping=request.fields())
            pipe.set(request.waiting_key(), request.id, ex=KEEP)
            pipe.rpush(QUEUED, request.id)
            pipe.execute()
    except redis.RedisError as e:
        raise Unavailable(f"the queue (Redis) does not answer: {e}") from e
    return request


def get(request_id: str) -> Request | None:
    """The request, or None when there is none (or it finished more than KEEP ago). Raises Unavailable without Redis."""
    try:
        return _get(connect(), request_id)
    except redis.RedisError as e:
        raise Unavailable(f"the queue (Redis) does not answer: {e}") from e


def _get(r: redis.Redis, request_id: str) -> Request | None:
    fields = r.hgetall(f"{PREFIX}:{request_id}")
    return Request.of(fields) if fields else None


def take() -> list[Request]:
    """The wiki's run (under its lock) takes every waiting request, and those a run that died left. Without a queue: none."""
    try:
        r = connect()
    except Unavailable:
        return []  # (no REDIS_URL: the run serves no requests)
    try:
        while r.lmove(QUEUED, RUNNING, "LEFT", "RIGHT") is not None:
            pass
        taken, broken = [], []
        for request_id in r.lrange(RUNNING, 0, -1):
            if (request := _get(r, request_id)) is None:  # (expired while it waited: nothing to tell anyone)
                r.lrem(RUNNING, 0, request_id)
                continue
            if r.get(request.waiting_key()) == request.id:
                r.delete(request.waiting_key())  # (the same request asked from now on is a new one: this run may have read the source already)
            request.status, request.started_at, request.attempts = "running", now(), request.attempts + 1
            r.hset(request.key(), mapping={"status": request.status, "started_at": request.started_at, "attempts": str(request.attempts)})
            (broken if request.attempts > ATTEMPTS else taken).append(request)
        if broken:
            finish(broken, "error", f"the wiki's run stopped {ATTEMPTS} times while serving it", failed=True)
        return taken
    except redis.RedisError as e:
        print(f"(the queue of requests does not answer: {e})", flush=True)
        return []


def finish(requests: list[Request], outcome: str, result: str, failed: bool = False) -> None:
    """What the run that served the requests did. A queue that does not answer leaves them to the next run."""
    if not requests:
        return
    try:
        with connect().pipeline() as pipe:
            for request in requests:
                pipe.hset(request.key(), mapping={"status": "failed" if failed else "done", "outcome": outcome, "result": result,
                                                  "finished_at": now()})
                pipe.expire(request.key(), KEEP)
                pipe.lrem(RUNNING, 0, request.id)
            pipe.execute()
    except (Unavailable, redis.RedisError) as e:
        print(f"(requests {', '.join(r.id for r in requests)} not marked {outcome}: {e})", flush=True)


def waiting() -> bool:
    """Whether a request waits (the loop of the wiki's run wakes up for it)."""
    try:
        return bool(connect().llen(QUEUED))
    except (Unavailable, redis.RedisError):
        return False
