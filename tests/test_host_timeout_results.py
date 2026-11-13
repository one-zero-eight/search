"""Safe timeout reasons survive host composition without making partial data free time."""
from copy import deepcopy
from datetime import date
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from catix.agent import meeting_tools, music_tools, room_tools, training_tools
from catix.agent.schedule_tools import merge_schedule
from catix.innohassle import mcp_client

DAY = "2026-11-10"
PERIOD = [DAY, DAY]
LOCAL_EVENT = {"title": "Personal meeting", "starts_at": DAY + "T18:00:00+03:00",
               "ends_at": DAY + "T19:00:00+03:00"}


@pytest.mark.parametrize("code", ["upstream_timeout", "mcp_timeout"])
def test_merge_keeps_timeout_reason_and_local_events(code):
    result = merge_schedule(PERIOD, {"error": "private-diagnostic", "code": code},
                            {"range": PERIOD, "events": [deepcopy(LOCAL_EVENT)]})
    assert result["complete"] is False
    assert result["sources"]["innohassle"]["status"] == "unavailable"
    assert result["source_errors"] == {"innohassle": code}
    assert result["not_read"] == [f"innohassle: {code}"]
    assert result["events"][0]["title"] == LOCAL_EVENT["title"]
    assert result["sources"]["ai_calendar"]["status"] == "complete"
    assert "private-diagnostic" not in str(result)


@pytest.mark.parametrize("component", ["class", "sport", "event", "music_room", "rooms"])
def test_merge_keeps_component_timeout_with_other_events_even_without_prose(component):
    external = {"range": PERIOD, "schedule": [deepcopy(LOCAL_EVENT)], "bookings": [],
                "source_errors": {component: "upstream_timeout"}}
    result = merge_schedule(PERIOD, external, {"range": PERIOD, "events": []})
    assert result["complete"] is False
    assert result["sources"]["innohassle"]["status"] == "partial"
    assert result["source_errors"] == {f"innohassle.{component}": "upstream_timeout"}
    assert result["not_read"] == [f"innohassle: {component}: upstream_timeout"]
    assert result["events"][0]["title"] == LOCAL_EVENT["title"]
    assert external["source_errors"] == {component: "upstream_timeout"}


@pytest.mark.parametrize("source_errors", [None, [], {"private-diagnostic": "upstream_timeout"},
                                           {"sport": "private-diagnostic"}, {"sport": ["upstream_timeout"]}])
def test_malformed_component_status_never_establishes_completeness(source_errors):
    result = merge_schedule(PERIOD, {"range": PERIOD, "schedule": [], "bookings": [],
                                    "source_errors": source_errors}, {"range": PERIOD, "events": []})
    assert result["complete"] is False and result["not_read"]
    assert result["source_errors"] == {}
    assert "private-diagnostic" not in str(result)


@pytest.mark.parametrize("code", [None, "permission_denied", "private-diagnostic", ["upstream_timeout"]])
def test_merge_does_not_guess_timeout_from_error_text(code):
    result = merge_schedule(PERIOD, {"error": "ReadTimeout private-diagnostic", "code": code},
                            {"range": PERIOD, "events": []})
    assert result["source_errors"] == {}
    assert result["not_read"] == ["innohassle: unavailable"]
    assert "private-diagnostic" not in str(result)


def test_complete_empty_agenda_is_not_a_timeout():
    result = merge_schedule(PERIOD, {"range": PERIOD, "schedule": [], "bookings": []},
                            {"range": PERIOD, "events": []})
    assert result["complete"] is True and result["events"] == []
    assert result["not_read"] == [] and result["source_errors"] == {}


READS = [
    (training_tools.get_my_available_trainings, {"day": date.fromisoformat(DAY)}, "sport_get_sport_trainings"),
    (room_tools.get_my_available_rooms, {"day": date.fromisoformat(DAY), "time_from": "18:00", "time_to": "19:00"},
     "rooms_get_free_rooms"),
    (music_tools.get_my_available_music_windows, {"day": date.fromisoformat(DAY)}, "music_get_available_windows"),
    (meeting_tools.get_my_available_meeting_slots, {"meeting_ref": "team-poll"}, "when2meet_get_meeting"),
]


@pytest.mark.parametrize("tool,arguments,service_name", READS, ids=[entry[2] for entry in READS])
@pytest.mark.parametrize("code", ["upstream_timeout", "mcp_timeout"])
def test_personal_availability_preserves_timeout_and_stops_before_calendar(monkeypatch, tool, arguments, service_name, code):
    calls = []

    def request(method, payload, *a, **kw):
        calls.append(payload["name"])
        assert method == "call_tool" and payload["name"] == service_name
        return {"error": "private-diagnostic", "code": code, "details": "private-diagnostic"}

    monkeypatch.setattr(mcp_client, "request_sync", request)
    runtime = SimpleNamespace(context=SimpleNamespace(innohassle_token=SecretStr("test-token"),
                              sport_token=SecretStr("test-sport")))
    response = tool.func(runtime, **arguments)
    if isinstance(response, tuple):
        result, artifact = response
        assert artifact is None
    else:
        result = response
    assert result["code"] == code and result["complete"] is False
    assert "error" in result and not result.get("available")
    assert "Do not retry" in result["note"]
    assert "calendar" in result["note"]
    assert "private-diagnostic" not in str(result)
    assert calls == [service_name]


@pytest.mark.parametrize("tool,arguments,service_name", READS, ids=[entry[2] for entry in READS])
@pytest.mark.parametrize("response", [{"error": "ReadTimeout private-diagnostic"},
                                      {"error": "private-diagnostic", "code": ["upstream_timeout"]},
                                      {"code": "upstream_timeout"}])
def test_availability_does_not_infer_timeout_from_text_or_invalid_envelope(monkeypatch, tool, arguments, service_name, response):
    calls = []

    def request(method, payload, *a, **kw):
        calls.append(payload["name"])
        return deepcopy(response)

    monkeypatch.setattr(mcp_client, "request_sync", request)
    runtime = SimpleNamespace(context=SimpleNamespace(innohassle_token=SecretStr("test-token"),
                              sport_token=SecretStr("test-sport")))
    output = tool.func(runtime, **arguments)
    result = output[0] if isinstance(output, tuple) else output
    assert "error" in result and result.get("code") not in ("upstream_timeout", "mcp_timeout")
    assert result["complete"] is False
    assert "private-diagnostic" not in str(result)
    assert calls == [service_name]
