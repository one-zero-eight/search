"""PlanThinkingMiddleware: only the supervisor's first model call of a real question thinks, with the model card's sampling;
its later calls, small talk and a run without the screen do not (agent/core.py)."""

import types

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from catix.agent import core, questions
from catix.agent.core import PlanThinkingMiddleware, PriorityMiddleware
from catix.settings import settings

ASK = {"name": "ask_campus", "args": {"question": "как добраться до верхнего услона"}, "id": "c1", "type": "tool_call"}
MODEL = types.SimpleNamespace(extra_body={"chat_template_kwargs": {"enable_thinking": False}})


class Req:
    """A ModelRequest with what the middleware reads, and `override` like the real one."""

    def __init__(self, messages: list, state: dict | None = None):
        self.messages, self.model, self.model_settings = messages, MODEL, {}
        self.state = {"messages": messages, **(state or {})}

    def override(self, **changes):
        clone = Req(self.messages)
        clone.__dict__.update(self.__dict__ | changes)
        return clone


QUESTION = [HumanMessage("как добраться до верхнего услона")]
REPORTED = [*QUESTION, AIMessage(content="", tool_calls=[ASK]), ToolMessage(content="Автобус …", tool_call_id="c1", name="ask_campus")]


def _settings(request: Req) -> dict:
    return PlanThinkingMiddleware()._with(request).model_settings


def test_the_first_call_of_a_real_question_thinks_with_the_model_cards_sampling():
    got = _settings(Req(QUESTION, {"answer_alone": False}))
    assert got["extra_body"]["chat_template_kwargs"] == {"enable_thinking": True}
    assert (got["temperature"], got["top_p"], got["presence_penalty"]) == (0.85, 0.95, 1.1)
    assert (got["extra_body"]["top_k"], got["extra_body"]["min_p"]) == (20, 0.0)
    assert got["max_tokens"] == settings.llm_plan_max_tokens


@pytest.mark.parametrize("state", [{"answer_alone": True}, {}], ids=["small talk", "no screen"])
def test_small_talk_and_a_run_without_the_screen_do_not_think(state):
    assert _settings(Req(QUESTION, state)) == {}


def test_the_calls_after_a_report_do_not_think_even_with_a_hint_after_the_conversation():
    later = Req(REPORTED, {"answer_alone": False})
    assert _settings(later) == {}
    # RunGuardMiddleware adds its order to answer as a human message of the request, not of the state.
    hinted = later.override(messages=[*REPORTED, HumanMessage(core.FINAL_HINT)])
    assert _settings(hinted) == {}


def test_off_nobody_thinks(monkeypatch):
    monkeypatch.setattr(settings, "agent_plan_thinking", False)
    assert _settings(Req(QUESTION, {"answer_alone": False})) == {}


def test_the_priority_keeps_the_thinking_of_the_plan():
    token = questions.PRIORITY.set(-5)
    try:
        planned = PlanThinkingMiddleware()._with(Req(QUESTION, {"answer_alone": False}))
        extra = PriorityMiddleware._with(planned).model_settings["extra_body"]
    finally:
        questions.PRIORITY.reset(token)
    assert extra["priority"] == -5 and extra["chat_template_kwargs"] == {"enable_thinking": True} and extra["top_k"] == 20
