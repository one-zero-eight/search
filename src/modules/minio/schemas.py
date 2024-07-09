import datetime

from urllib3 import HTTPHeaderDict

from src.custom_pydantic import CustomModel


class MinioData(CustomModel):
    size: int
    last_modified: datetime.datetime | None
    object_name: str
    metadata: dict[str, str] | HTTPHeaderDict | None


class MoodleFileObject(CustomModel):
    course_id: int
    module_id: int
    filename: str
    minio_data: MinioData
