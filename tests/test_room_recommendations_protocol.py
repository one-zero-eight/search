"""Native room MCP projection feeds the host read; only upstream HTTP is synthetic."""
from datetime import date
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from catix.agent import calendar_tools
from catix.agent.tools import AgentContext
from catix.innohassle import mcp_client
from tests.test_mcp_room_availability import DAY, NOW, room_api  # noqa: F401 -- shared fixture
from tests.test_room_recommendations import interval, tool


@pytest.mark.parametrize("mode", ["free", "occupied", "denied", "empty", "service_error", "conflict", "partial", "unknown"])
def test_host_consumes_native_room_availability(monkeypatch, room_api, mcp_http_protocol, mode):
    if mode == "occupied":
        room_api["bookings"] = [{"room_id": "r", "start": DAY + "T18:30:00+03:00", "end": DAY + "T19:30:00+03:00"}]
    elif mode == "denied":
        room_api["permission"] = {"can_book": False, "reason_why_cannot": "Staff only"}
    elif mode == "empty":
        room_api["rooms"] = []
    elif mode == "service_error":
        room_api["fail_path"] = "/room-booking/v0/bookings/"
    original = mcp_client.request_sync
    reads = []
    def request(method, payload, token=None, **credentials):
        reads.append(payload)
        if payload["name"] == "account_get_my_schedule":
            assert token == "ih" and credentials == {}
            assert payload["arguments"] == {"date_from": DAY, "date_to": DAY}
            return {"range": [DAY, DAY], "schedule": [], "bookings": [],
                    **({"not_read": ["class: unavailable"]} if mode == "partial" else {})}
        return original(method, payload, token, **credentials)
    monkeypatch.setattr(mcp_client, "request_sync", request)
    local = [interval("18:30", "19:30", title="Personal meeting")] if mode in {"conflict", "unknown"} else []
    if mode == "unknown":
        local[0]["ends_at"] = None
    monkeypatch.setattr(calendar_tools, "events_between", lambda *a: local)
    context = AgentContext(innohassle_id="owner", innohassle_token=SecretStr("ih"), asked_at=NOW)
    result, artifact = tool().func(SimpleNamespace(context=context), date.fromisoformat(DAY), "18:00", "19:00")
    assert room_api["writes"] == [] and all(r.method == "GET" for r in room_api["requests"])
    if mode == "service_error":
        assert "error" in result and artifact is None and len(reads) == 1
        return
    assert len(reads) == 2 and artifact["room_arguments"] == {"day": DAY, "time_from": "18:00", "time_to": "19:00"}
    assert result["interval"] == interval()
    if mode == "free":
        assert result["available"] == [{"room_id": "r", "title": "Room"}]
        assert result["complete"] is True
    elif mode in {"partial", "unknown"}:
        assert not result["available"] and result["unverified"] and result["complete"] is False
        assert bool(result["not_read"]) is (mode == "partial")
    elif mode == "empty":
        assert result["total"] == 0 and result["complete"] is True
    else:
        assert not result["available"] and result["complete"] is True
        assert result["excluded"][0]["reason"] == {"denied": "service_unavailable", "occupied": "room_occupied", "conflict": "schedule_conflict"}[mode]
    for upstream in room_api["requests"]:
        if upstream.url.path in {"/room-booking/v0/rooms/", "/room-booking/v0/bookings/"}:
            assert upstream.url.params["include_red"] == "true"
        if upstream.url.path.endswith("/can-book"):
            assert dict(upstream.url.params) == {"start": DAY + "T18:00:00+03:00", "end": DAY + "T19:00:00+03:00"}
