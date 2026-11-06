"""Events an answer names, for the "➕ В мой календарь" buttons under it.

The agent itself does not offer them (the model ignored a tool for it), so after the answer is sent one more short call
reads the answer text and lists the upcoming events it states with a date: an exam, a deadline, a lecture. The same kind
of structured call as the schedule-change detection in worker/changes.py. Only when the answer names a day from today on.
"""

import re
from datetime import date, datetime, time, timedelta

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


def extract(answer: str) -> list[dict]:
    """The upcoming events the answer names, as dicts ready for `personal_calendar.propose`."""
    body = re.split(r"\n+(?:Источники|Sources):", answer, maxsplit=1)[0][:MAX_CHARS]
    now = datetime.now(settings.tz)
    # Cheap gate: most answers name no day from today on and cost no extra call. The same date reading as for the chat
    # messages, so "в пятницу" and "через неделю" count, and the model gets the days worked out.
    if not dates.mentions_between(body, now, now, now.date(), now.date() + timedelta(days=366)):
        return []
    resolved = dates.resolve(body, now, now)
    hints = ("Dates in the answer, resolved: " + "; ".join(resolved) + "\n") if resolved else ""
    prompt = PROMPT.format(limit=MAX_EVENTS, now=f"{now:%Y-%m-%d %H:%M}", weekday=f"{now:%A}", hints=hints, answer=body)
    result: Events = _model().invoke(prompt, config=tracing.run_config("calendar-events", name="calendar-event-extraction"))
    links = source_links(answer)
    found = []
    for event in result.events[:MAX_EVENTS]:
        if event.day < now.date() or not event.title.strip():
            continue  # Over already (a wrong year is the usual mistake) or nameless.
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
