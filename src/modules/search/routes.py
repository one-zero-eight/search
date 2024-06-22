from fastapi import APIRouter, Request

from src.api.dependencies import VerifiedDep
from src.modules.search.repository import search_repository

from src.modules.search.schemas import SearchResponses

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/by-meta")
async def search_by_meta(_: VerifiedDep, query: str, request: Request) -> SearchResponses:
    responses = await search_repository.by_meta(query, request=request)

    return responses
