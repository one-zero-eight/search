"""The documents of every source made from what source_files holds, written to the store (`catix-docs build`)."""

import threading
from collections import Counter

from catix.db import pg
from catix.docs import store
from catix.docs.sources import eduwiki, pastpapers, regulations, rpd, sites

PREFIXES = ("regulations/", "course-programmes/", "sites/", "past-papers/", "eduwiki/")


LOCK = threading.Lock()  # (the run and its OCR thread rebuild one after the other)


def rebuild() -> dict[str, int]:
    """The documents of every source from what source_files holds: changed ones rewritten, gone ones removed. One at a time
    in the process (the run and its OCR thread)."""
    with LOCK:
        return _rebuild()


def _rebuild() -> dict[str, int]:
    """The documents of every source from what source_files holds: changed ones rewritten, gone ones removed."""
    counts: Counter[str] = Counter()
    for prefix, make in (
        ("regulations/", regulations.compile_all),
        ("course-programmes/", rpd.compile_all),
        ("past-papers/", pastpapers.compile_all),
        ("eduwiki/", eduwiki.compile_all),
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
