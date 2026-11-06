"""Tools on the public data of InNoHassle that need no account: the courses and the rooms of the official timetable, and the
bookings of the music room. They are the campus helper's (and get_courses the docs helper's too: who teaches a course)."""

import re
from datetime import date, datetime, time, timedelta

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from catix.common.dates import ClockTime
from catix.innohassle import client as innohassle
from catix.innohassle import timetable
from catix.settings import settings

MAX_COURSES = 5  # with their instructors and classes; more are listed by name
MAX_LISTED = 25
MAX_TEACHERS = 5
MAX_WEEKLY = 14
MAX_MUSIC_DAYS = 7
DEFAULT_RANGE = timedelta(minutes=90)  # a pair of the timetable
MUSIC_ROOM = {
    "where": "the music room of the Innopolis sports complex",
    "how_to_book": "Register in the Telegram bot @InnoMusicRoomBot (https://telegram.me/InnoMusicRoomBot) first: it adds you to "
    "the access lists of the sports complex. The rules: https://innohassle.ru/music-room/instructions",
}


def _words(text: str | None) -> str:
    return " ".join(re.findall(r"\w+", (text or "").lower().replace("ё", "е")))


def _matches(query: str, *fields: str | None) -> bool:
    haystack = " " + " ".join(_words(f) for f in fields if f) + " "
    return all(f" {word}" in haystack for word in _words(query).split())


def _now() -> datetime:
    return datetime.now(settings.tz)


def _teacher(person: dict | None) -> dict | None:
    if not person:
        return None
    out = {"name": person.get("name_en"), "name_ru": (person.get("name_ru") or "").rstrip(" -") or None,
           "position": person.get("position"), "email": person.get("email"), "telegram": person.get("alias")}  # fmt: skip
    return {k: v for k, v in out.items() if v}


class GetCoursesArgs(BaseModel):
    query: str = Field(
        max_length=80,
        description="A course ('Operating Systems', 'Операционные системы', 'AWA') or a teacher's name in English or Russian "
        "('Zuev', 'Зуев'). Plain words, no group or year.",
    )


@tool(args_schema=GetCoursesArgs)
def get_courses(query: str) -> dict:
    """The courses of the current term from the university's official timetable: who teaches each (primary instructor, teaching
    assistants) with their emails and Telegram, its weekly lectures, tutorials and labs with rooms and groups, and the blocks
    of the term it runs in. A teacher's name gives the courses they teach. Also the dates of the term and of its blocks."""
    data = innohassle.timetable()
    today = _now().date()
    people = {p["id"]: p for p in data.get("instructors") or []}
    blocks = {b["id"]: b for b in data.get("term", {}).get("blocks") or []}
    term = data.get("term") or {}
    result: dict = {
        "term": {"name": term.get("name"), "semester": term.get("semester"),
                 "blocks": [{"name": b["name"], "from": b["start_date"], "to": b["end_date"]} for b in blocks.values()]},  # fmt: skip
    }
    teachers = [p for p in people.values() if _matches(query, p.get("name_en"), p.get("name_ru"), p.get("alias"), p.get("email"))]
    taught = {p["id"] for p in teachers}
    courses = [
        c for c in data.get("courses") or []
        if _matches(query, c.get("name"), c.get("name_ru"), c.get("short_name"), c.get("short_name_ru"))
        or taught & {i["id"] for i in c.get("instructors") or []}
    ]  # fmt: skip
    found = []
    for course in courses[:MAX_COURSES]:
        item = {
            "course": course["name"],
            "name_ru": course.get("name_ru"),
            "short_name": course.get("short_name"),
            "kind": course.get("section_code"),  # core, electives, english, ...
            "blocks": [blocks[b]["name"] for b in course.get("blocks") or [] if b in blocks] or None,
            "instructors": [
                {**(_teacher(people.get(i["id"])) or {"email": i["id"]}), "role": i.get("role")} for i in course.get("instructors") or []
            ],
            "weekly_classes": timetable.weekly_classes(data, course, today)[:MAX_WEEKLY],
        }
        found.append({k: v for k, v in item.items() if v})
    result["courses"] = found
    if len(courses) > MAX_COURSES:
        result["more_courses"] = [c["name"] for c in courses[MAX_COURSES:MAX_LISTED]]
        result["note"] = f"{len(courses)} courses match: the first {MAX_COURSES} in full; narrow the query for another."
    if teachers and len(teachers) <= MAX_TEACHERS:
        result["teachers"] = [
            {**(_teacher(p) or {}), "courses": [{"course": c["name"], "role": i.get("role")} for c in data.get("courses") or []
                                                for i in c.get("instructors") or [] if i["id"] == p["id"]]}  # fmt: skip
            for p in teachers
        ]
    if not courses and not teachers:
        result["note"] = "No course or teacher of this term's timetable matches: try the English name or the surname alone."
    return result


class GetRoomTimetableArgs(BaseModel):
    day: date | None = Field(None, description="YYYY-MM-DD, default today.")
    room: str | None = Field(None, max_length=20, description="A room number ('108', '313'). Omit to find the rooms without classes.")
    time_from: ClockTime | None = Field(None, description="HH:MM: the start of the time the rooms must be free (without `room`); default now.")
    time_to: ClockTime | None = Field(None, description="HH:MM: its end; default 90 minutes after time_from.")


def _room_id(text: str) -> str:
    match = re.search(r"\d{3}[a-zа-я]?", text.lower())
    return match.group(0) if match else text.strip()


@tool(args_schema=GetRoomTimetableArgs)
def get_room_timetable(
    day: date | None = None, room: str | None = None, time_from: time | None = None, time_to: time | None = None
) -> dict:
    """The classes in the university's lecture rooms on a day, by the official timetable with its reschedules: with `room`,
    what is in that room and when; without it, which rooms have no class between time_from and time_to, with their
    capacity. Only classes are counted, not events, meetings or a locked door."""
    data = innohassle.timetable()
    now = _now()
    day = day or now.date()
    rooms = {r["id"]: r for r in data.get("rooms") or []}
    people = {p["id"]: p for p in data.get("instructors") or []}
    classes = timetable.sessions_on(data, day)
    if room:
        wanted = _room_id(room)
        info = rooms.get(wanted)
        here = [s for s in classes if s.room == wanted]
        out = []
        for s in here:
            begin, end = datetime.combine(day, s.start, settings.tz), datetime.combine(day, s.end, settings.tz)
            item = {"time": f"{s.start:%H:%M}-{s.end:%H:%M}", "course": s.course, "kind": s.kind, "groups": list(s.audience),
                    "instructor": (people.get(s.instructor or "") or {}).get("name_en") or s.instructor,
                    "status": "finished" if end <= now else "now" if begin <= now else "upcoming", "notes": s.notes}  # fmt: skip
            out.append({k: v for k, v in item.items() if v})
        result = {"room": wanted, "date": day.strftime("%Y-%m-%d %a"), "now": now.strftime("%Y-%m-%d %H:%M"), "classes": out}
        if info:
            result |= {"name": info.get("name"), "capacity": info.get("capacity")}
        elif not here:
            result["note"] = f"Room {wanted} is not one of the timetable's rooms: {', '.join(sorted(rooms))}."
        return result
    start = time_from or (now.time().replace(second=0, microsecond=0) if day == now.date() else time(9, 0))
    end = time_to or (datetime.combine(day, start) + DEFAULT_RANGE).time()
    if end <= start:
        return {"error": "time_to must be after time_from."}
    busy = {s.room for s in classes if timetable.overlaps(s, start, end)}
    free = [{"room": r["id"], "name": r.get("name"), "capacity": r.get("capacity")}
            for r in rooms.values() if r["id"] not in busy and r["id"] != timetable.ONLINE]  # fmt: skip
    return {
        "date": day.strftime("%Y-%m-%d %a"),
        "range": f"{start:%H:%M}-{end:%H:%M}",
        "free_of_classes": sorted(free, key=lambda r: r["room"]),
        "with_classes": sorted(r for r in busy if r and r in rooms and r != timetable.ONLINE),
        "note": "Free of classes by the official timetable only: events, meetings and bookings are not counted, and a room may be locked.",
    }


class GetMusicRoomScheduleArgs(BaseModel):
    date_from: date | None = Field(None, description="YYYY-MM-DD, default today.")
    date_to: date | None = Field(None, description=f"YYYY-MM-DD inclusive, default date_from; at most {MAX_MUSIC_DAYS} days.")


@tool(args_schema=GetMusicRoomScheduleArgs)
def get_music_room_schedule(date_from: date | None = None, date_to: date | None = None) -> dict:
    """When the music room (in the sports complex) is booked on each day: the busy times; the rest of the day is free to
    book. And how one gets access to it and books it."""
    start = date_from or _now().date()
    end = min(date_to or start, start + timedelta(days=MAX_MUSIC_DAYS - 1))
    days = []
    for offset in range((end - start).days + 1):
        day = start + timedelta(days=offset)
        bookings = sorted(innohassle.music_room_bookings(day), key=lambda b: b["time_start"])
        busy = [f"{datetime.fromisoformat(b['time_start']):%H:%M}-{datetime.fromisoformat(b['time_end']):%H:%M}" for b in bookings]
        days.append({"date": day.strftime("%Y-%m-%d %a"), "booked": busy or "nothing booked"})
    return {"music_room": MUSIC_ROOM, "days": days, "now": _now().strftime("%Y-%m-%d %H:%M")}


CAMPUS_TOOLS = [get_courses, get_room_timetable, get_music_room_schedule]
