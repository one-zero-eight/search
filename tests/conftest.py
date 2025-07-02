from unittest.mock import MagicMock, patch

import pytest
from beanie import PydanticObjectId
from fastapi import Request
from minio import Minio

from src.modules.minio.repository import MinioRepository
from src.modules.search.repository import SearchRepository
from src.storages.mongo import MoodleEntry
from src.storages.mongo.moodle import MoodleContentSchema


@pytest.fixture
def mock_minio_settings():
    with patch("src.modules.minio.repository.settings") as mock:
        mock.minio.bucket = "test_bucket"
        yield mock


@pytest.fixture
def mock_minio_client():
    mock = MagicMock(spec=Minio)
    mock.bucket = "test_bucket"
    return mock


@pytest.fixture
def minio_repository(mock_minio_client, mock_minio_settings):
    return MinioRepository(mock_minio_client)


@pytest.fixture
def search_repo():
    return SearchRepository()


@pytest.fixture
def mock_search_repo_request():
    request = MagicMock(spec=Request)
    return request


@pytest.fixture
def sample_moodle_entry():
    return {
        "id": PydanticObjectId(),
        "course_id": 1,
        "course_fullname": "test_course",
        "section_id": 2,
        "section_summary": "test_section",
        "module_id": 3,
        "module_name": "test_module",
        "module_modname": "test_modname",
        "contents": [{"type": "file", "filename": "test_file.pdf", "content": "test_content"}],
    }


@pytest.fixture
def sample_moodle_entry_mock():
    entry = MagicMock(spec=MoodleEntry)
    entry.course_id = 1
    entry.section_id = 2
    entry.module_id = 3
    entry.course_fullname = "coursename"
    entry.module_name = "modulename"
    entry.contents = [
        MagicMock(spec=MoodleContentSchema, type="file", filename="test_file.pdf"),
    ]
    return entry
