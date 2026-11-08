"""Host Music Room calendar policy; synthetic services, never live bookings."""

import asyncio
import json
from copy import deepcopy
from types import SimpleNamespace
from typing import Any

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.runtime import Runtime
from pydantic import SecretStr

from catix.agent import api_tools, schedule_tools
from catix.agent.api_preflight import ApiPreflightMiddleware
from catix.agent.tools import AgentContext

DAY = "2026-11-09"
PERIOD = {"date_from": DAY, "date_to": DAY}
ARGUMENTS = {"day": DAY, "time_from": "17:00", "time_to": "18:00"}
SCHEMA = {"type": "object", "additionalProperties": False,
          "properties": {"day": {"type": "string", "format": "date"},
                         "time_from": {"type": "string", "pattern": r"^\d{2}:\d{2}$"},
                         "time_to": {"type": "string", "pattern": r"^\d{2}:\d{2}$"}},
          "required": ["day", "time_from", "time_to"]}
CONTEXT = AgentContext(innohassle_id="synthetic-owner", innohassle_token=SecretStr("synthetic-ih"),
                       sport_token=SecretStr("synthetic-sport"))
RUNTIME = Runtime(context=CONTEXT)


def interval(start, end, **fields):
    return {"starts_at": f"{DAY}T{start}:00+03:00", "ends_at": f"{DAY}T{end}:00+03:00", **fields}


def agenda_data(events=()):
    return schedule_tools.merge_schedule([DAY, DAY], {"range": [DAY, DAY], "schedule": [], "bookings": []},
                                         {"range": [DAY, DAY], "events": list(events)})


def action(arguments=None, ident="write"):
    return {"name": "call_api_tool", "id": ident,
            "args": {"name": "music_book_music_room", "arguments": deepcopy(ARGUMENTS if arguments is None else arguments)}}


def read_messages(data, ident="agenda", arguments=None):
    return [AIMessage(content="", tool_calls=[{"name": "get_my_schedule", "id": ident, "args": arguments or PERIOD}]),
            ToolMessage(content=json.dumps(data), name="get_my_schedule", tool_call_id=ident)]


def history(events=()):
    return {"messages": [HumanMessage("Book the music room tomorrow from 17:00 to 18:00."),
        AIMessage(content="", tool_calls=[{"name": "search_api_tools", "id": "schema", "args": {"query": "music"}}]),
        ToolMessage(content=json.dumps({"tools": [{"name": "music_book_music_room", "inputSchema": SCHEMA}]}),
                    name="search_api_tools", tool_call_id="schema"),
        *read_messages(agenda_data(events)), AIMessage(content="", tool_calls=[action()])]}


def recommendation_messages(agenda, ident="recommendation", arguments=None):
    arguments = {"day": DAY, "duration_minutes": 60} if arguments is None else arguments
    return [AIMessage(content="", tool_calls=[{"name": "get_my_available_music_windows", "id": ident, "args": arguments}]),
            ToolMessage(content=json.dumps({"available": [], "error": "Model-visible content is not calendar evidence"}),
                        name="get_my_available_music_windows", tool_call_id=ident,
                        artifact={"music": {"day": DAY}, "agenda": agenda, "music_arguments": deepcopy(arguments)})]


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("conflicting", [False, True])
def test_native_music_recommendation_reuses_original_agenda_artifact(monkeypatch, asynchronous, conflicting):
    monkeypatch.setattr(schedule_tools, "read_my_schedule", lambda *a: pytest.fail("A matched complete artifact must be reused"))
    state = history()
    state["messages"][3:5] = recommendation_messages(agenda_data([interval("17:30", "18:30")] if conflicting else []))
    result = prepare(state, asynchronous)
    if conflicting:
        assert json.loads(result["messages"][0].content)["code"] == "schedule_conflict"
    else:
        assert result["api_prepared"][0]["arguments"] == ARGUMENTS


def prepare(state, asynchronous=False, runtime=RUNTIME):
    middleware = ApiPreflightMiddleware()
    return (asyncio.run(middleware.aafter_model(state, runtime)) if asynchronous else middleware.after_model(state, runtime))


@pytest.mark.parametrize("fault", ["unpaired", "wrapper", "prior_turn", "failed_latest", "no_artifact_latest",
                                  "wrong_day", "wrong_duration", "wrong_agenda_range", "content_only"])
def test_only_exact_current_host_recommendation_artifacts_are_evidence(monkeypatch, fault):
    fresh = []
    monkeypatch.setattr(schedule_tools, "read_my_schedule", lambda *a: fresh.append(a) or {"error": "Unavailable"})
    state = history()
    pair = recommendation_messages(agenda_data())
    call, message = pair
    if fault == "unpaired":
        message.tool_call_id = "unmatched"
    elif fault == "wrapper":
        call.tool_calls[0].update(name="call_api_tool", args={"name": "get_my_available_music_windows", "arguments": {"day": DAY}})
        message.name = "call_api_tool"
    elif fault == "prior_turn":
        pair.append(HumanMessage("Now book it."))
    elif fault in {"failed_latest", "no_artifact_latest"}:
        newer = recommendation_messages(agenda_data(), ident="latest")
        if fault == "failed_latest":
            newer[1].status = "error"
        else:
            newer[1].artifact = None
        pair += newer
    elif fault == "wrong_day":
        message.artifact["music_arguments"]["day"] = "2026-11-10"
    elif fault == "wrong_duration":
        message.artifact["music_arguments"]["duration_minutes"] = 30
    elif fault == "wrong_agenda_range":
        call.tool_calls[0]["args"]["day"] = "2026-11-10"
        message.artifact["music_arguments"]["day"] = "2026-11-10"
    elif fault == "content_only":
        message.content = json.dumps(message.artifact)
        message.artifact = None
    state["messages"][3:5] = pair
    result = prepare(state)
    assert len(fresh) == 1, "Untrusted evidence must trigger a fresh read, not reuse"
    assert result["api_prepared"] == []
    assert json.loads(result["messages"][0].content)["code"] == "schedule_unverified"


@pytest.mark.parametrize("target", ["rooms_book_room", "music_book_music_room", "account_cancel_booking",
                                    "sport_sport_checkin", "events_enroll_in_event", "events_update_draft",
                                    "add_to_ai_calendar", "update_ai_calendar", "remove_from_ai_calendar"])
@pytest.mark.parametrize("source", ["host", "artifact"])
def test_calendar_mutations_invalidate_older_agenda(monkeypatch, target, source):
    fresh = []
    monkeypatch.setattr(schedule_tools, "read_my_schedule", lambda *a: fresh.append(a) or {"error": "Unavailable"})
    state = history()
    if source == "artifact":
        state["messages"][3:5] = recommendation_messages(agenda_data())
    local = target.endswith("ai_calendar")
    name = target if local else "call_api_tool"
    args = {} if local else {"name": target, "arguments": {}}
    state["messages"][-1:-1] = [AIMessage(content="", tool_calls=[{"id": "intervening-write", "name": name, "args": args}]),
                                ToolMessage(content=json.dumps({"done": True}), name=name, tool_call_id="intervening-write")]
    result = prepare(state)
    assert len(fresh) == 1
    assert result["api_prepared"] == []
    assert json.loads(result["messages"][0].content)["code"] == "schedule_unverified"


@pytest.mark.parametrize("helper", ["ask_docs", "ask_chats"])
@pytest.mark.parametrize("outcome", ["confirmed", "unknown"])
def test_helper_mutation_receipts_invalidate_older_agenda(monkeypatch, helper, outcome):
    fresh = []
    monkeypatch.setattr(schedule_tools, "read_my_schedule", lambda *a: fresh.append(a) or {"error": "Unavailable"})
    state = history()
    state["messages"][-1:-1] = [
        AIMessage(content="", tool_calls=[{"id": "helper", "name": helper, "args": {"question": "Book a room"}}]),
        ToolMessage(content="Finished", name=helper, tool_call_id="helper",
                    artifact={"action_receipts": [{"name": "rooms_book_room", "outcome": outcome}]}),
    ]
    result = prepare(state)
    assert len(fresh) == 1
    assert json.loads(result["messages"][0].content)["code"] == "schedule_unverified"


@pytest.mark.parametrize("field", ["date_from", "date_to"])
def test_schedule_result_must_match_its_original_read_target(monkeypatch, field):
    fresh = []
    monkeypatch.setattr(schedule_tools, "read_my_schedule", lambda *a: fresh.append(a) or {"error": "Unavailable"})
    state = history()
    state["messages"][3].tool_calls[0]["args"][field] = "2026-11-10"
    result = prepare(state)
    assert len(fresh) == 1
    assert json.loads(result["messages"][0].content)["code"] == "schedule_unverified"


@pytest.mark.parametrize("kind", ["music", "sport"])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("overlapping", [False, True])
@pytest.mark.parametrize("asynchronous", [False, True])
def test_parallel_music_and_sport_proposals_check_each_other(monkeypatch, kind, reverse, overlapping, asynchronous):
    from catix.agent import core
    from tests.test_mcp_preflight_graph import ObservedModel
    from tests.test_sport_calendar_guard import BASKETBALL, SCHEMA as SPORT_SCHEMA, action as sport_action, read_messages as sport_reads

    state = history()
    if kind == "sport":
        schemas = json.loads(state["messages"][2].content)
        schemas["tools"].append({"name": "sport_sport_checkin", "inputSchema": SPORT_SCHEMA})
        state["messages"][2].content = json.dumps(schemas)
        state["messages"][-1:-1] = sport_reads("sport_get_sport_trainings", {"range": [DAY, DAY], "trainings": [BASKETBALL]}, "sport")
        second = sport_action(46975, ident="second")
        first = action() if overlapping else action({**ARGUMENTS, "time_from": "18:30", "time_to": "19:30"})
    else:
        first = action()
        second = action({**ARGUMENTS, "time_from": "17:30" if overlapping else "18:00", "time_to": "19:00"}, ident="second")
    state["messages"][-1].tool_calls = [second, first] if reverse else [first, second]
    result = prepare(state)
    if overlapping:
        assert result["api_prepared"] == [] and result["jump_to"] == "model"
        assert len(result["messages"]) == 2
        assert all(json.loads(m.content)["code"] == "schedule_conflict" for m in result["messages"])
    else:
        assert len(result["api_prepared"]) == 2
        assert "jump_to" not in result

    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    monkeypatch.setattr(api_tools.mcp_client, "request_sync", lambda *a, **kw: pytest.fail("All preflight reads supplied; no write before consent"))
    model = ObservedModel(responses=[state["messages"].pop(), AIMessage(content="Checked.")])
    agent = core.build_agent(model, guardrail=False)
    config = {"configurable": {"thread_id": "music-batch"}}
    out = (asyncio.run(agent.ainvoke(state, config, context=CONTEXT)) if asynchronous
           else agent.invoke(state, config, context=CONTEXT))
    if overlapping:
        assert not agent.get_state(config).interrupts
        refusals = [json.loads(m.content) for m in out["messages"] if isinstance(m, ToolMessage)
                    and m.tool_call_id in {"write", "second"} and isinstance(m.content, str)]
        assert len(refusals) == 2 and all(r["code"] == "schedule_conflict" for r in refusals)
    else:
        assert len(agent.get_state(config).interrupts) == 1


@pytest.mark.parametrize("asynchronous", [False, True])
def test_initial_ai_calendar_conflict_never_reaches_approval(monkeypatch, asynchronous):
    monkeypatch.setattr(api_tools.mcp_client, "request_sync", lambda *a, **kw: pytest.fail("Reads already present"))
    state = history([interval("17:30", "19:00", title="Appointment")])
    original = deepcopy(state)
    result = prepare(state, asynchronous)
    assert result.get("jump_to") == "model", "Overlapping music booking must not receive ordinary approval"
    assert result["api_prepared"] == []
    refusal = json.loads(result["messages"][0].content)
    assert refusal["code"] == "schedule_conflict" and refusal["done"] is False
    assert refusal["conflicts"][0]["title"] == "Appointment"
    assert state == original


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("conflicting", [False, True])
def test_missing_agenda_is_read_through_unified_host(monkeypatch, asynchronous, conflicting):
    calls = []

    def read(runtime, start, end):
        calls.append((runtime, str(start), str(end)))
        return agenda_data([interval("17:30", "18:30")] if conflicting else [])

    monkeypatch.setattr(schedule_tools, "read_my_schedule", read)
    state = history()
    state["messages"][3:5] = []
    result = prepare(state, asynchronous)
    assert calls == [(RUNTIME, DAY, DAY)]
    if conflicting:
        assert json.loads(result["messages"][0].content)["code"] == "schedule_conflict"
    else:
        checked = result["api_prepared"][0]
        assert checked["schedule_check"] == {"booking": interval("17:00", "18:00"), "period": PERIOD}
        assert checked["arguments"] == ARGUMENTS


@pytest.mark.parametrize("fault", ["partial", "truncated", "missing_local", "missing_external", "source_partial",
                                  "source_truncated", "wrong_period", "count", "malformed", "non_json", "missing_duration",
                                  "naive_time", "missing_events", "source_extra"])
def test_incomplete_or_malformed_agenda_cannot_establish_free_time(monkeypatch, fault):
    state = history()
    agenda = agenda_data()
    if fault == "partial":
        agenda.update(complete=False, not_read=["class unavailable"])
    elif fault == "truncated":
        agenda["truncated"] = True
    elif fault in {"missing_local", "missing_external"}:
        del agenda["sources"]["ai_calendar" if fault == "missing_local" else "innohassle"]
    elif fault == "source_partial":
        agenda["sources"]["innohassle"]["status"] = "partial"
    elif fault == "source_truncated":
        agenda["sources"]["ai_calendar"]["truncated"] = True
    elif fault == "wrong_period":
        agenda["range"] = ["2026-11-10", "2026-11-10"]
    elif fault == "count":
        agenda["total"] = 1
    elif fault in {"malformed", "missing_duration", "naive_time"}:
        agenda["events"] = [None if fault == "malformed" else {"starts_at": DAY + "T07:00:00" + ("+03:00" if fault == "missing_duration" else ""), "ends_at": None}]
        agenda["total"] = 1
    elif fault == "missing_events":
        del agenda["events"]
    elif fault == "source_extra":
        agenda["sources"]["group_timetable"] = {"status": "complete", "truncated": False}
    state["messages"][4].content = "not JSON" if fault == "non_json" else json.dumps(agenda)
    monkeypatch.setattr(schedule_tools, "read_my_schedule", lambda *a: {"error": "Unavailable"})
    result = prepare(state)
    assert result["api_prepared"] == []
    assert json.loads(result["messages"][0].content)["code"] == "schedule_unverified"


@pytest.mark.parametrize("events,code", [
    ([interval("16:00", "17:00"), interval("18:00", "19:00")], None),
    ([interval("17:30", "17:45")], "schedule_conflict"),
    ([{"starts_at": DAY + "T14:00:00Z", "ends_at": DAY + "T15:00:00Z"}], "schedule_conflict"),
    ([{"starts_at": DAY + "T12:00:00+03:00", "ends_at": None, "all_day": True}], "schedule_conflict"),
])
def test_interval_boundaries_offsets_and_all_day_semantics(events, code):
    result = prepare(history(events))
    if code:
        assert json.loads(result["messages"][0].content)["code"] == code
    else:
        assert result["api_prepared"][0]["schedule_check"]["booking"] == interval("17:00", "18:00")


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("start,end,code", [("07:00", "09:00", None),
                                          ("20:30", "21:00", "schedule_unverified"),
                                          ("10:00", "10:30", "schedule_conflict")])
def test_unknown_duration_preflight_and_fresh_write_are_slot_specific(monkeypatch, asynchronous, start, end, code):
    unknown = {**interval("09:00", "10:30", title="test1 по дискре", all_day=False), "ends_at": None}
    events = [unknown, interval("09:00", "10:30", title="Known class")]
    arguments = {"day": DAY, "time_from": start, "time_to": end}
    state = history(events)
    state["messages"][-1].tool_calls = [action(arguments)]
    monkeypatch.setattr(schedule_tools, "read_my_schedule", lambda *a: pytest.fail("Unknown end is not an unread calendar"))
    prepared = prepare(state, asynchronous)
    if code:
        refusal = json.loads(prepared["messages"][0].content)
        assert refusal["code"] == code
        if code == "schedule_unverified":
            assert refusal["uncertainty"] == "unknown_event_end"
            assert refusal["unknown_duration_events"][0]["title"] == "test1 по дискре"
    else:
        assert prepared["api_prepared"][0]["schedule_check"]["booking"] == interval(start, end)

    # Consent was granted against a previously empty agenda. Fresh data must
    # independently classify the exact approved slot before any remote write.
    clean = history()
    clean["messages"][-1].tool_calls = [action(arguments)]
    approved = prepare(clean, asynchronous)
    fresh = []
    def read(*a):
        fresh.append(True)
        return agenda_data(events)
    async def aread(*a):
        return read(*a)
    writes = []
    def request(*a, **kw):
        writes.append(a[1])
        return {"done": True}
    async def arequest(*a, **kw):
        return request(*a, **kw)
    monkeypatch.setattr(schedule_tools, "read_my_schedule", read)
    monkeypatch.setattr(schedule_tools, "aread_my_schedule", aread)
    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    monkeypatch.setattr(api_tools.mcp_client, "request", arequest)
    runtime: Any = SimpleNamespace(state=approved, context=CONTEXT, tool_call_id="write")
    result = (asyncio.run(api_tools._acall("music_book_music_room", runtime, arguments)) if asynchronous
              else api_tools._call("music_book_music_room", runtime, arguments))
    assert fresh == [True]
    assert len(writes) == (0 if code else 1)
    if code:
        assert result["code"] == code and result["done"] is False
        if code == "schedule_unverified":
            assert result["unknown_duration_events"][0]["ends_at"] is None
    else:
        assert result == {"done": True}


@pytest.mark.parametrize("arguments", [{"day": DAY, "time_from": "17:00"},
                                       {**ARGUMENTS, "time_to": None}, {**ARGUMENTS, "time_to": "18:00:01"},
                                       {**ARGUMENTS, "time_to": "17:00"}, {**ARGUMENTS, "time_to": "16:00"}])
def test_missing_or_invalid_booking_duration_never_inferred(monkeypatch, arguments):
    monkeypatch.setattr(schedule_tools, "read_my_schedule", lambda *a: pytest.fail("Invalid clocks must not read a calendar"))
    state = history()
    state["messages"][-1].tool_calls = [action(arguments)]
    result = prepare(state)
    assert result["api_prepared"] == [] and result["jump_to"] == "model"
    assert state["messages"][-1].tool_calls[0]["args"]["arguments"] == arguments


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("fault", ["missing", "call_id", "target", "arguments", "booking", "period"])
def test_execution_requires_exact_prepared_calendar_snapshot(monkeypatch, asynchronous, fault):
    state = prepare(history())
    if fault == "missing":
        state["api_prepared"] = []
    else:
        prepared = state["api_prepared"][0]
        if fault == "call_id":
            prepared["call_id"] = "other"
        elif fault == "target":
            prepared["target"] = "rooms_book_room"
        elif fault == "arguments":
            prepared["arguments"]["time_to"] = "18:30"
        elif fault == "booking":
            prepared["schedule_check"]["booking"] = interval("18:00", "19:00")
        elif fault == "period":
            prepared["schedule_check"]["period"]["date_to"] = "2026-11-10"
    monkeypatch.setattr(schedule_tools, "read_my_schedule", lambda *a: pytest.fail("Mismatched consent must fail before I/O"))
    monkeypatch.setattr(api_tools.mcp_client, "request_sync", lambda *a, **kw: pytest.fail("No writes without matched consent"))
    runtime: Any = SimpleNamespace(state=state, context=CONTEXT, tool_call_id="write")
    result = (asyncio.run(api_tools._acall("music_book_music_room", runtime, ARGUMENTS)) if asynchronous
              else api_tools._call("music_book_music_room", runtime, ARGUMENTS))
    assert result["code"] == "schedule_unverified" and result["done"] is False


@pytest.mark.parametrize("asynchronous", [False, True])
def test_music_cancellation_is_exempt_from_booking_calendar_policy(monkeypatch, asynchronous):
    sent = []
    monkeypatch.setattr(schedule_tools, "read_my_schedule", lambda *a: pytest.fail("Cancellation must not require availability"))
    monkeypatch.setattr(api_tools.mcp_client, "request_sync", lambda *a, **kw: sent.append(a) or {"done": True})

    async def request(*a, **kw):
        return api_tools.mcp_client.request_sync(*a, **kw)

    monkeypatch.setattr(api_tools.mcp_client, "request", request)
    arguments = {"service": "music_room", "booking_id": "77"}
    runtime: Any = RUNTIME
    result = (asyncio.run(api_tools._acall("account_cancel_booking", runtime, arguments)) if asynchronous
              else api_tools._call("account_cancel_booking", runtime, arguments))
    assert result == {"done": True}
    assert sent == [("call_tool", {"name": "account_cancel_booking", "arguments": arguments}, "synthetic-ih")]


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("helper", [None, "docs", "chats"])
@pytest.mark.parametrize("initial", ["conflict", "missing_owner"])
def test_graph_initial_guard_blocks_before_interrupt(monkeypatch, asynchronous, helper, initial):
    from catix.agent import calendar_tools, core
    from tests.test_mcp_preflight_graph import ObservedModel

    sent = []
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)

    def request(method, payload, token=None, **credentials):
        if method == "search_tools":
            assert token is None and credentials == {}
            return {"tools": [{"name": "music_book_music_room", "inputSchema": SCHEMA}]}
        sent.append(payload["name"])
        assert payload == {"name": "account_get_my_schedule", "arguments": PERIOD}
        assert token == "synthetic-ih" and credentials == {}
        return {"range": [DAY, DAY], "schedule": [], "bookings": []}

    async def arequest(*a, **kw):
        return request(*a, **kw)

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    monkeypatch.setattr(api_tools.mcp_client, "request", arequest)
    monkeypatch.setattr(calendar_tools, "events_between", lambda *a: [interval("17:30", "18:30")])
    script = ([AIMessage(content="", tool_calls=[{"name": f"ask_{helper}", "id": "helper", "args": {"question": "Book music 17:00–18:00."}}])]
              if helper else [])
    model = ObservedModel(responses=[*script, AIMessage(content="", tool_calls=[action()]), *[AIMessage(content="Refused.") for _ in range(4)]])
    agent = core.build_agent(model, guardrail=False)
    config = {"configurable": {"thread_id": "music-initial"}}
    context = CONTEXT if initial == "conflict" else AgentContext(innohassle_token=SecretStr("synthetic-ih"))
    inputs = {"messages": [HumanMessage("Book music 17:00–18:00 tomorrow.")]}
    if asynchronous:
        asyncio.run(agent.ainvoke(inputs, config, context=context))
    else:
        agent.invoke(inputs, config, context=context)
    assert not agent.get_state(config).interrupts
    assert sent == ["account_get_my_schedule"]
    refusal = next(json.loads(m.content) for messages in model.seen for m in messages
                   if isinstance(m, ToolMessage) and m.tool_call_id == "write" and isinstance(m.content, str))
    assert refusal["code"] == ("schedule_conflict" if initial == "conflict" else "schedule_unverified")


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("helper", [None, "docs", "chats"])
@pytest.mark.parametrize("change,decision,expected_writes", [("new_local", "approve", 0),
                                                           ("new_class", "approve", 0), ("failed", "approve", 0),
                                                           ("partial", "approve", 0), ("truncated", "approve", 0),
                                                           ("no_duration", "approve", 0), ("missing_owner", "approve", 0),
                                                           ("boundary", "approve", 1),
                                                           ("none", "approve", 1), ("none", "reject", 0)])
def test_graph_fresh_state_resume_rechecks_before_write(monkeypatch, asynchronous, helper, change, decision, expected_writes):
    from catix.agent import calendar_tools, core
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.types import Command
    from tests.test_mcp_preflight_graph import ObservedModel

    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    log, local = [], []
    external = {"range": [DAY, DAY], "schedule": [], "bookings": []}
    resumed = False
    context = CONTEXT

    def request(method, payload, token=None, **credentials):
        if method == "search_tools":
            log.append("schema")
            assert token is None and credentials == {} and payload == {"query": "music_book_music_room"}
            return {"tools": [{"name": "music_book_music_room", "inputSchema": SCHEMA}]}
        name = payload.get("name")
        log.append(name)
        assert method == "call_tool" and token == "synthetic-ih" and credentials == {}
        if name == "account_get_my_schedule":
            assert payload["arguments"] == PERIOD
            if resumed and change == "failed":
                raise RuntimeError("synthetic private diagnostic")
            return external
        assert name == "music_book_music_room" and payload["arguments"] == ARGUMENTS
        return {"done": True, "booking_id": "synthetic-booking"}

    async def arequest(*a, **kw):
        return request(*a, **kw)

    def local_events(key, start, end):
        log.append("ai_calendar")
        assert str(start) == DAY and str(end) == DAY
        return local

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    monkeypatch.setattr(api_tools.mcp_client, "request", arequest)
    monkeypatch.setattr(calendar_tools, "events_between", local_events)
    saver = InMemorySaver()
    script = ([AIMessage(content="", tool_calls=[{"name": f"ask_{helper}", "id": "helper", "args": {"question": "Book the music room tomorrow 17:00–18:00."}}])]
              if helper else [])
    model = ObservedModel(responses=[*script, AIMessage(content="", tool_calls=[action()]), *[AIMessage(content="Finished.") for _ in range(4)]])
    agent = core.build_agent(model, guardrail=False, checkpointer=saver)
    config = {"configurable": {"thread_id": "music-recheck"}}
    inputs = {"messages": [history()["messages"][0]]} if helper else history()
    if not helper:
        inputs["messages"].pop()

    def invoke(value):
        return (asyncio.run(agent.ainvoke(value, config, context=context)) if asynchronous
                else agent.invoke(value, config, context=context))

    invoke(inputs)
    paused = agent.get_state(config)
    assert len(paused.interrupts) == 1
    assert log == (["schema", "account_get_my_schedule", "ai_calendar"] if helper else [])
    log.clear()
    consent = paused.interrupts[0].value["action_requests"][0]
    assert consent["args"] == action()["args"]
    assert all(text in consent["description"] for text in (DAY, "17:00", "18:00"))
    assert "synthetic-ih" not in str(paused.values) and "synthetic-sport" not in str(paused.values)
    if change == "new_local":
        local.append(interval("17:30", "19:00", title="New appointment"))
    elif change == "new_class":
        external["schedule"].append(interval("17:30", "19:00", title="New class"))
    elif change == "partial":
        external["not_read"] = ["class: unavailable"]
    elif change == "truncated":
        external["truncated"] = True
    elif change == "no_duration":
        local.append({**interval("07:00", "08:00"), "ends_at": None})
    elif change == "missing_owner":
        context = AgentContext(innohassle_token=SecretStr("synthetic-ih"))
    elif change == "boundary":
        local.append(interval("18:00", "19:00"))
    resumed = True
    agent = core.build_agent(model, guardrail=False, checkpointer=saver)
    out = invoke(Command(resume={paused.interrupts[0].id: {"decisions": [{"type": decision}]}}))
    assert log.count("music_book_music_room") == expected_writes
    assert not agent.get_state(config).interrupts
    if decision == "reject":
        assert log == []
    elif expected_writes:
        assert log == ["account_get_my_schedule", "ai_calendar", "music_book_music_room"]
    else:
        refusal = next(json.loads(m.content) for messages in model.seen for m in messages
                       if isinstance(m, ToolMessage) and m.tool_call_id == "write" and isinstance(m.content, str))
        assert refusal["done"] is False
        assert refusal["code"] == ("schedule_conflict" if change in {"new_class", "new_local"} else "schedule_unverified")
        assert "synthetic private diagnostic" not in str(refusal)
