"""Calendar and Sport projections retain exact, aware intervals for conflict checks."""

from datetime import date, datetime
from types import SimpleNamespace

import pytest

from catix.innohassle.mcp_account import _calendar_items, _span
from catix.innohassle.mcp_sport import training_item


def test_sport_projection_preserves_midnight_and_offset():
    item = training_item({"id": 7, "sport_name": "Running", "start": "2026-11-09T20:30:00Z",
                          "end": "2026-11-09T22:00:00Z"})
    assert item["starts_at"] == "2026-11-09T23:30:00+03:00"
    assert item["ends_at"] == "2026-11-10T01:00:00+03:00"


def test_booking_projection_keeps_full_dates():
    start = datetime.fromisoformat("2026-11-09T23:00:00+03:00")
    end = datetime.fromisoformat("2026-11-10T01:00:00+03:00")
    assert _span(start, end)["starts_at"] == start.isoformat()
    assert _span(start, end)["ends_at"] == end.isoformat()


def calendar(fields):
    return "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nBEGIN:VEVENT\r\nUID:synthetic\r\n" + fields + "\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"


def test_class_projection_converts_utc_without_losing_interval():
    text = calendar("DTSTART:20261109T060000Z\r\nDTEND:20261109T073000Z\r\nSUMMARY:Logic")
    item, = _calendar_items(text, "class", date(2026, 11, 9), date(2026, 11, 9))
    assert item["starts_at"] == "2026-11-09T09:00:00+03:00"
    assert item["ends_at"] == "2026-11-09T10:30:00+03:00"


def test_personal_class_keeps_original_ics_uid_and_unknown_end():
    text = calendar("DTSTART:20261109T060000Z\r\nSUMMARY:Deadline")
    item, = _calendar_items(text, "class", date(2026, 11, 9), date(2026, 11, 9))
    assert item["calendar_uid"] == "synthetic"
    assert item["starts_at"] == "2026-11-09T09:00:00+03:00"
    assert item.get("ends_at") is None


def test_public_group_projection_keeps_aware_interval_and_ics_uid(monkeypatch):
    from catix.innohassle import client
    from tests.mcp_native_helpers import call

    monkeypatch.setattr(client, "event_groups", lambda: [{"name": "B26-CSE-01", "alias": "group"}])
    monkeypatch.setattr(client, "group_schedule_ics", lambda alias: calendar(
        "DTSTART:20261109T060000Z\r\nDTEND:20261109T073000Z\r\nSUMMARY:Logic"))
    item, = call("schedule_get_schedule", {"group": "B26-CSE-01", "date_from": "2026-11-09", "date_to": "2026-11-09"})["classes"]
    assert item["calendar_uid"] == "synthetic"
    assert item["starts_at"] == "2026-11-09T09:00:00+03:00"
    assert item["ends_at"] == "2026-11-09T10:30:00+03:00"


def test_all_day_interval_uses_exclusive_end_date():
    text = calendar("DTSTART;VALUE=DATE:20261109\r\nDTEND;VALUE=DATE:20261111\r\nSUMMARY:Trip")
    item, = _calendar_items(text, "event", date(2026, 11, 9), date(2026, 11, 9))
    assert item["all_day"] is True
    assert item["starts_at"] == "2026-11-09T00:00:00+03:00"
    assert item["ends_at"] == "2026-11-11T00:00:00+03:00"


@pytest.mark.parametrize("count,truncated", [(40, False), (41, True)])
def test_local_calendar_reads_a_sentinel_and_reports_truncation(monkeypatch, count, truncated):
    from catix.agent import calendar_tools
    from catix.personal_calendar import PersonalEvent
    from tests.test_sport_calendar_guard import CONTEXT

    seen = []
    def between(key, start, end, limit=40):
        seen.append(limit)
        return [PersonalEvent(i, "Appointment", datetime.fromisoformat("2026-11-09T10:00:00+03:00"),
                              datetime.fromisoformat("2026-11-09T11:00:00+03:00"), False, None)
                for i in range(count)][:limit]
    monkeypatch.setattr(calendar_tools.personal_calendar, "between", between)
    result = calendar_tools.get_my_ai_calendar.func(SimpleNamespace(context=CONTEXT), date(2026, 11, 9), date(2026, 11, 9))
    assert seen == [41]
    assert len(result["events"]) == 40 and result["truncated"] is truncated
