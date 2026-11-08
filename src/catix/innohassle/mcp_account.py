"""Explicit MCP account integrations. Business rules execute here, not in the agent."""

from __future__ import annotations

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


def _class_calendar(token: str, start: date, end: date) -> tuple[list[dict], list[str]]:
    """Mirror the site's visible calendars and source-aware English exclusion.

    Website CalendarPage/getCalendarsToShow and iCalendarPlugin/isEnglishEvent,
    revision 34dc0d59972778eb99de6b0f4b0c10f67599fdb5. Never fall back to all.ics.
    """
    from catix.innohassle import client as innohassle

    user_id, aliases = innohassle.my_calendar_groups(token)
    if not aliases:
        return [], []
    catalogue = innohassle.event_groups(fresh=True)
    if not isinstance(catalogue, list) or any(not isinstance(g, dict) or not isinstance(g.get("alias"), str) for g in catalogue):
        raise ValueError("Unreadable calendar catalogue.")
    groups = {group["alias"]: group for group in catalogue}
    has_english = any(alias.startswith("english-") for alias in aliases)
    items, problems, seen = [], [], set()
    with ThreadPoolExecutor(max_workers=min(8, len(aliases))) as pool:
        asked = {alias: pool.submit(innohassle.my_group_calendar_ics, token, user_id, alias)
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
        except httpx.HTTPError as error:
            problems.append(f"{alias}: InNoHassle did not answer ({type(error).__name__})")
        except ValueError as error:
            problems.append(f"{alias}: unreadable calendar: {error}"[:200])
    return items, problems


def _calendar(token: str, start: date, end: date) -> tuple[list[dict], dict[str, str]]:
    """The asker's InNoHassle calendars in the period (classes, sport, the events they enrolled in), each
    item with its `kind`; and what could not be read, by kind. Read concurrently rather than waiting on each service in turn.
    Raises ServiceError 401 when InNoHassle does not accept the token."""
    from catix.innohassle import client as innohassle

    with ThreadPoolExecutor(max_workers=len(innohassle.MY_CALENDARS) + 1) as pool:
        asked: dict[str, Future] = {"class": pool.submit(_class_calendar, token, start, end)}
        asked.update({kind: pool.submit(innohassle.my_calendar_ics, token, kind) for kind in innohassle.MY_CALENDARS})
    items, problems = ([], {})
    for kind, future in asked.items():
        try:
            if kind == "class":
                classes, missing = future.result()
                items += classes
                if missing:
                    problems[kind] = "; ".join(missing)
            else:
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
    """The signed-in user's CURRENT PERSONAL schedule: selected/subscribed class calendars,
    including English and course selections, sport, event enrolments, and personal room/music bookings.
    Моё расписание, мой календарь: выбранный английский, курсы, спорт и мои бронирования.

    Uses the user's authenticated calendar feeds, not the public academic-group timetable, which
    can contain other English streams. No group argument is needed. Excludes the local AI Calendar:
    the host should also read get_my_ai_calendar with the SAME explicit date_from/date_to.
    Report not_read and truncation; never substitute public group events for a failed personal feed.
    """
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
    """Room booking availability: find a free room or classroom for a reservation.
    Найти свободные аудитории и комнаты для бронирования.

    Check room booking times, occupancy and the signed-in user's access for the exact interval.
    Returns free, booked and unavailable rooms with refusal reasons; does not create a booking.
    Availability depends on the interval: ask for the end time or duration if unknown.
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
    *, token: str = Depends(require_innohassle),
) -> dict:
    """Find personal music room booking availability and free time windows for one day.
    Свободные окна музыкальной комнаты: когда можно записаться или забронировать музкомнату.

    Requires InNoHassle sign-in and Music Room registration. Calculates from fresh occupied
    intervals and daily/weekly quotas using local bot-derived 07:00–22:30 / 30-minute rules
    and a conservative rolling seven-day start horizon; not an upstream availability promise.
    Omit duration to see windows without inventing the user's duration. latest_start is for
    duration_minutes, or a 30-minute booking if omitted. max_duration_minutes is a limit at
    the window's start, not permission to book the whole window. No reservation is made.
    """
    return _music_availability(day, duration_minutes, token)


def _music_availability(day: date, duration_minutes: int | None, token: str) -> dict:
    """Shared fresh personal checks for the availability read and booking write."""
    from catix.innohassle import client as innohassle

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
    if not now.date() <= day <= (now + _MUSIC_HORIZON).date():
        return {**result, "reason": "outside_booking_horizon"}
    try:
        profile = innohassle.my_music_room_profile(token)
    except innohassle.ServiceError as error:
        if error.status in {403, 404}:
            return {"error": "Music Room registration/access could not be verified. "
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
        start, end = _local(booking["time_start"]), _local(booking["time_end"])
        if end <= start:
            raise ValueError("Invalid Music Room booking interval.")
        occupied.append((start, end))
    now = _now()
    result["checked_at"] = now.isoformat()
    result["rules"]["latest_booking_start"] = (now + _MUSIC_HORIZON).isoformat()
    daily_minutes, weekly_minutes = max(0, int(daily * 60)), max(0, int(weekly * 60))
    result["remaining_daily_minutes"], result["remaining_weekly_minutes"] = daily_minutes, weekly_minutes
    quota = min(daily_minutes, weekly_minutes)
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
