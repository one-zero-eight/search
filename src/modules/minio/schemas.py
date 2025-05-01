from src.custom_pydantic import CustomModel


class MoodleFileObject(CustomModel):
    course_id: int
    module_id: int
    filename: str

    course_fullname: str = ""
    section_summary: str = ""
    module_name: str = ""
    module_modname: str = ""
