import pymongo
from pymongo import IndexModel

from src.custom_pydantic import CustomModel
from src.storages.mongo.__base__ import CustomDocument


class ClubsEntrySchema(CustomModel):
    source_url: str
    source_page_title: str
    content: str


class ClubsEntry(ClubsEntrySchema, CustomDocument):
    class Settings:
        indexes = [
            IndexModel(
                [("source_page_title", pymongo.TEXT), ("content", pymongo.TEXT)],
                name="text_index",
            ),
        ]
