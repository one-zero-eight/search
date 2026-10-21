"""Turn the dates a chat message states loosely into concrete ones.

"Завтра будет тест" is only useful with the day it was sent; a model reading it a week later has to add that day
and then decide whether the result is in the past or the future, and small models get this wrong. This does the
arithmetic in code: for every relative or year-less date in a message it returns the exact date, the weekday and
how far it is from today.
"""

import re
from datetime import date, datetime, timedelta

MAX_RESULTS = 6
YEAR_ROLLOVER_DAYS = 180  # "15 января" in a message sent in December means the next year.

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
    "yesterday": -1, "today": 0, "tomorrow": 1,
}  # fmt: skip

_MONTH_NAMES = "|".join(sorted(_MONTHS, key=len, reverse=True))
_WEEKDAY_NAMES = "|".join(_WEEKDAYS)
_RELATIVE_RE = re.compile(rf"(?<![\w])({'|'.join(_RELATIVE)})(?![\w])", re.I)
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
        found.append((match.group(0), sent + timedelta(days=_RELATIVE[match.group(1).lower()])))

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
