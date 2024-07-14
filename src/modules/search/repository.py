import asyncio
import os
import uuid

from fastapi import Request

from src.api.logging_ import logger
from src.modules.compute.schemas import SearchTask, SearchResult
from src.modules.moodle.repository import moodle_repository
from src.modules.search.schemas import SearchResponse, MoodleSource, SearchResponses, MoodleEntryWithScore
from src.storages.mongo import MoodleEntry
from src.storages.mongo.moodle import MoodleContentSchema

MOODLE_URL = "https://moodle.innopolis.university"


class QueueItem:
    def __init__(self, search_request: SearchTask, future: asyncio.Future):
        self.search_request = search_request
        self.future = future


# noinspection PyMethodMayBeStatic
class SearchRepository:
    pending_searches: dict[str, SearchTask] = {}
    completed_searches: dict[str, SearchResult] = {}
    pending_events: dict[str, asyncio.Event] = {}

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
            .to_list(limit)
        )
        return [MoodleEntryWithScore.model_validate(e) for e in entries]

    def _moodle_entry_contents_to_search_response(
        self,
        entry: MoodleEntry,
        content: MoodleContentSchema,
        request: Request,
        score: float | list[float] | None = None,
    ) -> SearchResponse | None:
        if content.type == "file":
            _, file_extension = os.path.splitext(content.filename)
            if not file_extension:
                return None
            preview_url = str(
                request.url_for("preview_moodle").include_query_params(
                    course_id=entry.course_id, module_id=entry.module_id, filename=content.filename
                ),
            )
        else:
            preview_url = None

        if entry.section_id is not None:
            link = f"{MOODLE_URL}/course/view.php?id={entry.course_id}#sectionid-{entry.section_id}-title"
        else:
            link = f"{MOODLE_URL}/course/view.php?id={entry.course_id}#module-{entry.module_id}"

        source = MoodleSource(link=link, resource_preview_url=preview_url, resource_download_url=preview_url)
        source.set_breadcrumbs_and_display_name(entry.course_fullname, entry.module_name)
        return SearchResponse(score=score, source=source)

    def submit_search_results(self, search_results: list[SearchResult]) -> None:
        for result in search_results:
            self.completed_searches[result.task_id] = result
            self.pending_searches.pop(result.task_id, None)
            event = self.pending_events.get(result.task_id)
            if event:
                event.set()

    async def search_moodle(self, query: str, *, request: Request, limit: int, use_ai: bool) -> SearchResponses:
        if not use_ai:
            entries = await self._by_meta(query, limit=limit)
            responses = []

            for e in entries:
                for c in e.contents:
                    response = self._moodle_entry_contents_to_search_response(e, c, request, score=e.score)
                    if response:
                        responses.append(response)

            return SearchResponses(responses=responses, searched_for=query)

        else:
            search_task = SearchTask(query=query, task_id=str(uuid.uuid4()))
            result = None
            self.pending_searches[search_task.task_id] = search_task
            self.pending_events[search_task.task_id] = asyncio.Event()
            try:
                await asyncio.wait_for(self.pending_events[search_task.task_id].wait(), timeout=10)
                del self.pending_events[search_task.task_id]
                result = self.completed_searches.pop(search_task.task_id, None)
                logger.info(result)
            except asyncio.TimeoutError:
                logger.warning("Search task timed out")
                self.pending_events.pop(search_task.task_id, None)
                self.pending_searches.pop(search_task.task_id, None)

            if result is None:
                return SearchResponses(responses=[], searched_for=query)
            else:
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
