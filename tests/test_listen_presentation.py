"""Readable topic summaries and General-topic selection in the Telegram wizard."""

from catix import userbot_config as config
from tests.test_listen_ui import env


def test_review_and_chat_card_name_stored_topics(env):
    state, ui = env
    state.topics = [config.Topic(1, "General", False), config.Topic(7, "Объявления <важное>", False)]
    ui.press("ls:add")
    ui.click("Available")
    ui.click("all")
    ui.click("Объявления")
    ui.click("Хранить")
    ui.click("Проверить")
    assert "Хранить: 1" in ui.screen[0]
    assert "Объявления &lt;важное&gt;" in ui.screen[0]
    ui.click("Подтвердить")
    ui.press("ls:c:-1002")
    assert "Объявления &lt;важное&gt;" in ui.screen[0]


def test_general_can_be_selected_when_telegram_omits_it(env):
    state, ui = env
    state.topics = [config.Topic(7, "Объявления", False)]
    ui.press("ls:add")
    ui.click("Available")
    ui.click("all")
    ui.click("General")
    ui.click("Хранить")
    ui.click("Проверить")
    ui.click("Подтвердить")
    assert state.policies[-1002]["topics"] == {1: "store"}


def test_nonforum_review_does_not_show_zero_stored_topics(env):
    state, ui = env
    ui.press("ls:add")
    ui.click("Bot only")
    ui.click("all")
    ui.click("Весь чат")
    ui.click("Хранить")
    ui.click("Проверить")
    assert "Весь чат: Хранить" in ui.screen[0]
    assert "Хранить: 0" not in ui.screen[0]
