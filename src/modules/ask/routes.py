import asyncio

from fastapi import APIRouter, Body, HTTPException, Request

from src.api.logging_ import logger
from src.modules.ask.repository import ask_repository
from src.modules.ask.schemas import AskResponses

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
    query: str = Body(..., embed=True),
) -> AskResponses:
    try:
        result = await asyncio.wait_for(ask_repository.ask(query=query, request=request, sources=None), timeout=30)
        logger.info(f"Answer for `{query}`: {result.answer}")
    except TimeoutError:
        logger.warning("Timeout while generating chat response")
        raise HTTPException(status_code=408, detail="Chat timed out")

    return result
