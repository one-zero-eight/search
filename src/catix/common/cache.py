"""The cache every process shares, in Redis (REDIS_URL): what the API, the bots, the worker and the userbot read from other
services (InNoHassle, Sport, DeepSeek) or from the database (what /listen chose), each kept for a time of its own under
`catix:cache:<key>`.

One cache for all the processes: a process that starts finds it warm, a service is asked once for all of them, and a
change made in one (`drop`) is seen by the others at once. Redis expires the keys, so it holds only what is still fresh.

Values are JSON, and what comes back is what json.loads gives (a tuple is a list, the keys of a dict are strings), on a
miss too: the caller sees the same either way, and what it changes in a value is its own copy. Without Redis (REDIS_URL
is not set, or it does not answer) nothing is kept and every call reads again; nothing fails. After an error Redis is
not asked for DOWN_SECONDS, so that a call does not wait for it each time.
"""

import json
import logging
import threading
import time
from collections.abc import Callable
from typing import Any

import redis

from catix.settings import settings

log = logging.getLogger("catix.cache")

PREFIX = "catix:cache:"
DOWN_SECONDS = 30.0

_client: redis.Redis | None = None
_lock = threading.Lock()
_down_until = 0.0


def _redis() -> redis.Redis | None:
    global _client
    if not settings.redis_url or time.monotonic() < _down_until:
        return None
    with _lock:
        if _client is None:
            _client = redis.from_url(settings.redis_url, socket_timeout=2, socket_connect_timeout=1)
    return _client


def _failed(e: redis.RedisError) -> None:
    global _down_until
    log.warning("the cache (Redis) does not answer, nothing is cached for %.0f s: %s", DOWN_SECONDS, e)
    _down_until = time.monotonic() + DOWN_SECONDS


def get(key: str) -> tuple[bool, Any]:
    """(found, value): found is False when the key is not kept (never was, expired, or there is no Redis)."""
    if (r := _redis()) is None:
        return False, None
    try:
        raw = r.get(PREFIX + key)
    except redis.RedisError as e:
        _failed(e)
        return False, None
    return (False, None) if raw is None else (True, json.loads(raw))


def put(key: str, value: Any, ttl: float) -> Any:
    """Keep a value for `ttl` seconds (not at all when ttl is not positive); returns it as a get of it gives it."""
    raw = json.dumps(value, ensure_ascii=False)
    if ttl > 0 and (r := _redis()) is not None:
        try:
            r.set(PREFIX + key, raw, ex=max(1, round(ttl)))
        except redis.RedisError as e:
            _failed(e)
    return json.loads(raw)


def cached(key: str, ttl: float, load: Callable[[], Any]) -> Any:
    """The kept value of the key, or what `load` gives (kept for `ttl` seconds). An exception of load is not kept."""
    found, value = get(key)
    return value if found else put(key, load(), ttl)


def drop(*keys: str) -> None:
    """Forget the keys, in every process."""
    if not keys or (r := _redis()) is None:
        return
    try:
        r.delete(*(PREFIX + key for key in keys))
    except redis.RedisError as e:
        _failed(e)
