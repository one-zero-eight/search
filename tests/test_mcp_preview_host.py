"""Preflight prepares the exact arguments and schema of an action before the user is asked."""

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
    from tests.sport_helpers import DAY, FRISBEE, agenda_data, read_messages

    reads = read_messages("sport_get_sport_trainings", {"range": [DAY, DAY], "trainings": [{**FRISBEE, "training_id": 7}]}, "training")
    reads += read_messages("get_my_schedule", agenda_data(classes=[]), "agenda")
    return {"messages": [*(questions or [HumanMessage("Check in.")]),
                         AIMessage(content="", tool_calls=[{"name": "search_api_tools", "args": {"query": "sport"}, "id": "s1"}]),
                         ToolMessage(content=json.dumps({"tools": [{"name": "sport_sport_checkin", "inputSchema": schema}]}),
                                     name="search_api_tools", tool_call_id="s1"),
                         *reads,
                         AIMessage(content="", tool_calls=[deepcopy(call or CALL)])]}


@pytest.mark.parametrize("asynchronous", [False, True])
def test_preflight_prepares_exact_arguments_and_schema_without_rpc(monkeypatch, asynchronous):
    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: pytest.fail("No RPC for a discovered action"))
    monkeypatch.setattr(mcp_client, "request", lambda *a, **kw: pytest.fail("No RPC for a discovered action"))
    initial = state()
    middleware = ApiPreflightMiddleware()
    prepared = (asyncio.run(middleware.aafter_model(initial, RUNTIME)) if asynchronous
                else middleware.after_model(initial, RUNTIME))
    assert "jump_to" not in prepared
    assert prepared["api_prepared"] == [{"call_id": "write-1", "target": "sport_sport_checkin",
                                         "arguments": ARGUMENTS, "schema": SCHEMA}]  # Defaults never replace raw execution intent.


@pytest.mark.parametrize("change", ["target", "arguments", "bool_vs_int", "missing"])
def test_edit_schema_is_found_only_for_the_prepared_call(change):
    from catix.agent.approval_edit import prepared_schema

    prepared = [{"call_id": "write-1", "target": "sport_sport_checkin", "arguments": ARGUMENTS, "schema": SCHEMA}]
    name, args = "call_api_tool", {"name": "sport_sport_checkin", "arguments": dict(ARGUMENTS)}
    if change == "target":
        args["name"] = "rooms_book_room"
    elif change == "arguments":
        args["arguments"]["cancel"] = True
    elif change == "bool_vs_int":
        prepared[0]["arguments"] = {"training_id": 1}
        args["arguments"] = {"training_id": True}
    elif change == "missing":
        prepared = []
    assert prepared_schema(prepared, name, args) is None


@pytest.mark.parametrize("token", [None, SecretStr("synthetic-user")])
def test_missing_required_credentials_never_send_preflight_io(monkeypatch, token):
    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: pytest.fail("No required credentials"))
    runtime = Runtime(context=AgentContext(innohassle_token=token))
    initial: ApiPreflightState = {**state(), "api_prepared": [{"call_id": "stale"}]}
    assert ApiPreflightMiddleware().after_model(initial, runtime) == {"api_prepared": []}
    assert not api_tools._needs_approval(SimpleNamespace(tool_call=CALL, runtime=runtime))


@pytest.mark.parametrize("arguments", [{"training_id": True}, {"training_id": 7, "cancel": 1}])
def test_invalid_typed_arguments_never_reach_approval(monkeypatch, arguments):
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
