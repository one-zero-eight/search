import datetime


from src.custom_pydantic import CustomModel


class MinioData(CustomModel):
    size: int | None
    last_modified: datetime.datetime | None
    object_name: str
    metadata: dict[str, str] | None


class MoodleFileObject(CustomModel):
    course_id: int
    module_id: int
    filename: str
    minio_data: MinioData
