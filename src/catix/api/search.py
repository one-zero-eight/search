"""GET /search/search: the knowledge base of cAtIx (its wiki) as cards that link to the sources."""

import asyncio
import logging
import time
from typing import Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Query

from catix.api import state
from catix.api.auth import VerifiedDep
from catix.api.schemas import (
    ALL_SOURCES,
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
    fields = {"display_name": title, "url": url, "preview_text": preview[:PREVIEW_CHARS]}
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
    _auth: VerifiedDep,
    query: str,
    sources: list[InfoSources] = Query(default=[]),
    response_types: list[Literal["pdf", "link_to_source"]] = Query(...),  # Currently ignored
    limit: int = 10,
) -> SearchResponses:
    started = time.monotonic()
    responses = await find(query, sources, limit)
    log.info("search for `%s` (%d ms)", query, round((time.monotonic() - started) * 1000))
    return SearchResponses(searched_for=query, responses=responses, search_query_id=state.remember_search(len(responses)))


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
