"""GET /search/search: the knowledge base of cAtIx (its wiki) as cards that link to the sources."""

import asyncio
import json
import logging
import re
import time
from collections.abc import Callable
from typing import Literal
from urllib.parse import quote, unquote, urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup, Comment
from fastapi import APIRouter, HTTPException, Query, Response

from catix.agent import tracing
from catix.api import state
from catix.api.auth import VerifiedDep
from catix.api.schemas import (
    ALL_SOURCES,
    ArchiveDocument,
    CampusLifeSource,
    EduwikiSource,
    HotelSource,
    InfoSources,
    ResidentsSource,
    SearchResponse,
    SearchResponses,
    Sources,
)
from catix.db import wiki as wiki_store
from catix.wiki import previews
from catix.wiki.sources import sites as site_source
from catix.wiki.sources.archives import ArchiveError

log = logging.getLogger("catix.api")
router = APIRouter(prefix="/search", tags=["Search"])

PREVIEW_CHARS = 500
HOSTS = {  # the sites of the old sources that the wiki holds
    "campuslife.innopolis.ru": (CampusLifeSource, "Campus life"),
    "hotel.innopolis.university": (HotelSource, "Hotel"),
    "sez-innopolis.ru": (ResidentsSource, "Residents"),
}


def make_source(title: str, url: str, preview: str, *, site: bool, trust: str, archive_document: dict | None = None) -> Sources:
    """A page of the wiki as a card. What the old sources do not have (the university's documents, other sites) is an
    EduWiki card whose breadcrumbs say where it comes from."""
    fields = {"display_name": title, "url": url, "preview_text": table_as_text(preview)[:PREVIEW_CHARS]}
    if site:
        host = (urlsplit(url).hostname or "").removeprefix("www.")
        card, name = HOSTS.get(host, (EduwikiSource, host or "Сайт"))
        return card(**fields, breadcrumbs=[name])
    if trust == "wiki":
        return EduwikiSource(**fields, archive_document=ArchiveDocument.model_validate(archive_document) if archive_document else None)
    return EduwikiSource(**fields, breadcrumbs=["Сводка cAtIx" if trust == "guide" else "Документы университета"],
                         archive_document=ArchiveDocument.model_validate(archive_document) if archive_document else None)


def to_source(hit: wiki_store.WikiHit) -> Sources:
    document = previews.describe(hit.path, hit.page_sha, hit.resource or "")
    return make_source(hit.title, hit.resource or "", hit.text, site=hit.path.startswith("/raw/sites/"), trust=hit.trust,
                       archive_document=document)


def to_responses(hits: list[wiki_store.WikiHit], sources: list[InfoSources]) -> list[SearchResponse]:
    """One card per document: the scores of its pieces go together, as the search service did for the chunks of a page."""
    cards: dict[tuple, SearchResponse] = {}
    for hit in hits:
        source = to_source(hit)
        if source.type not in sources:
            continue
        score = hit.relevance if hit.relevance is not None else None
        document = source.archive_document if isinstance(source, EduwikiSource) else None
        key = (source.display_name, source.url, document.page if document else None, document.revision if document else None)
        if (card := cards.get(key)) is None:
            cards[key] = SearchResponse(score=None if score is None else [score], source=source)
        elif score is not None:
            card.score = [*(card.score or []), score]
    return list(cards.values())


async def find(query: str, sources: list[InfoSources], limit: int) -> list[SearchResponse]:
    hits = await asyncio.to_thread(wiki_store.search, query, limit=limit)
    return to_responses(hits, sources or ALL_SOURCES)


@router.get("/search", responses={200: {"description": "Success"}, 408: {"description": "Search timed out"}})
async def search_by_query(
    user: VerifiedDep,
    query: str,
    sources: list[InfoSources] = Query(default=[]),
    response_types: list[Literal["pdf", "link_to_source"]] = Query(...),  # Currently ignored
    limit: int = 10,
) -> SearchResponses:
    started = time.monotonic()
    # A trace of its own in Phoenix: the query, the cards found (title and link), and the steps of the search under it.
    with tracing.question("api-search", user.innohassle_id, query, name="search", kind="RETRIEVER") as traced:
        responses = await find(query, sources, limit)
        traced.answer(json.dumps([{"title": r.source.display_name, "url": r.source.url} for r in responses], ensure_ascii=False))
    log.info("search for `%s` (%d ms)", query, round((time.monotonic() - started) * 1000))
    return SearchResponses(searched_for=query, responses=responses, search_query_id=state.remember_search(len(responses)))


TABLE_CELLS = re.compile(r"(?<!\\)\|")


def table_as_text(text: str) -> str:
    """A table cut out of a page (no header, rows cut short) cannot be drawn: its rows are lines of cells."""
    lines = []
    for line in text.split("\n"):
        if line.startswith("|"):
            cells = [cell.strip() for cell in TABLE_CELLS.split(line.strip().strip("|"))]
            if all(set(cell) <= set("-: ") for cell in cells):
                continue  # the line under the header
            line = " · ".join(cells)
        lines.append(line)
    return "\n".join(lines)


DOWNLOAD_MAX_BYTES = 25_000_000  # the wiki reads no bigger document either (wiki/sources/regulations.MAX_BYTES)
DOWNLOAD_TIMEOUT = 60  # seconds for the whole download
DOWNLOAD_REDIRECTS = 5
DOWNLOAD_HEADERS = {"User-Agent": "catix-api/0.1 (Innopolis University assistant; preview)"}


def site_http() -> httpx.AsyncClient:
    return httpx.AsyncClient(headers=DOWNLOAD_HEADERS, timeout=DOWNLOAD_TIMEOUT, follow_redirects=False)


def same_site(url: str, original: str) -> bool:
    """A redirect of a document may lead to another host of the same site (www., files.), not anywhere else."""
    parts = urlsplit(url)
    host, base = (parts.hostname or "").lower(), ".".join((original or "").lower().split(".")[-2:])
    return (parts.scheme in {"http", "https"} and parts.port is None and not parts.username and not parts.password
            and "." in base and (host == base or host.endswith("." + base)))


def same_host(url: str, original: str) -> bool:
    """A redirect of a page stays on its host (www. aside): another host of the site is a login (SSO), not the page."""
    parts = urlsplit(url)
    return (parts.scheme in {"http", "https"} and parts.port is None and not parts.username and not parts.password
            and (parts.hostname or "").lower().removeprefix("www.") == original.lower().removeprefix("www."))


async def download(url: str, stays: Callable[[str, str], bool]) -> httpx.Response:
    """The answer at `url` read whole, redirects followed while `stays(next url, original host)`; 502 if the site gives no 200."""
    original = urlsplit(url).hostname or ""
    async with asyncio.timeout(DOWNLOAD_TIMEOUT), site_http() as http:
        for _ in range(DOWNLOAD_REDIRECTS + 1):
            if not stays(url, original):
                raise HTTPException(status_code=502, detail="The address moved off its site")
            async with http.stream("GET", url) as response:
                if response.is_redirect:
                    url = urljoin(url, response.headers.get("location", ""))
                    continue
                if response.status_code != 200:
                    raise HTTPException(status_code=502, detail=f"The site answered {response.status_code}")
                declared = response.headers.get("content-length", "")
                if declared.isdigit() and int(declared) > DOWNLOAD_MAX_BYTES:
                    raise HTTPException(status_code=502, detail="The answer is too big")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body += chunk
                    if len(body) > DOWNLOAD_MAX_BYTES:
                        raise HTTPException(status_code=502, detail="The answer is too big")
                return httpx.Response(200, content=bytes(body), headers={"content-type": response.headers.get("content-type", "")},
                                      request=httpx.Request("GET", url))
    raise HTTPException(status_code=502, detail="Too many redirects")


async def download_pdf(url: str) -> bytes:
    """The PDF at `url`, redirects followed on its own site; 502 if the site gives no PDF (a login page, an error)."""
    body = (await download(url, same_site)).content
    if b"%PDF-" not in body[:1024]:
        raise HTTPException(status_code=502, detail="The site gave no PDF")
    return body


@router.get("/pdf", response_class=Response, responses={
    200: {"description": "The PDF", "content": {"application/pdf": {}}},
    404: {"description": "The knowledge base has no page of this document"},
    502: {"description": "The site gave no PDF"},
    504: {"description": "The site did not answer in time"},
})
async def pdf_by_url(_auth: VerifiedDep, url: str) -> Response:
    """The original PDF of a page of the knowledge base, for a preview in a frame: the university's sites forbid showing
    their files in a frame of another site (X-Frame-Options: SAMEORIGIN), this answer does not. Only documents the
    knowledge base has a page of: not a proxy to anywhere."""
    if not await asyncio.to_thread(wiki_store.has_resource, url):
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        body = await download_pdf(url)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="The site did not answer in time") from None
    except httpx.HTTPError as error:
        log.warning("pdf %s: %r", url, error)
        raise HTTPException(status_code=502, detail="The site did not answer") from None
    name = unquote(urlsplit(url).path.rsplit("/", 1)[-1]) or "document.pdf"
    return Response(body, media_type="application/pdf", headers={
        "Content-Disposition": f"inline; filename*=UTF-8''{quote(name)}",
        "Cache-Control": "private, max-age=3600",
    })


PAGE_CSP = "script-src 'none'; object-src 'none'; frame-src 'none'; form-action 'none'"
UNSHOWN = ["script", "noscript", "iframe", "frame", "frameset", "object", "embed", "base", "portal"]
LAZY = ("data-src", "data-original", "data-lazy-src")  # the address of a picture that the page's scripts would load
PASSWORD = re.compile(r"""<input[^>]+type=["']?password""", re.I)


def framed_page(page: httpx.Response) -> str:
    """The page as a sandboxed frame on the site shows it: no scripts, frames or handlers, its addresses resolved against
    the original (<base>), its links opened in a new tab. 502 for what is not the page: not HTML, a bot check, a login,
    an app's empty shell (site_source.convert_page: its <noscript> asks for JavaScript or it has next to no words)."""
    if "text/html" not in page.headers.get("content-type", ""):
        raise HTTPException(status_code=502, detail="The site gave no page")
    title, _, _, script = site_source.convert_page(page.text, str(page.url))
    if site_source.WALL_TITLE.search(title):
        raise HTTPException(status_code=502, detail="A bot check answered")
    if PASSWORD.search(page.text):
        raise HTTPException(status_code=502, detail="The page asks to sign in")
    if script:
        raise HTTPException(status_code=502, detail="The page needs its scripts")
    soup = BeautifulSoup(page.content, "html.parser", from_encoding=page.charset_encoding)
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for tag in soup.find_all(UNSHOWN):
        tag.decompose()
    for tag in soup.find_all("meta"):
        if tag.get("http-equiv") or tag.get("charset"):
            tag.decompose()
    for tag in soup.find_all(True):
        for name in [name for name in tag.attrs if name.lower().startswith("on")]:
            del tag[name]
        for name in ("href", "src", "action", "formaction", "xlink:href"):
            if str(tag.get(name, "")).strip().lower().startswith("javascript:"):
                del tag[name]
        lazy = next((str(tag[name]) for name in LAZY if tag.get(name)), "")
        if lazy and tag.name == "img":
            tag["src"] = lazy
        elif lazy and tag.get("data-original"):  # (Tilda: a block's picture is its background)
            tag["style"] = f'{tag.get("style", "")};background-image:url("{lazy.replace(chr(34), "%22")}")'
    head = soup.head
    if head is None:
        head = soup.new_tag("head")
        (soup.html or soup).insert(0, head)
    for tag in reversed([soup.new_tag("meta", attrs={"charset": "utf-8"}),
                         soup.new_tag("meta", attrs={"http-equiv": "Content-Security-Policy", "content": PAGE_CSP}),
                         soup.new_tag("base", attrs={"href": str(page.url), "target": "_blank"})]):
        head.insert(0, tag)
    return str(soup)


@router.get("/html", response_class=Response, responses={
    200: {"description": "The page without its scripts", "content": {"text/html": {}}},
    404: {"description": "The knowledge base has no copy of the page"},
    502: {"description": "The site gave no page that can be shown without its scripts"},
    504: {"description": "The site did not answer in time"},
})
async def html_by_url(_auth: VerifiedDep, url: str) -> Response:
    """The original of a page of the knowledge base, for a sandboxed frame on the site: the university's sites forbid showing
    their pages in a frame of another site (X-Frame-Options: SAMEORIGIN) and give no CORS. Only pages the knowledge base
    has a copy of: not a proxy to anywhere."""
    if not await asyncio.to_thread(wiki_store.has_resource, url):
        raise HTTPException(status_code=404, detail="Page not found")
    try:
        body = await asyncio.to_thread(framed_page, await download(url, same_host))
    except TimeoutError:
        raise HTTPException(status_code=504, detail="The site did not answer in time") from None
    except httpx.HTTPError as error:
        log.warning("html %s: %r", url, error)
        raise HTTPException(status_code=502, detail="The site did not answer") from None
    return Response(body, media_type="text/html", headers={
        "Cache-Control": "private, max-age=3600",
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "sandbox; " + PAGE_CSP,
    })


@router.get("/archive-document", response_class=Response, responses={
    200: {"description": "The cited archive member", "content": {"application/pdf": {}}},
    404: {"description": "This document revision is unavailable"},
    502: {"description": "The archive could not be downloaded or opened"},
    503: {"description": "The preview cache is unavailable"},
    504: {"description": "The archive download timed out"},
})
async def archive_document(_auth: VerifiedDep, page: str, revision: str) -> Response:
    """Download and safely unpack the source archive on demand; cache the exact verified PDF."""
    hits = await asyncio.to_thread(wiki_store.page, page)
    if not hits or hits[0].page_sha != revision:
        raise HTTPException(status_code=404, detail="This document revision is unavailable")
    try:
        found = await asyncio.to_thread(previews.read, page, revision, hits[0].resource or "")
    except (TimeoutError, httpx.TimeoutException):
        raise HTTPException(status_code=504, detail="The archive download timed out") from None
    except (httpx.HTTPError, ArchiveError):
        raise HTTPException(status_code=502, detail="The archive could not be downloaded or opened") from None
    except OSError:
        raise HTTPException(status_code=503, detail="The preview cache is unavailable") from None
    if found is None:
        raise HTTPException(status_code=404, detail="This document revision is unavailable")
    body, name = found
    return Response(body, media_type="application/pdf", headers={
        "Content-Disposition": f"inline; filename*=UTF-8''{quote(name, safe='')}",
        "Cache-Control": "private, max-age=3600",
        "X-Content-Type-Options": "nosniff",
    })


@router.post("/search/{search_query_id}/feedback")
async def add_user_feedback(
    _auth: VerifiedDep, search_query_id: str, response_index: int, feedback: Literal["like", "dislike"]
):
    marks = state.searches.get(search_query_id)
    if marks is None:
        raise HTTPException(status_code=404, detail="Search query not found")
    if response_index < 0 or response_index >= len(marks):
        raise HTTPException(status_code=400, detail="Invalid response index")
    marks[response_index] = feedback
    return {"status": "success", "search_query_id": search_query_id}
