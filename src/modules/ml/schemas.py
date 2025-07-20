from src.custom_pydantic import CustomModel
from src.modules.sources_enum import InfoSources


class MLSearchTask(CustomModel):
    """
    Task for ML service
    """

    query: str
    sources: list[InfoSources]
    limit: int = 10


class MLSearchResultItem(CustomModel):
    """
    Item for SearchResult
    """

    resource: InfoSources
    mongo_id: str
    score: float
    content: str


class MLSearchResult(CustomModel):
    """
    List of ranked sources/files to backend
    """

    result_items: list[MLSearchResultItem]


class MLAskRequest(CustomModel):
    """
    Task for ML service: RAG-chat
    """

    query: str
    sources: list[InfoSources] | None = None
    user_token: str | None = None
    history: list
    "History of previous messages in the session, without current query, without system message"


class MLContextItem(CustomModel):
    """
    One snippet used as context for the answer
    """

    resource: InfoSources
    mongo_id: str
    score: float
    content: str


class MLAskResponse(CustomModel):
    """
    Response for ML service: RAG-chat
    """

    answer: str
    search_result: MLSearchResult
    messages: list[dict] | None = None
    updated_history: list


class MLActRequest(CustomModel):
    """
    Task for ML service: RAG-act
    """

    query: str
    user_token: str | None = None


class MLActResponse(CustomModel):
    """
    Task for ML service: RAG-act
    """

    answer: str
    tool_calls: list | None
    messages: list
