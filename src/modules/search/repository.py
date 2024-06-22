from fastapi import Request
from src.modules.search.schemas import SearchResponse, MoodleSource, SearchResponses
from src.storages.mongo import MoodleEntry

MOODLE_URL = "https://moodle.innopolis.university"


# noinspection PyMethodMayBeStatic
class SearchRepository:
    async def by_meta(self, query: str, *, request: Request) -> SearchResponses:
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
            .to_list(None)
        )

        responses = []

        for e in entries:
            response = SearchResponse(
                markdown_text="",
                score=e["score"],
                sources=[
                    MoodleSource(
                        course_id=e["course_id"],
                        course_name=e["course_fullname"],
                        module_id=e["module_id"],
                        module_name=e["module_name"],
                        display_name=c["filename"],
                        resource_type="pdf",
                        anchor_url=f'{MOODLE_URL}/course/view.php?id={e["course_id"]}#module-{e["module_id"]}',
                        resource_preview_url=str(
                            request.url_for("preview_moodle").include_query_params(
                                course_id=e["course_id"],
                                module_id=e["module_id"],
                                type=c["type"],
                                filename=c["filename"],
                            ),
                        ),
                    )
                    for c in e["contents"]
                    if c["type"] == "file"
                ],
            )
            if response.sources:
                responses.append(response)

        return SearchResponses(responses=responses, searched_for=query)


search_repository: SearchRepository = SearchRepository()
