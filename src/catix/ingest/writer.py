"""Collects incoming messages and writes them to Postgres in batches.

Handlers only put a message on an in-memory queue. One task takes everything that is waiting (up to a maximum
batch size) and writes it in one transaction, so thousands of messages per second cost a few transactions
instead of thousands, while a lone message is written without delay.
"""

import asyncio
import logging
import threading

from catix.db import store
from catix.ingest import publish as stream_out
from catix.settings import settings

log = logging.getLogger("catix.ingest")

QUEUE_LIMIT = 100_000  # Beyond this handlers wait (backpressure) instead of using unbounded memory.
RETRY_MAX_SECONDS = 30.0


class Writer:
    def __init__(self, wake: threading.Event | None = None) -> None:
        self._queue: asyncio.Queue[tuple[store.ChatInfo, store.Message]] = asyncio.Queue(QUEUE_LIMIT)
        self._wake = wake  # Tells the embedding workers that there is something new to embed.
        self._busy = False  # A batch is being written right now.

    async def put(self, chat: store.ChatInfo, message: store.Message) -> None:
        await self._queue.put((chat, message))

    async def wait_idle(self, timeout: float = 5.0) -> None:
        """Wait until everything handed over so far is written (before an operation that moves stored rows)."""
        deadline = asyncio.get_running_loop().time() + timeout
        while (self._busy or not self._queue.empty()) and asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(0.02)

    async def run(self) -> None:
        batch: list[tuple[store.ChatInfo, store.Message]] = []
        try:
            while True:
                batch = [await self._queue.get()]
                self._busy = True
                # No waiting: take what has already arrived. While a write is running the next batch fills up by
                # itself, so a quiet chat gets its message stored at once and a busy one is written in big batches.
                while len(batch) < settings.ingest_max_batch and not self._queue.empty():
                    batch.append(self._queue.get_nowait())
                await self._write(batch)
                batch = []
                self._busy = False
        except asyncio.CancelledError:
            # Shutting down: do not lose what is already collected.
            while not self._queue.empty():
                batch.append(self._queue.get_nowait())
            if batch:
                store.write_batch([c for c, _ in batch], [m for _, m in batch])
            raise

    async def _write(self, batch: list[tuple[store.ChatInfo, store.Message]]) -> None:
        delay = 1.0
        while True:
            try:
                await asyncio.to_thread(store.write_batch, [c for c, _ in batch], [m for _, m in batch])
                await stream_out.publish([(m.chat_id, m.msg_id) for _, m in batch])
            except Exception:  # noqa: BLE001 - the database may be restarting; keep the batch and retry
                log.exception("writing %d messages failed, retrying in %.0fs", len(batch), delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, RETRY_MAX_SECONDS)
                continue
            if self._wake:
                self._wake.set()
            return
