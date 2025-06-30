from src.custom_pydantic import CustomModel
from src.modules.sources_enum import InfoSources


class SearchTask(CustomModel):
    """
    Task for ML service
    """

    query: str
    sources: list[InfoSources]
    limit: int = 10


class SearchResultItem(CustomModel):
    """
    Item for SearchResult
    """

    resource: InfoSources
    mongo_id: str
    score: float
    content: str


class SearchResult(CustomModel):
    """
    List of ranked sources/files to backend
    """

    result_items: list[SearchResultItem]


class AskRequest(CustomModel):
    """
    Task for ML service: RAG-chat
    """

    query: str

    sources: list[InfoSources] | None = None
    limit: int | None = None


class ContextItem(CustomModel):
    """
    One snippet used as context for the answer
    """

    resource: InfoSources
    mongo_id: str
    score: float
    content: str


class AskResponse(CustomModel):
    """
    Response for ML service: RAG-chat
    """

    answer: str
    contexts: list[ContextItem]
