import re
from collections import defaultdict
from re import RegexFlag

from starlette.requests import Request

from src.modules.moodle.schemas import InContent
from src.modules.search.repository import moodle_entry_contents_to_sources
from src.modules.search.schemas import Sources
from src.storages.mongo.moodle import MoodleCourse, MoodleEntry


# noinspection PyMethodMayBeStatic
class MoodleRepository:
    async def read_all(self) -> list[MoodleEntry]:
        return await MoodleEntry.find().to_list()

    async def grouped_by_course_fullname(self) -> list:
        grouped = await MoodleEntry.aggregate(
            [
                {"$group": {"_id": "$course_fullname", "ids": {"$push": {"$toString": "$_id"}}}},
                {"$project": {"_id": 0, "course_fullname": "$_id", "ids": 1}},
            ]
        ).to_list()

        return grouped

    async def get_by_course_fullname(self) -> list:
        grouped = await MoodleEntry.aggregate(
            [
                {"$group": {"_id": "$course_fullname"}},
                {"$project": {"course_fullname": "$_id"}},
            ]
        ).to_list()

        return [item["course_fullname"] for item in grouped]

    async def get_courses_grouped_by_semester(self) -> dict[str, list[str]]:
        grouped = await MoodleEntry.aggregate(
            [
                {"$group": {"_id": "$course_fullname"}},
                {"$project": {"course_fullname": "$_id"}},
            ]
        ).to_list()

        courses = [item["course_fullname"] for item in grouped]

        patterns = [re.compile(r"\[(?P<semester>([FS]|SUM|IBC)\s?\d{2})(-MFAI)?\]", RegexFlag.IGNORECASE)]

        semester_groups = defaultdict(list)
        no_semester = []

        for course in courses:
            for pattern in patterns:
                match = pattern.search(course)
                if match:
                    normalized = match.group("semester").replace(" ", "")
                    semester_groups[normalized].append(course)
                    break
            else:
                no_semester.append(course)

        double_sem_pattern = re.compile(
            r"\[(?P<left>([FS]|SUM|IBC)\s?\d{2})(-MFAI)?-(?P<right>([FS]|SUM|IBC)\s?\d{2})(-MFAI)?\]",
            RegexFlag.IGNORECASE,
        )
        to_delete = []
        for sem in no_semester:
            match = double_sem_pattern.search(sem)
            if match:
                left, right = match.group("left"), match.group("right")
                semester_groups[left].append(sem)
                semester_groups[right].append(sem)
                to_delete.append(sem)
        for el in to_delete:
            no_semester.remove(el)

        if no_semester:
            semester_groups["No Semester"] = sorted(no_semester)
        # Sort it in such way:
        # Sum25, S25, F25, Sum24, S24, F24, ..., No Semester
        semester_groups = sorted(semester_groups.items(), key=lambda x: (x[0][-2:], x[0][0]))
        return dict(semester_groups)

    async def get_courses_by_course_fullname_content(self, course_fullname: str, request: Request) -> list[Sources]:
        # Sources
        entries = await MoodleEntry.find({"course_fullname": course_fullname}).to_list()

        sources = []
        for e in entries:
            for c in e.contents:
                source = moodle_entry_contents_to_sources(e, c, request)
                if source:
                    sources.append(source)
        return sources

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
