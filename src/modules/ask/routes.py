import time

from fastapi import APIRouter, Body, Request

from src.api.dependencies import VerifiedDep
from src.api.logging_ import logger
from src.modules.ask.repository import ask_repository
from src.modules.ask.schemas import ActResponses, AskResponses
from src.storages.mongo.statistics import ActStatistics, AskStatistics

router = APIRouter(prefix="", tags=["Ask"])


@router.post(
    "/ask",
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
    result = await ask_repository.ask(query=query, request=request, sources=None)
    time_spent = time.monotonic() - start_time
    logger.info(f"Ask for `{query}` ({round(time_spent * 1000)}ms): {result.answer}")
    ask_statistics = AskStatistics(time_spent=time_spent, ask_responses=result)
    await ask_statistics.insert()
    result.ask_query_id = ask_statistics.id
    return result


@router.post(
    "/act",
    responses={
        200: {"description": "Success"},
        408: {"description": "Chat timed out"},
        502: {"description": "ML service error"},
    },
)
async def act_by_query(
    request: Request,
    _verify: VerifiedDep,
    query: str = Body(..., embed=True),
) -> ActResponses:
    start_time = time.monotonic()
    result = await ask_repository.act(query=query, request=request)
    time_spent = time.monotonic() - start_time
    logger.info(f"Act for `{query}` ({round(time_spent * 1000)}ms): {result.answer}\n{result.tool_calls}")
    act_statistics = ActStatistics(time_spent=time_spent, act_responses=result)
    await act_statistics.insert()
    result.act_query_id = act_statistics.id
    return result
