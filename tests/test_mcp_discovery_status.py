"""MCP discovery remains public and reports progress before the tool finishes."""
import asyncio
import os
import subprocess
import sys
import textwrap
from typing import Any

import pytest
from langchain.tools import ToolRuntime
from langchain_core.messages import AIMessage, AIMessageChunk
from pydantic import SecretStr

from catix.agent import api_tools
from catix.agent.core import SUPERVISOR_NAME
from catix.agent.tools import AgentContext
from catix.api import ask
from catix.common.status import CHECKING
from catix.innohassle import token


def test_first_sdk_result_validates_without_cold_schema_imports():
    # Fresh process: the test runner/server fixtures already import jsonschema.
    code = textwrap.dedent('''
        import asyncio
        import anyio
        import importlib.abc
        import sys
        from catix.innohassle import mcp_client
        from mcp import ClientSession, types

        class NoColdImports(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.split('.')[0] in {'jsonschema', 'rfc3987_syntax'}:
                    raise AssertionError('Cold schema initialization on the MCP request path: ' + fullname)

        sys.meta_path.insert(0, NoColdImports())

        async def run():
            send, receive = anyio.create_memory_object_stream(1)
            session = ClientSession(receive, send)
            session._tool_output_schemas['probe'] = {
                'type': 'object', 'properties': {'ok': {'type': 'boolean'}}, 'required': ['ok'],
            }
            await session.validate_tool_result('probe', types.CallToolResult(content=[], structuredContent={'ok': True}))
            try:
                await session.validate_tool_result('probe', types.CallToolResult(content=[], structuredContent={'ok': 'wrong type'}))
            except RuntimeError:
                return
            raise AssertionError('Output validation was disabled')

        asyncio.run(run())
    ''')
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=30,
                            env={**os.environ, 'DATABASE_URL': '', 'REDIS_URL': ''})
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("asynchronous", [False, True])
def test_signed_in_catalogue_search_never_verifies_or_forwards_user_tokens(monkeypatch, mcp_http_protocol, asynchronous):
    verified = []
    monkeypatch.setattr(token, "claims", lambda value: verified.append(value) or {"uid": "synthetic-user"})
    context = AgentContext(
        innohassle_token=SecretStr("synthetic-user-token"), sport_token=SecretStr("synthetic-sport-token"),
    )
    runtime = ToolRuntime[Any](state={}, context=context, config={}, stream_writer=lambda _: None,
                               tool_call_id="search", store=None)
    result = (asyncio.run(api_tools._asearch("free rooms", runtime)) if asynchronous
              else api_tools._search("free rooms", runtime))
    assert any(tool["name"] == "rooms_get_free_rooms" for tool in result["tools"])
    assert verified == [], "Public catalogue lookup must not trigger JWT/JWKS work"
    assert "synthetic-user-token" not in str(result) and "synthetic-sport-token" not in str(result)


LABELS = [
    ("search_api_tools", "🔎 Ищу подходящий инструмент…"),
    ("call_api_tool", "🔧 Обращаюсь к сервису…"),
    ("add_to_ai_calendar", "🗓 Готовлю добавление в календарь…"),
    ("update_ai_calendar", "🗓 Готовлю изменение календаря…"),
]


@pytest.mark.parametrize("tool_name,label", LABELS)
@pytest.mark.parametrize("mode", ["messages", "custom"])
def test_api_emits_status_while_root_or_helper_tool_is_still_running(monkeypatch, tool_name, label, mode):
    async def run():
        started, release = asyncio.Event(), asyncio.Event()
        events = asyncio.Queue()

        class Agent:
            async def astream(self, *args, **kwargs):
                if mode == "custom":
                    yield "custom", {"tool": tool_name}
                else:
                    chunk = AIMessageChunk(content="", id="m1", tool_call_chunks=[{
                        "name": tool_name, "args": "", "id": "c1", "index": 0,
                    }])
                    yield "messages", (chunk, {"langgraph_node": "model", "lc_agent_name": SUPERVISOR_NAME})
                started.set()
                await release.wait()
                yield "values", {"messages": [AIMessage("Done")], "sources": {}}

        monkeypatch.setattr(ask, "agent", Agent)
        task = asyncio.create_task(ask.stream_agent({}, {}, AgentContext(), events))
        try:
            await asyncio.wait_for(started.wait(), timeout=2)
            assert not task.done()
            sent = [events.get_nowait() for _ in range(events.qsize())]
            assert sent == [("status", {"text": CHECKING}), ("status", {"text": label})]
        finally:
            release.set()
            await task

    asyncio.run(run())


@pytest.mark.parametrize("tool_name,label", LABELS)
def test_bot_shares_new_tool_progress_labels(tool_name, label):
    from tests.test_stream import Recorder, SUPERVISOR

    async def run():
        drafts = Recorder()
        await drafts.start()
        await drafts.feed(AIMessageChunk(content="", id="m1", tool_call_chunks=[{
            "name": tool_name, "args": "", "id": "c1", "index": 0,
        }]), SUPERVISOR)
        assert drafts.sent == [CHECKING, label]

    asyncio.run(run())
