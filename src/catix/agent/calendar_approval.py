"""Native orchestrator approval for local AI Calendar actions, independent of MCP."""

import logging
from datetime import datetime

from langchain_core.messages import HumanMessage
from psycopg import Error as DatabaseError
from pydantic import ValidationError

from catix import personal_calendar
from catix.agent.calendar_tools import AddToAiCalendarArgs, RemoveFromAiCalendarArgs, UpdateAiCalendarArgs, _mutation_key
from catix.settings import settings

log = logging.getLogger("catix.calendar.approval")
MONTHS_RU = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
WEEKDAYS_RU = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]


def _calendar_business_args(args: dict) -> dict:
    """ToolNode overwrites runtime; normalize the same field before consent and execution."""
    return {key: value for key, value in args.items() if key != "runtime"}


def _russian(state) -> bool:
    question = next((str(m.content) for m in reversed(state.get("messages", [])) if isinstance(m, HumanMessage)), "")
    letters = [c for c in question if c.isalpha()]
    return not letters or sum("Ѐ" <= c <= "ӿ" for c in letters) * 2 >= len(letters)


def _calendar_when(start: datetime, end: datetime | None, ru: bool) -> str:
    day = f"{WEEKDAYS_RU[start.weekday()]}, {start.day} {MONTHS_RU[start.month - 1]}" if ru else start.strftime("%a, %d %b")
    return f"{day} {start.year}, {start:%H:%M}" + (f"–{end:%H:%M}" if end else "")


def _calendar_event_for_approval(runtime, event_id: int, ru: bool) -> tuple[personal_calendar.PersonalEvent | None, str]:
    try:
        # Use exactly the mutation owner; never a Telegram lookup for write approval.
        key, _ = _mutation_key(runtime)
        return (personal_calendar.event_of(key, event_id) if key else None), ""
    except (DatabaseError, RuntimeError):
        log.warning("AI Calendar event details unavailable during approval")
        return None, (" Текущие данные события не удалось прочитать." if ru else " Current event details could not be read.")


def _describe_removal(tool_call, state, runtime) -> str:
    a = RemoveFromAiCalendarArgs.model_validate(_calendar_business_args(tool_call["args"]))
    ru = _russian(state)
    event, unavailable = _calendar_event_for_approval(runtime, a.calendar_event_id, ru)
    what = f"#{a.calendar_event_id}"
    if event is not None:
        start = event.starts_at.astimezone(settings.tz)
        when = _calendar_when(start, event.ends_at.astimezone(settings.tz) if event.ends_at else None, ru)
        what = f"«{event.title}» ({when.rsplit(', ', 1)[0] if event.all_day else when})"
    return (f"Убрать из вашего AI-календаря: {what}." if ru else f"Remove from your AI Calendar: {what}.") + unavailable


def _describe_calendar(tool_call, state, runtime) -> str:
    updating = tool_call["name"] == "update_ai_calendar"
    schema = UpdateAiCalendarArgs if updating else AddToAiCalendarArgs
    a, ru = schema.model_validate(_calendar_business_args(tool_call["args"])), _russian(state)
    values = a.event_values()
    when = _calendar_when(values["starts_at"], values["ends_at"], ru)
    if a.all_day:
        when = when.rsplit(", ", 1)[0] + (", весь день" if ru else ", all day")
    elif a.end_time is None:
        when += " (без времени окончания)" if ru else " (no end time)"
    place = a.room or ("место не задано" if ru else "no place specified")
    details = f"«{a.title}» — {when}; {place}"
    if not isinstance(a, UpdateAiCalendarArgs):
        return f"Добавить в ваш AI-календарь: {details}." if ru else f"Add to your AI Calendar: {details}."
    old, unavailable = _calendar_event_for_approval(runtime, a.calendar_event_id, ru)
    previous = f"«{old.title}» (#{a.calendar_event_id})" if old else f"#{a.calendar_event_id}"
    return (f"Изменить событие {previous} в вашем AI-календаре на: {details}."
            if ru else f"Update event {previous} in your AI Calendar to: {details}.") + unavailable


def _valid(request) -> bool:
    schema = {"add_to_ai_calendar": AddToAiCalendarArgs, "update_ai_calendar": UpdateAiCalendarArgs,
              "remove_from_ai_calendar": RemoveFromAiCalendarArgs}[request.tool_call["name"]]
    try:
        schema.model_validate(_calendar_business_args(request.tool_call["args"]))
    except ValidationError:
        return False
    key, _ = _mutation_key(request.runtime)
    return key is not None


LOCAL_CALENDAR_APPROVAL = {
    name: {"allowed_decisions": ["approve", "reject"], "description": describe, "when": _valid}
    for name, describe in (("add_to_ai_calendar", _describe_calendar), ("update_ai_calendar", _describe_calendar),
                           ("remove_from_ai_calendar", _describe_removal))
}
