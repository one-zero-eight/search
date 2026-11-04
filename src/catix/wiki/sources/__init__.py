"""The sources of the wiki: the code that reads them (one module each) and how often each is asked.

    eduwiki.py      eduwiki.innopolis.university: a snapshot of the pages (compile.py makes the bundle's pages of it)
    sveden.py       innopolis.university/sveden: every document the site discloses; the model decides which to keep
    regulations.py  the kept documents (PDF): text, then wiki/raw/regulations/ by code (the model writes only a description)
    rpd.py          course programmes (РПД) from the archives of sveden/education: wiki/raw/course-programmes/, by code only
    sites.py        the sites of the university's services (campus life, the campus hotel): wiki/raw/sites/, their documents as regulations;
                    the pages that appeared on them every 6 hours (new-pages), all their pages again every week (sites)
    discover.py     new sites of the university in the links of the pages: pending a person's look (autopilot accept | discard)
    pastpapers.py   past exam papers the students keep in Notion: wiki/raw/past-papers/, one page per subject, by code only
    ocr_queue.py    the scans the sources queue for a manual run with OCR (no scheduled model switching), and apart from it
                    those too long for OCR; `catix-wiki regs queue` shows them, the wiki's run tells the admins when they grow
    mock.py         a stand-in site for showing and testing the wiki's run (WIKI_MOCK_SITE)


A source is code: `update` asks the source what is new or changed since the last time and brings it into raw/ (the
wiki's run then makes pages of it, autopilot.py). It returns how many things changed; 0 means there is nothing to make.
Each source asks in its own way: the eduwiki by revision numbers (one listing), the disclosure section of the site by
its list of documents, the documents already read by what the site says about the file (HEAD: ETag, date, size),
without downloading them.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

from catix.settings import settings


@dataclass(frozen=True)
class Source:
    name: str
    every: timedelta  # how often it is asked
    update: Callable[[], int]  # brings what changed into raw/; the number of changes
    about: str


# The modules are imported when a source is asked, not here: they import compile.py, which imports eduwiki.py from this
# package, and a registry that imported them all at once would make that a cycle.


def _eduwiki() -> int:
    from catix.wiki.sources import eduwiki

    return eduwiki.fetch([0])


def _sveden() -> int:
    """New documents of the disclosure section: the listing, the model's decision about the new ones, then the files of
    the kept ones and the course programmes of new archives."""
    from catix.wiki.sources import regulations, rpd, sveden

    changed = sveden.discover()
    sveden.triage()
    return changed + regulations.fetch(ocr=False) + rpd.fetch()  # (scans stay queued for a manual OCR run)


def _files() -> int:
    """Documents already read that changed on the site under the same link; fetch downloads them again."""
    from catix.wiki.sources import regulations, rpd

    changed = regulations.refresh() + rpd.refresh()
    return changed and regulations.fetch(ocr=False) + rpd.fetch()  # (scans stay queued for a manual OCR run)


def _discover() -> int:
    """New sites of the university in the links of the pages already read: pending a person's look (discover.py)."""
    from catix.wiki import autopilot
    from catix.wiki.sources import discover

    return discover.discover(set(autopilot.load_state().get("rejected_sites", [])))


def _sites() -> int:
    """The pages of the sites read again (the pending ones too), and through them the documents: those that are new or
    changed, the pages of trusted sites their text names, their documents, ... (sites.fetch with documents: document -> site
    -> document -> site). Text layers only: scans stay queued for a manual OCR run; the bot's LLM is never stopped."""
    from catix.wiki.sources import regulations, sites

    return regulations.refresh(prefix="site-") + sites.fetch(documents=True, ocr=False)


def _new_pages() -> int:
    """The pages that appeared on the sites since the last run (sites.fetch_new), wave after wave through the documents they
    link (site -> site -> document -> site): a page of a hackathon on media is in the wiki hours after it is published, not up
    to a week later at the run of `sites`. With them every trusted link no run has processed: the documents not read yet and
    the pages that cached pages and documents link (sites.unread_links); one that gave nothing waits sites.RETRY. The
    documents are read by their text layer alone: scans stay queued for a manual OCR run, so the OCR model need not be up
    every 6 hours."""
    from catix.wiki.sources import sites

    return sites.fetch_new(documents=True)


def _new_sites() -> int:
    """Only the sites found by discover.py that wait for a person's look: their pages and the documents they link (`autopilot
    --only-new`, after `catix-wiki sites discover --all`). The weekly `sites` reads every site again, which takes hours."""
    from catix.wiki.sources import sites

    names = sorted(sites.pending_sites())
    print(f"  {len(names)} pending sites: {', '.join(names) or 'none'}", flush=True)
    return sites.fetch(names, documents=True, ocr=False) if names else 0  # (scans stay queued for a manual OCR run)


def _papers() -> int:
    from catix.wiki.sources import pastpapers

    return pastpapers.fetch(ocr=False)


SOURCES = [
    # TODO: Commented it for testing
    # Source("eduwiki", timedelta(days=6), _eduwiki, "eduwiki.innopolis.university: pages whose revision changed"),
    Source("new-pages", timedelta(seconds=1), _new_pages, "the feed (or start page) of each site: the new pages it links, the new pages of other trusted sites they link, "
    "the trusted links of pages and documents no run has read, and through the documents they link (text layers only, scans stay queued for OCR)"),
    # Source("sveden", timedelta(days=1), _sveden, "innopolis.university/sveden: documents and course programmes added to the site (scans stay queued for OCR)"),
    # Source("files", timedelta(days=7), _files, "documents and archives read before that changed on the site (HEAD, ~1 request every 2 s)"),
    # Source("discover", timedelta(days=7), _discover, "new hosts of the university in the links of the pages: probed, then read and sent for a person's look"),
    # Source("sites", timedelta(days=7), _sites, "every site again, its documents (text layers only, scans stay queued for OCR) and the pages their text names, wave after wave"),
    # Source("papers", timedelta(days=7), _papers, "past exam papers in the students' Notion database: new rows and their files"),
]


# Asked by name only (`autopilot --source NAME`, or its own flag), never by the schedule.
ON_REQUEST = [Source("new-sites", timedelta(days=36500), _new_sites, "the sites discover.py found that wait for a person's look, and only them")]


def sites_of(names: list[str]) -> Source:
    """The weekly `sites` limited to the named sites (`autopilot --site NAME`, a request of POST /sites/parse): their documents
    asked again (HEAD), their pages and, through them, the documents they link (text layers only, scans stay queued for OCR).
    A name the catalog no longer has is passed by. The schedule of `sites` does not change: of the other sites only the pages
    they do not have yet are read (sites.fetch), their known pages wait for the weekly run."""
    names = list(dict.fromkeys(names))

    def update() -> int:
        from catix.wiki.sources import regulations, sites

        every = sites.every_site()
        known = [name for name in names if name in every]
        if gone := [name for name in names if name not in every]:
            print(f"  not in the catalog of sites (passed by): {', '.join(gone)}", flush=True)
        if not known:
            return 0
        return sum(regulations.refresh(prefix=f"site-{name}-") for name in known) + sites.fetch(known, documents=True, ocr=False)

    return Source(f"sites ({', '.join(names)})", timedelta(days=36500), update,
                  f"the sites {', '.join(names)} only: their documents, pages and the documents they link (scans stay queued for OCR)")


def _mock() -> int:
    from catix.wiki.sources import mock

    return mock.update()


if settings.wiki_mock_site:  # a stand-in site for showing and testing the run (mock.py)
    SOURCES.append(Source("mock", timedelta(minutes=1), _mock, f"{settings.wiki_mock_site}: new documents and new versions of them"))
