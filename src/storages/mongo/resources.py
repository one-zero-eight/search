import pymongo
from pymongo import IndexModel

from src.custom_pydantic import CustomModel
from src.modules.resources_types_enum import Resources
from src.storages.mongo.__base__ import CustomDocument


class ResourcesEntrySchema(CustomModel):
    source_url: str
    source_page_title: str
    content: str
    resource_type: Resources


class ResourcesEntry(ResourcesEntrySchema, CustomDocument):
    class Settings:
        indexes = [
            IndexModel(
                [("source_page_title", pymongo.TEXT), ("content", pymongo.TEXT)],
                name="text_index",
            ),
        ]
