"""The sources of the documents: the code that reads them (one module each) and how often each is asked.

    eduwiki.py      eduwiki.innopolis.university: a snapshot of the pages (wikitext -> markdown by code)
    regulations.py  the documents the sites link (PDF, office files, archives): text, then documents under regulations/ by code
    rpd.py          course programmes (РПД) from the archives of sveden/education: documents under course-programmes/, by code only
    sites.py        the sites of the university and its services (its disclosure section sveden/ too): documents under sites/, their documents as regulations;
                    the pages that appeared on them every 6 hours (new-pages), all their pages again every week (sites)
    pastpapers.py   past exam papers the students keep in Notion: documents under past-papers/, one per subject, by code only
    unvisited       (not scheduled) the links of known sites no run has read, before the schedule on every turn
    ocr_queue.py    the scans the sources queue for a manual run with OCR (no scheduled model switching), and apart from it
                    those too long for OCR; `catix-docs regs queue` shows them, the run tells the admins when they grow


A source is code: `update` asks the source what is new or changed since the last time and brings it into Postgres
(source_files; the run then makes documents of it, docs/runner.py). It returns how many things changed; 0 means there is
nothing to make. Each source asks in its own way: the eduwiki by revision numbers (one listing), the sites by their pages,
the documents already read by what the site says about the file (HEAD: ETag, date, size), without downloading them.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class Source:
    name: str
    every: timedelta  # how often it is asked
    update: Callable[[], int]  # brings what changed into source_files; the number of changes
    about: str


# The modules are imported when a source is asked, not here: they import each other, and a registry that imported them all at
# once would make that a cycle.


def _eduwiki() -> int:
    from catix.docs.sources import eduwiki

    return eduwiki.fetch([0])


def _files() -> int:
    """Documents already read that changed on the site under the same link; fetch downloads them again."""
    from catix.docs.sources import regulations, rpd

    changed = regulations.refresh() + rpd.refresh()
    return changed and regulations.fetch(ocr=False) + rpd.fetch()  # (scans stay queued for a manual OCR run)


def _sites() -> int:
    """The pages of the sites read again, and through them the documents: those that are new or
    changed, the pages of trusted sites their text names, their documents, ... (sites.fetch with documents: document -> site
    -> document -> site). Text layers only: scans stay queued for a manual OCR run; the bot's LLM is never stopped."""
    from catix.docs.sources import regulations, rpd, sites

    return regulations.refresh(prefix="site-") + sites.fetch(documents=True, ocr=False) + rpd.fetch()  # (and the course programmes of new archives)


def _new_pages() -> int:
    """The pages that appeared on the sites since the last run (sites.fetch_new), wave after wave through the documents they
    link (site -> site -> document -> site): a page of a hackathon on media is in the search hours after it is published, not up
    to a week later at the run of `sites`. With them every trusted link no run has processed: the documents not read yet and
    the pages that cached pages and documents link (sites.unread_links); one that gave nothing waits sites.RETRY. The
    documents are read by their text layer alone: scans stay queued for a manual OCR run, so the OCR model need not be up
    every 6 hours. The disclosure section is among the feeds of the university's site (the catalog of sites): a document it
    lists is in the search hours later, the course programmes of a new archive too (rpd.fetch)."""
    from catix.docs.sources import rpd, sites

    return sites.fetch_new(documents=True) + rpd.fetch()


def _papers() -> int:
    from catix.docs.sources import pastpapers

    return pastpapers.fetch(ocr=False)


SOURCES = [
    Source("eduwiki", timedelta(days=6), _eduwiki, "eduwiki.innopolis.university: pages whose revision changed"),
    Source("new-pages", timedelta(hours=6), _new_pages, "the feed (or start page) of each site: the new pages it links, the new pages of other trusted sites they link, "
    "the trusted links of pages and documents no run has read, and through the documents they link (text layers only, scans stay queued for OCR)"),
    Source("files", timedelta(days=7), _files, "documents and archives read before that changed on the site (HEAD, ~1 request every 2 s)"),
    Source("sites", timedelta(days=7), _sites, "every site again, its documents (text layers only, scans stay queued for OCR) and the pages their text names, wave after wave"),
    Source("papers", timedelta(days=7), _papers, "past exam papers in the students' Notion database: new rows and their files"),
]


def _unvisited() -> int:
    """What `catix-docs sites unvisited --known` shows: the pages of known sites that cached pages and documents link and no run
    read, and the files no run read yet (sites.backlog); read as the run of new links reads them (text layers only)."""
    from catix.docs.sources import rpd, sites

    if not (waiting := sites.backlog()):
        return 0
    print(f"  {waiting} links of known sites no run has read", flush=True)
    return sites.fetch(only_new=True, documents=True, ocr=False) + rpd.fetch()


BACKLOG = Source("unvisited", timedelta(0), _unvisited, "the links of known sites no run has read (catix-docs sites unvisited --known), "
                 "before the schedule on every turn of the loop")


def sites_of(names: list[str]) -> Source:
    """The weekly `sites` limited to the named sites (`catix-docs run --site NAME`, a request of POST /sites/parse): their documents
    asked again (HEAD), their pages and, through them, the documents they link (text layers only, scans stay queued for OCR).
    A name the catalog no longer has is passed by. The schedule of `sites` does not change: of the other sites only the pages
    they do not have yet are read (sites.fetch), their known pages wait for the weekly run."""
    names = list(dict.fromkeys(names))

    def update() -> int:
        from catix.docs.sources import regulations, sites

        sites.reload_catalog()
        every = sites.SITES
        known = [name for name in names if name in every]
        if gone := [name for name in names if name not in every]:
            print(f"  not in the catalog of sites (passed by): {', '.join(gone)}", flush=True)
        if not known:
            return 0
        return sum(regulations.refresh(prefix=f"site-{name}-") for name in known) + sites.fetch(known, documents=True, ocr=False)

    return Source(f"sites ({', '.join(names)})", timedelta(days=36500), update,
                  f"the sites {', '.join(names)} only: their documents, pages and the documents they link (scans stay queued for OCR)")
