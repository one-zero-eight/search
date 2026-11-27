"""The import of the old store: the table source_files (a file system in Postgres: path -> JSON or text) into the tables of today,
once, and then source_files is dropped (frontier.ensure_imported, called before every command that reads the sources).

Nothing is downloaded or OCR'd again: the notes and texts of the documents, the archives' manifests, the course programmes, the
eduwiki's pages, the pages of the sites with their text and the documents they link come over as they are. What the old layout kept in
path conventions ('{root}/{key}.json' + '.txt' + '.archive.json' + '.members/<id>/<sha>/...') are rows with columns now.

`pg.connection()` hands out a separate pooled connection per call (db/pg.py), so the import is not one transaction. Atomicity comes
from the order: the tables of today are emptied first, source_files is dropped last. An import that fails or is stopped leaves
source_files whole, and the next one starts again from empty tables. The data of `past-papers/` (a dead source) is not imported.
"""

import random
import re
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from urllib.parse import urlsplit

from psycopg.types.json import Jsonb

from catix.db import pg
from catix.docs import frontier, notes
from catix.docs.sources import archive_documents, crawl, regulations, rpd, sites

TABLES = ("site_catalog", "blocked_hosts", "crawl_urls", "crawl_links", "document_files", "archives", "course_programmes", "rpd_archives", "eduwiki_pages")
NOT_FILES = ("catalog/", "eduwiki/", "rpd/", "past-papers/")  # (the paths of other kinds of data)
FILE = re.compile(r"^(?P<root>.+)/(?P<key>[^/]+)\.(?P<ext>json|txt)$")
REVISION = re.compile(r"\.(?:members/[^/]+|documents)/(?P<sha>[0-9a-f]{64})$")
ARCHIVE_FILE = re.compile(r"^(?P<root>.+)/(?P<key>[^/]+)\.archive\.json$")
OBSOLETE = ("new-pages", "files", "sites", "papers")  # the keys of `asked` of the sources that are jobs and crawl no more


def _scan(where: str, params: tuple = (), batch: int = 200) -> Iterator[dict]:
    """The rows (path, data, text) of source_files that `where` selects, by path, a few at a time."""
    last = ""
    while True:
        with pg.connection() as conn:
            rows = conn.execute(f"SELECT path, data, text FROM source_files WHERE ({where}) AND path > %s ORDER BY path LIMIT %s", (*params, last, batch)).fetchall()
        if not rows:
            return
        yield from rows
        last = rows[-1]["path"]


def _one(path: str) -> dict:
    with pg.connection() as conn:
        row = conn.execute("SELECT data FROM source_files WHERE path = %s", (path,)).fetchone()
    return row["data"] if row and row["data"] else {}


def _time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _spread(delta: timedelta | None) -> datetime | None:
    """When a row is read next: somewhere within its interval, so that the rows read together in the old store do not all come due at once."""
    return None if delta is None else datetime.now(timezone.utc) + delta * random.random()


def catalog() -> int:
    raw = _one("catalog/sites.json")
    if not raw:
        raise RuntimeError("source_files has no catalog/sites.json: the catalog of sites cannot be imported")
    sites.save_catalog(raw)  # (every record is checked: a Site, and the CHECKs of the table)
    sites.reload_catalog()
    return len(raw["sites"])


def wiki() -> int:
    manifest = _one("eduwiki/manifest.json")
    pages = {int(PurePosixPath(r["path"]).stem): r["data"] for r in _scan("starts_with(path, 'eduwiki/pages/')")}
    with pg.connection() as conn:
        for pid, entry in manifest.items():
            page = pages.get(int(pid)) or {}
            conn.execute(
                """INSERT INTO eduwiki_pages (pageid, ns, title, revid, redirect, deleted, timestamp, wikitext, fetched_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (int(pid), entry["ns"], entry["title"], entry["revid"], entry["redirect"], entry.get("deleted", False), _time(page.get("timestamp")),
                 page.get("wikitext"), _time(page.get("fetched_at"))))
    return len(manifest)


def programmes() -> int:
    index = _one("rpd/index.json")
    texts = {PurePosixPath(r["path"]).stem: r["text"] for r in _scan("starts_with(path, 'rpd/') AND path LIKE '%%.txt'", batch=100)}
    for key, entry in index.items():
        rpd.put(key, entry, texts.get(key))
    for url, value in _one("rpd/archives.json").items():
        rpd.put_remote(url, value)
    return len(index)


def documents_of(path: str) -> tuple[str, str, str] | None:
    """(key, revision, ext) of the file a path names, None for a path that is no note or text of a document."""
    if path.startswith(NOT_FILES) or not (m := FILE.match(path)):
        return None
    key, root = m["key"], m["root"]
    if key in ("index", "linked") or key.endswith((".archive", ".links")):
        return None
    return key, (r["sha"] if (r := REVISION.search(root)) else ""), m["ext"]


def files() -> tuple[int, int]:
    """The notes and texts of the documents; the manifests of the archives. (notes, archives)."""
    n = a = 0
    for row in _scan("path ~ '^(regulations|sites/[^/]+/docs)/'"):
        path = row["path"]
        if m := ARCHIVE_FILE.match(path):
            data = {k: v for k, v in row["data"].items() if k != "source"}  # (`source`: where the manifest's original was kept; nothing is kept)
            archive_documents.save(m["key"], data)
            a += 1
        elif found := documents_of(path):
            key, revision, ext = found
            if ext == "json":
                try:
                    notes.put_note(key, revision, row["data"])
                except ValueError as e:
                    raise RuntimeError(f"{path}: the note has {e} that is no column of document_files: add it to the table and to notes.COLUMNS") from None
            else:
                notes.put_text(key, revision, row["text"])
            n += 1
    return n, a


def _page_state(page: dict) -> str:
    return "gone" if page.get("gone") else "missing" if page.get("missing") else "ok"


def pages(name: str, site: sites.Site, index: dict) -> tuple[int, int]:
    """The pages and the tried addresses of a site's index into crawl_urls; (pages, tried). The pages not gone come first: of two
    under one address that one is kept."""
    start = frontier.starts(site)
    texts = {PurePosixPath(r["path"]).stem: r["text"] for r in _scan("starts_with(path, %s) AND path LIKE '%%.md'", (f"{sites.ROOT}/{name}/",), batch=100)}
    n = 0
    now = datetime.now(timezone.utc)
    with pg.connection() as conn:
        for slug, page in sorted(index.get("pages", {}).items(), key=lambda item: bool(item[1].get("gone"))):
            address, state = sites.address(page["url"]), _page_state(page)
            every = frontier.feed_every(site) if address in start else frontier.PAGE_EVERY
            short = (page.get("short") or {}).get("words")
            n += conn.execute(
                """INSERT INTO crawl_urls (address, url, site, kind, pinned, every, next_at, priority, state, why, slug, title, sha256, validators, short_words,
                                           text, audience, fetched_at, read_at) VALUES (%s, %s, %s, 'page', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT DO NOTHING""",
                (address, page["url"], name, address in start, every, _spread(every), frontier.RECHECK, state, (page.get("missing") or {}).get("why"), slug,
                 page.get("title"), page.get("sha256"), Jsonb(page.get("validators") or {}), short, None if state == "gone" else texts.get(slug),
                 page.get("audience"), _time(page.get("fetched_at")), _time(page.get("read_at")))).rowcount
        tried = 0
        for address, mark in (index.get("tried") or {}).items():
            tried += conn.execute(
                """INSERT INTO crawl_urls (address, url, site, kind, every, next_at, priority, state, why) VALUES (%s, %s, %s, 'page', %s, %s, %s, 'tried', %s)
                   ON CONFLICT DO NOTHING""",
                (address, address, name, frontier.PAGE_EVERY, (_time(mark.get("run")) or now) + sites.RETRY, frontier.RECHECK, mark.get("why"))).rowcount
    return n, tried


def page_links(name: str, index: dict) -> int:
    """The links of the pages kept: the markdown links of their text (the longest text of a link repeated), the contexts the index
    named for the documents they link. A document the index lists that no page text links (its page was cut short, or rewritten
    since) is linked from the site's start page with the anchor and context the index kept: the next read of the pages says."""
    site = sites.SITES[name]
    contexts = {sites.address(url): context for url, context in (index.get("contexts") or {}).items()}
    start = next(iter(frontier.starts(site)), "")
    made_by: dict[str, list[frontier.Link]] = {}
    linked: set[str] = set()
    rows = frontier.live_pages(name)
    for row in rows:
        made = made_by.setdefault(row.address, [])
        for anchor, url in sites.links_of(row.text or ""):
            if urlsplit(url).scheme in ("http", "https"):
                dst = sites.address(url)
                linked.add(dst)
                made.append(frontier.Link(dst, anchor, contexts.get(dst, "")))
    if start in made_by:
        for url, anchor in (index.get("docs") or {}).items():
            if (dst := sites.address(url)) not in linked:
                made_by[start].append(frontier.Link(dst, anchor, contexts.get(dst, "")))
    links = 0
    for address, made in made_by.items():
        frontier.set_links(address, made)
        links += len(made)
    return links


def _owner(url: str, candidates: list[tuple[str, str]], texts: set[str], known: set[str]) -> tuple[str, str]:
    """(site, key) of a file several sites link (the cookie policy in the footer of 16 of them, the licence on four): the key of the copy
    already read, else of one already tried (a note, an archive's manifest), else of the site that serves the file, else of the first
    that links it. A key once read stays: its text and OCR are not made again."""
    home = crawl.provider(url)
    return min(candidates, key=lambda c: (c[1] not in texts, c[1] not in known, c[0] != home))  # (min keeps the first of equal copies)


def document_rows(indexes: dict[str, dict]) -> int:
    """The documents the sites linked (docs, and unlisted ones that were read), and those the registry of the documents' own text
    kept: one row of the frontier for each file."""
    with pg.connection() as conn:
        texts = {r["key"] for r in conn.execute("SELECT DISTINCT key FROM document_files WHERE text IS NOT NULL").fetchall()}
        archived = {r["key"] for r in conn.execute("SELECT key FROM archives").fetchall()}
        known = texts | archived | {r["key"] for r in conn.execute("SELECT key FROM document_files").fetchall()}
    readable = texts | archived
    seen = {sites.canonical(regulations.BASE + path) for _, path in regulations.DOCS.values()}  # (the first regulations are rows of the seed)
    copies: dict[str, list[tuple[str, str]]] = {}
    anchors: dict[str, tuple[str, str]] = {}  # url -> (anchor, since) of what no page links any more
    listed: set[str] = set()
    for name, index in indexes.items():
        for url, anchor in (index.get("docs") or {}).items():
            copies.setdefault(url, []).append((name, sites.doc_key(name, url)))
            listed.add(url)
            anchors.setdefault(url, (anchor, ""))
        for url, mark in (index.get("unlisted") or {}).items():
            if url in (index.get("docs") or {}) or sites.doc_key(name, url) not in readable:
                continue  # (linked again, or one never read: nothing to keep)
            copies.setdefault(url, []).append((name, sites.doc_key(name, url)))
            anchors.setdefault(url, (mark["anchor"], mark["since"]))
    for url, found in _one("regulations/linked.json").get("documents", {}).items():
        copies.setdefault(url, []).append((found["provider"], found["key"]))
        anchors.setdefault(url, (found.get("title", ""), ""))
    count = 0
    now = datetime.now(timezone.utc)
    with pg.connection() as conn:
        for url, candidates in copies.items():
            if sites.canonical(url) in seen or (site := crawl.provider(url) or candidates[0][0]) not in sites.SITES:
                continue
            _, key = _owner(url, candidates, texts, known)
            ext = (indexes.get(candidates[0][0], {}).get("archive_types") or {}).get(url) or urlsplit(url).path.rsplit(".", 1)[-1].lower()
            state, why, delay = regulations.note_state(key, {"url": url, "ext": ext, "title": "", "section": ""})
            anchor, since = anchors[url]
            count += conn.execute(
                """INSERT INTO crawl_urls (address, url, site, kind, every, next_at, priority, state, why, doc_key, ext, title, unlinked_since, fetched_at)
                   VALUES (%s, %s, %s, 'document', %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL) ON CONFLICT DO NOTHING""",
                (sites.address(url), url, site, frontier.DOCUMENT_EVERY, _spread(delay) if state != "new" else now,
                 frontier.NEW if state == "new" else frontier.RECHECK, state, why, key, ext, anchor or None, since or None)).rowcount
    return count


def import_all() -> dict[str, int]:
    """source_files into the tables of today, then source_files is dropped; the counts of what came over."""
    with pg.connection() as conn:
        conn.execute(f"TRUNCATE {', '.join(TABLES)}")
    counts: dict[str, int] = {"sites in the catalog": catalog()}
    counts["eduwiki pages"] = wiki()
    counts["course programmes"] = programmes()
    counts["notes and texts"], counts["archives"] = files()
    indexes: dict[str, dict] = {}
    counts["pages"] = counts["tried addresses"] = counts["page links"] = 0
    for row in _scan("path ~ '^sites/[^/]+/index\\.json$'", batch=5):
        name = row["path"].split("/")[1]
        if name not in sites.SITES:
            print(f"  {name}: not in the catalog, its pages are not imported", flush=True)
            continue
        indexes[name] = row["data"]
        n, tried = pages(name, sites.SITES[name], row["data"])
        counts["pages"] += n
        counts["tried addresses"] += tried
    counts["documents"] = document_rows(indexes)
    for name, index in indexes.items():
        counts["page links"] += page_links(name, index)
    frontier.documents_read(list(regulations.all_docs()), note=False)  # (the links of the documents' own text)
    frontier.seed()
    with pg.connection() as conn:
        counts["links"] = pg.scalar(conn, "SELECT count(*) FROM crawl_links")
        conn.execute("DROP TABLE source_files")
        state = conn.execute("SELECT value FROM docs_meta WHERE key = 'runner'").fetchone()
        if state:
            import json

            data = json.loads(state["value"])
            for key in OBSOLETE:
                data.get("asked", {}).pop(key, None)
            conn.execute("UPDATE docs_meta SET value = %s WHERE key = 'runner'", (json.dumps(data, ensure_ascii=False),))
    return counts
