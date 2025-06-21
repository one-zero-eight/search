import os
from typing import assert_never

from fastapi import HTTPException, Request

from src.api.logging_ import logger
from src.modules.search.schemas import (
    CampusLifeSource,
    EduWikiSource,
    HotelSource,
    MoodleFileSource,
    MoodleUnknownSource,
    MoodleUrlSource,
    SearchResponse,
    SearchResponses,
    Sources,
    WithScore,
)
from src.modules.sources_enum import InfoSources
from src.storages.mongo import CampusLifeEntry, EduWikiEntry, HotelEntry, MoodleEntry
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
    async def _by_meta(self, query: str, *, limit: int, section: InfoSources) -> list[WithScore]:
        if section == InfoSources.hotel:
            model_class = HotelEntry
        elif section == InfoSources.eduwiki:
            model_class = EduWikiEntry
        elif section == InfoSources.campuslife:
            model_class = CampusLifeEntry
        elif section == InfoSources.moodle:
            model_class = MoodleEntry
        else:
            raise HTTPException(status_code=400, detail=f"Not supported section: {section}")
        # search by text
        entries = (
            await model_class.get_motor_collection()
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

        with_scores = []
        for e in entries:
            score = e.pop("score")
            with_scores.append(WithScore[model_class].model_validate({"score": score, "inner": e}))
        return with_scores

    def _moodle_entry_contents_to_search_response(
        self,
        entry: MoodleEntry,
        content: MoodleContentSchema,
        request: Request,
        score: float | list[float] | None = None,
    ) -> SearchResponse:
        source = moodle_entry_contents_to_sources(entry, content, request)
        return SearchResponse(score=score, source=source)

    async def search_mongo_index(self, query: str, *, request: Request, limit: int) -> SearchResponses:
        entries = []
        for section in InfoSources:
            logger.info(f"Searching for {section}")
            _ = await self._by_meta(query, limit=limit, section=section)
            logger.info(f"Found {len(_)} entries for {section}")
            entries.extend(_)
        responses = []

        for e in entries:
            inner = e.inner
            if isinstance(inner, MoodleEntry):
                for c in e.contents:
                    response = self._moodle_entry_contents_to_search_response(inner, c, request, score=e.score)
                    if response:
                        responses.append(response)
            elif isinstance(inner, CampusLifeEntry):
                responses.append(SearchResponse(score=e.score, source=CampusLifeSource(inner=inner)))
            elif isinstance(inner, HotelEntry):
                responses.append(SearchResponse(score=e.score, source=HotelSource(inner=inner)))
            elif isinstance(inner, EduWikiEntry):
                responses.append(SearchResponse(score=e.score, source=EduWikiSource(inner=inner)))
            else:
                assert_never(inner)

        responses.sort(key=lambda x: x.score, reverse=True)
        return SearchResponses(responses=responses, searched_for=query)


search_repository: SearchRepository = SearchRepository()
