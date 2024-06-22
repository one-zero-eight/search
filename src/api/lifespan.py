__all__ = ["lifespan"]

import asyncio
import json
from contextlib import asynccontextmanager

from beanie import init_beanie
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import timeout
from pymongo.errors import ConnectionFailure
from src.api.logging_ import logger

from src.config import settings
from src.storages.mongo import document_models


async def setup_database() -> AsyncIOMotorClient:
    motor_client = AsyncIOMotorClient(
        settings.database.uri.get_secret_value(), connectTimeoutMS=5000, serverSelectionTimeoutMS=5000, tz_aware=True
    )
    motor_client.get_io_loop = asyncio.get_running_loop  # type: ignore[method-assign]

    # healthcheck mongo
    try:
        with timeout(2):
            server_info = await motor_client.server_info()
            server_info_pretty_text = json.dumps(server_info, indent=2, default=str)
            logger.info(f"Connected to MongoDB: {server_info_pretty_text}")
    except ConnectionFailure as e:
        logger.critical("Could not connect to MongoDB: %s" % e)
        raise e

    mongo_db = motor_client.get_default_database()
    await init_beanie(database=mongo_db, document_models=document_models, recreate_views=True)
    return motor_client


async def setup_repositories():
    from src.modules.innohassle_accounts import innohassle_accounts

    await innohassle_accounts.update_key_set()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Application startup
    motor_client = await setup_database()

    await setup_repositories()
    yield

    # -- Application shutdown --
    motor_client.close()
