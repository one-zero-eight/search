from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse
from pymongo import UpdateOne
from starlette.requests import Request

from src.api.dependencies import VerifiedDep
from src.api.logging_ import logger
from src.modules.minio.repository import minio_repository
from src.modules.minio.schemas import MoodleFileObject
from src.modules.moodle.repository import moodle_repository
from src.modules.moodle.schemas import FlattenInContentsWithPresignedUrl, InContent, InContents, InCourses, InSections
from src.modules.search.schemas import Sources
from src.storages.mongo import MoodleCourse, MoodleEntry
from src.storages.mongo.moodle import MoodleContentSchema, MoodleEntrySchema

router = APIRouter(prefix="/moodle", tags=["Moodle"])


@router.get(
    "/courses/grouped-by-semester",
    responses={
        200: {
            "description": "Courses grouped by semester",
            "content": {
                "application/json": {
                    "example": {
                        "S25": ["[S25] Mathematical Analysis II / Математический анализ II"],
                        "F20": ["[F20] Discrete Mathematics"],
                        "F22": ["[F22]  Philosophy II (Languages and Perceptions)"],
                    }
                }
            },
        }
    },
)
async def get_courses_grouped_by_semester() -> dict[str, list[str]]:
    return await moodle_repository.get_courses_grouped_by_semester()


@router.get("/courses/by-course-fullname/content")
async def get_course_names_grouped(
    request: Request, course_fullname: str = Query(example="[S25] Mathematical Analysis II / Математический анализ II")
) -> list[Sources]:
    return await moodle_repository.get_courses_by_course_fullname_content(course_fullname, request)


@router.get(
    "/preview",
    responses={307: {"description": "Redirect to the file"}, 404: {"description": "File not found"}},
)
async def preview_moodle(course_id: int, module_id: int, filename: str):
    return RedirectResponse(url=minio_repository.get_presigned_url_moodle(course_id, module_id, filename))


@router.get(
    "/files",
    response_model=list[dict[str, Any]],
    responses={200: {"description": "Success"}},
)
async def get_moodle_files(_: VerifiedDep) -> list[MoodleFileObject]:
    return minio_repository.get_moodle_objects()


@router.get(
    "/courses",
    responses={200: {"description": "Success"}},
)
async def courses(_: VerifiedDep) -> list[MoodleCourse]:
    return await moodle_repository.read_all_courses()


@router.post(
    "/batch-courses",
    responses={200: {"description": "Success"}},
)
async def batch_upsert_courses(_: VerifiedDep, data: InCourses) -> None:
    operations = []
    for c in data.courses:
        m = MoodleCourse.model_validate(c, from_attributes=True)
        operations.append(UpdateOne({"course_id": m.course_id}, {"$set": m.model_dump()}, upsert=True))
    if not operations:
        return
    await MoodleCourse.get_motor_collection().bulk_write(operations, ordered=False)


@router.get(
    "/courses-content",
    responses={200: {"description": "Success"}},
)
async def courses_content(_: VerifiedDep) -> list[MoodleEntry]:
    return await moodle_repository.read_all()


@router.post(
    "/set-course-content",
    responses={200: {"description": "Success"}},
)
async def course_content(_: VerifiedDep, bulk: list[InSections]) -> None:
    operations = []
    course_module_filename = {
        (data.course_id, module.module_id, content.filename)
        for data in bulk
        for section in data.sections
        for module in section.modules
        for content in module.contents
    }

    moodle_entries = await moodle_repository.read_all_in(list(course_module_filename))
    moodle_entries_x = {(e.course_id, e.module_id, c.filename): (e, c) for e in moodle_entries for c in e.contents}

    for data in bulk:
        for section in data.sections:
            for module in section.modules:
                for c in module.contents:
                    _, mongo_content = moodle_entries_x.get(
                        (data.course_id, module.module_id, c.filename), (None, None)
                    )

                    if mongo_content and (
                        mongo_content.timecreated == c.timecreated and mongo_content.timemodified == c.timemodified
                    ):
                        c.uploaded = mongo_content.uploaded

                m = MoodleEntrySchema(
                    course_id=data.course_id,
                    course_fullname=data.course_fullname,
                    section_id=section.section_id,
                    section_summary=section.section_summary,
                    module_id=module.module_id,
                    module_name=module.module_name,
                    module_modname=module.module_modname,
                    contents=module.contents,
                )
                operations.append(
                    UpdateOne(
                        {"course_id": m.course_id, "module_id": m.module_id}, {"$set": m.model_dump()}, upsert=True
                    )
                )
    if not operations:
        return

    await MoodleEntry.get_motor_collection().bulk_write(operations, ordered=False)


@router.post(
    "/need-to-upload-contents",
    responses={200: {"description": "Success"}},
)
async def need_to_upload_contents(
    _: VerifiedDep, contents_list: list[InContents]
) -> list[FlattenInContentsWithPresignedUrl]:
    course_module_filenames = []

    for contents in contents_list:
        for content in contents.contents:
            if content.type != "file":
                continue
            course_module_filenames.append((contents.course_id, contents.module_id, content.filename))

    if not course_module_filenames:
        return []

    moodle_entries = await moodle_repository.read_all_in(course_module_filenames)
    moodle_entries_x = {(e.course_id, e.module_id, c.filename): (e, c) for e in moodle_entries for c in e.contents}
    response = []

    for contents in contents_list:
        for content in contents.contents:
            if content.type != "file":
                continue

            mongo_entry, mongo_content = moodle_entries_x.get(
                (contents.course_id, contents.module_id, content.filename), (None, None)
            )

            if mongo_entry is None or mongo_content is None:
                logger.warning("Entry not found in the database")
                continue

            mongo_entry: MoodleEntry
            mongo_content: MoodleContentSchema

            if not mongo_content.uploaded or (
                mongo_content.timecreated != content.timecreated or mongo_content.timemodified != content.timemodified
            ):
                response.append(
                    FlattenInContentsWithPresignedUrl(
                        course_id=contents.course_id,
                        module_id=contents.module_id,
                        content=MoodleContentSchema(
                            type=content.type,
                            filename=content.filename,
                            timecreated=content.timecreated,
                            timemodified=content.timemodified,
                            uploaded=mongo_content.uploaded,
                        ),
                        presigned_url=minio_repository.put_presigned_url_moodle(
                            contents.course_id, contents.module_id, content.filename
                        ),
                    )
                )

    return response


@router.post("/content-uploaded", responses={200: {"description": "Success"}})
async def content_uploaded(_: VerifiedDep, data: InContent) -> None:
    await moodle_repository.content_uploaded(data)
