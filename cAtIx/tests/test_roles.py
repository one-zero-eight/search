"""The supervisor and its two helpers (agent/core.py `_helper_tool`, agent/roles.py).

Without a model: the prompts and tools are split between the roles, and a question travels supervisor -> helper -> supervisor
with a scripted fake model (the helper's report is cleaned, its sources reach the supervisor, its tool calls stay out of the
supervisor's context). With the model: the supervisor asks the right helper, and answers greetings and refusals itself.
"""

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from catix.agent import roles
from catix.agent.core import build_agent, final_answer
from catix.agent.tools import TOOLS, AgentContext
from tests.helpers import ContainsAll, ContainsNone, SameLabel, ask, invoke_traced

CAMPUS_ROUTE = [
    "какие у меня сегодня пары",
    "что у группы B26-CSE-01 завтра",
    "в какой аудитории у меня лабораторная по итп",
    "какие клубы по шахматам есть",
    "расскажи про клуб робототехники",
    "какие мероприятия в университете на этой неделе",
    "где находится 301 аудитория",
    "где столовая",
    "где можно распечатать документы",
    "what is my schedule tomorrow",
    "привет!",
    "что ты умеешь?",
]
CHATS_ROUTE = [
    "когда мидтерм по итп",
    "когда ближайший дедлайн по матану",
    "что писали в чатах про экзамен по дискре",
    "перенесли ли лекцию по компарч",
    "когда пересдача по английскому",
    "какие тесты были на этой неделе",
    "сколько сообщений в чате про дедлайны за месяц",
    "что такое did?",
    "what happened with the agla test",
    "кто-нибудь писал про смену белья в корпусе 9",
    "какие дедлайны на этой неделе",
    "what are the rules for retaking a midterm",
]
DOCS_ROUTE = [
    "сколько раз можно пересдавать экзамен",
    "как оформить академический отпуск",
    "за что могут отчислить",
    "как перейти с платного обучения на бюджет",
    "какие вступительные испытания в магистратуру",
    "как сдают кандидатские экзамены в аспирантуре",
    "кто преподает операционные системы",
    "сколько часов в зачетной единице",
    "what are the prerequisites of control theory",
    "кто директор университета",
]



def test_each_helper_has_the_rules_about_facts_and_its_own_part():
    chats, campus = roles.prompt("chats"), roles.prompt("campus")
    assert_test(LLMTestCase(input="", actual_output=chats), [ContainsAll(["helper of cAtIx", "search_userbot_chats", "After every tool result", "dates_in_text"], name="Chats")])
    assert_test(LLMTestCase(input="", actual_output=campus), [ContainsAll(["helper of cAtIx", "get_schedule", "InNoHassle"], name="Campus"), ContainsNone(["search_userbot_chats", "After every tool result"], name="NotTheChatRules")])
    docs = roles.prompt("docs")
    assert_test(LLMTestCase(input="", actual_output=docs), [ContainsAll(["helper of cAtIx", "search_wiki", "read_wiki", "newest"], name="Docs"), ContainsNone(["search_userbot_chats", "get_schedule"], name="NotTheOtherRules")])
    assert len(campus) < len(chats)


def test_the_supervisor_has_the_rules_of_conduct_and_none_of_the_tools():
    text = roles.SUPERVISOR
    assert_test(LLMTestCase(input="", actual_output=text), [ContainsAll(["Stay in this role", "Never advertise", "helpers"], name="Conduct"), ContainsNone(["search_chats", "query_db", "dates_in_text", "After every tool result"], name="NoToolRules")])
    assert len(text) < len(roles.prompt("chats"))


def test_the_tools_are_split_between_the_helpers():
    known = {t.name for t in TOOLS}
    chats, campus, docs = roles.ROLES["chats"].tools, roles.ROLES["campus"].tools, roles.ROLES["docs"].tools
    assert chats <= known and campus <= known and docs <= known, "a helper names a tool that does not exist"
    assert known == chats | campus | docs, "a tool belongs to no helper"
    assert "search_userbot_chats" not in campus and "get_schedule" not in chats
    assert docs == {"search_wiki", "read_wiki"}, "the documents have a helper of their own"


class ScriptedModel(FakeMessagesListChatModel):
    """Answers with the given messages in turn, whichever agent asks (the supervisor and the helpers share one model)."""

    def bind_tools(self, tools, **kwargs):
        return self


def _run(script: list[AIMessage], question="когда мидтерм по итп"):
    agent = build_agent(ScriptedModel(responses=script), guardrail=False)
    out = agent.invoke(
        {"messages": [{"role": "user", "content": question}]},
        {"configurable": {"thread_id": "t"}},
        context=AgentContext(),
    )
    return out, agent


def _ask(helper: str, question: str) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": helper, "args": {"question": question}, "id": "c1", "type": "tool_call"}])


def test_a_question_goes_to_the_helper_and_its_report_comes_back():
    out, _ = _run([
        _ask("ask_chats", "когда мидтерм по итп"),
        AIMessage(content="Мидтерм 22 октября, ссылка: https://invented.example/x"),  # the helper (no tools needed here)
        AIMessage(content="Мидтерм 22 октября."),  # the supervisor
    ])
    names = [m.name for m in out["messages"] if isinstance(m, ToolMessage)]
    assert names == ["ask_chats"]
    report = next(m for m in out["messages"] if isinstance(m, ToolMessage))
    assert "invented.example" not in report.content, "an invented link in a helper's report must be cut"
    assert report.artifact == {"tools": [], "calls": [], "results": []}
    assert final_answer(out["messages"], out.get("sources") or {}) == "Мидтерм 22 октября."


def test_the_helper_keeps_its_own_context_and_has_no_memory_between_calls():
    out, agent = _run([
        _ask("ask_campus", "какие клубы есть"),
        AIMessage(content="Клуб шахмат."),
        AIMessage(content="Есть клуб шахмат."),
    ])
    # The helper's messages are not in the supervisor's state: question, call, report, answer.
    assert [m.type for m in out["messages"]] == ["human", "ai", "tool", "ai"]
    state = agent.get_state({"configurable": {"thread_id": "t"}}).values
    assert len(state["messages"]) == 4


def test_a_blocked_helper_tool_name_is_not_one_the_supervisor_can_make_up():
    # The supervisor's own tool-call markup is checked against its tools (the helpers), not against the chat tools.
    from catix.agent.core import parse_text_tool_calls

    text = "<tool_call><function=ask_chats><parameter=question>когда мидтерм</parameter></function></tool_call>"
    assert parse_text_tool_calls(text, {"ask_chats", "ask_campus"})[0]["args"] == {"question": "когда мидтерм"}
    assert parse_text_tool_calls(text, {"search_chats"}) == []


@pytest.mark.model
@pytest.mark.parametrize("text", CHATS_ROUTE, ids=[t[:40] for t in CHATS_ROUTE])
def test_a_question_about_the_chats_goes_to_the_chats_helper(agent, text):
    answer = ask(agent, text)
    assert_test(LLMTestCase(input=text, actual_output="chats" if "ask_chats" in answer.helpers else ",".join(answer.helpers) or "none", expected_output="chats"), [SameLabel()])


@pytest.mark.model
@pytest.mark.parametrize("text", DOCS_ROUTE, ids=[t[:40] for t in DOCS_ROUTE])
def test_a_question_about_rules_programmes_or_admission_goes_to_the_docs_helper(agent, text):
    answer = ask(agent, text)
    assert_test(LLMTestCase(input=text, actual_output="docs" if "ask_docs" in answer.helpers else ",".join(answer.helpers) or "none", expected_output="docs"), [SameLabel()])


@pytest.mark.parametrize("text", CAMPUS_ROUTE[:-2], ids=[t[:40] for t in CAMPUS_ROUTE[:-2]])
def test_a_question_about_the_timetable_clubs_or_map_goes_to_the_campus_helper(agent, text):
    answer = ask(agent, text)
    assert_test(LLMTestCase(input=text, actual_output="campus" if "ask_campus" in answer.helpers else ",".join(answer.helpers) or "none", expected_output="campus"), [SameLabel()])


@pytest.mark.model
@pytest.mark.parametrize("text", CAMPUS_ROUTE[-2:], ids=[t[:40] for t in CAMPUS_ROUTE[-2:]])
def test_a_greeting_is_answered_by_the_supervisor_itself(agent, text):
    assert ask(agent, text).helpers == []


@pytest.mark.model
@pytest.mark.parametrize("text", ["Переведи на английский: добрый день", "Реши интеграл x^2 sin x dx"], ids=["translation", "maths"])
def test_an_off_topic_task_is_refused_in_the_language_of_the_user_without_a_helper(agent, text):
    answer = ask(agent, text)
    assert answer.helpers == [] and not __import__("re").search(r"[a-z]{4,} [a-z]{4,} [a-z]{4,}", answer.body.lower()), answer.body


def test_the_supervisor_cannot_cite_a_ref_that_no_helper_reported_in_this_turn():
    # m0 was found by an earlier question of the conversation; this turn's helper report carries no refs, but the supervisor wrote [m0].
    registry = {"m0": {"key": "live:1:1", "chat_title": "Analytical Geometry", "link": "https://t.me/c/1/1", "date": "2026-10-02T07:57:32+00:00", "author": None}}
    messages = [
        HumanMessage("кто такой бурмяков?"),
        _ask("ask_chats", "кто такой бурмяков?"),
        ToolMessage(content="Студенты упоминают Бурмякова, роль не названа.", tool_call_id="c1", name="ask_chats"),
        AIMessage(content="Бурмяков упоминается в чатах [m0]."),
    ]
    answer = final_answer(messages, registry)
    assert "Источники" not in answer and "Sources" not in answer and "[1]" not in answer, answer
    messages[2] = ToolMessage(content="Бурмяков рассказывал [m0].", tool_call_id="c1", name="ask_chats")
    assert "Analytical Geometry" in final_answer(messages, registry)  # the same ref, reported this turn, is honoured


@pytest.mark.model
def test_a_repeated_question_goes_to_the_helpers_again(agent):
    """The supervisor once copied its own earlier answer for the same question and called no helper (trace b7e0a84)."""
    config = {"configurable": {"thread_id": "repeat-test"}}
    context = AgentContext(user_telegram_id=-1)
    for _ in range(3):
        out = invoke_traced(agent, "что будет на этой неделе?", user_id=-1, context=context, thread_id=config["configurable"]["thread_id"])
        last_question = max(i for i, m in enumerate(out["messages"]) if m.type == "human")
        calls = [c["name"] for m in out["messages"][last_question:] if isinstance(m, AIMessage) for c in m.tool_calls]
        assert calls, "answered a repeated question from the conversation, with no helper"


def test_a_helper_must_call_a_tool_on_its_first_model_call_only():
    import types

    from catix.agent.core import LookUpFirstMiddleware

    class Req:
        def __init__(self, messages, tool_choice=None):
            self.messages, self.tool_choice = messages, tool_choice

        def override(self, **changes):
            clone = Req(self.messages)
            clone.__dict__.update(self.__dict__ | changes)
            return clone

    middleware = LookUpFirstMiddleware()
    first = middleware._first(Req([HumanMessage("что такое git")]))
    assert first.tool_choice == "required"
    after_a_tool_call = middleware._first(Req([HumanMessage("что такое git"), _ask("ask_chats", "x"), ToolMessage(content="r", tool_call_id="c1")]))
    assert after_a_tool_call.tool_choice is None  # later calls are free: the model may answer


def test_when_every_helper_failed_the_answer_says_so_instead_of_what_the_supervisor_made_up():
    from catix.agent.core import TOOL_FAILURE_ANSWER

    messages = [
        HumanMessage("Какие вступительные испытания в магистратуру?"),
        _ask("ask_docs", "Какие вступительные испытания в магистратуру?"),
        ToolMessage(content=TOOL_FAILURE_ANSWER, tool_call_id="c1", name="ask_docs"),
        AIMessage(content="Вступительных испытаний нет, приём по портфолио."),
    ]
    assert final_answer(messages, {}) == TOOL_FAILURE_ANSWER
    messages[2] = ToolMessage(content="Компьютерное тестирование [m0].", tool_call_id="c1", name="ask_docs")
    messages[3] = AIMessage(content="Компьютерное тестирование [m0].")
    assert "тестирование" in final_answer(messages, {"m0": {"wiki": True, "title": "Правила приема", "clause": "", "link": None, "trust": "official"}})
