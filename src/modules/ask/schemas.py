from beanie import PydanticObjectId

from src.custom_pydantic import CustomModel
from src.modules.search.schemas import SearchResponse


class AskResponses(CustomModel):
    query: str
    answer: str
    ask_query_id: PydanticObjectId | None = None
    "Assigned ask query index"
    search_responses: list[SearchResponse]
    "Responses to the search query."
