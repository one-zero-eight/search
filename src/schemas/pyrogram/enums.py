"""
https://github.com/pyrogram/pyrogram/tree/master/pyrogram/enums
"""

from enum import auto, StrEnum


class AutoName(StrEnum):
    def _generate_next_value_(self, *args):
        return self.lower()

    def __repr__(self):
        return f"pyrogram.enums.{self}"


class ChatType(AutoName):
    """Chat type enumeration used in :obj:`~pyrogram.Chat`."""

    PRIVATE = auto()
    "Chat is a private chat with a user"

    BOT = auto()
    "Chat is a private chat with a bot"

    GROUP = auto()
    "Chat is a basic group"

    SUPERGROUP = auto()
    "Chat is a supergroup"

    CHANNEL = auto()
    "Chat is a channel"
