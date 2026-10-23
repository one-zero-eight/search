"""What RunGuardMiddleware does and does not do, without a model (DeepEval).

It never picks tools for the model (an earlier version added a search_userbot_chats call itself: the model answered, that answer
was thrown away and the run asked again, and the Telegram draft showed it). It only keeps a run from ending badly: a repeated
call is not executed again, a tool call written as text is repaired, the last model call has no tools and must answer.
"""

import types

from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from langchain.agents.middleware.types import ModelResponse
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from catix.agent import core
from catix.agent.core import RunGuardMiddleware
from tests.helpers import ContainsAll

SEARCH = {"name": "search_chats", "args": {"queries": ["мидтерм итп"]}, "id": "call-1", "type": "tool_call"}
TOOLS = [types.SimpleNamespace(name="search_chats"), types.SimpleNamespace(name="search_userbot_chats")]


class Req:
    """A ModelRequest with the few things the guard reads, and `override` like the real one."""

    def __init__(self, ai_messages: int, system="base prompt"):
        self.messages = [HumanMessage("вопрос"), *[AIMessage(content="", tool_calls=[SEARCH]) for _ in range(ai_messages)]]
        self.tools, self.system_message, self.tool_choice = TOOLS, types.SimpleNamespace(text=system), None

    def override(self, **changes):
        clone = Req(0)
        clone.__dict__.update(self.__dict__ | changes)
        return clone


def test_the_guard_does_not_add_tool_calls_the_model_did_not_make():
    guard = RunGuardMiddleware()
    assert not hasattr(guard, "_userbot_alongside") and not hasattr(guard, "_userbot_call")
    response = ModelResponse(result=[AIMessage(content="", tool_calls=[SEARCH])])
    seen = []
    result = guard.wrap_model_call(Req(1), lambda request: seen.append(request) or response)
    assert [c["name"] for c in result.result[-1].tool_calls] == ["search_chats"]  # only the model's own call
    assert seen[0].tools == TOOLS  # the request went on untouched


def test_a_final_answer_is_not_followed_by_a_forced_search():
    answer = AIMessage(content="Мидтерм в среду [m1].")
    result = RunGuardMiddleware().wrap_model_call(Req(1), lambda request: ModelResponse(result=[answer]))
    assert result.result[-1] is answer and not answer.tool_calls


def test_the_last_call_may_not_call_tools_and_has_an_order_to_answer():
    """The tools and the system prompt stay as they were (the start of the request is the model server's cache): the
    call only forbids tool calls and adds the order after the conversation."""
    guard = RunGuardMiddleware()
    early = guard._final(Req(1))
    assert early.tools == TOOLS and early.system_message.text == "base prompt" and early.tool_choice is None
    before = Req(core.settings.agent_max_model_calls - 1)
    last = guard._final(before)
    assert last.tools == TOOLS and last.system_message.text == "base prompt" and last.tool_choice == "none"
    assert last.messages[:-1] == before.messages
    assert_test(LLMTestCase(input="", actual_output=str(last.messages[-1].content)), [ContainsAll(["You have used your tool budget"], name="OrderToAnswer")])


def test_a_repeated_tool_call_is_not_executed_again():
    first = {**SEARCH, "id": "a"}
    again = {**SEARCH, "id": "b"}
    messages = [HumanMessage("q"), AIMessage(content="", tool_calls=[first]), ToolMessage(content="{}", name="search_chats", tool_call_id="a"), AIMessage(content="", tool_calls=[again])]
    guard = RunGuardMiddleware()
    state = {"messages": messages}
    assert guard._duplicate(types.SimpleNamespace(tool_call=first, state=state)) is None  # the first one runs
    hint = guard._duplicate(types.SimpleNamespace(tool_call=again, state=state))
    assert_test(LLMTestCase(input="", actual_output=str(hint.content)), [ContainsAll(["already made"], name="DuplicateHint")])


def test_a_tool_call_written_as_text_is_repaired_or_never_shown():
    markup = AIMessage(content='<tool_call>\n<function=search_chats>\n<parameter=queries>["мидтерм итп"]</parameter>\n</function>\n</tool_call>')  # Qwen's format
    guard = RunGuardMiddleware()
    repaired, ok = guard._check(ModelResponse(result=[markup]), allow_calls=True)
    assert ok and guard._last(repaired).tool_calls[0]["name"] == "search_chats"
    _, ok = guard._check(ModelResponse(result=[markup]), allow_calls=False)  # no tools left: it cannot become a call
    assert not ok
