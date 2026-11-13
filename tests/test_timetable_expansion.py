"""Public timetable expansion matches Schedule Assistant's concrete occurrences."""

from datetime import date, time

import pytest

from catix.innohassle import timetable


def schedule(*, pattern=None, **series):
    slot = {
        "weekday": "MONDAY", "start_time": "09:00:00", "end_time": "10:30:00Z",
        "room": "108", "instructor": "a@iu.ru", **(pattern or {}),
    }
    return {
        "term": {"semester": {"start_date": "2026-09-01", "end_date": "2026-09-30"},
                 "starting_day": "MONDAY"},
        "courses": [{"name": "Course", "components": [{"tag": "lec", "audience": ["G1"],
                     "sessions": [{"weekly_pattern": [slot], **series}]}]}],
    }


@pytest.mark.parametrize("source,destination", [("2026-09-07", "2026-09-15"), ("2026-09-21", "2026-09-08")])
def test_moves_are_selected_by_destination_even_across_weeks(source, destination):
    data = schedule(pattern={"edits": [{"select_week": source, "date": destination,
                                        "start_time": "12:40:00", "room": "313"}]})
    assert timetable.sessions_on(data, date.fromisoformat(source)) == []
    moved = timetable.sessions_on(data, date.fromisoformat(destination))
    assert [(item.day, item.start, item.room) for item in moved] == [
        (date.fromisoformat(destination), time(12, 40), "313"),
    ]


@pytest.mark.parametrize("starting_day,anchor,selected,source,destination,skipped", [
    ("MONDAY", "2026-09-23", "2026-09-09", "2026-09-07", "2026-09-15", "2026-09-14"),
    ("SUNDAY", "2026-09-20", "2026-09-06", "2026-09-07", "2026-09-15", "2026-09-14"),
])
def test_week_identity_and_alternation_use_term_starting_day(starting_day, anchor, selected, source, destination, skipped):
    data = schedule(pattern={"alternation": {"anchor_week": anchor}, "edits": [
        {"select_week": selected, "date": destination},
        {"select_week": skipped, "date": "2026-09-16"},
    ]})
    data["term"]["starting_day"] = starting_day
    assert timetable.sessions_on(data, date.fromisoformat(source)) == []
    assert len(timetable.sessions_on(data, date.fromisoformat(destination))) == 1
    assert timetable.sessions_on(data, date(2026, 9, 16)) == [], "an edit cannot create an off-phase occurrence"
    assert len(timetable.sessions_on(data, date(2026, 9, 21))) == 1
    assert timetable.sessions_on(data, date(2026, 9, 28)) == []


@pytest.mark.parametrize("dated", [False, True])
@pytest.mark.parametrize("override,expected", [({}, "Bring laptop"), ({"notes": None}, "Bring laptop"),
                                               ({"notes": ""}, ""), ({"notes": "Read chapter 2"}, "Read chapter 2")])
def test_notes_inherit_only_when_missing_or_null(dated, override, expected):
    if dated:
        data = schedule(weekly_pattern=[], notes="Bring laptop", dates_pattern=[{
            "date": "2026-09-07", "start_time": "09:00:00", "end_time": "10:30:00", **override,
        }])
    else:
        data = schedule(notes="Bring laptop", pattern={"edits": [{"select_week": "2026-09-07", **override}]})
    assert timetable.sessions_on(data, date(2026, 9, 7))[0].notes == expected


def test_unedited_weekly_occurrence_inherits_series_notes():
    assert timetable.sessions_on(schedule(notes="Bring laptop"), date(2026, 9, 7))[0].notes == "Bring laptop"


@pytest.mark.parametrize("instructor", ["b@iu.ru", ["a@iu.ru", "b@iu.ru"], [], "", None])
def test_weekly_instructor_override_preserves_string_list_and_explicit_empty(instructor):
    data = schedule(pattern={"instructor": ["a@iu.ru", "c@iu.ru"],
                             "edits": [{"select_week": "2026-09-07", "instructor": instructor, "room": ""}]})
    meeting = timetable.sessions_on(data, date(2026, 9, 7))[0]
    assert meeting.instructor == (instructor if instructor is not None else ["a@iu.ru", "c@iu.ru"])
    assert meeting.room == ""


@pytest.mark.parametrize("instructor", ["a@iu.ru", ["a@iu.ru", "b@iu.ru"], [], None])
def test_dated_instructor_preserves_public_shape(instructor):
    data = schedule(weekly_pattern=[], dates_pattern=[{
        "date": "2026-09-07", "start_time": "09:00:00", "end_time": "10:30:00", "instructor": instructor,
    }])
    assert timetable.sessions_on(data, date(2026, 9, 7))[0].instructor == instructor


@pytest.mark.parametrize("audience,active,expected", [
    ([], None, ["2026-09-07", "2026-09-14", "2026-09-21", "2026-09-28"]),
    (["unknown"], None, ["2026-09-07", "2026-09-14", "2026-09-21", "2026-09-28"]),
    (["G1"], None, ["2026-09-07", "2026-09-14", "2026-09-21"]),
    (["G2"], None, ["2026-09-14", "2026-09-21", "2026-09-28"]),
    (["G1", "G2"], None, ["2026-09-14", "2026-09-21"]),
    (["G3"], None, ["2026-08-31", "2026-09-07", "2026-09-14", "2026-09-21", "2026-09-28", "2026-10-05"]),
    (["G3", "unknown"], None, ["2026-09-07", "2026-09-14", "2026-09-21", "2026-09-28"]),
    (["G1"], {"start_date": "2026-09-14", "end_date": "2026-10-05"}, ["2026-09-14", "2026-09-21"]),
    (["G1"], {"start_date": "2026-09-22", "end_date": "2026-10-05"}, []),
])
def test_weekly_window_is_audience_intersection_with_optional_active(audience, active, expected):
    data = schedule(active=active)
    data["courses"][0]["components"][0]["audience"] = audience
    data["term"]["sections"] = [{"programs": [
        {"code": "P1", "groups": ["G1"], "semester": {"start_date": "2026-09-07", "end_date": "2026-09-21"}},
        {"code": "P2", "tracks": [{"code": "T2", "name": "Track", "groups": ["G2"]}],
         "semester": {"start_date": "2026-09-14", "end_date": "2026-09-28"}},
        {"code": "P3", "groups": ["G3"], "semester": {"start_date": "2026-08-31", "end_date": "2026-10-05"}},
    ]}]
    days = ["2026-08-31", "2026-09-07", "2026-09-14", "2026-09-21", "2026-09-28", "2026-10-05"]
    assert [day for day in days if timetable.sessions_on(data, date.fromisoformat(day))] == expected
    assert [day for day in days if timetable.weekly_classes(data, data["courses"][0], date.fromisoformat(day))] == expected


@pytest.mark.parametrize("audience", ["G2", "@P2", "@P2/T2", "@P2/Track", " @P2/T2 "])
def test_session_audience_and_program_track_selectors_choose_program_semester(audience):
    data = schedule(audience=[audience])
    data["term"]["sections"] = [{"programs": [{
        "code": "P2", "tracks": [{"code": "T2", "name": "Track", "groups": ["G2"]}],
        "semester": {"start_date": "2026-09-14", "end_date": "2026-09-21"},
    }]}]
    assert timetable.sessions_on(data, date(2026, 9, 7)) == []
    assert timetable.sessions_on(data, date(2026, 9, 14))[0].audience == (audience,)
    assert len(timetable.sessions_on(data, date(2026, 9, 21))) == 1
    assert timetable.sessions_on(data, date(2026, 9, 28)) == []


def test_term_days_filter_weekly_source_not_concrete_dates_or_destinations():
    data = schedule(pattern={"edits": [{"select_week": "2026-09-07", "date": "2026-09-08"}]},
                    dates_pattern=[{"date": "2026-09-08", "start_time": "12:40:00", "end_time": "14:10:00"}])
    data["term"]["days"] = ["TUESDAY"]
    assert [item.start for item in timetable.sessions_on(data, date(2026, 9, 8))] == [time(12, 40)]
    assert timetable.weekly_classes(data, data["courses"][0], date(2026, 9, 7)) == []
    data["term"]["days"] = ["MONDAY"]
    assert [item.start for item in timetable.sessions_on(data, date(2026, 9, 8))] == [time(9), time(12, 40)]
    data["term"]["days"] = []
    assert [item.start for item in timetable.sessions_on(data, date(2026, 9, 8))] == [time(9), time(12, 40)]


@pytest.mark.parametrize("active", [None, {"start_date": "2026-09-07", "end_date": "2026-09-21"}])
def test_weekly_window_checks_source_not_moved_destination(active):
    data = schedule(active=active, pattern={"edits": [
        {"select_week": "2026-09-07", "date": "2026-10-06"},
        {"select_week": "2026-10-05", "date": "2026-09-08"},
    ]})
    assert len(timetable.sessions_on(data, date(2026, 10, 6))) == 1
    assert timetable.sessions_on(data, date(2026, 9, 8)) == [], "out-of-window sources cannot be revived by edits"


def test_explicit_dates_remain_visible_even_outside_an_empty_teaching_window():
    data = schedule(active={"start_date": "2026-10-01", "end_date": "2026-10-05"}, dates_pattern=[{
        "date": "2026-11-01", "start_time": "09:00:00", "end_time": "10:30:00", "notes": "legacy date",
    }])
    assert [item.notes for item in timetable.sessions_on(data, date(2026, 11, 1))] == ["legacy date"]


def test_two_source_weeks_moved_to_same_day_remain_two_occurrences():
    data = schedule(pattern={"edits": [
        {"select_week": "2026-09-07", "date": "2026-09-21"},
        {"select_week": "2026-09-14", "date": "2026-09-21"},
        {"select_week": "2026-09-21", "cancel": True},
    ]})
    assert len(timetable.sessions_on(data, date(2026, 9, 21))) == 2


def test_in_week_move_is_not_emitted_twice_and_cancel_wins():
    data = schedule(pattern={"edits": [{"select_week": "2026-09-09", "date": "2026-09-08"}]})
    assert len(timetable.sessions_on(data, date(2026, 9, 8))) == 1
    data["courses"][0]["components"][0]["sessions"][0]["weekly_pattern"][0]["edits"][0]["cancel"] = True
    assert timetable.sessions_on(data, date(2026, 9, 8)) == []


def test_nonoverlapping_audience_semesters_have_no_weekly_occurrences():
    data = schedule(audience=["G1", "G2"])
    data["term"]["sections"] = [{"programs": [
        {"code": "P1", "groups": ["G1"], "semester": {"start_date": "2026-09-01", "end_date": "2026-09-10"}},
        {"code": "P2", "groups": ["G2"], "semester": {"start_date": "2026-09-14", "end_date": "2026-09-30"}},
    ]}]
    assert timetable.sessions_on(data, date(2026, 9, 7)) == []
    assert timetable.sessions_on(data, date(2026, 9, 14)) == []


def test_program_without_override_uses_default_and_course_blocks_do_not_clip():
    data = schedule()
    data["term"]["sections"] = [{"programs": [{"code": "P1", "groups": ["G1"], "semester": None}]}]
    data["term"]["blocks"] = [{"id": "old", "start_date": "2026-08-01", "end_date": "2026-08-31"}]
    data["courses"][0]["blocks"] = ["old"]
    assert timetable.sessions_on(data, date(2026, 8, 31)) == []
    assert len(timetable.sessions_on(data, date(2026, 9, 7))) == 1
    assert timetable.sessions_on(data, date(2026, 10, 5)) == []
