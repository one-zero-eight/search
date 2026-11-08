"""Moderation screens and handlers: never act outside an admin's private chat."""

import asyncio
import importlib.util
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest


def moderation():
    assert importlib.util.find_spec("catix.tgbot.source_requests") is not None, "source request moderation is missing"
    from catix.tgbot import source_requests
    return source_requests


def request(**changes):
    return {
        "id": "a" * 32, "email": "student@innopolis.university", "owner": "student",
        "invite_link": "https://t.me/+PrivateInvite", "group_code": "B26-CSE-01",
        "comment": "<private chat>", "title": None, "message": None, "status": "pending",
        **changes,
    }


def test_pending_detail_requires_explicit_group_and_consent_review():
    text, rows = moderation().request_screen(request())
    assert "B26-CSE-01" in text
    assert "&lt;private chat&gt;" in text and "<private chat>" not in text
    assert "администратор" in text.lower()
    callbacks = [button.callback_data for row in rows for button in row]
    assert "sr:review:" + "a" * 32 in callbacks
    assert not any(value.startswith("sr:approve:") for value in callbacks)


def test_review_is_explicit_about_scope_and_does_not_fetch_history():
    text, rows = moderation().review_screen(request())
    assert "B26-CSE-01" in text and "согласие" in text.lower()
    assert "sr:approve:" + "a" * 32 in [b.callback_data for row in rows for b in row]


def test_all_audience_review_warns_about_nonmembers_and_all_users():
    text, rows = moderation().review_screen(request(group_code="all"))
    assert "все пользователи cAtIx" in text
    assert "не только участники чата" in text
    assert "согласие" in text.lower()
    assert "sr:approve:" + "a" * 32 in [b.callback_data for row in rows for b in row]


def test_public_request_can_be_approved_by_command(monkeypatch):
    module = moderation()
    monkeypatch.setattr(module.changes, "admins", lambda: [7])
    store = Mock()
    store.get_request.return_value = request(group_code="all", status="approved")
    monkeypatch.setattr(module, "store", store)
    message = command("/source_approve " + "a" * 32 + " all")
    asyncio.run(module.approve_command(message))
    store.approve.assert_called_once_with("a" * 32, 7, "all")
    assert "все пользователи cAtIx" in message.answer.call_args.args[0]


def test_command_explains_why_private_consent_cannot_be_widened(monkeypatch):
    module = moderation()
    monkeypatch.setattr(module.changes, "admins", lambda: [7])
    store = Mock()
    store.approve.side_effect = ValueError("private request")
    monkeypatch.setattr(module, "store", store)
    message = command("/source_approve " + "a" * 32 + " all")
    asyncio.run(module.approve_command(message))
    assert "Нельзя сделать групповую заявку общей" in message.answer.call_args.args[0]
    store.get_request.assert_not_called()


def test_processed_request_has_no_approval_buttons():
    text, rows = moderation().request_screen(request(status="approved"))
    assert "одобрена" in text.lower()
    assert not any(b.callback_data.startswith("sr:review:") for row in rows for b in row)


def query(data, *, private=True):
    return SimpleNamespace(
        data=data, from_user=SimpleNamespace(id=7), answer=AsyncMock(),
        message=SimpleNamespace(chat=SimpleNamespace(type="private" if private else "supergroup"), edit_text=AsyncMock()),
    )


@pytest.mark.parametrize("private,admin", [(False, True), (True, False)])
def test_callback_requires_admin_and_private_chat(monkeypatch, private, admin):
    module = moderation()
    monkeypatch.setattr(module.changes, "admins", lambda: [7] if admin else [])
    callback = query("sr:approve:" + "a" * 32, private=private)
    store = Mock()
    monkeypatch.setattr(module, "store", store)
    asyncio.run(module.request_callback(callback))
    assert not store.mock_calls
    callback.answer.assert_awaited_once()


def test_admin_approval_records_exact_target_then_reads_back(monkeypatch):
    module = moderation()
    monkeypatch.setattr(module.changes, "admins", lambda: [7])
    store = Mock()
    store.get_request.side_effect = [request(), request(status="approved")]
    store.approve.return_value = True
    monkeypatch.setattr(module, "store", store)
    callback = query("sr:approve:" + "a" * 32)
    asyncio.run(module.request_callback(callback))
    store.approve.assert_called_once_with("a" * 32, 7, "B26-CSE-01")
    assert store.get_request.call_count == 2
    assert "одобрена" in callback.message.edit_text.call_args.args[0].lower()


def test_request_queue_paginates_without_exposing_invites(monkeypatch):
    module = moderation()
    store = Mock()
    store.pending_requests.return_value = [request(id=f"{number:032x}") for number in range(9)]
    monkeypatch.setattr(module, "store", store)
    text, rows = module.list_screen(0)
    store.pending_requests.assert_called_once_with(offset=0, limit=9)
    callbacks = [b.callback_data for row in rows for b in row]
    assert len([value for value in callbacks if value.startswith("sr:show:")]) == 8
    assert "sr:list:1" in callbacks
    assert "PrivateInvite" not in text


def test_list_callback_is_usable_for_admin(monkeypatch):
    module = moderation()
    monkeypatch.setattr(module.changes, "admins", lambda: [7])
    store = Mock()
    store.pending_requests.return_value = []
    monkeypatch.setattr(module, "store", store)
    callback = query("sr:list:0")
    asyncio.run(module.request_callback(callback))
    assert "нет" in callback.message.edit_text.call_args.args[0].lower()


def command(text, *, private=True):
    return SimpleNamespace(
        text=text, from_user=SimpleNamespace(id=7), answer=AsyncMock(),
        chat=SimpleNamespace(type="private" if private else "supergroup"),
    )


def test_approve_command_can_choose_group_and_reads_back(monkeypatch):
    module = moderation()
    monkeypatch.setattr(module.changes, "admins", lambda: [7])
    store = Mock()
    store.approve.return_value = True
    store.get_request.return_value = request(group_code="B27-CSE-02", status="approved")
    monkeypatch.setattr(module, "store", store)
    message = command("/source_approve " + "a" * 32 + " b27-cse-02")
    asyncio.run(module.approve_command(message))
    store.approve.assert_called_once_with("a" * 32, 7, "B27-CSE-02")
    assert "B27-CSE-02" in message.answer.call_args.args[0]


@pytest.mark.parametrize("text,private", [
    ("/source_approve " + "a" * 32 + " bad!", True),
    ("/source_approve " + "a" * 32 + " B26-CSE-01", False),
    ("/source_approve nope B26-CSE-01", True),
])
def test_approve_command_refuses_invalid_group_or_context(monkeypatch, text, private):
    module = moderation()
    monkeypatch.setattr(module.changes, "admins", lambda: [7])
    store = Mock()
    monkeypatch.setattr(module, "store", store)
    asyncio.run(module.approve_command(command(text, private=private)))
    store.approve.assert_not_called()


def test_reject_command_saves_reason_without_joining(monkeypatch):
    module = moderation()
    monkeypatch.setattr(module.changes, "admins", lambda: [7])
    store = Mock()
    store.reject.return_value = True
    store.get_request.return_value = request(status="rejected", message="Нет согласия")
    monkeypatch.setattr(module, "store", store)
    message = command("/source_reject " + "a" * 32 + " Нет согласия")
    asyncio.run(module.reject_command(message))
    store.reject.assert_called_once_with("a" * 32, 7, "Нет согласия")
    store.approve.assert_not_called()
    assert "Нет согласия" in message.answer.call_args.args[0]


def test_listen_offers_requests_even_before_userbot_publishes_dialogs(monkeypatch):
    from catix.tgbot import listen

    monkeypatch.setattr(listen.userbot_config, "dialogs", lambda: [])
    monkeypatch.setattr(listen.userbot_config, "listened", lambda: {})
    monkeypatch.setattr(listen.userbot_config, "readers", lambda: {})
    monkeypatch.setattr(listen, "_groups_of", lambda _: {})
    monkeypatch.setattr(listen.official, "flags", lambda _: {})
    _, rows = listen._list_screen(7)
    assert "sr:list:0" in [b.callback_data for row in rows for b in row]
    assert moderation().router in listen.router.sub_routers


def test_registered_router_handles_private_command_without_telegram_io(monkeypatch):
    from aiogram import Bot
    from aiogram.types import Message
    from catix.tgbot import listen

    module = moderation()
    monkeypatch.setattr(module.changes, "admins", lambda: [7])
    store = Mock()
    store.approve.return_value = True
    store.get_request.return_value = request(status="approved")
    monkeypatch.setattr(module, "store", store)
    answer = AsyncMock()
    monkeypatch.setattr(Message, "answer", answer)
    message = Message.model_validate({
        "message_id": 1, "date": 1, "chat": {"id": 7, "type": "private"},
        "from": {"id": 7, "is_bot": False, "first_name": "Admin"},
        "text": "/source_approve " + "a" * 32 + " B26-CSE-01",
    })
    asyncio.run(listen.router.propagate_event(update_type="message", event=message, bot=Bot("12345:" + "a" * 35)))
    store.approve.assert_called_once_with("a" * 32, 7, "B26-CSE-01")
    answer.assert_awaited_once()


def test_inaccessible_callback_is_refused_without_database_io(monkeypatch):
    from aiogram.types import InaccessibleMessage

    module = moderation()
    monkeypatch.setattr(module.changes, "admins", lambda: [7])
    store = Mock()
    monkeypatch.setattr(module, "store", store)
    callback = query("sr:approve:" + "a" * 32)
    callback.message = InaccessibleMessage(chat={"id": 7, "type": "private"}, message_id=1, date=0)
    asyncio.run(module.request_callback(callback))
    assert not store.mock_calls
    callback.answer.assert_awaited_once()
