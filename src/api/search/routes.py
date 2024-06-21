from fastapi import APIRouter

from src.api.dependencies import VerifiedDep

from src.api.search.schemas import read_search_responses
from src.api.search.schemas import SearchResponses


router = APIRouter(prefix="/search", tags=["Search"])


@router.get("/search/by-filename")
async def just_search(_: VerifiedDep, query: str) -> SearchResponses:
    return SearchResponses.model_config["json_schema_extra"]["examples"][0]


@router.get("/search/all")
async def search_all(_: VerifiedDep, query: str):
    """
    Get every single entry in SearchResponseDocument
    :return: all the objects
    """
    return read_search_responses()
