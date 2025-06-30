import pymongo
from pymongo import IndexModel

from src.custom_pydantic import CustomModel
from src.storages.mongo.__base__ import CustomDocument

class ResidentsEntrySchema(CustomModel):
    source_url: str
    source_page_title: str
    content: str

class ResidentsEntry(ResidentsEntrySchema, CustomDocument):
    class Settings:
        indexes = [
            IndexModel(
                [("source_url", pymongo.TEXT), ("source_page_title", pymongo.TEXT), ("content", pymongo.TEXT)],
                name="text_index",
            ),
        ]