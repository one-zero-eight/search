import datetime

import pymongo
from pymongo import IndexModel

from src.custom_pydantic import CustomModel
from src.storages.mongo.__base__ import CustomDocument


class MessageSchema(CustomModel):
    message_id: int
    "Unique message identifier inside this chat."
    date: datetime.datetime
    "Date the message was sent."
    chat_id: int
    "Conversation the message belongs to."
    chat_title: str
    "Title of the chat."
    chat_username: str
    "Username of the chat."
    text: str | None = None
    """
    For text messages, the actual UTF-8 text of the message, 0-4096 characters.
    If the message contains entities (bold, italic, ...) you can access *text.markdown* or
    *text.html* to get the marked up message text. In case there is no entity, the fields
    will contain the same text as *text*.
    """
    caption: str | None = None
    """
    Caption for the audio, document, photo, video or voice, 0-1024 characters.
    If the message contains caption entities (bold, italic, ...) you can access *caption.markdown* or
    *caption.html* to get the marked up caption text. In case there is no caption entity, the fields
    will contain the same text as *caption*.
    """
    link: str | None = None
    "Generate a link to this message, only for groups and channels."


class Message(MessageSchema, CustomDocument):
    class Settings:
        indexes = [
            IndexModel(
                [("message_id", pymongo.ASCENDING)],
                unique=True,
            ),
            IndexModel(
                [("chat_id", pymongo.ASCENDING), ("date", pymongo.DESCENDING)],
            ),
            IndexModel(
                [("text", pymongo.TEXT), ("caption", pymongo.TEXT), ("chat_title", pymongo.TEXT)], name="text_index"
            ),
        ]
