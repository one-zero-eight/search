"""The user's Moodle data (catix/moodle_sync.py): the InNoHassle browser extension writes it, the website reads it.

    PUT    /users/my-moodle/overview                  courses, calendar, grades, assignments, quizzes, completion, groups
    PUT    /users/my-moodle/courses/{id}/content      the text, file names and announcements of one course
    GET    /users/my-moodle                           what the extension sent, without the course texts
    GET    /users/my-moodle/courses/{id}              the texts of one course
    DELETE /users/my-moodle                           forget everything (the extension does this when sync is turned off)

Private to the user: every route works on the rows of the token's account only.
"""

from fastapi import APIRouter, HTTPException, Response

from catix import moodle_sync
from catix.api.auth import VerifiedDep
from catix.moodle_sync import (
    MoodleCourseContentIn,
    MoodleCourseContentOut,
    MoodleOverviewIn,
    MoodleOverviewOut,
    MoodleSyncResult,
)

router = APIRouter(prefix="/users/my-moodle", tags=["Moodle"])

UNAUTHORIZED: dict[int | str, dict] = {401: {"description": "No token or a bad one"}}
NO_STORE = "private, no-store"


@router.put("/overview", responses={**UNAUTHORIZED, 409: {"description": "The Moodle account is not the user's"}})
def put_overview(user: VerifiedDep, body: MoodleOverviewIn) -> MoodleSyncResult:
    """Replace the user's Moodle courses and the per-course data. A list of `grades`, `assignments`, `quizzes`,
    `completion` or `groups` has only the courses Moodle returned, and `events` is null when it did not answer: what is
    not sent stays. `courses_without_content` are the courses whose text was never sent (PUT their content next)."""
    if body.moodle_username.strip().lower() != user.email.strip().lower():
        raise HTTPException(409, "This Moodle account is not the one of the InNoHassle account")
    return MoodleSyncResult(courses_without_content=moodle_sync.replace_overview(user.innohassle_id, body))


@router.put(
    "/courses/{course_id}/content",
    status_code=204,
    responses={**UNAUTHORIZED, 404: {"description": "The overview was not sent with this course"}},
)
def put_course_content(user: VerifiedDep, course_id: int, body: MoodleCourseContentIn) -> Response:
    """Replace the text of the sections and modules, the names and links of the files and the announcements of a course."""
    if not moodle_sync.replace_course_content(user.innohassle_id, course_id, body):
        raise HTTPException(404, "Send the overview with this course first")
    return Response(status_code=204)


@router.get("", responses={**UNAUTHORIZED, 404: {"description": "Moodle sync was never turned on"}})
def get_my_moodle(user: VerifiedDep, response: Response) -> MoodleOverviewOut:
    """The user's Moodle data: courses, calendar events and deadlines, grades, assignments, quizzes, completion and groups."""
    response.headers["Cache-Control"] = NO_STORE
    data = moodle_sync.overview(user.innohassle_id)
    if data is None:
        raise HTTPException(404, "No Moodle data: turn on Moodle sync in the InNoHassle browser extension")
    return data


@router.get("/courses/{course_id}", responses={**UNAUTHORIZED, 404: {"description": "No such course"}})
def get_course_content(user: VerifiedDep, course_id: int, response: Response) -> MoodleCourseContentOut:
    """The text of a course: sections, modules with the names and links of their files, and announcements."""
    response.headers["Cache-Control"] = NO_STORE
    data = moodle_sync.course_content(user.innohassle_id, course_id)
    if data is None:
        raise HTTPException(404, "No such course in your Moodle data")
    return data


@router.delete("", status_code=204, responses=UNAUTHORIZED)
def delete_my_moodle(user: VerifiedDep) -> Response:
    """Delete all of the user's Moodle data."""
    moodle_sync.forget(user.innohassle_id)
    return Response(status_code=204)
