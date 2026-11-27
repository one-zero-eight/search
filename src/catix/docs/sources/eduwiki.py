"""Source `eduwiki`: a snapshot of the eduwiki (MediaWiki) in the table eduwiki_pages, and its pages as documents.

    catix-docs eduwiki fetch [NAMESPACE ...]   # default: namespace 0 (articles); only pages whose revision changed are downloaded
    catix-docs eduwiki status                  # pages in the snapshot, redirects, pages missing on the wiki now

One row per page (eduwiki_pages) with the wikitext and the revision it came from; load_manifest maps page id -> title and
revision id. compile_all turns the snapshot into documents by code alone: wikitext -> markdown
(markup.py, tables.py), no model.
"""

import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import httpx

from catix.db import pg
from catix.docs import markup, tables
from catix.docs.store import PRODUCER, Document

API = "https://eduwiki.innopolis.university/api.php"
SITE = "https://eduwiki.innopolis.university/index.php/"
ROOT = "eduwiki"
BATCH = 50  # MediaWiki returns page content for at most 50 titles per request
MIN_TEXT = 80  # pages with less text than this (after redirects) carry nothing to compile
MIN_LETTERS = 60  # letters of prose and tables left after markup and links are removed; fewer is an embed, a stub or a title (a teacher page with just an e-mail is content)
FRESH_DAYS = {"calendar": 365, "schedule": 365}  # how long a page of this type is trusted after its last edit (default: 2 years)
TYPES = {"course": "courses", "person": "people", "calendar": "calendars", "schedule": "schedules", "page": "pages"}  # type -> folder of the documents
# Old versions and drafts live next to the current page and contradict it: not content.
SKIP_TITLE = re.compile(r"previous version|\.tex$|\.[fFsS]\d\d\b|\bold$|\bdraft|\btemplate$", re.I)
LEVEL = re.compile(r"^(bsc|msc|bste|mste|bshe|mshe|te|mte|mhe|bte|elective|phd|bc|bs|ms)\s*:\s*", re.I)
WIKI_LINK = re.compile(r"\]\(wiki:([^)]+)\)")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
HEADING = re.compile(r"^=\s*([^=<].*?)\s*=\s*$", re.M)


def _get(client: httpx.Client, **params) -> dict:
    resp = client.get(API, params={"format": "json", "formatversion": "2", **params})
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"{params.get('action')}: {data['error']}")
    return data


def list_pages(client: httpx.Client, namespace: int) -> dict[int, dict]:
    """page id -> {title, revid, redirect} for every page of the namespace."""
    pages: dict[int, dict] = {}
    cont: dict = {}
    while True:
        data = _get(client, action="query", generator="allpages", gapnamespace=namespace, gaplimit=500, prop="info", **cont)
        for p in data["query"]["pages"]:
            pages[p["pageid"]] = {"title": p["title"], "revid": p["lastrevid"], "redirect": p.get("redirect", False), "ns": namespace}
        if "continue" not in data:
            return pages
        cont = data["continue"]


def fetch_content(client: httpx.Client, ids: list[int]) -> list[dict]:
    data = _get(client, action="query", pageids="|".join(map(str, ids)), prop="revisions", rvprop="ids|timestamp|content", rvslots="main")
    out = []
    for p in data["query"]["pages"]:
        if "missing" in p:
            continue
        rev = p["revisions"][0]
        out.append({"pageid": p["pageid"], "title": p["title"], "ns": p["ns"], "revid": rev["revid"], "timestamp": rev["timestamp"], "wikitext": rev["slots"]["main"]["content"]})
    return out


def load_manifest() -> dict[str, dict]:
    """page id (a string) -> {title, revid, redirect, ns, deleted} of every page of the snapshot."""
    with pg.connection() as conn:
        rows = conn.execute("SELECT pageid, title, revid, redirect, ns, deleted FROM eduwiki_pages").fetchall()
    return {str(r["pageid"]): {"title": r["title"], "revid": r["revid"], "redirect": r["redirect"], "ns": r["ns"], "deleted": r["deleted"]} for r in rows}


def fetch(namespaces: list[int]) -> int:
    """New and changed pages of the wiki into the snapshot; the number of pages new, changed or deleted."""
    manifest = load_manifest()
    with httpx.Client(timeout=60, headers={"User-Agent": "catix-docs/0.1 (Innopolis University assistant)"}) as client:
        remote: dict[int, dict] = {}
        for ns in namespaces:
            remote |= list_pages(client, ns)
        todo = [pid for pid, p in remote.items() if manifest.get(str(pid), {}).get("revid") != p["revid"]]
        print(f"{len(remote)} pages on the wiki, {len(todo)} new or changed")
        for i in range(0, len(todo), BATCH):
            with pg.connection() as conn:
                for page in fetch_content(client, todo[i : i + BATCH]):
                    conn.execute(
                        """INSERT INTO eduwiki_pages (pageid, ns, title, revid, redirect, timestamp, wikitext, fetched_at) VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                           ON CONFLICT (pageid) DO UPDATE SET ns = excluded.ns, title = excluded.title, revid = excluded.revid, redirect = excluded.redirect,
                           timestamp = excluded.timestamp, wikitext = excluded.wikitext, fetched_at = excluded.fetched_at""",
                        (page["pageid"], page["ns"], page["title"], page["revid"], remote[page["pageid"]]["redirect"], page["timestamp"], page["wikitext"]))
            print(f"  {min(i + BATCH, len(todo))}/{len(todo)}")
        # pages deleted on the wiki stay in the snapshot but are marked, so their documents are retired
        gone = 0
        with pg.connection() as conn:
            for pid, entry in manifest.items():
                if entry["ns"] in namespaces and (deleted := int(pid) not in remote) != entry["deleted"]:
                    gone += 1
                    conn.execute("UPDATE eduwiki_pages SET deleted = %s WHERE pageid = %s", (deleted, int(pid)))
    return len(todo) + gone


def status() -> None:
    manifest = load_manifest()
    redirects = sum(e["redirect"] for e in manifest.values())
    deleted = sum(e["deleted"] for e in manifest.values())
    print(f"{len(manifest)} pages in the snapshot, {redirects} redirects, {deleted} deleted on the wiki")


def slug(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "page"


def empty_reason(text: str, tables: list[str]) -> str | None:
    """Why the page has nothing worth keeping (a stub, only an embedded document, a blank template), or None."""
    if text.count("____") >= 3:
        return "blank template"
    prose = re.sub(r"@@TABLE_\d+@@|https?://\S+|\(wiki:[^)]*\)|<[^>]+>", " ", text)
    letters = len(re.findall(r"[^\W\d_]", prose + " ".join(tables)))
    return f"only {letters} letters of content" if letters < MIN_LETTERS and "@" not in prose else None


_names: dict[str, str] = {}


def filename(page: dict) -> str:
    """File name of a page's document. Titles that differ only in case or punctuation give the same slug (the wiki has near-duplicates
    like 'MSTE: IT COURSE' and 'MSTE: It Course'): the page with the lower id keeps the plain slug, the others get '-<pageid>'."""
    if not _names:
        seen: set[str] = set()
        for pid, e in sorted(load_manifest().items(), key=lambda kv: int(kv[0])):
            if e["redirect"] or e.get("deleted"):
                continue
            name = slug(e["title"])
            _names[pid] = f"{name}-{pid}" if name in seen else name
            seen.add(name)
    return _names[str(page["pageid"])]


def type_of(title: str, wikitext: str) -> str:
    if LEVEL.match(title):
        return "course"
    if "calendar" in title.lower():
        return "calendar"
    if "schedule" in title.lower():
        return "schedule"
    if re.fullmatch(r"[A-Z][a-z]+(?:[A-Z][a-z]+){1,2}", title) and EMAIL.search(wikitext):
        return "person"
    return "page"


def title_of(page: dict) -> str:
    """The first top-level heading of the text with a letter, else the page title split at CamelCase; a page whose title has a
    level prefix ('MSTE: ...') gets it at the end, in brackets."""
    title = page["title"]
    level = LEVEL.match(title)
    name = next((m.group(1) for m in HEADING.finditer(page["wikitext"]) if re.search(r"[^\W\d_]", m.group(1))), None)
    if name is None:
        name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", title[level.end():] if level else title)
    return f"{name} ({title[:level.end()].rstrip(': ').strip()})" if level else name


def compile_all() -> list[Document]:
    """The documents of the snapshot's pages: every page that is not a redirect, deleted, an old version or empty."""
    _names.clear()  # (the manifest changes between runs of a long-lived process)
    docs = []
    with pg.connection() as conn:
        stored = conn.execute("SELECT pageid, title, revid, ns, timestamp, wikitext, fetched_at FROM eduwiki_pages "
                              "WHERE NOT redirect AND NOT deleted AND wikitext IS NOT NULL ORDER BY pageid").fetchall()
    for row in stored:
        if SKIP_TITLE.search(row["title"]) or len(row["wikitext"]) < MIN_TEXT:
            continue
        page = {**row, "timestamp": row["timestamp"].astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "fetched_at": row["fetched_at"].astimezone(timezone.utc).isoformat(timespec="seconds")}
        text, tabs = tables.extract(page["wikitext"])
        text = markup.convert(text)
        if empty_reason(text, tabs):
            continue
        for i, table in enumerate(tabs):
            text = text.replace(tables.TOKEN.format(i), table)
        text = WIKI_LINK.sub(lambda m: f"]({SITE}{quote(m.group(1).strip().replace(' ', '_'))})", text)
        typ = type_of(page["title"], page["wikitext"])
        title = title_of(page)
        url = SITE + quote(page["title"].replace(" ", "_"))
        stale = datetime.fromisoformat(page["timestamp"]) + timedelta(days=FRESH_DAYS.get(typ, 730))
        docs.append(Document(
            path=f"eduwiki/{TYPES[typ]}/{filename(page)}",
            meta={"type": typ, "title": title, "resource": url,
                  "sources": [{"resource": url, "id": str(page["revid"]), "title": page["title"], "last_modified": page["timestamp"]}],
                  "generated": {"by": f"{PRODUCER} eduwiki", "at": page["fetched_at"]},
                  "status": "draft", "stale_after": stale.isoformat(timespec="seconds")},
            body=f"# {title}\n\n{text}\n\n# Citations\n\n1. [{page['title']}]({url}), revision {page['revid']}\n"))
    return docs
