__all__ = ["lifespan"]

from contextlib import asynccontextmanager

from beanie import init_beanie
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

# from src.api.search.schemas import read_search_responses
# from src.api.search.schemas import create_search_response
# from src.api.search.schemas import delete_search_response

from src.api.search.schemas import SearchResponseDocument
from src.config import settings


async def setup_repositories():
    from src.repositories.innohassle_accounts import innohassle_accounts

    await innohassle_accounts.update_key_set()

    pass


async def setup_mongo():
    client = AsyncIOMotorClient(settings.api_settings.db_url.get_secret_value())

    # TODO: Add database field to settings
    db = client["example_database"]

    await init_beanie(database=db, document_models=[SearchResponseDocument])

    # print(await read_search_responses())
    # await create_search_response()
    # print(await read_search_responses())
    #
    # delete_id = input("Input Object ID to delete: ")
    # await delete_search_response(delete_id)
    # print(await read_search_responses())


def setup_timezone():
    import sys
    import os
    import time

    if sys.platform != "win32":  # unix only
        os.environ["TZ"] = "Europe/Moscow"
        time.tzset()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Application startup
    # storage = await setup_repositories()

    await setup_mongo()
    yield
    # Application shutdown
    # await storage.close_connection()
