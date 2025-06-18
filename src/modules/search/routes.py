import asyncio
import time
from typing import Literal

from fastapi import APIRouter, HTTPException, Request

from src.api.logging_ import logger
from src.modules.search.repository import search_repository
from src.modules.search.schemas import SearchResponses
from src.storages.mongo.statistics import SearchStatistics, WrappedResponseSchema

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/search", responses={200: {"description": "Success"}, 408: {"description": "Search timed out"}})
async def search_by_query(
    query: str,
    response_types: list[str],
    search_category: list[str],
    search_sources: list[str],
    request: Request,
    limit: int = 10,
) -> SearchResponses:
    """
    Main endpoint for "search" functionality.
    :param query: User's query/question
    :param response_types: List of types for query result. Now can be ["pdf", "link_to_source"]
    :param search_category: List of addition context to add to ML. Now can be ["university", "city", "campus"]
    :param search_sources: List of sources to use for answering query.
    :param limit: Upper bound for number of entries to return
    :return:
    """
    # TODO: rewrite this endpoint
    start_time = time.monotonic()
    try:
        responses = await asyncio.wait_for(
            search_repository.search_moodle(query, request=request, limit=limit), timeout=15
        )
    except TimeoutError:
        logger.warning("Timeout while searching for query")
        raise HTTPException(status_code=408, detail="Search timed out")

    time_spent = time.monotonic() - start_time

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
