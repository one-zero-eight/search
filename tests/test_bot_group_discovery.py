"""Discover Bot API groups without opting them into ingestion."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from aiogram.enums import ChatMemberStatus, ChatType

from catix.tgbot import bot


@pytest.mark.parametrize("status,member", [
    (ChatMemberStatus.MEMBER, True),
    (ChatMemberStatus.ADMINISTRATOR, True),
    (ChatMemberStatus.LEFT, False),
    (ChatMemberStatus.KICKED, False),
])
def test_membership_updates_only_register_availability(monkeypatch, status, member):
    register = Mock()
    enable = Mock()
    monkeypatch.setattr(bot.userbot_config, "register_bot_chat", register, raising=False)
    monkeypatch.setattr(bot.userbot_config, "set_listen", enable)
    update = SimpleNamespace(
        chat=SimpleNamespace(id=-10071, title="Учебный чат", username=None, type=ChatType.SUPERGROUP),
        new_chat_member=SimpleNamespace(status=status),
    )
    assert hasattr(bot, "group_status"), "group membership needs discovery without saving messages"
    asyncio.run(bot.group_status(update))
    register.assert_called_once_with(-10071, "Учебный чат", None, member=member)
    enable.assert_not_called()


def test_unconfigured_message_discovers_chat_without_writing_content(monkeypatch):
    register = Mock()
    put = AsyncMock()
    monkeypatch.setattr(bot.userbot_config, "register_bot_chat", register, raising=False)
    monkeypatch.setattr(bot.userbot_config, "bot_listens", lambda _: False)
    monkeypatch.setattr(bot.writer, "put", put)
    monkeypatch.setattr(bot, "IGNORED", set())
    msg = SimpleNamespace(
        text="Do not store this message", caption=None, photo=None, document=None, edit_date=None,
        chat=SimpleNamespace(id=-10071, title="Учебный чат", username=None),
    )
    asyncio.run(bot._save(msg))
    register.assert_called_once_with(-10071, "Учебный чат", None)
    put.assert_not_called()
    asyncio.run(bot._save(msg))
    assert register.call_count == 1  # no extra metadata write for every ignored message


