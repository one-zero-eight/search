"""The official timetable read as the classes of a day (innohassle/timetable.py) and the campus tools on it
(agent/campus_tools.py), on a timetable made up here."""

from datetime import date, time

import pytest

from catix.agent import campus_tools
from catix.innohassle import client as innohassle
from catix.innohassle import timetable

BLOCK_1 = {"start_date": "2026-08-24", "end_date": "2026-10-25"}
BLOCK_2 = {"start_date": "2026-10-26", "end_date": "2026-12-27"}
MONDAY, NEXT_MONDAY = date(2026, 11, 2), date(2026, 11, 9)

DATA = {
    "term": {"name": "Fall 2026", "semester": {"start_date": "2026-08-24", "end_date": "2026-12-27"},
             "blocks": [{"id": "block_1", "name": "Блок 1", **BLOCK_1}, {"id": "block_2", "name": "Блок 2", **BLOCK_2}]},
    "rooms": [{"id": "108", "name": "Lecture Room 108", "capacity": 312}, {"id": "313", "name": "Room 313", "capacity": 30},
              {"id": "ONLINE", "name": "Online", "capacity": None}],
    "instructors": [{"id": "e.zuev@innopolis.ru", "name_en": "Evgeny Zuyev", "name_ru": "Зуев Евгений Александрович", "alias": "@zouev",
                     "email": "e.zuev@innopolis.ru", "position": "Full Professor"}],
    "courses": [
        {"name": "Compiler Construction", "short_name": "CC", "name_ru": "Конструирование компиляторов", "section_code": "core",
         "blocks": ["block_2"], "instructors": [{"id": "e.zuev@innopolis.ru", "role": "Primary Instructor"}],
         "components": [
             {"tag": "lec", "audience": ["B24-CSE-01"], "sessions": [{"audience": [], "active": BLOCK_2, "dates_pattern": [], "weekly_pattern": [
                 {"weekday": "MONDAY", "start_time": "09:00:00", "end_time": "10:30:00Z", "room": "108", "instructor": "e.zuev@innopolis.ru",
                  "edits": [{"select_week": "2026-11-09", "cancel": True}]},
             ]}]},
             {"tag": "lab", "audience": ["B24-CSE-01"], "sessions": [{"audience": [], "active": BLOCK_2, "weekly_pattern": [
                 {"weekday": "MONDAY", "start_time": "14:20:00Z", "end_time": "15:50:00Z", "room": "313", "instructor": None,
                  "edits": [{"select_week": "2026-11-02", "room": "108"}]},
             ], "dates_pattern": [{"date": "2026-11-10", "start_time": "12:40:00", "end_time": "14:10:00", "room": "313",
                                   "instructor": "e.zuev@innopolis.ru", "notes": "extra lab"}]}]},
         ]},
        {"name": "Old Course", "short_name": "OC", "section_code": "core", "blocks": ["block_1"], "instructors": [],
         "components": [{"tag": "lec", "audience": ["B25-X"], "sessions": [{"active": BLOCK_1, "weekly_pattern": [
             {"weekday": "MONDAY", "start_time": "09:00:00", "end_time": "10:30:00", "room": "313", "edits": None}]}]}]},
    ],
}


def test_a_day_has_its_classes_with_the_changes_of_its_week():
    monday = timetable.sessions_on(DATA, MONDAY)
    assert [(s.course, s.kind, f"{s.start:%H:%M}", s.room) for s in monday] == [
        ("Compiler Construction", "lecture", "09:00", "108"),
        ("Compiler Construction", "lab", "14:20", "108"),  # moved to 108 that week
    ], "a session of block 1 is over by November"
    assert [s.kind for s in timetable.sessions_on(DATA, NEXT_MONDAY)] == ["lab"], "the lecture is cancelled that week"
    assert monday[1].audience == ("B24-CSE-01",), "the component's groups when the session names none"


def test_a_class_on_a_date_of_its_own_is_there_that_day_only():
    tuesday = timetable.sessions_on(DATA, date(2026, 11, 10))
    assert [(s.kind, s.start, s.room, s.notes) for s in tuesday] == [("lab", time(12, 40), "313", "extra lab")]
    assert timetable.sessions_on(DATA, date(2026, 11, 17)) == []


@pytest.fixture(autouse=True)
def fake_timetable(monkeypatch):
    monkeypatch.setattr(innohassle, "timetable", lambda: DATA)


def test_a_room_has_the_classes_of_the_day_and_the_free_rooms_have_none():
    room = campus_tools.get_room_timetable.invoke({"room": "ауд. 108", "day": MONDAY.isoformat()})
    assert room["capacity"] == 312 and [c["time"] for c in room["classes"]] == ["09:00-10:30", "14:20-15:50"]
    assert room["classes"][0]["instructor"] == "Evgeny Zuyev"
    free = campus_tools.get_room_timetable.invoke({"day": MONDAY.isoformat(), "time_from": "14:00", "time_to": "15:00"})
    assert [r["room"] for r in free["free_of_classes"]] == ["313"] and free["with_classes"] == ["108"]  # never "ONLINE"


def test_a_teacher_gives_their_courses_and_a_course_its_teachers():
    by_teacher = campus_tools.get_courses.invoke({"query": "Зуев"})
    assert by_teacher["teachers"][0]["telegram"] == "@zouev"
    assert [c["course"] for c in by_teacher["teachers"][0]["courses"]] == ["Compiler Construction"]
    course = campus_tools.get_courses.invoke({"query": "компиляторов"})["courses"][0]
    assert course["instructors"][0] | {} == {"name": "Evgeny Zuyev", "name_ru": "Зуев Евгений Александрович", "position": "Full Professor",
                                             "email": "e.zuev@innopolis.ru", "telegram": "@zouev", "role": "Primary Instructor"}
    assert course["blocks"] == ["Блок 2"] and {c["kind"] for c in course["weekly_classes"]} == {"lecture", "lab"}
    assert "note" in campus_tools.get_courses.invoke({"query": "квантовая гравитация"})


def test_a_group_the_asker_did_not_name_is_not_taken_for_theirs(monkeypatch):
    """Told that the asker's group was not known, the helper took B26-CSE-01 from an example and gave its timetable as theirs."""
    from types import SimpleNamespace

    from langchain_core.messages import HumanMessage

    from catix.agent import tools
    from catix.agent.tools import AgentContext

    asked = []
    monkeypatch.setattr(tools, "_find_group", lambda group: asked.append(group) or [{"name": "B26-CSE-01", "alias": "b26-cse-01"}])
    monkeypatch.setattr(tools.innohassle, "group_schedule_ics", lambda alias: "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n")

    def schedule(question: str, group: str, own: str | None = None) -> dict:
        runtime = SimpleNamespace(context=AgentContext(study_group=own), state={"messages": [HumanMessage(question)]})
        return tools.get_schedule.func(runtime, group=group)

    assert schedule("что у меня на этой неделе", "B26-CSE-01") == {"error": tools.GROUP_UNKNOWN} and not asked
    assert "error" not in schedule("расписание b26 cse 01 на неделю", "B26-CSE-01"), "named in the question, in other spelling"
    assert "error" not in schedule("что у меня на этой неделе", "B26-CSE-01", own="B26-CSE-01"), "the asker's own group"
