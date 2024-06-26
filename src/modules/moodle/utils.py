from fastapi import Form, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from pydantic.json_schema import SkipJsonSchema
from starlette import status

from src.modules.moodle.schemas import InContents


def content_to_minio_object(course_id: int, module_id: int, filename: str) -> str:
    return f"moodle/{course_id}/{module_id}/{filename}"


def module_to_minio_prefix(course_id: int, module_id: int) -> str:
    return f"moodle/{course_id}/{module_id}/"


def checker(data: InContents | SkipJsonSchema[str] = Form(...)):
    try:
        return InContents.model_validate_json(data)
    except ValidationError as e:
        raise HTTPException(
            detail=jsonable_encoder(e.errors()),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
