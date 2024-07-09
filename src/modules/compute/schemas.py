from typing import Any, Literal

from src.custom_pydantic import CustomModel
from src.modules.minio.schemas import MoodleFileObject


class SearchTask(CustomModel):
    task_id: str
    status: Literal["pending", "completed", "failed"] = "pending"
    query: str


class SearchResult(CustomModel):
    task_id: str
    status: Literal["completed", "failed"]
    result: Any


class Corpora(CustomModel):
    moodle_files: list[MoodleFileObject]
