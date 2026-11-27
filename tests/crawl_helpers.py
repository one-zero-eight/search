"""Rows of the crawl (frontier.py) for the tests of sites.py and crawl.py: written to the temporary tables of docs_db, read by the
loop a run makes (crawl), and the fake sites (Web) the pages are read from."""

import hashlib
from datetime import datetime, timedelta, timezone

import httpx

from catix.db import pg
from catix.docs import frontier
from catix.docs.sources import sites

LATER = timedelta(days=7)
WORDS = " ".join(f"слово{chr(1072 + i % 26)}{chr(1072 + i // 26)}ы" for i in range(40))


def put(url: str, site: str, *, kind: str = "page", **columns) -> frontier.Row:
    """A row of the frontier as the crawl leaves it (new, due now) unless the columns say otherwise; the row."""
    if kind == "document":
        columns.setdefault("doc_key", sites.doc_key(site, url))
    values = {"address": sites.address(url), "url": url, "site": site, "kind": kind, "every": LATER, "next_at": datetime.now(timezone.utc),
              "priority": frontier.NEW, **columns}
    with pg.connection() as conn:
        conn.execute(f"INSERT INTO crawl_urls ({', '.join(values)}) VALUES ({', '.join(['%s'] * len(values))})",
                     [frontier.Jsonb(v) if isinstance(v, dict) else v for v in values.values()])
    return row_of(url)


def row_of(url: str) -> frontier.Row | None:
    with pg.connection() as conn:
        found = conn.execute(f"SELECT {frontier._LIST} FROM crawl_urls WHERE address = %s", (sites.address(url),)).fetchone()
    return frontier._row(found) if found else None


def rows(site: str | None = None, kind: str | None = None) -> dict[str, frontier.Row]:
    """The rows (of a site, of a kind) by address."""
    with pg.connection() as conn:
        found = conn.execute(f"SELECT {frontier._LIST} FROM crawl_urls WHERE (%s::text IS NULL OR site = %s) AND (%s::text IS NULL OR kind = %s) ORDER BY address",
                             (site, site, kind, kind)).fetchall()
    return {r["address"]: frontier._row(r) for r in found}


def by_slug(site: str) -> dict[str, frontier.Row]:
    """The pages of a site with a slug, by slug."""
    return {r.slug: r for r in rows(site, "page").values() if r.slug}


def page(url: str, site: str, slug: str, text: str, *, title: str | None = None, **columns) -> frontier.Row:
    """A page of the search as a read left it: ok, its text and the hash of its words, read lately and not due for a week."""
    when = datetime(2026, 10, 30, tzinfo=timezone.utc)
    values = {"state": "ok", "slug": slug, "title": title or slug.title(), "text": text, "sha256": hashlib.sha256(sites.plain(text).encode()).hexdigest(),
              "fetched_at": when, "read_at": when, "next_at": datetime.now(timezone.utc) + LATER, "priority": frontier.RECHECK, **columns}
    return put(url, site, **values)


def document(url: str, site: str, anchor: str = "", *, context: str = "", linked_by: str | None = None, **columns) -> frontier.Row:
    """A document of the sites and the link of the live page of `linked_by` (the site; its start page is made when it is not a row) that says `anchor`."""
    row = put(url, site, kind="document", ext=sites.canonical(url).rsplit(".", 1)[-1].lower(), **columns)
    if linked_by:
        start = sites.SITES[linked_by].base
        source = row_of(start) or page(start, linked_by, "home", f"{WORDS} start of {linked_by}", pinned=True)
        frontier.set_links(source.address, [frontier.Link(row.address, anchor, context)])
    return row


def due(names: tuple[str, ...] | None = None) -> frontier.Row | None:
    """The row that is due next (frontier.next_due) among the rows of these sites."""
    with pg.connection() as conn:
        found = conn.execute(
            f"SELECT {frontier._LIST} FROM crawl_urls WHERE next_at <= now() AND kind <> 'document' AND (%s::text[] IS NULL OR site = ANY(%s)) ORDER BY priority, next_at LIMIT 1",
            (list(names) if names else None, list(names) if names else None)).fetchone()
    return frontier._row(found) if found else None


def read(client, row: frontier.Row) -> bool:
    return sites.read_listing(client, row) if row.kind == "listing" else sites.read_page(client, row)


def crawl(client, names: tuple[str, ...] | None = None, limit: int = 200) -> int:
    """What the runner does with pages: read the row that is due next until none of these sites is due; how many were read."""
    reads = 0
    while reads < limit and (row := due(names)):
        read(client, row)
        reads += 1
    return reads


def make_due(*urls: str) -> None:
    """The rows are read again: due now, in this order."""
    with pg.connection() as conn:
        for i, url in enumerate(urls):
            conn.execute("UPDATE crawl_urls SET next_at = now() - make_interval(secs => %s), priority = %s WHERE address = %s",
                         (len(urls) - i, frontier.RECHECK, sites.address(url)))


class Web:
    """Sites of pages that link each other: {host: {path: [links]}}, and links in a form ({host: {path: [links]}}: followed,
    not in the text); what was asked, as (host, path)."""

    def __init__(self, links: dict[str, dict[str, list[str]]], forms: dict[str, dict[str, list[str]]] | None = None):
        self.links, self.forms, self.asked = links, forms or {}, []

    def get(self, url):
        host, path = httpx.URL(url).host, httpx.URL(url).path
        self.asked.append((host, path))
        if path not in self.links.get(host, {}):
            return httpx.Response(404, headers={"content-type": "text/html"}, text="", request=httpx.Request("GET", url))
        menu = " ".join(f"<a href='{link}'>{link.strip('/').rsplit('/', 1)[-1] or 'home'}</a>" for link in self.links[host][path])
        form = "".join(f"<form action='/send'><label><input type='checkbox'> <a href='{link}'>согласие</a></label><button>Отправить</button></form>"
                       for link in self.forms.get(host, {}).get(path, []))
        html = f"<html><head><title>{host}{path}</title></head><body><div>{menu}</div><h1>{path}</h1><p>{host}{path} {WORDS}</p>{form}</body></html>"
        return httpx.Response(200, headers={"content-type": "text/html"}, text=html, request=httpx.Request("GET", url))
