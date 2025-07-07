import json
from unittest.mock import MagicMock, patch

import pytest
from beanie import PydanticObjectId
from fastapi import Request
from httpx import ASGITransport, AsyncClient
from minio import Minio

from src.api.app import app as api_app
from src.api.lifespan import setup_database
from src.ml_service.app import app as ml_app
from src.modules.minio.repository import MinioRepository
from src.modules.parsers.routes import run_parse_route
from src.modules.search.repository import SearchRepository
from src.modules.sources_enum import InfoSources, MongoEntryNameToMongoEntry
from src.storages.mongo import MoodleEntry
from src.storages.mongo.moodle import MoodleContentSchema


@pytest.fixture(autouse=True)
async def mock_ml_service_client(ml_client):
    """Mock that returns our test client"""

    def mock():
        return ml_client

    with patch("src.modules.ml.ml_client.get_ml_service_client", new=mock):
        yield


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


@pytest.fixture(scope="session")
async def fill_mongo_with_test_data():
    motor_client = await setup_database()

    filepath = "tests/test_data/data.json"
    with open(filepath, encoding="utf-8") as file:
        for line in file:
            data = json.loads(line)
            model_class = MongoEntryNameToMongoEntry[data["model_type"]]
            model_instance = model_class(**data["data"])
            await model_instance.save()

    yield

    motor_client.close()


@pytest.fixture(scope="session")
async def init_ml_data(fill_mongo_with_test_data, mock_ml_service_client):
    for source in (InfoSources.hotel, InfoSources.eduwiki, InfoSources.campuslife, InfoSources.residents):
        await run_parse_route(section=source, parsing_is_needed=False, indexing_is_needed=True)


@pytest.fixture(scope="session")
async def api_client(fill_mongo_with_test_data):
    async with AsyncClient(transport=ASGITransport(app=api_app), base_url="http://test") as client:
        yield client


@pytest.fixture(scope="session")
async def ml_client(fill_mongo_with_test_data):
    async with AsyncClient(transport=ASGITransport(app=ml_app), base_url="http://test") as client:
        yield client
