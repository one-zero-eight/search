"""The documents of every source made from what source_files holds, written to the store (`catix-docs build`)."""

import threading
from collections import Counter
from datetime import datetime

from catix.db import pg
from catix.docs import store
from catix.docs.sources import eduwiki, guide, regulations, rpd, sites

PREFIXES = ("regulations/", "course-programmes/", "sites/", "eduwiki/", "guide/")


LOCK = threading.Lock()  # (the run and its OCR thread rebuild one after the other)
BUILT_UP_TO: datetime | None = None  # max(source_files.updated_at) the last rebuild of this process read from


def source_mark() -> datetime | None:
    """The newest write of the sources (source_files.updated_at); None when the table is empty."""
    with pg.connection() as conn:
        return pg.scalar(conn, "SELECT max(updated_at) FROM source_files")


def rebuild() -> dict[str, int]:
    """The documents of every source from what source_files holds: changed ones rewritten, gone ones removed. One at a time
    in the process (the run and its OCR thread)."""
    global BUILT_UP_TO
    with LOCK:
        mark = source_mark()  # (taken before: writes made during the rebuild count as not built)
        counts = _rebuild()
        BUILT_UP_TO = mark
        return counts


def sync_guide() -> dict[str, int]:
    """The guide documents (sources/guide.py) made what the repo's files say; unchanged ones are left alone."""
    with LOCK:
        return store.sync(guide.PREFIX, guide.compile_all())


def _rebuild() -> dict[str, int]:
    """The documents of every source from what source_files holds: changed ones rewritten, gone ones removed."""
    counts: Counter[str] = Counter()
    for prefix, make in (
        ("regulations/", regulations.compile_all),
        ("course-programmes/", rpd.compile_all),
        ("eduwiki/", eduwiki.compile_all),
        ("guide/", guide.compile_all),
    ):
        print(f"== {prefix}", flush=True)
        counts.update(store.sync(prefix, make()))
    print("== sites/", flush=True)
    docs, keep = sites.compile_all()
    counts.update(store.sync("sites/", docs, keep))
    counts["pages removed"] += store.prune(PREFIXES)
    with pg.connection() as conn:
        counts["pieces marked as copies"] = store.mark_copies(conn)
    return dict(counts)
