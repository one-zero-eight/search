import time

from fastapi import APIRouter, Request, HTTPException

from src.modules.search.repository import search_repository
from src.modules.search.schemas import SearchResponses
from src.storages.mongo.statistics import WrappedResponseSchema, SearchStatistics

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/search")
async def search_by_query(query: str, request: Request, limit: int = 5) -> SearchResponses:
    start_time = time.monotonic()
    responses = await search_repository.by_meta(query, request=request, limit=limit)
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
async def add_user_feedback(search_query_id: str, response_index: int, feedback: str):
    valid_feedback = {"like", "dislike"}
    if feedback not in valid_feedback:
        raise HTTPException(status_code=400, detail="Invalid feedback value, must be 'like' or 'dislike'")

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
