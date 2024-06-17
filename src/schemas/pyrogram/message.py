import datetime

from src.custom_pydantic import CustomModel
from src.schemas.pyrogram.chat import Chat


class Message(CustomModel):
    id: int
    "Unique message identifier inside this chat."
    sender_chat: Chat = None
    "Sender of the message, sent on behalf of a chat."
    date: datetime.datetime = None
    "Date the message was sent."
    chat: Chat = None
    "Conversation the message belongs to."
    edit_date: datetime.datetime = None
    "Date the message was last edited."
    text: str = None
    """
    For text messages, the actual UTF-8 text of the message, 0-4096 characters.
    If the message contains entities (bold, italic, ...) you can access *text.markdown* or
    *text.html* to get the marked up message text. In case there is no entity, the fields
    will contain the same text as *text*.
    """
    caption: str = None
    """
    Caption for the audio, document, photo, video or voice, 0-1024 characters.
    If the message contains caption entities (bold, italic, ...) you can access *caption.markdown* or
    *caption.html* to get the marked up caption text. In case there is no caption entity, the fields
    will contain the same text as *caption*.
    """
    link: str = None
    "Generate a link to this message, only for groups and channels."
