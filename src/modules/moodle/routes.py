from datetime import timedelta
from typing import Any

import minio
from fastapi import APIRouter, UploadFile, Depends
from fastapi.responses import RedirectResponse
from minio.deleteobjects import DeleteObject
from pymongo import UpdateOne

from src.api.dependencies import VerifiedDep
from src.config import settings
from src.modules.minio.repository import minio_repository
from src.modules.minio.schemas import MoodleFileObject
from src.modules.moodle.schemas import InCourses, InSections, InContents
from src.modules.moodle.utils import content_to_minio_object, module_to_minio_prefix, checker
from src.storages.minio import minio_client
from src.storages.mongo import MoodleCourse, MoodleEntry
from src.storages.mongo.moodle import MoodleEntrySchema

router = APIRouter(prefix="/moodle", tags=["Moodle"])


@router.get(
    "/preview",
    responses={307: {"description": "Redirect to the file"}, 404: {"description": "File not found"}},
)
async def preview_moodle(course_id: int, module_id: int, filename: str):
    # Redirect to a pre-signed URL
    obj = content_to_minio_object(course_id, module_id, filename)
    url = minio_client.presigned_get_object(settings.minio.bucket, obj, expires=timedelta(days=1))
    return RedirectResponse(url=url)


@router.get(
    "/files",
    response_model=list[dict[str, Any]],
    responses={200: {"description": "Success"}},
)
async def get_moodle_files(_: VerifiedDep) -> list[MoodleFileObject]:
    moodle_objects = minio_repository.get_moodle_objects()
    return moodle_objects


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
                section_id=section.section_id,
                section_summary=section.section_summary,
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
async def need_to_upload_contents(_: VerifiedDep, contents_list: list[InContents]) -> list[InContents]:
    result = []

    for contents in contents_list:
        need_to_update = False
        for content in contents.contents:
            if content.type != "file":
                continue

            try:
                obj = content_to_minio_object(contents.course_id, contents.module_id, content.filename)
                r = minio_client.stat_object(settings.minio.bucket, obj)
                meta = r.metadata
                if meta is None:
                    meta = {}
                timecreated = int(meta["x-amz-meta-timecreated"]) if "x-amz-meta-timecreated" in meta else None
                timemodified = int(meta["x-amz-meta-timemodified"]) if "x-amz-meta-timemodified" in meta else None
                # check if different
                if timecreated != content.timecreated or timemodified != content.timemodified:
                    need_to_update = True

            except minio.S3Error as e:
                if e.code == "NoSuchKey":
                    need_to_update = True
                else:
                    raise e

        if need_to_update:
            result.append(contents)

    return result


@router.post(
    "/upload-contents",
    responses={200: {"description": "Success"}},
)
async def upload_content(
    _: VerifiedDep,
    files: list[UploadFile],
    data: InContents = Depends(checker),
) -> None:
    # clear files for that module first
    module_prefix = module_to_minio_prefix(data.course_id, data.module_id)
    delete_object_list = list(
        map(
            lambda x: DeleteObject(x.object_name),
            minio_client.list_objects(settings.minio.bucket, module_prefix, recursive=True),
        )
    )
    minio_client.remove_objects(settings.minio.bucket, delete_object_list)

    # upload files
    for file, content in zip(files, data.contents):
        meta = {}

        if content.timecreated is not None:
            meta["x-amz-meta-timecreated"] = str(content.timecreated)
        if content.timemodified is not None:
            meta["x-amz-meta-timemodified"] = str(content.timemodified)

        minio_client.put_object(
            settings.minio.bucket,
            content_to_minio_object(data.course_id, data.module_id, content.filename),
            file.file,
            file.size or 0,
            file.content_type or "application/octet-stream",
            metadata=meta,  # type: ignore[arg-type]
        )
