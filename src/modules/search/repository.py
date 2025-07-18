import os
from typing import assert_never

import httpx
from fastapi import HTTPException, Request

from src.api.logging_ import logger
from src.ml_service.text import clean_text
from src.modules.ml.ml_client import get_ml_service_client
from src.modules.ml.schemas import MLSearchResult, MLSearchTask
from src.modules.search.schemas import (
    CampusLifeSource,
    EduwikiSource,
    HotelSource,
    MapsSource,
    MoodleFileSource,
    MoodleUnknownSource,
    MoodleUrlSource,
    ResidentsSource,
    ResourcesSource,
    SearchResponse,
    SearchResponses,
    Sources,
    WithScore,
)
from src.modules.sources_enum import InfoSources
from src.storages.mongo import (
    CampusLifeEntry,
    EduWikiEntry,
    HotelEntry,
    MapsEntry,
    MoodleEntry,
    ResidentsEntry,
    ResourcesEntry,
)
from src.storages.mongo.moodle import MoodleContentSchema

MOODLE_URL = "https://moodle.innopolis.university"
"Size of preview text shown to user"


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
        try:
            if section == InfoSources.moodle:
                _MongoEntryClass = MoodleEntry
            elif section == InfoSources.eduwiki:
                _MongoEntryClass = EduWikiEntry
            elif section == InfoSources.campuslife:
                _MongoEntryClass = CampusLifeEntry
            elif section == InfoSources.hotel:
                _MongoEntryClass = HotelEntry
            elif section == InfoSources.maps:
                _MongoEntryClass = MapsEntry
            elif section == InfoSources.residents:
                _MongoEntryClass = ResidentsEntry
            elif section == InfoSources.resources:
                _MongoEntryClass = ResourcesEntry
            else:
                assert_never(section)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Not supported section: {section}")

        # search by text
        entries = (
            await _MongoEntryClass.get_motor_collection()
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
            with_scores.append(WithScore[_MongoEntryClass].model_validate({"score": score, "inner": e}))  # type: ignore
        return with_scores

    def _moodle_entry_contents_to_search_response(
        self,
        entry: MoodleEntry,
        content: MoodleContentSchema,
        request: Request,
        score: float | list[float] | None = None,
    ) -> SearchResponse:
        source = moodle_entry_contents_to_sources(entry, content, request)
        if hasattr(source, "preview_text"):
            source.preview_text = clean_text(source.preview_text)
        return SearchResponse(score=score, source=source)

    async def search_via_mongo(
        self, query: str, sources: list[InfoSources], request: Request, limit: int
    ) -> SearchResponses:
        """
        Fallback to search in mongo for cases when ML service fails or cannot be used.
        """
        entries: list[WithScore] = []
        for section in sources:
            logger.info(f"Searching for {section}")
            _ = await self._by_meta(query, limit=limit, section=section)
            logger.info(f"Found {len(_)} entries for {section}")
            entries.extend(_)
        responses: list[SearchResponse] = []

        for e in entries:
            inner = e.inner
            if isinstance(inner, MoodleEntry):
                for c in inner.contents:
                    response = self._moodle_entry_contents_to_search_response(inner, c, request, score=e.score)
                    if response:
                        responses.append(response)
            elif isinstance(inner, MapsEntry):
                responses.append(
                    SearchResponse(
                        score=e.score,
                        source=MapsSource(
                            display_name=inner.title,
                            preview_text=inner.content,
                            url=inner.location_url,
                        ),
                    )
                )
            elif isinstance(inner, ResourcesEntry):
                responses.append(
                    SearchResponse(
                        score=e.score,
                        source=ResourcesSource(
                            display_name=inner.title,
                            preview_text=inner.content,
                            url=inner.location_url,
                            resource_type=inner.resource_type,
                        ),
                    )
                )
            elif isinstance(inner, (CampusLifeEntry | HotelEntry | EduWikiEntry | ResidentsEntry)):
                if isinstance(inner, CampusLifeEntry):
                    _SourceModel = CampusLifeSource
                elif isinstance(inner, HotelEntry):
                    _SourceModel = HotelSource
                elif isinstance(inner, EduWikiEntry):
                    _SourceModel = EduwikiSource
                elif isinstance(inner, ResidentsEntry):
                    _SourceModel = ResidentsSource
                else:
                    assert_never(inner)

                source_model = _SourceModel(
                    display_name=inner.source_page_title,
                    preview_text=clean_text(inner.content),
                    url=inner.source_url,
                )
                responses.append(SearchResponse(score=e.score, source=source_model))
            else:
                assert_never(inner)

        responses.sort(key=lambda x: x.score, reverse=True)  # type: ignore
        return SearchResponses(responses=responses, searched_for=query)

    async def search_sources(
        self, query: str, sources: list[InfoSources], request: Request, limit: int
    ) -> SearchResponses:
        search_task = MLSearchTask(query=query, sources=sources, limit=limit)

        async with get_ml_service_client() as client:
            try:
                r = await client.post("/search", json=search_task.model_dump())
                r.raise_for_status()
                results = MLSearchResult.model_validate(r.json())

                responses = await self._process_ml_results(results, request)
                return SearchResponses(responses=responses, searched_for=query)
            except httpx.HTTPError as e:
                # Fallback to mongo search
                logger.exception(f"ML service search failed: {repr(e)}", exc_info=True)
                return await self.search_via_mongo(query, sources, request, limit)

    async def _process_ml_results(self, results: MLSearchResult, request: Request) -> list[SearchResponse]:
        responses: list[SearchResponse] = []

        for res_item in results.result_items:
            if res_item.resource == InfoSources.moodle:
                mongo_entry = await MoodleEntry.get(res_item.mongo_id)
                if mongo_entry is None:
                    logger.warning(f"mongo_entry is None: {res_item}")
                else:
                    for c in mongo_entry.contents:
                        response = self._moodle_entry_contents_to_search_response(
                            mongo_entry,
                            c,
                            request,
                            res_item.score,
                        )
                        responses.append(response)
            elif res_item.resource == InfoSources.resources:
                mongo_entry = await ResourcesEntry.get(res_item.mongo_id)
                if mongo_entry is None:
                    logger.warning(f"mongo_entry is None: {res_item}")
                else:
                    responses.append(
                        SearchResponse(
                            score=res_item.score,
                            source=ResourcesSource(
                                display_name=mongo_entry.source_page_title,
                                preview_text="\n".join(mongo_entry.content.splitlines()[2:]).strip("\n")
                                if mongo_entry.content
                                else "",
                                url=mongo_entry.source_url,
                                resource_type=mongo_entry.resource_type,
                            ),
                        )
                    )
            elif res_item.resource in (
                InfoSources.eduwiki,
                InfoSources.campuslife,
                InfoSources.hotel,
                InfoSources.residents,
                InfoSources.maps,
            ):
                model_map = {
                    InfoSources.eduwiki: (EduWikiEntry, EduwikiSource),
                    InfoSources.campuslife: (CampusLifeEntry, CampusLifeSource),
                    InfoSources.hotel: (HotelEntry, HotelSource),
                    InfoSources.residents: (ResidentsEntry, ResidentsSource),
                    InfoSources.maps: (MapsEntry, MapsSource),
                }

                _MongoEntryClass, _SourceModel = model_map[res_item.resource]

                mongo_entry = await _MongoEntryClass.get(res_item.mongo_id)
                if mongo_entry is None:
                    logger.warning(f"mongo_entry is None: {res_item}")
                else:
                    source_model = _SourceModel(
                        display_name=mongo_entry.title
                        if res_item.resource == InfoSources.maps
                        else mongo_entry.source_page_title,
                        preview_text="\n".join(mongo_entry.content.splitlines()[2:]).strip("\n")
                        if mongo_entry.content
                        else "",
                        url=mongo_entry.location_url
                        if res_item.resource == InfoSources.maps
                        else mongo_entry.source_url,
                    )
                    responses.append(SearchResponse(score=res_item.score, source=source_model))
            else:
                assert_never(res_item)
        responses.sort(key=lambda x: x.score, reverse=True)
        return responses


search_repository: SearchRepository = SearchRepository()
