"""Turn the dates a chat message states loosely into concrete ones.

"Завтра будет тест" is only useful with the day it was sent; a model reading it a week later has to add that day
and then decide whether the result is in the past or the future, and small models get this wrong. This does the
arithmetic in code: for every relative or year-less date in a message it returns the exact date, the weekday and
how far it is from today.
"""

import re
from datetime import date, datetime, time, timedelta
from typing import Annotated

from pydantic import BeforeValidator, WithJsonSchema

MAX_RESULTS = 6
YEAR_ROLLOVER_DAYS = 180  # "15 января" in a message sent in December means the next year.
UNDATED_COMING_DAYS = 14  # A message that names no day counts for what is coming this long after it was written (`coming`).
ANNOUNCED_AHEAD_DAYS = 60  # How long before an event its announcement may be written (a hackathon of 13 November on 24 September).

# A time of day in a model's structured output, written HH:MM. Not plain `time`: its JSON schema (format "time") lets
# the guided decoding go on with fractional seconds, and the model did: "18:00:00.0000…" up to the token limit.
def _clock_time(value):
    if isinstance(value, str) and re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", value):
        return time.fromisoformat(value)
    if isinstance(value, time) and value.second == 0 and value.microsecond == 0 and value.tzinfo is None:
        return value
    raise ValueError("Time must use HH:MM format.")


ClockTime = Annotated[
    time,
    BeforeValidator(_clock_time),
    WithJsonSchema({"type": "string", "pattern": "^([01][0-9]|2[0-3]):[0-5][0-9]$"}),
]

_MONTHS = {
    # Russian genitive ("23 октября") and English names/abbreviations.
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6, "июля": 7, "августа": 8,
    "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10,
    "nov": 11, "dec": 12,
}  # fmt: skip
_WEEKDAYS = {
    "понедельник": 0, "вторник": 1, "среду": 2, "четверг": 3, "пятницу": 4, "субботу": 5, "воскресенье": 6,
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
}  # fmt: skip
_RELATIVE = {
    "позавчера": -2, "вчера": -1, "сегодня": 0, "завтра": 1, "послезавтра": 2,
    "после завтра": 2, "day after tomorrow": 2, "the day after tomorrow": 2,
    "yesterday": -1, "today": 0, "tomorrow": 1,
    # The evening of the day written: "room 108 tonight between 18:30-19:10" was told as "в ночь с 23 на 24 октября".
    "tonight": 0, "this evening": 0, "this morning": 0,
}  # fmt: skip

_MONTH_NAMES = "|".join(sorted(_MONTHS, key=len, reverse=True))
_WEEKDAY_NAMES = "|".join(_WEEKDAYS)
# Prefer full phrases and consume their nested words once; normalize whitespace only for lookup.
_RELATIVE_NAMES = "|".join(r"\s+".join(map(re.escape, phrase.split())) for phrase in sorted(_RELATIVE, key=len, reverse=True))
_RELATIVE_RE = re.compile(rf"(?<![\w])({_RELATIVE_NAMES})(?![\w])", re.I)
_WEEKDAY_RE = re.compile(
    rf"(?<![\w])(?:(?:в|во)\s+(?:(следующий|следующую|следующее)\s+)?|(on|next|this)\s+)({_WEEKDAY_NAMES})(?![\w])", re.I
)
_DAY_MONTH_RE = re.compile(rf"(?<![\w.])(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({_MONTH_NAMES})(?![\w])(?:\s+(\d{{4}}))?", re.I)
_MONTH_DAY_RE = re.compile(rf"(?<![\w])({_MONTH_NAMES})\s+(\d{{1,2}})(?:st|nd|rd|th)?(?![\w:])", re.I)
_NUMBERS = {"одну": 1, "один": 1, "два": 2, "две": 2, "три": 3, "четыре": 4, "пять": 5, "a": 1, "one": 1, "two": 2, "three": 3}
_SPAN_RE = re.compile(
    r"(?<![\w])(?:через|in)\s+(\d+|одну|один|два|две|три|четыре|пять|a|one|two|three)\s+"
    r"(дн(?:я|ей|и)?|день|недел\w+|days?|weeks?)(?![\w])",
    re.I,
)
_NUMERIC_RE = re.compile(r"(?<![\w.:])(\d{1,2})\.(\d{1,2})(?:\.(\d{4}|\d{2}))?(?![\w:])")


def _day(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _with_year(sent: date, month: int, day: int, year: int | None) -> date | None:
    """A date without a year: the year of the message, or the next one if that lands far in the past."""
    if year is not None:
        return _day(year + 2000 if year < 100 else year, month, day)
    found = _day(sent.year, month, day)
    if found and (sent - found).days > YEAR_ROLLOVER_DAYS:
        found = _day(sent.year + 1, month, day)
    return found


def _relation(target: date, today: date) -> str:
    days = (target - today).days
    if days == 0:
        return "today"
    if days == 1:
        return "tomorrow"
    if days == -1:
        return "yesterday"
    return f"in {days} days" if days > 0 else f"{-days} days ago"


def resolve(text: str, sent_at: datetime, now: datetime) -> list[str]:
    """Concrete dates for the loose dates in a message, e.g. "'Завтра' = 2026-10-05 Mon (10 days ago)"."""
    today = now.date()
    result, seen = [], set()
    for phrase, target in found_dates(text, sent_at, now):
        key = (phrase.lower(), target)
        if key in seen:
            continue
        seen.add(key)
        result.append(f"'{phrase.strip()}' = {target:%Y-%m-%d %a} ({_relation(target, today)})")
    return result[:MAX_RESULTS]


def mentions_between(text: str, sent_at: datetime, now: datetime, start: date, end: date) -> bool:
    """Does the message speak of a day in start..end (both included)? "23 October" in a post of 5 October does."""
    return any(start <= target <= end for _, target in found_dates(text, sent_at, now))


# "на этой неделе", "события недели", "на следующей неделе", "this week": a whole week, the message's own or the next. Only
# for `coming`: as a day it would put "на этой неделе перенос пары" on one day for the schedule-change detection.
_THIS_WEEK_RE = re.compile(
    r"(?<![\w])(?:(?:этой|эту|эта|текущей)\s+недел[еияю]|(?:событи[йя]|мероприяти[йя])\s+недели|this\s+week)(?![\w])", re.I
)
# "13–16 ноября", "с 13 по 16 ноября": the days between count too (`first_day_in` only, as the weeks).
_RANGE_RE = re.compile(rf"(?<![\w.])(?:с\s+)?(\d{{1,2}})\s*(?:[–—-]|по)\s*(\d{{1,2}})\s+({_MONTH_NAMES})(?![\w])", re.I)
_NEXT_WEEK_RE = re.compile(r"(?<![\w])(?:(?:следующей|следующую|будущей)\s+недел[еияю]|next\s+week)(?![\w])", re.I)


_LAST_WEEK_RE = re.compile(r"(?<![\w])(?:(?:прошлой|прошлую|прошедшей|предыдущей)\s+недел[еияю]|(?:last|previous|past)\s+week)(?![\w])", re.I)
_WEEKEND_RE = re.compile(
    r"(?<![\w])(?:(?:на|в)\s+(?:(прошлых|прошлые)|(следующих|следующие)|эт(?:их|и)\s+)?\s*выходн\w*|(?:(last)|(next)|this)?\s*weekend)(?![\w])", re.I
)
_MONTH_AROUND_RE = re.compile(r"(?<![\w])(?:(?:в\s+)?(этом|прошлом|следующем)\s+месяце|(this|last|next)\s+month)(?![\w])", re.I)
# A question about what was: its "в понедельник" is the last Monday, its "15 января" of this year, not of the next one.
_PAST_RE = re.compile(
    r"(?<![\w])(?:был[аио]?|прошл\w*|прошедш\w*|прош[её]л|писали|написали|состоял\w*|was|were|did|happened|last)(?![\w])", re.I
)
_MONTH_AROUND = {"этом": 0, "this": 0, "прошлом": -1, "last": -1, "следующем": 1, "next": 1}


def question_dates(text: str, now: datetime) -> list[str]:
    """The days, weeks and months a question names, worked out from now: "'на прошлой неделе' = 2026-10-26 Mon to
    2026-11-01 Sun". The model gave "с 2 по 6 ноября" for last week on Friday 6 November, and passed it to the helpers."""
    today = now.date()
    monday = today - timedelta(days=today.weekday())
    past = bool(_PAST_RE.search(text))
    lines: list[str] = []

    def span(phrase: str, first: date, last: date) -> None:
        lines.append(f"'{phrase.strip()}' = {first:%Y-%m-%d %a} to {last:%Y-%m-%d %a}")

    for pattern, ahead in ((_LAST_WEEK_RE, -7), (_THIS_WEEK_RE, 0), (_NEXT_WEEK_RE, 7)):
        if match := pattern.search(text):
            span(match.group(0), monday + timedelta(days=ahead), monday + timedelta(days=ahead + 6))
    if match := _WEEKEND_RE.search(text):
        last_one = match.group(1) or match.group(3) or (past and today.weekday() < 5)
        ahead = -7 if last_one else 7 if match.group(2) or match.group(4) else 0
        span(match.group(0), monday + timedelta(days=ahead + 5), monday + timedelta(days=ahead + 6))
    if match := _MONTH_AROUND_RE.search(text):
        index = today.year * 12 + today.month - 1 + _MONTH_AROUND[(match.group(1) or match.group(2)).lower()]
        first = date(index // 12, index % 12 + 1, 1)
        span(match.group(0), first, date(first.year + first.month // 12, first.month % 12 + 1, 1) - timedelta(days=1))
    for phrase, target in found_dates(text, now, now):
        if past and target > today and not _RELATIVE_RE.fullmatch(phrase.strip()) and not _SPAN_RE.search(phrase):
            if _WEEKDAY_RE.fullmatch(phrase.strip()):
                if not re.search(r"следующ|next", phrase, re.I):
                    target -= timedelta(days=7)  # "что было в понедельник": the last one
            elif not re.search(r"\d{4}", phrase):
                target = _day(target.year - 1, target.month, target.day) or target  # "что было 15 января": this January
        lines.append(f"'{phrase.strip()}' = {target:%Y-%m-%d %a} ({_relation(target, today)})")
    return list(dict.fromkeys(lines))[:MAX_RESULTS]


def first_day_in(text: str, sent_at: datetime, now: datetime, start: date, end: date) -> date | None:
    """The earliest day from `start` to `end` the message speaks of (a day, or a week: "на следующей неделе"), or None."""
    sent = sent_at.astimezone(now.tzinfo).date()
    spans = [(target, target) for _, target in found_dates(text, sent_at, now)]
    monday = sent - timedelta(days=sent.weekday())
    for pattern, ahead in ((_THIS_WEEK_RE, 0), (_NEXT_WEEK_RE, 7)):
        if pattern.search(text):
            spans.append((monday + timedelta(days=ahead), monday + timedelta(days=ahead + 6)))
    for match in _RANGE_RE.finditer(text):
        month = _MONTHS[match.group(3).lower()]
        first, last = _with_year(sent, month, int(match.group(1)), None), _with_year(sent, month, int(match.group(2)), None)
        if first and last and first <= last:
            spans.append((first, last))
    return min((max(first, start) for first, last in spans if first <= end and last >= start), default=None)


def names_a_day(text: str, sent_at: datetime, now: datetime) -> bool:
    """Does the message speak of any day or week at all?"""
    return first_day_in(text, sent_at, now, date.min, date.max) is not None


def coming(text: str, sent_at: datetime, now: datetime, start: date | None = None, end: date | None = None) -> bool:
    """Is the message about something still to come, for a question about what is coming? It speaks of a day (or a week)
    from `start`, today at the earliest, to `end`. One that names no day counts only for a period that starts today and
    only for UNDATED_COMING_DAYS after it was written: "registration is open" of June is not of something coming in
    November, and a weekly digest without days is of its own week."""
    today = now.date()
    start = max(start or today, today)
    if names_a_day(text, sent_at, now):
        return first_day_in(text, sent_at, now, start, end or date.max) is not None
    return start == today and (today - sent_at.astimezone(now.tzinfo).date()).days <= UNDATED_COMING_DAYS


def found_dates(text: str, sent_at: datetime, now: datetime) -> list[tuple[str, date]]:
    """The loose dates of a message as (phrase, day), relative to the day it was sent."""
    sent = sent_at.astimezone(now.tzinfo).date()
    found: list[tuple[str, date]] = []

    for match in _DAY_MONTH_RE.finditer(text):
        month = _MONTHS[match.group(2).lower()]
        if target := _with_year(sent, month, int(match.group(1)), int(match.group(3)) if match.group(3) else None):
            found.append((match.group(0), target))
    for match in _MONTH_DAY_RE.finditer(text):
        if target := _with_year(sent, _MONTHS[match.group(1).lower()], int(match.group(2)), None):
            found.append((match.group(0), target))
    for match in _NUMERIC_RE.finditer(text):
        day, month = int(match.group(1)), int(match.group(2))
        # "2.5" is a decimal, "03.10" or "5.10" a date: without a year the month must have two digits.
        if (match.group(3) or len(match.group(2)) == 2) and 1 <= month <= 12 and (target := _with_year(sent, month, day, int(match.group(3)) if match.group(3) else None)):
            found.append((match.group(0), target))
    for match in _RELATIVE_RE.finditer(text):
        phrase = " ".join(match.group(1).lower().split())
        found.append((match.group(0), sent + timedelta(days=_RELATIVE[phrase])))

    for match in _SPAN_RE.finditer(text):
        count = int(match.group(1)) if match.group(1).isdigit() else _NUMBERS[match.group(1).lower()]
        unit = match.group(2).lower()
        found.append((match.group(0), sent + timedelta(days=count * (7 if unit.startswith(("недел", "week")) else 1))))
    # "через неделю" has no number: the pattern above needs one, so "неделю" alone is handled here.
    for match in re.finditer(r"(?<![\w])через\s+неделю(?![\w])", text, re.I):
        found.append((match.group(0), sent + timedelta(days=7)))

    explicit_weekdays = {target.weekday() for _, target in found}
    for match in _WEEKDAY_RE.finditer(text):
        weekday = _WEEKDAYS[match.group(3).lower()]
        if weekday in explicit_weekdays:
            continue  # "в пятницу, 18.09": the written date is more reliable than a guess from the weekday.
        qualifier = (match.group(1) or match.group(2) or "").lower()
        ahead = (weekday - sent.weekday()) % 7
        if qualifier in ("this",):
            pass
        elif qualifier in ("next", "следующий", "следующую", "следующее"):
            ahead = (7 - sent.weekday()) + weekday  # The same weekday of the following week.
        elif ahead == 0:
            ahead = 7
        found.append((match.group(0), sent + timedelta(days=ahead)))

    return found
