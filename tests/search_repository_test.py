from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import HTTPError

from src.modules.ml.schemas import MLSearchResult, MLSearchResultItem
from src.modules.search.repository import moodle_entry_contents_to_sources
from src.modules.search.schemas import SearchResponses
from src.modules.sources_enum import InfoSources
from src.storages.mongo import EduWikiEntry, MoodleEntry


@pytest.mark.asyncio
async def test_by_meta_moodle(search_repo, sample_moodle_entry):
    with patch.object(MoodleEntry, "get_motor_collection") as mock_collection:
        mock_collection.return_value.find.return_value.sort.return_value.to_list = AsyncMock(
            return_value=[{**sample_moodle_entry, "score": 0.7}, {**sample_moodle_entry, "score": 0.8}]
        )

        source = InfoSources.moodle
        results = await search_repo._by_meta("test query", limit=10, section=source)

        assert len(results) == 2
        assert results[0].score == 0.7
        assert results[1].score == 0.8
        mock_collection.return_value.find.assert_called_once_with(
            {"$text": {"$search": "test query"}}, {"score": {"$meta": "textScore"}}
        )


@pytest.mark.asyncio
async def test_by_meta_unknown_section(search_repo):
    # In the future it will be likely HTTPException
    with pytest.raises(AssertionError):
        await search_repo._by_meta("test", limit=10, section="unknown_section")


def test_moodle_entry_contents_to_sources(mock_search_repo_request, sample_moodle_entry_mock):
    preview_url = "http://testurl/preview?course_id=1&module_id=2&filename=test_file.pdf"
    mock_url = MagicMock()
    mock_url.include_query_params.return_value = preview_url
    mock_search_repo_request.url_for.return_value = mock_url

    entry = sample_moodle_entry_mock

    content = MagicMock()
    content.type = "file"
    content.filename = "test_file.pdf"

    source = moodle_entry_contents_to_sources(entry, content, mock_search_repo_request)

    assert (
        source.link
        == f"https://moodle.innopolis.university/course/view.php?id={entry.course_id}#sectionid-{entry.section_id}-title"
    )
    assert source.resource_preview_url == preview_url
    mock_search_repo_request.url_for.assert_called_once_with("preview_moodle")
    mock_search_repo_request.url_for.return_value.include_query_params.assert_called_once_with(
        course_id=entry.course_id, module_id=entry.module_id, filename="test_file.pdf"
    )


@pytest.mark.asyncio
async def test_search_via_mongo_moodle(search_repo, mock_search_repo_request, sample_moodle_entry_mock):
    with patch.object(search_repo, "_by_meta", new_callable=AsyncMock) as mock_by_meta:
        mock_by_meta.return_value = [MagicMock(score=0.9, inner=sample_moodle_entry_mock)]

        results = await search_repo.search_via_mongo("test query", [InfoSources.moodle], mock_search_repo_request, 10)

        assert len(results.responses) == 1
        assert results.responses[0].score == 0.9
        assert results.searched_for == "test query"


@pytest.mark.asyncio
async def test_search_via_mongo_eduwiki(search_repo, mock_search_repo_request):
    with patch.object(search_repo, "_by_meta", new_callable=AsyncMock) as mock_by_meta:
        eduwiki_entry = MagicMock(spec=EduWikiEntry)
        eduwiki_entry.source_page_title = "Test Page"
        eduwiki_entry.content = "Test content"
        eduwiki_entry.source_url = "http://test.url"

        mock_by_meta.return_value = [MagicMock(score=0.8, inner=eduwiki_entry)]

        results = await search_repo.search_via_mongo("test query", [InfoSources.eduwiki], mock_search_repo_request, 10)

        assert len(results.responses) == 1
        assert results.responses[0].score == 0.8
        assert results.responses[0].source.display_name == "Test Page"


@pytest.mark.asyncio
async def test_search_sources_ml_success(search_repo, mock_search_repo_request, sample_moodle_entry_mock):
    with patch("src.modules.search.repository.get_ml_service_client") as mock_client:
        # Setup mock client
        mock_ml_response = MagicMock()
        mock_ml_response.raise_for_status.return_value = None
        mock_ml_response.json.return_value = {
            "result_items": [{"resource": "moodle", "mongo_id": "1", "score": 0.9, "content": "test_content"}]
        }

        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_ml_response)

        with patch.object(MoodleEntry, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = sample_moodle_entry_mock

            results = await search_repo.search_sources("test query", [InfoSources.moodle], mock_search_repo_request, 10)

            assert len(results.responses) == 1
            assert results.responses[0].score == 0.9
            assert results.searched_for == "test query"


@pytest.mark.asyncio
async def test_search_sources_ml_fallback(search_repo, mock_search_repo_request):
    with patch("src.modules.search.repository.get_ml_service_client") as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(side_effect=HTTPError("Test error"))

        with patch.object(search_repo, "search_via_mongo", new_callable=AsyncMock) as mock_fallback:
            mock_fallback.return_value = SearchResponses(responses=[], searched_for="test query")

            results = await search_repo.search_sources("test query", [InfoSources.moodle], mock_search_repo_request, 10)

            assert len(results.responses) == 0
            mock_fallback.assert_called_once()


@pytest.mark.asyncio
async def test_process_ml_results(search_repo, mock_search_repo_request, sample_moodle_entry_mock):
    eduwiki_entry = MagicMock(spec=EduWikiEntry)
    eduwiki_entry.source_page_title = "test_title"
    eduwiki_entry.source_url = "http://testurl"

    results = MLSearchResult(
        result_items=[
            MLSearchResultItem.model_validate(
                {"resource": InfoSources.moodle, "mongo_id": "1", "score": 0.7, "content": "test_content"}
            ),
            MLSearchResultItem.model_validate(
                {"resource": InfoSources.eduwiki, "mongo_id": "2", "score": 0.9, "content": "test_content"}
            ),
        ]
    )

    with (
        patch.object(MoodleEntry, "get", new_callable=AsyncMock) as mock_moodle_get,
        patch.object(EduWikiEntry, "get", new_callable=AsyncMock) as mock_eduwiki_get,
    ):
        mock_moodle_get.return_value = sample_moodle_entry_mock
        mock_eduwiki_get.return_value = eduwiki_entry

        responses = await search_repo._process_ml_results(results, mock_search_repo_request)

        assert len(responses) == 2
        assert responses[0].source.display_name == "test_title"
        assert responses[0].score == 0.9
        assert responses[1].score == 0.7
