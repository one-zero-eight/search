"""Events an answer names, for the "➕ В мой календарь" buttons under it.

The agent itself does not offer them (the model ignored a tool for it), so after the answer is sent one more short call
reads the answer text and lists the upcoming events it states with a date: an exam, a deadline, a lecture. The same kind
of structured call as the schedule-change detection in worker/changes.py. Only when the answer looks like it has a date.
"""

import re
from datetime import date, datetime, time

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from catix.agent import tracing
from catix.settings import settings

MAX_EVENTS = 3

# Cheap gate: a month name, a numeric date or "today/tomorrow". Most answers have none and cost no extra call.
_LOOKS_DATED = re.compile(
    r"\d{1,2}\s*(?:янв|фев|мар|апр|ма[йя]|июн|июл|авг|сен|окт|ноя|дек)|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s*\d{1,2}"
    r"|\d{1,2}\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)|\b\d{1,2}[./]\d{1,2}\b(?!\d)|сегодня|завтра|послезавтра|today|tomorrow",
    re.I,
)

PROMPT = """\
Below is an answer a university assistant gave to a student. List the UPCOMING events it states with a date: an exam, \
midterm, test, deadline, lecture, meeting, contest. Rules:
- Only events that are in the future relative to now and whose day the answer states (or says "today"/"tomorrow").
- Never invent or guess a day or a time. A time only if the answer gives it. Skip events already over, vague \
recurrences and anything without a day.
- title: short, in the language of the answer: the subject and what happens ("Midterm: Mathematical Analysis").
- day: YYYY-MM-DD. start_time / end_time: HH:MM local time or null. room: as written or null.
- source: the number n of the marker [n] next to the fact in the answer (the source list is below it), or null.
- At most {limit} events; an empty list if there is none.

Now: {now} ({weekday}).
Answer:
{answer}
"""


class Event(BaseModel):
    title: str
    day: date
    start_time: time | None = None
    end_time: time | None = None
    room: str | None = None
    source: int | None = None


class Events(BaseModel):
    events: list[Event] = Field(default_factory=list)


def _model():
    return ChatOpenAI(
        base_url=str(settings.llm_route),
        api_key="not-needed",
        model=settings.llm_model,
        max_tokens=500,
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
    body = re.split(r"\n+(?:Источники|Sources):", answer, maxsplit=1)[0]
    if not _LOOKS_DATED.search(body):  # The source list adds nothing to look at.
        return []
    text = answer
    now = datetime.now(settings.tz)
    prompt = PROMPT.format(limit=MAX_EVENTS, now=f"{now:%Y-%m-%d %H:%M}", weekday=f"{now:%A}", answer=text[:1500])
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
