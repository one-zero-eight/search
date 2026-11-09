"""Every supervisor call thinks; sampling and priority overrides remain compatible."""

import types

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from catix.agent import core, questions
from catix.agent.core import PlanThinkingMiddleware, PriorityMiddleware
from catix.settings import settings

ASK = {"name": "ask_docs", "args": {"question": "как добраться до верхнего услона"}, "id": "c1", "type": "tool_call"}
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
REPORTED = [*QUESTION, AIMessage(content="", tool_calls=[ASK]), ToolMessage(content="Автобус …", tool_call_id="c1", name="ask_docs")]


def _settings(request: Req) -> dict:
    return PlanThinkingMiddleware()._with(request).model_settings


@pytest.mark.parametrize("state", [{"answer_alone": False}, {"answer_alone": True}, {}], ids=["question", "small-talk", "no-screen"])
def test_the_first_call_always_thinks_with_the_model_cards_sampling(state):
    got = _settings(Req(QUESTION, state))
    assert got["extra_body"]["chat_template_kwargs"] == {"enable_thinking": True}
    assert (got["temperature"], got["top_p"], got["presence_penalty"]) == (0.85, 0.95, 1.1)
    assert (got["extra_body"]["top_k"], got["extra_body"]["min_p"], got["extra_body"]["repetition_penalty"]) == (20, 0.0, 1.0)
    assert got["max_tokens"] == settings.llm_plan_max_tokens




def test_calls_after_results_and_terminal_hints_keep_thinking():
    later = Req(REPORTED, {"answer_alone": False})
    for request in (later, later.override(messages=[*REPORTED, HumanMessage(core.FINAL_HINT)])):
        assert _settings(request)["extra_body"]["chat_template_kwargs"]["enable_thinking"] is True




def test_the_priority_keeps_the_thinking_of_the_plan():
    token = questions.PRIORITY.set(-5)
    try:
        planned = PlanThinkingMiddleware()._with(Req(QUESTION, {"answer_alone": False}))
        extra = PriorityMiddleware._with(planned).model_settings["extra_body"]
    finally:
        questions.PRIORITY.reset(token)
    assert extra["priority"] == -5 and extra["chat_template_kwargs"] == {"enable_thinking": True} and extra["top_k"] == 20
