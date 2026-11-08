"""Personal Music Room availability over real MCP and synthetic HTTP only."""
import asyncio
from datetime import datetime

import httpx
import pytest

from catix.innohassle import client as backend, mcp_account, mcp_server
from catix.settings import settings
from tests.mcp_native_helpers import connection

NAME = "music_get_available_windows"
NOW = datetime(2026, 11, 9, 12, 10, tzinfo=settings.tz)
DAY = "2026-11-10"


@pytest.fixture
def music_api(monkeypatch):
    state = {"requests": [], "daily": 2, "weekly": 1, "profile": {"status": "free"},
             "bookings": [
                 {"time_start": DAY + "T09:00:00", "time_end": DAY + "T10:00:00"},
                 {"time_start": DAY + "T09:30:00", "time_end": DAY + "T10:30:00"},
             ]}
    monkeypatch.setattr(mcp_account, "_now", lambda: NOW)
    monkeypatch.setattr(mcp_server.token_verifier, "claims", lambda token: {"uid": "owner"} if token == "ih" else None)
    def respond(request):
        state["requests"].append(request)
        assert request.method == "GET", "Availability must never reserve anything"
        assert "cookie" not in request.headers
        path = request.url.path
        if state.get("fail_path") and path.endswith(state["fail_path"]):
            return httpx.Response(state.get("status", 500), json={"detail": "private-upstream-diagnostic"},
                                  headers={"Location": "https://forbidden.test/"})
        if path.endswith("/bookings/daily_bookings"):
            assert "authorization" not in request.headers
            return httpx.Response(200, json=state["bookings"])
        assert request.headers["authorization"] == "Bearer ih"
        if path.endswith("/users/me"):
            return httpx.Response(200, json=state["profile"])
        if path.endswith("/remaining_daily_hours"):
            return httpx.Response(200, json=state["daily"])
        if path.endswith("/remaining_weekly_hours"):
            return httpx.Response(200, json=state["weekly"])
        pytest.fail(f"Unexpected path: {path}")
    with backend._http_client("https://synthetic.test", transport=httpx.MockTransport(respond)) as http:
        monkeypatch.setattr(backend, "_client", http)
        yield state


def invoke(arguments, *, generic=False, remote=False, token="ih"):
    async def run():
        async with connection(remote, token) as client:
            return await client.call_tool(
                "call_tool" if generic else NAME,
                {"name": NAME, "arguments": arguments} if generic else arguments,
                raise_on_error=False,
            )
    return asyncio.run(run())


@pytest.mark.parametrize("generic", [False, True])
@pytest.mark.parametrize("remote", [False, True])
def test_windows_subtract_bookings_and_limit_duration_to_personal_quota(music_api, generic, remote):
    result = invoke({"day": DAY}, generic=generic, remote=remote)
    assert not result.is_error, result
    data = result.data
    assert data["date"] == DAY and data["timezone"] == str(settings.tz)
    assert data["checked_at"] == NOW.isoformat()
    assert data["availability"] == "calculated" and data["reason"] is None
    assert data["remaining_daily_minutes"] == 120
    assert data["remaining_weekly_minutes"] == 60
    assert data["windows"] == [
        {"start": "07:00", "end": "09:00", "latest_start": "08:30", "max_duration_minutes": 60},
        {"start": "10:30", "end": "22:30", "latest_start": "22:00", "max_duration_minutes": 60},
    ]
    assert data["rules"]["step_minutes"] == 30
    assert len(music_api["requests"]) == 4


@pytest.mark.parametrize("quota", [True, "2", None])
def test_malformed_quota_is_not_used_as_available_time(music_api, quota):
    music_api["daily"] = quota
    result = invoke({"day": DAY})
    assert result.is_error
    assert result.data is None


def test_booking_rechecks_fresh_occupancy_instead_of_cached_free_time(music_api, monkeypatch):
    from catix.common import cache

    monkeypatch.setattr(cache, "cached", lambda key, ttl, load: [])
    writes = []
    monkeypatch.setattr(backend, "book_music_room", lambda *args: writes.append(args) or {"id": 99})
    async def run():
        async with connection(token="ih") as client:
            return (await client.call_tool("music_book_music_room", {
                "day": DAY, "time_from": "09:00", "time_to": "10:00",
            })).data
    result = asyncio.run(run())
    assert result["done"] is False
    assert writes == []
    assert any(r.url.path.endswith("/daily_bookings") for r in music_api["requests"])


def test_host_calls_availability_as_authenticated_read_without_approval(music_api, monkeypatch, mcp_http_protocol):
    import json
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
    from pydantic import SecretStr
    from catix.agent import core
    from catix.agent.tools import AgentContext
    from tests.test_roles import ScriptedModel

    monkeypatch.setattr(core.store, "visible_chats", lambda *args: [])
    model = ScriptedModel(responses=[
        AIMessage(content="", tool_calls=[{"name": "call_api_tool", "args": {
            "name": NAME, "arguments": {"day": DAY}}, "id": "windows", "type": "tool_call"}]),
        AIMessage(content="Доступные окна рассчитаны по свежим броням и вашим лимитам."),
    ])
    agent = core.build_agent(model, guardrail=False)
    config = {"configurable": {"thread_id": "music-availability"}}
    out = agent.invoke({"messages": [HumanMessage("Когда можно забронировать музкомнату?")]}, config,
                       context=AgentContext(innohassle_token=SecretStr("ih"), innohassle_id="owner"))
    assert not agent.get_state(config).interrupts
    payload = json.loads(next(m.content for m in out["messages"] if isinstance(m, ToolMessage)))
    assert payload.get("windows"), payload
    assert core.successful_read(out["messages"]) and core.read_evidence(out["messages"])


@pytest.mark.parametrize("generic", [False, True])
@pytest.mark.parametrize("remote", [False, True])
@pytest.mark.parametrize("token", [None, "forged"])
def test_availability_requires_verified_identity_before_any_upstream_read(music_api, token, generic, remote):
    denied = invoke({"day": DAY}, token=token, generic=generic, remote=remote)
    assert denied.is_error and music_api["requests"] == []
    assert not invoke({"day": DAY}, generic=generic, remote=remote).is_error


@pytest.mark.parametrize("duration", [False, 0, 15, 45, -30, "60"])
def test_duration_is_native_strict_half_hour_constraint(music_api, duration):
    denied = invoke({"day": DAY, "duration_minutes": duration})
    assert denied.is_error and music_api["requests"] == []


@pytest.mark.parametrize("arguments", [{}, {"day": "2026-02-30"}, {"day": DAY, "token": "other"}])
def test_bad_arguments_do_not_reach_upstream(music_api, arguments):
    assert invoke(arguments).is_error and music_api["requests"] == []


@pytest.mark.parametrize("day", ["2026-11-08", "2026-11-17"])
def test_dates_outside_local_start_horizon_are_explicit(music_api, day):
    data = invoke({"day": day}).data
    assert data["windows"] == [] and data["reason"] == "outside_booking_horizon"
    assert music_api["requests"] == []


def test_horizon_limits_latest_start_not_the_whole_free_window(music_api):
    music_api["bookings"] = []
    data = invoke({"day": "2026-11-16", "duration_minutes": 60}).data
    assert data["windows"] == [{"start": "07:00", "end": "22:30", "latest_start": "12:00", "max_duration_minutes": 60}]
    assert data["rules"]["latest_booking_start"] == "2026-11-16T12:10:00+03:00"


@pytest.mark.parametrize("clock,expected", [("12:10", "12:30"), ("12:30", "13:00"), ("22:00", None)])
def test_today_excludes_started_slots_and_closed_hours(music_api, monkeypatch, clock, expected):
    current = datetime.fromisoformat("2026-11-09T" + clock).replace(tzinfo=settings.tz)
    monkeypatch.setattr(mcp_account, "_now", lambda: current)
    music_api["bookings"] = []
    data = invoke({"day": current.date().isoformat()}).data
    if expected:
        assert data["windows"][0]["start"] == expected
        assert data["windows"][0]["end"] == "22:30"
    else:
        assert data["windows"] == [] and data["reason"] == "no_matching_window"


def test_partial_slots_offsets_and_overlaps_are_excluded_without_leaking_bookers(music_api):
    music_api["bookings"] = [
        {"time_start": DAY + "T06:45:00", "time_end": DAY + "T07:15:00", "user_alias": "private-booker"},
        {"time_start": DAY + "T06:00:00+00:00", "time_end": DAY + "T07:10:00+00:00"},
        {"time_start": DAY + "T09:30:00", "time_end": DAY + "T10:00:00"},
        {"time_start": DAY + "T22:15:00", "time_end": DAY + "T23:00:00"},
    ]
    data = invoke({"day": DAY, "duration_minutes": 60}).data
    assert data["windows"] == [
        {"start": "07:30", "end": "09:00", "latest_start": "08:00", "max_duration_minutes": 60},
        {"start": "10:30", "end": "22:00", "latest_start": "21:00", "max_duration_minutes": 60},
    ]
    assert "private-booker" not in str(data)


@pytest.mark.parametrize("daily,weekly,duration,expected", [(2, 0.5, None, 30), (0.5, 2, None, 30), (2, 1, 60, 60)])
def test_each_personal_limit_caps_maximum_duration(music_api, daily, weekly, duration, expected):
    music_api.update(daily=daily, weekly=weekly)
    data = invoke({"day": DAY, "duration_minutes": duration}).data
    assert data["windows"] and all(window["max_duration_minutes"] == expected for window in data["windows"])


@pytest.mark.parametrize("daily,weekly,duration", [(0, 2, None), (2, 0, None), (-1, 2, None), (2, 0.25, None), (2, 1, 90)])
def test_quota_exhaustion_is_not_confused_with_occupied_room(music_api, daily, weekly, duration):
    music_api.update(daily=daily, weekly=weekly)
    data = invoke({"day": DAY, "duration_minutes": duration}).data
    assert data["windows"] == [] and data["reason"] == "insufficient_quota"


def test_empty_windows_are_valid_read_evidence_but_not_a_service_error(music_api):
    from catix.agent import core
    music_api["bookings"] = [{"time_start": DAY + "T07:00:00", "time_end": DAY + "T22:30:00"}]
    data = invoke({"day": DAY}).data
    assert data["windows"] == [] and data["reason"] == "no_matching_window"
    assert core._read_parts(NAME, data) == ([],)
    assert core._read_parts(NAME, {"windows": []}) is None
    assert core._read_parts("rooms_get_free_rooms", data) is None
    assert core._read_parts(NAME, {**data, "reason": []}) is None


@pytest.mark.parametrize("profile", [{"status": "unknown"}, {}, None])
def test_unknown_access_is_not_treated_as_available(music_api, profile):
    music_api["profile"] = profile
    assert invoke({"day": DAY}).is_error
    assert len(music_api["requests"]) == 1


def test_banned_user_gets_no_windows_or_other_service_reads(music_api):
    music_api["profile"] = {"status": "banned"}
    data = invoke({"day": DAY}).data
    assert data["reason"] == "access_denied" and data["windows"] == []
    assert len(music_api["requests"]) == 1


@pytest.mark.parametrize("bookings", [None, {}, [None], [{}], [
    {"time_start": DAY + "T10:00:00", "time_end": DAY + "T09:00:00"}], [
    {"time_start": "bad-date", "time_end": DAY + "T11:00:00"}]])
def test_malformed_occupancy_is_not_reported_as_free(music_api, bookings):
    music_api["bookings"] = bookings
    assert invoke({"day": DAY}).is_error


def test_repeated_availability_bypasses_even_a_warm_empty_cache(music_api, monkeypatch):
    from catix.common import cache
    monkeypatch.setattr(cache, "cached", lambda key, ttl, load: [])
    assert invoke({"day": DAY}).data["windows"]
    music_api["bookings"] = [{"time_start": DAY + "T07:00:00", "time_end": DAY + "T22:30:00"}]
    assert invoke({"day": DAY}).data["windows"] == []
    assert len(music_api["requests"]) == 8


@pytest.mark.parametrize("path,status", [("/users/me", 403), ("/users/me", 404), ("/users/me", 500),
                                        ("/remaining_weekly_hours", 503), ("/daily_bookings", 500),
                                        ("/daily_bookings", 307)])
def test_upstream_failures_are_unknown_availability_not_empty_windows(music_api, caplog, path, status):
    music_api.update(fail_path=path, status=status)
    result = invoke({"day": DAY})
    assert result.is_error or "error" in result.data
    assert "windows" not in (result.data or {})
    assert "private-upstream-diagnostic" not in str(result) + caplog.text
    assert not any(request.url.host == "forbidden.test" for request in music_api["requests"])
    music_api["fail_path"] = None
    assert invoke({"day": DAY}).data["windows"]


def test_each_read_refreshes_personal_quota(music_api):
    assert invoke({"day": DAY}).data["windows"]
    music_api["weekly"] = 0
    data = invoke({"day": DAY}).data
    assert data["windows"] == [] and data["reason"] == "insufficient_quota"
    assert len(music_api["requests"]) == 8


def test_discovery_publishes_native_constraints_and_no_credentials(music_api):
    async def run():
        async with connection() as client:
            for query in [NAME, "свободные окна музыкальной комнаты", "music room available windows"]:
                found = (await client.call_tool("search_tools", {"query": query})).data
                declared = next(item for item in found if item["name"] == NAME)
                fields = declared["inputSchema"]["properties"]
                assert set(fields) == {"day", "duration_minutes"}
                assert declared["inputSchema"]["required"] == ["day"]
                assert fields["duration_minutes"]["anyOf"][0]["multipleOf"] == 30
            directory = (await client.call_tool("service_status", {})).data
            assert NAME in directory["music"]["tool_names"]
    asyncio.run(run())
    assert music_api["requests"] == []
