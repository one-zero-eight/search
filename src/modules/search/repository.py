import os

import httpx
from fastapi import Request

from src.api.logging_ import logger
from src.modules.compute.schemas import SearchTask, SearchResult
from src.modules.moodle.repository import moodle_repository
from src.modules.search.schemas import (
    SearchResponse,
    MoodleFileSource,
    SearchResponses,
    MoodleEntryWithScore,
    MoodleUrlSource,
    MoodleUnknownSource,
)
from src.storages.mongo import MoodleEntry
from src.storages.mongo.moodle import MoodleContentSchema
from src.config import settings

MOODLE_URL = "https://moodle.innopolis.university"


# noinspection PyMethodMayBeStatic
class SearchRepository:
    @property
    def compute_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=settings.api_settings.compute_service_url,
            headers={"X-API-KEY": settings.api_settings.compute_service_token},
        )

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
    ) -> SearchResponse | None:
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

        return SearchResponse(score=score, source=source)

    async def search_moodle(self, query: str, *, request: Request, limit: int) -> SearchResponses:
        search_task = SearchTask(query=query)

        async with self.compute_client as client:
            try:
                r = await client.post("/search", json=search_task.model_dump())
                r.raise_for_status()
                result = SearchResult.model_validate(r.json())
            except httpx.HTTPError as e:
                logger.warning(f"Failed to search: {e}")
                # Fallback to MongoDB search
                entries = await self._by_meta(query, limit=limit)
                responses = []

                for e in entries:
                    for c in e.contents:
                        response = self._moodle_entry_contents_to_search_response(e, c, request, score=e.score)
                        if response:
                            responses.append(response)

                return SearchResponses(responses=responses, searched_for=query)

        responses = []
        moodle_entries = await moodle_repository.read_all()
        _mapping = {(e.course_id, e.module_id): e for e in moodle_entries}

        for entry in result.result:
            moodle_entry = _mapping.get((entry.course_id, entry.module_id), None)
            if moodle_entry is None:
                logger.warning(f"Entry not found: {entry.course_id} {entry.module_id}")
                continue

            for c in moodle_entry.contents:
                if c.filename == entry.filename:
                    response = self._moodle_entry_contents_to_search_response(
                        moodle_entry, c, request, score=entry.score
                    )
                    if response:
                        responses.append(response)

        return SearchResponses(responses=responses, searched_for=query)


search_repository: SearchRepository = SearchRepository()
