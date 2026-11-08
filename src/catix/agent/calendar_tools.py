"""Explicit local tools for the asker's AI Calendar (personal_calendar.py).

Read by the known site account or the account linked to Telegram. On the signed-in site, adding, replacing and removing
an event require the orchestrator's native approval flow. Mutations never use service authentication or a Telegram lookup.
The existing "➕ В мой календарь" answer buttons remain available in the bot and on the site.
"""

import logging
from datetime import date, datetime, time, timedelta
from typing import Literal

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from psycopg import Error as DatabaseError
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from catix import personal_calendar
from catix.common.dates import ClockTime
from catix.settings import settings

DEFAULT_DAYS = 14
MAX_EVENTS = 40
log = logging.getLogger("catix.calendar.tools")
NO_CALENDAR = (
    "The asker's AI Calendar is kept under their InNoHassle account, and this chat does not know it: it is in the Telegram "
    "bot (/calendar) and on the site innohassle.ru/calendar."
)
NOT_LINKED = (
    "The asker's Telegram is not linked to an InNoHassle account, where the AI Calendar is kept: they can link it at "
    f"{personal_calendar.CONNECT_TELEGRAM}."
)
UNAVAILABLE = "InNoHassle does not answer now, and the AI Calendar is kept under the asker's InNoHassle account: try later."


def _unknown_calendar_outcome() -> dict:
    # A lost connection can follow a commit; RuntimeError also covers a missing committed readback.
    # Never log the exception/traceback: database diagnostics may contain credentials or private data.
    log.warning("AI Calendar mutation outcome could not be confirmed")
    return {
        "done": None, "outcome": "unknown",
        "error": "The AI Calendar action could not be confirmed; changes may have been applied. "
                 "Check the calendar (read back its events) before deciding what to do. Do not retry automatically.",
    }


def calendar_key(runtime: ToolRuntime) -> tuple[str | None, str | None]:
    """(the key of the asker's AI Calendar, None) or (None, why it is not known)."""
    context = getattr(runtime, "context", None)
    telegram_id = getattr(context, "user_telegram_id", None)
    telegram_id = telegram_id if telegram_id and telegram_id > 0 else None  # (the Max bot gives -its user id: no Telegram)
    if innohassle_id := getattr(context, "innohassle_id", None):
        return personal_calendar.account_key(innohassle_id, telegram_id), None
    if not telegram_id:
        return None, NO_CALENDAR
    try:
        return personal_calendar.telegram_key(telegram_id), None
    except personal_calendar.NoAccount as e:
        return None, NOT_LINKED if str(e) == personal_calendar.NOT_LINKED else UNAVAILABLE


def _mutation_key(runtime: ToolRuntime) -> tuple[str | None, str | None]:
    """Only the site's authenticated user can mutate; never resolve a bot account through service auth."""
    context = getattr(runtime, "context", None)
    account = getattr(context, "innohassle_id", None)
    token = getattr(context, "innohassle_token", None)
    if not isinstance(account, str) or not account.strip() or not token or not token.get_secret_value().strip():
        return None, "AI Calendar actions require signing in on innohassle.ru; nothing was done here."
    return personal_calendar.account_key(account), None


def calendar_item(event: personal_calendar.PersonalEvent) -> dict:
    """An event of the AI Calendar as the model sees it, with the id remove_from_ai_calendar takes."""
    start = event.starts_at.astimezone(settings.tz)
    item: dict = {
        "calendar_event_id": event.id, "date": start.strftime("%Y-%m-%d %a"), "title": event.title,
        "all_day": event.all_day, "starts_at": event.starts_at.isoformat(),
        "ends_at": event.ends_at.isoformat() if event.ends_at is not None else None,
    }
    if not event.all_day:
        end = event.ends_at.astimezone(settings.tz) if event.ends_at else None
        item["time"] = f"{start:%H:%M}" + (f"-{end:%H:%M}" if end else "")
    if event.room:
        item["place"] = event.room
    if event.source_url:
        item["source"] = event.source_url
    return item


def events_between(key: str, start: date, end: date) -> list[dict]:
    """The AI Calendar's events, with one extra row to detect truncation."""
    first = datetime.combine(start, time.min, settings.tz)
    found = personal_calendar.between(key, first, datetime.combine(end + timedelta(days=1), time.min, settings.tz),
                                      limit=MAX_EVENTS + 1)
    return [calendar_item(e) for e in found]


class GetAiCalendarArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date_from: date | None = Field(None, description="YYYY-MM-DD, default today.")
    date_to: date | None = Field(None, description=f"YYYY-MM-DD inclusive, default date_from + {DEFAULT_DAYS - 1} days.")

    @model_validator(mode="before")
    @classmethod
    def without_injected_runtime(cls, values):
        if isinstance(values, dict) and isinstance(values.get("runtime"), ToolRuntime):
            return {key: value for key, value in values.items() if key != "runtime"}
        return values


@tool(args_schema=GetAiCalendarArgs)
def get_my_ai_calendar(runtime: ToolRuntime, date_from: date | None = None, date_to: date | None = None) -> dict:
    """The asker's local AI Calendar: personal events added through answer buttons or approved local actions,
    with ids, timestamps and source messages where available. Use date_from/date_to, not day.
    Use this only for explicitly local AI Calendar requests. For the full personal agenda use get_my_schedule,
    which includes these events together with selected class calendars, sport, enrolments and bookings.
    """
    start = date_from or datetime.now(settings.tz).date()
    end = date_to or start + timedelta(days=DEFAULT_DAYS - 1)
    return read_calendar(runtime, start, end)


def read_calendar(runtime, start: date, end: date) -> dict:
    """Read the local calendar for an explicit period, shared by both host agenda tools."""
    key, why = calendar_key(runtime)
    if key is None:
        return {"error": why}
    events = events_between(key, start, end)
    result: dict = {"range": [start.isoformat(), end.isoformat()], "events": events[:MAX_EVENTS],
                    "truncated": len(events) > MAX_EVENTS}
    if result["truncated"]:
        result["note"] = "Only the first 40 AI Calendar events are shown; narrow the dates. Availability is not verified."
    if not events:
        result["note"] = "No event of the AI Calendar in this period. Add through an answer button or an approved AI Calendar action on the site."
    return result


class RemoveFromAiCalendarArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    calendar_event_id: int = Field(gt=0, description="The `calendar_event_id` from get_my_ai_calendar.")

    @model_validator(mode="before")
    @classmethod
    def without_injected_runtime(cls, values):
        if isinstance(values, dict) and isinstance(values.get("runtime"), ToolRuntime):
            return {key: value for key, value in values.items() if key != "runtime"}
        return values


@tool(args_schema=RemoveFromAiCalendarArgs)
def remove_from_ai_calendar(calendar_event_id: int, runtime: ToolRuntime) -> dict:
    """Remove one event from the asker's AI Calendar. The asker approves or declines it before it is done: call it as soon as
    they asked; never ask them yourself."""
    try:
        calendar_event_id = RemoveFromAiCalendarArgs(calendar_event_id=calendar_event_id).calendar_event_id
    except ValidationError as e:
        return {"done": False, "error": str(e)}
    key, why = _mutation_key(runtime)
    if key is None:
        return {"done": False, "error": why}
    try:
        removed = personal_calendar.delete_event(key, calendar_event_id)
    except (DatabaseError, RuntimeError):
        return _unknown_calendar_outcome()
    if not removed:
        return {"done": False, "error": "No such event in the asker's AI Calendar: take its `calendar_event_id` from get_my_ai_calendar."}
    return {"done": True, "removed": calendar_event_id, "note": "Removed: tell the asker."}


class AddToAiCalendarArgs(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    title: str = Field(min_length=1, max_length=personal_calendar.MAX_TITLE_LENGTH)
    day: date = Field(description="YYYY-MM-DD in the local timezone.")
    all_day: bool = Field(False, description="True only when the asker explicitly requests an all-day event.")
    start_time: ClockTime | None = Field(None, description="Local HH:MM, required unless all_day is true.")
    end_time: ClockTime | None = Field(None, description="Known local HH:MM on end_day (default day), after the start. Never invent it. Use proposed_duration_minutes=90 to offer a duration when the end is unknown.")
    end_day: date | None = Field(None, description="Optional explicit end date for an overnight timed event, YYYY-MM-DD; requires end_time. Omit for same-day events.")
    proposed_duration_minutes: Literal[90] | None = Field(None, description="Explicit proposal, not a source fact: use 90 for a new timed event whose end is unknown, unless the user wants to leave it unknown. Approval shows the proposed interval; rejection saves nothing. Cannot combine with end_time/end_day/all_day.")
    room: str | None = Field(None, description="Optional place; not a room booking.")

    @model_validator(mode="before")
    @classmethod
    def without_injected_runtime(cls, values):
        # LangChain validates its injected ToolRuntime before restoring it from the original input.
        # Exclude that trusted object, not arbitrary extra model arguments or a model-supplied runtime dict.
        if isinstance(values, dict) and isinstance(values.get("runtime"), ToolRuntime):
            return {key: value for key, value in values.items() if key != "runtime"}
        return values

    @model_validator(mode="after")
    def valid_time_span(self):
        if self.proposed_duration_minutes is not None and (self.all_day or self.end_time is not None or self.end_day is not None):
            raise ValueError("A duration proposal requires a timed event without an explicit end.")
        for clock in (self.start_time, self.end_time):
            if clock is not None and clock.tzinfo is not None:
                raise ValueError("Use local clock times without a timezone offset.")
        if self.all_day:
            if self.start_time is not None or self.end_time is not None or self.end_day is not None:
                raise ValueError("An all-day event must not specify start_time, end_time or end_day.")
        elif self.start_time is None:
            raise ValueError("Specify start_time, or explicitly request all_day=true.")
        elif self.end_day is not None and self.end_time is None:
            raise ValueError("end_day requires an explicit end_time.")
        elif self.end_time is not None and datetime.combine(self.end_day or self.day, self.end_time) <= datetime.combine(self.day, self.start_time):
            raise ValueError("The end date and time must be after the start.")
        return self

    @property
    def end_suggested(self) -> bool:
        return self.proposed_duration_minutes is not None

    def event_values(self) -> dict:
        start = self.start_time or settings.changes_default_time
        starts_at = datetime.combine(self.day, start, settings.tz)
        ends_at = datetime.combine(self.end_day or self.day, self.end_time, settings.tz) if self.end_time else None
        if self.proposed_duration_minutes is not None:
            ends_at = starts_at + timedelta(minutes=self.proposed_duration_minutes)
        return {
            "title": self.title, "starts_at": starts_at, "all_day": self.all_day,
            "ends_at": ends_at, "room": self.room,
        }


@tool(args_schema=AddToAiCalendarArgs)
def add_to_ai_calendar(
    title: str, day: date, runtime: ToolRuntime, all_day: bool = False,
    start_time: ClockTime | None = None, end_time: ClockTime | None = None, room: str | None = None,
    end_day: date | None = None,
    proposed_duration_minutes: Literal[90] | None = None,
) -> dict:
    """Add one personal event to the asker's AI Calendar, not a booking or enrollment. The asker approves it before it runs.
    If no end is known, leave end_time unset and use proposed_duration_minutes=90 to offer a duration explicitly.
    Only approval saves that end; omitting the proposal leaves it unknown, including for old pending actions.
    Never invent end_time yourself. No recurrence or notifications. A repeated title and start keeps the existing details."""
    try:
        args = AddToAiCalendarArgs(title=title, day=day, all_day=all_day, start_time=start_time, end_time=end_time, room=room,
                                   end_day=end_day, proposed_duration_minutes=proposed_duration_minutes)
    except ValidationError as e:
        return {"done": False, "error": str(e)}
    key, why = _mutation_key(runtime)
    if key is None:
        return {"done": False, "error": why}
    try:
        event = personal_calendar.add_event(key, **args.event_values())
    except (DatabaseError, RuntimeError):
        return _unknown_calendar_outcome()
    except ValueError as e:
        return {"done": False, "error": str(e)}
    return {"done": True, "event": calendar_item(event), "note": "Saved in AI Calendar; if already present, its existing details were kept."}


class UpdateAiCalendarArgs(AddToAiCalendarArgs):
    calendar_event_id: int = Field(gt=0, description="The owned event id from get_my_ai_calendar.")
    end_time: ClockTime | None = Field(None, description="Known local HH:MM on end_day (default day), after the start. Omitted/null clears the end; updating never silently proposes a default duration.")


@tool(args_schema=UpdateAiCalendarArgs)
def update_ai_calendar(
    calendar_event_id: int, title: str, day: date, runtime: ToolRuntime, all_day: bool = False,
    start_time: ClockTime | None = None, end_time: ClockTime | None = None, room: str | None = None,
    end_day: date | None = None,
    proposed_duration_minutes: Literal[90] | None = None,
) -> dict:
    """Replace one owned AI Calendar event after approval. Read it first and pass every unchanged field too: omitted room
    and end_time are cleared. A material edit clears its old source attribution. No booking, recurrence or notifications."""
    try:
        args = UpdateAiCalendarArgs(calendar_event_id=calendar_event_id, title=title, day=day, all_day=all_day,
                                    start_time=start_time, end_time=end_time, room=room, end_day=end_day,
                                    proposed_duration_minutes=proposed_duration_minutes)
    except ValidationError as e:
        return {"done": False, "error": str(e)}
    key, why = _mutation_key(runtime)
    if key is None:
        return {"done": False, "error": why}
    try:
        event = personal_calendar.update_event(key, args.calendar_event_id, **args.event_values())
    except (DatabaseError, RuntimeError):
        return _unknown_calendar_outcome()
    except ValueError as e:
        return {"done": False, "error": str(e)}
    if event is None:
        return {"done": False, "error": "No such event in the asker's AI Calendar: read get_my_ai_calendar first."}
    return {"done": True, "event": calendar_item(event), "note": "Saved the event's requested details in AI Calendar."}


CALENDAR_TOOLS = [get_my_ai_calendar, remove_from_ai_calendar, add_to_ai_calendar, update_ai_calendar]

