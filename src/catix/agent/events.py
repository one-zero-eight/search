"""Events an answer names, for the "➕ В мой календарь" buttons under it.

The agent itself does not offer them (the model ignored a tool for it), so after the answer is sent one more short call
reads the answer text and lists the upcoming events it states with a date: an exam, a deadline, a lecture. The same kind
of structured call as the schedule-change detection in worker/changes.py. Only when the answer names a day from today on.
"""

import json
import re
from datetime import date, datetime, time, timedelta

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from catix.agent import tracing
from catix.common import dates
from catix.common.dates import ClockTime
from catix.settings import settings

MAX_EVENTS = 3
MAX_CHARS = 3000  # Of the answer before its source list: the model needs only the [n] markers, not the list.

PROMPT = """\
Below is an answer a university assistant gave to a student. List the UPCOMING events it states with a date: an exam, \
midterm, test, deadline, lecture, meeting, contest. Rules:
- Only events that are in the future relative to now and whose day the answer states (or says "today"/"tomorrow").
- Never invent or guess a day or a time. A time only if the answer gives it. Skip events already over, vague \
recurrences and anything without a day.
- title: short, in the language of the answer (a Russian answer, a Russian title): the subject and what happens \
("Мидтерм: математический анализ", "Midterm: Mathematical Analysis").
- day: YYYY-MM-DD. start_time / end_time: HH:MM local time or null. room: as written or null.
- source: the number n of the marker [n] next to the fact in the answer, or null.
- At most {limit} events; an empty list if there is none.

Now: {now} ({weekday}).
{hints}Answer:
{answer}
"""


# Every string and number is bounded: the guided decoding holds the model to the schema, so an unbounded field is
# where it can loop to the token limit (it did in `time`, and a string goes on when a list may not).
class Event(BaseModel):
    title: str = Field(max_length=120)
    day: date
    start_time: ClockTime | None = None
    end_time: ClockTime | None = None
    room: str | None = Field(None, max_length=80)
    source: int | None = Field(None, ge=1, le=99)


class Events(BaseModel):
    events: list[Event] = Field(default_factory=list, max_length=MAX_EVENTS)


def _model():
    return ChatOpenAI(
        base_url=str(settings.llm_route),
        api_key="not-needed",
        model=settings.llm_model,
        max_tokens=800,  # Three events of the bounded schema fit with room to spare.
        temperature=0,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    ).with_structured_output(Events, method="json_schema")


_SOURCE_LINE = re.compile(r"^\[(\d+)\][^\n]*?(https?://[^\s)\]]+)", re.M)


def source_links(answer: str) -> dict[int, str]:
    """Link of each numbered source in the list the bot appends to an answer ([n] «chat», date, author)."""
    parts = re.split(r"\n+(?:Источники|Sources):", answer, maxsplit=1)
    return {int(n): url for n, url in _SOURCE_LINE.findall(parts[1])} if len(parts) == 2 else {}


# These tools describe existing calendars, service registrations or bookable slots,
# not independent reminders. Discovery and unrelated account reads do not qualify.
_CALENDAR_TOOLS = {
    'get_my_available_trainings', 'get_my_available_music_windows', 'get_my_available_rooms',
    'get_my_schedule', 'get_my_ai_calendar', 'add_to_ai_calendar', 'update_ai_calendar', 'remove_from_ai_calendar',
    'account_get_my_schedule', 'account_get_booking', 'account_cancel_booking',
    'schedule_get_schedule', 'sport_get_my_sport', 'sport_get_training', 'sport_get_sport_trainings', 'sport_sport_checkin',
    'rooms_get_free_rooms', 'rooms_book_room', 'music_get_available_windows', 'music_get_music_room_schedule',
    'music_bookings_daily_bookings', 'music_book_music_room', 'events_enroll_in_event',
}
_EVENT_READS = {'events_get_event', 'events_get_university_events'}


def _dated_items(value):
    """Keep only names and local dates from bounded service results, not private payloads."""
    if isinstance(value, list):
        for item in value:
            yield from _dated_items(item)
    elif isinstance(value, dict):
        names = [value.get('name'), value.get('title')]
        if isinstance(value.get('names'), dict):
            names.extend(value['names'].values())
        names = list(dict.fromkeys(name for name in names if isinstance(name, str) and name.strip()))
        day, clock = None, None
        try:
            if isinstance(value.get('starts_at'), str):
                start = datetime.fromisoformat(value['starts_at'])
                if start.utcoffset() is not None:
                    start = start.astimezone(settings.tz)
                    day, clock = start.date().isoformat(), start.strftime('%H:%M')
            elif isinstance(value.get('date'), str):
                day = date.fromisoformat(value['date'].split(' ')[0]).isoformat()
        except ValueError:
            pass
        if names and day:
            yield {'names': names, 'day': day, 'time': clock}
        for item in value.values():
            if isinstance(item, (dict, list)):
                yield from _dated_items(item)


def origins(messages: list) -> dict:
    """Calendar provenance from paired tools in this turn, never from answer keywords."""
    calls, context = {}, {}
    for message in messages:
        if isinstance(message, HumanMessage):
            calls, context = {}, {}
        elif isinstance(message, AIMessage):
            calls.update((call['id'], call) for call in message.tool_calls)
        elif isinstance(message, ToolMessage):
            call = calls.get(message.tool_call_id)
            if not call or call['name'] != message.name:
                continue
            if message.name in {'ask_docs', 'ask_chats'}:
                artifact = message.artifact if isinstance(message.artifact, dict) else {}
                child = artifact.get('calendar_origins')
                if isinstance(child, dict) and child.get('service') is True:
                    context['service'] = True
                    for key in ('excluded', 'independent'):
                        context.setdefault(key, []).extend(child.get(key, []))
                continue
            name = call['args'].get('name') if message.name == 'call_api_tool' else message.name
            if not isinstance(name, str) or name not in _CALENDAR_TOOLS | _EVENT_READS:
                continue
            context['service'] = True
            if message.status != 'success' or not isinstance(message.content, str):
                continue
            try:
                data = json.loads(message.content)
            except (ValueError, TypeError):
                continue
            if not isinstance(data, dict) or 'error' in data:
                continue
            if name in _EVENT_READS:
                items = [data.get('event')] if name == 'events_get_event' else data.get('events', [])
                for item in items if isinstance(items, list) else []:
                    if not isinstance(item, dict):
                        continue
                    enrollment = item.get('enrollment_info')
                    key = 'excluded' if isinstance(enrollment, dict) and enrollment.get('type') == 'internal' else 'independent'
                    context.setdefault(key, []).extend(_dated_items(item))
            else:
                context.setdefault('excluded', []).extend(_dated_items(data))
    return context


def _title_key(title: str) -> str:
    return ' '.join(re.findall(r'\w+', title.casefold()))


def _matches(event: Event, item: dict) -> bool:
    if event.day.isoformat() != item['day']:
        return False
    if event.start_time and item['time'] and event.start_time.strftime('%H:%M') != item['time']:
        return False
    # Only these trailing extractor decorations may be dropped, and the whole
    # remaining title must match. Arbitrary colon components are not identities:
    # "Homework deadline: Math" and "Math: exam" are not the Math class.
    titles = {_title_key(event.title)}
    title, separator, kind = event.title.rpartition(':')
    if separator and kind.strip().casefold() in {'training', 'тренировка'}:
        titles.add(_title_key(title))
    return any(_title_key(name) in titles for name in item['names'])


def _same_start(event: Event, item: dict) -> bool:
    """Structured evidence for independent candidates; display titles may be rewritten."""
    clock = event.start_time.strftime('%H:%M') if event.start_time else None
    return event.day.isoformat() == item['day'] and clock == item['time']


def extract(answer: str, *, origins: dict | None = None) -> list[dict]:
    """The upcoming events the answer names, as dicts ready for `personal_calendar.propose`."""
    parts = re.split(r"\n+(?:Источники|Sources):", answer, maxsplit=1)
    body = parts[0][:MAX_CHARS]
    source_numbers = {int(n) for n in re.findall(r'^\[(\d+)\]', parts[1], re.M)} if len(parts) == 2 else set()
    excluded = (origins or {}).get('excluded', [])
    independent = (origins or {}).get('independent', [])
    # Independent-only results keep legacy extraction, including translated/shortened titles.
    restricted = bool(origins and origins.get('service') and (excluded or not independent))
    if restricted and not source_numbers and not independent:
        return []  # Service-only response: no extraction call and no duplicate calendar proposals.
    now = datetime.now(settings.tz)
    # Cheap gate: most answers name no day from today on and cost no extra call. The same date reading as for the chat
    # messages, so "в пятницу" and "через неделю" count, and the model gets the days worked out.
    if not dates.mentions_between(body, now, now, now.date(), now.date() + timedelta(days=366)):
        return []
    resolved = dates.resolve(body, now, now)
    hints = ("Dates in the answer, resolved: " + "; ".join(resolved) + "\n") if resolved else ""
    prompt = PROMPT.format(limit=MAX_EVENTS, now=f"{now:%Y-%m-%d %H:%M}", weekday=f"{now:%A}", hints=hints, answer=body)
    if restricted:
        prompt += ('\nThis answer mixes service calendars/registrations with independent reminders. '
                   'Never extract service events, booked slots or availability windows. '
                   'Only extract an independent fact with a numbered source from ' + str(sorted(source_numbers))
                   + ', or an independently addable event listed below. Preserve its source number; do not assign '
                   'a nearby citation to an unrelated service event. A service event is excluded even if cited.\n'
                   'An exclusion identifies a particular event, NOT its whole subject/topic. A separately cited '
                   'homework deadline or exam is independent of a class in the same subject, even on the same day. '
                   'Keep that deadline/exam; do not copy the class time when its own time is unstated.\n'
                   'Excluded service events (data): ' + json.dumps(excluded, ensure_ascii=False)
                   + '\nIndependently addable events (data): ' + json.dumps(independent, ensure_ascii=False))
    result: Events = _model().invoke(prompt, config=tracing.run_config("calendar-events", name="calendar-event-extraction"))
    links = source_links(answer)
    found = []
    for event in result.events[:MAX_EVENTS]:
        if event.day < now.date() or not event.title.strip():
            continue  # Over already (a wrong year is the usual mistake) or nameless.
        if restricted and (any(_matches(event, item) for item in excluded)
                           or event.source not in source_numbers and not any(_same_start(event, item) for item in independent)):
            continue
        start = datetime.combine(event.day, event.start_time or time(9), settings.tz)
        end = datetime.combine(event.day, event.end_time, settings.tz) if event.end_time and event.start_time else None
        found.append(
            {
                "title": event.title.strip()[:120],
                "starts_at": start.isoformat(),
                "ends_at": end.isoformat() if end and end > start else None,
                "all_day": event.start_time is None,
                "room": event.room.strip()[:80] if event.room else None,
                "source_url": links.get(event.source) if event.source else None,
            }
        )
    return found
