"""GET /search/search: the knowledge base of cAtIx (its wiki) as cards that link to the sources."""

import asyncio
import json
import logging
import re
import time
from typing import Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Query

from catix.agent import tracing
from catix.api import state
from catix.api.auth import VerifiedDep
from catix.api.schemas import (
    ALL_SOURCES,
    CampusLifeSource,
    EduwikiSource,
    HotelSource,
    InfoSources,
    PageText,
    ResidentsSource,
    SearchResponse,
    SearchResponses,
    Sources,
)
from catix.db import wiki as wiki_store

log = logging.getLogger("catix.api")
router = APIRouter(prefix="/search", tags=["Search"])

PREVIEW_CHARS = 500
HOSTS = {  # the sites of the old sources that the wiki holds
    "campuslife.innopolis.ru": (CampusLifeSource, "Campus life"),
    "hotel.innopolis.university": (HotelSource, "Hotel"),
    "sez-innopolis.ru": (ResidentsSource, "Residents"),
}


def make_source(title: str, url: str, preview: str, *, site: bool, trust: str) -> Sources:
    """A page of the wiki as a card. What the old sources do not have (the university's documents, other sites) is an
    EduWiki card whose breadcrumbs say where it comes from."""
    fields = {"display_name": title, "url": url, "preview_text": table_as_text(preview)[:PREVIEW_CHARS]}
    if site:
        host = (urlsplit(url).hostname or "").removeprefix("www.")
        card, name = HOSTS.get(host, (EduwikiSource, host or "Сайт"))
        return card(**fields, breadcrumbs=[name])
    if trust == "wiki":
        return EduwikiSource(**fields)
    return EduwikiSource(**fields, breadcrumbs=["Сводка cAtIx" if trust == "guide" else "Документы университета"])


def to_source(hit: wiki_store.WikiHit) -> Sources:
    return make_source(hit.title, hit.resource or "", hit.text, site=hit.path.startswith("/raw/sites/"), trust=hit.trust)


def to_responses(hits: list[wiki_store.WikiHit], sources: list[InfoSources]) -> list[SearchResponse]:
    """One card per document: the scores of its pieces go together, as the search service did for the chunks of a page."""
    cards: dict[tuple[str, str], SearchResponse] = {}
    for hit in hits:
        source = to_source(hit)
        if source.type not in sources:
            continue
        score = hit.relevance if hit.relevance is not None else None
        key = (source.display_name, source.url)
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


# A row, the blank line after it, and a heading the chunker repeated at the start of a piece (which a row cannot be under)
TABLE_ROWS = re.compile(r"^(\|.*\|)\n\n(?:#{1,6} .*\n\n)?(?=\|)", re.M)
TABLE_CELLS = re.compile(r"(?<!\\)\|")


def join_pieces(texts: list[str]) -> str:
    """The pieces of a page as one text. The wiki keeps every block apart by a blank line, the rows of a table too, and a
    table with blank lines between its rows (or a heading the chunker repeated there) is not a table in markdown: the rows
    go together again."""
    return TABLE_ROWS.sub(r"\1\n", "\n\n".join(texts))


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


@router.get("/page", responses={200: {"description": "Success"}, 404: {"description": "The knowledge base has no copy of the page"}})
async def page_by_url(_auth: VerifiedDep, url: str) -> PageText:
    """The text of a page of the knowledge base by the address of its original: for sites that cannot be shown in a frame."""
    hits = await asyncio.to_thread(wiki_store.page_of_resource, url)
    if not hits:
        raise HTTPException(status_code=404, detail="Page not found")
    return PageText(title=hits[0].title, url=url, text=join_pieces([hit.text for hit in hits]))


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
