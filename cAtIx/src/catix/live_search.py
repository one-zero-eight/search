"""Live search in Telegram for chats that are not stored (reader `search` in /listen).

The userbot's account is the only thing that can use Telegram's own search, and its session cannot be opened by two
processes, so the bot asks the userbot through Redis: it pushes a request to a list and waits for the answer on a list of
its own (`request`); the userbot serves the requests next to listening (`tguserbot/userbot.py`, `_serve_search`).
Telegram's search matches words (with their forms) in one chat at a time and returns the newest first, so the model's
queries are turned into a few keywords, every keyword is searched in every live chat, and the hits are ordered by the
reranker (newest first without it) before the best go to the model.
"""

import json
import logging
import re
import secrets
import time
from dataclasses import dataclass
from datetime import datetime

import redis

from catix.agent import tracing
from catix.db import pg
from catix.settings import settings

log = logging.getLogger("catix.live_search")

REQUESTS = "catix:search:requests"
REQUEST_TTL = 30  # Seconds: a request older than this is not worth answering (nobody waits any more).
MAX_KEYWORDS = 5
STOPWORDS = {
    "когда", "где", "как", "что", "это", "для", "или", "при", "про", "кто", "какой", "какая", "какие", "будет", "есть",
    "the", "and", "for", "with", "when", "where", "what", "how", "this", "that", "are", "was",
}


def reply_key(request_id: str) -> str:
    return f"catix:search:reply:{request_id}"


@dataclass(frozen=True, slots=True)
class Hit:
    chat_id: int
    msg_id: int
    chat_title: str
    date: datetime
    author: str | None
    sender_link: str | None
    link: str | None
    text: str


def keywords(queries: list[str]) -> list[str]:
    """The words worth searching in Telegram: those of the queries, the ones several queries share first."""
    counts: dict[str, int] = {}
    for query in queries:
        for word in dict.fromkeys(re.findall(r"[\w-]+", query.casefold())):
            if len(word) >= 3 and word not in STOPWORDS and not word.isdigit():
                counts[word] = counts.get(word, 0) + 1
    return sorted(counts, key=lambda word: -counts[word])[:MAX_KEYWORDS]


def request(chat_ids: list[int], words: list[str], date_from: str | None = None, date_to: str | None = None) -> tuple[list[Hit], str | None]:
    """Ask the userbot; (hits, problem). A problem (it is down, Telegram asked to wait) is a sentence for the model."""
    if not settings.redis_url:
        return [], "live search needs Redis"
    timeout = settings.live_search_timeout
    client = redis.from_url(settings.redis_url, socket_timeout=timeout + 5)
    request_id = secrets.token_hex(8)
    payload = {
        "id": request_id, "chat_ids": chat_ids, "keywords": words, "per_chat": settings.live_search_per_chat,
        "date_from": date_from, "date_to": date_to, "sent": time.time(),
    }
    try:
        client.rpush(REQUESTS, json.dumps(payload))
        answer = client.blpop([reply_key(request_id)], timeout=max(1, int(timeout)))
    except redis.RedisError as e:
        return [], f"Redis is not available: {e}"
    if answer is None:
        return [], "the userbot did not answer in time (it may be down)"
    data = json.loads(answer[1])
    hits = [Hit(**{**h, "date": datetime.fromisoformat(h["date"])}) for h in data.get("hits", [])]
    return hits, data.get("error")


MAX_CANDIDATES = 40  # The reranker server works through documents one request at a time: ~1.6 s per 100.


def rank(queries: list[str], hits: list[Hit], limit: int) -> list[Hit]:
    """The best `limit` hits: by the reranker against the keywords taken together, else the newest."""
    if len(hits) <= 1:
        return hits[:limit]
    candidates = sorted(hits, key=lambda h: h.date, reverse=True)[:MAX_CANDIDATES]
    if not settings.reranker_route:
        return candidates[:limit]
    try:
        scores = pg.rerank(" ".join(queries)[:200], [h.text[:600] for h in candidates])
    except Exception:  # noqa: BLE001 - live search must work without the reranker
        log.warning("reranker unavailable, live hits ordered by date", exc_info=True)
        return candidates[:limit]
    keep = sorted(range(len(candidates)), key=lambda i: scores[i], reverse=True)[:limit]
    if settings.rerank_min_score is not None:
        keep = [i for i in keep if scores[i] >= settings.rerank_min_score]
    return [candidates[i] for i in keep]


def search(queries: list[str], chat_ids: list[int], date_from: str | None = None, date_to: str | None = None) -> tuple[list[Hit], str | None]:
    """Live search for a question: keywords of the queries in every live chat, the best hits."""
    words = keywords(queries)
    if not words or not chat_ids:
        return [], None
    with tracing.span("userbot search", "RETRIEVER", input=words, chats=len(chat_ids)) as done:
        hits, problem = request(chat_ids, words, date_from, date_to)
        done(problem or len(hits))
    unique = list({(h.chat_id, h.msg_id): h for h in hits}.values())
    return rank(queries, unique, settings.live_search_results), problem
