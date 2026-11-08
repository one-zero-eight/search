"""Explicit MCP account integrations. Business rules execute here, not in the agent."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal

if TYPE_CHECKING:
    from catix.innohassle import client as innohassle
from concurrent.futures import ThreadPoolExecutor
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
    invalid_arguments, metadata, require_innohassle, result_boundary,
)
from catix.settings import settings

MAX_ITEMS = 40


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
    return {"date": start.strftime("%Y-%m-%d %a"), "time": f"{start:%H:%M}-{end:%H:%M}"}


def _why(e: innohassle.ServiceError, what: str) -> str:
    if e.status == 401:
        return "InNoHassle did not accept the asker's sign-in: ask them to sign in on the site again."
    return f"{what} refused: {e.detail}"


def _refused(e: innohassle.ServiceError, what: str) -> dict:
    """The result of an action a service refused: nothing was done."""
    return {"done": False, "error": _why(e, what)}


def _calendar_items(text: str, kind: str, start: date, end: date) -> list[dict]:
    calendar = icalendar.Calendar.from_ical(text)
    now, seen, out = (_now(), set(), [])
    for ev in recurring_ical_events.of(calendar).between(start, end + timedelta(days=1)):
        begin = ev.decoded("DTSTART")
        title, place = (str(ev.get("SUMMARY", "")), str(ev.get("LOCATION", "")) or None)
        if (key := (str(begin), title, place)) in seen:
            continue
        seen.add(key)
        if not isinstance(begin, datetime):
            out.append(
                {
                    k: v
                    for k, v in {
                        "kind": kind,
                        "date": begin.strftime("%Y-%m-%d %a"),
                        "all_day": True,
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


def _calendar(token: str, start: date, end: date) -> tuple[list[dict], dict[str, str]]:
    """The asker's InNoHassle calendars in the period (classes, sport, the events they enrolled in), each
    item with its `kind`; and what could not be read, by kind. Read concurrently rather than waiting on each service in turn.
    Raises ServiceError 401 when InNoHassle does not accept the token."""
    from catix.innohassle import client as innohassle

    with ThreadPoolExecutor(max_workers=len(innohassle.MY_CALENDARS)) as pool:
        asked = {kind: pool.submit(innohassle.my_calendar_ics, token, kind) for kind in innohassle.MY_CALENDARS}
    items, problems = ([], {})
    for kind, future in asked.items():
        try:
            items += _calendar_items(future.result(), kind, start, end)
        except innohassle.ServiceError as e:
            if e.status == 401:
                raise
            problems[kind] = f"{e.status}: {e.detail}"
        except httpx.HTTPError as e:
            problems[kind] = f"InNoHassle did not answer ({type(e).__name__})"
        except ValueError as e:
            problems[kind] = f"unreadable calendar: {e}"[:200]
    return (sorted(items, key=lambda i: (i["date"], i.get("time", ""))), problems)


def _bookings(token: str, start: date, end: date) -> tuple[list[dict], list[str]]:
    """The asker's bookings of the music room and of rooms in the period, with the ids cancel_booking takes; and what could
    not be read."""
    from catix.innohassle import client as innohassle

    out, problems = ([], [])
    first, last = (_at(start, time.min), _at(end + timedelta(days=1), time.min))
    try:
        for b in innohassle.my_music_room_bookings(token):
            begin, finish = (_local(b["time_start"]), _local(b["time_end"]))
            if first <= begin < last:
                out.append(
                    {"service": "music_room", "booking_id": str(b["id"]), **_span(begin, finish), "title": "Music room"}
                )
    except innohassle.ServiceError as e:
        problems.append(f"music room: {e.detail}")
    try:
        for b in innohassle.my_room_bookings(token, first, last):
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
    except innohassle.ServiceError as e:
        problems.append(f"rooms: {e.detail}")
    return (sorted(out, key=lambda b: (b["date"], b["time"])), problems)


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
    *, token: str = Depends(require_innohassle),
) -> dict:
    """Signed-in user's external InNoHassle calendars and room/music bookings. No local AI Calendar data."""
    from catix.innohassle import client as innohassle

    start = date_from or _now().date()
    end = date_to or start + timedelta(days=DEFAULT_DAYS - 1)
    result: dict = {"now": _now().strftime("%Y-%m-%d %H:%M"), "range": [start.isoformat(), end.isoformat()]}
    try:
        schedule, problems = _calendar(token, start, end)
    except innohassle.ServiceError as e:
        return {"error": _why(e, "The InNoHassle schedule")}
    result["schedule"] = schedule[:MAX_ITEMS]
    if len(schedule) > MAX_ITEMS:
        result["note"] = f"Only the first {MAX_ITEMS} of {len(schedule)} are shown; narrow the dates."
    result["bookings"], not_booked = _bookings(token, start, end)
    not_read = [f"{kind}: {problem}" for kind, problem in problems.items()] + not_booked
    if not_read:
        result["not_read"] = not_read
    return result


@tool(**metadata())
@result_boundary()
def rooms_get_free_rooms(
    time_from: ClockTime, time_to: ClockTime, day: date | None = None,
    *, token: str = Depends(require_innohassle),
) -> dict:
    """Room booking availability: find a free room or classroom for a reservation.
    Найти свободные аудитории и комнаты для бронирования.

    Check room booking times for the requested day and interval, including capacity and access rules.
    Sign-in required. Returns free and occupied rooms separately; does not create a booking.
    Availability depends on the interval: ask for the end time or duration if it is unknown.
    """
    from catix.innohassle import client as innohassle

    day = day or _now().date()
    start, end = (_at(day, time_from), _at(day, time_to))
    if end <= start:
        return {"error": "time_to must be after time_from."}
    try:
        rooms = innohassle.bookable_rooms(token)
        bookings = innohassle.room_bookings(token, start, end)
    except innohassle.ServiceError as e:
        return {"error": _why(e, "The room booking service")}
    busy = {b["room_id"] for b in bookings if _local(b["start"]) < end and start < _local(b["end"])}
    free = []
    for room in rooms:
        if room["id"] in busy:
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
    }


@tool(**metadata(write=True))
@result_boundary(write=True)
def rooms_book_room(
    room_id: Annotated[str, Field(max_length=80), AfterValidator(validate_room_id)],
    day: date, time_from: ClockTime, time_to: ClockTime,
    title: Annotated[str, Field(max_length=100)],
    *, token: str = Depends(require_innohassle),
) -> dict:
    """Create a room booking or reservation after permission/time checks.
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


@tool(**metadata(write=True))
@result_boundary(write=True)
def music_book_music_room(
    day: date, time_from: ClockTime, time_to: ClockTime,
    *, token: str = Depends(require_innohassle),
) -> dict:
    """Book the music room after overlap and remaining-hours checks.

    Sign-in required; client hosts handle confirmation. Never retry unknown outcomes automatically.
    """
    from catix.innohassle import client as innohassle

    if problem := _future_span(day, time_from, time_to):
        return invalid_arguments(problem)
    start, end = (_at(day, time_from), _at(day, time_to))
    try:
        taken = [
            b
            for b in innohassle.music_room_bookings(day)
            if _local(b["time_start"]) < end and start < _local(b["time_end"])
        ]
        if taken:
            busy = ", ".join((f"{_local(b['time_start']):%H:%M}-{_local(b['time_end']):%H:%M}" for b in taken))
            return {"done": False, "error": f"The music room is booked then ({busy}): nothing was booked."}
        daily, weekly = innohassle.music_room_hours_left(token, day)
        hours = (end - start).total_seconds() / 3600
        if hours > min(daily, weekly):
            return {
                "done": False,
                "error": f"The asker may book {daily:g} more hours that day and {weekly:g} that week: nothing was booked.",
            }
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

    try:
        event = innohassle.event(event_id)
        enrollment = (event.get("data") or {}).get("enrollment") or {}
        if not leave and enrollment.get("type") == "external":
            return {
                "done": False,
                "error": f"This event is enrolled with its organisers: {enrollment.get('url') or 'no link given'}.",
            }
        (innohassle.unenroll if leave else innohassle.enroll)(token, event_id)
    except innohassle.ServiceError as e:
        return _refused(e, "InNoHassle Events")
    return {
        "done": True,
        "event_id": event_id,
        "enrolled": not leave,
        "note": "Done: tell the asker. Their enrolments are in their InNoHassle calendar.",
    }
