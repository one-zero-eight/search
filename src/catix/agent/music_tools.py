"""Read-only Music Room windows checked against the host's full personal agenda."""
import re
from datetime import date, datetime, time, timedelta

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from langgraph.errors import GraphBubbleUp
from pydantic import BaseModel, ConfigDict, Field, model_validator

from catix.agent.api_tools import _credentials
from catix.agent.schedule_tools import read_my_schedule
from catix.agent.scheduling import ScheduleCheckError, _busy, _calendar_conflicts
from catix.innohassle import mcp_client
from catix.settings import settings


class AvailableMusicArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    day: date = Field(description="One requested local date, YYYY-MM-DD. Ask if unknown.")
    duration_minutes: int | None = Field(None, strict=True, ge=30, le=1440, multiple_of=30,
                                         description="Only the user's requested duration; omit to show windows without choosing it.")
    time_from: str | None = Field(None, pattern=r"^(?:[01][0-9]|2[0-3]):(?:00|30)$",
                                  description="Exact requested start, HH:MM. Always pass both times when the user specifies an interval.")
    time_to: str | None = Field(None, pattern=r"^(?:[01][0-9]|2[0-3]):(?:00|30)$",
                                description="Exact requested end on the same day, HH:MM; never replace exact times with duration alone.")

    @model_validator(mode="before")
    @classmethod
    def without_injected_runtime(cls, values):
        if isinstance(values, dict) and isinstance(values.get("runtime"), ToolRuntime):
            return {key: value for key, value in values.items() if key != "runtime"}
        return values

    @model_validator(mode="after")
    def exact_interval(self):
        if (self.time_from is None) != (self.time_to is None):
            raise ValueError("Pass both time_from and time_to, or omit both.")
        if self.time_from is not None:
            if self.time_from >= self.time_to:
                raise ValueError("time_to must be after time_from on the same day.")
            duration = int((_at(self.day, self.time_to) - _at(self.day, self.time_from)).total_seconds() // 60)
            if self.duration_minutes is not None and self.duration_minutes != duration:
                raise ValueError("duration_minutes must match the exact requested interval.")
            self.duration_minutes = duration
        return self


def _at(day, clock):
    if not isinstance(clock, str) or not re.fullmatch(r"(?:[01][0-9]|2[0-3]):(?:00|30)", clock):
        raise ValueError("Music windows must use the half-hour HH:MM grid.")
    return datetime.combine(day, time.fromisoformat(clock), settings.tz)


def _span(start, end):
    return {"start": start.strftime("%H:%M"), "end": end.strftime("%H:%M"),
            "starts_at": start.isoformat(), "ends_at": end.isoformat()}


def _windows(music, day, duration_minutes, time_from=None, time_to=None):
    """Validate the client wire contract before using service data as availability."""
    if time_from is not None or time_to is not None:
        args = AvailableMusicArgs(day=day, duration_minutes=duration_minutes, time_from=time_from, time_to=time_to)
        duration_minutes = args.duration_minutes
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
    requested = music.get("requested_interval")
    if time_from is not None or time_to is not None:
        expected = {key: value for key, value in _span(_at(day, args.time_from), _at(day, args.time_to)).items()
                    if key in {"starts_at", "ends_at"}}
        if requested != expected:
            raise ValueError("Music availability does not match the requested interval.")
    elif requested is not None:
        raise ValueError("Unexpected exact Music Room response to a day-wide request.")
    windows = music["windows"]
    if not windows:
        if music.get("reason") not in {"outside_booking_horizon", "access_denied", "insufficient_quota", "no_matching_window",
                                       "outside_opening_hours", "past", "room_occupied"}:
            raise ValueError("Missing Music Room refusal reason.")
        if requested is not None and music.get("reason") == "room_occupied":
            occupied = music.get("occupied_intervals")
            if not isinstance(occupied, list) or not occupied:
                raise ValueError("Missing exact Music Room occupancy evidence.")
            previous = _at(day, time_from)
            for item in occupied:
                if not isinstance(item, dict) or set(item) != {"starts_at", "ends_at"}:
                    raise ValueError("Invalid Music Room occupancy evidence.")
                start, end = (datetime.fromisoformat(item[key]) for key in ("starts_at", "ends_at"))
                if start.utcoffset() is None or end.utcoffset() is None or not previous <= start < end <= _at(day, time_to):
                    raise ValueError("Music Room occupancy is outside the requested interval.")
                previous = end
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
    if requested is not None and windows != [{"start": time_from, "end": time_to, "latest_start": time_from,
                                               "max_duration_minutes": duration_minutes}]:
        raise ValueError("Music availability window differs from the exact requested interval.")
    return windows


def _fit_windows(day, duration_minutes, windows, busy, time_from=None, time_to=None):
    """Keep the service's half-hour grid, per-window quota and latest start bound."""
    available, excluded, unverified = [], [], []
    if time_from is not None:
        if not windows:
            return available, excluded, unverified
        item = {**_span(_at(day, time_from), _at(day, time_to)), "latest_start": time_from,
                "max_duration_minutes": duration_minutes}
        conflicts, unknown = _calendar_conflicts(item, busy)
        if conflicts:
            excluded.append({"reason": "schedule_conflict", "conflicts": conflicts})
        elif unknown:
            unverified.append({**item, "reason": "schedule_unverified", "uncertainty": "unknown_event_end",
                               "unknown_duration_events": unknown})
        else:
            available.append(item)
        return available, excluded, unverified
    step = timedelta(minutes=30)
    minimum = timedelta(minutes=duration_minutes or 30)
    for window in windows:
        cursor, end = _at(day, window["start"]), _at(day, window["end"])
        conflicts, _ = _calendar_conflicts(_span(cursor, end), busy)
        if conflicts:
            excluded.append({"reason": "schedule_conflict", "conflicts": conflicts})
        segments, uncertain = [], []
        while cursor < end:
            finish = cursor + step
            item = _span(cursor, finish)
            overlaps, unknown = _calendar_conflicts(item, busy)
            if not overlaps and not unknown:
                if segments and segments[-1][1] == cursor:
                    segments[-1] = (segments[-1][0], finish)
                else:
                    segments.append((cursor, finish))
            # Check the whole requested interval, including starts before an
            # unknown event whose requested finish crosses that event's start.
            candidate_end = cursor + minimum
            if candidate_end <= end and cursor <= _at(day, window["latest_start"]):
                overlaps, unknown = _calendar_conflicts(_span(cursor, candidate_end), busy)
                if unknown and not overlaps:
                    if uncertain and uncertain[-1][1] + step == cursor and uncertain[-1][2] == unknown:
                        uncertain[-1] = (uncertain[-1][0], cursor, unknown)
                    else:
                        uncertain.append((cursor, cursor, unknown))
            cursor = finish
        for start, finish in segments:
            maximum = min(window["max_duration_minutes"], int((finish - start).total_seconds() // 60))
            latest = min(finish - minimum, _at(day, window["latest_start"]))
            item = _span(start, finish)
            if latest < start or maximum < minimum.total_seconds() / 60:
                excluded.append({**item, "reason": "no_matching_duration_or_start"})
            else:
                available.append({**item, "latest_start": latest.strftime("%H:%M"), "max_duration_minutes": maximum})
        for start, latest, unknown in uncertain:
            finish = latest + minimum
            maximum = min(window["max_duration_minutes"], int((finish - start).total_seconds() // 60))
            unverified.append({**_span(start, finish), "latest_start": latest.strftime("%H:%M"), "max_duration_minutes": maximum,
                               "reason": "schedule_unverified", "uncertainty": "unknown_event_end", "unknown_duration_events": unknown})
    return available, excluded, unverified


@tool(args_schema=AvailableMusicArgs, response_format="content_and_artifact")
def get_my_available_music_windows(runtime: ToolRuntime, day: date, duration_minutes: int | None = None,
                                   time_from: str | None = None, time_to: str | None = None) -> tuple[dict, dict | None]:
    """Find music room windows that fit MY full personal agenda, including AI Calendar, for ONE explicit day.
    Когда мне можно поиграть / подбери свободное время в музкомнате без пересечений с занятиями.
    Combines Music Room access, quotas and occupied intervals with get_my_schedule. No separate calendar read needed.
    Recommend only available; excluded/unverified are NOT free time. Omit duration_minutes unless the user specified it.
    When the user specifies an exact interval, pass BOTH time_from and time_to, not just its duration.
    Exact mode checks only that interval; a service refusal does not imply room occupancy or personal conflicts.
    Never derive extra windows from gaps between excluded events: conflicts is NOT the full calendar or room schedule.
    complete=false means some availability is UNKNOWN, not no available slots. Available windows remain safe choices.
    unknown_duration_events names events needing an end time; ask when they end, not for another calendar read.
    Report missing source data separately; do not retry the same reads this turn.
    Windows share the quota; max_duration_minutes is a limit, not the selected booking duration.
    No booking or signup. Booking requires the user's exact interval, separate approval and fresh checks.
    """
    args = AvailableMusicArgs(day=day, duration_minutes=duration_minutes, time_from=time_from, time_to=time_to)
    day, duration_minutes = args.day, args.duration_minutes
    try:
        token, credentials = _credentials("innohassle", runtime)
    except ValueError as error:
        return {"error": str(error)}, None
    arguments = args.model_dump(mode="json", exclude_none=True)
    failure = {"error": "Music Room availability could not be checked; availability is unknown.",
               "code": "music_unverified", "complete": False,
               "note": "Personal Music Room availability was not verified. End this turn with an uncertainty report: "
                       "'Не удалось проверить, когда вам подходит музкомната: проверка не завершена.' "
                       "Do not retry this recommendation or call get_my_schedule, get_my_ai_calendar, "
                       "music_get_available_windows, music_get_music_room_schedule or public group timetables "
                       "to bypass it in the same turn. A separate calendar read cannot establish Music Room availability. "
                       "Do not recommend windows or offer a booking. The user may request a new check later."}
    music = None
    try:
        music = mcp_client.request_sync("call_tool", {"name": "music_get_available_windows", "arguments": arguments},
                                       token, **credentials)
        if isinstance(music, dict) and "error" in music and music.get("code") in ("upstream_timeout", "mcp_timeout"):
            service = "The Music Room service" if music["code"] == "upstream_timeout" else "MCP"
            return {**failure, "code": music["code"],
                    "error": f"{service} did not answer in time; personal Music Room availability is unknown."}, (
                        {"music": music, "agenda": None, "music_arguments": arguments} if time_from is not None else None)
        windows = _windows(music, day, duration_minutes, time_from, time_to)
    except GraphBubbleUp:
        raise
    except Exception:
        return failure, ({"music": music, "agenda": None, "music_arguments": arguments}
                         if time_from is not None and music is not None else None)
    agenda = read_my_schedule(runtime, day, day) if time_from is None or windows else None
    available, excluded, unverified, not_read = [], [], [], []
    try:
        if agenda is not None:
            busy = _busy(agenda, {"date_from": day.isoformat(), "date_to": day.isoformat()})
            available, excluded, unverified = _fit_windows(day, duration_minutes, windows, busy, time_from, time_to)
        else:
            excluded = [{**music["requested_interval"], "reason": music["reason"]}]
            if music.get("reason") == "room_occupied":
                excluded[0]["occupied_intervals"] = music["occupied_intervals"]
    except ScheduleCheckError as error:
        unverified = [{**window, "reason": error.result["code"]} for window in windows]
        not_read = [*agenda.get("not_read", []), "Personal calendar coverage or event times are invalid or incomplete; "
                    "availability is unknown, not a fully booked day. Do not repeat these reads in the same turn."]
    result = {"range": [day.isoformat(), day.isoformat()], "timezone": str(settings.tz),
              "duration_minutes": duration_minutes, "available": available, "excluded": excluded, "unverified": unverified,
              "total": len(available) + len(excluded) + len(unverified), "complete": not not_read and not unverified,
              "truncated": bool(agenda and agenda.get("truncated")), "not_read": not_read,
              "source_errors": agenda.get("source_errors", {}) if agenda else {},
              "remaining_daily_minutes": music["remaining_daily_minutes"],
              "remaining_weekly_minutes": music["remaining_weekly_minutes"], "rules": music["rules"],
              "reason": music.get("reason"), "checked_at": datetime.now(settings.tz).isoformat(),
              "service_checked_at": music["checked_at"],
              "note": "Calculated using conservative local Music Room rules, not a reservation or guaranteed access. "
                      "ONLY the available list contains verified choices. Do not calculate other free windows between conflicts; "
                      "excluded events are not the full calendar or room occupancy. "
                      "Unknown event ends affect only unverified intervals; ask when those named events end. "
                      "Quotas apply to the requested date, not necessarily today. A window is a range of choices, not a booking interval. "
                      "Describe classes/meetings only using exact starts_at/ends_at inside conflicts. "
                      "Windows are alternatives sharing the same quota. max_duration_minutes is the limit at the window's start; "
                      "latest_start is for the requested duration, or the minimum 30 minutes if omitted. "
                      "Do not book the whole window or select a duration automatically."}
    if time_from is not None:
        result["requested_interval"] = music["requested_interval"]
        result["note"] = ("Only the exact requested interval was checked. Recommend only available. "
                          "Report only the returned reason or actual overlapping conflicts; no other classes were relevant. "
                          "A service refusal does not establish room occupancy unless reason=room_occupied. "
                          "If the service refused the interval, the personal agenda was not read. "
                          "Unverified means unknown, not occupied. No reservation or guaranteed physical access.")
    return result, {"music": music, "agenda": agenda, "music_arguments": arguments}
