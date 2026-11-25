"""How the supervisor's context is kept small: old lookup results are pruned at a new question, the summary trigger counts the
whole prompt, and a failing summarizer never fails the question. No model server: fake models only."""

import asyncio
import json
import logging
import time
import types
from copy import deepcopy
from typing import Any

import httpx
import openai
import pytest
from langchain.agents.middleware.types import ModelResponse
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, RemoveMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from pydantic import Field

from catix.agent import api_context, api_tools, core, roles
from catix.agent.api_preflight import ApiPreflightMiddleware, _discovered_schema
from catix.agent.calendar_approval import LOCAL_CALENDAR_APPROVAL
from catix.agent.feedback_tools import FEEDBACK_APPROVAL
from catix.agent.core import (
    OMITTED,
    PRUNED_RESULT,
    SUMMARY_INPUT_TOKENS,
    LoggingMiddleware,
    PruneOldToolResults,
    TurnStartSummarization,
    estimate_tokens,
    prompt_floor,
)
from catix.agent.tools import TOOLS, AgentContext
from catix.innohassle.mcp_access import CONFIRMATION_TOOLS
from catix.settings import settings


def call(tool: str, ident: str, /, **args) -> dict:
    return {"name": tool, "args": args, "id": ident, "type": "tool_call"}


def turn(n: int, results: list[tuple[str, dict, str]], answer: str = "Ответ.", artifacts: dict | None = None) -> list[BaseMessage]:
    """One finished question: a user message, one model call with a tool call per result, the results, the answer.
    `results`: (tool name, arguments, content); `artifacts`: tool call id -> artifact of its result."""
    calls = [call(tool, f"c{n}-{i}", **args) for i, (tool, args, _) in enumerate(results)]
    return [
        HumanMessage(f"вопрос {n}", id=f"h{n}"),
        *([AIMessage(content="", tool_calls=calls, id=f"a{n}")] if calls else []),
        *[ToolMessage(content=content, tool_call_id=c["id"], name=c["name"], id=f"t{n}-{i}", artifact=(artifacts or {}).get(c["id"]))
          for i, (c, (_, _, content)) in enumerate(zip(calls, results))],
        AIMessage(content=answer, id=f"r{n}"),
    ]


def docs_search(text: str = "Автобус идёт от кампуса [m1].") -> tuple[str, dict, str]:
    return ("search", {"queries": ["как добраться"]}, text)


def tool_results(messages: list[BaseMessage]) -> dict[str, ToolMessage]:
    return {m.id: m for m in messages if isinstance(m, ToolMessage)}


def apply(messages: list[BaseMessage], update: dict | None) -> list[BaseMessage]:
    """The state after a middleware's update, as the graph's reducer makes it."""
    return add_messages(messages, update["messages"]) if update else messages


def assert_paired(messages: list[BaseMessage]) -> None:
    """What the model API demands: every tool call is answered by a tool message right after it, and none without a call."""
    open_calls: set[str] = set()
    for m in messages:
        if isinstance(m, ToolMessage):
            assert m.tool_call_id in open_calls, f"tool result {m.id} without its call"
            open_calls.discard(m.tool_call_id)
        else:
            assert not open_calls, f"calls without results: {open_calls}"
            open_calls = {c["id"] for c in m.tool_calls} if isinstance(m, AIMessage) else set()
    assert not open_calls


# --- what is pruned -------------------------------------------------------------------------------------------------------

BOOKING = ("call_api_tool", {"name": "rooms_book_room", "arguments": {"room_id": "314"}}, json.dumps({"done": True}))
UNKNOWN = ("call_api_tool", {"name": "sport_sport_checkin", "arguments": {}}, json.dumps({"done": None, "outcome": "unknown"}))
READ = ("call_api_tool", {"name": "rooms_get_free_rooms", "arguments": {}}, json.dumps({"rooms": ["314"] * 300}))


def history() -> list[BaseMessage]:
    return [
        *turn(1, [docs_search("доклад " * 300)]),
        *turn(2, [("search_api_tools", {"query": "rooms"}, json.dumps({"tools": ["x"] * 400}))]),
        *turn(3, [READ]),
        *turn(4, [BOOKING]),
        *turn(5, [UNKNOWN]),
        *turn(6, [("get_my_schedule", {}, json.dumps({"classes": ["y"] * 300})),
                  ("get_my_ai_calendar", {}, json.dumps({"events": []})),
                  ("read_chats", {"chat_id": 1}, "[]"),
                  ("get_my_moodle", {"kind": "deadlines"}, "{}")]),
        *turn(7, [("add_to_ai_calendar", {"title": "t"}, json.dumps({"done": True})),
                  ("update_ai_calendar", {"calendar_event_id": 1}, json.dumps({"done": True})),
                  ("remove_from_ai_calendar", {"calendar_event_id": 1}, json.dumps({"done": True}))]),
        *turn(8, [("read_attachment", {"attachment_id": "f"}, "страница " * 400), ("read_attachment", {"attachment_id": "f", "question": "?"}, "картинка")]),
        *turn(9, [docs_search("Забронировано.")]),
    ]


KEPT = {"t4-0", "t5-0", "t7-0", "t7-1", "t7-2", "t8-0", "t8-1"}


def test_the_results_of_lookups_are_pruned_and_actions_and_files_stay_when_a_question_arrives():
    before = [*history(), HumanMessage("новый вопрос", id="h10")]
    after = apply(before, PruneOldToolResults().before_model({"messages": before}, None))
    results = tool_results(after)
    pruned = {i for i, m in results.items() if m.content == PRUNED_RESULT}
    assert pruned == {"t1-0", "t2-0", "t3-0", "t6-0", "t6-1", "t6-2", "t6-3", "t9-0"}
    assert {i for i in results if i not in pruned} == KEPT
    for i in KEPT:
        assert results[i].content == tool_results(before)[i].content  # untouched
    assert estimate_tokens(after) < estimate_tokens(before)


def test_pruning_keeps_every_tool_call_answered_in_place_and_changes_nothing_else():
    before = [*history(), HumanMessage("новый вопрос", id="h10")]
    after = apply(before, PruneOldToolResults().before_model({"messages": before}, None))
    assert_paired(after)
    assert [(type(m), m.id) for m in after] == [(type(m), m.id) for m in before]  # same messages, same order
    for old, new in zip(before, after):
        if isinstance(old, ToolMessage):
            assert (new.tool_call_id, new.name, new.status) == (old.tool_call_id, old.name, old.status)
        else:
            assert new == old


def test_pruning_is_once_and_idempotent():
    messages = [*history(), HumanMessage("новый вопрос", id="h10")]
    middleware = PruneOldToolResults()
    once = apply(messages, middleware.before_model({"messages": messages}, None))
    assert middleware.before_model({"messages": once}, None) is None  # a stub is not stubbed again
    assert apply(once, middleware.before_model({"messages": once}, None)) == once


def test_only_a_new_question_prunes_and_never_the_results_of_the_run_in_progress():
    messages = [*turn(1, [READ]), HumanMessage("вопрос 2", id="h2"),
                AIMessage(content="", tool_calls=[call("get_my_schedule", "c2")], id="a2"),
                ToolMessage(content="{}", tool_call_id="c2", name="get_my_schedule", id="t2")]
    assert PruneOldToolResults().before_model({"messages": messages}, None) is None  # the last message is a tool result
    assert PruneOldToolResults().before_model({"messages": []}, None) is None
    asked = [*messages[:-1]]
    assert PruneOldToolResults().before_model({"messages": asked}, None) is None  # (ends in a call, not in a question)
    # the next question prunes both, and its own (none yet) cannot be among them
    after = apply([*messages, AIMessage(content="Готово.", id="r2"), HumanMessage("вопрос 3", id="h3")],
                  PruneOldToolResults().before_model({"messages": [*messages, AIMessage(content="Готово.", id="r2"),
                                                                    HumanMessage("вопрос 3", id="h3")]}, None))
    assert {m.content for m in after if isinstance(m, ToolMessage)} == {PRUNED_RESULT}


def test_a_call_that_cannot_be_matched_and_a_result_without_an_id_stay():
    orphan = ToolMessage(content=READ[2], tool_call_id="nobody", name="call_api_tool", id="orphan")
    no_id = ToolMessage(content="{}", tool_call_id="c1-0", name="get_my_schedule")
    messages = [HumanMessage("вопрос 1", id="h1"), AIMessage(content="", tool_calls=[call("get_my_schedule", "c1-0")], id="a1"),
                no_id, orphan, AIMessage(content="Ответ.", id="r1"), HumanMessage("вопрос 2", id="h2")]
    assert PruneOldToolResults.before_model(PruneOldToolResults(), {"messages": messages}, None) is None


def test_every_tool_of_the_supervisor_is_either_pruned_or_kept_on_purpose():
    kept = {"read_attachment"} | LOCAL_CALENDAR_APPROVAL.keys() | FEEDBACK_APPROVAL.keys()
    assert roles.MAIN_TOOLS <= core.LOOKUP_RESULTS | kept, "a new tool: are its results looked up afresh, or evidence?"
    assert not core.LOOKUP_RESULTS & kept
    assert core.LOOKUP_RESULTS <= {t.name for t in TOOLS}
    assert {"rooms_book_room", "sport_sport_checkin"} <= CONFIRMATION_TOOLS


# --- the graph ------------------------------------------------------------------------------------------------------------

class Seen(FakeMessagesListChatModel):
    seen: list = Field(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        return self.bind(tools=tools, **kwargs)

    def _generate(self, messages, *args, **kwargs):
        self.seen.append(deepcopy(messages))
        return super()._generate(messages, *args, **kwargs)


@pytest.fixture
def no_markup_ban(monkeypatch):
    monkeypatch.setattr(core, "tool_call_token", lambda: None)


@pytest.mark.parametrize("asynchronous", [False, True])
def test_a_new_question_prunes_the_stored_thread_and_the_model_sees_the_stubs(no_markup_ban, asynchronous):
    model = Seen(responses=[AIMessage(content="Ответ.")])
    agent = core.build_agent(model, guardrail=False, checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "prune"}}
    seeded = history()
    agent.update_state(config, {"messages": seeded, "sources": {"m1": {"url": "https://example.org"}}}, as_node="model")
    inputs = {"messages": [HumanMessage("и ещё вопрос")]}
    out = asyncio.run(agent.ainvoke(inputs, config, context=AgentContext())) if asynchronous else agent.invoke(inputs, config, context=AgentContext())
    stored = agent.get_state(config).values
    results = tool_results(stored["messages"])
    assert {i for i, m in results.items() if m.content != PRUNED_RESULT} == KEPT
    assert_paired(stored["messages"])
    assert stored["sources"] == {"m1": {"url": "https://example.org"}}  # the sources of the conversation are not touched
    assert [m.content for m in out["messages"][-2:]] == ["и ещё вопрос", "Ответ."]
    sent = model.seen[0]  # the one model call: it was sent the stubs
    assert {m.content for m in sent if isinstance(m, ToolMessage)} >= {PRUNED_RESULT, BOOKING[2]}
    assert sum(isinstance(m, ToolMessage) and m.content == PRUNED_RESULT for m in sent) == 8
    assert all("доклад" not in str(m.content) for m in sent)
    assert_paired(sent)


def test_the_prune_runs_before_the_summary_in_the_graph(no_markup_ban):
    agent = core.build_agent(Seen(responses=[AIMessage(content="x")]), guardrail=False)
    order = [n for n in agent.get_graph().nodes if n.endswith(".before_model")]
    assert order.index("PruneOldToolResults.before_model") < order.index("TurnStartSummarization.before_model")


# --- the other middleware on a pruned history -------------------------------------------------------------------------------

def stubbed(*turns: list[BaseMessage]) -> list[BaseMessage]:
    """The turns, pruned as a following question would prune them."""
    messages = [m for t in turns for m in t] + [HumanMessage("вопрос", id="hx")]
    return apply(messages, PruneOldToolResults().before_model({"messages": messages}, None))[:-1]


def test_a_schema_found_in_an_earlier_question_is_gone_and_the_preflight_asks_for_it_once(monkeypatch):
    schema = {"type": "object", "properties": {"training_id": {"type": "integer"}, "cancel": {"type": "boolean", "default": False}},
              "required": ["training_id"]}
    training = {"training_id": 48591, "name": "Frisbee", "starts_at": "2026-11-09T08:00:00+03:00",
                "ends_at": "2026-11-09T10:00:00+03:00", "place": "[SC] Big Hall", "date": "2026-11-09 Mon", "time": "08:00-10:00"}
    old = stubbed(turn(1, [("search_api_tools", {"query": "sport"}, json.dumps({"tools": [{"name": "sport_sport_checkin", "inputSchema": schema}]})),
                           ("call_api_tool", {"name": "sport_get_training", "arguments": {"training_id": 48591}}, json.dumps({"training": training}))]))
    assert [m.content for m in old if isinstance(m, ToolMessage)] == [PRUNED_RESULT] * 2
    assert _discovered_schema(old, "sport_sport_checkin") is None  # a stub is not a catalogue (and does not raise)
    action = call("call_api_tool", "write", name="sport_sport_checkin", arguments={"training_id": 48591})
    state = {"messages": [*old, HumanMessage("запиши меня", id="h2"), AIMessage(content="", tool_calls=[action], id="a2")]}
    sent = []

    def request(method, payload, token=None, **credentials):
        sent.append(method)
        return {"tools": [{"name": "sport_sport_checkin", "inputSchema": schema}]} if method == "search_tools" else {"training": training}

    async def arequest(*args, **kwargs):
        return request(*args, **kwargs)

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    monkeypatch.setattr(api_tools.mcp_client, "request", arequest)
    runtime = types.SimpleNamespace(context=AgentContext(innohassle_token=settings.llm_api_key, sport_token=settings.llm_api_key))
    result = ApiPreflightMiddleware().after_model(state, runtime)
    assert "jump_to" not in result and result["api_prepared"][0]["target"] == "sport_sport_checkin"
    assert sent == ["search_tools", "call_tool"]  # the catalogue and the training are asked for again, once each
    assert api_context.from_messages("sport_sport_checkin", {"training_id": 48591}, state["messages"]) is None  # nothing of the earlier turn


# --- the estimator and the trigger ----------------------------------------------------------------------------------------

def summarizer(model=None, **kwargs) -> TurnStartSummarization:
    model = model or ChatOpenAI(base_url="http://127.0.0.1:1/v1", api_key="x", model="m")
    kwargs.setdefault("floor_tokens", prompt_floor(real_tools()))
    return TurnStartSummarization(model, trigger=("tokens", settings.agent_summarize_trigger_tokens),
                                  keep=("messages", settings.agent_summarize_keep_messages), **kwargs)


def real_tools() -> list:
    return core.agent_tools()


def real_like_chat(questions: int, *, big: bool = True) -> list[BaseMessage]:
    """The shape of the long real chat (Phoenix trace 7fb329d3…): eight short questions to the docs helper, then one that read
    the catalogue three times, an API three times and the schedule (33k characters of tool results at 55% of the prompt)."""
    messages: list[BaseMessage] = []
    for n in range(1, questions + 1):
        if big and n == 8:
            results = [("search_api_tools", {"query": f"q{i}"}, "x" * 5400) for i in range(3)]
            results += [("call_api_tool", {"name": "rooms_get_free_rooms", "arguments": {}}, "y" * 2000) for _ in range(3)]
            results += [("get_my_schedule", {}, "z" * 7200)]
            messages += turn(n, results, "Вот что нашлось: " + "расписание " * 55)
        else:
            messages += turn(n, [docs_search("Автобус идёт от кампуса. " * 26 + "[m1]")], "Автобус идёт от кампуса. " * 24 + "[m1]")
    return messages


def test_the_estimate_counts_tool_calls_and_results_and_the_floor_the_system_prompt_and_schemas():
    result = ToolMessage(content="я" * 5000, tool_call_id="c", name="get_my_schedule")
    assert estimate_tokens([result]) >= 5000 / core.CHARS_PER_TOKEN
    calls = AIMessage(content="", tool_calls=[call("search", "c", queries=["мидтерм " * 200])])
    assert estimate_tokens([calls]) >= 1600 / core.CHARS_PER_TOKEN
    floor = prompt_floor(real_tools())
    assert 6000 <= floor <= 8500  # real: 2.9k of system prompt and 3.2k of tool schemas
    assert prompt_floor(real_tools()[:-1]) < floor and prompt_floor([]) < floor // 2


def test_a_chat_like_the_real_one_triggers_the_summary_and_a_short_chat_does_not():
    middleware = summarizer()
    trigger = settings.agent_summarize_trigger_tokens
    question = HumanMessage("новый вопрос", id="hq")
    long = [*real_like_chat(9), question]
    assert middleware.token_counter(long) > trigger  # 20k of the real 21.7k at question 9
    short = [*real_like_chat(3), question]
    assert middleware.token_counter(short) < trigger
    assert not middleware._should_summarize(short, middleware.token_counter(short))
    assert middleware._should_summarize(long, middleware.token_counter(long))
    assert middleware.token_counter(long) == estimate_tokens(long) + prompt_floor(real_tools())


def test_a_long_chat_whose_old_results_are_pruned_stays_under_the_trigger():
    middleware = summarizer()
    long = [*real_like_chat(9), HumanMessage("новый вопрос", id="hq")]
    pruned = apply(long, PruneOldToolResults().before_model({"messages": long}, None))
    assert middleware.token_counter(pruned) < settings.agent_summarize_trigger_tokens < middleware.token_counter(long)
    assert middleware.token_counter(pruned) < 0.7 * middleware.token_counter(long)


def test_the_trigger_leaves_room_for_the_answer_and_for_the_results_of_the_question():
    window, answer = 32768, settings.llm_plan_max_tokens
    room = window - answer - settings.agent_summarize_trigger_tokens
    assert room >= 10000  # a schedule, a catalogue search and an API read were 11k tokens (3.7k + 4.2k + 2.9k) in a real chat
    assert settings.agent_summarize_trigger_tokens > prompt_floor(real_tools()) + 3000  # a question and an answer do not trigger it


def test_the_tokens_the_last_call_reported_do_not_decide_whether_to_summarize():
    """The reported usage counts the results that were just pruned; with the trigger it would summarize every question."""
    middleware = summarizer()
    last = AIMessage(content="Ответ.", id="r1", usage_metadata={"input_tokens": 30000, "output_tokens": 5, "total_tokens": 30005},
                     response_metadata={"model_provider": "openai"})
    messages = [HumanMessage("вопрос", id="h1"), last, HumanMessage("ещё", id="h2")]
    assert not middleware._should_summarize(messages, middleware.token_counter(messages))


def test_the_supervisors_model_is_asked_for_usage_when_streaming(monkeypatch):
    made: list[dict] = []

    class Recording(ChatOpenAI):
        def __init__(self, **kwargs):
            made.append(kwargs)
            super().__init__(**kwargs)

    monkeypatch.setattr(core, "ChatOpenAI", Recording)
    core.build_agent(guardrail=False)
    assert made[0]["stream_usage"] is True and made[0]["max_tokens"] == settings.llm_max_tokens  # [0]: the supervisor's own


def test_the_log_of_a_call_says_what_the_server_counted(caplog):
    request = types.SimpleNamespace(messages=[HumanMessage("вопрос")])
    counted = AIMessage(content="x", usage_metadata={"input_tokens": 1234, "output_tokens": 1, "total_tokens": 1235})
    with caplog.at_level(logging.INFO, logger="catix.agent"):
        LoggingMiddleware()._log_model(request, ModelResponse(result=[counted]), time.monotonic())
        LoggingMiddleware()._log_model(request, AIMessage(content="x"), time.monotonic())
    first, second = [r.getMessage() for r in caplog.records]
    assert "the server counted 1234 prompt tokens" in first and "server counted" not in second


# --- the summarizer -------------------------------------------------------------------------------------------------------

class Summarizer(BaseChatModel):
    """Writes a fixed summary, or raises `error`; keeps the prompts it was sent."""

    error: Any = None
    prompts: list = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "summarizer"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.prompts.append(str(messages[-1].content))
        if self.error is not None:
            raise self.error
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="Студент спрашивает про автобус."))])


def overflow() -> Exception:
    request = httpx.Request("POST", "http://127.0.0.1:1/v1/chat/completions")
    message = ("This model's maximum context length is 32768 tokens. However, you requested 500 output tokens and your prompt "
               "contains at least 32269 input tokens, for a total of at least 32769 tokens. (parameter=input_tokens, value=32269)")
    return openai.BadRequestError(message, response=httpx.Response(400, request=request), body={"message": message, "code": 400})


def connection() -> Exception:
    return openai.APIConnectionError(request=httpx.Request("POST", "http://127.0.0.1:1/v1/chat/completions"))


def messy_history() -> list[BaseMessage]:
    """What the summarizer must not be sent: the catalogue, the schedule, an API read and a tool call with nothing said."""
    return [
        *turn(1, [docs_search("Отчёт поиска. " * 200)], "Автобус идёт от кампуса."),
        *turn(2, [("search_api_tools", {"query": "rooms"}, "КАТАЛОГ " * 3000), ("get_my_schedule", {}, "РАСПИСАНИЕ " * 3000),
                  READ[:2] + ("ВЫДАЧА " * 3000,)], "Вот ваше расписание."),
        *turn(3, [BOOKING], "Забронировано."),
        HumanMessage("и ещё один вопрос", id="h4"),
    ]


def small_summarizer(model, **kwargs) -> TurnStartSummarization:
    middleware = TurnStartSummarization(model, trigger=("tokens", 100), keep=("messages", 4), **kwargs)
    middleware._summary_model = model  # (no retries with their pauses: a failing model is the case)
    return middleware


def test_the_summarizer_is_sent_the_questions_and_answers_and_not_the_tool_results():
    model = Summarizer()
    middleware = small_summarizer(model)
    update = middleware.before_model({"messages": messy_history()}, None)
    assert update is not None
    prompt = model.prompts[0]
    assert "вопрос 1" in prompt and "Автобус идёт от кампуса." in prompt and "Вот ваше расписание." in prompt
    for forbidden in ("КАТАЛОГ", "РАСПИСАНИЕ", "ВЫДАЧА", "Забронировано.\"}", "Отчёт поиска."):
        assert forbidden not in prompt
    assert estimate_tokens([HumanMessage(prompt)]) < SUMMARY_INPUT_TOKENS * 1.1
    assert "Студент спрашивает про автобус." in update["messages"][1].content


def test_a_prompt_larger_than_the_budget_keeps_the_newest_part_and_never_goes_over_it():
    model = Summarizer()
    middleware = small_summarizer(model)
    many = [m for n in range(1, 120) for m in turn(n, [docs_search("Старый отчёт. " * 80)], f"Ответ номер {n}. " + "слово " * 150)]
    kept = middleware._trim_messages_for_summary([*many, HumanMessage("и ещё", id="hz")])
    assert estimate_tokens(kept) <= SUMMARY_INPUT_TOKENS
    assert kept[-1].content == "и ещё" and "Ответ номер 119." in kept[-2].content
    assert not any("вопрос 1" == m.content or "Ответ номер 1." in str(m.content) for m in kept)  # the oldest are dropped
    # one message alone larger than all of it is cut, not sent whole
    huge = middleware._trim_messages_for_summary([HumanMessage("я" * 400_000, id="h1")])
    assert len(huge) == 1 and estimate_tokens(huge) <= SUMMARY_INPUT_TOKENS


def test_pruned_reports_are_not_sent_to_the_summarizer_as_if_they_said_something():
    middleware = small_summarizer(Summarizer())
    kept = middleware._trim_messages_for_summary(stubbed(turn(1, [docs_search("Отчёт.")]), turn(2, [BOOKING])))
    assert [type(m).__name__ for m in kept] == ["HumanMessage", "AIMessage", "HumanMessage", "AIMessage"]
    assert all(PRUNED_RESULT not in str(m.content) for m in kept)


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("error", [overflow, connection, lambda: RuntimeError("boom")], ids=["overflow-400", "connection", "other"])
def test_when_the_summarizer_fails_the_question_goes_on_with_the_earlier_messages_dropped(error, asynchronous, caplog):
    model = Summarizer(error=error())
    middleware = small_summarizer(model)
    history = messy_history()
    with caplog.at_level(logging.WARNING, logger="catix.agent"):
        update = (asyncio.run(middleware.abefore_model({"messages": history}, None)) if asynchronous
                  else middleware.before_model({"messages": history}, None))
    assert model.prompts, "the summarizer was tried"
    assert "the summary of the conversation failed" in caplog.text
    first, *rest = update["messages"]
    assert isinstance(first, RemoveMessage)
    placeholder, *kept = rest
    assert isinstance(placeholder, HumanMessage) and OMITTED in placeholder.content
    assert kept == history[-len(kept):] and len(kept) >= settings.agent_summarize_keep_messages
    assert isinstance(kept[-1], HumanMessage) and kept[-1].content == "и ещё один вопрос"  # the new question is kept
    assert_paired(rest)


def test_the_messages_kept_never_split_a_tool_call_from_its_results():
    """Four messages from the end would start at the second of two results: the call with both stays."""
    history = [*turn(1, [docs_search()]), *turn(2, [("get_my_schedule", {}, "{}"), ("get_my_ai_calendar", {}, "{}")]), HumanMessage("новый", id="h3")]
    update = small_summarizer(Summarizer(error=connection())).before_model({"messages": history}, None)
    _, placeholder, *kept = update["messages"]
    assert isinstance(kept[0], AIMessage) and len(kept[0].tool_calls) == 2
    assert_paired([placeholder, *kept])


def test_a_summary_that_works_replaces_the_earlier_messages_as_before():
    model = Summarizer()
    update = small_summarizer(model).before_model({"messages": messy_history()}, None)
    placeholder = update["messages"][1]
    assert placeholder.content.endswith("Студент спрашивает про автобус.") and OMITTED not in placeholder.content


def test_nothing_is_summarized_in_the_middle_of_a_run():
    model = Summarizer()
    history = [*messy_history()[:-1], HumanMessage("вопрос", id="hq"), AIMessage(content="", tool_calls=[call("get_my_schedule", "x")], id="ax")]
    assert small_summarizer(model).before_model({"messages": history}, None) is None and not model.prompts
