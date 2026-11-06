"""Tools on the asker's own InNoHassle account, asked with their token, which only the site has (api/auth.py): their schedule
and bookings, the free rooms they may book, and the actions done for them: booking the music room or a room, enrolling in
an event (or leaving it), cancelling a booking, removing an event from their AI Calendar (agent/calendar_tools.py), checking
them in to a sport training (agent/sport_tools.py).

No action is done at once. HumanInTheLoopMiddleware stops the account helper after the model call that asks for one
(core._helper_tool, `APPROVAL` here): the run pauses (a LangGraph interrupt, kept in the chat's checkpoint), the site shows
the user what is to be done (the `description`s here) and the user approves or declines it (api/ask.py, POST
/ask/{chat_id}/decision). Approved, the tool runs; declined, it does not, and the helper is told so. Arguments that cannot
be right whatever happens (a time already past, an end before the start: `_problem`) are not put to the user: the tool runs
and says what is wrong without doing anything, so a call that was not approved never does anything.
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta
from typing import Literal

import httpx
import icalendar
import recurring_ical_events
from langchain.tools import ToolRuntime
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from pydantic import BaseModel, Field, ValidationError

from catix import personal_calendar
from catix.agent.calendar_tools import RemoveFromAiCalendarArgs, calendar_key, events_between
from catix.agent.sport_tools import SportCheckinArgs, sport_token, training_name
from catix.common.dates import ClockTime
from catix.innohassle import client as innohassle
from catix.innohassle import sport as sport_api
from catix.settings import settings

log = logging.getLogger("catix.account")

MAX_ITEMS = 40
DEFAULT_DAYS = 7
NO_ACCOUNT = (
    "The asker's own InNoHassle account is reachable only on the site innohassle.ru, signed in. Say that their schedule and "
    "bookings are there, in the chat with the assistant, and that nothing was done here."
)
DECLINED = "The user declined: nothing was done. Do not ask for it again unless the user asks."
MONTHS_RU = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
WEEKDAYS_RU = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]


def _token(runtime: ToolRuntime) -> str | None:
    context = getattr(runtime, "context", None)
    token = getattr(context, "innohassle_token", None)
    return token.get_secret_value() if token else None


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


# ---- what the asker has ----------------------------------------------------------------------------------------------


class GetMyScheduleArgs(BaseModel):
    date_from: date | None = Field(None, description="YYYY-MM-DD, default today.")
    date_to: date | None = Field(None, description=f"YYYY-MM-DD inclusive, default date_from + {DEFAULT_DAYS - 1} days.")


MOODLE_NOT_LINKED = (
    "Their Moodle is not linked to InNoHassle, so its deadlines are not here: they are in Moodle's own calendar, "
    "https://moodle.innopolis.university/calendar/view.php?view=month"
)


def _calendar_items(text: str, kind: str, start: date, end: date) -> list[dict]:
    calendar = icalendar.Calendar.from_ical(text)
    now, seen, out = _now(), set(), []
    for ev in recurring_ical_events.of(calendar).between(start, end + timedelta(days=1)):
        begin = ev.decoded("DTSTART")
        title, place = str(ev.get("SUMMARY", "")), str(ev.get("LOCATION", "")) or None
        if (key := (str(begin), title, place)) in seen:
            continue
        seen.add(key)
        if not isinstance(begin, datetime):  # a whole day: a deadline, a holiday
            out.append({k: v for k, v in {"kind": kind, "date": begin.strftime("%Y-%m-%d %a"), "all_day": True, "title": title,
                                          "place": place}.items() if v})  # fmt: skip
            continue
        begin = begin.astimezone(settings.tz)
        finish = ev.decoded("DTEND").astimezone(settings.tz) if "DTEND" in ev else begin
        item = {"kind": kind, **(_span(begin, finish) if finish > begin else {"date": begin.strftime("%Y-%m-%d %a"),
                "time": f"{begin:%H:%M}"}), "title": title, "place": place,  # a deadline is a moment
                "status": "finished" if finish <= now else "now" if begin <= now else "upcoming"}  # fmt: skip
        out.append({k: v for k, v in item.items() if v})
    return out


def _calendar(token: str, start: date, end: date) -> tuple[list[dict], dict[str, str]]:
    """The asker's InNoHassle calendars in the period (classes, sport, Moodle deadlines, the events they enrolled in), each
    item with its `kind`; and what could not be read, by kind. Read at once: four requests one after another took seconds.
    Raises ServiceError 401 when InNoHassle does not accept the token."""
    with ThreadPoolExecutor(max_workers=len(innohassle.MY_CALENDARS)) as pool:
        asked = {kind: pool.submit(innohassle.my_calendar_ics, token, kind) for kind in innohassle.MY_CALENDARS}
    items, problems = [], {}
    for kind, future in asked.items():
        try:
            items += _calendar_items(future.result(), kind, start, end)
        except innohassle.ServiceError as e:
            if e.status == 401:
                raise
            problems[kind] = MOODLE_NOT_LINKED if kind == "deadline" and e.status == 404 else f"{e.status}: {e.detail}"
        except httpx.HTTPError as e:  # (a timeout: the others are still there)
            problems[kind] = f"InNoHassle did not answer ({type(e).__name__})"
        except ValueError as e:  # not iCalendar
            problems[kind] = f"unreadable calendar: {e}"[:200]
    return sorted(items, key=lambda i: (i["date"], i.get("time", ""))), problems


def _bookings(token: str, start: date, end: date) -> tuple[list[dict], list[str]]:
    """The asker's bookings of the music room and of rooms in the period, with the ids cancel_booking takes; and what could
    not be read."""
    out, problems = [], []
    first, last = _at(start, time.min), _at(end + timedelta(days=1), time.min)
    try:
        for b in innohassle.my_music_room_bookings(token):
            begin, finish = _local(b["time_start"]), _local(b["time_end"])
            if first <= begin < last:
                out.append({"service": "music_room", "booking_id": str(b["id"]), **_span(begin, finish), "title": "Music room"})
    except innohassle.ServiceError as e:
        problems.append(f"music room: {e.detail}")
    try:
        for b in innohassle.my_room_bookings(token, first, last):
            begin, finish = _local(b["start"]), _local(b["end"])
            out.append({"service": "room", "booking_id": b.get("outlook_booking_id"), **_span(begin, finish),
                        "room": b.get("room_id"), "title": b.get("title")})  # fmt: skip
    except innohassle.ServiceError as e:
        problems.append(f"rooms: {e.detail}")
    return sorted(out, key=lambda b: (b["date"], b["time"])), problems


@tool(args_schema=GetMyScheduleArgs)
def get_my_schedule(runtime: ToolRuntime, date_from: date | None = None, date_to: date | None = None) -> dict:
    """The asker's own calendar for a period, everything in it: the classes of their groups and of the groups they added
    (kind "class"), sport ("sport"), Moodle deadlines ("deadline", when their Moodle is linked), the events they enrolled in
    ("event"), and their AI Calendar (the events they added under the assistant's answers, with the `calendar_event_id`
    remove_from_ai_calendar takes); and their bookings of the music room and of rooms, with the ids cancel_booking takes."""
    if not (token := _token(runtime)):
        return {"error": NO_ACCOUNT}
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
    try:
        key, no_key = calendar_key(runtime)
        if key:
            result["ai_calendar"] = events_between(key, start, end)
        else:
            not_read.append(f"ai_calendar: {no_key}")
    except Exception:  # noqa: BLE001 - the calendar of InNoHassle is there without it
        log.exception("the AI Calendar could not be read")
        not_read.append("ai_calendar: could not be read now")
    if not_read:
        result["not_read"] = not_read
    return result


class GetFreeRoomsArgs(BaseModel):
    day: date | None = Field(None, description="YYYY-MM-DD, default today.")
    time_from: ClockTime = Field(description="HH:MM")
    time_to: ClockTime = Field(description="HH:MM")


@tool(args_schema=GetFreeRoomsArgs)
def get_free_rooms(runtime: ToolRuntime, time_from: time, time_to: time, day: date | None = None) -> dict:
    """The rooms of the room booking service (meeting rooms, lecture rooms) that nobody booked for that time, with their
    capacity, the `room_id` book_room takes, and who may book each."""
    if not (token := _token(runtime)):
        return {"error": NO_ACCOUNT}
    day = day or _now().date()
    start, end = _at(day, time_from), _at(day, time_to)
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
        item = {"room_id": room["id"], "title": room.get("title"), "capacity": room.get("capacity"),
                "who": {"yellow": "students", "red": "staff only", "special": "special rules"}.get(room.get("access_level") or "", None),
                "night_only": "only 19:00-08:00 and at weekends" if room.get("restrict_daytime") else None}  # fmt: skip
        free.append({k: v for k, v in item.items() if v})
    return {"date": day.strftime("%Y-%m-%d %a"), "range": f"{time_from:%H:%M}-{time_to:%H:%M}", "free": free,
            "booked": sorted(busy)}  # fmt: skip


# ---- what is done for the asker, once they approve -------------------------------------------------------------------


class BookMusicRoomArgs(BaseModel):
    day: date = Field(description="YYYY-MM-DD")
    time_from: ClockTime = Field(description="HH:MM")
    time_to: ClockTime = Field(description="HH:MM")


class BookRoomArgs(BaseModel):
    room_id: str = Field(max_length=80, description="The `room_id` from get_free_rooms.")
    day: date = Field(description="YYYY-MM-DD")
    time_from: ClockTime = Field(description="HH:MM")
    time_to: ClockTime = Field(description="HH:MM")
    title: str = Field(max_length=100, description="What the booking is for, as the asker said it ('Встреча команды').")


class EnrollArgs(BaseModel):
    event_id: str = Field(max_length=40, description="The `id` of the event from get_university_events.")
    leave: bool = Field(False, description="true to cancel the asker's enrolment instead.")


class CancelBookingArgs(BaseModel):
    service: Literal["music_room", "room"] = Field(description="The `service` of the booking from get_my_schedule.")
    booking_id: str = Field(max_length=200, description="The `booking_id` of the booking from get_my_schedule.")


def _future_span(day: date, time_from: time, time_to: time) -> str | None:
    if _at(day, time_to) <= _at(day, time_from):
        return "time_to must be after time_from."
    if _at(day, time_from) <= _now():
        return "That time is already past: ask the asker for a time to come."
    return None


def _problem(name: str, args: dict) -> str | None:
    """What makes the arguments of an action wrong whatever happens; None if they may be right. Such a call is not put to the
    user: the tool says what is wrong and does nothing."""
    schema = {"book_music_room": BookMusicRoomArgs, "book_room": BookRoomArgs, "enroll_in_event": EnrollArgs,
              "cancel_booking": CancelBookingArgs, "remove_from_ai_calendar": RemoveFromAiCalendarArgs,
              "sport_checkin": SportCheckinArgs}[name]  # fmt: skip
    try:
        parsed = schema.model_validate(args)
    except ValidationError as e:
        return f"Wrong arguments: {e.errors()[0]['msg']}"
    if isinstance(parsed, BookMusicRoomArgs | BookRoomArgs):
        return _future_span(parsed.day, parsed.time_from, parsed.time_to)
    if isinstance(parsed, EnrollArgs) and not (len(parsed.event_id) == 24 and all(c in "0123456789abcdef" for c in parsed.event_id)):
        return "No such event id: take the `id` of the event from get_university_events."
    if isinstance(parsed, CancelBookingArgs) and parsed.service == "music_room" and not parsed.booking_id.isdigit():
        return "No such music room booking: take its `booking_id` from get_my_schedule."
    return None


@tool(args_schema=BookMusicRoomArgs)
def book_music_room(day: date, time_from: time, time_to: time, runtime: ToolRuntime) -> dict:
    """Book the music room for the asker. The asker is shown the booking and approves or declines it before it is made: call
    it as soon as they asked to book a time, after get_music_room_schedule showed that time free; never ask them yourself."""
    if not (token := _token(runtime)):
        return {"error": NO_ACCOUNT}
    if problem := _future_span(day, time_from, time_to):
        return {"done": False, "error": problem}
    start, end = _at(day, time_from), _at(day, time_to)
    try:
        taken = [b for b in innohassle.music_room_bookings(day) if _local(b["time_start"]) < end and start < _local(b["time_end"])]
        if taken:
            busy = ", ".join(f"{_local(b['time_start']):%H:%M}-{_local(b['time_end']):%H:%M}" for b in taken)
            return {"done": False, "error": f"The music room is booked then ({busy}): nothing was booked."}
        daily, weekly = innohassle.music_room_hours_left(token, day)
        hours = (end - start).total_seconds() / 3600
        if hours > min(daily, weekly):
            return {"done": False, "error": f"The asker may book {daily:g} more hours that day and {weekly:g} that week: nothing was booked."}
        booking = innohassle.book_music_room(token, start, end)
    except innohassle.ServiceError as e:
        return _refused(e, "The music room")
    return {"done": True, "booked": {"service": "music_room", "booking_id": str(booking.get("id")), **_span(start, end)},
            "note": "Booked: tell the asker. The booking is in their InNoHassle calendar."}  # fmt: skip


@tool(args_schema=BookRoomArgs)
def book_room(room_id: str, day: date, time_from: time, time_to: time, title: str, runtime: ToolRuntime) -> dict:
    """Book a room (from get_free_rooms) for the asker, in the university's room booking (Outlook). The asker is shown the
    booking and approves or declines it before it is made: call it as soon as they asked to book; never ask them yourself."""
    if not (token := _token(runtime)):
        return {"error": NO_ACCOUNT}
    if problem := _future_span(day, time_from, time_to):
        return {"done": False, "error": problem}
    start, end = _at(day, time_from), _at(day, time_to)
    try:
        allowed, why = innohassle.can_book_room(token, room_id, start, end)
        if not allowed:
            return {"done": False, "error": f"The asker cannot book this room then: {why or 'the service gave no reason'}."}
        booking = innohassle.book_room(token, room_id, title, start, end)
    except innohassle.ServiceError as e:
        return _refused(e, "The room booking service")
    return {"done": True, "booked": {"service": "room", "booking_id": booking.get("outlook_booking_id"), "room": room_id,
            "title": title, **_span(start, end)}, "note": "Booked: tell the asker. It is in their Outlook and InNoHassle calendars."}  # fmt: skip


@tool(args_schema=EnrollArgs)
def enroll_in_event(event_id: str, runtime: ToolRuntime, leave: bool = False) -> dict:
    """Enrol the asker in a university event of InNoHassle Events whose enrolment is on InNoHassle (or, with leave, cancel
    their enrolment). The asker approves or declines it before it is done: call it as soon as they asked; never ask them
    yourself. An event enrolled with the organisers ('on the organisers' page') cannot be enrolled here: give its link."""
    if not (token := _token(runtime)):
        return {"error": NO_ACCOUNT}
    try:
        event = innohassle.event(event_id)
        enrollment = (event.get("data") or {}).get("enrollment") or {}
        if not leave and enrollment.get("type") == "external":
            return {"done": False, "error": f"This event is enrolled with its organisers: {enrollment.get('url') or 'no link given'}."}
        (innohassle.unenroll if leave else innohassle.enroll)(token, event_id)
    except innohassle.ServiceError as e:
        return _refused(e, "InNoHassle Events")
    return {"done": True, "event_id": event_id, "enrolled": not leave,
            "note": "Done: tell the asker. Their enrolments are in their InNoHassle calendar."}  # fmt: skip


@tool(args_schema=CancelBookingArgs)
def cancel_booking(service: str, booking_id: str, runtime: ToolRuntime) -> dict:
    """Cancel one of the asker's bookings (of the music room or of a room) from get_my_schedule. The asker approves or
    declines it before it is done: call it as soon as they asked; never ask them yourself."""
    if not (token := _token(runtime)):
        return {"error": NO_ACCOUNT}
    try:
        if service == "music_room":
            innohassle.cancel_music_room(token, int(booking_id))
        else:
            innohassle.cancel_room(token, booking_id)
    except ValueError:
        return {"done": False, "error": "No such music room booking: take its `booking_id` from get_my_schedule."}
    except innohassle.ServiceError as e:
        return _refused(e, "The music room" if service == "music_room" else "The room booking service")
    return {"done": True, "cancelled": {"service": service, "booking_id": booking_id}, "note": "Cancelled: tell the asker."}


ACCOUNT_TOOLS = [get_my_schedule, get_free_rooms, book_music_room, book_room, enroll_in_event, cancel_booking]


# ---- what the user is asked to approve -------------------------------------------------------------------------------


def _russian(state) -> bool:
    """The helper's question is in the user's language: is it Russian?"""
    question = next((str(m.content) for m in state.get("messages", []) if isinstance(m, HumanMessage)), "")
    letters = [c for c in question if c.isalpha()]
    return not letters or sum("Ѐ" <= c <= "ӿ" for c in letters) * 2 >= len(letters)


def _when(start: datetime, end: datetime | None, ru: bool) -> str:
    day = f"{WEEKDAYS_RU[start.weekday()]}, {start.day} {MONTHS_RU[start.month - 1]}" if ru else start.strftime("%a, %d %b")
    return f"{day}, {start:%H:%M}" + (f"–{end:%H:%M}" if end else "")


def _context_token(runtime) -> str | None:
    token = getattr(getattr(runtime, "context", None), "innohassle_token", None)
    return token.get_secret_value() if token else None


def _describe_music_room(tool_call, state, runtime) -> str:
    a, ru = BookMusicRoomArgs.model_validate(tool_call["args"]), _russian(state)
    when = _when(_at(a.day, a.time_from), _at(a.day, a.time_to), ru)
    return f"Забронировать музыкальную комнату (спорткомплекс) на {when}." if ru else f"Book the music room (sports complex) for {when}."


def _describe_room(tool_call, state, runtime) -> str:
    a, ru = BookRoomArgs.model_validate(tool_call["args"]), _russian(state)
    name = a.room_id
    try:
        token = _context_token(runtime)
        found = next((r for r in innohassle.bookable_rooms(token) if r["id"] == a.room_id), None) if token else None
        name = (found or {}).get("ru_title" if ru else "title") or name
    except innohassle.ServiceError:
        pass
    when = _when(_at(a.day, a.time_from), _at(a.day, a.time_to), ru)
    return f"Забронировать {name} на {when}: «{a.title}»." if ru else f"Book {name} for {when}: “{a.title}”."


def _describe_enrol(tool_call, state, runtime) -> str:
    a, ru = EnrollArgs.model_validate(tool_call["args"]), _russian(state)
    try:
        data = innohassle.event(a.event_id).get("data") or {}
        locales = data.get("locales") or {}
        name = (locales.get("ru" if ru else "en") or next(iter(locales.values()), {})).get("name") or a.event_id
        start = _local(data["starts_at"])
        what = f"«{name}» ({_when(start, None, ru)}, {(data.get('location') or {}).get('display_name') or '—'})"
    except (innohassle.ServiceError, KeyError, StopIteration):
        what = a.event_id
    if ru:
        return f"Отменить вашу запись на {what}." if a.leave else f"Записать вас на {what}."
    return f"Cancel your enrolment in {what}." if a.leave else f"Enrol you in {what}."


def _describe_cancel(tool_call, state, runtime) -> str:
    a, ru = CancelBookingArgs.model_validate(tool_call["args"]), _russian(state)
    when = None
    try:
        token = _context_token(runtime)
        now = _now()
        if token and a.service == "music_room":
            b = next((b for b in innohassle.my_music_room_bookings(token) if str(b["id"]) == a.booking_id), None)
            when = b and _when(_local(b["time_start"]), _local(b["time_end"]), ru)
        elif token:
            b = next((b for b in innohassle.my_room_bookings(token, now - timedelta(days=1), now + timedelta(days=60))
                      if b.get("outlook_booking_id") == a.booking_id), None)  # fmt: skip
            when = b and f"{b.get('room_id')}, {_when(_local(b['start']), _local(b['end']), ru)}: «{b.get('title')}»"
    except innohassle.ServiceError:
        pass
    if a.service == "music_room":
        return f"Отменить вашу бронь музыкальной комнаты: {when or a.booking_id}." if ru else f"Cancel your music room booking: {when or a.booking_id}."
    return f"Отменить вашу бронь аудитории: {when or a.booking_id}." if ru else f"Cancel your room booking: {when or a.booking_id}."


def _describe_removal(tool_call, state, runtime) -> str:
    a, ru = RemoveFromAiCalendarArgs.model_validate(tool_call["args"]), _russian(state)
    key, _ = calendar_key(runtime)
    event = personal_calendar.event_of(key, a.calendar_event_id) if key else None
    what = f"#{a.calendar_event_id}"
    if event is not None:
        start = event.starts_at.astimezone(settings.tz)
        when = _when(start, event.ends_at.astimezone(settings.tz) if event.ends_at else None, ru)
        what = f"«{event.title}» ({when.rsplit(', ', 1)[0] if event.all_day else when})"
    return f"Убрать из вашего AI-календаря: {what}." if ru else f"Remove from your AI Calendar: {what}."


def _describe_checkin(tool_call, state, runtime) -> str:
    a, ru = SportCheckinArgs.model_validate(tool_call["args"]), _russian(state)
    what = f"#{a.training_id}"
    try:
        token = sport_token(runtime)
        t = sport_api.training(token, a.training_id) if token else None
        if t:
            when = _when(_local(t["start"]), None if t.get("is_all_day") else _local(t["end"]), ru)
            place = (t.get("training_location") or {}).get("name")
            what = f"«{training_name(t)}» ({when.rsplit(', ', 1)[0] if t.get('is_all_day') else when}{', ' + place if place else ''})"
    except (innohassle.ServiceError, KeyError, ValueError):
        pass
    if ru:
        return f"Отменить вашу запись на тренировку {what}." if a.cancel else f"Записать вас на тренировку {what}."
    return f"Cancel your check-in to the training {what}." if a.cancel else f"Check you in to the training {what}."


def _gate(name: str, describe) -> dict:
    return {
        "allowed_decisions": ["approve", "reject"],
        "description": describe,
        "when": lambda request: _problem(name, request.tool_call["args"]) is None,
    }


# HumanInTheLoopMiddleware's `interrupt_on` (core._helper_tool): each action waits for the user's decision.
APPROVAL = {
    "book_music_room": _gate("book_music_room", _describe_music_room),
    "book_room": _gate("book_room", _describe_room),
    "enroll_in_event": _gate("enroll_in_event", _describe_enrol),
    "cancel_booking": _gate("cancel_booking", _describe_cancel),
    "remove_from_ai_calendar": _gate("remove_from_ai_calendar", _describe_removal),
    "sport_checkin": _gate("sport_checkin", _describe_checkin),
}
