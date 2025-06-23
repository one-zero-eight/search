from fastapi import APIRouter
from starlette.requests import Request

from src.modules.chat.schemas import ChatResponse

# TODO: tie this router with backend app
router = APIRouter(prefix="/chat", tags=["Chat"])


# First, use ml search endpoint to get context info.
# Second, use ml chat endpoint, pass, at least, user query and context info there.
@router.get("/chat", responses={200: {"description": "Success"}, 408: {"description": "Search timed out"}})
async def ask_llm(
    query: str,
    response_types: list[str],
    search_category: list[str],
    search_sources: list[str],
    request: Request,
    limit: int = 3,
) -> ChatResponse: ...
