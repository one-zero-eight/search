import pymongo
from pymongo import IndexModel

from src.custom_pydantic import CustomModel
from src.storages.mongo.__base__ import CustomDocument


class MoodleContentSchema(CustomModel):
    type: str
    filename: str
    timecreated: int | None = None
    timemodified: int | None = None
    uploaded: bool = False


class MoodleEntrySchema(CustomModel):
    course_id: int
    course_fullname: str
    section_id: int
    section_summary: str
    module_id: int
    module_name: str
    module_modname: str
    contents: list[MoodleContentSchema]

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

        meta_prefix = "; ".join(parts) + "\n"
        return meta_prefix


class MoodleEntry(MoodleEntrySchema, CustomDocument):
    class Settings:
        indexes = [
            IndexModel(("course_id", "module_id"), unique=True),
            IndexModel(
                [("course_fullname", pymongo.TEXT), ("module_name", pymongo.TEXT), ("contents.filename", pymongo.TEXT)],
                name="text_index",
            ),
        ]


class MoodleCourseSchema(CustomModel):
    course_id: int
    fullname: str
    startdate: int
    enddate: int
    coursecategory: str


class MoodleCourse(MoodleCourseSchema, CustomDocument):
    class Settings:
        indexes = [
            IndexModel("course_id", unique=True),
            IndexModel(
                [("fullname", pymongo.TEXT), ("coursecategory", pymongo.TEXT)],
                name="text_index",
            ),
        ]
