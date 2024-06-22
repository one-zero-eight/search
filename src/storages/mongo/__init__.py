from typing import cast

from beanie import Document, View

from src.storages.mongo.moodle import MoodleEntry, MoodleCourse
from src.storages.mongo.telegram import Message

document_models = cast(
    list[type[Document] | type[View] | str],
    [Message, MoodleEntry, MoodleCourse],
)
