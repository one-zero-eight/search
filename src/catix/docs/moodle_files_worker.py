"""The course files users uploaded, read as they arrive: a thread of `catix-docs run --loop` (start). It claims one blob of
`moodle_blobs` at a time, reads its text in the sandbox of moodle_files.read_file (text layer, LibreOffice, LightOnOCR) and
stores its pieces; the embeddings worker embeds them."""

import threading
import time
import traceback
from datetime import datetime, timezone

from catix import moodle_files
from catix.moodle_files import OcrAway, ReadFailed

IDLE = 30  # seconds before the queue is looked at again when it was empty
AWAY = 60  # seconds before asking again when the OCR server did not answer


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


def read_once() -> bool:
    """Read one queued file; False when none waited, or the OCR server did not answer (the file stays queued)."""
    job = moodle_files.claim()
    if job is None:
        return False
    label = f"[{now()}] moodle files: {job['sha256'][:12]} {job['suffix']}"
    try:
        found = moodle_files.read_file(job["data"], job["suffix"])
    except OcrAway:
        moodle_files.fail(job, away=True, note="OCR server away")
        print(f"{label} OCR server away", flush=True)
        return False
    except ReadFailed:
        moodle_files.fail(job, away=False, note="could not be read")
        print(f"{label} failed", flush=True)
        return True
    except BaseException:
        moodle_files.fail(job, away=False, note="could not be read")
        raise
    moodle_files.finish(job, found)
    print(f"{label} {found.skipped or found.method}", flush=True)
    return True


def loop() -> None:
    """For ever: read_once, and wait when there was nothing to read (AWAY when the OCR server did not answer). An exception
    is printed and the loop goes on."""
    while True:
        try:
            if read_once():
                continue
        except Exception:  # noqa: BLE001 - the thread must not die; the next pass tries again
            traceback.print_exc()
        time.sleep(IDLE)


def start() -> threading.Thread:
    """The moodle-files thread, a daemon: it ends with the run."""
    thread = threading.Thread(target=loop, name="moodle-files", daemon=True)
    thread.start()
    return thread
