from fastapi import APIRouter, Request

from src.modules.search.repository import search_repository

from src.modules.search.schemas import SearchResponses

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/by-meta")
async def search_by_meta(query: str, request: Request, limit: int = 5) -> SearchResponses:
    responses = await search_repository.by_meta(query, request=request, limit=limit)

    return responses
