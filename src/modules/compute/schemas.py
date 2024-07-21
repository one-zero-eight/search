from typing import Literal

from src.custom_pydantic import CustomModel
from src.modules.minio.schemas import MoodleFileObject
from src.storages.mongo.moodle import MoodleEntrySchema


class SearchTask(CustomModel):
    query: str


class MoodleFileResult(CustomModel):
    course_id: int
    module_id: int
    filename: str
    score: list[float] | float | None = None


class SearchResult(CustomModel):
    status: Literal["completed", "failed"]
    result: list[MoodleFileResult] = []


class Corpora(CustomModel):
    moodle_entries: list[MoodleEntrySchema] = []
    moodle_files: list[MoodleFileObject] = []
