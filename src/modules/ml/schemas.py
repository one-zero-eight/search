from src.custom_pydantic import CustomModel
from src.modules.sources_enum import InfoSources


class SearchTask(CustomModel):
    query: str
    sources: list[InfoSources]
    limit: int | None = 10


class SearchResultItem(CustomModel):
    resource: InfoSources
    mongo_id: str
    score: float
    snippet: str


# List of ranked sources/files to backend
class SearchResult(CustomModel):
    result_items: list[SearchResultItem]


# Currently unused
class ChatTask(CustomModel):
    query: str
    snippets: list[str] | None = None
    "Additional context to forward to LLM. See RAG."


# Currently unused
class ChatResult(CustomModel):
    status: str = "completed"
    answer: str
