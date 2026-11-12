"""Safe timeout reasons survive host composition without making partial data free time."""
from copy import deepcopy

import pytest

from catix.agent.schedule_tools import merge_schedule

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
