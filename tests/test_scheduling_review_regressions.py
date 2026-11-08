"""Pre-commit scheduling regressions; synthetic services only."""

import asyncio
import json
from copy import deepcopy
from datetime import date

import pytest

from catix.agent import scheduling
from catix.agent.schedule_tools import merge_schedule
from catix.innohassle.mcp_account import _calendar_items
from tests.mcp_native_helpers import call
from tests.test_schedule_intervals import calendar
from tests.test_sport_calendar_guard import DAY, PERIOD, interval


@pytest.mark.parametrize("reader", ["personal", "public"])
@pytest.mark.parametrize("fields,expected", [
    ("DTSTART:20261108T210000Z\r\nDTEND:20261109T090000Z", True),
    ("DTSTART:20261108T230000Z\r\nDTEND:20261109T000000Z", True),
    ("DTSTART:20261109T200000Z\r\nDTEND:20261109T210000Z", True),
    ("DTSTART:20261108T200000Z\r\nDTEND:20261108T210000Z", False),
    ("DTSTART:20261109T210000Z\r\nDTEND:20261109T220000Z", False),
])
def test_ics_readers_cover_local_day_not_utc_day(monkeypatch, reader, fields, expected):
    from catix.innohassle import client

    text = calendar(fields + "\r\nSUMMARY:Logic")
    if reader == "personal":
        items = _calendar_items(text, "class", date.fromisoformat(DAY), date.fromisoformat(DAY))
    else:
        monkeypatch.setattr(client, "event_groups", lambda: [{"name": "B26-CSE-01", "alias": "group"}])
        monkeypatch.setattr(client, "group_schedule_ics", lambda alias: text)
        items = call("schedule_get_schedule", {"group": "B26-CSE-01", **PERIOD})["classes"]
    assert bool(items) is expected
    if expected:
        assert len(items) == 1 and items[0]["calendar_uid"] == "synthetic"


@pytest.mark.parametrize("start,end,conflict", [("09:00", "10:00", True), ("12:00", "13:00", False)])
def test_previous_utc_day_class_reaches_unified_agenda_training_check(start, end, conflict):
    text = calendar("DTSTART:20261108T210000Z\r\nDTEND:20261109T090000Z\r\nSUMMARY:Logic")
    items = _calendar_items(text, "class", date.fromisoformat(DAY), date.fromisoformat(DAY))
    agenda = merge_schedule([DAY, DAY], {"range": [DAY, DAY], "schedule": items, "bookings": []},
                            {"range": [DAY, DAY], "events": [], "truncated": False})
    training = interval(start, end, training_id=41, name="Swimming", checked_in=False, can_check_in=True)
    trainings = {"range": [DAY, DAY], "trainings": [training]}
    assert agenda["complete"] is True
    if conflict:
        with pytest.raises(scheduling.ScheduleCheckError) as error:
            scheduling.check_training(41, trainings, agenda)
        assert error.value.result["code"] == "schedule_conflict"
        assert error.value.result["conflicts"][0]["calendar_uid"] == "synthetic"
    else:
        assert scheduling.check_training(41, trainings, agenda)["training"] == training
    assert agenda["total"] == 1
    assert agenda["events"][0]["starts_at"] == DAY + "T00:00:00+03:00"
    assert agenda["events"][0]["ends_at"] == DAY + "T12:00:00+03:00"


def test_local_midnight_ics_without_end_still_has_unknown_duration():
    items = _calendar_items(calendar("DTSTART:20261108T210000Z\r\nSUMMARY:Deadline"),
                            "class", date.fromisoformat(DAY), date.fromisoformat(DAY))
    assert len(items) == 1 and items[0]["calendar_uid"] == "synthetic"
    assert items[0].get("ends_at") is None
    agenda = merge_schedule([DAY, DAY], {"range": [DAY, DAY], "schedule": items, "bookings": []},
                            {"range": [DAY, DAY], "events": [], "truncated": False})
    trainings = {"range": [DAY, DAY], "trainings": [interval(
        "09:00", "10:00", training_id=41, name="Swimming", checked_in=False, can_check_in=True)]}
    with pytest.raises(scheduling.ScheduleCheckError) as error:
        scheduling.check_training(41, trainings, agenda)
    assert error.value.result["code"] == "schedule_unverified"


@pytest.mark.parametrize("service", ["music", "sport"])
@pytest.mark.parametrize("event,code", [
    ({"starts_at": DAY + "T06:00:00Z", "ends_at": None, "all_day": False}, None),
    ({"starts_at": DAY + "T06:00:01Z", "ends_at": None, "all_day": False}, None),
    ({"starts_at": DAY + "T05:59:59Z", "ends_at": None, "all_day": False}, "schedule_unverified"),
    ({"starts_at": "2026-11-08T09:00:00+03:00", "ends_at": None, "all_day": False}, "schedule_unverified"),
    ({"starts_at": DAY + "T12:00:00+03:00", "ends_at": None, "all_day": True}, "schedule_conflict"),
    ({"starts_at": DAY + "T12:00:00", "ends_at": None}, "schedule_unverified"),
    ({"starts_at": "invalid", "ends_at": None}, "schedule_unverified"),
    ({"starts_at": DAY + "T12:00:00+03:00", "ends_at": DAY + "T11:00:00+03:00"}, "schedule_unverified"),
    ({"starts_at": DAY + "T12:00:00+03:00", "ends_at": DAY + "T13:00:00"}, "schedule_unverified"),
])
def test_unknown_end_boundaries_do_not_weaken_malformed_or_all_day_checks(service, event, code):
    from catix.agent.music_scheduling import check_booking
    from tests.test_sport_calendar_guard import agenda_data

    agenda = agenda_data(classes=[])
    agenda.update(events=[event], total=1)
    candidate = interval("07:00", "09:00", training_id=1, name="Swimming", checked_in=False, can_check_in=True)
    def check():
        return (check_booking(candidate, agenda) if service == "music" else
                scheduling.check_training(1, {"range": [DAY, DAY], "trainings": [candidate]}, agenda))
    if code:
        with pytest.raises(scheduling.ScheduleCheckError) as error:
            check()
        assert error.value.result["code"] == code
    else:
        assert check()


@pytest.mark.parametrize("end,expected", [
    (DAY + "T13:00:00+03:00", "2026-11-10T00:00:00+03:00"),
    ("2026-11-11T15:00:00+03:00", "2026-11-11T00:00:00+03:00"),
    ("2026-11-10T22:00:00Z", "2026-11-11T00:00:00+03:00"),
])
def test_explicit_all_day_end_uses_exclusive_local_dates(end, expected):
    event = {"starts_at": DAY + "T12:00:00+03:00", "ends_at": end, "all_day": True}
    start, finish = scheduling._interval(event)
    assert start.isoformat() == DAY + "T00:00:00+03:00"
    assert finish.isoformat() == expected


@pytest.mark.parametrize("end", ["invalid", DAY + "T13:00:00", DAY + "T11:00:00+03:00"])
def test_all_day_normalization_does_not_repair_invalid_end(end):
    with pytest.raises(scheduling.ScheduleCheckError):
        scheduling._interval({"starts_at": DAY + "T12:00:00+03:00", "ends_at": end, "all_day": True})


@pytest.fixture
def capped_sport_services(monkeypatch):
    from fastmcp.tools.function_tool import FunctionTool
    from catix.agent import calendar_tools, core
    from catix.innohassle import mcp_client, sport
    from tests.mcp_native_helpers import registered_tools
    from tests.test_sport_calendar_guard import SCHEMA

    # Exercise the real MCP filter-before-40-cap projection, not a mock cap.
    reader_tool = registered_tools()["sport_get_sport_trainings"]
    assert isinstance(reader_tool, FunctionTool)
    reader = reader_tool.fn
    rows = [{"training": {"id": ident, "sport_name": "Swimming" if ident == 41 else "Yoga",
                           "training_custom_name": "Pool skills" if ident == 41 else "Stretching",
                           "start": DAY + "T17:00:00+03:00", "end": DAY + "T18:00:00+03:00",
                           "training_location": {"name": "Sports centre"}, "is_all_day": False},
             "checked_in": False, "can_check_in": True} for ident in range(1, 42)]
    state = {"log": [], "writes": [], "rows": rows,
             "external": {"range": [DAY, DAY], "schedule": [], "bookings": []}}

    def my_trainings(token, start, end):
        assert token == "synthetic-sport"
        assert start.isoformat() == DAY + "T00:00:00+03:00"
        assert end.isoformat() == "2026-11-10T00:00:00+03:00"
        return deepcopy(state["rows"])

    def request(method, payload, token=None, **credentials):
        if method == "search_tools":
            assert token is None and credentials == {}
            return {"tools": [{"name": "sport_sport_checkin", "inputSchema": SCHEMA}]}
        assert method == "call_tool" and token == "synthetic-ih"
        name, arguments = payload["name"], payload["arguments"]
        state["log"].append((name, deepcopy(arguments)))
        if name == "account_get_my_schedule":
            assert arguments == PERIOD and credentials == {}
            return deepcopy(state["external"])
        assert credentials == {"sport_token": "synthetic-sport"}
        if name == "sport_get_sport_trainings":
            return reader(**{key: date.fromisoformat(value) if key in PERIOD else value
                             for key, value in arguments.items()}, token=credentials["sport_token"])
        assert name == "sport_sport_checkin"
        state["writes"].append(deepcopy(arguments))
        return {"done": True, "training_id": arguments["training_id"], "signed_up": True}

    async def arequest(*args, **kwargs):
        return request(*args, **kwargs)

    monkeypatch.setattr(sport, "my_trainings", my_trainings)
    monkeypatch.setattr(mcp_client, "request_sync", request)
    monkeypatch.setattr(mcp_client, "request", arequest)
    monkeypatch.setattr(calendar_tools, "events_between", lambda *args: [])
    monkeypatch.setattr(core.store, "visible_chats", lambda *args: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    return state


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("source", ["raw", "recommendation"])
@pytest.mark.parametrize("sport_filter", [None, "  sWiM  "])
@pytest.mark.parametrize("change,code", [("none", None), ("missing_training", "schedule_unverified"),
                                       ("partial_agenda", "schedule_unverified"), ("new_class", "schedule_conflict")])
def test_approved_training_rechecks_original_filter_after_real_40_cap(
        capped_sport_services, asynchronous, source, sport_filter, change, code):
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.types import Command
    from catix.agent import core
    from tests.test_roles import ScriptedModel
    from tests.test_sport_calendar_guard import CONTEXT, action

    services = capped_sport_services
    filters = {} if sport_filter is None else {"sport": sport_filter}
    target = 1 if sport_filter is None else 41
    original = {"training_id": target}
    if source == "raw":
        reads = [{"name": "call_api_tool", "id": "read", "args": {
            "name": "sport_get_sport_trainings", "arguments": {**PERIOD, **filters}}},
            {"name": "get_my_schedule", "id": "agenda", "args": PERIOD}]
    else:
        reads = [{"name": "get_my_available_trainings", "id": "read", "args": {"day": DAY, **filters}}]
    model = ScriptedModel(responses=[AIMessage(content="", tool_calls=reads),
                                    AIMessage(content="", tool_calls=[action(target)]), AIMessage(content="Processed.")])
    saver = InMemorySaver()
    graph = core.build_agent(model, guardrail=False, checkpointer=saver)
    config = {"configurable": {"thread_id": "filter-regression"}}

    def invoke(value):
        return (asyncio.run(graph.ainvoke(value, config, context=CONTEXT)) if asynchronous
                else graph.invoke(value, config, context=CONTEXT))

    invoke({"messages": [HumanMessage("Choose a suitable training and sign me up.")]})
    paused = graph.get_state(config)
    assert len(paused.interrupts) == 1 and services["writes"] == []
    prepared, = paused.values["api_prepared"]
    assert prepared["arguments"] == original
    assert prepared["schedule_check"]["training"]["training_id"] == target
    assert prepared["schedule_check"]["training"]["name"] != sport_filter
    assert prepared["schedule_check"]["training_filters"] == filters
    read = next(message for message in paused.values["messages"] if isinstance(message, ToolMessage) and message.tool_call_id == "read")
    if source == "recommendation":
        assert read.artifact["training_arguments"] == {**PERIOD, **filters}
        trainings = read.artifact["trainings"]
    else:
        assert isinstance(read.content, str)
        trainings = json.loads(read.content)
    assert [item["training_id"] for item in trainings["trainings"]] == ([41] if filters else list(range(1, 41)))
    assert [args for name, args in services["log"] if name == "sport_get_sport_trainings"] == [{**PERIOD, **filters}]
    if change == "missing_training":
        services["rows"] = [row for row in services["rows"] if row["training"]["id"] != target]
    elif change == "partial_agenda":
        services["external"]["not_read"] = ["class: selected feed unavailable"]
    elif change == "new_class":
        services["external"]["schedule"] = [interval("17:30", "18:30", title="New class")]
    # The saved checkpoint, not transient process state, must retain the query.
    graph = core.build_agent(model, guardrail=False, checkpointer=saver)
    out = invoke(Command(resume={paused.interrupts[0].id: {"decisions": [{"type": "approve"}]}}))
    result = next(message for message in out["messages"] if isinstance(message, ToolMessage) and message.tool_call_id == "write")
    assert isinstance(result.content, str)
    if code:
        assert json.loads(result.content)["code"] == code
        assert services["writes"] == []
    else:
        assert services["writes"] == [original], result.content
        assert services["log"][-3:] == [("sport_get_sport_trainings", {**PERIOD, **filters}),
                                        ("account_get_my_schedule", PERIOD), ("sport_sport_checkin", original)]
    assert [args for name, args in services["log"] if name == "sport_get_sport_trainings"] == [{**PERIOD, **filters}] * 2