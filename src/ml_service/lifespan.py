from contextlib import asynccontextmanager

from fastapi import FastAPI

# TODO: add proper initialization for ML stuff like vector db, LLM, etc.


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
