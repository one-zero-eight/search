"""Deterministic relative-date regressions; no model or external services."""

import asyncio
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from langchain.agents.middleware import ModelRequest, ModelResponse
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.runtime import Runtime

from catix.agent import core
from catix.agent.tools import AgentContext
from catix.common import dates

TZ = ZoneInfo("Europe/Moscow")
TRACE_ASKED_AT = datetime.fromisoformat("2026-11-08T07:20:55+03:00")
TRACE_QUESTION = "предложи мне тренировки на после завтра"


def test_original_training_trace_resolves_the_whole_phrase():
    """Trace dc23b42b40763a13cecb0f40c2bc92a1 must not inject tomorrow."""
    assert dates.question_dates(TRACE_QUESTION, TRACE_ASKED_AT) == [
        "'после завтра' = 2026-11-10 Tue (in 2 days)"
    ]


@pytest.mark.parametrize("phrase", [
    "после завтра", "ПОСЛЕ ЗАВТРА", "После\t завтра", "после\nзавтра",
    "day after tomorrow", "the day after tomorrow", "THE DAY AFTER TOMORROW",
    "The\tday  after\ntomorrow", "после\u00a0завтра",
])
@pytest.mark.parametrize(("sent_at", "expected"), [
    (TRACE_ASKED_AT, date(2026, 11, 10)),
    (datetime(2026, 11, 30, 23, 59, tzinfo=TZ), date(2026, 12, 2)),
    (datetime(2026, 12, 31, 23, 59, tzinfo=TZ), date(2027, 1, 2)),
])
def test_long_relative_phrase_is_one_date_preserving_its_text(phrase, sent_at, expected):
    assert dates.found_dates(f"({phrase})!", sent_at, sent_at) == [(phrase, expected)]
    assert dates.question_dates(phrase, sent_at) == [
        f"'{phrase}' = {expected:%Y-%m-%d %a} (in 2 days)"
    ]


@pytest.mark.parametrize(("text", "expected"), [
    ("завтра", [("завтра", date(2026, 11, 9))]),
    ("tomorrow", [("tomorrow", date(2026, 11, 9))]),
    ("послезавтра", [("послезавтра", date(2026, 11, 10))]),
    ("сегодня", [("сегодня", date(2026, 11, 8))]),
    ("today", [("today", date(2026, 11, 8))]),
    ("вчера", [("вчера", date(2026, 11, 7))]),
    ("yesterday", [("yesterday", date(2026, 11, 7))]),
    ("позавчера", [("позавчера", date(2026, 11, 6))]),
    ("tonight", [("tonight", date(2026, 11, 8))]),
    ("this evening", [("this evening", date(2026, 11, 8))]),
    ("this morning", [("this morning", date(2026, 11, 8))]),
    ("завтра и после завтра", [("завтра", date(2026, 11, 9)), ("после завтра", date(2026, 11, 10))]),
    ("the day after tomorrow or tomorrow", [
        ("the day after tomorrow", date(2026, 11, 10)), ("tomorrow", date(2026, 11, 9)),
    ]),
    ("завтрак tomorrowland послезавтрашний", []),
    ("после завтрака; day after tomorrowland", []),
    ("предложи мне тренировки", []),
])
def test_existing_dates_and_independent_mentions_are_unchanged(text, expected):
    assert dates.found_dates(text, TRACE_ASKED_AT, TRACE_ASKED_AT) == expected


@pytest.fixture
def clock(monkeypatch):
    class Clock(datetime):
        current = datetime(2030, 6, 15, 12, 0, tzinfo=TZ)

        @classmethod
        def now(cls, tz=None):
            return cls.current.astimezone(tz)

    monkeypatch.setattr(core, "datetime", Clock)
    monkeypatch.setattr(core.settings, "tz", TZ)
    return Clock


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize(("asked_at", "expected"), [
    (TRACE_ASKED_AT, "'после завтра' = 2026-11-10 Tue (in 2 days)"),
    # UTC date is December 31, but the trusted local question date is January 1.
    (datetime.fromisoformat("2026-12-31T22:30:00+00:00"), "'после завтра' = 2027-01-03 Sun (in 2 days)"),
])
def test_hint_uses_trusted_question_time_across_model_calls(clock, asked_at, expected, asynchronous):
    previous = HumanMessage("завтра", id="previous")
    question = HumanMessage(TRACE_QUESTION, id="question")
    followup = AIMessage("checking")
    messages = [previous, AIMessage("old answer"), question, followup]
    request: ModelRequest[Any] = ModelRequest(
        model=FakeListChatModel(responses=["unused"]), messages=messages,
        state={"messages": messages}, runtime=Runtime(context=AgentContext(asked_at=asked_at)),
    )
    middleware = core.QuestionNoteMiddleware()
    seen: list[ModelRequest[Any]] = []
    response = ModelResponse(result=[AIMessage("unused")])

    def receive(request):
        seen.append(request)
        return response

    async def areceive(request):
        return receive(request)

    results = []
    for live_time in (datetime(2030, 6, 15, 23, 59, tzinfo=TZ), datetime(2030, 6, 16, 0, 1, tzinfo=TZ)):
        clock.current = live_time
        if asynchronous:
            assert asyncio.run(middleware.awrap_model_call(request, areceive)) is response
        else:
            assert middleware.wrap_model_call(request, receive) is response
        result = seen[-1]
        results.append(result.messages[-2].content)
        assert result.messages[-2].id == question.id
        assert result.messages[:2] == messages[:2]
        assert result.messages[-1] is followup
        assert question.content == TRACE_QUESTION
        assert request.messages == messages
        assert request.state["messages"] == messages
    note = f"Dates in this message, worked out (use them, not your own arithmetic): {expected}."
    assert results == [f"{TRACE_QUESTION}\n\n[{note}]"] * 2


@pytest.mark.parametrize("runtime", [None, Runtime()])
def test_hint_without_context_falls_back_to_local_clock(clock, runtime):
    request: ModelRequest[Any] = ModelRequest(
        model=FakeListChatModel(responses=["unused"]), messages=[HumanMessage("tomorrow")],
        runtime=runtime,
    )
    result = core.QuestionNoteMiddleware()._with_hint(request)
    assert "'tomorrow' = 2030-06-16 Sun (tomorrow)" in result.messages[0].content


def test_no_date_or_reminder_leaves_request_untouched(clock):
    request: ModelRequest[Any] = ModelRequest(
        model=FakeListChatModel(responses=["unused"]), messages=[HumanMessage("предложи мне тренировки")],
        runtime=Runtime(context=AgentContext(asked_at=TRACE_ASKED_AT)),
    )
    assert core.QuestionNoteMiddleware()._with_hint(request) is request
