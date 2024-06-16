__all__ = ["lifespan"]

from contextlib import asynccontextmanager

from fastapi import FastAPI


# TODO
async def setup_repositories():
    from src.repositories.innohassle_accounts import innohassle_accounts

    await innohassle_accounts.update_key_set()

    pass


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
    storage = await setup_repositories()
    yield
    # Application shutdown
    await storage.close_connection()
