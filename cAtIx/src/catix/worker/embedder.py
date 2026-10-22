"""Background workers that turn queued messages into vectors.

A trigger puts every new or edited message into embedding_queue. A worker claims the newest queued messages
(FOR UPDATE SKIP LOCKED, so several workers and processes can run side by side), embeds them in one request,
stores the vectors and removes them from the queue, all in one transaction: if the embeddings server fails the
messages simply stay queued. Newest first, so under a backlog recent messages become searchable by meaning first.
Until its vector exists a message is already found by words. The pieces of the wiki have a queue of their own
(wiki/search_index.py), served when no message waits.
"""

import logging
import threading
import time

from catix.db import pg
from catix.db.rows import QueuedMessage
from catix.settings import settings
from catix.wiki import search_index

log = logging.getLogger("catix.embedder")

IDLE_POLL_SECONDS = 1.0
BACKOFF_MAX_SECONDS = 30.0
LOG_EVERY_SECONDS = 10.0

CLAIM = """
SELECT m.id, m.chat_id, m.text
FROM messages m
JOIN (SELECT message_id FROM embedding_queue ORDER BY message_id DESC LIMIT %s FOR UPDATE SKIP LOCKED) q
  ON q.message_id = m.id
"""


def embed_batch() -> int:
    """Embed one batch of queued messages; returns how many (0 = queue empty)."""
    with pg.connection() as conn:
        rows = pg.rows(conn, QueuedMessage, CLAIM, (settings.embed_batch,))
        if not rows:
            return 0
        vectors = pg.embed([r.text for r in rows])  # Raises on failure: the transaction rolls back, rows stay queued.
        with conn.cursor() as cur:
            cur.executemany(
                """INSERT INTO message_embeddings (message_id, chat_id, embedding) VALUES (%s, %s, %s)
                   ON CONFLICT (message_id) DO UPDATE SET embedding = excluded.embedding""",
                [(r.id, r.chat_id, v) for r, v in zip(rows, vectors)],
            )
        conn.execute("DELETE FROM embedding_queue WHERE message_id = ANY(%s::bigint[])", ([r.id for r in rows],))
        return len(rows)


def backlog() -> int:
    with pg.connection() as conn:
        return pg.scalar(conn, "SELECT count(*) FROM embedding_queue")


def run_forever(stop: threading.Event, wake: threading.Event) -> None:
    """Worker loop. `wake` is set by the writer after new messages arrive, to skip the idle wait."""
    backoff, done, last_log = 1.0, 0, time.monotonic()
    while not stop.is_set():
        try:
            # Pieces of the wiki (catix-wiki index) only when no message waits: fresh messages come first.
            n = embed_batch() or search_index.embed_batch()
            backoff = 1.0
        except Exception:  # noqa: BLE001 - keep the worker alive through database or server outages
            log.exception("embedding failed, retrying in %.0fs", backoff)
            stop.wait(backoff)
            backoff = min(backoff * 2, BACKOFF_MAX_SECONDS)
            continue
        done += n
        if n == 0:
            wake.wait(IDLE_POLL_SECONDS)
            wake.clear()
        if done and time.monotonic() - last_log > LOG_EVERY_SECONDS:
            log.info("embedded %d messages, %d still queued", done, backlog())
            done, last_log = 0, time.monotonic()


def start(stop: threading.Event, wake: threading.Event) -> list[threading.Thread]:
    threads = [
        threading.Thread(target=run_forever, args=(stop, wake), name=f"embedder-{i}", daemon=True)
        for i in range(settings.embed_workers)
    ]
    for thread in threads:
        thread.start()
    return threads


def main() -> None:
    """`catix-embed`: run the workers on their own, e.g. to drain a backlog or when only the userbot is running."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    stop, wake = threading.Event(), threading.Event()
    start(stop, wake)
    log.info("%d workers running, %d messages queued", settings.embed_workers, backlog())
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        stop.set()
    finally:
        pg.close()
