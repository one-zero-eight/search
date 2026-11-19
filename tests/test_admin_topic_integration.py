"""The real wizard writes real PostgreSQL policy; only Telegram transport is faked."""

from unittest.mock import AsyncMock

import pytest

from catix import userbot_config as config
from catix.tgbot import admin, listen
from tests.test_listen_ui import UI
from tests.test_topic_policy_db import db, policy_database  # reusable guarded disposable-DB fixtures


@pytest.fixture
def ui(db, monkeypatch):
    listen.SESSIONS.clear()
    listen.PAGE.clear()
    admin.PENDING.clear()
    monkeypatch.setattr(listen, "_is_admin", AsyncMock(return_value=True))
    yield UI()
    listen.SESSIONS.clear()
    admin.PENDING.clear()


def test_wizard_confirms_one_stored_topic_others_search_and_one_off(db, ui):
    ui.press("ls:add")
    ui.click("Forum")
    ui.click("Другая группа")
    ui.text("b26-cse-01")
    ui.click("Stored ·")
    ui.click("Хранить")
    ui.click("Off ·")
    ui.click("Выключен")
    ui.click("Проверить")
    assert -82001 not in config.listened()
    with db() as conn:
        assert conn.execute("SELECT 1 FROM chats WHERE chat_id=-82001").fetchone() is None
    ui.click("Подтвердить")
    assert "Сохранено" in ui.notices
    assert config.get_policy(-82001) == {"default": "search", "topics": {7: "store", 8: "off"}}
    assert config.userbot_reads()[-82001] == [7]
    assert -82001 in config.live_chats()
    assert config.topic_allowed(-82001, 7, 1)
    assert not config.topic_allowed(-82001, None, 1)
    assert not config.topic_allowed(-82001, 8, 1)
    assert config.search_topic_allowed(-82001, None)
    assert config.search_topic_allowed(-82001, 9)  # new topic inherits search
    assert not config.search_topic_allowed(-82001, 8)
    with db() as conn:
        assert conn.execute("SELECT group_code FROM chats WHERE chat_id=-82001").fetchone()["group_code"] == "B26-CSE-01"


def test_remove_last_stored_topic_then_disable_keeps_old_messages(db, ui):
    config.save_configuration(-82001, "all", "search", {7: "store"})
    with db() as conn:
        conn.execute("INSERT INTO messages (chat_id,msg_id,date,text) VALUES (-82001,100,now(),'retained history')")
    ui.press("ls:edit:-82001")
    ui.click("all")
    ui.click("Stored ·")
    ui.click("Только поиск")
    ui.click("Проверить")
    ui.click("Подтвердить")
    assert config.listened()[-82001] == []
    assert -82001 not in config.userbot_reads()
    assert not config.topic_allowed(-82001, 99, 1)
    ui.press("ls:adv:-82001")
    ui.click("Отключить группу")
    assert -82001 in config.listened()
    ui.click("Да, отключить")
    assert -82001 not in config.listened()
    assert not config.search_topic_allowed(-82001, 7)
    with db() as conn:
        assert conn.execute("SELECT text FROM messages WHERE chat_id=-82001 AND msg_id=100").fetchone()["text"] == "retained history"
