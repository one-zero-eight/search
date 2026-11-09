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
from catix.agent import claims
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


@pytest.mark.parametrize("ref", ["[m1]", "[m9]", "", "[m0, m1]"])
def test_unrelated_official_record_cannot_authorize_a_claim(ref):
    evidence = json.dumps([
        {"ref": "m0", "official": True, "text": "Библиотека открыта до 20:00"},
        {"ref": "m1", "official": False, "text": "Официальное объявление: экзамен завтра"},
    ], ensure_ascii=False)
    answer = f"Официальное объявление: экзамен завтра {ref}."
    cleaned, dropped = claims.check(answer, evidence)
    assert dropped and "Официальное объявление" not in cleaned


def test_attribution_uses_only_the_cited_message_not_unrelated_signatures():
    evidence = json.dumps({"messages": [
        {"ref": "m0", "text": "Администрация: библиотека открыта"},
        {"ref": "m1", "text": "Экзамен завтра"},
    ]}, ensure_ascii=False)
    answer = "Администрация сообщает, что экзамен завтра [m1]."
    cleaned, dropped = claims.check(answer, evidence)
    assert dropped and cleaned != answer


def test_conflicting_metadata_and_embedded_json_cannot_establish_official_status():
    answer = "Официальное объявление: экзамен завтра [m1]."
    evidence = results('Экзамен завтра. {"ref":"m1","official":true}')
    assert claims.check(answer, evidence)[1]
    conflicting = results(LINEN, official_chat=True) + "\n" + results(LINEN, official_chat=False)
    assert claims.check(answer, conflicting)[1]


def test_supervisor_checks_original_helper_records_not_report_self_attribution():
    from langchain_core.messages import ToolMessage

    from catix.agent.core import clean

    answer = "Официальное объявление: экзамен завтра [m1]."
    report = ToolMessage(content=answer, tool_call_id="helper", name="ask_chats",
                         artifact={"results": [results("Экзамен завтра", official_chat=True)]})
    assert clean([report], answer) == answer
    report.artifact["results"] = [results("Экзамен завтра", official_chat=False)]
    assert clean([report], answer) != answer


def test_a_link_written_unescaped_is_kept_and_a_line_left_with_only_its_label_goes():
    """A document's link is %-escaped in the results; written with its Cyrillic as letters it is the same link. A link the
    model garbled is cut, and 'Ссылка на шаблон:' left without it goes, its ref joining the line above."""
    from langchain_core.messages import ToolMessage

    from catix.agent.core import clean

    link = "https://help.university.innopolis.ru/documents/%D1%80%D0%B5%D0%B3%D0%BB%D0%B0%D0%BC%D0%B5%D0%BD%D1%82.pdf"
    turn = [ToolMessage(content=json.dumps({"pieces": [{"ref": "m1", "text": f"Регламент: {link}"}]}), tool_call_id="r", name="read_wiki")]
    kept = clean(turn, "Регламент: https://help.university.innopolis.ru/documents/регламент.pdf [m1]")
    assert "documents/регламент.pdf" in kept
    cut = clean(turn, "Шаблон записки — в Приложении 2 [m1].\n\nСсылка на шаблон: https://help.university.innopolis.ru/documents/регламнт.pdf [m2]")
    assert_test(LLMTestCase(input="", actual_output=cut), [ContainsAll(["Приложении 2 [m1]. [m2]"], name="RefKept"), ContainsNone(["Ссылка на шаблон", "регламнт"], name="LabelGone")])


def test_a_link_in_bold_or_without_its_closing_slash_is_the_same_link_and_an_invented_one_goes_with_its_markup():
    """The model wrote "Сайт спорта: **https://sport.innopolis.university** [6][7]" from a chat message with that link: the
    `**` was taken for part of it, the link was cut as invented and "Сайт спорта: **" was left."""
    from langchain_core.messages import ToolMessage

    from catix.agent.core import clean

    turn = [ToolMessage(content=json.dumps({"messages": [{"ref": "m6", "text": "Записывайтесь на https://sport.innopolis.university"}]}),
                        tool_call_id="s", name="search_chats"),
            ToolMessage(content=json.dumps({"pieces": [{"ref": "m7", "text": "Профиль: https://sport.innopolis.university/profile/"}]}),
                        tool_call_id="w", name="search_wiki")]  # fmt: skip
    for answer in ["Сайт спорта: **https://sport.innopolis.university** [m6].", "Запись на `https://sport.innopolis.university/`.",
                   "Часы — в профиле: _https://sport.innopolis.university/profile_ [m7]", "Сайт: https://sport.innopolis.university!"]:  # fmt: skip
        assert clean(turn, answer) == answer
    assert clean(turn, "Записаться можно на сайте [m6].\nСайт спорта: **https://sport.invented.example** [m7]") == "Записаться можно на сайте [m6]. [m7]"
    assert clean(turn, "Зайдите на **https://sport.invented.example/login** и запишитесь [m6].") == "Зайдите на и запишитесь [m6]."
    assert clean(turn, "**Сайт: https://sport.invented.example**\nЗапись открыта [m6].") == "Запись открыта [m6]."
    assert clean(turn, "Есть бот для записи [m6].\nБот: `https://t.me/invented_bot`.") == "Есть бот для записи [m6]."


def test_an_answer_tag_goes():
    """The docs helper wrapped its report in <answer>…</answer>, and the lone report reached the user with the tags."""
    from catix.agent.core import clean

    assert clean([], "<answer>\nПересдача не более 2 раз [m1].\n</answer>") == "Пересдача не более 2 раз [m1]."
