"""The documents of every source made from what its tables hold, written to the store (`catix-docs build`)."""

import threading
from collections import Counter

from catix.db import pg
from catix.docs import frontier, store
from catix.docs.sources import eduwiki, guide, regulations, rpd, sites

PREFIXES = ("regulations/", "course-programmes/", "sites/", "eduwiki/", "guide/")
GROUPS = {  # a group of documents -> (its prefix, what makes them); the other group is "sites/<name>"
    "regulations": ("regulations/", regulations.compile_all),
    "course-programmes": ("course-programmes/", rpd.compile_all),
    "eduwiki": ("eduwiki/", eduwiki.compile_all),
    "guide": ("guide/", guide.compile_all),
}

LOCK = threading.Lock()  # (the run and its OCR thread rebuild one after the other)


def rebuild(groups: set[str] | None = None) -> dict[str, int]:
    """The documents made again and written: changed ones rewritten, gone ones removed. One at a time in the process (the run and
    its OCR thread). `groups`: only these ("regulations", "course-programmes", "eduwiki", "guide", "sites/<name>"); None: every
    source, and the documents of a source that is gone are pruned."""
    with LOCK:
        return _rebuild() if groups is None else _rebuild_groups(groups)


def sync_guide() -> dict[str, int]:
    """The guide documents (sources/guide.py) made what the repo's files say; unchanged ones are left alone."""
    with LOCK:
        return store.sync(guide.PREFIX, guide.compile_all())


def _rebuild_groups(groups: set[str]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    sites.reload_catalog()
    for group in sorted(groups):
        if group in GROUPS:
            prefix, make = GROUPS[group]
            print(f"== {prefix}", flush=True)
            counts.update(store.sync(prefix, make()))
        elif group.startswith("sites/"):
            name = group.removeprefix("sites/")
            if name not in sites.SITES or not frontier.has_pages(name):
                continue  # (a site that left the catalog or that is not read here: the full rebuild prunes or keeps its documents)
            print(f"== {group}/", flush=True)
            counts.update(store.sync(f"{group}/", sites.compile_site(name)))
        else:
            raise ValueError(f"no group of documents {group!r}")
    with pg.connection() as conn:
        counts["pieces marked as copies"] = store.mark_copies(conn)
    return dict(counts)


def _rebuild() -> dict[str, int]:
    """The documents of every source from what its tables hold: changed ones rewritten, gone ones removed."""
    counts: Counter[str] = Counter()
    for group, (prefix, make) in GROUPS.items():
        print(f"== {prefix}", flush=True)
        counts.update(store.sync(prefix, make()))
    print("== sites/", flush=True)
    docs, keep = sites.compile_all()
    counts.update(store.sync("sites/", docs, keep))
    counts["pages removed"] += store.prune(PREFIXES)
    with pg.connection() as conn:
        counts["pieces marked as copies"] = store.mark_copies(conn)
    return dict(counts)
