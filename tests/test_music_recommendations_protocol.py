"""Host music recommendations consume the real MCP projection, with synthetic HTTP only."""
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from catix.agent import calendar_tools
from catix.agent.tools import AgentContext
from catix.innohassle import mcp_account, mcp_client
from tests.test_mcp_music_availability import DAY, NOW, music_api  # noqa: F401 -- shared fixture
from tests.test_music_recommendations import interval, tool


@pytest.mark.parametrize("mode", ["free", "banned", "no_quota", "service_error"])
def test_host_reads_native_music_wire_contract(monkeypatch, music_api, mcp_http_protocol, mode):
    if mode == "banned":
        music_api["profile"] = {"status": "banned"}
    elif mode == "no_quota":
        music_api["weekly"] = 0
    elif mode == "service_error":
        music_api.update(fail_path="/remaining_weekly_hours", status=503)
    original = mcp_client.request_sync
    reads = []
    def request(method, payload, token=None, **credentials):
        reads.append(payload)
        if payload["name"] == "account_get_my_schedule":
            assert token == "ih" and credentials == {}
            assert payload["arguments"] == {"date_from": DAY, "date_to": DAY}
            return {"range": [DAY, DAY], "schedule": [interval("12:40", "14:10", title="Class")], "bookings": []}
        return original(method, payload, token, **credentials)
    monkeypatch.setattr(mcp_client, "request_sync", request)
    monkeypatch.setattr(calendar_tools, "events_between", lambda *a: [interval("16:00", "16:30", title="Personal")])
    context = AgentContext(innohassle_id="owner", innohassle_token=SecretStr("ih"), asked_at=NOW)
    result, artifact = tool().func(SimpleNamespace(context=context), date.fromisoformat(DAY), 60)
    assert all(r.method == "GET" for r in music_api["requests"])
    if mode == "service_error":
        assert "error" in result and artifact is None and len(reads) == 1
    elif mode in {"banned", "no_quota"}:
        assert result["available"] == [] and result["complete"] is True
        assert result["reason"] == ("access_denied" if mode == "banned" else "insufficient_quota")
    else:
        assert [(w["start"], w["end"], w["latest_start"], w["max_duration_minutes"]) for w in result["available"]] == [
            ("07:00", "09:00", "08:00", 60), ("10:30", "12:30", "11:30", 60),
            ("14:30", "16:00", "15:00", 60), ("16:30", "22:30", "21:30", 60),
        ]
        assert result["complete"] is True and artifact["music"]["availability"] == "calculated"
        assert len(music_api["requests"]) == 4 and len(reads) == 2


@pytest.mark.parametrize("mode", ["no_duration", "horizon"])
def test_native_window_limits_survive_personal_filtering(monkeypatch, music_api, mcp_http_protocol, mode):
    if mode == "horizon":
        monkeypatch.setattr(mcp_account, "_now", lambda: NOW - timedelta(days=6))
    original = mcp_client.request_sync
    def request(method, payload, token=None, **credentials):
        if payload["name"] == "account_get_my_schedule":
            return {"range": [DAY, DAY], "schedule": [], "bookings": []}
        return original(method, payload, token, **credentials)
    monkeypatch.setattr(mcp_client, "request_sync", request)
    monkeypatch.setattr(calendar_tools, "events_between", lambda *a: [interval("16:00", "16:30")])
    context = AgentContext(innohassle_id="owner", innohassle_token=SecretStr("ih"), asked_at=NOW)
    duration = None if mode == "no_duration" else 60
    result, artifact = tool().func(SimpleNamespace(context=context), date.fromisoformat(DAY), duration)
    assert result["complete"] is True and result["duration_minutes"] == duration
    assert all(r.method == "GET" for r in music_api["requests"])
    assert artifact["music_arguments"] == {"day": DAY, **({"duration_minutes": 60} if duration else {})}
    windows = [(w["start"], w["end"], w["latest_start"], w["max_duration_minutes"]) for w in result["available"]]
    assert windows == ([("07:00", "09:00", "08:30", 60), ("10:30", "16:00", "15:30", 60),
                        ("16:30", "22:30", "22:00", 60)] if mode == "no_duration" else
                       [("07:00", "09:00", "08:00", 60), ("10:30", "16:00", "12:00", 60)])
