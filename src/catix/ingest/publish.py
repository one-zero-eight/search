"""Hands newly stored messages to the schedule-changes worker through a Redis stream.

The bots publish only the ids (chat_id, msg_id) after the batch is in Postgres; the worker reads the text from
there. Publishing is best effort: if Redis is down the bots keep storing messages and the worker simply misses those.
"""

import logging

import redis.asyncio as redis

from catix.settings import settings

log = logging.getLogger("catix.stream_out")

STREAM = "ctx:messages"
MAX_LEN = 100_000  # Approximate cap: a worker that is down for long loses the oldest instead of filling memory.

_client: redis.Redis | None = None


async def publish(ids: list[tuple[int, int]]) -> None:
    global _client
    if not settings.redis_url or not ids:
        return
    try:
        _client = _client or redis.from_url(settings.redis_url)
        async with _client.pipeline(transaction=False) as pipe:
            for chat_id, msg_id in ids:
                pipe.xadd(STREAM, {"chat_id": chat_id, "msg_id": msg_id}, maxlen=MAX_LEN, approximate=True)
            await pipe.execute()
    except Exception as e:  # noqa: BLE001 - never block storing messages because of the queue
        log.warning("could not publish %d messages to redis: %s", len(ids), e)
