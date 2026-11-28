"""Exact Music Room intervals over the native MCP read and synthetic upstream HTTP."""
from datetime import datetime

import pytest

from catix.innohassle import mcp_account
from catix.settings import settings
from tests.test_mcp_music_availability import DAY, invoke, music_api  # noqa: F401


def exact(**arguments):
    return invoke({"day": DAY, "time_from": "15:00", "time_to": "16:00", **arguments})


@pytest.mark.parametrize("generic", [False, True])
@pytest.mark.parametrize("remote", [False, True])
def test_exact_interval_derives_duration_and_never_returns_alternatives(music_api, generic, remote):
    result = invoke({"day": DAY, "time_from": "15:00", "time_to": "16:00"},
                    generic=generic, remote=remote)
    assert not result.is_error
    assert result.data["duration_minutes"] == 60
    assert result.data["requested_interval"] == {
        "starts_at": DAY + "T15:00:00+03:00", "ends_at": DAY + "T16:00:00+03:00",
    }
    assert result.data["windows"] == [
        {"start": "15:00", "end": "16:00", "latest_start": "15:00", "max_duration_minutes": 60},
    ]
    assert result.data["reason"] is None


@pytest.mark.parametrize("begin,end,occupied", [
    ("14:00", "15:00", False),
    ("16:00", "17:00", False),
    ("14:30", "15:01", True),
    ("15:59", "16:30", True),
    ("15:00", "16:00", True),
    ("14:00", "17:00", True),
])
def test_exact_overlap_uses_half_open_actual_booking_intervals(music_api, begin, end, occupied):
    music_api["bookings"] = [{
        "time_start": DAY + "T" + begin + ":00", "time_end": DAY + "T" + end + ":00",
        "name": "private-booker", "user_id": "private-user", "id": 444,
    }]
    data = exact().data
    assert bool(data["windows"]) is not occupied
    assert data["reason"] == ("room_occupied" if occupied else None)
    assert "private" not in str(data) and "444" not in str(data)
    assert "bookings" not in data and "occupied" not in data
    if occupied:
        assert data["occupied_intervals"] == [{
            "starts_at": DAY + "T" + max(begin, "15:00") + ":00+03:00",
            "ends_at": DAY + "T" + min(end, "16:00") + ":00+03:00",
        }]
    else:
        assert "occupied_intervals" not in data


def test_exact_offset_overlap_is_compared_as_an_instant(music_api):
    music_api["bookings"] = [{"time_start": DAY + "T12:30:00Z", "time_end": DAY + "T13:30:00Z"}]
    data = exact().data
    assert data["windows"] == [] and data["reason"] == "room_occupied"


def test_unrelated_occupancy_does_not_exclude_requested_time_or_leak_data(music_api):
    music_api["bookings"] = [
        {"time_start": DAY + "T07:00:00", "time_end": DAY + "T15:00:00", "name": "private-morning"},
        {"time_start": DAY + "T16:00:00", "time_end": DAY + "T22:30:00", "name": "private-evening"},
    ]
    data = exact().data
    assert data["windows"][0]["start"] == "15:00"
    assert "private" not in str(data)
    assert "07:00:00" not in str(data) and "22:30:00" not in str(data)


@pytest.mark.parametrize("daily,weekly", [(0.5, 2), (2, 0.5), (0, 0)])
def test_exact_quota_failure_is_not_room_occupancy(music_api, daily, weekly):
    music_api.update(daily=daily, weekly=weekly)
    data = exact().data
    assert data["windows"] == [] and data["reason"] == "insufficient_quota"
    assert data["duration_minutes"] == 60


def test_exact_overlapping_booking_evidence_is_clipped_merged_and_identity_free(music_api):
    music_api["bookings"] = [
        {"time_start": DAY + "T14:00:00", "time_end": DAY + "T15:30:00", "name": "private-one"},
        {"time_start": DAY + "T15:15:00", "time_end": DAY + "T17:00:00", "name": "private-two"},
        {"time_start": DAY + "T08:00:00", "time_end": DAY + "T09:00:00", "name": "private-other"},
    ]
    data = exact().data
    assert data["reason"] == "room_occupied" and data["windows"] == []
    assert data["occupied_intervals"] == [{
        "starts_at": DAY + "T15:00:00+03:00", "ends_at": DAY + "T16:00:00+03:00",
    }]
    assert "private" not in str(data)


@pytest.mark.parametrize("begin,end", [("06:30", "07:30"), ("22:00", "23:00")])
def test_exact_closed_hours_are_not_reported_as_occupied(music_api, begin, end):
    data = exact(time_from=begin, time_to=end).data
    assert data["windows"] == [] and data["reason"] == "outside_opening_hours"
    assert music_api["requests"] == []


def test_exact_end_can_equal_closing_time(music_api):
    data = exact(time_from="21:30", time_to="22:30").data
    assert data["reason"] is None and data["windows"][0]["end"] == "22:30"


@pytest.mark.parametrize("arguments", [
    {"time_from": "15:00"}, {"time_to": "16:00"},
    {"time_from": "15:00", "time_to": "15:00"},
    {"time_from": "16:00", "time_to": "15:00"},
    {"time_from": "23:00", "time_to": "01:00"},
    {"time_from": "15:15", "time_to": "16:00"},
    {"time_from": "15:00", "time_to": "16:15"},
    {"time_from": "15:00", "time_to": "16:00", "duration_minutes": 30},
    {"time_from": "15:00", "time_to": "16:00", "duration_minutes": 90},
])
def test_exact_invalid_pair_grid_order_or_duration_is_rejected_before_io(music_api, arguments):
    result = invoke({"day": DAY, **arguments})
    assert result.data["code"] == "invalid_arguments"
    assert music_api["requests"] == []


@pytest.mark.parametrize("value", ["15:00:00", "15:00+03:00", "25:00", "3pm"])
def test_exact_native_clock_format_is_strict_before_io(music_api, value):
    assert exact(time_from=value).is_error
    assert music_api["requests"] == []


def test_exact_matching_explicit_duration_is_accepted(music_api):
    assert exact(duration_minutes=60).data["windows"]


@pytest.mark.parametrize("day,begin,end,reason", [
    ("2026-11-09", "12:00", "13:00", "past"),
    ("2026-11-16", "12:30", "13:30", "outside_booking_horizon"),
    ("2026-11-17", "15:00", "16:00", "outside_booking_horizon"),
])
def test_exact_past_and_rolling_horizon_have_specific_reasons(music_api, day, begin, end, reason):
    data = exact(day=day, time_from=begin, time_to=end).data
    assert data["windows"] == [] and data["reason"] == reason
    assert music_api["requests"] == []


def test_exact_start_equal_to_now_is_not_future(music_api, monkeypatch):
    monkeypatch.setattr(mcp_account, "_now", lambda: datetime(2026, 11, 10, 15, tzinfo=settings.tz))
    data = exact().data
    assert data["windows"] == [] and data["reason"] == "past"


def test_exact_banned_access_retains_interval_without_other_reads(music_api):
    music_api["profile"] = {"status": "banned"}
    data = exact().data
    assert data["windows"] == [] and data["reason"] == "access_denied"
    assert data["requested_interval"]["starts_at"] == DAY + "T15:00:00+03:00"
    assert len(music_api["requests"]) == 1


def test_exact_unknown_occupancy_never_becomes_room_occupied(music_api):
    music_api["bookings"] = [{}]
    result = exact()
    assert result.is_error and result.data is None


def test_day_wide_mode_keeps_original_shape(music_api):
    data = invoke({"day": DAY}).data
    assert "requested_interval" not in data and data["duration_minutes"] is None
    assert data["windows"] == [
        {"start": "07:00", "end": "09:00", "latest_start": "08:30", "max_duration_minutes": 60},
        {"start": "10:30", "end": "22:30", "latest_start": "22:00", "max_duration_minutes": 60},
    ]
