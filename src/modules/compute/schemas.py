from typing import Any, Literal

from pydantic import BaseModel


class SearchTask(BaseModel):
    task_id: str
    status: Literal["pending", "completed", "failed"]
    query: str
    result: Any = None


class SearchResult(BaseModel):
    task_id: str
    status: Literal["completed", "failed"]
    result: Any
