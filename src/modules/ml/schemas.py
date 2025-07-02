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
