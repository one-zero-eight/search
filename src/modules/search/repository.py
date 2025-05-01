import os

from fastapi import Request

from src.api.logging_ import logger
from src.modules.search.schemas import (
    SearchResponse,
    MoodleFileSource,
    SearchResponses,
    MoodleEntryWithScore,
    MoodleUrlSource,
    MoodleUnknownSource,
    Sources,
)
from src.storages.mongo import MoodleEntry
from src.storages.mongo.moodle import MoodleContentSchema

MOODLE_URL = "https://moodle.innopolis.university"


def moodle_entry_contents_to_sources(entry: MoodleEntry, content: MoodleContentSchema, request: Request) -> Sources:
    link = f"{MOODLE_URL}/course/view.php?id={entry.course_id}#sectionid-{entry.section_id}-title"
    within_folder = len(entry.contents) > 1

    if content.type == "file":
        _, file_extension = os.path.splitext(content.filename)
        if not file_extension:
            logger.warning(f"File extension not found: {content.filename}")
        preview_url = str(
            request.url_for("preview_moodle").include_query_params(
                course_id=entry.course_id, module_id=entry.module_id, filename=content.filename
            ),
        )
        source = MoodleFileSource(link=link, resource_preview_url=preview_url, resource_download_url=preview_url)
    elif content.type == "url":
        # https://moodle.innopolis.university/mod/url/view.php?id=79390&redirect=1
        url = f"{MOODLE_URL}/mod/url/view.php?id={entry.module_id}&redirect=1"
        source = MoodleUrlSource(link=link, url=url)
    else:
        logger.warning(f"Unknown content type: {content.type}")
        source = MoodleUnknownSource(link=link)

    source.set_breadcrumbs_and_display_name(
        entry.course_fullname, entry.module_name, content.filename, within_folder=within_folder
    )

    return source


# noinspection PyMethodMayBeStatic
class SearchRepository:
    async def _by_meta(self, query: str, *, limit: int) -> list[MoodleEntryWithScore]:
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
            .to_list(None if limit <= 0 else limit)
        )
        return [MoodleEntryWithScore.model_validate(e) for e in entries]

    def _moodle_entry_contents_to_search_response(
        self,
        entry: MoodleEntry,
        content: MoodleContentSchema,
        request: Request,
        score: float | list[float] | None = None,
    ) -> SearchResponse:
        source = moodle_entry_contents_to_sources(entry, content, request)
        return SearchResponse(score=score, source=source)

    async def search_moodle(self, query: str, *, request: Request, limit: int) -> SearchResponses:
        entries = await self._by_meta(query, limit=limit)
        responses = []

        for e in entries:
            for c in e.contents:
                response = self._moodle_entry_contents_to_search_response(e, c, request, score=e.score)
                if response:
                    responses.append(response)

        return SearchResponses(responses=responses, searched_for=query)


search_repository: SearchRepository = SearchRepository()
