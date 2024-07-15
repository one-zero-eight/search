from src.custom_pydantic import CustomModel


class MoodleFileObject(CustomModel):
    course_id: int
    module_id: int
    filename: str

    course_fullname: str = ""
    section_summary: str = ""
    module_name: str = ""
    module_modname: str = ""

    def meta_prefix(self) -> str:
        return " ".join([self.course_fullname, self.section_summary, self.module_name, self.module_modname])
