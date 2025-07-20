from beanie import PydanticObjectId

from src.custom_pydantic import CustomModel
from src.modules.search.schemas import SearchResponse


class AskResponses(CustomModel):
    query: str
    answer: str
    chat_id: PydanticObjectId | None = None
    "Assigned chat index"
    ask_query_id: PydanticObjectId | None = None
    "Assigned ask query index"
    search_responses: list[SearchResponse]
    "Responses to the search query."
    messages: list
    "Chat history for llm (do not show on frontend)."


class ActResponses(CustomModel):
    query: str
    answer: str
    act_query_id: PydanticObjectId | None = None
    "Assigned act query index"
    tool_calls: list
    "Which tools were used."
    messages: list
    "Chat history for llm (do not show on frontend)."
