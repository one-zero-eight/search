"""What the Telegram draft shows while the agent works (tgbot/stream.py), without a model or Telegram (DeepEval)."""

import asyncio

from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from langchain_core.messages import AIMessageChunk, ToolMessage

from catix.tgbot import stream
from tests.helpers import ContainsAll, ContainsNone, SameLabel

SUPERVISOR = {"langgraph_node": "model", "lc_agent_name": "supervisor"}


class Recorder(stream.DraftStreamer):
    def __init__(self):
        super().__init__(None, 1, None, lambda text: text)
        self.sent: list[str] = []

    async def _send(self, text, *, html):
        self.sent.append(text)
        self._last = -10_000.0  # never throttled in the test


def _run(coro):
    return asyncio.run(coro)


def test_the_screens_verdict_is_never_shown():
    drafts = Recorder()
    _run(drafts.start())
    verdict = AIMessageChunk(content='{\n  "category": "ok"\n}', id="g1")
    _run(drafts.feed(verdict, {"langgraph_node": "GuardrailMiddleware.before_agent", "lc_agent_name": "supervisor"}))
    assert drafts.sent == [stream.CHECKING]


def test_a_helpers_own_text_is_not_shown_but_the_supervisors_answer_is():
    drafts = Recorder()
    _run(drafts.feed(AIMessageChunk(content="отчёт помощника", id="h1"), {"langgraph_node": "model", "lc_agent_name": "chats"}))
    assert drafts.sent == []
    _run(drafts.feed(AIMessageChunk(content="Мидтерм 22 октября", id="s1"), SUPERVISOR))
    assert drafts.sent == ["Мидтерм 22 октября"]


def test_the_user_sees_each_stage_in_turn():
    drafts = Recorder()
    _run(drafts.start())
    call = AIMessageChunk(content="", id="s1", tool_call_chunks=[{"name": "ask_chats", "args": "", "id": "c", "index": 0}])
    _run(drafts.feed(call, SUPERVISOR))
    _run(drafts.feed_custom({"tool": "search_chats"}))
    _run(drafts.feed_custom({"tool": "search_chats"}))  # the same status twice is sent once
    _run(drafts.feed_custom({"tool": "no-such-tool"}))
    _run(drafts.feed(ToolMessage(content="отчёт", tool_call_id="c", name="ask_chats"), {"langgraph_node": "tools"}))
    assert drafts.sent == [stream.CHECKING, stream.STATUS["ask_chats"], stream.STATUS["search_chats"], stream.WRITING]
    assert_test(LLMTestCase(input="", actual_output=" ".join(drafts.sent)), [ContainsAll(["Проверяю", "помощника", "Ищу", "Формулирую"], name="Stages"), ContainsNone(["category", "{"], name="NoJson")])


def test_without_metadata_the_text_is_shown_as_before():
    drafts = Recorder()
    _run(drafts.feed(AIMessageChunk(content="Привет", id="s1")))
    assert drafts.sent == ["Привет"]
