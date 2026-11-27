"""The crawl as tables: one row per address (crawl_urls) and the links between them (crawl_links).

A row is a page, a listing (a sitemap, the pages a browser lists) or a document (a file: PDF, Word, an archive). It knows when it is
read again (`next_at`, then `every` later; NULL: never) and in which order (`priority`: 0 a request, 1 an address found now,
2 a read again). The runner (runner.py) reads the row that is due next (next_due), sources/sites.py read_page / read_listing
and regulations.recheck read it and write what they found back (save, set_links) and the new addresses (add).

An address is sites.address(url): the same page by any of its spellings or the aliases of its site. A page is kept in the search
while its row is live (`ok`, or `missing`: the site said 404 once); a row that is no longer linked from any live row is `unlinked_since`
that day, and after UNLINKED_GRACE the sweep (daily) drops it. The documents: a row per file, its `doc_key` the key of its notes
(document_files) and of its archive manifest (archives).
"""

from collections import Counter
from dataclasses import dataclass, field, fields
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import urljoin, urlsplit

from psycopg.types.json import Jsonb

from catix.db import pg
from catix.docs import notes
from catix.docs.sources import crawl, regulations, sites

PAGE_EVERY = timedelta(days=7)
FEED_EVERY = timedelta(hours=6)
DOCUMENT_EVERY = timedelta(days=7)
SOON = timedelta(days=1)
UNLINKED_GRACE = timedelta(days=7)
SWEEP_EVERY = timedelta(days=1)
DOC_BATCH = 50
REQUEST, NEW, RECHECK = 0, 1, 2
RETRY = sites.RETRY  # an address that gave nothing waits this long
UNSIGNED_EVERY = regulations.UNSIGNED_EVERY  # a file the site says nothing about is downloaded and compared by its bytes this often
LIVE = ("ok", "missing")


@dataclass
class Row:
    address: str
    url: str
    site: str
    kind: str
    pinned: bool
    every: timedelta
    next_at: datetime | None
    priority: int
    state: str
    why: str | None
    slug: str | None
    doc_key: str | None
    ext: str | None
    title: str | None
    sha256: str | None
    validators: dict
    short_words: int | None
    text: str | None
    audience: list[str] | None
    fetched_at: datetime | None
    read_at: datetime | None
    unlinked_since: date | None


COLUMNS = [f.name for f in fields(Row)]
_LIST = ", ".join(COLUMNS)
_UNLIST = ", ".join(f"u.{c}" for c in COLUMNS)


@dataclass
class DocRow(Row):
    anchor: str = ""  # the longest text of a link to it
    context: str = ""  # the longest context of a link to it (sites.contexts_of)
    linking_sites: list[str] = field(default_factory=list)  # the sites of the live pages that link it


@dataclass
class Found:
    url: str
    site: str
    kind: str  # 'page' or 'document'
    ext: str | None = None
    doc_key: str | None = None


@dataclass
class Link:
    dst: str  # sites.address of the link
    anchor: str = ""
    context: str = ""


def later(delta: timedelta) -> datetime:
    return datetime.now(timezone.utc) + delta


def _row(record: dict) -> Row:
    return Row(**record)


def starts(site: sites.Site) -> dict[str, str]:
    """address -> url of the start pages of a site: its base and its feeds (sites.entries)."""
    return {sites.address(url): url for url in (sites.page_url(site, site.base), *(sites.page_url(site, u) for u in sites.entries(site))) if url}


def feed_every(site: sites.Site) -> timedelta:
    """How often the start pages of a site are read: its feeds show the new pages (a site behind a login: as any page)."""
    return PAGE_EVERY if site.profile else FEED_EVERY


def seed() -> None:
    """The rows the catalog says must be there: each site's start pages and feeds (read every FEED_EVERY: the pages that appeared
    are in them first), its listing (the sitemap, the pages a browser lists) and the first regulations (regulations.DOCS). They are
    `pinned`: no sweep drops them. A site that names no more pages as feeds has its old pinned rows read like any page again."""
    sites.reload_catalog()
    with pg.connection() as conn:
        for name, site in sites.SITES.items():
            every, by_address = feed_every(site), starts(site)
            for address in by_address:
                conn.execute(
                    """INSERT INTO crawl_urls (address, url, site, kind, pinned, every, next_at, priority) VALUES (%s, %s, %s, 'page', true, %s, now(), %s)
                       ON CONFLICT (address) DO UPDATE SET pinned = true, every = excluded.every""",
                    (address, by_address[address], name, every, NEW))
            conn.execute("UPDATE crawl_urls SET pinned = false, every = %s WHERE site = %s AND kind = 'page' AND pinned AND address <> ALL(%s)",
                         (PAGE_EVERY, name, list(by_address)))
            listings = []
            if site.sitemap or site.discover:
                url = urljoin(site.base, site.sitemap if isinstance(site.sitemap, str) else "sitemap.xml")
                listings.append(sites.address(url))
                conn.execute(
                    """INSERT INTO crawl_urls (address, url, site, kind, pinned, every, next_at, priority) VALUES (%s, %s, %s, 'listing', true, %s, now(), %s)
                       ON CONFLICT (address) DO UPDATE SET pinned = true, every = excluded.every""",
                    (listings[0], url, name, PAGE_EVERY, NEW))
            conn.execute("DELETE FROM crawl_urls WHERE site = %s AND kind = 'listing' AND address <> ALL(%s)", (name, listings))
        for key, (_, path) in regulations.DOCS.items():
            url = regulations.BASE + path
            conn.execute(
                """INSERT INTO crawl_urls (address, url, site, kind, pinned, every, next_at, priority, doc_key, ext)
                   VALUES (%s, %s, 'university', 'document', true, %s, now(), %s, %s, 'pdf')
                   ON CONFLICT (address) DO UPDATE SET pinned = true, every = excluded.every, doc_key = excluded.doc_key""",
                (sites.address(url), url, DOCUMENT_EVERY, NEW, key))


def add(found: list[Found], by: Row | None = None) -> int:
    """The addresses that are not rows yet become rows (new, read now); how many. Priority: a request (0) when `by` was one and the
    address is of its site or a document, else NEW. A page is not added once its site has max_pages of them (new, ok or missing): a
    calendar or a catalogue cannot run away. A site behind a login (Site.profile) is read one page after another: the new row waits
    for the latest of the site's."""
    if not found:
        return 0
    sites.reload_catalog()
    pages: dict[str, int] = {}
    later_at: dict[str, datetime | None] = {}
    added = 0
    with pg.connection() as conn:
        for f in found:
            site = sites.SITES.get(f.site)
            if site is None:
                continue
            if f.kind == "page":
                if f.site not in pages:
                    pages[f.site] = pg.scalar(conn, "SELECT count(*) FROM crawl_urls WHERE site = %s AND kind = 'page' AND state IN ('new', 'ok', 'missing')", (f.site,))
                if pages[f.site] >= site.max_pages:
                    continue
            priority = REQUEST if by is not None and by.priority == REQUEST and (by.site == f.site or f.kind == "document") else NEW
            if site.profile:
                if f.site not in later_at:
                    later_at[f.site] = pg.scalar(conn, "SELECT min(next_at) FROM crawl_urls WHERE site = %s AND next_at > now()", (f.site,))
                at = later_at[f.site] or datetime.now(timezone.utc)
            else:
                at = datetime.now(timezone.utc)
            if f.kind == "document":
                key = f.doc_key or sites.doc_key(f.site, f.url)
                ext = f.ext or urlsplit(f.url).path.rsplit(".", 1)[-1].lower()
                every = DOCUMENT_EVERY
            else:
                key, ext, every = None, None, PAGE_EVERY
            n = conn.execute(
                """INSERT INTO crawl_urls (address, url, site, kind, every, next_at, priority, doc_key, ext) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT DO NOTHING""",
                (sites.address(f.url), f.url, f.site, f.kind, every, at, priority, key, ext)).rowcount
            if n and f.kind == "page":
                pages[f.site] += 1
            added += n
    return added


def next_due(documents: bool = True) -> Row | None:
    """The row to read next: requests first, then the addresses found, then those read again; each in the order they are due.
    `documents` False: not a document (the documents are being read by another thread)."""
    with pg.connection() as conn:
        found = conn.execute(f"SELECT {_LIST} FROM crawl_urls WHERE next_at <= now() AND (%s OR kind <> 'document') ORDER BY priority, next_at LIMIT 1",
                             (documents,)).fetchone()
    return _row(found) if found else None


def due_documents(limit: int, priority: int, exclude: str | None = None) -> list[Row]:
    """Up to `limit` documents of that priority that are due, in the order they are due (but the row `exclude`)."""
    with pg.connection() as conn:
        found = conn.execute(f"SELECT {_LIST} FROM crawl_urls WHERE next_at <= now() AND kind = 'document' AND priority = %s AND address <> %s ORDER BY next_at LIMIT %s",
                             (priority, exclude or "", limit)).fetchall()
    return [_row(r) for r in found]


def next_wake() -> datetime | None:
    """When the next row falls due; None when none will."""
    with pg.connection() as conn:
        return pg.scalar(conn, "SELECT min(next_at) FROM crawl_urls WHERE next_at IS NOT NULL")


def save(row: Row, **changes: Any) -> None:
    """What came of reading the row: the columns named. The row is read again (priority RECHECK) at `next_at` when it is given
    (None: never), else after its `every`. The row object takes the values too."""
    for column in changes:
        if column not in COLUMNS or column == "address":
            raise ValueError(column)
    changes.setdefault("priority", RECHECK)
    if "next_at" not in changes:
        changes["next_at"] = later(changes.get("every", row.every))
    values = [Jsonb(v) if isinstance(v, dict) else v for v in changes.values()]
    with pg.connection() as conn:
        conn.execute(f"UPDATE crawl_urls SET {', '.join(f'{c} = %s' for c in changes)} WHERE address = %s", (*values, row.address))
    for column, value in changes.items():
        setattr(row, column, value)


def set_links(src: str, links: list[Link]) -> None:
    """The links of a row replaced: those it makes now. A link repeated keeps its longest text and its first context; a link to
    itself is none."""
    merged: dict[str, Link] = {}
    for link in links:
        if link.dst == src:
            continue
        if (old := merged.get(link.dst)) is None:
            merged[link.dst] = Link(link.dst, link.anchor, link.context)
        else:
            old.anchor = max(old.anchor, link.anchor, key=len)
            old.context = old.context or link.context
    with pg.connection() as conn:
        conn.execute("DELETE FROM crawl_links WHERE src = %s", (src,))
        with conn.cursor() as cur:
            cur.executemany("INSERT INTO crawl_links (src, dst, anchor, context) VALUES (%s, %s, %s, %s)",
                            [(src, link.dst, link.anchor, link.context) for link in merged.values()])


def live_pages(site: str) -> list[Row]:
    """The pages of a site the search has, with their text, by slug."""
    with pg.connection() as conn:
        found = conn.execute(f"SELECT {_LIST} FROM crawl_urls WHERE site = %s AND kind = 'page' AND state IN ('ok', 'missing') AND text IS NOT NULL ORDER BY slug", (site,)).fetchall()
    return [_row(r) for r in found]


def has_pages(site: str) -> bool:
    with pg.connection() as conn:
        return conn.execute("SELECT 1 FROM crawl_urls WHERE site = %s AND kind = 'page' AND state = 'ok' LIMIT 1", (site,)).fetchone() is not None


def same_words(site: str, sha256: str, address: str) -> str | None:
    """The address of another page of the site read with these words, if there is one."""
    with pg.connection() as conn:
        found = conn.execute("SELECT url FROM crawl_urls WHERE site = %s AND kind = 'page' AND state = 'ok' AND sha256 = %s AND address <> %s LIMIT 1", (site, sha256, address)).fetchone()
    return found["url"] if found else None


def slug_taken(site: str, slug: str) -> bool:
    with pg.connection() as conn:
        return conn.execute("SELECT 1 FROM crawl_urls WHERE site = %s AND slug = %s", (site, slug)).fetchone() is not None


def known_documents(addresses: list[str]) -> set[str]:
    """Which of the addresses are rows of documents already (a link without a file's extension that led to one: a download)."""
    if not addresses:
        return set()
    with pg.connection() as conn:
        return {r["address"] for r in conn.execute("SELECT address FROM crawl_urls WHERE kind = 'document' AND address = ANY(%s)", (addresses,)).fetchall()}


def still_due(rows: list[Row]) -> list[Row]:
    """Which of the rows are due still (what was read of them was not noted: no document of the bundle is theirs)."""
    with pg.connection() as conn:
        due = {r["address"] for r in conn.execute("SELECT address FROM crawl_urls WHERE address = ANY(%s) AND next_at <= now()", ([r.address for r in rows],)).fetchall()}
    return [row for row in rows if row.address in due]


def request(names: list[str]) -> int:
    """Every row of these sites that is read again at some time is read now, before the others; how many."""
    with pg.connection() as conn:
        return conn.execute("UPDATE crawl_urls SET priority = %s, next_at = now() WHERE site = ANY(%s) AND state <> 'gone' AND next_at IS NOT NULL", (REQUEST, names)).rowcount


def request_address(address: str) -> None:
    with pg.connection() as conn:
        conn.execute("UPDATE crawl_urls SET priority = %s, next_at = now() WHERE address = %s AND state <> 'gone'", (REQUEST, address))


def requested(names: list[str]) -> bool:
    """Whether a row of these sites asked for is still to be read."""
    with pg.connection() as conn:
        return conn.execute("SELECT 1 FROM crawl_urls WHERE site = ANY(%s) AND priority = %s AND next_at IS NOT NULL LIMIT 1", (names, REQUEST)).fetchone() is not None


def postpone(site: str, delta: timedelta) -> None:
    """The rows of a site that are due wait `delta` (its login ended: nothing can be read there now)."""
    with pg.connection() as conn:
        conn.execute("UPDATE crawl_urls SET next_at = now() + %s WHERE site = %s AND next_at <= now()", (delta, site))


def documents(exts: tuple[str, ...] | None = None) -> list[DocRow]:
    """The document rows with what the pages that link them say of them: the longest text of a link, the longest context and the
    sites of the live pages that link (a row nothing links is `unlinked_since`: it is listed only when something was read of it).
    `exts`: only the files of these extensions."""
    sql = f"""
        SELECT {_UNLIST}, coalesce(a.anchor, u.title, '') AS anchor, coalesce(c.context, '') AS context, coalesce(s.names, '{{}}') AS linking_sites
        FROM crawl_urls u
        LEFT JOIN LATERAL (SELECT l.anchor FROM crawl_links l JOIN crawl_urls src ON src.address = l.src WHERE l.dst = u.address AND l.anchor <> ''
                           ORDER BY src.state IN ('ok', 'missing') DESC, length(l.anchor) DESC, l.src LIMIT 1) a ON true
        LEFT JOIN LATERAL (SELECT l.context FROM crawl_links l JOIN crawl_urls src ON src.address = l.src WHERE l.dst = u.address AND l.context <> ''
                           ORDER BY src.state IN ('ok', 'missing') DESC, length(l.context) DESC, l.src LIMIT 1) c ON true
        LEFT JOIN LATERAL (SELECT array_agg(DISTINCT src.site) AS names FROM crawl_links l JOIN crawl_urls src ON src.address = l.src
                           WHERE l.dst = u.address AND src.state IN ('ok', 'missing')) s ON true
        WHERE u.kind = 'document' AND (%s OR u.ext = ANY(%s)) AND (u.unlinked_since IS NULL
              OR EXISTS (SELECT 1 FROM document_files f WHERE f.key = u.doc_key AND f.text IS NOT NULL)
              OR EXISTS (SELECT 1 FROM archives r WHERE r.key = u.doc_key))
        ORDER BY u.doc_key"""
    with pg.connection() as conn:
        return [DocRow(**r) for r in conn.execute(sql, (exts is None, list(exts or ()))).fetchall()]


def documents_read(keys: list[str], note: bool = True) -> set[str]:
    """The bookkeeping after documents were read (regulations._fetch_once): each container (an archive and its members, or the file)
    that has a row gets its state from its notes (regulations.note_state) and its links from its text and its members': the
    documents and the pages the text names are rows too. Keys without a row are passed by. The addresses of the rows noted.
    Without `note` only the links are made (the import of the old store)."""
    docs = regulations.all_docs()
    containers: dict[str, list[str]] = {}
    for key, d in docs.items():
        containers.setdefault(d.get("archive_key") or key, []).append(key)
    wanted = dict.fromkeys(docs[k].get("archive_key") or k for k in keys if k in docs)
    saved: set[str] = set()
    for container in wanted:
        with pg.connection() as conn:
            found = conn.execute(f"SELECT {_LIST} FROM crawl_urls WHERE doc_key = %s", (container,)).fetchone()
        if found is None:
            continue
        row = _row(found)
        if note:
            state, why, delay = regulations.note_state(container, docs.get(container) or docs[containers[container][0]])
            save(row, state=state, why=why, fetched_at=datetime.now(timezone.utc), next_at=None if delay is None else later(delay))
            saved.add(row.address)
        links: list[Link] = []
        more: list[Found] = []
        for key in containers[container]:
            text = notes.text(key, docs[key].get("revision", ""))
            if not text:
                continue
            for url in crawl.document_links(text, row.url):
                links.append(Link(sites.address(url)))
                more.append(Found(url, crawl.provider(url) or row.site, "document"))
            for url in crawl.text_page_links(text, row.url):
                links.append(Link(sites.address(url)))
                if (name := crawl.provider(url, page=True)):
                    more.append(Found(url, name, "page"))
        set_links(row.address, links)
        add(more, by=row)
    return saved


def sweep() -> dict[str, int]:
    """The daily housekeeping, in this order: the rows of sites that left the catalog go; an address nothing live links is noted
    `unlinked_since` (and one linked again is not); a page unlinked for UNLINKED_GRACE is gone (kept out of the search); the
    unpinned rows that are tried or gone and linked by nothing are dropped; so are the documents of that kind never read; and the
    notes and texts of documents that are no document any more (an old revision of an archive's member, a document that left)."""
    counts: dict[str, int] = {}
    sites.reload_catalog()
    linked = "EXISTS (SELECT 1 FROM crawl_links l JOIN crawl_urls s ON s.address = l.src WHERE l.dst = u.address AND s.state IN ('ok', 'missing'))"
    with pg.connection() as conn:
        if sites.SITES:
            counts["rows of sites that left"] = conn.execute("DELETE FROM crawl_urls WHERE site <> ALL(%s)", (list(sites.SITES),)).rowcount
        conn.execute(f"UPDATE crawl_urls u SET unlinked_since = coalesce(unlinked_since, current_date) WHERE NOT pinned AND NOT {linked}")
        conn.execute(f"UPDATE crawl_urls u SET unlinked_since = NULL WHERE unlinked_since IS NOT NULL AND {linked}")
        counts["pages unlinked"] = conn.execute(
            "UPDATE crawl_urls SET state = 'gone', why = 'no link leads to it', text = NULL WHERE kind = 'page' AND state IN ('ok', 'missing') AND unlinked_since <= %s",
            (date.today() - UNLINKED_GRACE,)).rowcount
        counts["rows dropped"] = conn.execute(f"DELETE FROM crawl_urls u WHERE NOT pinned AND state IN ('tried', 'gone') AND NOT {linked}").rowcount
        counts["documents never read dropped"] = conn.execute(
            """DELETE FROM crawl_urls u WHERE kind = 'document' AND NOT pinned AND unlinked_since IS NOT NULL
               AND NOT EXISTS (SELECT 1 FROM document_files f WHERE f.key = u.doc_key AND f.text IS NOT NULL)
               AND NOT EXISTS (SELECT 1 FROM archives r WHERE r.key = u.doc_key)""").rowcount
    counts["notes dropped"] = notes.delete_except({(k, d.get("revision", "")) for k, d in regulations.all_docs().items()})
    return counts


def site_counts(name: str) -> tuple[int, int, list[str], str | None]:
    """(pages read, documents read, why each address that gave no page gave none, the title of the start page) of a site."""
    with pg.connection() as conn:
        pages = pg.scalar(conn, "SELECT count(*) FROM crawl_urls WHERE site = %s AND kind = 'page' AND state = 'ok' AND text IS NOT NULL", (name,))
        docs = pg.scalar(conn, "SELECT count(*) FROM crawl_urls WHERE site = %s AND kind = 'document' AND state = 'ok'", (name,))
        whys = pg.column(conn, "SELECT why FROM crawl_urls WHERE site = %s AND state = 'tried' AND why IS NOT NULL", (name,))
        title = pg.scalar(conn, "SELECT title FROM crawl_urls WHERE site = %s AND slug = 'home' AND state = 'ok'", (name,))
    return pages, docs, whys, title


def status() -> None:
    """The addresses of every site by kind and state, and how many are due."""
    sites.reload_catalog()
    with pg.connection() as conn:
        rows = conn.execute("SELECT site, kind, state, count(*) AS n FROM crawl_urls GROUP BY site, kind, state").fetchall()
        due = pg.scalar(conn, "SELECT count(*) FROM crawl_urls WHERE next_at <= now()")
        waiting = pg.scalar(conn, "SELECT count(*) FROM crawl_urls WHERE priority = %s AND next_at IS NOT NULL", (REQUEST,))
    by_site: dict[str, Counter] = {}
    for r in rows:
        by_site.setdefault(r["site"], Counter())[r["kind"], r["state"]] += r["n"]
    for name in sorted(by_site):
        counts = by_site[name]
        base = sites.SITES[name].base if name in sites.SITES else "not in the catalog"
        pages = {state: n for (kind, state), n in counts.items() if kind == "page"}
        documents = {state: n for (kind, state), n in counts.items() if kind == "document"}
        print(f"{name} ({base}): pages {dict(sorted(pages.items()))}; documents {dict(sorted(documents.items()))}")
    print(f"{due} addresses are due, {waiting} of them asked for")


def _host_of(link: str, ours: set[str]) -> str | None:
    try:
        host = (urlsplit(link).hostname or "").lower().rstrip(".")
    except ValueError:
        return None
    if not host or any(host == b or host.endswith("." + b) for b in sites.BLOCKED) or host in ours:
        return None
    return host


def unvisited(names: list[str] | None = None, summary: bool = False, only: str | None = None) -> None:
    """Print the addresses no run has gone to: those of the sites of the catalog still `new` (pages, and files), and the links to
    hosts the catalog does not have. `only`: 'known' or 'unknown' prints one of the two (the other is not searched)."""
    sites.reload_catalog()
    selected = [n for n in (names or list(sites.SITES)) if n in sites.SITES]
    blocks: list[tuple[str, dict[str, set[str]], str]] = []
    with pg.connection() as conn:
        if only != "unknown":
            for title, kinds in (("Known sites, pages", ("page", "listing")), ("Known sites, files", ("document",))):
                groups: dict[str, set[str]] = {}
                for r in conn.execute("SELECT site, url FROM crawl_urls WHERE state = 'new' AND kind = ANY(%s) AND site = ANY(%s)", (list(kinds), selected)).fetchall():
                    groups.setdefault(r["site"], set()).add(r["url"])
                blocks.append((title, groups, "sites"))
        if only != "known":
            ours = {host for site in sites.SITES.values() for host in crawl._site_hosts(site)}
            found: dict[str, set[str]] = {}
            judged: dict[str, str | None] = {}
            for r in conn.execute(
                    """SELECT DISTINCT l.dst FROM crawl_links l JOIN crawl_urls s ON s.address = l.src
                       WHERE s.site = ANY(%s) AND NOT EXISTS (SELECT 1 FROM crawl_urls u WHERE u.address = l.dst)""", (selected,)).fetchall():
                if r["dst"] not in judged:
                    judged[r["dst"]] = _host_of(r["dst"], ours)
                if host := judged[r["dst"]]:
                    found.setdefault(host, set()).add(r["dst"])
            blocks.append(("Unknown hosts", found, "hosts"))
    for title, groups, kind in blocks:
        print(f"{title}: {sum(map(len, groups.values()))} addresses in {len(groups)} {kind}")
        for group, urls in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
            print(f"  {group}: {len(urls)}")
            if not summary:
                for url in sorted(urls):
                    print(f"    {url}")


def ensure_imported() -> None:
    """The old store (the table source_files) is imported into the tables of today once, and dropped (legacy.py)."""
    with pg.connection() as conn:
        old = pg.scalar(conn, "SELECT to_regclass('public.source_files')")
    if old is not None:
        from catix.docs import legacy

        print(f"source_files imported: {legacy.import_all()}", flush=True)
