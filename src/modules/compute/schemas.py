from typing import Literal

from src.custom_pydantic import CustomModel
from src.modules.minio.schemas import MoodleFileObject


class SearchTask(CustomModel):
    task_id: str
    status: Literal["pending", "completed", "failed"] = "pending"
    query: str


class MoodleFileResult(CustomModel):
    course_id: int
    module_id: int
    filename: str
    score: list[float] | float | None = None


class SearchResult(CustomModel):
    task_id: str
    status: Literal["completed", "failed"]
    result: list[MoodleFileResult] = []


class Corpora(CustomModel):
    moodle_files: list[MoodleFileObject]
