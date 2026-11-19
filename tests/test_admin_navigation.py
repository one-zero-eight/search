"""Private admin navigation and authorization, without Telegram or a database."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from aiogram.enums import ChatType

from catix.tgbot import admin


def message(text="/admin", *, user_id=71, kind=ChatType.PRIVATE):
    return SimpleNamespace(
        text=text, from_user=SimpleNamespace(id=user_id),
        chat=SimpleNamespace(id=user_id, type=kind),
        answer=AsyncMock(), edit_text=AsyncMock(), forward_origin=None,
    )


@pytest.fixture(autouse=True)
def reset_pending(monkeypatch):
    from catix.tgbot import listen

    monkeypatch.setattr(listen, "cancel_pending", Mock(), raising=False)
    monkeypatch.setattr(admin.admins, "configured", lambda: [])
    monkeypatch.setattr(admin.admins, "added", lambda: [])
    monkeypatch.setattr(admin, "_menu", AsyncMock())
    admin.PENDING.clear()
    yield
    admin.PENDING.clear()


def test_admin_opens_navigation_without_fetching_administrator_profiles(monkeypatch):
    monkeypatch.setattr(admin, "_is_admin", AsyncMock(return_value=True))
    bot = SimpleNamespace(get_chat=AsyncMock())
    msg = message()
    asyncio.run(admin.admin_command(msg, bot))
    response = msg.answer.call_args
    buttons = [b for row in response.kwargs["reply_markup"].inline_keyboard for b in row]
    assert {b.callback_data for b in buttons} >= {"ls:l:0", "adm:users"}
    assert "Группы и источники" in " ".join(b.text for b in buttons)
    bot.get_chat.assert_not_called()


def test_revoked_admin_cannot_finish_pending_add(monkeypatch):
    monkeypatch.setattr(admin, "_is_admin", AsyncMock(return_value=False))
    add = Mock()
    monkeypatch.setattr(admin.admins, "add", add)
    admin.PENDING.add(71)
    msg = message("999")
    asyncio.run(admin.new_admin(msg, SimpleNamespace()))
    add.assert_not_called()
    assert 71 not in admin.PENDING
    assert "администратора" in msg.answer.call_args.args[0]


def test_admin_callback_in_group_cannot_mutate(monkeypatch):
    monkeypatch.setattr(admin, "_is_admin", AsyncMock(return_value=True))
    remove = Mock()
    monkeypatch.setattr(admin.admins, "remove", remove)
    query = SimpleNamespace(
        from_user=SimpleNamespace(id=71), data="adm:rm:99",
        message=message(kind=ChatType.SUPERGROUP), answer=AsyncMock(),
    )
    asyncio.run(admin.admin_callback(query, SimpleNamespace()))
    remove.assert_not_called()
    assert query.answer.call_args.kwargs["show_alert"] is True


def test_any_command_cancels_pending_admin_input():
    admin.PENDING.add(71)
    assert admin._waiting_for_id(message("/start")) is False
    assert 71 not in admin.PENDING


@pytest.mark.parametrize("callback", [None, "adm:home", "adm:users", "adm:add"])
def test_admin_navigation_cancels_group_wizard(monkeypatch, callback):
    from catix.tgbot import listen

    cancel = Mock()
    monkeypatch.setattr(listen, "cancel_pending", cancel, raising=False)
    monkeypatch.setattr(admin, "_is_admin", AsyncMock(return_value=True))
    if callback:
        query = SimpleNamespace(from_user=SimpleNamespace(id=71), data=callback,
                                message=message(), answer=AsyncMock())
        asyncio.run(admin.admin_callback(query, SimpleNamespace()))
    else:
        asyncio.run(admin.admin_command(message(), SimpleNamespace()))
    cancel.assert_called_once_with(71)


def test_revoked_admin_command_clears_pending_input(monkeypatch):
    monkeypatch.setattr(admin, "_is_admin", AsyncMock(return_value=False))
    admin.PENDING.add(71)
    asyncio.run(admin.admin_command(message(), SimpleNamespace()))
    assert 71 not in admin.PENDING


def test_malformed_remove_callback_does_not_crash_or_write(monkeypatch):
    monkeypatch.setattr(admin, "_is_admin", AsyncMock(return_value=True))
    remove = Mock()
    monkeypatch.setattr(admin.admins, "remove", remove)
    query = SimpleNamespace(from_user=SimpleNamespace(id=71), data="adm:rm:not-an-id",
                            message=message(), answer=AsyncMock())
    asyncio.run(admin.admin_callback(query, SimpleNamespace()))
    remove.assert_not_called()
    assert query.answer.called
