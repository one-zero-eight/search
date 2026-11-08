"""Read-only Music Room windows checked against the host's full personal agenda."""
import re
from datetime import date, datetime, time, timedelta

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from langgraph.errors import GraphBubbleUp
from pydantic import BaseModel, ConfigDict, Field, model_validator

from catix.agent.api_tools import _credentials
from catix.agent.schedule_tools import read_my_schedule
from catix.agent.scheduling import ScheduleCheckError, _busy, _overlaps
from catix.innohassle import mcp_client
from catix.settings import settings


class AvailableMusicArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    day: date = Field(description="One requested local date, YYYY-MM-DD. Ask if unknown.")
    duration_minutes: int | None = Field(None, strict=True, ge=30, le=1440, multiple_of=30,
                                         description="Only the user's requested duration; omit to show windows without choosing it.")

    @model_validator(mode="before")
    @classmethod
    def without_injected_runtime(cls, values):
        if isinstance(values, dict) and isinstance(values.get("runtime"), ToolRuntime):
            return {key: value for key, value in values.items() if key != "runtime"}
        return values


def _at(day, clock):
    if not isinstance(clock, str) or not re.fullmatch(r"(?:[01][0-9]|2[0-3]):(?:00|30)", clock):
        raise ValueError("Music windows must use the half-hour HH:MM grid.")
    return datetime.combine(day, time.fromisoformat(clock), settings.tz)


def _span(start, end):
    return {"start": start.strftime("%H:%M"), "end": end.strftime("%H:%M"),
            "starts_at": start.isoformat(), "ends_at": end.isoformat()}


def _windows(music, day, duration_minutes):
    """Validate the client wire contract before using service data as availability."""
    if (not isinstance(music, dict) or "error" in music or music.get("truncated") or music.get("more")
            or music.get("date") != day.isoformat() or music.get("timezone") != str(settings.tz)
            or music.get("availability") != "calculated" or music.get("duration_minutes") != duration_minutes
            or not isinstance(music.get("windows"), list)):
        raise ValueError("Music availability is unverified.")
    checked = datetime.fromisoformat(music["checked_at"])
    rules = music["rules"]
    horizon = datetime.fromisoformat(rules["latest_booking_start"])
    if (checked.utcoffset() is None or horizon.utcoffset() is None or horizon < checked
            or type(rules.get("step_minutes")) is not int or rules["step_minutes"] != 30):
        raise ValueError("Music availability rules are unverified.")
    opening, closing = _at(day, rules["opens_at"]), _at(day, rules["closes_at"])
    if closing <= opening:
        raise ValueError("Music opening interval is invalid.")
    windows = music["windows"]
    if not windows:
        if music.get("reason") not in {"outside_booking_horizon", "access_denied", "insufficient_quota", "no_matching_window"}:
            raise ValueError("Missing Music Room refusal reason.")
        return windows
    quotas = [music[key] for key in ("remaining_daily_minutes", "remaining_weekly_minutes")]
    if music.get("reason") is not None or any(type(value) is not int or value < 0 for value in quotas):
        raise ValueError("Music quotas are unverified.")
    minimum = duration_minutes or 30
    previous_end = opening
    for window in windows:
        start, end, latest = (_at(day, window[key]) for key in ("start", "end", "latest_start"))
        maximum = window["max_duration_minutes"]
        if (not previous_end <= start < end <= closing or not checked < start <= latest <= horizon
                or latest + timedelta(minutes=minimum) > end
                or type(maximum) is not int or maximum % 30 or not minimum <= maximum <= min(quotas)
                or maximum > (end - start).total_seconds() / 60):
            raise ValueError("Music window bounds or limits are invalid.")
        previous_end = end
    return windows


def _fit_windows(day, duration_minutes, windows, busy):
    """Keep the service's half-hour grid, per-window quota and latest start bound."""
    available, excluded = [], []
    step = timedelta(minutes=30)
    minimum = timedelta(minutes=duration_minutes or 30)
    for window in windows:
        cursor, end = _at(day, window["start"]), _at(day, window["end"])
        conflicts = [event for event in busy if _overlaps(_span(cursor, end), event)]
        if conflicts:
            excluded.append({"reason": "schedule_conflict", "conflicts": conflicts})
        free = []
        while cursor < end:
            finish = cursor + step
            item = _span(cursor, finish)
            if not any(_overlaps(item, event) for event in conflicts):
                if free and free[-1][1] == cursor:
                    free[-1] = (free[-1][0], finish)
                else:
                    free.append((cursor, finish))
            cursor = finish
        for start, finish in free:
            maximum = min(window["max_duration_minutes"], int((finish - start).total_seconds() // 60))
            latest = min(finish - minimum, _at(day, window["latest_start"]))
            item = _span(start, finish)
            if latest < start or maximum < minimum.total_seconds() / 60:
                excluded.append({**item, "reason": "no_matching_duration_or_start"})
            else:
                available.append({**item, "latest_start": latest.strftime("%H:%M"), "max_duration_minutes": maximum})
    return available, excluded


@tool(args_schema=AvailableMusicArgs, response_format="content_and_artifact")
def get_my_available_music_windows(runtime: ToolRuntime, day: date, duration_minutes: int | None = None) -> tuple[dict, dict | None]:
    """Find music room windows that fit MY full personal agenda, including AI Calendar, for ONE explicit day.
    Когда мне можно поиграть / подбери свободное время в музкомнате без пересечений с занятиями.
    Combines Music Room access, quotas and occupied intervals with get_my_schedule. No separate calendar read needed.
    Recommend only available; excluded/unverified are NOT free time. Omit duration_minutes unless the user specified it.
    complete=false means UNKNOWN, not no available slots. Report the missing data; do not retry the same reads this turn.
    Windows share the quota; max_duration_minutes is a limit, not the selected booking duration.
    No booking or signup. Booking requires the user's exact interval, separate approval and fresh checks.
    """
    try:
        token, credentials = _credentials("innohassle", runtime)
    except ValueError as error:
        return {"error": str(error)}, None
    arguments = {"day": day.isoformat(), **({"duration_minutes": duration_minutes} if duration_minutes is not None else {})}
    try:
        music = mcp_client.request_sync("call_tool", {"name": "music_get_available_windows", "arguments": arguments},
                                       token, **credentials)
        windows = _windows(music, day, duration_minutes)
    except GraphBubbleUp:
        raise
    except Exception:
        return {"error": "Music Room availability could not be checked; availability is unknown."}, None
    agenda = read_my_schedule(runtime, day, day)
    available, excluded, unverified, not_read = [], [], [], []
    try:
        busy = _busy(agenda, {"date_from": day.isoformat(), "date_to": day.isoformat()})
        available, excluded = _fit_windows(day, duration_minutes, windows, busy)
    except ScheduleCheckError as error:
        unverified = [{**window, "reason": error.result["code"]} for window in windows]
        not_read = [*agenda.get("not_read", []), "Personal calendar coverage or event durations are incomplete; "
                    "availability is unknown, not a fully booked day. Do not repeat these reads in the same turn."]
    result = {"range": [day.isoformat(), day.isoformat()], "timezone": str(settings.tz),
              "duration_minutes": duration_minutes, "available": available, "excluded": excluded, "unverified": unverified,
              "total": len(available) + len(excluded) + len(unverified), "complete": not not_read,
              "truncated": bool(agenda.get("truncated")), "not_read": not_read,
              "remaining_daily_minutes": music["remaining_daily_minutes"],
              "remaining_weekly_minutes": music["remaining_weekly_minutes"], "rules": music["rules"],
              "reason": music.get("reason"), "checked_at": datetime.now(settings.tz).isoformat(),
              "service_checked_at": music["checked_at"],
              "note": "Calculated using conservative local Music Room rules, not a reservation or guaranteed access. "
                      "Quotas apply to the requested date, not necessarily today. A window is a range of choices, not a booking interval. "
                      "Describe classes/meetings only using exact starts_at/ends_at inside conflicts. "
                      "Windows are alternatives sharing the same quota. max_duration_minutes is the limit at the window's start; "
                      "latest_start is for the requested duration, or the minimum 30 minutes if omitted. "
                      "Do not book the whole window or select a duration automatically."}
    return result, {"music": music, "agenda": agenda, "music_arguments": arguments}
