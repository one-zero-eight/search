"""Partial schedule timeout behavior over native FastMCP transports."""
import asyncio
import logging
from datetime import datetime, timedelta

import httpx
import pytest
from icalendar import Calendar, Event

from catix.innohassle import client as backend, mcp_server
from catix.innohassle import sport
from catix.settings import settings
from tests.mcp_native_helpers import call, connection

TOKEN = "synthetic-schedule-timeout-token"
DAY = "2026-11-09"
ARGS = {"date_from": DAY, "date_to": DAY}
SECRET = "private-timeout-detail-and-token"
SPORT_TOKEN = "synthetic-direct-sport-token"


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
        if path == "/users/me/schedule":
            return httpx.Response(200, json=state.get("trainings", []))
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
        monkeypatch.setattr(sport, "_client", client)
        yield state


def invoke(remote=False, generic=False, sport_token=None) -> dict:
    if not remote and not generic:
        return call("account_get_my_schedule", ARGS, token=TOKEN, sport_token=sport_token)
    async def run():
        async with connection(remote=remote, token=TOKEN, sport_token=sport_token) as mcp:
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


def training_row(training_id=51, *, checked_in=True, **overrides):
    return {"checked_in": checked_in, "can_check_in": False, "training": {
        "id": training_id, "is_all_day": False, "sport_name": "Swimming",
        "start": f"{DAY}T08:00:00+03:00", "end": f"{DAY}T09:30:00+03:00", **overrides}}


@pytest.mark.parametrize("remote,generic", [(False, False), (False, True), (True, False), (True, True)])
def test_direct_sport_uses_request_credential_exact_bounds_and_checked_in_only(sources, remote, generic):
    sources["trainings"] = [training_row(), training_row(52, checked_in=False)]
    result = invoke(remote, generic, SPORT_TOKEN)
    sport_rows = [row for row in result["schedule"] if row["kind"] == "sport"]
    assert len(sport_rows) == 1 and sport_rows[0]["title"] == "Swimming"
    assert sport_rows[0]["calendar_uid"] == "51"
    assert sport_rows[0]["starts_at"] == f"{DAY}T08:00:00+03:00"
    requests = [r for r in sources["requests"] if r.url.path == "/users/me/schedule"]
    assert len(requests) == 1
    assert requests[0].headers["Authorization"] == f"Bearer {SPORT_TOKEN}"
    assert dict(requests[0].url.params) == {"start": f"{DAY}T00:00:00+03:00", "end": "2026-11-10T00:00:00+03:00"}
    assert not any(r.url.path.endswith("sport.ics") for r in sources["requests"])
    assert SPORT_TOKEN not in str(result)
    assert "not_read" not in result


def test_missing_sport_token_keeps_existing_personal_feed_without_acquiring_identity(sources):
    result = invoke()
    assert any(row["kind"] == "sport" and row["title"] == "Sport" for row in result["schedule"])
    assert sum(r.url.path.endswith("sport.ics") for r in sources["requests"]) == 1
    assert not any(r.url.path == "/users/me/schedule" or "accounts" in r.url.path for r in sources["requests"])


@pytest.mark.parametrize("remote,generic", [(False, False), (False, True), (True, False), (True, True)])
def test_direct_sport_timeout_is_partial_without_retry_or_ics_fallback(sources, caplog, remote, generic):
    sources["fail"].add("/users/me/schedule")
    sources["booking_payloads"]["/room-booking/v0/bookings/my"] = [{
        "outlook_booking_id": "room-id", "room_id": "314", "title": "Study",
        "start": f"{DAY}T14:00:00+03:00", "end": f"{DAY}T15:00:00+03:00"}]
    result = invoke(remote, generic, SPORT_TOKEN)
    assert {row["kind"] for row in result["schedule"]} == {"class", "event"}
    assert result["bookings"][0]["booking_id"] == "room-id"
    assert result["source_errors"] == {"sport": "upstream_timeout"}
    assert any(value.startswith("sport:") for value in result["not_read"])
    assert sum(r.url.path == "/users/me/schedule" for r in sources["requests"]) == 1
    assert not any(r.url.path.endswith("sport.ics") for r in sources["requests"])
    assert SECRET not in str(result) and SPORT_TOKEN not in str(result)
    assert SECRET not in caplog.text and SPORT_TOKEN not in caplog.text


def test_direct_sport_overlap_and_inclusive_all_day_end(sources):
    sources["trainings"] = [
        training_row(51, start="2026-11-08T23:30:00+03:00", end=f"{DAY}T00:30:00+03:00"),
        training_row(52, is_all_day=True, start="2026-11-08T00:00:00+03:00", end=f"{DAY}T00:00:00+03:00"),
        training_row(53, is_all_day=True, start="2026-11-08T00:00:00+03:00", end="2026-11-08T00:00:00+03:00"),
    ]
    result = invoke(sport_token=SPORT_TOKEN)
    rows = {row["calendar_uid"]: row for row in result["schedule"] if row["kind"] == "sport"}
    assert set(rows) == {"51", "52"}
    assert rows["51"]["starts_at"] == "2026-11-08T23:30:00+03:00"
    assert rows["51"]["ends_at"] == f"{DAY}T00:30:00+03:00"
    assert rows["52"]["all_day"] is True and "time" not in rows["52"]
    assert rows["52"]["ends_at"] == "2026-11-10T00:00:00+03:00"


@pytest.mark.parametrize("bad", [
    {}, [None], [{"checked_in": "false"}], [{"checked_in": 1}],
    [training_row(id=True)], [training_row(id=0)], [training_row(is_all_day="false")],
    [training_row(sport_name=[])], [training_row(sport_name=" ")],
    [training_row(start="invalid")], [training_row(start=f"{DAY}T08:00:00")],
    [training_row(end=f"{DAY}T07:00:00+03:00")], [training_row(training_location=[])],
])
def test_invalid_direct_sport_data_never_proves_empty_or_complete(sources, bad):
    sources["trainings"] = bad
    result = invoke(sport_token=SPORT_TOKEN)
    assert any(value.startswith("sport: unreadable calendar:") for value in result["not_read"])
    assert {row["kind"] for row in result["schedule"]} == {"class", "event"}
    assert not any(r.url.path.endswith("sport.ics") for r in sources["requests"])
    from catix.agent.schedule_tools import merge_schedule

    merged = merge_schedule([DAY, DAY], result, {"range": [DAY, DAY], "events": []})
    assert merged["complete"] is False


def test_native_agenda_credential_dependencies_are_not_model_arguments():
    from tests.mcp_native_helpers import input_schema

    schema = input_schema("account_get_my_schedule")
    assert "token" not in schema["properties"]
    assert "sport_token" not in schema["properties"]


@pytest.mark.parametrize("status", [401, 403, 503])
def test_direct_sport_service_failure_keeps_other_sources_without_fallback(sources, status):
    sources["responses"]["/users/me/schedule"] = httpx.Response(status, json={"detail": SECRET})
    result = invoke(sport_token=SPORT_TOKEN)
    assert {row["kind"] for row in result["schedule"]} == {"class", "event"}
    assert any(value.startswith(f"sport: {status}:") for value in result["not_read"])
    assert "source_errors" not in result
    assert not any(r.url.path.endswith("sport.ics") for r in sources["requests"])


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
