"""The Moodle routes of the search service that cAtIx has nothing behind (a crawler filled its courses and files in
MongoDB and MinIO). They keep their paths and models, so clients and the crawler do not break.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from catix.api.auth import VerifiedDep
from catix.api.schemas import Sources

moodle = APIRouter(prefix="/moodle", tags=["Moodle"])

NO_MOODLE = "cAtIx does not index Moodle"


class MoodleCourse(BaseModel):
    course_id: int
    course_fullname: str | None = None


@moodle.get("/courses/grouped-by-semester")
async def get_courses_grouped_by_semester() -> dict[str, list[str]]:
    return {}


@moodle.get("/courses/by-course-fullname/content")
async def get_course_names_grouped(
    course_fullname: str = Query(examples=["[S25] Mathematical Analysis II / Математический анализ II"]),
) -> list[Sources]:
    return []


@moodle.get("/preview", responses={307: {"description": "Redirect to the file"}, 404: {"description": "File not found"}})
async def preview_moodle(course_id: int, module_id: int, filename: str):
    raise HTTPException(status_code=404, detail="File not found")


@moodle.get("/files", response_model=list[dict[str, Any]])
async def get_moodle_files(_auth: VerifiedDep) -> list[dict[str, Any]]:
    return []


@moodle.get("/courses")
async def courses(_auth: VerifiedDep) -> list[MoodleCourse]:
    return []


@moodle.post("/batch-courses")
async def batch_upsert_courses(_auth: VerifiedDep, data: dict[str, Any]) -> None:
    """Accepted and dropped."""


@moodle.get("/courses-content")
async def courses_content(_auth: VerifiedDep) -> list[dict[str, Any]]:
    return []


@moodle.post("/set-course-content")
async def course_content(_auth: VerifiedDep, bulk: list[dict[str, Any]]) -> None:
    """Accepted and dropped."""


@moodle.post("/need-to-upload-contents")
async def need_to_upload_contents(_auth: VerifiedDep, contents_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return []  # Nothing needs uploading: the files are not kept.


@moodle.post("/content-uploaded")
async def content_uploaded(_auth: VerifiedDep, data: dict[str, Any]) -> None:
    """Accepted and dropped."""
