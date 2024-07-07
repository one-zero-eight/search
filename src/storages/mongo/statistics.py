import datetime
from typing import Any

import pymongo
from pydantic import Field
from pymongo import IndexModel

from src.custom_pydantic import CustomModel
from src.storages.mongo.__base__ import CustomDocument


class WrappedResponseSchema(CustomModel):
    source: Any
    score: float
    user_feedback: str = None  # 'like', 'dislike', or None


class SearchStatisticsSchema(CustomModel):
    query: str
    wrapped_responses: list[WrappedResponseSchema]
    time_spent: float  # Time spent on the search in seconds
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.UTC))


class SearchStatistics(SearchStatisticsSchema, CustomDocument):
    class Settings:
        indexes = [
            IndexModel([("query", pymongo.TEXT)], name="query_index"),
            IndexModel([("created_at", pymongo.DESCENDING)], name="created_at_index"),
        ]
