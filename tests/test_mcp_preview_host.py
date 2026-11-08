"""Confirmation text is local; the replayed HITL callback is a pure lookup."""

import asyncio
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
SCHEMA = {"type": "object", "properties": {"training_id": {"type": "integer"}, "cancel": {"type": "boolean", "default": False}},
          "required": ["training_id"]}


def state(call=None, questions=None, schema=SCHEMA) -> ApiPreflightState:
    import json
    return {"messages": [*(questions or [HumanMessage("Check in.")]),
                         AIMessage(content="", tool_calls=[{"name": "search_api_tools", "args": {"query": "sport"}, "id": "s1"}]),
                         ToolMessage(content=json.dumps({"tools": [{"name": "sport_sport_checkin", "inputSchema": schema}]}),
                                     name="search_api_tools", tool_call_id="s1"),
                         AIMessage(content="", tool_calls=[deepcopy(call or CALL)])]}


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("question,description", [
    ("Check in.", "Check you in to the training #7."),
    ("Запиши на спорт.", "Записать вас на тренировку #7."),
])
def test_preflight_formats_locally_in_latest_language_then_callback_is_pure(monkeypatch, asynchronous, question, description):
    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: pytest.fail("No RPC for a discovered action"))
    monkeypatch.setattr(mcp_client, "request", lambda *a, **kw: pytest.fail("No RPC for a discovered action"))
    initial = state(questions=[HumanMessage("Previous question."), HumanMessage(question)])
    middleware = ApiPreflightMiddleware()
    prepared = (asyncio.run(middleware.aafter_model(initial, RUNTIME)) if asynchronous
                else middleware.after_model(initial, RUNTIME))
    assert "jump_to" not in prepared
    assert api_tools._describe_mutation(CALL, prepared, RUNTIME) == description
    assert api_tools._describe_mutation(CALL, prepared, RUNTIME) == description
    assert prepared["api_prepared"][0]["arguments"] == ARGUMENTS  # Defaults never replace raw execution intent.


@pytest.mark.parametrize("default", [False, True])
@pytest.mark.parametrize("explicit", [None, False, True])
def test_description_uses_discovered_defaults_without_changing_execution_arguments(monkeypatch, default, explicit):
    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: pytest.fail("No RPC"))
    schema = deepcopy(SCHEMA)
    schema["properties"]["cancel"]["default"] = default
    call = deepcopy(CALL)
    if explicit is not None:
        call["args"]["arguments"]["cancel"] = explicit
    original = deepcopy(call)
    prepared = ApiPreflightMiddleware().after_model(state(call, schema=schema), RUNTIME)
    assert "jump_to" not in prepared
    description = api_tools._describe_mutation(call, prepared, RUNTIME)
    assert description.startswith("Cancel" if (default if explicit is None else explicit) else "Check")
    assert prepared["api_prepared"][0]["arguments"] == original["args"]["arguments"]
    assert call == original


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("default", [None, 0, "false", "absent"])
def test_invalid_or_missing_display_defaults_fail_without_approval(monkeypatch, asynchronous, default):
    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: pytest.fail("No RPC"))
    monkeypatch.setattr(mcp_client, "request", lambda *a, **kw: pytest.fail("No RPC"))
    schema = deepcopy(SCHEMA)
    if default == "absent":
        del schema["properties"]["cancel"]["default"]
    else:
        schema["properties"]["cancel"]["default"] = default
    initial = state(schema=schema)
    original = deepcopy(initial)
    middleware = ApiPreflightMiddleware()
    prepared = (asyncio.run(middleware.aafter_model(initial, RUNTIME)) if asynchronous
                else middleware.after_model(initial, RUNTIME))
    assert prepared["jump_to"] == "model" and prepared["api_prepared"] == []
    assert prepared["messages"][0].status == "error"
    assert prepared["messages"][0].tool_call_id == CALL["id"]
    assert initial == original
    with pytest.raises(ValueError, match="prepared"):
        api_tools._describe_mutation(CALL, prepared, RUNTIME)


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


@pytest.mark.parametrize("arguments", [{"training_id": True}, {"training_id": 7, "cancel": 1}])
def test_invalid_typed_arguments_never_reach_description(monkeypatch, arguments):
    call = deepcopy(CALL)
    call["args"]["arguments"] = arguments
    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: pytest.fail("No RPC"))
    result = ApiPreflightMiddleware().after_model(state(call), RUNTIME)
    assert result["jump_to"] == "model" and result["api_prepared"] == []
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
    initial = state()
    initial["messages"] = [initial["messages"][0], initial["messages"][-1]]  # No discovered schema: exercise I/O.
    with pytest.raises(GraphBubbleUp) as actual:
        if asynchronous:
            asyncio.run(middleware.aafter_model(initial, RUNTIME))
        else:
            middleware.after_model(initial, RUNTIME)
    assert actual.value is error
