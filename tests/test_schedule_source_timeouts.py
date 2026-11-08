"""Partial schedule timeout behavior over native FastMCP transports."""
import asyncio
import logging
from datetime import datetime, timedelta

import httpx
import pytest
from icalendar import Calendar, Event

from catix.innohassle import client as backend, mcp_server
from catix.settings import settings
from tests.mcp_native_helpers import call, connection

TOKEN = "synthetic-schedule-timeout-token"
DAY = "2026-11-09"
ARGS = {"date_from": DAY, "date_to": DAY}
SECRET = "private-timeout-detail-and-token"


def feed(title):
    calendar, event = Calendar(), Event()
    if not title:
        return calendar.to_ical()
    start = datetime.fromisoformat(f"{DAY}T10:00").replace(tzinfo=settings.tz)
    event.add("uid", title)
    event.add("summary", title)
    event.add("dtstart", start)
    event.add("dtend", start + timedelta(hours=1))
    calendar.add_component(event)
    return calendar.to_ical()


@pytest.fixture
def sources(monkeypatch):
    """Synthetic HTTP gateway; every schedule read uses the real account MCP leaf."""
    monkeypatch.setattr(mcp_server.token_verifier, "claims", lambda value: {"uid": "owner"} if value == TOKEN else None)
    state = {"requests": [], "fail": set(), "responses": {}, "booking_payloads": {},
             "feeds": {"sport": feed("Sport"), "event": feed("Event"), "class": feed("Class"),
                       "core": feed("Core"), "lab": feed("Lab")}, "booking_fail": set()}

    def respond(request):
        state["requests"].append(request)
        path = request.url.path
        if path in state["responses"]:
            return state["responses"][path]
        if path in state["fail"] or path in state["booking_fail"]:
            raise httpx.ReadTimeout(SECRET, request=request)
        if path == "/schedule/v0/users/me":
            return httpx.Response(200, json={"id": 73, "favorite_event_groups": ["core", "lab"], "hidden_event_groups": []})
        if path == "/schedule/v0/users/me/predefined":
            return httpx.Response(200, json={"event_groups": []})
        if path == "/schedule/v0/event-groups/":
            return httpx.Response(200, json={"event_groups": [{"alias": group_alias, "tags": []} for group_alias in ("core", "lab")]})
        if path in {"/schedule/v0/core.ics", "/schedule/v0/lab.ics"}:
            alias = path.rsplit("/", 1)[1].removesuffix(".ics")
            return httpx.Response(200, content=state["feeds"][alias])
        if path in {"/schedule/v0/users/me/sport.ics", "/events/v1/users/me/events.ics"}:
            kind = "sport" if "sport" in path else "event"
            return httpx.Response(200, content=state["feeds"][kind])
        if path in {"/music-room/v0/bookings/my_bookings", "/room-booking/v0/bookings/my"}:
            return httpx.Response(200, json=state["booking_payloads"].get(path, []))
        raise AssertionError(f"Unexpected request path {path}")

    with backend._http_client("https://schedule-timeouts.test", transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr(backend, "_client", client)
        yield state


def invoke(remote=False, generic=False) -> dict:
    if not remote and not generic:
        return call("account_get_my_schedule", ARGS, token=TOKEN)
    async def run():
        async with connection(remote=remote, token=TOKEN) as mcp:
            if generic:
                result = await mcp.call_tool("call_tool", {"name": "account_get_my_schedule", "arguments": ARGS}, raise_on_error=False)
            else:
                result = await mcp.call_tool("account_get_my_schedule", ARGS, raise_on_error=False)
            return result.data
    return asyncio.run(run())


@pytest.mark.parametrize("remote,generic", [(False, False), (False, True), (True, False), (True, True)])
def test_schedule_feed_timeout_preserves_other_sources_and_emits_safe_code(sources, caplog, remote, generic):
    sources["fail"].add("/schedule/v0/users/me/sport.ics")
    caplog.set_level(logging.WARNING)
    result = invoke(remote, generic)
    assert {row["kind"] for row in result["schedule"]} == {"class", "event"}
    assert result["not_read"] == [f"sport: InNoHassle did not answer (ReadTimeout)"]
    assert result["source_errors"] == {"sport": "upstream_timeout"}
    assert SECRET not in str(result) and SECRET not in caplog.text
    assert sum(r.url.path == "/schedule/v0/users/me/sport.ics" for r in sources["requests"]) == 1


def test_class_feed_timeout_keeps_other_class_aliases(sources):
    sources["fail"].add("/schedule/v0/core.ics")
    result = invoke()
    assert {row["title"] for row in result["schedule"]} == {"Sport", "Event", "Lab"}
    assert result["source_errors"] == {"class": "upstream_timeout"}
    assert SECRET not in str(result)
    assert sum(r.url.path == "/schedule/v0/core.ics" for r in sources["requests"]) == 1


def test_class_selection_timeout_is_class_source_error_and_keeps_independent_feeds(sources):
    sources["fail"].add("/schedule/v0/users/me")
    result = invoke()
    assert {row["kind"] for row in result["schedule"]} == {"sport", "event"}
    assert result["source_errors"] == {"class": "upstream_timeout"}
    assert not any(r.url.path.endswith(".ics") and "core.ics" in r.url.path for r in sources["requests"])


@pytest.mark.parametrize("path,component,remaining", [
    ("/music-room/v0/bookings/my_bookings", "music_room", "rooms"),
    ("/room-booking/v0/bookings/my", "rooms", "music_room"),
])
def test_booking_timeout_keeps_other_booking_branch_and_class_calendars(sources, path, component, remaining):
    path_other = "/room-booking/v0/bookings/my" if component == "music_room" else "/music-room/v0/bookings/my_bookings"
    if remaining == "rooms":
        sources["booking_payloads"][path_other] = [{"outlook_booking_id": "safe-room-id", "room_id": "R1", "title": "Study",
            "start": f"{DAY}T12:00:00+03:00", "end": f"{DAY}T13:00:00+03:00"}]
    else:
        sources["booking_payloads"][path_other] = [{"id": 42, "time_start": f"{DAY}T12:00:00+03:00",
            "time_end": f"{DAY}T13:00:00+03:00"}]
    sources["booking_fail"].add(path)
    result = invoke()
    assert {row["kind"] for row in result["schedule"]} == {"class", "sport", "event"}
    assert len(result["bookings"]) == 1
    assert result["bookings"][0]["service"] == ("room" if remaining == "rooms" else "music_room")
    assert result["source_errors"] == {component: "upstream_timeout"}
    assert sum(r.url.path == path for r in sources["requests"]) == 1
    assert any(r.url.path == path_other for r in sources["requests"])


def test_empty_success_has_no_source_errors(sources):
    sources["feeds"] = {key: feed("") for key in sources["feeds"]}
    result = invoke()
    assert result["schedule"] == [] and result["bookings"] == []
    assert "source_errors" not in result and "not_read" not in result


def test_native_partial_schedule_merges_with_local_events_as_incomplete(sources):
    from catix.agent.schedule_tools import merge_schedule

    sources["fail"].add("/schedule/v0/users/me/sport.ics")
    partial = invoke()
    local = {"range": [DAY, DAY], "events": [{
        "title": "Local event", "starts_at": f"{DAY}T15:00:00+03:00", "ends_at": f"{DAY}T16:00:00+03:00"}]}
    merged = merge_schedule([DAY, DAY], partial, local)
    assert merged["complete"] is False
    assert merged["source_errors"] == {"innohassle.sport": "upstream_timeout"}
    assert {event["title"] for event in merged["events"]} >= {"Local event", "Core", "Lab", "Event"}
    assert any(item.startswith("sport:") for item in partial["not_read"])


def test_non_timeout_control_has_no_timeout_code(sources, caplog):
    sources["responses"]["/schedule/v0/users/me/sport.ics"] = httpx.Response(503, json={"detail": SECRET})
    caplog.set_level(logging.WARNING)
    result = invoke()
    assert "source_errors" not in result
    assert "Schedule source timed out" not in caplog.text


@pytest.mark.parametrize("selected", [False, True])
def test_timeout_is_logged_in_worker_before_unrelated_slow_feed_finishes(monkeypatch, selected):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event as Signal
    from catix.innohassle import mcp_account

    failed, logged, release = Signal(), Signal(), Signal()

    def fetch(*args):
        if args[-1] in ("sport", "core"):
            failed.set()
            raise httpx.ReadTimeout(SECRET)
        assert release.wait(5), "The test must release the independent reader"
        return feed("Slow feed")

    class Notice(logging.Handler):
        def emit(self, record):
            if record.name == "catix.mcp.schedule_sources":
                assert SECRET not in record.getMessage() and record.exc_info is None
                logged.set()

    monkeypatch.setattr(backend, "my_calendar_groups", lambda token: (73, ["core", "lab"] if selected else []))
    monkeypatch.setattr(backend, "event_groups", lambda **kw: [{"alias": name} for name in ("core", "lab")])
    monkeypatch.setattr(backend, "my_group_calendar_ics", fetch)
    monkeypatch.setattr(backend, "my_calendar_ics", fetch)
    handler = Notice()
    logger = logging.getLogger("catix.mcp.schedule_sources")
    logger.addHandler(handler)
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            reader = mcp_account._class_calendar if selected else mcp_account._calendar
            future = pool.submit(reader, TOKEN, datetime.fromisoformat(DAY).date(), datetime.fromisoformat(DAY).date())
            try:
                assert failed.wait(2)
                assert logged.wait(1), "Timeout duration must not include waiting for other futures"
            finally:
                release.set()
            assert future.result()[2] == {"class" if selected else "sport": "upstream_timeout"}
    finally:
        logger.removeHandler(handler)
