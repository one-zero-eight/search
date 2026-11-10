"""The documents of every source made from what source_files holds, written to the store (`catix-docs build`)."""

from collections import Counter

from catix.db import pg
from catix.docs import store
from catix.docs.sources import eduwiki, pastpapers, regulations, rpd, sites

PREFIXES = ("regulations/", "course-programmes/", "sites/", "past-papers/", "eduwiki/")


def rebuild() -> dict[str, int]:
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
