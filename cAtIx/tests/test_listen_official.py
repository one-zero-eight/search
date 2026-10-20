"""The "official chat" mark in the admin's /listen screens (DeepEval, no model involved): the chat screen shows the mark and
a button, the button's handler switches it, and the search results then say so."""

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from catix import official
from catix.db import pg, store
from catix.tgbot import listen
from tests.helpers import ContainsAll


@pytest.fixture
def in_the_list(chat):
    """The synthetic chat as a chat of the userbot's list, which is what /listen shows."""
    with pg.connection() as conn:
        conn.execute(
            "INSERT INTO userbot_dialogs (chat_id, title, kind, username, forum) VALUES (%s, %s, 'group', NULL, false)"
            " ON CONFLICT (chat_id) DO NOTHING",
            (chat, "tests: synthetic chat"),
        )
    try:
        yield chat
    finally:
        official.set_official(chat, False)
        with pg.connection() as conn:
            conn.execute("DELETE FROM userbot_dialogs WHERE chat_id = %s", (chat,))


def screen(chat_id: int) -> tuple[LLMTestCase, list[str]]:
    text, rows = listen._chat_screen(chat_id)
    buttons = [f"{b.callback_data}|{b.text}" for row in rows for b in row]
    return LLMTestCase(input="", actual_output=text + "\n" + "\n".join(buttons)), buttons


def test_chat_screen_shows_the_mark_and_a_button_to_switch_it(in_the_list):
    case, buttons = screen(in_the_list)
    assert_test(case, [ContainsAll(["Официальный чат: нет", f"ls:of:{in_the_list}|🏛 Сделать официальным"], name="NotOfficialYet")])


def test_the_button_switches_the_mark_both_ways(in_the_list):
    assert "официальным" in listen._toggle_official(in_the_list)
    case, _ = screen(in_the_list)
    assert_test(case, [ContainsAll(["Официальный чат: да", "Снять отметку"], name="Official")])
    assert official.flags([in_the_list]) == {in_the_list: True}
    rows = store.search(["ботаника"], chat_ids={in_the_list}, limit=3)
    assert rows and rows[0].chat_official is True  # the search results carry it

    assert "снята" in listen._toggle_official(in_the_list)
    case, _ = screen(in_the_list)
    assert_test(case, [ContainsAll(["Официальный чат: нет"], name="NotOfficialAgain")])


def test_the_list_marks_official_chats(in_the_list):
    official.set_official(in_the_list, True)
    text, rows = listen._list_screen(user_id=1)
    labels = [b.text for row in rows for b in row]
    # the chat may be on another page of a long list: the legend explains the icon either way
    assert "🏛 — официальный чат" in text
    assert any("🏛" in label and "synthetic chat" in label for label in labels) or len(listen.userbot_config.dialogs()) > listen.PAGE_SIZE


def test_the_toggle_ignores_a_chat_that_is_not_in_the_list():
    assert listen._toggle_official(-123456789) is None
