"""Read-only room recommendations for an exact interval, including AI Calendar."""
from datetime import date, datetime, time

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from langgraph.errors import GraphBubbleUp
from pydantic import BaseModel, ConfigDict, Field, model_validator

from catix.agent.api_tools import _credentials
from catix.agent.schedule_tools import read_my_schedule
from catix.agent.scheduling import ScheduleCheckError, _busy, _calendar_conflicts
from catix.innohassle import mcp_client
from catix.settings import settings


class AvailableRoomsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    day: date = Field(description="One explicit local date, YYYY-MM-DD. Ask if unknown.")
    time_from: str = Field(pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$", description="Requested start, HH:MM, Moscow time.")
    time_to: str = Field(pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$",
                         description="Requested end on the same day, HH:MM. Never invent a duration; ask if unknown.")

    @model_validator(mode="before")
    @classmethod
    def without_injected_runtime(cls, values):
        if isinstance(values, dict) and isinstance(values.get("runtime"), ToolRuntime):
            return {key: value for key, value in values.items() if key != "runtime"}
        return values


    @model_validator(mode="after")
    def ordered(self):
        if self.time_from >= self.time_to:
            raise ValueError("time_to must be after time_from on the same day.")
        return self


def _rooms(data, day, time_from, time_to):
    """Validate the existing MCP wire response, not server implementation models."""
    if (not isinstance(data, dict) or "error" in data or data.get("truncated") or data.get("more")
            or data.get("date") != day.strftime("%Y-%m-%d %a") or data.get("range") != f"{time_from}-{time_to}"
            or data.get("timezone") != str(settings.tz)
            or not all(isinstance(data.get(key), list) for key in ("free", "booked", "unavailable"))):
        raise ValueError("Room availability is unverified.")
    checked = datetime.fromisoformat(data["checked_at"])
    if checked.utcoffset() is None or checked >= datetime.combine(day, time.fromisoformat(time_from), settings.tz):
        raise ValueError("Room availability check time is invalid.")
    ids = list(data["booked"])
    for room in [*data["free"], *data["unavailable"]]:
        if not isinstance(room, dict):
            raise ValueError("Invalid room entry.")
        ids.append(room.get("room_id"))
    if (any(not isinstance(value, str) or not value.strip() or len(value) > 80 for value in ids)
            or len(ids) != len(set(ids))
            or "total" in data and (type(data["total"]) is not int or data["total"] != len(ids))):
        raise ValueError("Invalid or duplicate room identifiers/count.")
    for room in data["free"]:
        if (any(key in room and not isinstance(room[key], str) for key in ("title", "who", "night_only"))
                or "capacity" in room and (type(room["capacity"]) is not int or room["capacity"] < 0)):
            raise ValueError("Invalid room details.")
    if any(not isinstance(room.get("reason"), str) or not room["reason"].strip() for room in data["unavailable"]):
        raise ValueError("Missing room refusal reason.")
    return data


@tool(args_schema=AvailableRoomsArgs, response_format="content_and_artifact")
def get_my_available_rooms(runtime: ToolRuntime, day: date, time_from: str, time_to: str) -> tuple[dict, dict | None]:
    """Find bookable university rooms for ONE exact interval that fits MY full personal agenda including AI Calendar.
    Подбери доступные комнаты/аудитории для бронирования без пересечений с моими занятиями.
    Call ONLY when the user supplied BOTH start and end (or start and duration). A start alone is NOT enough:
    ask how long BEFORE any availability call; never assume one hour. day, time_from and time_to are required.
    Only available contains verified choices. excluded/unverified are NOT available recommendations.
    Conflicts are shared for the requested interval, not evidence that a room itself is occupied.
    complete=false means some checks are unknown, not that all rooms are booked. Do not repeat these reads this turn.
    unknown_duration_events identifies events whose end needs clarification; never invent an end or another free slot.
    This read never books anything and does not require approval.
    """
    try:
        token, credentials = _credentials("innohassle", runtime)
    except ValueError as error:
        return {"error": str(error)}, None
    arguments = {"day": day.isoformat(), "time_from": time_from, "time_to": time_to}
    try:
        rooms = mcp_client.request_sync("call_tool", {"name": "rooms_get_free_rooms", "arguments": arguments}, token, **credentials)
        rooms = _rooms(rooms, day, time_from, time_to)
    except GraphBubbleUp:
        raise
    except Exception:
        return {"error": "Room availability could not be checked for the requested interval; availability is unknown."}, None
    agenda = read_my_schedule(runtime, day, day)
    interval = {field: datetime.combine(day, time.fromisoformat(clock), settings.tz).isoformat()
                for field, clock in (("starts_at", time_from), ("ends_at", time_to))}
    available, unverified, conflicts, unknown, not_read = [], [], [], [], []
    excluded = [{"room_id": room_id, "reason": "room_occupied"} for room_id in rooms["booked"]]
    excluded.extend({"room_id": room["room_id"], "reason": "service_unavailable", "detail": room["reason"]}
                    for room in rooms["unavailable"])
    try:
        busy = _busy(agenda, {"date_from": day.isoformat(), "date_to": day.isoformat()})
        conflicts, unknown = _calendar_conflicts(interval, busy)
        if conflicts:
            excluded.extend({**room, "reason": "schedule_conflict"} for room in rooms["free"])
        elif unknown:
            unverified = [{**room, "reason": "schedule_unverified"} for room in rooms["free"]]
        else:
            available = rooms["free"]
    except ScheduleCheckError:
        unverified = [{**room, "reason": "schedule_unverified"} for room in rooms["free"]]
        not_read = [*agenda.get("not_read", []), "Personal calendar coverage or event times are incomplete or invalid; "
                    "personal availability is unknown. Do not repeat these reads in the same turn."]
    result = {"range": [day.isoformat(), day.isoformat()], "timezone": str(settings.tz), "interval": interval,
              "available": available, "excluded": excluded, "unverified": unverified, "conflicts": conflicts,
              "total": len(available) + len(excluded) + len(unverified), "complete": not not_read and not unverified,
              "truncated": bool(agenda.get("truncated")), "not_read": not_read,
              "checked_at": datetime.now(settings.tz).isoformat(), "service_checked_at": rooms["checked_at"],
              "note": "Only available contains personally verified choices. Rooms in unverified ARE free and permitted "
                      "by the room service; only their compatibility with the personal calendar is unknown. "
                      "Report that distinction, not 'no rooms available' or 'room occupancy unknown'. "
                      "Conflicts are personal events, not room occupancy. Do not infer alternative times. "
                      "Outlook data may be cached; this is not a reservation or guaranteed physical access."}
    if unknown and not conflicts:
        result.update(uncertainty="unknown_event_end", unknown_duration_events=unknown)
    return result, {"rooms": rooms, "agenda": agenda, "room_arguments": arguments}
