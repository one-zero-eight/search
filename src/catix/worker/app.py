"""Background worker: embeddings, moodle files and health alerts, a separate app that the Telegram and Max bots feed.

    bots --(ids of stored messages)--> Redis stream --> wakes the embedders of this worker

Embedding threads (embedder.py) turn every stored message into a vector; they read their queue from Postgres and
are woken by the stream. The bots only store messages, they compute nothing. A moodle-files thread (moodle_reader.py) reads the text of the
course files users uploaded (moodle_blobs) as they arrive. Run: `catix-worker`.
"""

import asyncio
import logging
import threading

import redis.asyncio as redis

from catix.worker import embedder
from catix.worker import health
from catix.worker import moodle_reader
from catix.common import logs
from catix.db import pg
from catix.agent import tracing
from catix.settings import settings
from catix.ingest.publish import STREAM

log = logging.getLogger("catix.worker")

BLOCK_MS = 5000
RETRY_SECONDS = 10


async def wake_on_new(client: redis.Redis, wake: threading.Event) -> None:
    """Wake the embedding threads when a bot publishes a message, so a new message gets its vector without waiting
    for the next poll. (Without Redis they simply poll the queue in the database once a second.)"""
    last = "$"  # Only entries that arrive from now on.
    while True:
        try:
            reply: list[tuple[bytes, list[tuple[bytes, dict[bytes, bytes]]]]] | None = await client.xread(
                {STREAM: last}, count=100, block=BLOCK_MS
            )  # type: ignore[assignment] - redis-py types every reply as a union
            if reply:
                last = reply[0][1][-1][0]
                wake.set()
        except (redis.ConnectionError, redis.TimeoutError):
            await asyncio.sleep(RETRY_SECONDS)


async def run() -> None:
    tracing.log_status()
    stop, wake = threading.Event(), threading.Event()
    embedder.start(stop, wake)
    moodle_reader.start()  # the course files the browser extension uploaded (moodle_files.py)
    monitoring = asyncio.create_task(health.run())  # Alerts to the admins, independent of Redis.
    if not settings.redis_url:
        log.warning("REDIS_URL is not set: the embedders poll the queue")
        await asyncio.Event().wait()
        return
    # The socket timeout must be longer than the blocking read, or an idle stream looks like a broken connection.
    client = redis.from_url(settings.redis_url, socket_timeout=BLOCK_MS / 1000 + 25, health_check_interval=30)
    await client.ping()
    log.info("watching %s", STREAM)
    try:
        await wake_on_new(client, wake)
    finally:
        tracing.flush()
        stop.set()
        monitoring.cancel()
        await client.aclose()
        pg.close()


def main() -> None:
    logs.setup()
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
