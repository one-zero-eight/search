from src.storages.mongo.moodle import MoodleEntry


# noinspection PyMethodMayBeStatic
class MoodleRepository:
    async def read_all(self) -> list[MoodleEntry]:
        return await MoodleEntry.find().to_list()


moodle_repository: MoodleRepository = MoodleRepository()
