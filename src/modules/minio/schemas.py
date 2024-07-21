from src.custom_pydantic import CustomModel


class MoodleFileObject(CustomModel):
    course_id: int
    module_id: int
    filename: str

    course_fullname: str = ""
    section_summary: str = ""
    module_name: str = ""
    module_modname: str = ""

    @property
    def meta_prefix(self) -> str:
        parts = []
        if self.course_fullname:
            parts.append(f"Course: {self.course_fullname}")
        if self.section_summary:
            parts.append(f"Section: {self.section_summary}")
        if self.module_name:
            parts.append(f"Module: {self.module_name}")
        if self.module_modname:
            parts.append(f"Type: {self.module_modname}")
        if self.filename:
            parts.append(f"Filename: {self.filename}")
        if not parts:
            return ""
        meta_prefix = "; ".join(parts) + "\n"
        return meta_prefix
