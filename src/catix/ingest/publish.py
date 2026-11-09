"""Hands newly stored messages to the schedule-changes worker through a Redis stream.

The bots publish only the ids (chat_id, msg_id) after the batch is in Postgres; the worker reads the text from
there. Default publishing is best effort. Durable outbox callers use strict=True and acknowledge only success.
"""

import logging

import redis.asyncio as redis

from catix.settings import settings

log = logging.getLogger("catix.stream_out")

STREAM = "ctx:messages"
MAX_LEN = 100_000  # Approximate cap: a worker that is down for long loses the oldest instead of filling memory.

_client: redis.Redis | None = None


async def publish(ids: list[tuple[int, int]], *, strict: bool = False) -> None:
    global _client
    if not ids:
        return
    if not settings.redis_url:
        if strict:
            raise RuntimeError("publication_error: REDIS_URL is not configured")
        return
    try:
        _client = _client or redis.from_url(settings.redis_url)
        async with _client.pipeline(transaction=False) as pipe:
            for chat_id, msg_id in ids:
                pipe.xadd(STREAM, {"chat_id": chat_id, "msg_id": msg_id}, maxlen=MAX_LEN, approximate=True)
            await pipe.execute()
    except Exception:  # noqa: BLE001 - default callers must not block ingestion
        if strict:
            raise
        log.warning("publication_error: could not publish %d messages to redis", len(ids))
