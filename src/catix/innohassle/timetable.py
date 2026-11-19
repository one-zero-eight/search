"""The official timetable of the term (Schedule Assistant, client.timetable) read as classes on a day.

A course has components (lec, tut, lab, class) containing session series. Weekly patterns use the audience's semester
intersected with optional `active` dates; explicit `dates_pattern` meetings remain visible without clipping. Edits select
a source week using any date in it, normalized by term.starting_day, and may move its occurrence across weeks/windows.
Alternation repeats every two weeks in both directions from anchor_week. The times carry a stray "Z"
("10:40:00Z" next to "09:00:00"): all of them are local time.
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
    instructor: str | list[str] | None  # instructor id(s), including co-teaching
    audience: tuple[str, ...]  # the student groups (or an elective's code)
    notes: str | None = None


def clock(value: str | None) -> time | None:
    return time.fromisoformat(value.rstrip("Z")) if value else None


def _window(data: dict, session: dict, audience: tuple[str, ...]) -> tuple[date, date]:
    """Inclusive intersection; program semesters replace, not intersect, the default."""
    term = data.get("term") or {}
    default = term.get("semester")
    by_audience = {}
    for section in term.get("sections") or []:
        for program in section.get("programs") or []:
            semester = program.get("semester") or default
            by_audience[f"@{program['code']}"] = semester
            for group in program.get("groups") or []:
                by_audience[group] = semester
            for track in program.get("tracks") or []:
                by_audience[f"@{program['code']}/{track['code']}"] = semester
                by_audience[f"@{program['code']}/{track['name']}"] = semester
                for group in track.get("groups") or []:
                    by_audience[group] = semester
    windows = [by_audience.get(token.strip(), default) for token in audience] if audience else [default]
    windows.append(session.get("active"))
    return (
        max((date.fromisoformat(window["start_date"]) for window in windows if window), default=date.min),
        min((date.fromisoformat(window["end_date"]) for window in windows if window), default=date.max),
    )


def _week_start(day: date, starting_day: int) -> date:
    return day - timedelta(days=(day.weekday() - starting_day) % 7)


def _weekly(data: dict, course: dict, kind: str, session: dict, audience: tuple[str, ...], day: date) -> list[Session]:
    """Select by destination after checking source eligibility, without expanding the whole semester."""
    out = []
    first, last = _window(data, session, audience)
    term = data.get("term") or {}
    starting_day = WEEKDAYS.index(term.get("starting_day", "MONDAY"))
    target_week = _week_start(day, starting_day)
    for pattern in session.get("weekly_pattern") or []:
        if term.get("days") and pattern["weekday"] not in term["days"]:
            continue
        edits = {_week_start(date.fromisoformat(e["select_week"]), starting_day): e for e in pattern.get("edits") or []}
        alternation = pattern.get("alternation")
        anchor = _week_start(date.fromisoformat(alternation["anchor_week"]), starting_day) if alternation else None
        # Only the target week and edits landing on this day can contribute.
        weeks = {target_week} | {week for week, edit in edits.items() if edit.get("date") == day.isoformat()}
        for week in sorted(weeks):
            if anchor is not None and (week - anchor).days % 14:
                continue
            edit = edits.get(week, {})
            if edit.get("cancel"):
                continue
            usual = week + timedelta(days=(WEEKDAYS.index(pattern["weekday"]) - starting_day) % 7)
            when = date.fromisoformat(edit["date"]) if edit.get("date") else usual
            if when != day or not first <= usual <= last:
                continue
            start, end = clock(edit.get("start_time") or pattern["start_time"]), clock(edit.get("end_time") or pattern["end_time"])
            if start is None or end is None:
                continue
            notes = edit.get("notes") if edit.get("notes") is not None else session.get("notes", "")
            room = edit["room"] if edit.get("room") is not None else pattern.get("room")
            instructor = edit["instructor"] if edit.get("instructor") is not None else pattern.get("instructor")
            out.append(
                Session(course["name"], course.get("short_name"), kind, day, start, end, room,
                        instructor, audience, notes)  # fmt: skip
            )
    return out


def _dated(course: dict, kind: str, session: dict, audience: tuple[str, ...], day: date) -> list[Session]:
    # Upstream keeps stored concrete dates visible even outside teaching windows.
    out = []
    for entry in session.get("dates_pattern") or []:
        start, end = clock(entry.get("start_time")), clock(entry.get("end_time"))
        if entry.get("date") != day.isoformat() or start is None or end is None:
            continue
        notes = entry.get("notes") if entry.get("notes") is not None else session.get("notes", "")
        out.append(Session(course["name"], course.get("short_name"), kind, day, start, end, entry.get("room"),
                           entry.get("instructor"), audience, notes))  # fmt: skip
    return out


def sessions_on(data: dict, day: date) -> list[Session]:
    """Every class of the timetable on `day`, by start time."""
    found = []
    for course in data.get("courses") or []:
        for component in course.get("components") or []:
            kind = KINDS.get(component.get("tag"), component.get("tag") or "class")
            for session in component.get("sessions") or []:
                audience = tuple(session.get("audience") or component.get("audience") or ())
                found += _weekly(data, course, kind, session, audience, day) + _dated(course, kind, session, audience, day)
    return sorted(found, key=lambda s: (s.start, s.room or "", s.course))


def weekly_classes(data: dict, course: dict, day: date) -> list[dict]:
    """The usual week of a course as it is around `day`: kind, weekday, time, room and groups of each of its weekly classes
    whose teaching window includes `day` (one-week edits and alternation are not shown)."""
    seen, out = set(), []
    for component in course.get("components") or []:
        kind = KINDS.get(component.get("tag"), component.get("tag") or "class")
        for session in component.get("sessions") or []:
            audience = tuple(session.get("audience") or component.get("audience") or ())
            first, last = _window(data, session, audience)
            if not first <= day <= last:
                continue
            for pattern in session.get("weekly_pattern") or []:
                days = (data.get("term") or {}).get("days")
                if days and pattern["weekday"] not in days:
                    continue
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
