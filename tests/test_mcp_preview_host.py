"""Preview I/O belongs to preflight; the replayed HITL callback is a pure lookup."""

import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.errors import GraphBubbleUp
from langgraph.runtime import Runtime
from pydantic import SecretStr

from catix.agent import api_tools
from catix.agent.api_preflight import ApiPreflightMiddleware, ApiPreflightState
from catix.agent.tools import AgentContext
from catix.innohassle import mcp_client


ARGUMENTS = {"training_id": 7}
CALL = {"name": "call_api_tool", "id": "write-1", "args": {"name": "sport_sport_checkin", "arguments": ARGUMENTS}}
RUNTIME = Runtime(context=AgentContext(
    innohassle_token=SecretStr("synthetic-user"), sport_token=SecretStr("synthetic-sport"),
))
SCHEMA = {"type": "object", "properties": {"training_id": {"type": "integer"}, "cancel": {"type": "boolean"}},
          "required": ["training_id"]}


def state(call=None, questions=None) -> ApiPreflightState:
    import json
    return {"messages": [*(questions or [HumanMessage("Check in.")]),
                         AIMessage(content="", tool_calls=[{"name": "search_api_tools", "args": {"query": "sport"}, "id": "s1"}]),
                         ToolMessage(content=json.dumps({"tools": [{"name": "sport_sport_checkin", "inputSchema": SCHEMA}]}),
                                     name="search_api_tools", tool_call_id="s1"),
                         AIMessage(content="", tool_calls=[deepcopy(call or CALL)])]}


def test_preflight_uses_sport_credentials_and_latest_language_then_callback_is_pure(monkeypatch):
    sent = []

    def request(method, payload, token, **credentials):
        sent.append((method, payload, token, credentials))
        return {"name": payload["name"], "arguments": {**payload["arguments"], "cancel": False}, "description": "Reviewed training."}

    monkeypatch.setattr(mcp_client, "request_sync", request)
    initial = state(questions=[HumanMessage("Запиши на спорт."), HumanMessage("Check in.")])
    prepared = ApiPreflightMiddleware().after_model(initial, RUNTIME)
    assert "jump_to" not in prepared
    assert api_tools._describe_mutation(CALL, prepared, RUNTIME) == "Reviewed training."
    assert api_tools._describe_mutation(CALL, prepared, RUNTIME) == "Reviewed training."
    assert sent == [("preview_tool", {
        "name": "sport_sport_checkin", "arguments": ARGUMENTS, "language": "en",
    }, "synthetic-user", {"sport_token": "synthetic-sport"})]
    assert prepared["api_prepared"][0]["arguments"] == ARGUMENTS  # Defaults never replace raw execution intent.


@pytest.mark.parametrize("change", ["id", "target", "arguments", "bool_vs_int", "missing"])
def test_description_refuses_unprepared_or_different_call_without_io(monkeypatch, change):
    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: pytest.fail("HITL lookup must never perform I/O"))
    prepared = {"api_prepared": [{"call_id": "write-1", "target": "sport_sport_checkin", "arguments": ARGUMENTS,
                                  "description": "Reviewed training."}]}
    call = deepcopy(CALL)
    if change == "id":
        call["id"] = "write-2"
    elif change == "target":
        call["args"]["name"] = "rooms_book_room"
    elif change == "arguments":
        call["args"]["arguments"]["cancel"] = True
    elif change == "bool_vs_int":
        prepared["api_prepared"][0]["arguments"] = {"training_id": 1}
        call["args"]["arguments"] = {"training_id": True}
    else:
        prepared = {}
    assert api_tools._needs_approval(SimpleNamespace(tool_call=call, runtime=RUNTIME))
    with pytest.raises(ValueError, match="prepared"):
        api_tools._describe_mutation(call, prepared, RUNTIME)
    assert api_tools._needs_approval(SimpleNamespace(tool_call=call, runtime=RUNTIME))


@pytest.mark.parametrize("token", [None, SecretStr("synthetic-user")])
def test_missing_required_credentials_never_send_preflight_io(monkeypatch, token):
    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: pytest.fail("No required credentials"))
    runtime = Runtime(context=AgentContext(innohassle_token=token))
    initial: ApiPreflightState = {**state(), "api_prepared": [{"description": "stale"}]}
    assert ApiPreflightMiddleware().after_model(initial, runtime) == {"api_prepared": []}
    assert not api_tools._needs_approval(SimpleNamespace(tool_call=CALL, runtime=runtime))


@pytest.mark.parametrize("preview_arguments", [{"training_id": 8}, {"training_id": True}, {"training_id": 7, "cancel": False}])
def test_preview_cannot_change_any_explicit_typed_value(monkeypatch, preview_arguments):
    call = deepcopy(CALL)
    call["args"]["arguments"]["cancel"] = True
    if preview_arguments.get("training_id") is True:
        call["args"]["arguments"]["training_id"] = 1
    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: {
        "name": "sport_sport_checkin", "arguments": preview_arguments, "description": "WRONG PREVIEW",
    })
    result = ApiPreflightMiddleware().after_model(state(call), RUNTIME)
    assert result["jump_to"] == "model" and result["api_prepared"] == []
    assert "WRONG PREVIEW" not in str(result)
    assert api_tools._needs_approval(SimpleNamespace(tool_call=call, runtime=RUNTIME))


@pytest.mark.parametrize("asynchronous", [False, True])
def test_graph_control_flow_is_not_swallowed(monkeypatch, asynchronous):
    error = GraphBubbleUp("synthetic control flow")

    def request(*args, **kwargs):
        raise error

    async def arequest(*args, **kwargs):
        raise error

    monkeypatch.setattr(mcp_client, "request_sync", request)
    monkeypatch.setattr(mcp_client, "request", arequest)
    middleware = ApiPreflightMiddleware()
    with pytest.raises(GraphBubbleUp) as actual:
        if asynchronous:
            asyncio.run(middleware.aafter_model(state(), RUNTIME))
        else:
            middleware.after_model(state(), RUNTIME)
    assert actual.value is error


@pytest.mark.parametrize("inside_event_loop", [False, True])
def test_mcp_preview_transport_sync_bridge_remains_usable(monkeypatch, inside_event_loop):
    calls = []
    payload = {"name": "music_book_music_room", "arguments": {}, "language": "en"}
    result = {"name": payload["name"], "arguments": {}, "description": "Remote preview."}

    class Client:
        async def call_tool(self, method, arguments, **kwargs):
            calls.append((method, arguments))
            return SimpleNamespace(is_error=False, data=result)

    @asynccontextmanager
    async def connection(token, **kwargs):
        assert token == "synthetic-user" and not kwargs
        yield Client()

    monkeypatch.setattr(mcp_client, "_connection", connection)

    def call():
        return mcp_client.request_sync("preview_tool", payload, "synthetic-user")

    async def in_loop():
        return call()

    actual = asyncio.run(in_loop()) if inside_event_loop else call()
    assert actual == result
    assert calls == [("preview_tool", payload)]
