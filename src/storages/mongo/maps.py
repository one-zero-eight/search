import pymongo
from pymongo import IndexModel

from src.custom_pydantic import CustomModel
from src.storages.mongo.__base__ import CustomDocument


class MapsEntrySchema(CustomModel):
    location_url: str
    scene_id: str
    area_id: str
    content: str


class MapsEntry(MapsEntrySchema, CustomDocument):
    class Settings:
        indexes = [
            IndexModel(
                [("content", pymongo.TEXT)],
                name="text_index",
            ),
        ]
