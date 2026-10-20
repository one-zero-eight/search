"""How a run is put together, without a model (DeepEval).

Regression: after `search_chats` the model wrote its answer, and only then the run made it call `search_userbot_chats` and
asked the model again. The first answer was thrown away (in Telegram the draft showed it first), one model call was wasted.
Now the second search goes in the same step as the first, so the model answers once.
"""

import types

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from langchain.agents.middleware.types import ModelResponse
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from catix.agent import core
from catix.agent.core import RunGuardMiddleware
from tests.helpers import ContainsAll

SEARCH = {"name": "search_chats", "args": {"queries": ["мидтерм итп", "midterm ITP"]}, "id": "call-1", "type": "tool_call"}
TOOLS = [types.SimpleNamespace(name="search_chats"), types.SimpleNamespace(name="search_userbot_chats")]


def request(messages=None, tools=TOOLS):
    return types.SimpleNamespace(tools=tools, messages=messages or [HumanMessage("когда мидтерм по итп")])


@pytest.fixture(autouse=True)
def big_chats_exist(monkeypatch):
    monkeypatch.setattr(core, "_live_titles", lambda request: {1: "Big chat"})


def names(response) -> list[str]:
    return [c["name"] for c in RunGuardMiddleware._last(response).tool_calls]


def test_the_userbot_search_goes_with_the_first_search():
    response = ModelResponse(result=[AIMessage(content="", tool_calls=[SEARCH])])
    extended = RunGuardMiddleware()._userbot_alongside(request(), response)
    assert [c["name"] for c in extended.tool_calls] == ["search_chats", "search_userbot_chats"]
    extra = extended.tool_calls[1]
    assert extra["args"]["queries"] and extra["id"].startswith("auto-")
    assert_test(LLMTestCase(input="", actual_output=" ".join(extra["args"]["queries"])), [ContainsAll(["итп"], name="KeywordsOfTheQueries")])


def test_nothing_is_added_when_the_model_already_asked_for_it():
    both = AIMessage(content="", tool_calls=[SEARCH, {**SEARCH, "name": "search_userbot_chats", "id": "call-2"}])
    assert RunGuardMiddleware()._userbot_alongside(request(), ModelResponse(result=[both])) is None


def test_it_is_done_once_per_question():
    done = ToolMessage(content="{}", name="search_userbot_chats", tool_call_id="x")
    messages = [HumanMessage("q"), AIMessage(content="", tool_calls=[SEARCH]), done]
    assert RunGuardMiddleware()._userbot_alongside(request(messages), ModelResponse(result=[AIMessage(content="", tool_calls=[SEARCH])])) is None


def test_a_final_answer_or_another_tool_gets_nothing():
    guard = RunGuardMiddleware()
    assert guard._userbot_alongside(request(), ModelResponse(result=[AIMessage(content="Мидтерм в среду")])) is None
    other = AIMessage(content="", tool_calls=[{**SEARCH, "name": "get_clubs", "args": {"query": "chess"}}])
    assert guard._userbot_alongside(request(), ModelResponse(result=[other])) is None


def test_no_userbot_chats_no_extra_call(monkeypatch):
    monkeypatch.setattr(core, "_live_titles", lambda request: {})
    assert RunGuardMiddleware()._userbot_alongside(request(), ModelResponse(result=[AIMessage(content="", tool_calls=[SEARCH])])) is None


def test_without_the_tool_nothing_is_added():
    only = [types.SimpleNamespace(name="search_chats")]
    assert RunGuardMiddleware()._userbot_alongside(request(tools=only), ModelResponse(result=[AIMessage(content="", tool_calls=[SEARCH])])) is None
