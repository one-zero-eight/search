"""One request at a time to a host across the threads of the process (the crawl and the OCR thread of `catix-docs run`): two
requests to one host are at least `pause` seconds apart (PAUSE; a site that asks for more says so: Site.pause). Off until
share() (the run turns it on; tests and manual commands wait for nothing)."""

import threading
import time
from urllib.parse import urlsplit

PAUSE = 2.0  # seconds between two requests to one host: regulations.PAUSE
_LOCK = threading.Lock()
_NEXT: dict[str, float] = {}
_SHARED = False


def share() -> None:
    """The threads of this process read the same hosts at once: turn() waits from now on."""
    global _SHARED
    _SHARED = True


def turn(url: str, pause: float = PAUSE) -> None:
    """Wait for the host's turn (nothing when not shared): its next request is `pause` seconds after the one before, of any thread."""
    if not _SHARED:
        return
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    with _LOCK:
        now = time.monotonic()
        at = max(now, _NEXT.get(host, 0.0))
        _NEXT[host] = at + pause
    if at > now:
        time.sleep(at - now)
