"""Authoritative Music Room checks through real MCP and synthetic upstream HTTP."""
import asyncio
import json

import httpx
import pytest

from tests.mcp_native_helpers import connection
from tests.test_mcp_music_availability import DAY, music_api  # noqa: F401

NAME = "music_book_music_room"
VALID = {"day": DAY, "time_from": "11:00", "time_to": "12:00"}


def book(arguments=None, *, generic=False, remote=False, token="ih"):
    arguments = VALID if arguments is None else arguments
    async def run():
        async with connection(remote, token) as client:
            return await client.call_tool(
                "call_tool" if generic else NAME,
                {"name": NAME, "arguments": arguments} if generic else arguments,
                raise_on_error=False,
            )
    return asyncio.run(run())


def posts(state):
    return [request for request in state["requests"] if request.method == "POST"]


@pytest.mark.parametrize("generic", [False, True])
@pytest.mark.parametrize("remote", [False, True])
@pytest.mark.parametrize("profile", [{"status": "banned"}, {"status": "unknown"}, {}, None])
def test_direct_booking_requires_verified_personal_music_status(music_api, generic, remote, profile):
    music_api.update(allow_write=True, profile=profile)
    result = book(generic=generic, remote=remote)
    assert not result.is_error and result.data["done"] is False, result
    assert posts(music_api) == []
    assert [request.url.path for request in music_api["requests"]] == ["/music-room/v0/users/me"]

    music_api["profile"] = {"status": "free"}
    result = book(generic=generic, remote=remote)
    assert result.data["done"] is True, result
    assert len(posts(music_api)) == 1
    assert json.loads(posts(music_api)[0].content) == {
        "time_start": DAY + "T11:00:00", "time_end": DAY + "T12:00:00",
    }


@pytest.mark.parametrize("generic", [False, True])
@pytest.mark.parametrize("remote", [False, True])
@pytest.mark.parametrize("time_from,time_to", [("11:15", "11:45"), ("11:00", "11:45"), ("11:15", "12:00")])
def test_booking_rejects_off_grid_start_or_end_before_service_reads(music_api, generic, remote, time_from, time_to):
    music_api["allow_write"] = True
    result = book({**VALID, "time_from": time_from, "time_to": time_to}, generic=generic, remote=remote)
    assert not result.is_error and result.data["done"] is False, result
    assert result.data["code"] == "invalid_arguments"
    assert music_api["requests"] == []
    assert book(generic=generic, remote=remote).data["done"] is True
    assert len(posts(music_api)) == 1


@pytest.mark.parametrize("generic", [False, True])
@pytest.mark.parametrize("arguments", [
    {**VALID, "time_from": "06:30", "time_to": "07:30"},
    {**VALID, "time_from": "22:00", "time_to": "23:00"},
    {**VALID, "day": "2026-11-17"},
    {**VALID, "day": "2026-11-16", "time_from": "12:30", "time_to": "13:00"},
    {**VALID, "day": "2026-11-09"},
    {**VALID, "time_to": "11:00"},
    {**VALID, "time_to": "10:30"},
])
def test_booking_enforces_conservative_local_opening_horizon_and_future_span(music_api, generic, arguments):
    music_api["allow_write"] = True
    result = book(arguments, generic=generic, remote=True)
    assert not result.is_error and result.data["done"] is False, result
    assert posts(music_api) == []
    assert book(generic=generic, remote=True).data["done"] is True


@pytest.mark.parametrize("generic", [False, True])
@pytest.mark.parametrize("arguments", [
    {**VALID, "time_from": "07:00", "time_to": "07:30"},
    {**VALID, "time_from": "22:00", "time_to": "22:30"},
    {**VALID, "day": "2026-11-16", "time_from": "12:00", "time_to": "13:00"},
    {**VALID, "time_from": "10:30", "time_to": "11:30"},
])
def test_booking_allows_boundary_slots_and_start_before_horizon_even_if_end_is_after(music_api, generic, arguments):
    music_api["allow_write"] = True
    result = book(arguments, generic=generic, remote=True)
    assert not result.is_error and result.data["done"] is True, result
    assert len(posts(music_api)) == 1
    assert [request.method for request in music_api["requests"]] == ["GET"] * 4 + ["POST"]


@pytest.mark.parametrize("generic", [False, True])
@pytest.mark.parametrize("daily,weekly", [(0.5, 2), (2, 0.5), (0, 2), (2, 0), (-1, 2)])
def test_booking_checks_both_personal_quotas(music_api, generic, daily, weekly):
    music_api.update(allow_write=True, daily=daily, weekly=weekly)
    result = book(generic=generic, remote=True)
    assert not result.is_error and result.data["done"] is False, result
    assert result.data["code"] == "insufficient_quota"
    assert posts(music_api) == []
    music_api.update(daily=1, weekly=1)
    assert book(generic=generic, remote=True).data["done"] is True


@pytest.mark.parametrize("generic", [False, True])
@pytest.mark.parametrize("updates", [
    {"profile": {"status": "banned"}}, {"daily": 0}, {"weekly": 0},
    {"bookings": [{"time_start": DAY + "T11:15:00", "time_end": DAY + "T11:45:00"}]},
])
def test_booking_rereads_personal_state_and_occupancy_after_available_windows(music_api, monkeypatch, generic, updates):
    from catix.common import cache
    from tests.test_mcp_music_availability import invoke

    monkeypatch.setattr(cache, "cached", lambda key, ttl, load: [])
    music_api["allow_write"] = True
    assert invoke({"day": DAY, "duration_minutes": 60}).data["windows"]
    music_api["requests"].clear()
    music_api.update(updates)
    result = book(generic=generic, remote=True)
    assert not result.is_error and result.data["done"] is False, result
    assert posts(music_api) == []
    assert music_api["requests"][0].url.path.endswith("/users/me")
    if "bookings" in updates:
        assert any(request.url.path.endswith("/daily_bookings") for request in music_api["requests"])


@pytest.mark.parametrize("generic", [False, True])
@pytest.mark.parametrize("updates", [
    {"daily": True}, {"weekly": "2"}, {"daily": None},
    {"bookings": None}, {"bookings": {}}, {"bookings": [None]}, {"bookings": [{}]},
    {"bookings": [{"time_start": DAY + "T10:00:00", "time_end": DAY + "T09:00:00"}]},
    {"bookings": [{"time_start": DAY + "T10:00:00", "time_end": DAY + "T10:00:00"}]},
    {"bookings": [{"time_start": "bad-date", "time_end": DAY + "T11:00:00"}]},
])
def test_malformed_preexecution_data_is_definite_refusal_without_post(music_api, generic, updates):
    music_api.update(allow_write=True, **updates)
    result = book(generic=generic, remote=True)
    assert not result.is_error and result.data["done"] is False, result
    assert result.data["code"] == "availability_unverified"
    assert posts(music_api) == []


@pytest.mark.parametrize("generic", [False, True])
@pytest.mark.parametrize("path,status", [
    ("/users/me", 403), ("/users/me", 404), ("/users/me", 500),
    ("/remaining_daily_hours", 503), ("/remaining_weekly_hours", 503),
    ("/daily_bookings", 500), ("/daily_bookings", 307),
])
def test_failed_preexecution_reads_are_definite_refusal_not_unknown(music_api, caplog, generic, path, status):
    music_api.update(allow_write=True, fail_path=path, status=status)
    result = book(generic=generic, remote=True)
    assert not result.is_error and result.data["done"] is False, result
    assert posts(music_api) == []
    assert "private-upstream-diagnostic" not in str(result) + caplog.text
    assert not any(request.url.host == "forbidden.test" for request in music_api["requests"])
    music_api["fail_path"] = None
    assert book(generic=generic, remote=True).data["done"] is True


@pytest.mark.parametrize("generic", [False, True])
@pytest.mark.parametrize("token", [None, "forged"])
def test_booking_requires_identity_before_any_preexecution_reads(music_api, generic, token):
    music_api["allow_write"] = True
    assert book(generic=generic, remote=True, token=token).is_error
    assert music_api["requests"] == []
    assert book(generic=generic, remote=True).data["done"] is True


@pytest.mark.parametrize("generic", [False, True])
@pytest.mark.parametrize("updates", [
    {"post_status": 503}, {"post_status": 408}, {"post_content": b"{broken"},
])
def test_post_failures_keep_unknown_outcome_and_do_not_retry(music_api, generic, updates):
    music_api.update(allow_write=True, **updates)
    result = book(generic=generic, remote=True)
    assert not result.is_error and result.data["done"] is None, result
    assert result.data["outcome"] == "unknown"
    assert "not retry automatically" in result.data["error"]
    assert len(posts(music_api)) == 1


@pytest.mark.parametrize("updates,expected,write_count", [
    ({"profile": {"status": "banned"}}, False, 0),
    ({"bookings": [{}]}, False, 0),
    ({"read_error": httpx.ReadTimeout("private-diagnostic")}, False, 0),
    ({"post_error": httpx.ReadTimeout("private-diagnostic")}, None, 1),
    ({"post_error": ValueError("private-diagnostic")}, None, 1),
    ({"post_status": 503}, None, 1),
    ({}, True, 1),
])
def test_host_decoder_preserves_definite_preexecution_refusal_vs_unknown_post(
    music_api, mcp_http_protocol, caplog, updates, expected, write_count,
):
    from catix.innohassle import mcp_client

    music_api.update(allow_write=True, **updates)
    result = mcp_client.request_sync("call_tool", {"name": NAME, "arguments": VALID}, "ih")
    assert result["done"] is expected, result
    assert len(posts(music_api)) == write_count
    if expected is None:
        assert result["outcome"] == "unknown" and "not retry automatically" in result["error"]
    assert "private-diagnostic" not in str(result) + caplog.text
