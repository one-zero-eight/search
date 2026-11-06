"""The asker's AI Calendar (personal_calendar.py): the events they added with "➕ В мой календарь" under the assistant's
answers, in the Telegram bot and on the site. cAtIx keeps it under their InNoHassle account, so it is read without their
InNoHassle token: on the site by their account (AgentContext.innohassle_id), in the Telegram bot by the account linked to
their Telegram. An event is added only by its button under an answer (agent/events.py offers it): the button is the
asker's own decision, in the bot as on the site. Removing one waits for the asker's approval like the account helper's
other actions (account_tools.APPROVAL), so it is the account helper's, on the site; in the bot /calendar has a button
for each event.
"""

from datetime import date, datetime, time, timedelta

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from catix import personal_calendar
from catix.settings import settings

DEFAULT_DAYS = 14
NO_CALENDAR = (
    "The asker's AI Calendar is kept under their InNoHassle account, and this chat does not know it: it is in the Telegram "
    "bot (/calendar) and on the site innohassle.ru/calendar."
)
NOT_LINKED = (
    "The asker's Telegram is not linked to an InNoHassle account, where the AI Calendar is kept: they can link it at "
    f"{personal_calendar.CONNECT_TELEGRAM}."
)
UNAVAILABLE = "InNoHassle does not answer now, and the AI Calendar is kept under the asker's InNoHassle account: try later."


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


def calendar_item(event: personal_calendar.PersonalEvent) -> dict:
    """An event of the AI Calendar as the model sees it, with the id remove_from_ai_calendar takes."""
    start = event.starts_at.astimezone(settings.tz)
    item: dict = {"calendar_event_id": event.id, "date": start.strftime("%Y-%m-%d %a"), "title": event.title}
    if not event.all_day:
        end = event.ends_at.astimezone(settings.tz) if event.ends_at else None
        item["time"] = f"{start:%H:%M}" + (f"-{end:%H:%M}" if end else "")
    if event.room:
        item["place"] = event.room
    if event.source_url:
        item["source"] = event.source_url
    return item


def events_between(key: str, start: date, end: date) -> list[dict]:
    """The AI Calendar's events from `start` to `end` inclusive."""
    first = datetime.combine(start, time.min, settings.tz)
    found = personal_calendar.between(key, first, datetime.combine(end + timedelta(days=1), time.min, settings.tz))
    return [calendar_item(e) for e in found]


class GetAiCalendarArgs(BaseModel):
    date_from: date | None = Field(None, description="YYYY-MM-DD, default today.")
    date_to: date | None = Field(None, description=f"YYYY-MM-DD inclusive, default date_from + {DEFAULT_DAYS - 1} days.")


@tool(args_schema=GetAiCalendarArgs)
def get_my_ai_calendar(runtime: ToolRuntime, date_from: date | None = None, date_to: date | None = None) -> dict:
    """The asker's AI Calendar for a period: the events they added themselves with the "➕ В мой календарь" button under the
    assistant's answers (in the Telegram bot and on the site), with the source message of each. Not their classes: those
    are in the timetable."""
    key, why = calendar_key(runtime)
    if key is None:
        return {"error": why}
    start = date_from or datetime.now(settings.tz).date()
    end = date_to or start + timedelta(days=DEFAULT_DAYS - 1)
    events = events_between(key, start, end)
    result: dict = {"range": [start.isoformat(), end.isoformat()], "events": events}
    if not events:
        result["note"] = "No event of the AI Calendar in this period. An event gets there by its button under an answer."
    return result


class RemoveFromAiCalendarArgs(BaseModel):
    calendar_event_id: int = Field(gt=0, description="The `calendar_event_id` from get_my_ai_calendar or get_my_schedule.")


@tool(args_schema=RemoveFromAiCalendarArgs)
def remove_from_ai_calendar(calendar_event_id: int, runtime: ToolRuntime) -> dict:
    """Remove one event from the asker's AI Calendar. The asker approves or declines it before it is done: call it as soon as
    they asked; never ask them yourself."""
    key, why = calendar_key(runtime)
    if key is None:
        return {"done": False, "error": why}
    if not personal_calendar.delete_event(key, calendar_event_id):
        return {"done": False, "error": "No such event in the asker's AI Calendar: take its `calendar_event_id` from get_my_ai_calendar."}
    return {"done": True, "removed": calendar_event_id, "note": "Removed: tell the asker."}


CALENDAR_TOOLS = [get_my_ai_calendar, remove_from_ai_calendar]

