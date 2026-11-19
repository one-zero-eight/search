"""The documents the crawl registers, read beside it: a thread of `catix-docs run --loop` (start). It downloads and reads by
their text layer (regulations.read_new without OCR: scans are queued for the OCR thread) the documents the sites link and
those they lead to, while the crawl goes on reading pages. It wakes when the crawl saves a site's index (wake) and every
RESCAN anyway. It never writes a site's index (collect=False): the crawl adds the documents of other trusted sites
(sites.collect_linked_docs). What it reads reaches the search with the next flush (flusher.py)."""

import threading
import traceback
from datetime import datetime, timezone

from catix.docs.sources import regulations

RESCAN = 10 * 60  # seconds: the documents looked at again without a wake
WAKE = threading.Event()
_RUNNING = threading.Event()


def wake() -> None:
    """The crawl registered documents: the thread looks now."""
    WAKE.set()


def running() -> bool:
    """Whether this process reads the documents in this thread (the sources then leave them to it)."""
    return _RUNNING.is_set()


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def loop() -> None:
    """For ever: read the documents not read yet; when some were read, look again at once (the crawl went on registering),
    else wait for a wake or RESCAN. An exception is printed and the loop goes on."""
    while True:
        WAKE.clear()
        try:
            if read := regulations.read_new(ocr=False, collect=False):
                print(f"[{now()}] documents: {len(read)} read beside the crawl", flush=True)
                continue
        except Exception:  # noqa: BLE001 - the thread must not die; the next wake or RESCAN tries again
            traceback.print_exc()
        WAKE.wait(RESCAN)


def start() -> threading.Thread:
    """The document thread, a daemon: it ends with the run."""
    _RUNNING.set()
    thread = threading.Thread(target=loop, name="documents", daemon=True)
    thread.start()
    return thread
