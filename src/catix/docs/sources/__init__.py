"""The sources of the documents: the code that reads them (one module each).

    eduwiki.py      eduwiki.innopolis.university: a snapshot of the pages (wikitext -> markdown by code)
    regulations.py  the documents the sites link (PDF, office files, archives): text, then documents under regulations/ by code
    rpd.py          course programmes (РПД) from the archives of sveden/education: documents under course-programmes/, by code only
    sites.py        the sites of the university and its services (its disclosure section sveden/ too): documents under sites/, their documents as regulations
    ocr_queue.py    the scans the sources queue for the OCR thread, and apart from it those too long for OCR;
                    `catix-docs regs queue` shows them, the run tells the admins when they grow

The sites and the documents are read by the crawl: the frontier (docs/frontier.py) says which address is read next and when it is
read again, the runner (docs/runner.py) reads it. The other sources are jobs (JOBS): code that asks its source what is new
since the last time, on an interval of its own, and brings it into Postgres. It returns how many things changed; 0 means there
is nothing to make. Each asks in its own way: the eduwiki by revision numbers (one listing), the course programmes by their
archives (a HEAD each).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class Job:
    name: str
    every: timedelta  # how often it is asked
    run: Callable[[], int]  # brings what changed into Postgres; the number of changes
    group: str  # the documents it changes (build.rebuild)


# The modules are imported when a job runs, not here: they import each other, and a registry that imported them all at once
# would make that a cycle.


def _eduwiki() -> int:
    from catix.docs.sources import eduwiki

    return eduwiki.fetch([0])


def _rpd() -> int:
    """The course programmes of the archives the crawl found and no run has read."""
    from catix.docs.sources import rpd

    return rpd.fetch()


def _rpd_refresh() -> int:
    """The archives read before that changed on the site (HEAD), and the programmes of the changed ones read again."""
    from catix.docs.sources import rpd

    return rpd.refresh() + rpd.fetch()


JOBS = [
    Job("eduwiki", timedelta(days=6), _eduwiki, "eduwiki"),
    Job("rpd", timedelta(hours=6), _rpd, "course-programmes"),
    Job("rpd-refresh", timedelta(days=7), _rpd_refresh, "course-programmes"),
]
