"""Music acquisition → native account projection → agenda → room recommendation."""
from datetime import date
from types import SimpleNamespace

import httpx
import pytest
from pydantic import SecretStr

from catix.agent import calendar_tools
from catix.agent.tools import AgentContext
from catix.innohassle import client as backend, mcp_account, mcp_client, mcp_server
from tests.test_mcp_room_availability import DAY, NOW
from tests.test_room_recommendations import tool


@pytest.mark.parametrize("start,end,included,conflicts", [
    pytest.param("2026-11-09T23:30", "2026-11-10T00:30", True, True, id="overnight"),
    pytest.param("2026-11-10T00:15", "2026-11-10T00:45", True, True, id="same-day"),
    pytest.param("2026-11-10T00:00", "2026-11-10T00:30", True, True, id="starts-at-midnight"),
    pytest.param("2026-11-09T23:30", "2026-11-10T00:00", False, False, id="ends-at-day-start"),
    pytest.param("2026-11-11T00:00", "2026-11-11T00:30", False, False, id="starts-at-day-end"),
    pytest.param("2026-11-10T01:00", "2026-11-10T01:30", True, False, id="touches-request-end"),
    pytest.param("2026-11-09T23:30", "2026-11-11T00:30", True, True, id="spans-whole-day"),
])
def test_music_booking_acquisition_reaches_room_recommendation(
    monkeypatch, mcp_http_protocol, start, end, included, conflicts,
):
    start, end = start + ":00+03:00", end + ":00+03:00"
    requests, account_results = [], []
    monkeypatch.setattr(mcp_account, "_now", lambda: NOW)
    monkeypatch.setattr(mcp_server.token_verifier, "claims", lambda token: {"uid": "owner"} if token == "ih" else None)

    # Isolate unrelated calendar acquisition, not the account envelope or bookings.
    def calendar(token, first, last):
        assert token == "ih" and first == last == date.fromisoformat(DAY)
        return [], {}

    monkeypatch.setattr(mcp_account, "_calendar", calendar)
    monkeypatch.setattr(calendar_tools, "events_between", lambda *args: [])

    def respond(request):
        requests.append(request)
        assert request.method == "GET"
        assert request.headers["authorization"] == "Bearer ih"
        path = request.url.path
        if path == "/music-room/v0/bookings/my_bookings":
            return httpx.Response(200, json=[{"id": 17, "time_start": start, "time_end": end}])
        if path == "/room-booking/v0/bookings/my":
            assert dict(request.url.params) == {
                "start": DAY + "T00:00:00+03:00", "end": "2026-11-11T00:00:00+03:00",
            }
            return httpx.Response(200, json=[])
        if path == "/room-booking/v0/bookings/":
            return httpx.Response(200, json=[])
        if path == "/room-booking/v0/rooms/":
            return httpx.Response(200, json=[{"id": "r", "title": "Room"}])
        if path == "/room-booking/v0/room/r/can-book":
            return httpx.Response(200, json={"can_book": True, "reason_why_cannot": ""})
        pytest.fail(f"Unexpected upstream path: {path}")

    native_request = mcp_client.request_sync

    def record_request(method, payload, token=None, **credentials):
        result = native_request(method, payload, token, **credentials)
        if payload["name"] == "account_get_my_schedule":
            assert payload["arguments"] == {"date_from": DAY, "date_to": DAY}
            account_results.append(result)
        return result

    monkeypatch.setattr(mcp_client, "request_sync", record_request)
    context = AgentContext(innohassle_id="owner", innohassle_token=SecretStr("ih"), asked_at=NOW)
    with backend._http_client("https://synthetic.test", transport=httpx.MockTransport(respond)) as http:
        monkeypatch.setattr(backend, "_client", http)
        result, artifact = tool().func(SimpleNamespace(context=context), date.fromisoformat(DAY), "00:00", "01:00")

    assert result["available"] == ([] if conflicts else [{"room_id": "r", "title": "Room"}])
    assert result["excluded"] == ([{"room_id": "r", "title": "Room", "reason": "schedule_conflict"}] if conflicts else [])
    assert result["complete"] is True and result["unverified"] == [] and result["not_read"] == []
    assert len(account_results) == 1
    account = account_results[0]
    assert account["range"] == [DAY, DAY] and account["schedule"] == [] and not account.get("not_read")
    assert len(account["bookings"]) == int(included)
    agenda = artifact["agenda"]
    assert agenda["complete"] is True and agenda["total"] == int(included)
    assert agenda["not_read"] == [] and agenda["truncated"] is False
    assert result["conflicts"] == (agenda["events"] if conflicts else [])
    if included:
        booking, event = account["bookings"][0], agenda["events"][0]
        for item in (booking, event):
            assert item["booking_id"] == "17" and item["service"] == "music_room"
            assert item["starts_at"] == start and item["ends_at"] == end
        assert event["source"] == "innohassle" and event["kind"] == "music_room"
    assert len(requests) == 5 and all(request.method == "GET" for request in requests)
    assert sum(request.url.path == "/music-room/v0/bookings/my_bookings" for request in requests) == 1
