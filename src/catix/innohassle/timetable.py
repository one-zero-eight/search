"""The official timetable of the term (Schedule Assistant, client.timetable) read as classes on a day.

A course has components (lec, tut, lab, class), a component has sessions, and a session meets by a weekly pattern (a weekday,
a time, a room, an instructor) while it is `active` (a block of the term), or on the dates of its `dates_pattern`. An edit
of a weekly pattern changes one week of it (`select_week`, the Monday): it cancels the class, or moves it to another room,
time or day. The times carry a stray "Z" ("10:40:00Z" next to "09:00:00"): all of them are local time.
"""

from dataclasses import dataclass
from datetime import date, time, timedelta

WEEKDAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
KINDS = {"lec": "lecture", "tut": "tutorial", "lab": "lab", "class": "class"}
ONLINE = "ONLINE"


@dataclass(frozen=True, slots=True)
class Session:
    course: str
    short_name: str | None
    kind: str  # lecture, tutorial, lab, class
    day: date
    start: time
    end: time
    room: str | None  # a room id ("108"), ONLINE, or None when the timetable names none
    instructor: str | None  # the instructor's id (an email)
    audience: tuple[str, ...]  # the student groups (or an elective's code)
    notes: str | None = None


def clock(value: str | None) -> time | None:
    return time.fromisoformat(value.rstrip("Z")) if value else None


def _active(session: dict, day: date) -> bool:
    active = session.get("active")
    return not active or date.fromisoformat(active["start_date"]) <= day <= date.fromisoformat(active["end_date"])


def _weekly(course: dict, kind: str, session: dict, audience: tuple[str, ...], day: date) -> list[Session]:
    """The classes of a session's weekly patterns that fall on `day`, with the changes of their week."""
    out = []
    monday = day - timedelta(days=day.weekday())
    for pattern in session.get("weekly_pattern") or []:
        edit = next((e for e in pattern.get("edits") or [] if e.get("select_week") == monday.isoformat()), None) or {}
        if edit.get("cancel"):
            continue
        usual = monday + timedelta(days=WEEKDAYS.index(pattern["weekday"]))
        when = date.fromisoformat(edit["date"]) if edit.get("date") else usual
        if when != day or not _active(session, usual):
            continue
        start, end = clock(edit.get("start_time") or pattern["start_time"]), clock(edit.get("end_time") or pattern["end_time"])
        if start is None or end is None:
            continue
        out.append(
            Session(course["name"], course.get("short_name"), kind, day, start, end, edit.get("room") or pattern.get("room"),
                    edit.get("instructor") or pattern.get("instructor"), audience, edit.get("notes"))  # fmt: skip
        )
    return out


def _dated(course: dict, kind: str, session: dict, audience: tuple[str, ...], day: date) -> list[Session]:
    out = []
    for entry in session.get("dates_pattern") or []:
        start, end = clock(entry.get("start_time")), clock(entry.get("end_time"))
        if entry.get("date") != day.isoformat() or start is None or end is None:
            continue
        out.append(Session(course["name"], course.get("short_name"), kind, day, start, end, entry.get("room"),
                           entry.get("instructor"), audience, entry.get("notes")))  # fmt: skip
    return out


def sessions_on(data: dict, day: date) -> list[Session]:
    """Every class of the timetable on `day`, by start time."""
    found = []
    for course in data.get("courses") or []:
        for component in course.get("components") or []:
            kind = KINDS.get(component.get("tag"), component.get("tag") or "class")
            for session in component.get("sessions") or []:
                audience = tuple(session.get("audience") or component.get("audience") or ())
                found += _weekly(course, kind, session, audience, day) + _dated(course, kind, session, audience, day)
    return sorted(found, key=lambda s: (s.start, s.room or "", s.course))


def weekly_classes(data: dict, course: dict, day: date) -> list[dict]:
    """The usual week of a course as it is around `day`: kind, weekday, time, room and groups of each of its weekly classes
    whose session is active then (an edit of one week is not shown)."""
    seen, out = set(), []
    for component in course.get("components") or []:
        kind = KINDS.get(component.get("tag"), component.get("tag") or "class")
        for session in component.get("sessions") or []:
            if not _active(session, day):
                continue
            audience = tuple(session.get("audience") or component.get("audience") or ())
            for pattern in session.get("weekly_pattern") or []:
                start, end = clock(pattern.get("start_time")), clock(pattern.get("end_time"))
                if start is None or end is None:
                    continue
                key = (kind, pattern["weekday"], start, pattern.get("room"), audience)
                if key in seen:
                    continue
                seen.add(key)
                out.append({"kind": kind, "weekday": pattern["weekday"].capitalize(), "time": f"{start:%H:%M}-{end:%H:%M}",
                            "room": pattern.get("room"), "groups": list(audience)})  # fmt: skip
    out.sort(key=lambda c: (WEEKDAYS.index(c["weekday"].upper()), c["time"]))
    return out


def overlaps(session: Session, start: time, end: time) -> bool:
    return session.start < end and start < session.end
