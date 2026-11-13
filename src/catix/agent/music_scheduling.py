"""Host-only Music Room personal-calendar guard, independent of MCP business checks."""

import json
from datetime import date, datetime, time

from langgraph.errors import GraphBubbleUp

from catix.agent import schedule_tools
from catix.agent.scheduling import ScheduleCheckError, _busy, _calendar_conflicts, _period, _reads, _unknown, _unknown_duration
from catix.settings import settings


def _booking(arguments):
    """Exact schema-validated clocks; never infer a duration or select another slot."""
    day = date.fromisoformat(arguments["day"])
    return {field: datetime.combine(day, time.fromisoformat(arguments[key]), settings.tz).isoformat()
            for field, key in (("starts_at", "time_from"), ("ends_at", "time_to"))}


def check_booking(booking, agenda):
    period = _period(booking)
    conflicts, unknown = _calendar_conflicts(booking, _busy(agenda, period))
    if conflicts:
        raise ScheduleCheckError(
            "schedule_conflict", "The music booking overlaps the personal calendar. Do not request ordinary approval "
            "for this slot. Ask for a non-overlapping time; never move events or select another slot automatically.",
            conflicts=conflicts,
        )
    if unknown:
        raise _unknown_duration(unknown)
    return {"booking": dict(booking), "period": period}


def prepare_booking(arguments, messages, runtime):
    booking = _booking(arguments)
    period = _period(booking)
    agenda = _reads(messages).get("get_my_schedule")
    try:
        _busy(agenda, period)
    except ScheduleCheckError:
        # A stale, unmatched or incomplete snapshot is not evidence of free time.
        # One fresh host read may establish it; failures never fall back to old data.
        agenda = schedule_tools.read_my_schedule(runtime, date.fromisoformat(period["date_from"]), date.fromisoformat(period["date_to"]))
    return check_booking(booking, agenda)


def _approved_booking(arguments, runtime):
    state = getattr(runtime, "state", None) or {}
    for prepared in state.get("api_prepared", []):
        if (prepared.get("call_id") == getattr(runtime, "tool_call_id", None)
                and prepared.get("target") == "music_book_music_room"
                and json.dumps(prepared.get("arguments"), sort_keys=True) == json.dumps(arguments, sort_keys=True)
                and isinstance(prepared.get("schedule_check"), dict)):
            checked = prepared["schedule_check"]
            booking = _booking(arguments)
            if checked.get("booking") == booking and checked.get("period") == _period(booking):
                return checked
    raise _unknown("No matching calendar-checked approval. Read calendars and request approval again.")


def recheck_booking(arguments, runtime):
    """Fresh unified read after consent, before any remote mutation can execute."""
    try:
        approved = _approved_booking(arguments, runtime)
        period = approved["period"]
        agenda = schedule_tools.read_my_schedule(runtime, date.fromisoformat(period["date_from"]), date.fromisoformat(period["date_to"]))
        check_booking(approved["booking"], agenda)
    except GraphBubbleUp:
        raise
    except ScheduleCheckError as error:
        return error.result
    except Exception:
        return _unknown("The fresh calendar check failed.").result
    return None


async def arecheck_booking(arguments, runtime):
    try:
        approved = _approved_booking(arguments, runtime)
        period = approved["period"]
        agenda = await schedule_tools.aread_my_schedule(runtime, date.fromisoformat(period["date_from"]), date.fromisoformat(period["date_to"]))
        check_booking(approved["booking"], agenda)
    except GraphBubbleUp:
        raise
    except ScheduleCheckError as error:
        return error.result
    except Exception:
        return _unknown("The fresh calendar check failed.").result
    return None
