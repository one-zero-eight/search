"""Real graph/protocol checks: incomplete actions are questions, not approvals."""
import asyncio
import json

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.types import Command
from pydantic import SecretStr

from catix.agent import core
from catix.agent.tools import AgentContext
from catix.innohassle import client, mcp_client, token
from tests.test_roles import ScriptedModel


MISSING_TITLE = {
    "name": "rooms_book_room",
    "arguments": {"day": "2099-01-01", "room_id": "su-office", "time_from": "10:00", "time_to": "12:00"},
}
QUESTION = "Забронируй su-office 1 января 2099 года с 10:00 до 12:00."


def tool_call(name, args, ident):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": ident}])


@pytest.mark.parametrize("helper", [None, "ask_docs", "ask_chats"])
@pytest.mark.parametrize("asynchronous", [False, True])
def test_discovered_schema_rejects_missing_title_locally_before_approval(
    mcp_http_protocol, monkeypatch, helper, asynchronous,
):
    calls, writes = [], []
    async_request = mcp_client.request
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(token, "claims", lambda value: {"uid": "test-user"} if value == "synthetic-user" else None)
    monkeypatch.setattr(client, "book_room", lambda *a: writes.append(a) or {"outlook_booking_id": "test-booking"})
    monkeypatch.setattr(client, "bookable_rooms", lambda *a: pytest.fail("No detail lookup for invalid arguments"))

    async def record_async(method, arguments, access=None, **kwargs):
        # Both request_sync and native async callers reach this boundary once.
        calls.append((method, access, kwargs))
        return await async_request(method, arguments, access, **kwargs)

    monkeypatch.setattr(mcp_client, "request", record_async)
    script: list[BaseMessage] = []
    if helper:
        script.append(tool_call(helper, {"question": QUESTION}, "helper"))
    script.extend([
        tool_call("search_api_tools", {"query": "rooms_book_room"}, "discover"),
        tool_call("call_api_tool", MISSING_TITLE, "incomplete"),
        *[AIMessage(content="Какое название указать для бронирования?") for _ in range(6)],
    ])
    agent = core.build_agent(ScriptedModel(responses=script), guardrail=False)
    config = {"configurable": {"thread_id": f"missing-title-{helper}-{asynchronous}"}}
    context = AgentContext(innohassle_token=SecretStr("synthetic-user"))
    inputs = {"messages": [HumanMessage(QUESTION)]}
    out = (asyncio.run(agent.ainvoke(inputs, config, context=context)) if asynchronous
           else agent.invoke(inputs, config, context=context))
    assert not agent.get_state(config).interrupts
    assert writes == []
    assert calls == [("search_tools", None, {})], calls
    results = []
    for message in out["messages"]:
        if not isinstance(message, ToolMessage):
            continue
        if message.name == "call_api_tool":
            assert isinstance(message.content, str)
            results.append(json.loads(message.content))
        elif message.name == helper:
            results.extend(json.loads(value) for value in message.artifact["results"])
    assert any(isinstance(result, dict) and "title" in str(result.get("error", "")).lower() for result in results)
    assert "название" in core.final_answer(out["messages"], {}).answer.lower()


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_title_clarification_then_local_description_and_explicit_consent(
    mcp_http_protocol, monkeypatch, decision,
):
    requests, writes = [], []
    original = mcp_client.request
    monkeypatch.setattr(token, "claims", lambda value: {"uid": "test-user"} if value == "synthetic-user" else None)
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(client, "bookable_rooms", lambda *a: pytest.fail("Confirmation must not fetch display details"))
    monkeypatch.setattr(client, "can_book_room", lambda *a: (True, None))
    occupancy = []
    monkeypatch.setattr(client, "room_bookings", lambda *a, **kw: occupancy.append((a, kw)) or [])
    monkeypatch.setattr(client, "book_room", lambda *a: writes.append(a) or {"outlook_booking_id": "test-booking"})

    async def record(method, arguments, access=None, **kwargs):
        requests.append(method)
        return await original(method, arguments, access, **kwargs)

    monkeypatch.setattr(mcp_client, "request", record)
    complete = {**MISSING_TITLE, "arguments": {**MISSING_TITLE["arguments"], "title": "Заседание студсовета"}}
    script: list[BaseMessage] = [
        tool_call("search_api_tools", {"query": "rooms_book_room"}, "discover"),
        tool_call("call_api_tool", MISSING_TITLE, "incomplete"),
        AIMessage(content="Какое название указать для бронирования?"),
        tool_call("call_api_tool", complete, "complete"),
        AIMessage(content="Бронирование подтверждено сервисом." if decision == "approve" else "Бронирование не выполнялось."),
    ]
    agent = core.build_agent(ScriptedModel(responses=script), guardrail=False)
    config = {"configurable": {"thread_id": f"clarification-{decision}"}}
    context = AgentContext(innohassle_token=SecretStr("synthetic-user"))
    first = agent.invoke({"messages": [HumanMessage(QUESTION)]}, config, context=context)
    assert not agent.get_state(config).interrupts and writes == []
    assert requests == ["search_tools"]
    assert "название" in core.final_answer(first["messages"], {}).answer.lower()

    agent.invoke({"messages": [HumanMessage("Название: Заседание студсовета.")]}, config, context=context)
    pending = agent.get_state(config).interrupts
    assert len(pending) == 1 and writes == []
    assert occupancy == []
    action = pending[0].value["action_requests"][0]
    assert action["args"] == complete
    assert all(value in action["description"] for value in ["su-office", "2099", "10:00", "12:00", "Заседание студсовета"]), action["description"]
    assert requests == ["search_tools"]
    prepared_requests = list(requests)

    agent.invoke(Command(resume={pending[0].id: {"decisions": [{"type": decision}]}}), config, context=context)
    assert not agent.get_state(config).interrupts
    assert requests == prepared_requests + (["call_tool"] if decision == "approve" else [])
    assert len(writes) == (1 if decision == "approve" else 0)
    assert occupancy == ([(('synthetic-user', *writes[0][3:]), {'room_id': 'su-office'})]
                         if decision == "approve" else [])
    if writes:
        access, room, title, start, end = writes[0]
        assert (access, room, title) == ("synthetic-user", "su-office", "Заседание студсовета")
        assert (start.hour, end.hour) == (10, 12)
