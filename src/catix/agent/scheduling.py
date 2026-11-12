"""Interval helpers shared by the When2Meet personal slot check."""

from datetime import datetime, time, timedelta

from catix.settings import settings


class ScheduleCheckError(ValueError):
    requires_user_input = False

    def __init__(self, code, message, **details):
        super().__init__(message)
        self.result = {"done": False, "code": code, "error": message, **details}


def _unknown(message):
    return ScheduleCheckError("schedule_unverified", message + " Nothing was written; do not claim the time is free.")


def _calendar_interval(item):
    try:
        start = datetime.fromisoformat(item["starts_at"])
        if start.utcoffset() is None:
            raise ValueError
        # Local all-day entries have no end and may store the display default hour.
        # Their calendar semantics are one entire local day, not an unknown timed event.
        if item.get("all_day") is True and item.get("ends_at") is None:
            start = datetime.combine(start.astimezone(settings.tz).date(), time.min, settings.tz)
            return start, start + timedelta(days=1)
        if "ends_at" in item and item["ends_at"] is None:
            return start.astimezone(settings.tz), None
        end = datetime.fromisoformat(item["ends_at"])
        if start.utcoffset() is None or end.utcoffset() is None or end <= start:
            raise ValueError
        if item.get("all_day") is True:
            start = datetime.combine(start.astimezone(settings.tz).date(), time.min, settings.tz)
            end = datetime.combine(end.astimezone(settings.tz).date(), time.min, settings.tz)
            return start, max(start + timedelta(days=1), end)
        return start.astimezone(settings.tz), end.astimezone(settings.tz)
    except (KeyError, TypeError, ValueError, AttributeError):
        raise _unknown("Missing or invalid timezone-aware starts_at/ends_at; read the full event duration.") from None


def _interval(item):
    start, end = _calendar_interval(item)
    if end is None:
        raise _unknown("Missing or invalid timezone-aware starts_at/ends_at; read the full event duration.")
    return start, end


def _busy(agenda, period):
    """Best-effort busy list: unread, partial, all-day, open-ended or malformed events never block."""
    events = agenda.get("events") if isinstance(agenda, dict) else None
    busy = []
    for item in events if isinstance(events, list) else []:
        if not isinstance(item, dict) or item.get("all_day") is True:
            continue
        try:
            _, end = _calendar_interval(item)
        except ScheduleCheckError:
            continue
        if end is not None:
            busy.append(item)
    return busy


def _calendar_conflicts(item, busy):
    """Separate definite overlap from unknown duration, without inventing an end."""
    start, end = _interval(item)
    conflicts, unknown = [], []
    for event in busy:
        other_start, other_end = _calendar_interval(event)
        if other_end is None:
            if other_start < end:
                unknown.append(event)
        elif start < other_end and other_start < end:
            conflicts.append(event)
    return conflicts, unknown
