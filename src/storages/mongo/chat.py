import datetime

import pymongo
from pydantic import Field
from pymongo import IndexModel

from src.custom_pydantic import CustomModel
from src.storages.mongo.__base__ import CustomDocument


class ChatSessionSchema(CustomModel):
    innohassle_id: str = Field(..., description="User InNoHassle ID, matches the cookie SESSION_ID")
    history: list[dict] = Field(
        default_factory=list, description="List of messages in the session, without system messages"
    )
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
        description="Date and time at which the session was created",
    )


class ChatSession(ChatSessionSchema, CustomDocument):
    class Settings:
        indexes = [
            IndexModel(
                [("innohassle_id", pymongo.ASCENDING)],
                name="innohassle_id_idx",
            ),
        ]
