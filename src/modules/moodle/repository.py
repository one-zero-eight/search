from src.storages.mongo.moodle import MoodleEntry


# noinspection PyMethodMayBeStatic
class MoodleRepository:
    async def read_all(self) -> list[MoodleEntry]:
        return await MoodleEntry.find().to_list()

    async def read_all_in(self, course_module_filenames: list[tuple[int, int, str]]) -> list[MoodleEntry]:
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


moodle_repository: MoodleRepository = MoodleRepository()
