from datetime import timedelta

import minio
from fastapi import APIRouter, Depends, UploadFile
from pymongo import UpdateOne
from starlette.responses import RedirectResponse

from src.api.dependencies import VerifiedDep
from src.modules.moodle.schemas import InCourses, InSections, FileOnlyContentRef, UploadableContentRef
from src.storages.minio import minio_client
from src.storages.mongo import MoodleCourse, MoodleEntry
from src.storages.mongo.moodle import MoodleEntrySchema

router = APIRouter(prefix="/moodle", tags=["Moodle"])


@router.get(
    "/preview",
    responses={307: {"description": "Redirect to the file"}, 404: {"description": "File not found"}},
    response_class=RedirectResponse,
)
async def preview_moodle(_: VerifiedDep, content_ref: FileOnlyContentRef = Depends()) -> RedirectResponse:
    # get url for minio
    url = minio_client.presigned_get_object("search", content_ref.to_object(), expires=timedelta(days=1))

    return RedirectResponse(url)


@router.post(
    "/batch-courses",
    responses={200: {"description": "Success"}},
)
async def batch_upsert_courses(_: VerifiedDep, data: InCourses) -> None:
    operations = []
    for c in data.courses:
        m = MoodleCourse.model_validate(c, from_attributes=True)
        operations.append(UpdateOne({"course_id": m.course_id}, {"$set": m.model_dump()}, upsert=True))

    await MoodleCourse.get_motor_collection().bulk_write(operations, ordered=False)


@router.get(
    "/courses",
    responses={200: {"description": "Success"}},
)
async def courses(_: VerifiedDep) -> list[MoodleCourse]:
    return await MoodleCourse.find().to_list()


@router.post(
    "/set-course-content",
    responses={200: {"description": "Success"}},
)
async def course_content(_: VerifiedDep, data: InSections) -> None:
    operations = []

    for section in data.sections:
        for module in section.modules:
            m = MoodleEntrySchema(
                course_id=data.course_id,
                course_fullname=data.course_fullname,
                module_id=module.module_id,
                module_name=module.module_name,
                module_modname=module.module_modname,
                contents=module.contents,
            )
            operations.append(
                UpdateOne({"course_id": m.course_id, "module_id": m.module_id}, {"$set": m.model_dump()}, upsert=True)
            )

    await MoodleEntry.get_motor_collection().bulk_write(operations, ordered=False)


@router.get(
    "/courses-content",
    responses={200: {"description": "Success"}},
)
async def courses_content(_: VerifiedDep) -> list[MoodleEntry]:
    return await MoodleEntry.find().to_list()


@router.post(
    "/need-to-upload-contents",
    responses={200: {"description": "Success"}},
)
async def need_to_upload_contents(_: VerifiedDep, contents: list[UploadableContentRef]) -> list[FileOnlyContentRef]:
    result = []

    for content in contents:
        try:
            r = minio_client.stat_object("search", content.to_object())
            meta = r.metadata
            timecreated = int(meta["timecreated"]) if "timecreated" in meta else None
            timemodified = int(meta["timemodified"]) if "timemodified" in meta else None
            # check if different
            if timecreated != content.timecreated or timemodified != content.timemodified:
                result.append(content)

        except minio.S3Error as e:
            if e.code == "NoSuchKey":
                result.append(content)
            else:
                raise e

    return result


@router.post(
    "/upload-content",
    responses={200: {"description": "Success"}},
)
async def upload_content(_: VerifiedDep, file: UploadFile, content: UploadableContentRef = Depends()) -> None:
    # upload file
    meta = {}

    if content.timecreated is not None:
        meta["timecreated"] = str(content.timecreated)
    if content.timemodified is not None:
        meta["timemodified"] = str(content.timemodified)

    minio_client.put_object(
        "search",
        content.to_object(),
        file.file,
        file.size,
        file.content_type or "application/octet-stream",
        metadata=meta,
    )
