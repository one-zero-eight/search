import os

from fastapi import Request
from src.modules.search.schemas import SearchResponse, MoodleSource, SearchResponses
from src.storages.mongo import MoodleEntry

MOODLE_URL = "https://moodle.innopolis.university"


# noinspection PyMethodMayBeStatic
class SearchRepository:
    async def by_meta(self, query: str, *, request: Request, limit: int) -> SearchResponses:
        # search by text
        entries = (
            await MoodleEntry.get_motor_collection()
            .find(
                {
                    "$text": {
                        "$search": query,
                    },
                },
                {
                    "score": {"$meta": "textScore"},
                },
            )
            .sort({"score": {"$meta": "textScore"}})
            .to_list(limit)
        )

        responses = []

        for e in entries:
            for c in e["contents"]:
                if c["type"] != "file":
                    continue
                _, file_extension = os.path.splitext(c["filename"])
                if not file_extension:
                    continue
                resource_type = file_extension[1:]
                preview_url = str(
                    request.url_for("preview_moodle").include_query_params(
                        course_id=e["course_id"],
                        module_id=e["module_id"],
                        type=c["type"],
                        filename=c["filename"],
                    ),
                )
                if "section_id" in c and c["section_id"] is not None:
                    link = f'{MOODLE_URL}/course/view.php?id={e["course_id"]}#sectionid-{e["section_id"]}-title'
                else:
                    link = f'{MOODLE_URL}/course/view.php?id={e["course_id"]}#module-{e["module_id"]}'

                response = SearchResponse(
                    score=e["score"],
                    source=MoodleSource(
                        course_id=e["course_id"],
                        course_name=e["course_fullname"],
                        module_id=e["module_id"],
                        module_name=e["module_name"],
                        resource_type=resource_type,
                        filename=c["filename"],
                        link=link,
                        resource_preview_url=preview_url,
                        resource_download_url=preview_url,
                    ),
                )
                responses.append(response)

        return SearchResponses(responses=responses, searched_for=query)


search_repository: SearchRepository = SearchRepository()
