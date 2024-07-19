from src.modules.moodle.schemas import InContent
from src.storages.mongo.moodle import MoodleEntry, MoodleCourse


# noinspection PyMethodMayBeStatic
class MoodleRepository:
    async def read_all(self) -> list[MoodleEntry]:
        return await MoodleEntry.find().to_list()

    async def read_all_in(self, course_module_filenames: list[tuple[int, int, str]]) -> list[MoodleEntry]:
        if not course_module_filenames:
            return []
        return await MoodleEntry.find(
            {
                "$or": [
                    {
                        "course_id": course_id,
                        "module_id": module_id,
                        "contents.filename": filename,
                    }
                    for course_id, module_id, filename in course_module_filenames
                ]
            }
        ).to_list()

    async def read_all_courses(self) -> list[MoodleCourse]:
        return await MoodleCourse.find().to_list()

    async def content_uploaded(self, data: InContent) -> None:
        content = data.content

        await MoodleEntry.get_motor_collection().update_one(
            {"course_id": data.course_id, "module_id": data.module_id, "contents.filename": content.filename},
            {
                "$set": {
                    "contents.$.uploaded": True,
                    "contents.$.timecreated": content.timecreated,
                    "contents.$.timemodified": content.timemodified,
                }
            },
        )


moodle_repository: MoodleRepository = MoodleRepository()
