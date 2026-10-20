"""The code check of the final answer (agent/claims.py) and the `official` mark of chats (DeepEval, no model involved).

The model tends to write "the administration says", "ask the head of the building", "it was not announced" when no message
says so. Those sentences are cut unless the tool results back them, and "official" is allowed only for a chat an admin
marked official. These tests feed answers and tool results straight into the check.
"""

import json

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from catix import official
from catix.agent import claims, sources
from catix.db import store
from tests.helpers import ContainsAll, ContainsNone


def results(text: str, official_chat: bool = False, chat: str = "Dorm chat") -> str:
    """What search_chats returns, as the check sees it."""
    return json.dumps({"total": 1, "messages": [{"ref": "m1", "chat": chat, "official": official_chat, "text": text}]}, ensure_ascii=False)


def checked(answer: str, evidence: str) -> LLMTestCase:
    cleaned, _ = claims.check(answer, evidence)
    return LLMTestCase(input=answer, actual_output=cleaned)


LINEN = "Смена белья в корпусе 9 сегодня с 14:00 до 17:00"


def test_invented_attribution_and_advice_are_cut():
    answer = (
        "Согласно последним сообщениям от администрации жилого комплекса, смена белья в 9-м корпусе не анонсировалась.\n"
        "Сегодня смена белья в корпусе 9 с 14:00 до 17:00 [m1].\n"
        "Рекомендую уточнить у старосты корпуса."
    )
    assert_test(
        checked(answer, results(LINEN)),
        [ContainsNone(["администрац", "анонсир", "старост"], name="NoInventedClaims"), ContainsAll(["14:00 до 17:00", "[m1]"], name="FactStays")],
    )


def test_a_claim_the_messages_make_stays():
    answer = "Администрация сообщает, что смена белья сегодня с 14:00 до 17:00 [m1]."
    evidence = results("Администрация общежития: смена белья сегодня с 14:00 до 17:00")
    assert_test(checked(answer, evidence), [ContainsAll(["Администрация сообщает", "[m1]"], name="SupportedClaimStays")])


def test_official_is_cut_for_an_unofficial_chat_and_kept_for_an_official_one():
    answer = "Это официальное объявление: смена белья сегодня с 14:00 до 17:00 [m1]."
    assert_test(checked(answer, results(LINEN, official_chat=False)), [ContainsNone(["официальн"], name="NotOfficial")])
    assert_test(checked(answer, results(LINEN, official_chat=True)), [ContainsAll(["официальное объявление"], name="OfficialKept")])


def test_unofficial_is_not_mistaken_for_official():
    answer = "В неофициальных чатах пишут, что смена сегодня с 14:00 [m1]."
    assert_test(checked(answer, results(LINEN)), [ContainsAll(["неофициальных чатах"], name="UnofficialStays")])


def test_a_fully_unsupported_answer_gets_a_safe_reply():
    cleaned, dropped = claims.check("От администрации: это не анонсировалось.", results(LINEN))
    assert dropped
    assert_test(LLMTestCase(input="", actual_output=cleaned), [ContainsAll(["Не нашёл"], name="SafeReply")])


def test_english_answers_are_checked_too():
    answer = "The administration says it was not announced. The linen change is today 14:00-17:00 [m1]."
    assert_test(checked(answer, results(LINEN)), [ContainsNone(["administration", "announced"], name="NoInventedClaims"), ContainsAll(["14:00-17:00"], name="FactStays")])


def test_chats_are_unofficial_until_an_admin_marks_them(chat):
    def mark() -> bool:
        rows = store.search(["ботаника"], chat_ids={chat}, limit=3)
        assert rows, "the synthetic chat was not found"
        return rows[0].chat_official

    try:
        assert mark() is False
        assert official.set_official(chat, True)
        assert mark() is True
    finally:
        official.set_official(chat, False)


def test_the_source_list_says_when_a_chat_is_official():
    line = sources._line(1, {"chat_title": "Campus Information", "official": True, "date": None})
    other = sources._line(2, {"chat_title": "Dorm chat", "official": False, "date": None})
    assert_test(LLMTestCase(input="", actual_output=line), [ContainsAll(["(официальный чат)"], name="MarkedOfficial")])
    assert_test(LLMTestCase(input="", actual_output=other), [ContainsNone(["официальный"], name="NotMarked")])


def test_command_lists_and_switches_chats(chat):
    listing = official.command("")
    number = next(i for i, c in enumerate(official.chats(), 1) if c.chat_id == chat)
    try:
        assert "официальные" in listing.lower()
        assert "официальный чат ✔" in official.command(f"{number} on")
        assert chat in official.ids()
        assert "неофициальный" in official.command(f"{number} off")
        assert chat not in official.ids()
        assert official.command("999999") == official.USAGE
    finally:
        official.set_official(chat, False)


def test_mentions_and_advice_are_not_attributions():
    """Regression: a refusal that said 'contact the dean's office' lost that sentence, because the check cut every sentence that
    merely contained the word. Advice and links are not claims about where a message came from."""
    answers = [
        "I cannot help with forging documents. If you cannot attend, contact the Student Affairs office or the dean's office.",
        "Обратитесь в деканат или в учебный офис.",
        "Официальный Telegram-канал столовой: https://t.me/matrixfood",
        "Подробности на официальном сайте университета.",
        "Администрация общежития находится на первом этаже.",
    ]
    for answer in answers:
        cleaned, dropped = claims.check(answer, results(LINEN))
        assert not dropped, f"cut: {dropped}"
        assert_test(LLMTestCase(input=answer, actual_output=cleaned), [ContainsAll([answer[:25]], name="SentenceStays")])


def test_a_message_signed_by_the_administration_backs_the_attribution():
    answer = "Администрация сообщает, что смена белья сегодня с 14:00 до 17:00 [m1]."
    evidence = results("Смена белья сегодня с 14:00 до 17:00. С уважением, администрация жилого комплекса")
    assert_test(checked(answer, evidence), [ContainsAll(["Администрация сообщает"], name="Backed")])
