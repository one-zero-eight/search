"""The agent's tools and prompt (agent/core.py, agent/roles.py).

Without a model: the tools are the ones the agent is given, and a citation is honoured only for a ref this turn's retrieval
results gave. With the model: the agent searches for facts, reads the asker's own data directly, and answers greetings and
refusals itself.
"""

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from catix.agent import roles
from catix.agent.core import build_agent, final_answer
from catix.agent.tools import TOOLS, AgentContext
from tests.helpers import SameLabel, ask, invoke_traced

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
    "что пишут в чатах про did?",
    "what happened with the agla test",
    "кто-нибудь писал про смену белья в корпусе 9",
    "какие дедлайны на этой неделе",
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
    "what are the rules for retaking a midterm",
    "какие есть олимпиады?",  # (the sites: the chats helper alone was asked it and found students' talk)
    "а что в медиа иннополис?",
]
WHAT_IS_ROUTE = ["что такое did?", "кто такой Тьюринг", "что такое kubernetes"]
NEWS_ROUTE = [
    "какие последние новости?",
    "какие последние новости в иннополисе?",
]



def test_the_agent_has_every_tool_there_is():
    known = {t.name for t in TOOLS}
    assert roles.MAIN_TOOLS <= known, "the agent names a tool that does not exist"
    assert known == roles.MAIN_TOOLS, "retired tools must not remain registered"
    assert not {"get_schedule", "find_room", "get_clubs", "get_university_events", "book_room", "sport_checkin"} & known
    assert not {"search_chats", "search_userbot_chats", "search_wiki", "search_my_moodle", "ask_docs", "ask_chats"} & known
    assert {"search", "read_wiki", "read_chats"} <= known
    assert roles.READ_TOOLS <= roles.MAIN_TOOLS and roles.API_TOOLS <= roles.MAIN_TOOLS
    assert "act_api_tool" not in known


class ScriptedModel(FakeMessagesListChatModel):
    """Answers with the given messages in turn."""

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


def _ask(tool: str, question: str) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": tool, "args": {"question": question}, "id": "c1", "type": "tool_call"}])


def test_an_answer_without_a_tool_call_is_the_whole_turn(monkeypatch):
    from catix.db import store

    monkeypatch.setattr(store, "visible_chats", lambda *a: [])
    out, _ = _run([AIMessage(content="Привет! Чем помочь?")], "привет")
    assert [m.type for m in out["messages"]] == ["human", "ai"]
    assert final_answer(out["messages"], out.get("sources") or {}).answer == "Привет! Чем помочь?"


@pytest.mark.model
@pytest.mark.parametrize("text", CHATS_ROUTE + DOCS_ROUTE + NEWS_ROUTE + WHAT_IS_ROUTE, ids=lambda t: t[:40])
def test_a_question_about_facts_is_searched(agent, text):
    answer = ask(agent, text)
    assert_test(LLMTestCase(input=text, actual_output="search" if "search" in answer.tool_names else ",".join(answer.tool_names) or "none", expected_output="search"), [SameLabel()])


@pytest.mark.model
@pytest.mark.parametrize("text", CAMPUS_ROUTE[:-2], ids=[t[:40] for t in CAMPUS_ROUTE[:-2]])
def test_a_question_about_the_timetable_clubs_or_map_uses_direct_reads(agent, text):
    answer = ask(agent, text)
    assert {"search_api_tools", "call_api_tool", "get_my_schedule"} & set(answer.tool_names), answer.tool_names


@pytest.mark.model
@pytest.mark.parametrize("text", CAMPUS_ROUTE[-2:], ids=[t[:40] for t in CAMPUS_ROUTE[-2:]])
def test_a_greeting_is_answered_by_the_agent_itself(agent, text):
    assert ask(agent, text).tool_names == []


@pytest.mark.model
@pytest.mark.parametrize("text", ["Переведи на английский: добрый день", "Реши интеграл x^2 sin x dx"], ids=["translation", "maths"])
def test_an_off_topic_task_is_refused_in_the_language_of_the_user_without_a_tool(agent, text):
    answer = ask(agent, text)
    assert answer.tool_names == [] and not __import__("re").search(r"[a-z]{4,} [a-z]{4,} [a-z]{4,}", answer.body.lower()), answer.body


def test_the_agent_cannot_cite_a_ref_that_this_turns_results_did_not_give():
    # m0 was found by an earlier question of the conversation; this turn's result carries no refs, but the agent wrote [m0].
    registry = {"m0": {"key": "live:1:1", "chat_title": "Analytical Geometry", "link": "https://t.me/c/1/1", "date": "2026-10-02T07:57:32+00:00", "author": None}}
    messages = [
        HumanMessage("кто такой бурмяков?"),
        _ask("search", "кто такой бурмяков?"),
        ToolMessage(content='{"total": 0, "chat": {"total": 0, "messages": []}}', tool_call_id="c1", name="search"),
        AIMessage(content="Бурмяков упоминается в чатах [m0]."),
    ]
    answer = final_answer(messages, registry)
    assert answer.sources == [] and "[1]" not in answer.answer, answer
    messages[2] = ToolMessage(content='{"total": 1, "chat": {"messages": [{"ref": "m0", "text": "Бурмяков рассказывал"}]}}', tool_call_id="c1", name="search")
    assert final_answer(messages, registry).sources[0].title == "Analytical Geometry"  # a ref given this turn is honoured


def test_a_ref_in_a_result_that_is_not_a_retrieval_tool_is_not_honoured():
    registry = {"m0": {"key": "live:1:1", "chat_title": "Analytical Geometry", "link": "https://t.me/c/1/1", "date": "2026-10-02T07:57:32+00:00", "author": None}}
    messages = [
        HumanMessage("кто такой бурмяков?"),
        _ask("get_my_schedule", "x"),
        ToolMessage(content='{"ref": "m0"}', tool_call_id="c1", name="get_my_schedule"),
        AIMessage(content="Бурмяков упоминается в чатах [m0]."),
    ]
    assert final_answer(messages, registry).sources == []


@pytest.mark.model
def test_a_repeated_question_is_searched_again(agent):
    """The agent once copied its own earlier answer for the same question and called no tool (trace b7e0a84)."""
    config = {"configurable": {"thread_id": "repeat-test"}}
    context = AgentContext(user_telegram_id=-1)
    for _ in range(3):
        out = invoke_traced(agent, "что будет на этой неделе?", user_id=-1, context=context, thread_id=config["configurable"]["thread_id"])
        last_question = max(i for i, m in enumerate(out["messages"]) if m.type == "human")
        calls = [c["name"] for m in out["messages"][last_question:] if isinstance(m, AIMessage) for c in m.tool_calls]
        assert calls, "answered a repeated question from the conversation, with no tool"


def test_when_every_tool_failed_the_answer_says_so_instead_of_what_the_agent_made_up():
    from catix.agent.core import TOOL_FAILURE_ANSWER

    messages = [
        HumanMessage("Какие вступительные испытания в магистратуру?"),
        _ask("search", "Какие вступительные испытания в магистратуру?"),
        ToolMessage(content=TOOL_FAILURE_ANSWER, tool_call_id="c1", name="search"),
        AIMessage(content="Вступительных испытаний нет, приём по портфолио."),
    ]
    assert final_answer(messages, {}).answer == TOOL_FAILURE_ANSWER
    messages[2] = ToolMessage(content='{"ref": "m0"}', tool_call_id="c1", name="search")
    messages[3] = AIMessage(content="Компьютерное тестирование [m0].")
    assert "тестирование" in final_answer(messages, {"m0": {"wiki": True, "title": "Правила приема", "clause": "", "link": None, "trust": "official"}}).answer


def test_refs_the_agent_left_out_go_under_the_answer():
    messages = [
        HumanMessage("Какое вступительное испытание в магистратуру?"),
        _ask("search", "Какое вступительное испытание в магистратуру?"),
        ToolMessage(content='{"ref": "m7"} {"ref": "m9"}', tool_call_id="c1", name="search"),
        AIMessage(content="Компьютерное тестирование, минимальный балл 40."),
    ]
    rules = {"wiki": True, "title": "Правила приема 2026/2027", "clause": "", "link": "https://innopolis.university/r.pdf", "trust": "official"}
    answer = final_answer(messages, {"m7": rules, "m9": rules})
    assert answer.answer == "Компьютерное тестирование, минимальный балл 40. [1]"
    assert len(answer.sources) == 1
    assert answer.sources[0].number == 1 and answer.sources[0].title == "Правила приема 2026/2027"
    assert answer.sources[0].url == "https://innopolis.university/r.pdf" and answer.sources[0].kind == "official_document"


def test_a_run_of_refs_keeps_at_most_five_sources():
    """Twenty-six messages cited for one sentence all went under the answer: 28 sources ("что такое пчз?"). A run of refs keeps
    its first MAX_RUN sources, in the text and under it; two clauses of one document are one source."""
    from catix.agent.sources import MAX_RUN

    registry = {f"m{i}": {"wiki": True, "title": f"Документ {i}", "clause": "", "link": f"https://innopolis.university/{i}.pdf", "trust": "official"} for i in range(8)}
    registry["m8"] = {**registry["m0"], "clause": "п. 2"}
    run = "".join(f"[m{i}]" for i in (0, 8, *range(1, 8)))
    results = " ".join(f'{{"ref": "m{i}"}}' for i in range(9))
    messages = [
        HumanMessage("что такое пчз?"),
        _ask("search", "что такое пчз?"),
        ToolMessage(content=results, tool_call_id="c1", name="search"),
        AIMessage(content=f"ПЧЗ — канал первокурсников {run}."),
    ]
    answer = final_answer(messages, registry)
    assert answer.answer == "ПЧЗ — канал первокурсников. [1][2][3][4][5]", answer
    assert len(answer.sources) == MAX_RUN == 5
    assert [source.url for source in answer.sources] == [f"https://innopolis.university/{i}.pdf" for i in range(MAX_RUN)]
    messages[3] = AIMessage(content=f"ПЧЗ — канал [m0][m1], первокурсников {run}.")
    answer = final_answer(messages, registry)
    assert "канал [1][2], первокурсников [1][2][3][4][5]." in answer.answer  # two runs, each cut by itself


def test_an_answer_without_refs_is_asked_again_only_when_the_tools_gave_sources():
    from catix.agent.core import CiteMiddleware

    class Req:
        def __init__(self, messages):
            self.messages = messages

        def override(self, **changes):
            clone = Req(self.messages)
            clone.__dict__.update(changes)
            return clone

    found = ToolMessage(content='{"results": [{"ref": "m3", "text": "40 баллов"}]}', tool_call_id="c1", name="search")
    nothing = ToolMessage(content='{"results": []}', tool_call_id="c1", name="search")
    calls = []

    def model(request):
        calls.append(request.messages)
        return AIMessage(content="Минимальный балл 40." if len(calls) == 1 else "Минимальный балл 40 [m3].")

    question = HumanMessage("минимальный балл в магистратуру")
    assert CiteMiddleware().wrap_model_call(Req([question, _ask("search", "x"), found]), model).text == "Минимальный балл 40 [m3]."
    assert len(calls) == 2 and "ref" in calls[1][-1].text
    calls.clear()
    assert CiteMiddleware().wrap_model_call(Req([question, _ask("search", "x"), nothing]), model).text == "Минимальный балл 40."
    assert len(calls) == 1
