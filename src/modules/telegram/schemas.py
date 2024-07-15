from datetime import datetime
from pydantic import BaseModel, Field


class Chat(BaseModel):
    id: int = Field(serialization_alias="chat_id")
    type: str
    title: str
    username: str


class MessageSchema(BaseModel):
    id: int = Field(serialization_alias="message_id")
    sender_chat: Chat
    date: datetime
    chat: Chat
    text: str | None
    caption: str | None


class DBMessageSchema(BaseModel):
    message_id: int
    date: datetime
    chat_id: int
    chat_title: str
    chat_username: str
    text: str | None
    caption: str | None
    link: str
