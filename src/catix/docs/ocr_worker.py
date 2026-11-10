"""The OCR queue read as scans arrive: a thread of `catix-docs run --loop` (start). LightOnOCR (sources/lighton.py) reads
every scan the sources queued (ocr_queue), then the documents are rebuilt. It wakes when a source queues a scan (wake) and
every RESCAN anyway (scans queued by another process: a manual `regs fetch --no-ocr`, ones that failed)."""

import threading
import traceback
from datetime import datetime, timezone

from catix.docs import build
from catix.docs.sources import lighton, ocr_queue, pastpapers, regulations
from catix.settings import settings

RESCAN = 30 * 60  # seconds: the queue looked at again without a wake
AWAY = 60  # seconds before asking again a server that did not answer
WAKE = threading.Event()


def wake() -> None:
    """A scan was queued: the thread looks at the queue now."""
    WAKE.set()


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def waiting() -> dict[str, list[str]]:
    """source ('regs' | 'papers') -> the keys of its scans queued for OCR (not those too long)."""
    out: dict[str, list[str]] = {}
    for scan in ocr_queue.scans():
        if not scan.too_long:
            out.setdefault(scan.source, []).append(scan.key)
    return out


def read_once() -> tuple[int, bool]:
    """(documents read, whether the server answered): the queued scans of the documents (regulations.read_new limited to
    their keys) and of the past papers (pastpapers.fetch with OCR), within each one's page budget of a run."""
    queue = waiting()
    if not queue:
        return 0, True
    if not lighton.available():
        return 0, False
    print(f"[{now()}] OCR: {', '.join(f'{source} {len(keys)}' for source, keys in queue.items())} scans wait", flush=True)
    read = len(regulations.read_new(prefixes=tuple(queue["regs"]), ocr=True)) if "regs" in queue else 0
    read += pastpapers.fetch(ocr=True) if "papers" in queue else 0
    return read, True


def loop() -> None:
    """For ever: read_once; a read that brought documents is rebuilt and the queue looked at again at once (more may wait
    beyond the budget); else wait for a wake, AWAY seconds when the server did not answer, RESCAN otherwise. An exception
    is printed and the loop goes on."""
    while True:
        WAKE.clear()
        try:
            read, up = read_once()
            if read:
                print(f"[{now()}] OCR: {read} documents read; rebuilding", flush=True)
                counts = build.rebuild()
                print(f"[{now()}] OCR: documents: {counts.get('pages new', 0)} new, {counts.get('pages changed', 0)} changed, "
                      f"{counts.get('pages removed', 0)} removed", flush=True)
                continue
        except Exception:  # noqa: BLE001 - the thread must not die; the next wake or RESCAN tries again
            traceback.print_exc()
            up = True
        if not up:
            print(f"[{now()}] OCR: the server {settings.ocr_route} does not answer; the scans stay queued", flush=True)
        WAKE.wait(AWAY if not up else RESCAN)


def start() -> threading.Thread:
    """The OCR thread, a daemon: it ends with the run."""
    thread = threading.Thread(target=loop, name="ocr", daemon=True)
    thread.start()
    return thread
