from src.custom_pydantic import CustomModel


class MoodleFileObject(CustomModel):
    course_id: int
    module_id: int
    filename: str
