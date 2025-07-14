import asyncio
import time

from fastapi import APIRouter, Body, HTTPException, Request

from src.api.dependencies import VerifiedDep
from src.api.logging_ import logger
from src.modules.ask.repository import ask_repository
from src.modules.ask.schemas import AskResponses
from src.storages.mongo.statistics import AskStatistics, WrappedResponseSchema

router = APIRouter(prefix="/ask", tags=["Ask"])


@router.post(
    "/",
    responses={
        200: {"description": "Success"},
        408: {"description": "Chat timed out"},
        502: {"description": "ML service error"},
    },
)
async def ask_by_query(
    request: Request,
    _verify: VerifiedDep,
    query: str = Body(..., embed=True),
) -> AskResponses:
    start_time = time.monotonic()
    try:
        result = await asyncio.wait_for(ask_repository.ask(query=query, request=request, sources=None), timeout=30)
        logger.info(f"Answer for `{query}`: {result.answer}")
    except TimeoutError:
        logger.warning("Timeout while generating chat response")
        raise HTTPException(status_code=408, detail="Chat timed out")

    time_spent = time.monotonic() - start_time

    search_responses = [
        WrappedResponseSchema(source=response.source, score=response.score) for response in result.search_responses
    ]

    ask_statistics = AskStatistics(
        query=query, answer=result.answer, search_responses=search_responses, time_spent=time_spent
    )
    await ask_statistics.insert()

    result.ask_query_id = ask_statistics.id

    return result
