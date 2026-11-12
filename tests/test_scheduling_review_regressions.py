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
from tests.sport_helpers import DAY, PERIOD, interval


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
    from tests.sport_helpers import SCHEMA

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

