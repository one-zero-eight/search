"""GET /search/search: the knowledge base of cAtIx (its wiki) and the asker's Moodle courses as cards that link to the sources."""

import asyncio
import json
import logging
import re
import time
from collections.abc import Callable
from typing import Literal
from urllib.parse import quote, unquote, urljoin, urlsplit

import httpx
from fastapi import APIRouter, HTTPException, Query, Response

from catix import groups, moodle_files
from catix.agent import tracing
from catix.api import state
from catix.api.auth import UserTokenData, VerifiedDep
from catix.api.schemas import (
    ALL_SOURCES,
    ArchiveDocument,
    CampusLifeSource,
    EduwikiSource,
    HotelSource,
    InfoSources,
    MoodleFileSource,
    MoodleUrlSource,
    PdfLocation,
    ResidentsSource,
    SearchResponse,
    SearchResponses,
    Sources,
)
from catix.db import docs as doc_store
from catix.db import rerank as joint_rerank
from catix.docs import previews
from catix.docs.sources.archives import ArchiveError
from catix.settings import settings

log = logging.getLogger("catix.api")
router = APIRouter(prefix="/search", tags=["Search"])

PREVIEW_CHARS = 500
LIMIT = 10  # cards of a search by default
HOSTS = {  # the sites of the old sources that the wiki holds
    "campuslife.innopolis.ru": (CampusLifeSource, "Campus life"),
    "hotel.innopolis.university": (HotelSource, "Hotel"),
    "sez-innopolis.ru": (ResidentsSource, "Residents"),
}


def make_source(title: str, url: str, preview: str, *, site: bool, trust: str, archive_document: dict | None = None,
                guide: bool = False) -> Sources:
    """A document as a card. What the old sources do not have (the university's documents, other sites) is an
    EduWiki card whose breadcrumbs say where it comes from."""
    fields = {"display_name": title, "url": url, "preview_text": table_as_text(preview)[:PREVIEW_CHARS]}
    if guide:
        return EduwikiSource(**fields, breadcrumbs=["catix"])
    if site:
        host = (urlsplit(url).hostname or "").removeprefix("www.")
        card, name = HOSTS.get(host, (EduwikiSource, host or "Сайт"))
        return card(**fields, breadcrumbs=[name])
    if trust == "wiki":
        return EduwikiSource(**fields, archive_document=ArchiveDocument.model_validate(archive_document) if archive_document else None)
    return EduwikiSource(**fields, breadcrumbs=["Документы университета"],
                         archive_document=ArchiveDocument.model_validate(archive_document) if archive_document else None)


def to_source(hit: doc_store.DocHit) -> Sources:
    document = previews.describe(hit)
    return make_source(hit.title, hit.resource or "", hit.text, site=hit.path.startswith("sites/"), trust=hit.trust,
                       archive_document=document, guide=hit.path.startswith("guide/"))


def to_responses(hits: list[doc_store.DocHit], sources: list[InfoSources]) -> list[SearchResponse]:
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


def moodle_responses(hits: list[moodle_files.MoodleHit]) -> list[SearchResponse]:
    """One card per file or course page: the scores of its pieces go together, as for the documents."""
    cards: dict[tuple, SearchResponse] = {}
    for hit in hits:
        breadcrumbs = ["Moodle", *hit.path.split(" › ")]
        if hit.kind == "file":
            source = MoodleFileSource(display_name=hit.title, breadcrumbs=breadcrumbs, link=hit.url,
                                      preview_location=PdfLocation(page_index=hit.page) if hit.page else None)
        else:
            source = MoodleUrlSource(display_name=hit.title, breadcrumbs=breadcrumbs, link=hit.url, url=hit.url)
        key = (hit.url, hit.page)
        if (card := cards.get(key)) is None:
            cards[key] = SearchResponse(score=None if hit.relevance is None else [hit.relevance], source=source)
        elif hit.relevance is not None:
            card.score = [*(card.score or []), hit.relevance]
    return list(cards.values())


def _moodle(user: UserTokenData, study_groups: list[str], query: str, rerank: bool) -> list[moodle_files.MoodleHit]:
    try:
        return moodle_files.search(user.innohassle_id, [query], study_groups=study_groups, limit=LIMIT, rerank=rerank)
    except Exception:  # noqa: BLE001 - the documents are still found when Moodle is not
        log.warning("moodle search failed", exc_info=True)
        return []


async def find(user: UserTokenData, query: str, sources: list[InfoSources], limit: int) -> list[SearchResponse]:
    """The cards for `query` from every source asked for (all by default): the candidates of the documents and of the asker's
    Moodle courses are scored by the reranker together, one pass, so that the best of both come first (db/rerank.py)."""
    wanted = sources or ALL_SOURCES
    want_docs = any(s != InfoSources.moodle for s in wanted)
    want_moodle = InfoSources.moodle in wanted
    together = settings.reranker_route is not None  # else each source keeps its own order and limit
    study_groups = await asyncio.to_thread(groups.website_groups, user.token.get_secret_value() if user.token else None) if want_moodle else []

    async def none() -> list:
        return []

    docs_hits, moodle_hits = await asyncio.gather(
        asyncio.to_thread(doc_store.search, query, limit=limit, rerank=not together) if want_docs else none(),
        asyncio.to_thread(_moodle, user, study_groups, query, not together) if want_moodle else none(),
    )
    if together:
        ranked = joint_rerank.mixed(
            [query],
            {"docs": [(h, doc_store.rerank_document(h)) for h in docs_hits],
             "moodle": [(h, moodle_files.rerank_document(h)) for h in moodle_hits]},
            limit,
        )
        docs_hits, moodle_hits = ranked["docs"], ranked["moodle"]
    cards = [*to_responses(docs_hits, wanted), *moodle_responses(moodle_hits)]
    if together:
        cards.sort(key=lambda card: max(card.score) if card.score else float("-inf"), reverse=True)
    return cards


@router.get("/search", responses={200: {"description": "Success"}, 408: {"description": "Search timed out"}})
async def search_by_query(
    user: VerifiedDep,
    query: str,
    sources: list[InfoSources] = Query(default=[]),
    response_types: list[Literal["pdf", "link_to_source"]] = Query(...),  # Currently ignored
    limit: int = LIMIT,
) -> SearchResponses:
    return await searched(user, query, sources, limit)


async def searched(user: UserTokenData, query: str, sources: list[InfoSources], limit: int = LIMIT) -> SearchResponses:
    """The cards found for `query`, with a trace of its own in Phoenix (the query, the cards' titles and links, the steps of the search)."""
    started = time.monotonic()
    # A trace of its own in Phoenix: the query, the cards found (title and link), and the steps of the search under it.
    with tracing.question("api-search", user.innohassle_id, query, name="search", kind="RETRIEVER") as traced:
        responses = await find(user, query, sources, limit)
        traced.answer(json.dumps([{"title": r.source.display_name, "url": getattr(r.source, "url", None) or r.source.link} for r in responses], ensure_ascii=False))
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


DOWNLOAD_MAX_BYTES = 25_000_000  # the documents are read no bigger either (docs/sources/regulations.MAX_BYTES)
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
    if not await asyncio.to_thread(doc_store.has_resource, url):
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


@router.get("/archive-document", response_class=Response, responses={
    200: {"description": "The cited archive member", "content": {"application/pdf": {}}},
    404: {"description": "This document revision is unavailable"},
    502: {"description": "The archive could not be downloaded or opened"},
    503: {"description": "The preview cache is unavailable"},
    504: {"description": "The archive download timed out"},
})
async def archive_document(_auth: VerifiedDep, page: str, revision: str) -> Response:
    """Download and safely unpack the source archive on demand; cache the exact verified PDF."""
    hits = await asyncio.to_thread(doc_store.page, page)
    if not hits or hits[0].page_sha != revision:
        raise HTTPException(status_code=404, detail="This document revision is unavailable")
    try:
        found = await asyncio.to_thread(previews.read, hits[0])
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
