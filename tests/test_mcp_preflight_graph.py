"""Preflight must finish before the checkpointed host approval node."""

import json
from copy import deepcopy

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from pydantic import Field, SecretStr

from catix.agent import api_tools, core
from catix.agent.tools import AgentContext



TARGET = "rooms_book_room"
ARGUMENTS = {"day": "2026-11-10", "room_id": "su-office", "time_from": "10:00", "time_to": "12:00"}
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "day": {"type": "string", "format": "date"},
        "room_id": {"type": "string"},
        "time_from": {"type": "string", "pattern": r"^\d{2}:\d{2}$"},
        "time_to": {"type": "string", "pattern": r"^\d{2}:\d{2}$"},
        "title": {"type": "string", "minLength": 1},
    },
    "required": ["day", "room_id", "time_from", "time_to", "title"],
}
CONTEXT = AgentContext(innohassle_token=SecretStr("synthetic-user"))
CONFIG = {"configurable": {"thread_id": "schema-preflight"}}


class ObservedModel(FakeMessagesListChatModel):
    seen: list = Field(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        return self.bind(tools=tools, **kwargs)

    def _generate(self, messages, *args, **kwargs):
        self.seen.append(deepcopy(messages))
        return super()._generate(messages, *args, **kwargs)


class PlaceholderModel(ObservedModel):
    """Try a fabricated repair unless the transport forbids further tools."""

    bindings: list = Field(default_factory=list)

    def _generate(self, messages, *args, **kwargs):
        self.bindings.append({"tools": kwargs.get("tools"), "tool_choice": kwargs.get("tool_choice")})
        result = super()._generate(messages, *args, **kwargs)
        if kwargs.get("tool_choice") == "none":
            result.generations[0].message = AIMessage(content="What is the title?")
        return result


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("helper", [None, "docs", "chats"])
@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_missing_required_field_forces_no_tools_clarification(monkeypatch, rpc, asynchronous, helper, decision):
    import asyncio
    from langgraph.types import Command

    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)

    async def request(*args, **kwargs):
        return api_tools.mcp_client.request_sync(*args, **kwargs)

    monkeypatch.setattr(api_tools.mcp_client, "request", request)
    script: list[BaseMessage] = []
    if helper:
        script.append(AIMessage(content="", tool_calls=[{
            "name": f"ask_{helper}", "args": {"question": "Book SU office."}, "id": "helper-1",
        }]))
    script += [
        AIMessage(content="", tool_calls=[action(ARGUMENTS)]),
        AIMessage(content="", tool_calls=[action({**ARGUMENTS, "title": "Invented placeholder"}, "invented")]),
    ]
    if helper:
        script.append(AIMessage(content="", tool_calls=[action({**ARGUMENTS, "title": "Invented by root"}, "root-invented")]))
    corrected = {**ARGUMENTS, "title": "User supplied meeting"}
    script += [AIMessage(content="", tool_calls=[action(corrected, "corrected")]), AIMessage(content="Finished.")]
    model = PlaceholderModel(responses=script)
    agent = core.build_agent(model, guardrail=False)
    inputs = {"messages": [HumanMessage("Book SU office.")]}
    out = (asyncio.run(agent.ainvoke(inputs, CONFIG, context=CONTEXT)) if asynchronous
           else agent.invoke(inputs, CONFIG, context=CONTEXT))
    assert not agent.get_state(CONFIG).interrupts, "A fabricated repair must never reach approval"
    assert [method for method, *_ in rpc] == ["search_tools"]
    assert len(model.bindings) == (4 if helper else 2)
    assert model.bindings[-1]["tool_choice"] == "none"
    assert model.bindings[-1]["tools"] == model.bindings[0]["tools"]
    assert model.seen[-1][0] == model.seen[0][0], "Keep the system/prompt cache prefix"
    if helper:
        assert model.bindings[2]["tool_choice"] == "none"
        assert model.bindings[2]["tools"] == model.bindings[1]["tools"]
        report = next(m for m in out["messages"] if isinstance(m, ToolMessage) and m.name == f"ask_{helper}")
        assert report.artifact["requires_user_input"] is True
    assert out["messages"][-1].content == "What is the title?"
    assert not out["messages"][-1].tool_calls

    def invoke(value):
        return (asyncio.run(agent.ainvoke(value, CONFIG, context=CONTEXT)) if asynchronous
                else agent.invoke(value, CONFIG, context=CONTEXT))

    invoke({"messages": [HumanMessage("Use the title User supplied meeting.")]})
    pending = agent.get_state(CONFIG).interrupts
    assert len(pending) == 1
    assert model.bindings[-1]["tool_choice"] != "none", "A new human turn must clear the restriction"
    assert pending[0].value["action_requests"][0]["args"] == {"name": TARGET, "arguments": corrected}
    assert [method for method, *_ in rpc].count("preview_tool") == 1
    before_resume = list(rpc)
    invoke(Command(resume={pending[0].id: {"decisions": [{"type": decision}]}}))
    assert not agent.get_state(CONFIG).interrupts
    assert [method for method, *_ in rpc] == [method for method, *_ in before_resume] + (["call_tool"] if decision == "approve" else [])
    if decision == "approve":
        assert rpc[-1][1] == {"name": TARGET, "arguments": corrected}


def action(arguments, ident="write-1", target=TARGET):
    return {"name": "call_api_tool", "args": {"name": target, "arguments": arguments}, "id": ident}


def graph(monkeypatch, calls, *, helper=None, responses=None):
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    script: list[BaseMessage] = ([AIMessage(content="", tool_calls=[{
        "name": f"ask_{helper}", "args": {"question": "Book the room."}, "id": "helper-1",
    }])] if helper else [])
    script += responses or [AIMessage(content="", tool_calls=calls), *[AIMessage(content="What is the title?") for _ in range(4)]]
    model = ObservedModel(responses=script)
    return core.build_agent(model, guardrail=False), model


@pytest.fixture
def rpc(monkeypatch):
    sent = []

    def request(method, payload, token=None, **credentials):
        sent.append((method, deepcopy(payload), token, credentials))
        if method == "search_tools":
            assert token is None and credentials == {}
            assert payload == {"query": TARGET}
            return {"tools": [{"name": TARGET, "inputSchema": deepcopy(SCHEMA)}]}
        if method == "preview_tool":
            return {"name": payload["name"], "arguments": payload["arguments"], "description": "Book SU office."}
        assert method == "call_tool"
        return {"done": True}

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    return sent


def discovery(schema=SCHEMA, ident="discover-1", name="search_api_tools", status="success", paired=True):
    return [AIMessage(content="", tool_calls=[{"name": name, "args": {"query": TARGET}, "id": ident}]),
            ToolMessage(content=json.dumps({"tools": [{"name": TARGET, "inputSchema": schema}]}),
                        name=name, tool_call_id=ident if paired else "unmatched", status=status)]


@pytest.mark.parametrize("trusted", [True, False])
def test_only_paired_successful_discovery_supplies_schema(monkeypatch, rpc, trusted):
    agent, _ = graph(monkeypatch, [action(ARGUMENTS)])
    history = discovery(paired=trusted)
    agent.invoke({"messages": [HumanMessage("Book SU office."), *history]}, CONFIG, context=CONTEXT)
    assert not agent.get_state(CONFIG).interrupts
    assert [method for method, *_ in rpc] == ([] if trusted else ["search_tools"])


def test_root_missing_title_reaches_model_without_preview_interrupt_or_write(monkeypatch, rpc):
    agent, model = graph(monkeypatch, [action(ARGUMENTS)])
    out = agent.invoke({"messages": [HumanMessage("Book SU office.")]}, CONFIG, context=CONTEXT)
    assert not agent.get_state(CONFIG).interrupts
    assert [method for method, *_ in rpc] == ["search_tools"]
    feedback = [m for m in model.seen[-1] if isinstance(m, ToolMessage)]
    assert len(feedback) == 1 and feedback[0].tool_call_id == "write-1"
    assert "title" in feedback[0].content and "required" in feedback[0].content
    assert all(value not in feedback[0].content for value in ARGUMENTS.values())
    assert out["messages"][-1].content == "What is the title?"


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_valid_write_uses_durable_preview_once_and_original_arguments(monkeypatch, rpc, decision):
    from langgraph.types import Command

    arguments = {**ARGUMENTS, "title": "Planning"}
    agent, _ = graph(monkeypatch, [action(arguments)])
    agent.invoke({"messages": [HumanMessage("Book SU office.")]}, CONFIG, context=CONTEXT)
    paused = agent.get_state(CONFIG)
    assert len(paused.interrupts) == 1
    assert [method for method, *_ in rpc] == ["search_tools", "preview_tool"]
    request = paused.interrupts[0].value["action_requests"][0]
    assert request["description"] == "Book SU office."
    assert request["args"] == {"name": TARGET, "arguments": arguments}
    prepared = paused.values.get("api_prepared")
    assert prepared == [{"call_id": "write-1", "target": TARGET, "arguments": arguments, "description": "Book SU office."}]
    agent.invoke(Command(resume={paused.interrupts[0].id: {"decisions": [{"type": decision}]}}), CONFIG, context=CONTEXT)
    assert not agent.get_state(CONFIG).interrupts
    assert [method for method, *_ in rpc] == ["search_tools", "preview_tool"] + (["call_tool"] if decision == "approve" else [])
    assert agent.get_state(CONFIG).values["api_prepared"] == []


@pytest.mark.parametrize("decision", [None, "approve", "reject"])
def test_async_preflight_uses_native_transport_and_durable_preview(monkeypatch, decision):
    import asyncio
    from langgraph.types import Command

    sent = []

    async def request(method, payload, token=None, **credentials):
        sent.append(method)
        if method == "search_tools":
            assert token is None and not credentials
            return {"tools": [{"name": TARGET, "inputSchema": SCHEMA}]}
        if method == "preview_tool":
            return {"name": TARGET, "arguments": payload["arguments"], "description": "Book SU office."}
        return {"done": True}

    monkeypatch.setattr(api_tools.mcp_client, "request", request)
    monkeypatch.setattr(api_tools.mcp_client, "request_sync", lambda *a, **kw: pytest.fail("Root async preflight must use native async I/O"))
    arguments = {**ARGUMENTS, **({"title": "Planning"} if decision else {})}
    agent, _ = graph(monkeypatch, [action(arguments)])

    async def run():
        out = await agent.ainvoke({"messages": [HumanMessage("Book SU office.")]}, CONFIG, context=CONTEXT)
        paused = await agent.aget_state(CONFIG)
        if decision:
            assert len(paused.interrupts) == 1
            assert sent == ["search_tools", "preview_tool"]
            await agent.ainvoke(Command(resume={paused.interrupts[0].id: {"decisions": [{"type": decision}]}}),
                                CONFIG, context=CONTEXT)
        else:
            assert not paused.interrupts
            assert "title" in next(m.content for m in out["messages"] if isinstance(m, ToolMessage))
        assert not (await agent.aget_state(CONFIG)).interrupts

    asyncio.run(run())
    assert sent == ["search_tools"] + (["preview_tool"] if decision else []) + (["call_tool"] if decision == "approve" else [])


@pytest.mark.parametrize("failure", ["error", "invalid_arguments", "name", "arguments", "empty", "timeout", "exception"])
def test_preview_failure_returns_feedback_without_approval_or_execution(monkeypatch, failure):
    sent = []
    arguments = {**ARGUMENTS, "title": "Planning"}

    def request(method, payload, *args, **kwargs):
        sent.append(method)
        assert method == "preview_tool"
        if failure == "timeout":
            raise TimeoutError("synthetic-private-diagnostic")
        if failure == "exception":
            raise ValueError("synthetic-private-diagnostic")
        if failure == "error":
            return {"error": "synthetic-private-diagnostic"}
        if failure == "invalid_arguments":
            return {"error": "End time must be after start time.", "code": "invalid_arguments"}
        result = {"name": TARGET, "arguments": arguments, "description": "Book SU office."}
        if failure == "name":
            result["name"] = "music_book_music_room"
        elif failure == "arguments":
            result["arguments"] = {**arguments, "room_id": "another-office"}
        else:
            result["description"] = " "
        return result

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    agent, model = graph(monkeypatch, [action(arguments)])
    out = agent.invoke({"messages": [HumanMessage("Book SU office."), *discovery()]}, CONFIG, context=CONTEXT)
    assert not agent.get_state(CONFIG).interrupts
    assert sent == ["preview_tool"]
    feedback = next(m for m in model.seen[-1] if isinstance(m, ToolMessage) and m.tool_call_id == "write-1")
    assert json.loads(feedback.text)["error"]
    assert "synthetic-private-diagnostic" not in str(out)
    if failure == "invalid_arguments":
        assert "End time must be after start time" in feedback.content


@pytest.mark.parametrize("schema,value", [
    ({"type": "string", "format": "date"}, "2026-02-30"),
    ({"type": "string", "format": "date-time"}, "not-a-timestamp"),
    ({"type": "string", "pattern": r"^\d{2}:\d{2}$"}, "10:00:00"),
    ({"enum": ["allowed"]}, "forbidden-private-value"),
    ({"type": "integer"}, True),
    ({"type": "boolean"}, 1),
    ({"type": "string", "minLength": 2}, "x"),
    ({"type": "number", "minimum": 2}, 1),
    ({"type": "array", "items": {"type": "integer"}}, [False]),
])
def test_complete_discovery_constraints_fail_before_preview(monkeypatch, schema, value):
    monkeypatch.setattr(api_tools.mcp_client, "request_sync", lambda *a, **kw: pytest.fail("Invalid discovered arguments need no I/O"))
    catalogue_schema = {"type": "object", "properties": {"field": schema}}
    agent, _ = graph(monkeypatch, [action({"field": value})])
    out = agent.invoke({"messages": [HumanMessage("Book the room."), *discovery(catalogue_schema)]}, CONFIG, context=CONTEXT)
    assert not agent.get_state(CONFIG).interrupts
    error = next(m.text for m in out["messages"] if isinstance(m, ToolMessage) and m.tool_call_id == "write-1")
    assert json.loads(error)["error"] and "forbidden-private-value" not in error


@pytest.mark.parametrize("catalogue", [
    {"tools": []},
    {"tools": [{"name": TARGET}]},
    {"tools": [{"name": TARGET, "inputSchema": None}]},
    {"tools": [{"name": TARGET, "inputSchema": {"type": "not-a-type"}}]},
    {"tools": [{"name": "other", "inputSchema": {"type": "object"}}]},
    {"error": "synthetic-private-diagnostic"},
])
def test_missing_or_invalid_schema_fails_closed(monkeypatch, catalogue):
    sent = []

    def request(method, payload, token=None, **credentials):
        sent.append(method)
        assert method == "search_tools" and token is None and not credentials
        return catalogue

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    agent, _ = graph(monkeypatch, [action({**ARGUMENTS, "title": "Planning"})])
    out = agent.invoke({"messages": [HumanMessage("Book the room.")]}, CONFIG, context=CONTEXT)
    assert not agent.get_state(CONFIG).interrupts and sent == ["search_tools"]
    error = next(m.text for m in out["messages"] if isinstance(m, ToolMessage))
    assert json.loads(error)["error"] and "synthetic-private-diagnostic" not in error


def test_exact_search_selects_target_not_first_ranked_match(monkeypatch):
    sent = []

    def request(method, payload, token=None, **credentials):
        sent.append(method)
        assert method == "search_tools" and payload == {"query": TARGET} and token is None and not credentials
        return {"tools": [{"name": "other", "inputSchema": {"type": "object"}}, {"name": TARGET, "inputSchema": SCHEMA}]}

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    agent, _ = graph(monkeypatch, [action(ARGUMENTS)])
    out = agent.invoke({"messages": [HumanMessage("Book the room.")]}, CONFIG, context=CONTEXT)
    assert not agent.get_state(CONFIG).interrupts and sent == ["search_tools"]
    assert "title" in next(m.content for m in out["messages"] if isinstance(m, ToolMessage))


@pytest.mark.parametrize("external", [False, True])
def test_references_are_local_only(monkeypatch, rpc, external):
    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: pytest.fail("Schema retrieval is forbidden"))
    ref = "https://schema.invalid/private" if external else "#/$defs/title"
    schema = {"type": "object", "$defs": {"title": {"type": "string"}}, "properties": {"title": {"$ref": ref}}}
    agent, _ = graph(monkeypatch, [action({"title": "Planning"})])
    agent.invoke({"messages": [HumanMessage("Book the room."), *discovery(schema)]}, CONFIG, context=CONTEXT)
    assert bool(agent.get_state(CONFIG).interrupts) is not external
    assert [method for method, *_ in rpc] == ([] if external else ["preview_tool"])


def test_invalid_parallel_batch_pairs_every_call_and_executes_none(monkeypatch, rpc):
    calls = [action({**ARGUMENTS, "title": "Planning"}, "valid"), action(ARGUMENTS, "invalid"),
             action({}, "read", "maps_scenes_scenes"),
             {"name": "get_my_ai_calendar", "args": {}, "id": "local-read"}]
    agent, model = graph(monkeypatch, calls)
    initial = {"messages": [HumanMessage("Book the room and read my calendar."), *discovery()],
               "api_prepared": [{"call_id": "invalid", "target": TARGET, "arguments": ARGUMENTS, "description": "STALE"}]}
    out = agent.invoke(initial, CONFIG, context=CONTEXT)
    assert not agent.get_state(CONFIG).interrupts
    assert [method for method, *_ in rpc] == ["preview_tool"]
    results = {m.tool_call_id: m for m in model.seen[-1] if isinstance(m, ToolMessage) and m.tool_call_id != "discover-1"}
    assert set(results) == {call["id"] for call in calls}
    assert "title" in results["invalid"].content
    assert all("Not executed" in results[ident].content for ident in ("valid", "read", "local-read"))
    assert out["api_prepared"] == []


@pytest.mark.parametrize("asynchronous", [False, True])
def test_missing_arguments_stop_preflight_io_for_remaining_parallel_calls(monkeypatch, rpc, asynchronous):
    import asyncio

    monkeypatch.setattr(core, "tool_call_token", lambda: None)

    async def request(*args, **kwargs):
        return api_tools.mcp_client.request_sync(*args, **kwargs)

    monkeypatch.setattr(api_tools.mcp_client, "request", request)
    calls = [action(ARGUMENTS, "missing"), action({**ARGUMENTS, "title": "Already supplied"}, "valid")]
    agent, model = graph(monkeypatch, calls)
    inputs = {"messages": [HumanMessage("Book both."), *discovery()]}
    out = (asyncio.run(agent.ainvoke(inputs, CONFIG, context=CONTEXT)) if asynchronous
           else agent.invoke(inputs, CONFIG, context=CONTEXT))
    assert not agent.get_state(CONFIG).interrupts
    assert rpc == [], "No more preflight requests once missing required values need the user"
    results = {m.tool_call_id: m for m in out["messages"] if isinstance(m, ToolMessage)}
    assert results["missing"].artifact["requires_user_input"] is True
    assert results["valid"].status == "error" and "Not executed" in results["valid"].content


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("reverse", [False, True])
def test_parallel_helper_results_preserve_clarification_in_either_order(monkeypatch, reverse, asynchronous):
    import asyncio

    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    monkeypatch.setattr(api_tools.mcp_client, "request_sync", lambda *a, **kw: pytest.fail("No requests while clarification is pending"))
    monkeypatch.setattr(api_tools.mcp_client, "request", lambda *a, **kw: pytest.fail("No async requests while clarification is pending"))
    calls = [{"name": f"ask_{helper}", "args": {"question": "Book and check rules."}, "id": helper}
             for helper in ("docs", "chats")]
    reports = [
        ToolMessage(content="What is the title?", name="ask_docs", tool_call_id="docs", artifact={"requires_user_input": True}),
        ToolMessage(content="Other useful report [m1].", name="ask_chats", tool_call_id="chats", artifact={"found": True}),
    ]
    model = PlaceholderModel(responses=[AIMessage(content="", tool_calls=[action({**ARGUMENTS, "title": "Invented by root"})])])
    agent = core.build_agent(model, guardrail=False)
    inputs = {"messages": [HumanMessage("Book and check rules."), AIMessage(content="", tool_calls=calls),
                           *(reversed(reports) if reverse else reports)]}
    out = (asyncio.run(agent.ainvoke(inputs, CONFIG, context=CONTEXT)) if asynchronous
           else agent.invoke(inputs, CONFIG, context=CONTEXT))
    assert not agent.get_state(CONFIG).interrupts
    assert model.bindings[-1]["tool_choice"] == "none"
    assert out["messages"][-1].content == "What is the title?"


@pytest.mark.parametrize("case", ["generic_required", "ordinary_validation"])
def test_clarification_is_schema_generic_but_not_for_other_validation_errors(monkeypatch, rpc, case):
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    arguments = {**ARGUMENTS, "title": "Supplied title"}
    schema = ({"type": "object", "required": ["organizer"], "properties": {"organizer": {"type": "string"}}}
              if case == "generic_required" else SCHEMA)
    model = PlaceholderModel(responses=[
        AIMessage(content="", tool_calls=[action({} if case == "generic_required" else {**arguments, "time_from": "10:00:00"})]),
        AIMessage(content="", tool_calls=[action(arguments, "repair")]),
    ])
    agent = core.build_agent(model, guardrail=False)
    out = agent.invoke({"messages": [HumanMessage("Book SU office."), *discovery(schema)]}, CONFIG, context=CONTEXT)
    assert (model.bindings[-1]["tool_choice"] == "none") is (case == "generic_required")
    assert bool(agent.get_state(CONFIG).interrupts) is (case == "ordinary_validation")
    assert [method for method, *_ in rpc] == (["preview_tool"] if case == "ordinary_validation" else [])
    if case == "generic_required":
        error = next(m for m in out["messages"] if isinstance(m, ToolMessage) and m.tool_call_id == "write-1")
        assert "organizer" in error.content and error.artifact["requires_user_input"] is True


@pytest.mark.parametrize("marker", ["unmatched", "wrong_name", "wire_only", "previous_turn"])
def test_only_current_matched_artifacts_require_user_input(monkeypatch, rpc, marker):
    from catix.agent.api_preflight import requires_user_input

    call = {"name": "ask_chats", "args": {"question": "Book the room."}, "id": "helper"}
    report = ToolMessage(content=json.dumps({"requires_user_input": True}), name="ask_chats", tool_call_id="helper",
                         artifact={"requires_user_input": True})
    if marker == "unmatched":
        report.tool_call_id = "unmatched"
    elif marker == "wrong_name":
        report.name = "ask_docs"
    elif marker == "wire_only":
        report.artifact = None
    messages = [HumanMessage("Book the room."), AIMessage(content="", tool_calls=[call]), report]
    if marker == "previous_turn":
        assert requires_user_input(messages)
        messages.append(HumanMessage("Use title Planning."))
    assert not requires_user_input(messages)
    agent, _ = graph(monkeypatch, [action({**ARGUMENTS, "title": "Planning"})])
    agent.invoke({"messages": [*messages, *discovery()]}, CONFIG, context=CONTEXT)
    assert len(agent.get_state(CONFIG).interrupts) == 1
    assert [method for method, *_ in rpc] == ["preview_tool"]


@pytest.mark.parametrize("asynchronous", [False, True])
def test_provider_ignoring_no_tools_cannot_retry_before_new_user(monkeypatch, rpc, asynchronous):
    import asyncio

    monkeypatch.setattr(core, "tool_call_token", lambda: None)

    async def request(*args, **kwargs):
        return api_tools.mcp_client.request_sync(*args, **kwargs)

    monkeypatch.setattr(api_tools.mcp_client, "request", request)
    agent, _ = graph(monkeypatch, [], responses=[
        AIMessage(content="", tool_calls=[action(ARGUMENTS)]),
        AIMessage(content="", tool_calls=[action({**ARGUMENTS, "title": "Invented despite tool_choice"}, "retry")]),
        AIMessage(content="What is the title?"),
    ])
    inputs = {"messages": [HumanMessage("Book SU office.")]}
    out = (asyncio.run(agent.ainvoke(inputs, CONFIG, context=CONTEXT)) if asynchronous
           else agent.invoke(inputs, CONFIG, context=CONTEXT))
    assert not agent.get_state(CONFIG).interrupts
    assert [method for method, *_ in rpc] == ["search_tools"]
    assert not out["messages"][-1].tool_calls
    assert out["messages"][-1].content == "What is the title?"


def test_repeated_invalid_calls_remain_bounded_by_global_model_budget(monkeypatch, rpc):
    monkeypatch.setattr(core.settings, "agent_max_model_calls", 3)
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    script = [AIMessage(content="", tool_calls=[action(ARGUMENTS, f"invalid-{i}")]) for i in range(8)]
    agent, model = graph(monkeypatch, [], responses=script)
    out = agent.invoke({"messages": [HumanMessage("Book the room."), *discovery()]}, CONFIG, context=CONTEXT)
    assert not agent.get_state(CONFIG).interrupts and rpc == []
    assert len(model.seen) == 3
    assert not out["messages"][-1].tool_calls


def test_new_batch_never_reuses_previous_approval_or_prepared_description(monkeypatch, rpc):
    from langgraph.types import Command

    first = {**ARGUMENTS, "title": "First meeting"}
    second = {**ARGUMENTS, "title": "Second meeting"}
    script = [AIMessage(content="", tool_calls=[action(first, "first")]),
              AIMessage(content="", tool_calls=[action(second, "second")]), AIMessage(content="Done.")]
    agent, _ = graph(monkeypatch, [], responses=script)
    agent.invoke({"messages": [HumanMessage("Book both meetings."), *discovery()]}, CONFIG, context=CONTEXT)
    paused = agent.get_state(CONFIG).interrupts[0]
    agent.invoke(Command(resume={paused.id: {"decisions": [{"type": "approve"}]}}), CONFIG, context=CONTEXT)
    second_pause = agent.get_state(CONFIG)
    assert len(second_pause.interrupts) == 1 and second_pause.interrupts[0].id != paused.id
    assert second_pause.values["api_prepared"][0]["call_id"] == "second"
    assert second_pause.values["api_prepared"][0]["arguments"] == second
    assert [method for method, *_ in rpc] == ["preview_tool", "call_tool", "preview_tool"]
    agent.invoke(Command(resume={second_pause.interrupts[0].id: {"decisions": [{"type": "reject"}]}}), CONFIG, context=CONTEXT)
    assert [method for method, *_ in rpc] == ["preview_tool", "call_tool", "preview_tool"]
    assert not agent.get_state(CONFIG).interrupts


def test_pending_approval_survives_fresh_graph_and_preflight_outage(monkeypatch, rpc):
    from langgraph.types import Command

    arguments = {**ARGUMENTS, "title": "Planning"}
    agent, _ = graph(monkeypatch, [action(arguments)])
    agent.invoke({"messages": [HumanMessage("Book the room.")]}, CONFIG, context=CONTEXT)
    paused = agent.get_state(CONFIG).interrupts[0]
    fresh = core.build_agent(ObservedModel(responses=[AIMessage(content="Done.")]), guardrail=False, checkpointer=agent.checkpointer)
    writes = []

    def request(method, payload, *args, **kwargs):
        assert method == "call_tool", "Resume must consume the pending interrupt, not re-run preflight"
        writes.append(payload)
        return {"done": True}

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    fresh.invoke(Command(resume={paused.id: {"decisions": [{"type": "approve"}]}}), CONFIG, context=CONTEXT)
    assert writes == [{"name": TARGET, "arguments": arguments}]
    assert not fresh.get_state(CONFIG).interrupts
    assert [method for method, *_ in rpc] == ["search_tools", "preview_tool"]
