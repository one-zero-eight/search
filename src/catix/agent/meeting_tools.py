"""Read-only When2Meet recommendations over the host's complete personal agenda."""

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from langgraph.errors import GraphBubbleUp
from pydantic import BaseModel, ConfigDict, Field, model_validator

from catix.agent.api_tools import _credentials
from catix.agent.schedule_tools import read_my_schedule
from catix.agent.scheduling import ScheduleCheckError, _busy, _calendar_conflicts, _calendar_interval
from catix.innohassle import mcp_client

MOSCOW = ZoneInfo("Europe/Moscow")
SLOT_MINUTES = 30
MAX_CALENDAR_DAYS = 31


class MeetingSlotsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meeting_ref: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$",
                             description="Exact When2Meet slug or lowercase ObjectId, not a URL.")

    @model_validator(mode="before")
    @classmethod
    def without_injected_runtime(cls, values):
        if isinstance(values, dict) and isinstance(values.get("runtime"), ToolRuntime):
            return {key: value for key, value in values.items() if key != "runtime"}
        return values


def _poll_slots(meeting, reference):
    """Validate the client wire projection, without importing MCP server DTOs."""
    if (not isinstance(meeting, dict) or "error" in meeting
            or not isinstance(meeting.get("id"), str) or not re.fullmatch(r"[0-9a-f]{24}", meeting["id"])
            or not isinstance(meeting.get("slug"), str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", meeting["slug"])
            or reference != meeting["id" if re.fullmatch(r"[0-9a-f]{24}", reference) else "slug"]
            or meeting.get("page") != f"https://innohassle.ru/when2meet/{meeting['slug']}"
            or not isinstance(meeting.get("name"), str)
            or type(meeting.get("is_archived")) is not bool or type(meeting.get("my_participation")) is not bool
            or type(meeting.get("participants_count")) is not int or meeting["participants_count"] < 0):
        raise ValueError("Invalid meeting projection")
    parsed = []
    for key in ("slots", "common_slots"):
        values, count, truncated = meeting.get(key), meeting.get(key + "_count"), meeting.get(key + "_truncated")
        if (not isinstance(values, list) or len(values) > 2000 or type(count) is not int
                or count < len(values) or type(truncated) is not bool or truncated != (count > len(values))):
            raise ValueError("Invalid slot projection")
        instants = set()
        for value in values:
            start = datetime.fromisoformat(value)
            if start.utcoffset() is None:
                raise ValueError("Naive poll timestamp")
            start = start.astimezone(MOSCOW)
            start + timedelta(minutes=SLOT_MINUTES)  # Ensure the full cell is representable.
            instants.add(start)
        parsed.append(instants)
    starts, common = parsed
    if (not meeting["slots_truncated"] and not common <= starts
            or not meeting["participants_count"] and meeting["common_slots_count"]):
        raise ValueError("Invalid common slots")
    return sorted(starts), common


@tool(args_schema=MeetingSlotsArgs)
def get_my_available_meeting_slots(runtime: ToolRuntime, meeting_ref: str) -> dict:
    """Check When2Meet poll slots against my personal schedule AND AI Calendar. Какие варианты встречи мне подходят?
    Read-only: available fits my calendar; common_available also belongs to all respondents' selections (including
    mine if I responded). Nonrespondents are NOT agreement. excluded contains conflicts; unverified is NOT free time.
    Moscow half-hour cells, not a meeting-duration recommendation. Report incomplete/truncated results and exact
    conflicts; never infer extra free windows or repeat identical reads. Does not mark availability or book anything.
    """
    try:
        token, credentials = _credentials("innohassle", runtime)
    except ValueError as error:
        return {"error": str(error)}
    try:
        meeting = mcp_client.request_sync("call_tool", {"name": "when2meet_get_meeting",
                                         "arguments": {"meeting_ref": meeting_ref}}, token, **credentials)
        starts, common = _poll_slots(meeting, meeting_ref)
    except GraphBubbleUp:
        raise
    except Exception:
        return {"code": "meeting_unverified", "error": "The exact meeting and its slots could not be verified; availability is unknown."}

    not_read = []
    poll_complete = not (meeting["slots_truncated"] or meeting["common_slots_truncated"])
    if not poll_complete:
        not_read.append("The poll's slots or common slots are truncated; this is not an exhaustive result.")
    now = getattr(getattr(runtime, "context", None), "asked_at", None) or datetime.now(MOSCOW)
    available, common_available, excluded, unverified = [], [], [], []
    candidates = []
    for start in starts:
        item = {"starts_at": start.isoformat(), "ends_at": (start + timedelta(minutes=SLOT_MINUTES)).isoformat()}
        if meeting["is_archived"] or start < now:
            excluded.append({**item, "reason": "meeting_archived" if meeting["is_archived"] else "past_slot"})
        elif start.minute % SLOT_MINUTES or start.second or start.microsecond:
            unverified.append({**item, "reason": "unsupported_slot"})
        else:
            candidates.append(item)

    calendar_complete, calendar_truncated = None, False
    busy = []
    if candidates:
        first = datetime.fromisoformat(candidates[0]["starts_at"]).date()
        last = (datetime.fromisoformat(candidates[-1]["ends_at"]) - timedelta(microseconds=1)).date()
        if (last - first).days >= MAX_CALENDAR_DAYS:
            unverified.extend({**item, "reason": "calendar_range_too_large"} for item in candidates)
            candidates = []
            not_read.append("The poll spans more than 31 calendar days; the personal agenda was not read.")
        else:
            try:
                agenda = read_my_schedule(runtime, first, last)
            except GraphBubbleUp:
                raise
            except Exception:
                agenda = {"error": "unavailable"}
            if not isinstance(agenda, dict):
                agenda = {"error": "unavailable"}
            calendar_truncated = bool(agenda.get("truncated"))
            problems = agenda.get("not_read", [])
            if isinstance(problems, list) and all(isinstance(value, str) for value in problems):
                not_read.extend(problems)
            calendar_complete = True
            try:
                busy = _busy(agenda, {"date_from": first.isoformat(), "date_to": last.isoformat()})
            except ScheduleCheckError:
                calendar_complete = False
                not_read.append("The personal agenda could not be fully verified; other cells are not known to be free.")
                # A partial read can still prove an overlap. Keep exact known events.
                for event in agenda.get("events", []) if isinstance(agenda.get("events"), list) else []:
                    try:
                        _calendar_interval(event)
                        busy.append(event)
                    except ScheduleCheckError:
                        continue
    for item in candidates:
        conflicts, unknown = _calendar_conflicts(item, busy)
        if conflicts:
            excluded.append({**item, "reason": "schedule_conflict", "conflicts": conflicts})
        elif unknown:
            unverified.append({**item, "reason": "schedule_unverified", "uncertainty": "unknown_event_end",
                               "unknown_duration_events": unknown})
        elif not calendar_complete:
            unverified.append({**item, "reason": "schedule_unverified"})
        else:
            available.append(item)
            if datetime.fromisoformat(item["starts_at"]) in common:
                common_available.append(item)
    period = ([starts[0].date().isoformat(),
               (starts[-1] + timedelta(minutes=SLOT_MINUTES, microseconds=-1)).date().isoformat()] if starts else None)
    return {"meeting_ref": meeting_ref, "id": meeting["id"], "slug": meeting["slug"], "name": meeting["name"],
            "page": meeting["page"], "range": period, "timezone": str(MOSCOW), "is_archived": meeting["is_archived"],
            "slot_duration_minutes": SLOT_MINUTES, "participants_count": meeting["participants_count"],
            "my_participation": meeting["my_participation"], "available": available, "common_available": common_available,
            "excluded": excluded, "unverified": unverified, "total": len(starts), "slots_count": meeting["slots_count"],
            "poll_complete": poll_complete, "calendar_complete": calendar_complete,
            "complete": poll_complete and not not_read and not unverified,
            "truncated": not poll_complete or calendar_truncated, "not_read": not_read,
            "checked_at": datetime.now(MOSCOW).isoformat()}
