import time
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.params import Query

from src.api.dependencies import VerifiedDep
from src.api.logging_ import logger
from src.modules.search.repository import search_repository
from src.modules.search.schemas import SearchResponses
from src.modules.sources_enum import ALL_SOURCES, InfoSources
from src.storages.mongo.statistics import SearchStatistics, WrappedResponseSchema

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/search", responses={200: {"description": "Success"}, 408: {"description": "Search timed out"}})
async def search_by_query(
    request: Request,
    _verify: VerifiedDep,
    query: str,
    sources: list[InfoSources] = Query(default=[]),
    response_types: list[Literal["pdf", "link_to_source"]] = Query(...),  # Currently ignored
    limit: int = 10,
) -> SearchResponses:
    if not sources:
        sources = ALL_SOURCES
    start_time = time.monotonic()
    responses = await search_repository.search_sources(query, sources, request, limit)
    time_spent = time.monotonic() - start_time
    logger.info(f"Search for `{query}` ({round(time_spent * 1000)}ms): {responses.responses}")

    # Create a list of wrapped responses
    wrapped_responses = [
        WrappedResponseSchema(source=response.source, score=response.score) for response in responses.responses
    ]

    # Create a new search statistics document
    search_statistics = SearchStatistics(query=query, wrapped_responses=wrapped_responses, time_spent=time_spent)
    await search_statistics.insert()

    # Adding search statistics ID to the response
    responses.search_query_id = search_statistics.id

    return responses


@router.post("/search/{search_query_id}/feedback")
async def add_user_feedback(search_query_id: str, response_index: int, feedback: Literal["like", "dislike"]):
    search_statistics = await SearchStatistics.get(search_query_id)

    if not search_statistics:
        raise HTTPException(status_code=404, detail="Search query not found")

    # Validate response_index
    if response_index < 0 or response_index >= len(search_statistics.wrapped_responses):
        raise HTTPException(status_code=400, detail="Invalid response index")

    # Update the user feedback
    search_statistics.wrapped_responses[response_index].user_feedback = feedback
    await search_statistics.save()

    return {"status": "success", "search_query_id": search_query_id}
