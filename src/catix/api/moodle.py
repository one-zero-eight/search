"""The user's Moodle data (catix/moodle_sync.py): the InNoHassle browser extension writes it, the website reads it.

    PUT    /users/my-moodle/overview                  courses, calendar, grades, assignments, quizzes, completion, groups
    PUT    /users/my-moodle/courses/{id}/content      the text, files (names, links, sha256) and announcements of one course
    GET    /users/my-moodle                           what the extension sent, without the course texts
    GET    /users/my-moodle/courses/{id}              the texts of one course
    PUT    /users/my-moodle/files/{sha256}            the bytes of a listed course file (PDF, Office, text, image; up to 25 MiB)
    GET    /users/my-moodle/files/{sha256}            the original of one of the user's files
    GET    /users/my-moodle/search?q=                 pieces of the user's course files that answer the query
    DELETE /users/my-moodle                           forget everything (the extension does this when sync is turned off)

Private to the user: every route works on the rows of the token's account only.
"""

import hashlib
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Path, Query, Request, Response
from starlette.concurrency import run_in_threadpool

from catix import moodle_files, moodle_sync
from catix.api.attachments import BINARY
from catix.api.auth import VerifiedDep
from catix.moodle_sync import (
    MoodleContentResult,
    MoodleCourseContentIn,
    MoodleCourseContentOut,
    MoodleFileHitOut,
    MoodleOverviewIn,
    MoodleOverviewOut,
    MoodleSyncResult,
)

router = APIRouter(prefix="/users/my-moodle", tags=["Moodle"])

SHA256 = r"^[0-9a-f]{64}$"

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
    responses={**UNAUTHORIZED, 404: {"description": "The overview was not sent with this course"}},
)
def put_course_content(user: VerifiedDep, course_id: int, body: MoodleCourseContentIn) -> MoodleContentResult:
    """Replace the text of the sections and modules, the files (names, links and sha256) and the announcements of a course.
    `files_missing` are the listed files whose bytes the server does not have: PUT them to `/files/{sha256}`."""
    missing = moodle_sync.replace_course_content(user.innohassle_id, course_id, body)
    if missing is None:
        raise HTTPException(404, "Send the overview with this course first")
    return MoodleContentResult(files_missing=missing)


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


@router.put(
    "/files/{sha256}",
    status_code=204,
    openapi_extra={"requestBody": {"required": True, **BINARY}},
    responses={
        **UNAUTHORIZED,
        404: {"description": "No content the user sent lists this file"},
        413: {"description": "More than 25 MiB"},
        415: {"description": "Not application/octet-stream, or a file type that is not read"},
        422: {"description": "The bytes are not the file of this sha256"},
    },
)
async def put_file(request: Request, user: VerifiedDep, sha256: str = Path(pattern=SHA256)) -> Response:
    """Upload the bytes of a course file the user's content lists (`files_missing` of the content's answer). The server
    reads its text and makes it searchable for this user only."""
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/octet-stream":
        raise HTTPException(415, "Send raw file bytes as application/octet-stream.")
    too_big = HTTPException(413, "A file must be at most 25 MiB.")
    if length := request.headers.get("content-length"):
        try:
            size = int(length)
        except ValueError:
            raise HTTPException(400, "Invalid Content-Length.") from None
        if size < 0:
            raise HTTPException(400, "Invalid Content-Length.")
        if size > moodle_files.MAX_BYTES:
            raise too_big
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > moodle_files.MAX_BYTES:
            raise too_big
        data.extend(chunk)
    if hashlib.sha256(data).hexdigest() != sha256:
        raise HTTPException(422, "The bytes do not match the sha256")
    match await run_in_threadpool(moodle_files.put_blob, user.innohassle_id, sha256, bytes(data)):
        case "not_listed":
            raise HTTPException(404, "Send the course content listing this file first")
        case "type":
            raise HTTPException(415, "This file type is not read")
    return Response(status_code=204)


@router.get(
    "/files/{sha256}",
    response_class=Response,
    responses={200: {"description": "The file as uploaded", **BINARY}, **UNAUTHORIZED, 404: {"description": "Not a file of the user"}},
)
def get_file(user: VerifiedDep, sha256: str = Path(pattern=SHA256)) -> Response:
    """The original bytes of one of the user's course files (shown in the browser for PDF, images and text)."""
    found = moodle_files.get_blob(user.innohassle_id, sha256)
    if found is None:
        raise HTTPException(404, "No such file in your Moodle data")
    filename, suffix, data = found
    disposition = "inline" if suffix in moodle_files.INLINE else "attachment"
    return Response(
        data,
        media_type=moodle_files.SUFFIXES[suffix],
        headers={
            "Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(filename)}",
            "Cache-Control": NO_STORE,
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox",
        },
    )


@router.get("/search", responses=UNAUTHORIZED)
def search_files(
    user: VerifiedDep,
    response: Response,
    q: str = Query(min_length=1, max_length=500),
    course_id: int | None = None,
    limit: int = Query(8, ge=1, le=20),
) -> list[MoodleFileHitOut]:
    """Pieces of the user's own course files (slides, assignments, readings) that answer the query, best first."""
    response.headers["Cache-Control"] = NO_STORE
    hits = moodle_files.search(user.innohassle_id, [q], course_ids=[course_id] if course_id is not None else None, limit=limit)
    return [
        MoodleFileHitOut(
            course_id=h.course_id, course=h.course, module_id=h.module_id, filename=h.filename, url=h.url,
            sha256=h.sha256, heading=h.heading, text=h.text,
        )
        for h in hits
    ]


@router.delete("", status_code=204, responses=UNAUTHORIZED)
def delete_my_moodle(user: VerifiedDep) -> Response:
    """Delete all of the user's Moodle data."""
    moodle_sync.forget(user.innohassle_id)
    return Response(status_code=204)
