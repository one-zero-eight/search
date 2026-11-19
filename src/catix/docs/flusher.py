"""The documents flushed while the threads work: a thread of `catix-docs run --loop` (start). Every EVERY seconds, when the
crawl or the document thread wrote to source_files since the last rebuild of the process (build.BUILT_UP_TO), the documents
are rebuilt: what they read is found by words minutes later, its vectors come from the queue (the worker service)."""

import threading
import traceback
from datetime import datetime, timezone

from catix.docs import build

EVERY = 10 * 60  # seconds between two looks
_TICK = threading.Event()  # (never set: a sleep the tests need not wait for)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def flush_once() -> bool:
    """Rebuild when source_files changed since the last rebuild (or none ran yet in this process); whether it rebuilt."""
    mark = build.source_mark()
    if mark is None or build.BUILT_UP_TO is not None and mark <= build.BUILT_UP_TO:
        return False
    counts = build.rebuild()
    print(f"[{now()}] flush: documents: {counts.get('pages new', 0)} new, {counts.get('pages changed', 0)} changed, "
          f"{counts.get('pages removed', 0)} removed", flush=True)
    return True


def loop() -> None:
    """For ever: wait EVERY seconds, then flush_once. An exception is printed and the loop goes on."""
    while True:
        _TICK.wait(EVERY)
        try:
            flush_once()
        except Exception:  # noqa: BLE001 - the thread must not die; the next look tries again
            traceback.print_exc()


def start() -> threading.Thread:
    """The flush thread, a daemon: it ends with the run."""
    thread = threading.Thread(target=loop, name="flush", daemon=True)
    thread.start()
    return thread
