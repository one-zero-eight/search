"""Explicit MCP account integrations. Business rules execute here, not in the agent."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import TYPE_CHECKING, Annotated, Literal

if TYPE_CHECKING:
    from catix.innohassle import client as innohassle
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import date, datetime, time, timedelta

import httpx
import icalendar
import recurring_ical_events
from fastmcp.dependencies import Depends
from fastmcp.tools import tool
from pydantic import AfterValidator, Field

from catix.common.dates import ClockTime
from catix.innohassle.identifiers import validate_outlook_id, validate_room_id
from catix.innohassle.mcp_declarations import (
    invalid_arguments, metadata, optional_sport, require_innohassle, result_boundary,
)
from catix.settings import settings

MAX_ITEMS = 40
_timeout_log = logging.getLogger("catix.mcp.schedule_sources")


DEFAULT_DAYS = 7


def _now() -> datetime:
    return datetime.now(settings.tz)


def _at(day: date, clock: time) -> datetime:
    return datetime.combine(day, clock, settings.tz)


def _local(value: str) -> datetime:
    """A time a service gave: with an offset or without one (then local time)."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(settings.tz) if parsed.tzinfo else parsed.replace(tzinfo=settings.tz)


def _span(start: datetime, end: datetime) -> dict:
    return {"date": start.strftime("%Y-%m-%d %a"), "time": f"{start:%H:%M}-{end:%H:%M}",
            "starts_at": start.isoformat(), "ends_at": end.isoformat()}


def _why(e: innohassle.ServiceError, what: str) -> str:
    if e.status == 401:
        return "InNoHassle did not accept the asker's sign-in: ask them to sign in on the site again."
    return f"{what} refused: {e.detail}"


def _refused(e: innohassle.ServiceError, what: str) -> dict:
    """The result of an action a service refused: nothing was done."""
    return {"done": False, "error": _why(e, what)}


def _read_source(operation: str, read, *args):
    """Measure inside the worker, not after waiting for unrelated parallel feeds."""
    started = perf_counter()
    try:
        return read(*args)
    except httpx.TimeoutException as error:
        _timeout_log.warning("Schedule source timed out operation=%s exception=%s elapsed_ms=%.1f",
                             operation, type(error).__name__, (perf_counter() - started) * 1000)
        raise


def _calendar_items(text: str, kind: str, start: date, end: date) -> list[dict]:
    calendar = icalendar.Calendar.from_ical(text)
    now, seen, out = (_now(), set(), [])
    first, last = _at(start, time.min), _at(end + timedelta(days=1), time.min)
    originals = calendar.walk("VEVENT")
    recurring_uids = {str(ev.get("UID", "")) for ev in originals
                      if any(key in ev for key in ("RRULE", "RDATE", "EXRULE", "EXDATE", "RECURRENCE-ID"))}
    unknown = [ev for ev in originals if isinstance(ev.decoded("DTSTART", None), datetime)
               and "DTEND" not in ev and "DURATION" not in ev]
    if any(str(ev.get("UID", "")) in recurring_uids for ev in unknown):
        # A bounded expansion cannot prove that earlier occurrences ended;
        # raw masters are not occurrences (EXDATE, detached/RANGE exceptions).
        # Let the existing caller report this feed as incomplete instead.
        raise ValueError("Coverage of recurring timed events with unknown ends cannot be verified.")
    events = recurring_ical_events.of(calendar).between(first, last)
    # Expansion treats a missing timed end as zero duration. In our agenda it
    # remains unknown, so even an old start can overlap this query: no lookback
    # or midnight boundary can establish that the event has finished.
    for ev in unknown:
        begin = ev.decoded("DTSTART")
        if begin.utcoffset() is None:
            raise ValueError("Coverage of timed events with unknown ends and floating starts cannot be verified.")
        if begin < first:
            events.append(ev)
    for ev in events:
        begin = ev.decoded("DTSTART")
        title, place = (str(ev.get("SUMMARY", "")), str(ev.get("LOCATION", "")) or None)
        if (key := (str(begin), title, place, str(ev.get("UID", "")),
                    str(ev.decoded("DTEND", None)), str(ev.decoded("DURATION", None)))) in seen:
            continue
        seen.add(key)
        if not isinstance(begin, datetime):
            out.append(
                {
                    k: v
                    for k, v in {
                        "kind": kind,
                        "calendar_uid": str(ev.get("UID", "")),
                        "date": begin.strftime("%Y-%m-%d %a"),
                        "all_day": True,
                        "starts_at": _at(begin, time.min).isoformat(),
                        "ends_at": _at(ev.decoded("DTEND", begin + timedelta(days=1)), time.min).isoformat(),
                        "title": title,
                        "place": place,
                    }.items()
                    if v
                }
            )
            continue
        begin = begin.astimezone(settings.tz)
        finish = ev.decoded("DTEND").astimezone(settings.tz) if "DTEND" in ev else begin
        item = {
            "kind": kind,
            "calendar_uid": str(ev.get("UID", "")),
            "starts_at": begin.isoformat(),
            **(
                _span(begin, finish)
                if finish > begin
                else {"date": begin.strftime("%Y-%m-%d %a"), "time": f"{begin:%H:%M}"}
            ),
            "title": title,
            "place": place,
            "status": "finished" if finish <= now else "now" if begin <= now else "upcoming",
        }
        out.append({k: v for k, v in item.items() if v})
    return out


def _class_calendar(token: str, start: date, end: date) -> tuple[list[dict], list[str], dict[str, str]]:
    """Mirror the site's visible calendars and source-aware English exclusion.

    Website CalendarPage/getCalendarsToShow and iCalendarPlugin/isEnglishEvent,
    revision 34dc0d59972778eb99de6b0f4b0c10f67599fdb5. Never fall back to all.ics.
    """
    from catix.innohassle import client as innohassle

    user_id, aliases = innohassle.my_calendar_groups(token)
    if not aliases:
        return [], [], {}
    catalogue = innohassle.event_groups(fresh=True)
    if not isinstance(catalogue, list) or any(not isinstance(g, dict) or not isinstance(g.get("alias"), str) for g in catalogue):
        raise ValueError("Unreadable calendar catalogue.")
    groups = {group["alias"]: group for group in catalogue}
    has_english = any(alias.startswith("english-") for alias in aliases)
    items, problems, seen = [], [], set()
    errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=min(8, len(aliases))) as pool:
        asked = {alias: pool.submit(_read_source, "class_calendar_feed", innohassle.my_group_calendar_ics, token, user_id, alias)
                 for alias in aliases if alias in groups}
    for alias in aliases:
        if alias not in groups:
            problems.append(f"{alias}: selected calendar is not in the catalogue")
            continue
        try:
            tags = groups[alias].get("tags")
            if tags is None:
                tags = []
            if not isinstance(tags, list) or any(not isinstance(tag, dict) for tag in tags):
                raise ValueError("Unreadable calendar tags.")
            exclude_english = has_english and any(tag.get("type") == "core-courses" for tag in tags)
            for item in _calendar_items(asked[alias].result(), "class", start, end):
                title = item.get("title", "")
                if exclude_english and any(word in title.strip().lower()
                                           for word in ("english", "foreign language", "иностранный язык")):
                    continue
                key = (item["date"], item.get("time"), title, item.get("place"))
                if key not in seen:
                    seen.add(key)
                    items.append({**item, "calendar": alias})
        except innohassle.ServiceError as error:
            if error.status == 401:
                raise
            problems.append(f"{alias}: {error.status}: {error.detail}")
        except httpx.TimeoutException as error:
            errors["class"] = "upstream_timeout"
            problems.append(f"{alias}: InNoHassle did not answer ({type(error).__name__})")
        except httpx.HTTPError as error:
            problems.append(f"{alias}: InNoHassle did not answer ({type(error).__name__})")
        except ValueError as error:
            problems.append(f"{alias}: unreadable calendar: {error}"[:200])
    return items, problems, errors


def _sport_calendar(token: str, start: date, end: date) -> list[dict]:
    """Normalize checked-in Sport rows through the shared calendar overlap reader.

    Sport all-day end dates are inclusive in its ICS export. No credential or
    upstream payload is embedded in the generated, trusted calendar.
    """
    from catix.innohassle import sport
    from catix.innohassle.mcp_sport import training_name

    rows = sport.my_trainings(token, _at(start, time.min), _at(end + timedelta(days=1), time.min))
    if not isinstance(rows, list):
        raise ValueError("Unreadable Sport schedule.")
    calendar = icalendar.Calendar()
    for row in rows:
        if not isinstance(row, dict) or type(row.get("checked_in")) is not bool:
            raise ValueError("Unreadable Sport check-in status.")
        if not row["checked_in"]:
            continue
        training = row.get("training")
        if (not isinstance(training, dict) or type(training.get("id")) is not int or training["id"] <= 0
                or type(training.get("is_all_day")) is not bool):
            raise ValueError("Unreadable Sport training.")
        names = [training.get(key) for key in ("training_custom_name", "sport_name", "display_name", "group_name")]
        if (any(name is not None and not isinstance(name, str) for name in names)
                or not any(isinstance(name, str) and name.strip() for name in names)):
            raise ValueError("Unreadable Sport training name.")
        bounds = []
        for key in ("start", "end"):
            value = training.get(key)
            if not isinstance(value, str):
                raise ValueError("Unreadable Sport training date.")
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if stamp.utcoffset() is None:
                raise ValueError("Unreadable Sport training timezone.")
            bounds.append(stamp.astimezone(settings.tz))
        begin, finish = bounds
        if training["is_all_day"]:
            begin, finish = begin.date(), finish.date()
            if finish < begin:
                raise ValueError("Unreadable Sport training interval.")
            finish += timedelta(days=1)
        elif finish <= begin:
            raise ValueError("Unreadable Sport training interval.")
        location = training.get("training_location")
        if location is not None and (not isinstance(location, dict)
                or not isinstance(location.get("name"), str) or not location["name"].strip()):
            raise ValueError("Unreadable Sport training location.")
        event = icalendar.Event()
        event.add("uid", str(training["id"]))
        event.add("summary", training_name(training))
        event.add("dtstart", begin)
        event.add("dtend", finish)
        if location:
            event.add("location", location["name"])
        calendar.add_component(event)
    return _calendar_items(calendar.to_ical(), "sport", start, end)


def _calendar(token: str, start: date, end: date, sport_token: str | None = None) -> tuple[list[dict], dict[str, str], dict[str, str]]:
    """The asker's InNoHassle calendars in the period (classes, sport, the events they enrolled in), each
    item with its `kind`; and what could not be read, by kind. Read concurrently rather than waiting on each service in turn.
    Raises ServiceError 401 when InNoHassle does not accept the token."""
    from catix.innohassle import client as innohassle

    with ThreadPoolExecutor(max_workers=len(innohassle.MY_CALENDARS) + 1) as pool:
        asked: dict[str, Future] = {"class": pool.submit(_read_source, "class_calendar", _class_calendar, token, start, end)}
        asked.update({kind: pool.submit(_read_source, f"{kind}_calendar", innohassle.my_calendar_ics, token, kind)
                      for kind in innohassle.MY_CALENDARS if kind != "sport" or not sport_token})
        if sport_token:
            asked["sport"] = pool.submit(_read_source, "sport_calendar", _sport_calendar, sport_token, start, end)
    items, problems, errors = ([], {}, {})
    for kind, future in asked.items():
        try:
            if kind == "class":
                classes, missing, class_errors = future.result()
                items += classes
                errors.update(class_errors)
                if missing:
                    problems[kind] = "; ".join(missing)
            elif kind == "sport" and sport_token:
                items += future.result()
            else:
                items += _calendar_items(future.result(), kind, start, end)
        except innohassle.ServiceError as e:
            if e.status == 401 and not (kind == "sport" and sport_token):
                raise
            problems[kind] = f"{e.status}: {e.detail}"
        except httpx.TimeoutException as e:
            errors[kind] = "upstream_timeout"
            problems[kind] = f"InNoHassle did not answer ({type(e).__name__})"
        except httpx.HTTPError as e:
            problems[kind] = f"InNoHassle did not answer ({type(e).__name__})"
        except ValueError as e:
            problems[kind] = f"unreadable calendar: {e}"[:200]
    return (sorted(items, key=lambda i: (i["date"], i.get("time", ""))), problems, errors)


def _bookings(token: str, start: date, end: date) -> tuple[list[dict], list[str], dict[str, str]]:
    """The asker's bookings of the music room and of rooms in the period, with the ids cancel_booking takes; and what could
    not be read."""
    from catix.innohassle import client as innohassle

    out, problems, errors = ([], [], {})
    first, last = (_at(start, time.min), _at(end + timedelta(days=1), time.min))
    try:
        for b in _read_source("music_room_bookings", innohassle.my_music_room_bookings, token):
            begin, finish = (_local(b["time_start"]), _local(b["time_end"]))
            if begin < last and first < finish:
                out.append(
                    {"service": "music_room", "booking_id": str(b["id"]), **_span(begin, finish), "title": "Music room"}
                )
    except httpx.TimeoutException as e:
        errors["music_room"] = "upstream_timeout"
        problems.append(f"music room: InNoHassle did not answer ({type(e).__name__})")
    except innohassle.ServiceError as e:
        problems.append(f"music room: {e.detail}")
    try:
        for b in _read_source("room_bookings", innohassle.my_room_bookings, token, first, last):
            begin, finish = (_local(b["start"]), _local(b["end"]))
            out.append(
                {
                    "service": "room",
                    "booking_id": b.get("outlook_booking_id"),
                    **_span(begin, finish),
                    "room": b.get("room_id"),
                    "title": b.get("title"),
                }
            )
    except httpx.TimeoutException as e:
        errors["rooms"] = "upstream_timeout"
        problems.append(f"rooms: InNoHassle did not answer ({type(e).__name__})")
    except innohassle.ServiceError as e:
        problems.append(f"rooms: {e.detail}")
    return (sorted(out, key=lambda b: (b["date"], b["time"])), problems, errors)


def _future_span(day: date, time_from: time, time_to: time) -> str | None:
    if _at(day, time_to) <= _at(day, time_from):
        return "time_to must be after time_from."
    if _at(day, time_from) <= _now():
        return "That time is already past: ask the asker for a time to come."
    return None


@tool(**metadata())
@result_boundary()
def account_get_my_schedule(
    date_from: date | None = None, date_to: date | None = None,
    *, token: str = Depends(require_innohassle), sport_token: str | None = Depends(optional_sport),
) -> dict:
    """The signed-in user's CURRENT PERSONAL schedule: selected/subscribed class calendars,
    including English and course selections, sport, event enrolments, and personal room/music bookings.
    Моё расписание, мой календарь: выбранный английский, курсы, спорт и мои бронирования.

    Uses the user's authenticated calendar feeds, not the public academic-group timetable, which
    can contain other English streams. No group argument is needed. Excludes the local AI Calendar:
    cAtIx hosts use get_my_schedule to combine this external source with their local AI Calendar.
    Report not_read and truncation; never substitute public group events for a failed personal feed.
    """
    from catix.innohassle import client as innohassle

    start = date_from or _now().date()
    end = date_to or start + timedelta(days=DEFAULT_DAYS - 1)
    result: dict = {"now": _now().strftime("%Y-%m-%d %H:%M"), "range": [start.isoformat(), end.isoformat()]}
    try:
        schedule, problems, errors = _calendar(token, start, end, sport_token)
    except innohassle.ServiceError as e:
        return {"error": _why(e, "The InNoHassle schedule")}
    result["schedule"] = schedule[:MAX_ITEMS]
    if len(schedule) > MAX_ITEMS:
        result["note"] = f"Only the first {MAX_ITEMS} of {len(schedule)} are shown; narrow the dates."
    result["bookings"], not_booked, booking_errors = _bookings(token, start, end)
    errors.update(booking_errors)
    if errors:
        result["source_errors"] = errors
    not_read = [f"{kind}: {problem}" for kind, problem in problems.items()] + not_booked
    if not_read:
        result["not_read"] = not_read
    return result


def _busy_rooms(bookings: list[dict], start: datetime, end: datetime) -> set[str]:
    if not isinstance(bookings, list):
        raise ValueError("Invalid room bookings response.")
    busy = set()
    for booking in bookings:
        if not isinstance(booking, dict) or not all(isinstance(booking.get(k), str) for k in ("room_id", "start", "end")):
            raise ValueError("Invalid room booking.")
        room_id = validate_room_id(booking["room_id"])
        begin, finish = _local(booking["start"]), _local(booking["end"])
        if finish <= begin:
            raise ValueError("Invalid room booking interval.")
        if begin < end and start < finish:
            busy.add(room_id)
    return busy


@tool(**metadata())
@result_boundary()
def rooms_get_free_rooms(
    time_from: ClockTime, time_to: ClockTime, day: date | None = None,
    *, token: str = Depends(require_innohassle),
) -> dict:
    """Room booking availability: find a free room or classroom for an exact interval.
    Найти свободные аудитории и комнаты для бронирования на указанное время.

    Default for generic free/bookable room requests, including "find a room for me".
    Check room booking times, occupancy and the signed-in user's access, without reading their personal agenda.
    Returns free, booked and unavailable rooms with refusal reasons; does not create a booking or check calendar conflicts.
    Personal-schedule matching is separate and only needed when explicitly requested; booking still requires scheduling checks.
    Ask for missing day/start/end or duration before checking; never invent a duration from a start time alone.
    A find/list/recommend request is read-only, not permission to book. After this result, report choices and stop;
    do not call rooms_book_room or open approval unless the user explicitly requested booking.
    """
    from catix.innohassle import client as innohassle

    day = day or _now().date()
    if problem := _future_span(day, time_from, time_to):
        return {"error": problem}
    start, end = (_at(day, time_from), _at(day, time_to))
    rooms = innohassle.bookable_rooms(token)
    bookings = innohassle.room_bookings(token, start, end)
    busy = _busy_rooms(bookings, start, end)
    free, unavailable = [], []
    for room in rooms:
        if room["id"] in busy:
            continue
        allowed, reason = innohassle.can_book_room(token, room["id"], start, end)
        if not allowed:
            unavailable.append({"room_id": room["id"], "reason": reason or "The service gave no reason."})
            continue
        item = {
            "room_id": room["id"],
            "title": room.get("title"),
            "capacity": room.get("capacity"),
            "who": {"yellow": "students", "red": "staff only", "special": "special rules"}.get(
                room.get("access_level") or "", None
            ),
            "night_only": "only 19:00-08:00 and at weekends" if room.get("restrict_daytime") else None,
        }
        free.append({k: v for k, v in item.items() if v})
    return {
        "date": day.strftime("%Y-%m-%d %a"),
        "range": f"{time_from:%H:%M}-{time_to:%H:%M}",
        "free": free,
        "booked": sorted(busy),
        "unavailable": unavailable,
        "checked_at": _now().isoformat(),
        "timezone": str(settings.tz),
        "note": "Checked against the service's current response, which may cache Outlook data. "
                "Not a reservation or guaranteed physical access; rechecked before booking.",
    }


@tool(**metadata(write=True))
@result_boundary(write=True)
def rooms_book_room(
    room_id: Annotated[str, Field(max_length=80), AfterValidator(validate_room_id)],
    day: date, time_from: ClockTime, time_to: ClockTime,
    title: Annotated[str, Field(max_length=100)],
    *, token: str = Depends(require_innohassle),
) -> dict:
    """Create a room booking or reservation after permission/time and occupancy checks.
    Забронировать аудиторию или комнату.

    Book a room with its actual ID, requested title and time interval.
    Sign-in required; client hosts handle confirmation. Never retry an unknown outcome automatically.
    """
    from catix.innohassle import client as innohassle

    if problem := _future_span(day, time_from, time_to):
        return invalid_arguments(problem)
    start, end = (_at(day, time_from), _at(day, time_to))
    try:
        allowed, why = innohassle.can_book_room(token, room_id, start, end)
        if not allowed:
            return {
                "done": False,
                "error": f"The asker cannot book this room then: {why or 'the service gave no reason'}.",
            }
        bookings = innohassle.room_bookings(token, start, end, room_id=room_id)
        if room_id in _busy_rooms(bookings, start, end):
            return {"done": False, "code": "room_occupied", "error": "The room is booked then; nothing was booked."}
    except (innohassle.ServiceError, httpx.HTTPError, ValueError, TypeError, KeyError):
        return {"done": False, "code": "availability_unverified",
                "error": "Room availability could not be verified; nothing was booked."}
    if problem := _future_span(day, time_from, time_to):
        return invalid_arguments(problem)
    try:
        booking = innohassle.book_room(token, room_id, title, start, end)
    except innohassle.ServiceError as e:
        return _refused(e, "The room booking service")
    return {
        "done": True,
        "booked": {
            "service": "room",
            "booking_id": booking.get("outlook_booking_id"),
            "room": room_id,
            "title": title,
            **_span(start, end),
        },
        "note": "Booked: tell the asker. It is in their Outlook and InNoHassle calendars.",
    }


@tool(**metadata())
@result_boundary()
def account_get_booking(
    service: Literal["music_room", "room"],
    booking_id: Annotated[str, Field(min_length=1, max_length=200), AfterValidator(validate_outlook_id)],
    *, token: str = Depends(require_innohassle),
) -> dict:
    """Inspect an existing personal reservation by its exact opaque identifier.

    Sign-in required. Returns title, full dates, times and place for the selected service.
    Only owned reservations are returned. Does not create or cancel anything.
    """
    from catix.innohassle import client as innohassle

    if service == "room":
        booking = innohassle.room_booking(token, booking_id)
        if (not isinstance(booking, dict) or booking.get("outlook_booking_id") != booking_id
                or booking.get("related_to_me") is not True):
            raise ValueError("The exact personal booking could not be verified.")
        if any(not isinstance(booking.get(key), str) or not booking[key].strip() for key in ("room_id", "title")):
            raise ValueError("Unreadable room booking details.")
        start, end = _local(booking["start"]), _local(booking["end"])
        item = {"room": booking["room_id"], "place": booking["room_id"], "title": booking["title"]}
    else:
        bookings = innohassle.my_music_room_bookings(token)
        if not isinstance(bookings, list) or any(
            not isinstance(b, dict) or type(b.get("id")) not in (int, str) for b in bookings
        ):
            raise ValueError("Unreadable personal music bookings.")
        matches = [b for b in bookings if str(b["id"]) == booking_id]
        if len(matches) != 1:
            raise ValueError("The exact personal booking could not be verified.")
        booking = matches[0]
        start, end = _local(booking["time_start"]), _local(booking["time_end"])
        item = {"title": "Music room", "place": "Music room"}
    if end <= start:
        raise ValueError("Unreadable booking interval.")
    return {"booking": {"service": service, "booking_id": booking_id, **_span(start, end), **item,
                        "timezone": str(settings.tz), "starts_at": start.isoformat(), "ends_at": end.isoformat()}}


@tool(**metadata(write=True))
@result_boundary(write=True)
def account_cancel_booking(
    service: Literal["music_room", "room"],
    booking_id: Annotated[str, Field(max_length=200), AfterValidator(validate_outlook_id)],
    *, token: str = Depends(require_innohassle),
) -> dict:
    """Cancel the signed-in user's room or music_room booking/reservation by its exact opaque ID.
    Отменить бронь аудитории или музыкальной комнаты.

    Client hosts handle confirmation; never retry an unknown outcome automatically.
    """
    from catix.innohassle import client as innohassle

    music_id = None
    if service == "music_room":
        if not booking_id.isdigit():
            return invalid_arguments("No such music room booking: take its booking_id from account_get_my_schedule.")
        try:
            music_id = int(booking_id)
        except ValueError:
            return invalid_arguments("No such music room booking: take its booking_id from account_get_my_schedule.")
    try:
        if music_id is not None:
            innohassle.cancel_music_room(token, music_id)
        else:
            innohassle.cancel_room(token, booking_id)
    except innohassle.ServiceError as e:
        return _refused(e, "The music room" if service == "music_room" else "The room booking service")
    return {
        "done": True,
        "cancelled": {"service": service, "booking_id": booking_id},
        "note": "Cancelled: tell the asker.",
    }


# Conservative local availability rules from the published Music Room bot UI.
# Keep separate from the upstream API's permissive/buggy hour and .days checks.
_MUSIC_OPEN, _MUSIC_CLOSE = time(7), time(22, 30)
_MUSIC_STEP = timedelta(minutes=30)
_MUSIC_HORIZON = timedelta(days=7)
_MUSIC_RULES_SOURCE = (
    "https://github.com/one-zero-eight/music-room/blob/60e67e3cc3e770513a748b8cf59c0a61d687de92/"
    "src/bot/routers/booking/create_booking_routes.py"
)


def _music_windows(day: date, now: datetime, occupied: list[tuple[datetime, datetime]],
                   quota_minutes: int, duration_minutes: int | None) -> list[dict]:
    """Subtract occupied half-hours, then constrain starts and personal duration."""
    cursor, closing = _at(day, _MUSIC_OPEN), _at(day, _MUSIC_CLOSE)
    spans = []
    while cursor < closing:
        end = cursor + _MUSIC_STEP
        if cursor > now and not any(start < end and cursor < finish for start, finish in occupied):
            if spans and spans[-1][1] == cursor:
                spans[-1] = (spans[-1][0], end)
            else:
                spans.append((cursor, end))
        cursor = end
    minimum = timedelta(minutes=duration_minutes) if duration_minutes is not None else _MUSIC_STEP
    horizon, midnight = now + _MUSIC_HORIZON, _at(day, time.min)
    windows = []
    for start, end in spans:
        maximum = min(quota_minutes, int((end - start).total_seconds() // 60)) // 30 * 30
        latest = min(end - minimum, horizon)
        latest = midnight + ((latest - midnight) // _MUSIC_STEP) * _MUSIC_STEP
        if maximum < minimum.total_seconds() / 60 or latest < start:
            continue
        windows.append({"start": start.strftime("%H:%M"), "end": end.strftime("%H:%M"),
                        "latest_start": latest.strftime("%H:%M"), "max_duration_minutes": maximum})
    return windows


@tool(**metadata())
@result_boundary()
def music_get_available_windows(
    day: date,
    duration_minutes: Annotated[int | None, Field(ge=30, le=1440, multiple_of=30)] = None,
    time_from: ClockTime | None = None,
    time_to: ClockTime | None = None,
    *, token: str = Depends(require_innohassle),
) -> dict:
    """Music Room service availability: bookable intervals and free windows for one day, NOT the user's personal free time.
    Свободные окна музыкальной комнаты без проверки личного расписания.

    Default for ordinary Music Room availability, including "find a music room" or "can I book".
    Does not read classes, Sport or AI Calendar; service access and personal booking quotas still apply.

    Requires InNoHassle sign-in and Music Room registration. Calculates from fresh occupied
    intervals and daily/weekly quotas using local bot-derived 07:00–22:30 / 30-minute rules
    and a conservative rolling seven-day start horizon; not an upstream availability promise.
    For a requested time interval pass both time_from and time_to exactly as stated by the
    user, not duration alone. The pair must be ordered on the same day and on the half-hour
    grid; duration is derived from it and any supplied duration must match. Exact mode
    returns only that interval or an explicit exclusion, never alternatives elsewhere that day.
    Omit both times for day-wide windows. Omit duration to avoid inventing it. latest_start
    is for duration_minutes, or 30 minutes if omitted. max_duration_minutes is a limit at
    the window's start, not permission to book the whole window. No reservation is made.
    """
    return _music_availability(day, duration_minutes, token, time_from=time_from, time_to=time_to)


def _music_availability(day: date, duration_minutes: int | None, token: str, *,
                        time_from: time | None = None, time_to: time | None = None) -> dict:
    """Shared fresh personal checks for the availability read and booking write."""
    from catix.innohassle import client as innohassle

    if (time_from is None) != (time_to is None):
        return invalid_arguments("Pass both time_from and time_to for an exact Music Room interval.")
    start = end = None
    if time_from is not None and time_to is not None:
        if any(clock.tzinfo is not None or clock.second or clock.microsecond or clock.minute % 30
               for clock in (time_from, time_to)):
            return invalid_arguments("Music Room intervals must use the local 30-minute grid.")
        if time_to <= time_from:
            return invalid_arguments("Music Room interval must end after it starts on the same day.")
        start, end = _at(day, time_from), _at(day, time_to)
        canonical_duration = int((end - start).total_seconds() // 60)
        if duration_minutes is not None and duration_minutes != canonical_duration:
            return invalid_arguments("duration_minutes must match the requested Music Room interval.")
        duration_minutes = canonical_duration
    now = _now()
    result = {
        "date": day.isoformat(), "timezone": str(settings.tz), "checked_at": now.isoformat(),
        "availability": "calculated", "duration_minutes": duration_minutes,
        "rules": {"opens_at": "07:00", "closes_at": "22:30", "step_minutes": 30,
                  "latest_booking_start": (now + _MUSIC_HORIZON).isoformat(), "source": _MUSIC_RULES_SOURCE},
        "remaining_daily_minutes": None, "remaining_weekly_minutes": None,
        "windows": [], "reason": None,
        "note": "Calculated from fresh bookings and personal limits using conservative local, bot-derived rules, "
                "not live upstream policy, a reservation or guaranteed physical access. "
                "Windows are alternatives sharing the same quota. Availability may change before confirmation.",
    }
    if start is not None:
        result["requested_interval"] = {"starts_at": start.isoformat(), "ends_at": end.isoformat()}
        if start <= now:
            return {**result, "reason": "past"}
        if start > now + _MUSIC_HORIZON:
            return {**result, "reason": "outside_booking_horizon"}
        if time_from < _MUSIC_OPEN or time_to > _MUSIC_CLOSE:
            return {**result, "reason": "outside_opening_hours"}
    if not now.date() <= day <= (now + _MUSIC_HORIZON).date():
        return {**result, "reason": "outside_booking_horizon"}
    try:
        profile = innohassle.my_music_room_profile(token)
    except innohassle.ServiceError as error:
        if error.status in {403, 404}:
            return {**(result if start is not None else {}),
                    "error": "Music Room registration/access could not be verified. "
                             "Check your registration in @InnoMusicRoomBot.", "code": "access_unverified"}
        raise
    status = profile.get("status") if isinstance(profile, dict) else None
    if status == "banned":
        return {**result, "reason": "access_denied"}
    if status not in {"free", "middle", "senior", "lord", "admin"}:
        raise ValueError("Unknown Music Room access status.")
    daily, weekly = innohassle.music_room_hours_left(token, day)
    bookings = innohassle.music_room_bookings(day, fresh=True)
    if not isinstance(bookings, list):
        raise ValueError("Invalid Music Room bookings response.")
    occupied = []
    for booking in bookings:
        booking_start, booking_end = _local(booking["time_start"]), _local(booking["time_end"])
        if booking_end <= booking_start:
            raise ValueError("Invalid Music Room booking interval.")
        occupied.append((booking_start, booking_end))
    now = _now()
    result["checked_at"] = now.isoformat()
    result["rules"]["latest_booking_start"] = (now + _MUSIC_HORIZON).isoformat()
    daily_minutes, weekly_minutes = max(0, int(daily * 60)), max(0, int(weekly * 60))
    result["remaining_daily_minutes"], result["remaining_weekly_minutes"] = daily_minutes, weekly_minutes
    quota = min(daily_minutes, weekly_minutes)
    if start is not None:
        if start <= now:
            result["reason"] = "past"
        elif start > now + _MUSIC_HORIZON:
            result["reason"] = "outside_booking_horizon"
        elif quota < duration_minutes:
            result["reason"] = "insufficient_quota"
        elif any(begin < end and start < finish for begin, finish in occupied):
            result["reason"] = "room_occupied"
            overlaps = []
            for begin, finish in sorted((max(start, begin), min(end, finish))
                                        for begin, finish in occupied if begin < end and start < finish):
                if overlaps and begin <= overlaps[-1][1]:
                    overlaps[-1] = (overlaps[-1][0], max(overlaps[-1][1], finish))
                else:
                    overlaps.append((begin, finish))
            result["occupied_intervals"] = [{"starts_at": begin.isoformat(), "ends_at": finish.isoformat()}
                                            for begin, finish in overlaps]
        else:
            result["windows"] = [{"start": time_from.strftime("%H:%M"), "end": time_to.strftime("%H:%M"),
                                  "latest_start": time_from.strftime("%H:%M"),
                                  "max_duration_minutes": duration_minutes}]
        return result
    result["windows"] = _music_windows(day, now, occupied, quota, duration_minutes)
    if not result["windows"]:
        result["reason"] = "insufficient_quota" if quota < (duration_minutes or 30) else "no_matching_window"
    return result


@tool(**metadata(write=True))
@result_boundary(write=True)
def music_book_music_room(
    day: date, time_from: ClockTime, time_to: ClockTime,
    *, token: str = Depends(require_innohassle),
) -> dict:
    """Book the music room after fresh personal access, quota and occupancy checks.

    Enforces the same conservative local 07:00–22:30 opening, half-hour grid and rolling
    seven-day start horizon as music_get_available_windows, including direct MCP calls.
    These are local bot-derived constraints, not a live upstream policy guarantee.
    Sign-in required; client hosts handle confirmation. Never retry unknown outcomes automatically.
    """
    from catix.innohassle import client as innohassle

    if problem := _future_span(day, time_from, time_to):
        return invalid_arguments(problem)
    if time_from.minute % 30 or time_to.minute % 30:
        return invalid_arguments("Music Room bookings must start and end on the conservative local 30-minute grid.")
    start, end = (_at(day, time_from), _at(day, time_to))
    duration = int((end - start).total_seconds() // 60)
    try:
        available = _music_availability(day, duration, token)
    except Exception:
        # This block is read-only: unlike a POST/readback failure, nothing was written.
        return {"done": False, "code": "availability_unverified",
                "error": "Music Room access, quotas or occupancy could not be verified; nothing was booked."}
    if "error" in available:
        return {"done": False, **available}
    if not any(
        window["start"] <= time_from.strftime("%H:%M") <= window["latest_start"]
        and time_to.strftime("%H:%M") <= window["end"]
        and duration <= window["max_duration_minutes"]
        for window in available["windows"]
    ):
        return {"done": False, "code": available["reason"] or "no_matching_window",
                "error": "The requested interval is not available under the Music Room personal limits "
                         "and conservative local booking rules; nothing was booked."}
    try:
        booking = innohassle.book_music_room(token, start, end)
    except innohassle.ServiceError as e:
        return _refused(e, "The music room")
    return {
        "done": True,
        "booked": {"service": "music_room", "booking_id": str(booking.get("id")), **_span(start, end)},
        "note": "Booked: tell the asker. The booking is in their InNoHassle calendar.",
    }


@tool(**metadata(write=True))
@result_boundary(write=True)
def events_enroll_in_event(
    event_id: Annotated[str, Field(pattern="^[0-9a-f]{24}$")], leave: bool = False,
    *, token: str = Depends(require_innohassle),
) -> dict:
    """Enroll in or leave an InNoHassle event; external registrations return their link instead.

    Sign-in required; client hosts handle confirmation. Never retry unknown outcomes automatically.
    """
    from catix.innohassle import client as innohassle
    from catix.innohassle.mcp_public import _event_details

    try:
        event = innohassle.my_event(token, event_id)
        enrollment = (event.get("data") or {}).get("enrollment") or {}
        if not leave and enrollment.get("type") == "external":
            return {"done": False, "error": "This event uses external registration; open the organisers' page."}
        if not leave:
            start = datetime.fromisoformat(event['data']['starts_at'])
            capacity, count = enrollment.get('capacity'), event.get('enrolled_count')
            if (enrollment.get('type') != 'internal' or start.utcoffset() is None or start <= datetime.now(settings.tz)
                    or type(count) is not int or count < 0
                    or capacity is not None and (type(capacity) is not int or capacity < 0)):
                return {'done': False, 'error': 'Event enrollment is not available or could not be verified.'}
            if event['enrolled'] is not True and capacity is not None and count >= capacity:
                return {'done': False, 'error': 'Event is at capacity.'}
    except Exception:  # noqa: BLE001 - this check is read-only, so no write happened
        return {'done': False, 'error': 'The fresh enrollment check failed; nothing was written.'}
    if event['enrolled'] is not (not leave):
        try:
            (innohassle.unenroll if leave else innohassle.enroll)(token, event_id)
        except innohassle.ServiceError as e:
            return _refused(e, "InNoHassle Events")
        # Outside the definite-refusal handler: readback failure after POST is unknown.
        event = innohassle.my_event(token, event_id)
    if event['enrolled'] is not (not leave):
        return {'done': None, 'outcome': 'unknown', 'error': 'Enrollment could not be confirmed. Do not retry automatically.'}
    return {
        "done": True,
        "event_id": event_id,
        "enrolled": not leave,
        "enrollment_verified": True,
        "event": _event_details(event, event_id),
        "note": "Done: tell the asker. Their enrolments are in their InNoHassle calendar.",
    }
