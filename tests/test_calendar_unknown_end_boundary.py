"""External ICS acquisition -> unified agenda -> When2Meet, without network/writes."""
from datetime import date, datetime
from types import SimpleNamespace

import httpx
import pytest
from fastmcp.tools.function_tool import FunctionTool
from langchain_core.tools import StructuredTool
from pydantic import SecretStr

from catix.agent import calendar_tools, meeting_tools, schedule_tools
from catix.innohassle import client, mcp_client, when2meet
from tests.mcp_native_helpers import registered_tools

DAY = "2099-01-02"
CELL = DAY + "T00:00:00+03:00"
REF = "unknown-end-boundary"
TOKEN = "synthetic-ih"


def ics(*events):
    return "BEGIN:VCALENDAR\r\nVERSION:2.0\r\n" + "".join(
        "BEGIN:VEVENT\r\n" + fields + "\r\nEND:VEVENT\r\n" for fields in events
    ) + "END:VCALENDAR\r\n"


def event(fields, uid="late"):
    return f"UID:{uid}\r\nSUMMARY:Late meeting\r\n" + fields


@pytest.fixture
def services(monkeypatch, request):
    cell = getattr(request, "param", CELL)
    state = {"ics": ics(), "feed": "event", "http": [], "rpc": [], "local": []}
    tool = registered_tools()["account_get_my_schedule"]
    assert isinstance(tool, FunctionTool)
    reader = tool.fn
    recommendation = meeting_tools.get_my_available_meeting_slots
    assert isinstance(recommendation, StructuredTool)
    recommend = recommendation.func
    assert recommend is not None
    runtime = SimpleNamespace(context=SimpleNamespace(
        innohassle_id="owner", innohassle_token=SecretStr(TOKEN),
        asked_at=datetime.fromisoformat("2098-12-31T12:00:00+03:00")))
    meeting = when2meet.Meeting.model_validate({
        "id": "a" * 24, "slug": REF, "name": "Midnight poll", "specific_time": True,
        "slots": [cell], "participants": [{"user_id": "other", "availability": [cell]}],
        "created_at": "2098-12-31T09:00:00Z", "archive_after": "2099-01-03T00:00:00+03:00",
        "is_archived": False})

    def transport(request):
        assert request.method == "GET", "Recommendations must not write"
        assert request.headers["Authorization"] == f"Bearer {TOKEN}"
        state["http"].append(request.url.path)
        paths = {"/events/v1/users/me/events.ics": "event",
                 "/schedule/v0/users/me/sport.ics": "sport", "/schedule/v0/core.ics": "class"}
        assert request.url.path in paths
        return httpx.Response(200, text=state["ics"] if paths[request.url.path] == state["feed"] else ics())

    def rpc_request(method, payload, token=None, **credentials):
        assert method == "call_tool" and token == TOKEN and credentials == {}
        state["rpc"].append(payload["name"])
        if payload["name"] == "when2meet_get_meeting":
            assert payload["arguments"] == {"meeting_ref": REF}
            return when2meet.details(meeting, "owner")
        assert payload["name"] == "account_get_my_schedule", "Recommendations must not write"
        assert payload["arguments"] == {"date_from": DAY, "date_to": DAY}
        state["external"] = reader(date.fromisoformat(DAY), date.fromisoformat(DAY), token=token)
        return state["external"]

    def agenda(*args):
        state["agenda"] = schedule_tools.read_my_schedule(*args)
        return state["agenda"]

    monkeypatch.setattr(client, "my_calendar_groups", lambda token: (1, ["core"]))
    monkeypatch.setattr(client, "event_groups", lambda **kwargs: [{"alias": "core", "tags": []}])
    monkeypatch.setattr(client, "my_music_room_bookings", lambda token: [])
    monkeypatch.setattr(client, "my_room_bookings", lambda *args: [])
    monkeypatch.setattr(calendar_tools, "events_between", lambda *args: state["local"])
    monkeypatch.setattr(mcp_client, "request_sync", rpc_request)
    monkeypatch.setattr(meeting_tools, "read_my_schedule", agenda)
    with httpx.Client(base_url="https://calendar.test/", transport=httpx.MockTransport(transport)) as http:
        monkeypatch.setattr(client, "_client", http)
        state["recommend"] = lambda: recommend(runtime, REF)
        yield state


@pytest.mark.parametrize("feed", ["event", "sport", "class"])
def test_previous_day_unknown_end_is_not_free_after_real_ics_acquisition(services, feed):
    services["feed"] = feed
    services["ics"] = ics(event("DTSTART;TZID=Europe/Moscow:20990101T234500"))
    result = services["recommend"]()
    assert services["rpc"] == ["when2meet_get_meeting", "account_get_my_schedule"]
    assert "/events/v1/users/me/events.ics" in services["http"]
    assert result["available"] == result["common_available"] == []
    assert result["complete"] is False and result["not_read"] == []
    row, = result["unverified"]
    assert row["starts_at"] == CELL and row["uncertainty"] == "unknown_event_end"
    unknown, = row["unknown_duration_events"]
    assert unknown["starts_at"] == "2099-01-01T23:45:00+03:00" and unknown["ends_at"] is None
    assert unknown["calendar_uid"] == "late"
    assert services["agenda"]["complete"] is True
    assert services["agenda"]["events"][0]["ends_at"] is None


@pytest.mark.parametrize("services", [DAY + "T00:30:00+03:00"], indirect=True)
@pytest.mark.parametrize("unknown_first", [True, False], ids=["unknown-first", "known-first"])
@pytest.mark.parametrize("known_end", ["DTEND:20990101T211500Z", "DURATION:PT30M"])
def test_colliding_display_fields_preserve_unknown_end(services, unknown_first, known_end):
    fields = "DTSTART:20990101T204500Z\r\nLOCATION:Room 1"
    unknown = event(fields, uid="unknown")
    known = event(fields + "\r\n" + known_end, uid="known")
    services["ics"] = ics(*([unknown, known] if unknown_first else [known, unknown]))
    result = services["recommend"]()
    assert result["available"] == result["common_available"] == result["excluded"] == []
    assert result["complete"] is False and result["not_read"] == []
    row, = result["unverified"]
    assert row["starts_at"] == DAY + "T00:30:00+03:00"
    assert row["uncertainty"] == "unknown_event_end"
    unknown_row, = row["unknown_duration_events"]
    assert unknown_row["calendar_uid"] == "unknown" and unknown_row["ends_at"] is None
    agenda = services["agenda"]
    assert agenda["complete"] is True
    assert {row["calendar_uid"]: row["ends_at"] for row in agenda["events"]} == {
        "unknown": None, "known": "2099-01-02T00:15:00+03:00"}
    assert len(agenda["events"]) == 2


@pytest.mark.parametrize("end, bucket", [
    ("", "unverified"),
    ("\r\nDTEND:20990101T211500Z", "excluded"),
    ("\r\nDURATION:PT30M", "excluded"),
])
def test_identical_occurrences_are_still_deduplicated(services, end, bucket):
    duplicate = event("DTSTART:20990101T204500Z\r\nLOCATION:Room 1" + end)
    services["ics"] = ics(duplicate, duplicate)
    result = services["recommend"]()
    assert result["available"] == result["common_available"] == []
    assert result["not_read"] == [] and services["agenda"]["complete"] is True
    assert len(services["agenda"]["events"]) == 1
    row, = result[bucket]
    assert row["starts_at"] == CELL
    if bucket == "unverified":
        unknown, = row["unknown_duration_events"]
        assert unknown["calendar_uid"] == "late" and unknown["ends_at"] is None


@pytest.mark.parametrize("fields", [
    # A finite series may have an arbitrarily old, still-unknown occurrence.
    ["DTSTART:20000101T204500Z\r\nRRULE:FREQ=DAILY;COUNT=2"],
    # The master itself is not proof of an occurrence when excluded.
    ["DTSTART:20990101T204500Z\r\nRRULE:FREQ=DAILY;COUNT=2\r\nEXDATE:20990101T204500Z"],
    # RDATE may precede DTSTART; checking only the master's date is unsafe.
    ["DTSTART:20990201T204500Z\r\nRDATE:20990101T204500Z"],
    # An unknown detached exception in an otherwise known-duration series.
    ["DTSTART:20981231T204500Z\r\nDTEND:20981231T214500Z\r\nRRULE:FREQ=DAILY;COUNT=2",
     "DTSTART:20990101T204500Z\r\nRECURRENCE-ID:20990101T204500Z"],
    # A known exception cannot establish ends for the other occurrences.
    ["DTSTART:20981231T204500Z\r\nRRULE:FREQ=DAILY;COUNT=2",
     "DTSTART:20990101T204500Z\r\nDTEND:20990101T210000Z\r\nRECURRENCE-ID:20990101T204500Z"],
    # RANGE edits must not turn the raw master into a trustworthy interval.
    ["DTSTART:20981231T204500Z\r\nRRULE:FREQ=DAILY",
     "DTSTART:20990101T220000Z\r\nDTEND:20990101T230000Z\r\nRECURRENCE-ID;RANGE=THISANDFUTURE:20990101T204500Z"],
])
@pytest.mark.parametrize("feed", ["event", "class"])
def test_unknown_recurrence_history_reports_incomplete_coverage(services, fields, feed):
    services["feed"] = feed
    services["ics"] = ics(*(event(field) for field in fields))
    result = services["recommend"]()
    assert result["available"] == result["common_available"] == []
    assert result["complete"] is False
    assert services["agenda"]["complete"] is False
    assert result["not_read"] and any("unknown" in reason.lower() for reason in result["not_read"])
    assert len(result["unverified"]) == 1
    assert services["agenda"]["events"] == [], "Do not invent actual occurrences from a raw series master"


@pytest.mark.parametrize("fields, bucket, end", [
    ("DTSTART:20990101T204500Z\r\nDTEND:20990101T211500Z", "excluded", "2099-01-02T00:15:00+03:00"),
    ("DTSTART:20990101T204500Z\r\nDTEND:20990101T210000Z", "available", None),
    ("DTSTART:20990101T204500Z\r\nDURATION:PT45M", "excluded", "2099-01-02T00:30:00+03:00"),
    ("DTSTART:20990101T204500Z\r\nDURATION:PT15M", "available", None),
    # The queried local midnight is on the previous UTC date.
    ("DTSTART:20990101T210000Z\r\nDTEND:20990101T213000Z", "excluded", "2099-01-02T00:30:00+03:00"),
    ("DTSTART:20990101T213000Z\r\nDTEND:20990101T220000Z", "available", "2099-01-02T01:00:00+03:00"),
    ("DTSTART;VALUE=DATE:20990101", "available", None),
    ("DTSTART;VALUE=DATE:20990102", "excluded", "2099-01-03T00:00:00+03:00"),
    ("DTSTART;VALUE=DATE:20990101\r\nDTEND;VALUE=DATE:20990103", "excluded", "2099-01-03T00:00:00+03:00"),
    ("DTSTART;VALUE=DATE:20981231\r\nRRULE:FREQ=DAILY;COUNT=3", "excluded", "2099-01-03T00:00:00+03:00"),
    ("DTSTART:20981231T204500Z\r\nDURATION:PT45M\r\nRRULE:FREQ=DAILY;COUNT=2", "excluded", "2099-01-02T00:30:00+03:00"),
    ("DTSTART:20981231T204500Z\r\nDURATION:PT45M\r\nRRULE:FREQ=DAILY;COUNT=2\r\nEXDATE:20990101T204500Z", "available", None),
    ("DTSTART:20990101T211500Z", "unverified", None),
    ("DTSTART:20990101T213000Z", "available", None),
    ("DTSTART:20990103T000000Z", "available", None),
    ("DTSTART:20000101T204500Z", "unverified", None),
])
def test_known_intervals_all_day_utc_and_unknown_boundary_controls(services, fields, bucket, end):
    services["ics"] = ics(event(fields))
    result = services["recommend"]()
    assert services["agenda"]["complete"] is True and result["not_read"] == []
    assert [row["starts_at"] for row in result[bucket]] == [CELL]
    assert all(result[key] == [] for key in ("available", "excluded", "unverified") if key != bucket)
    assert result["complete"] is (bucket != "unverified")
    if end:
        assert any(row["ends_at"] == end for row in services["agenda"]["events"])
    if bucket == "unverified":
        assert result[bucket][0]["uncertainty"] == "unknown_event_end"
        assert result[bucket][0]["unknown_duration_events"][0]["ends_at"] is None


def test_floating_unknown_start_does_not_borrow_the_host_timezone(services):
    services["ics"] = ics(event("DTSTART:20990101T234500"))
    result = services["recommend"]()
    assert result["available"] == result["common_available"] == []
    assert services["agenda"]["complete"] is False and result["not_read"]
    assert len(result["unverified"]) == 1


def test_next_event_does_not_supply_an_unknown_end(services):
    services["ics"] = ics(event("DTSTART:20990101T180000Z"), event(
        "DTSTART:20990101T190000Z\r\nDTEND:20990101T200000Z", uid="finished"))
    result = services["recommend"]()
    assert result["available"] == result["common_available"] == []
    unknown, = result["unverified"][0]["unknown_duration_events"]
    assert unknown["starts_at"] == "2099-01-01T21:00:00+03:00" and unknown["ends_at"] is None


def test_incomplete_recurrence_feed_keeps_independent_known_conflicts(services):
    services["ics"] = ics(event("DTSTART:20981231T204500Z\r\nRRULE:FREQ=DAILY"))
    services["local"] = [{"title": "Known conflict", "starts_at": CELL,
                          "ends_at": "2099-01-02T00:15:00+03:00"}]
    result = services["recommend"]()
    assert result["available"] == result["common_available"] == result["unverified"] == []
    assert result["complete"] is False and result["not_read"]
    conflict, = result["excluded"][0]["conflicts"]
    assert conflict["title"] == "Known conflict" and conflict["source"] == "ai_calendar"


def test_known_recurrence_exception_still_uses_its_actual_end(services):
    services["ics"] = ics(
        event("DTSTART:20981231T204500Z\r\nDURATION:PT45M\r\nRRULE:FREQ=DAILY;COUNT=2"),
        event("DTSTART:20990101T190000Z\r\nDTEND:20990101T200000Z\r\nRECURRENCE-ID:20990101T204500Z"))
    result = services["recommend"]()
    assert result["complete"] is True and result["not_read"] == []
    assert result["available"] == result["common_available"] == [{
        "starts_at": CELL, "ends_at": "2099-01-02T00:30:00+03:00"}]
