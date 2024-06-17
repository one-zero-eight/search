"""
https://github.com/pyrogram/pyrogram/blob/master/pyrogram/types/user_and_chats/chat.py
"""
from src.custom_pydantic import CustomModel
from src.schemas.pyrogram.enums import ChatType


class Chat(CustomModel):
    id: int
    "Unique identifier for this chat."
    type: ChatType
    "Type of chat."
    title: str = None
    "Title, for supergroups, channels and basic group chats."
    username: str = None
    "Username, for private chats, bots, supergroups and channels if available."
    first_name: str = None
    "First name of the other party in a private chat, for private chats and bots."
    last_name: str = None
    "Last name of the other party in a private chat."
    bio: str = None
    "Bio of the other party in a private chat."
    description: str = None
    "Description, for groups, supergroups and channel chats."
