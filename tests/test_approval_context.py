"""A blank model response must still leave an informative, exact-target consent card."""

import asyncio
import json
from copy import deepcopy


import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.runtime import Runtime
from pydantic import SecretStr

from catix.agent import api_tools
from catix.agent.api_preflight import ApiPreflightMiddleware
from catix.agent.tools import AgentContext


TRAINING = {"training_id": 48591, "name": "Frisbee", "date": "2026-11-09 Mon",
            "time": "08:00-10:00", "place": "[SC] Big Hall", "places_left": 16,
            "starts_at": "2026-11-09T08:00:00+03:00", "ends_at": "2026-11-09T10:00:00+03:00",
            "checked_in": False, "can_check_in": True}
SCHEMA = {"type": "object", "additionalProperties": False,
          "properties": {"training_id": {"type": "integer", "minimum": 1},
                         "cancel": {"type": "boolean", "default": False}}, "required": ["training_id"]}
CALL = {"name": "call_api_tool", "id": "write", "args": {
    "name": "sport_sport_checkin", "arguments": {"training_id": 48591}}}
RUNTIME = Runtime(context=AgentContext(innohassle_token=SecretStr("synthetic-ih"),
                                     sport_token=SecretStr("synthetic-sport")))


def read_messages(name, arguments, data, ident="read"):
    return [AIMessage(content="", tool_calls=[{
        "name": "call_api_tool", "id": ident, "args": {"name": name, "arguments": arguments},
    }]), ToolMessage(content=json.dumps(data), name="call_api_tool", tool_call_id=ident)]


def initial(messages=None):
    from tests.test_sport_calendar_guard import agenda_data, read_messages as host_read

    calendars = host_read("get_my_schedule", agenda_data(classes=[]), "agenda")
    return {"messages": [HumanMessage("Запиши на подходящую тренировку."),
                         AIMessage(content="", tool_calls=[{"name": "search_api_tools", "id": "schema", "args": {"query": "sport"}}]),
                         ToolMessage(content=json.dumps({"tools": [{"name": "sport_sport_checkin", "inputSchema": SCHEMA}]}),
                                     name="search_api_tools", tool_call_id="schema"),
                         *calendars, *(messages or []), AIMessage(content="", tool_calls=[deepcopy(CALL)])]}


def prepare(state, asynchronous):
    middleware = ApiPreflightMiddleware()
    return (asyncio.run(middleware.aafter_model(state, RUNTIME)) if asynchronous
            else middleware.after_model(state, RUNTIME))


@pytest.mark.parametrize("asynchronous", [False, True])
def test_blank_model_content_uses_exact_training_from_current_paired_read(monkeypatch, asynchronous):
    monkeypatch.setattr(api_tools.mcp_client, "request_sync", lambda *a, **kw: pytest.fail("Already read: no extra request"))
    monkeypatch.setattr(api_tools.mcp_client, "request", lambda *a, **kw: pytest.fail("Already read: no extra request"))
    messages = read_messages("sport_get_sport_trainings", {"date_from": "2026-11-09", "date_to": "2026-11-09"},
                             {"range": ["2026-11-09", "2026-11-09"], "trainings": [
                                 {**TRAINING, "training_id": 10, "name": "Wrong sport"}, TRAINING]})
    state = initial(messages)
    original = deepcopy(state)
    result = prepare(state, asynchronous)
    assert "jump_to" not in result
    description = api_tools._describe_mutation(CALL, result, RUNTIME)
    assert "Записать" in description and "48591" in description
    for value in ("Frisbee", "2026-11-09", "08:00", "10:00", "[SC] Big Hall"):
        assert value in description
    assert "Wrong sport" not in description and "16" not in description
    assert result["api_prepared"][0]["arguments"] == {"training_id": 48591}
    assert state == original
    assert api_tools._describe_mutation(CALL, result, RUNTIME) == description


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("missing", ["absent", "previous_turn", "wrong_tool", "unpaired", "failed", "wrong_id", "incomplete", "duplicate"])
def test_unusable_context_gets_one_exact_authenticated_read(monkeypatch, asynchronous, missing):
    messages = read_messages("sport_get_sport_trainings", {}, {"trainings": [TRAINING]})
    if missing == "absent":
        messages = []
    elif missing == "previous_turn":
        messages.append(HumanMessage("Теперь запиши."))
    elif missing == "wrong_tool":
        messages[0].tool_calls[0]["args"]["name"] = "events_get_university_events"
    elif missing == "unpaired":
        messages[1].tool_call_id = "not-the-read"
    elif missing == "failed":
        messages[1].status = "error"
    elif missing == "wrong_id":
        messages[1].content = json.dumps({"trainings": [{**TRAINING, "training_id": 1}]})
    elif missing == "incomplete":
        messages[1].content = json.dumps({"trainings": [{**TRAINING, "place": ""}]})
    else:
        messages[1].content = json.dumps({"trainings": [TRAINING, {**TRAINING, "name": "Conflicting"}]})
    sent = []

    def request(method, payload, token=None, **credentials):
        sent.append((method, payload, token, credentials))
        assert method == "call_tool"
        assert payload == {"name": "sport_get_training", "arguments": {"training_id": 48591}}
        assert token == "synthetic-ih" and credentials == {"sport_token": "synthetic-sport"}
        return {"training": TRAINING}

    async def arequest(*args, **kwargs):
        return request(*args, **kwargs)

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    monkeypatch.setattr(api_tools.mcp_client, "request", arequest)
    state = initial(messages)
    state["messages"][-1].tool_calls[0]["args"]["arguments"]["cancel"] = True
    result = prepare(state, asynchronous)
    assert "jump_to" not in result
    assert "Frisbee" in api_tools._describe_mutation(state["messages"][-1].tool_calls[0], result, RUNTIME)
    assert len(sent) == 1


EVENT = {"id": "a" * 24, "title": "Robotics workshop", "start": "2026-11-09 17:00 Mon",
         "end": "2026-11-09 19:00 Mon", "location": "Room 314"}
BOOKING = {"service": "room", "booking_id": "AAMk=opaque+ID", "title": "Study group",
           "date": "2026-11-09 Mon", "time": "19:00-20:00", "room": "314"}


def other_state(target, arguments, read_name, data):
    schema = {"type": "object", "properties": {}}
    if target == "events_enroll_in_event":
        schema["properties"]["leave"] = {"type": "boolean", "default": False}
    call = {"name": "call_api_tool", "id": "write", "args": {"name": target, "arguments": arguments}}
    return {"messages": [HumanMessage("Сделай это."),
                         AIMessage(content="", tool_calls=[{"name": "search_api_tools", "id": "schema", "args": {"query": target}}]),
                         ToolMessage(content=json.dumps({"tools": [{"name": target, "inputSchema": schema}]}),
                                     name="search_api_tools", tool_call_id="schema"),
                         *read_messages(read_name, {}, data), AIMessage(content="", tool_calls=[call])]}


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("case", ["event", "leave_event", "room", "music_room"])
def test_event_and_booking_cards_include_exact_object_details(monkeypatch, asynchronous, case):
    monkeypatch.setattr(api_tools.mcp_client, "request_sync", lambda *a, **kw: pytest.fail("All details already read"))
    monkeypatch.setattr(api_tools.mcp_client, "request", lambda *a, **kw: pytest.fail("All details already read"))
    if case in {"event", "leave_event"}:
        state = other_state("events_enroll_in_event", {"event_id": EVENT["id"], "leave": case == "leave_event"},
                            "events_get_university_events", {"events": [EVENT]})
        expected = ["Robotics workshop", "2026-11-09", "17:00", "19:00", "Room 314"]
    else:
        booking = BOOKING if case == "room" else {**BOOKING, "service": "music_room", "booking_id": "7", "title": "Music room"}
        state = other_state("account_cancel_booking", {"service": case, "booking_id": booking["booking_id"]},
                            "account_get_my_schedule", {"bookings": [booking]})
        expected = [booking["title"], "2026-11-09", "19:00", "20:00", "314" if case == "room" else "спорткомплекс"]
    result = prepare(state, asynchronous)
    assert "jump_to" not in result
    description = api_tools._describe_mutation(state["messages"][-1].tool_calls[0], result, RUNTIME)
    for value in expected:
        assert value in description
    assert ("Отменить" in description) is (case != "event")


@pytest.mark.parametrize("failure", ["error", "missing", "wrong_id", "wrong_type", "malformed_date", "timeout"])
@pytest.mark.parametrize("asynchronous", [False, True])
def test_detail_read_failure_never_leaves_a_blind_approval(monkeypatch, failure, asynchronous):
    sent = []
    result = {"training": TRAINING}
    if failure == "error":
        result = {"error": "private upstream diagnostic"}
    elif failure == "missing":
        result = {"training": {**TRAINING, "name": None}}
    elif failure == "wrong_id":
        result = {"training": {**TRAINING, "training_id": 1}}
    elif failure == "wrong_type":
        result = {"training": {**TRAINING, "training_id": "48591"}}
    elif failure == "malformed_date":
        result = {"training": {**TRAINING, "starts_at": "invalid", "date": "2026-02-30 Mon"}}

    def request(method, payload, *args, **kwargs):
        sent.append(payload)
        assert payload["name"] == "sport_get_training", "No write before informed consent"
        if failure == "timeout":
            raise TimeoutError("private upstream diagnostic")
        return result

    async def arequest(*args, **kwargs):
        return request(*args, **kwargs)

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    monkeypatch.setattr(api_tools.mcp_client, "request", arequest)
    state = initial()
    state["messages"][-1].tool_calls[0]["args"]["arguments"]["cancel"] = True
    prepared = prepare(state, asynchronous)
    assert prepared["api_prepared"] == [] and prepared["jump_to"] == "model"
    assert len(sent) == 1 and "private upstream diagnostic" not in str(prepared)
    assert prepared["messages"][0].tool_call_id == "write" and prepared["messages"][0].status == "error"


@pytest.mark.parametrize("newer", ["failed", "empty", "malformed", "changed", "other_detail_target", "mutation"])
def test_newer_reads_or_mutations_do_not_reuse_obsolete_context(newer):
    from catix.agent.api_context import from_messages

    messages = [HumanMessage("Cancel my training."),
                *read_messages("sport_get_sport_trainings", {}, {"trainings": [TRAINING]}, "first")]
    if newer == "other_detail_target":
        # Even a matching returned object cannot substitute for a different request's target.
        messages = [HumanMessage("Cancel my training."),
                    *read_messages("sport_get_training", {"training_id": 1}, {"training": TRAINING})]
    elif newer == "mutation":
        messages += read_messages("sport_sport_checkin", {"training_id": 48591}, {"done": True})
    else:
        messages += read_messages("sport_get_sport_trainings", {}, {"trainings": []})
        if newer == "failed":
            messages[-1].status = "error"
        elif newer == "malformed":
            messages[-1].content = "not json"
        elif newer == "changed":
            messages[-1].content = json.dumps({"trainings": [{**TRAINING, "place": None}]})
    assert from_messages("sport_sport_checkin", {"training_id": 48591}, messages) is None


@pytest.mark.parametrize("case", ["overnight", "all_day", "no_time", "naive", "negative_duration"])
def test_dates_preserve_full_interval_and_do_not_infer_missing_times(case):
    from catix.agent.api_context import from_result

    training = deepcopy(TRAINING)
    if case == "overnight":
        training.update(starts_at="2026-11-09T23:00:00+03:00", ends_at="2026-11-10T02:00:00+03:00")
    elif case == "all_day":
        training.update(starts_at="2026-11-09T00:00:00+03:00", ends_at="2026-11-10T00:00:00+03:00", all_day=True)
        training.pop("time")
    elif case == "no_time":
        for key in ("starts_at", "ends_at", "time"):
            training.pop(key)
    elif case == "naive":
        training["starts_at"] = "2026-11-09T08:00:00"
    else:
        training["ends_at"] = training["starts_at"]
    description = from_result("sport_sport_checkin", {"training_id": 48591}, "sport_get_training", {"training": training}, "ru")
    if case in {"overnight", "all_day"}:
        assert description and "2026-11-09" in description and "2026-11-10" in description
        assert ("весь день" in description) is (case == "all_day")
    else:
        assert description is None


@pytest.mark.parametrize("decision", ["approve", "reject"])
@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("helper", [None, "docs", "chats"])
def test_graph_saves_details_and_resume_never_repeats_preparation(monkeypatch, decision, asynchronous, helper):
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langgraph.types import Command
    from catix.agent import core

    class Model(FakeMessagesListChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    sent = []

    def request(method, payload, token=None, **credentials):
        sent.append((method, deepcopy(payload)))
        if method == "search_tools":
            assert token is None and not credentials
            return {"tools": [{"name": "sport_sport_checkin", "inputSchema": SCHEMA}]}
        assert token == "synthetic-ih" and credentials == {"sport_token": "synthetic-sport"}
        if payload["name"] == "sport_get_training":
            return {"training": TRAINING}
        assert payload == {"name": "sport_sport_checkin", "arguments": {"training_id": 48591, "cancel": True}}
        return {"done": True, "training_id": 48591, "signed_up": False}

    async def arequest(*args, **kwargs):
        return request(*args, **kwargs)

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    monkeypatch.setattr(api_tools.mcp_client, "request", arequest)
    call = deepcopy(CALL)
    call["args"]["arguments"]["cancel"] = True
    script: list[BaseMessage] = []
    if helper:
        script.append(AIMessage(content="", tool_calls=[{"name": f"ask_{helper}", "id": "helper", "args": {"question": "Cancel my training."}}]))
    script.extend([AIMessage(content="", tool_calls=[call]), AIMessage(content="Finished.")])
    graph = core.build_agent(Model(responses=script), guardrail=False)
    config = {"configurable": {"thread_id": "context-resume"}}

    def invoke(agent, value):
        return (asyncio.run(agent.ainvoke(value, config, context=RUNTIME.context)) if asynchronous
                else agent.invoke(value, config, context=RUNTIME.context))

    invoke(graph, {"messages": [HumanMessage("Cancel my training.")]})
    paused = graph.get_state(config)
    assert len(paused.interrupts) == 1
    description = paused.interrupts[0].value["action_requests"][0]["description"]
    assert "Frisbee" in description and "2026-11-09" in description and "Big Hall" in description
    assert [payload.get("name") for method, payload in sent if method == "call_tool"] == ["sport_get_training"]
    before = list(sent)
    fresh = core.build_agent(Model(responses=[AIMessage(content="Finished.")]), guardrail=False, checkpointer=graph.checkpointer)
    invoke(fresh, Command(resume={paused.interrupts[0].id: {"decisions": [{"type": decision}]}}))
    assert not fresh.get_state(config).interrupts
    assert sent[:len(before)] == before
    extra = sent[len(before):]
    assert extra == ([("call_tool", call["args"])] if decision == "approve" else [])


@pytest.mark.parametrize("target,data", [
    ("sport_get_training", {"training": TRAINING}),
    ("events_get_event", {"event": EVENT}),
    ("account_get_booking", {"booking": BOOKING}),
])
def test_new_exact_reads_are_evidence_only_for_their_own_shape(target, data):
    from catix.agent.core import _read_parts

    assert _read_parts(target, data)
    assert _read_parts(target, {"done": True}) is None
    assert _read_parts(target, {"training": {"training_id": True}}) is None
    assert _read_parts(target, {"booking": {"service": "room", "booking_id": "id-only"}}) is None


@pytest.mark.parametrize("language", ["ru", "en"])
def test_raw_event_list_uses_exact_event_and_known_timezone(language):
    from catix.agent.api_context import from_messages

    raw = {"action_id": "events.events_list_events", "data": [{"id": EVENT["id"], "data": {
        "name": "Robotics workshop", "starts_at": "2026-11-09T14:00:00Z", "duration_hours": 2,
        "location": {"display_name": "Room 314"}}}], "total": 1, "truncated": False}
    messages = [HumanMessage("Join."), *read_messages("events_events_list_events", {}, raw)]
    description = from_messages("events_enroll_in_event", {"event_id": EVENT["id"]}, messages, language)
    assert description and all(value in description for value in ("Robotics workshop", "2026-11-09", "17:00", "19:00", "Room 314"))
    raw["data"][0]["data"]["name"] = None
    messages = [HumanMessage("Join."), *read_messages("events_events_list_events", {}, raw)]
    assert from_messages("events_enroll_in_event", {"event_id": EVENT["id"]}, messages, language) is None


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("case", ["event", "room", "music_room"])
def test_other_exact_reads_forward_only_their_own_credentials(monkeypatch, asynchronous, case):
    if case == "event":
        arguments = {"event_id": EVENT["id"]}
        state = other_state("events_enroll_in_event", arguments, "maps_scenes_scenes", {})
        lookup = {"name": "events_get_event", "arguments": arguments}
        result = {"event": EVENT}
    else:
        item = BOOKING if case == "room" else {**BOOKING, "service": "music_room", "booking_id": "7"}
        arguments = {"service": case, "booking_id": item["booking_id"]}
        state = other_state("account_cancel_booking", arguments, "maps_scenes_scenes", {})
        lookup = {"name": "account_get_booking", "arguments": arguments}
        result = {"booking": item}
    sent = []

    def request(method, payload, token=None, **credentials):
        sent.append(payload)
        assert method == "call_tool" and payload == lookup
        assert token == (None if case == "event" else "synthetic-ih")
        assert credentials == {}, "Never forward Sport credentials to another service"
        return result

    async def arequest(*args, **kwargs):
        return request(*args, **kwargs)

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    monkeypatch.setattr(api_tools.mcp_client, "request", arequest)
    prepared = prepare(state, asynchronous)
    assert "jump_to" not in prepared
    assert len(sent) == 1
    assert "2026-11-09" in prepared["api_prepared"][0]["description"]


def test_context_failure_rejects_whole_parallel_batch_without_writes(monkeypatch):
    state = other_state("events_enroll_in_event", {"event_id": EVENT["id"]}, "maps_scenes_scenes", {})
    call = state["messages"][-1].tool_calls[0]
    other = {"name": "call_api_tool", "id": "read-other", "args": {"name": "maps_scenes_scenes", "arguments": {}}}
    state["messages"][-1].tool_calls.append(other)
    sent = []

    def request(method, payload, *args, **kwargs):
        sent.append(payload)
        assert payload["name"] == "events_get_event"
        return {"error": "not available"}

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    result = prepare(state, False)
    assert result["api_prepared"] == [] and result["jump_to"] == "model"
    assert {m.tool_call_id for m in result["messages"]} == {call["id"], other["id"]}
    assert len(sent) == 1
