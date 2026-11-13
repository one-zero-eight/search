"""Stored event intervals agree across ICS, agent reads and approval; no display-only duration."""
from contextlib import nullcontext
from datetime import date, datetime

from icalendar import Calendar
import pytest

from catix import personal_calendar
from catix.agent.calendar_tools import calendar_item
from catix.settings import settings
from tests.test_calendar_approval import calendar  # noqa: F401 -- synthetic storage fixture
from tests.test_calendar_actions import calendar_db  # noqa: F401 -- disposable PostgreSQL fixture


def event(**changes):
    values = {"id": 274, "title": "тест1 по дискре", "starts_at": datetime(2026, 11, 9, 9, tzinfo=settings.tz),
              "ends_at": None, "all_day": False, "room": None}
    return personal_calendar.PersonalEvent(**{**values, **changes})


def feed(monkeypatch, row):
    monkeypatch.setattr(personal_calendar.pg, "connection", lambda: nullcontext(None))
    monkeypatch.setattr(personal_calendar.pg, "rows", lambda *a: [row])
    return Calendar.from_ical(personal_calendar.ics("ih:synthetic")).walk("VEVENT")[0]


def test_trace_unknown_end_remains_unknown_in_ics_and_agent(monkeypatch):
    row = event()
    exported = feed(monkeypatch, row)
    assert exported.decoded("DTSTART") == row.starts_at
    assert "DTEND" not in exported and "DURATION" not in exported
    assert calendar_item(row)["ends_at"] is None
    assert row.ends_at is None


def test_explicit_interval_is_exported_without_replacement(monkeypatch):
    row = event(ends_at=datetime(2026, 11, 9, 10, 30, tzinfo=settings.tz))
    assert row.ends_at is not None
    exported = feed(monkeypatch, row)
    assert exported.decoded("DTEND") == row.ends_at
    assert calendar_item(row)["ends_at"] == row.ends_at.isoformat()


def test_all_day_exports_a_real_date_not_a_ninety_minute_class(monkeypatch):
    row = event(all_day=True)
    exported = feed(monkeypatch, row)
    assert type(exported.decoded("DTSTART")) is date
    assert exported.decoded("DTSTART") == date(2026, 11, 9)
    assert exported.decoded("DTEND") == date(2026, 11, 10)
    assert exported["DTSTART"].params["VALUE"] == "DATE"
    assert exported["DTEND"].params["VALUE"] == "DATE"


@pytest.mark.parametrize("decision", ["approve", "reject"])
@pytest.mark.parametrize("language", ["ru", "en"])
@pytest.mark.parametrize("asynchronous", [False, True])
def test_new_event_proposes_ninety_minutes_before_consent(calendar, decision, language, asynchronous):
    import asyncio
    from langchain_core.messages import AIMessage, HumanMessage
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.types import Command
    from catix.agent.core import build_agent
    from tests.test_calendar_approval import SITE, call
    from tests.test_roles import ScriptedModel

    args = {"title": "тест1 по дискре", "day": "2026-11-09", "start_time": "09:00", "proposed_duration_minutes": 90}
    saver = InMemorySaver()
    model = ScriptedModel(responses=[call("add_to_ai_calendar", args, "add"), AIMessage(content="Обработано.")])
    graph = build_agent(model, guardrail=False, checkpointer=saver)
    config = {"configurable": {"thread_id": "explicit-calendar-duration"}}
    def invoke(value):
        return asyncio.run(graph.ainvoke(value, config, context=SITE)) if asynchronous else graph.invoke(value, config, context=SITE)
    invoke({"messages": [HumanMessage("Добавь тест1 по дискре 9 ноября в 9 утра." if language == "ru" else "Add a test on November 9 at 9 am.")]})
    paused = graph.get_state(config)
    assert len(paused.interrupts) == 1 and calendar.writes == []
    description = paused.interrupts[0].value["action_requests"][0]["description"]
    assert "09:00" in description and "10:30" in description and "90" in description
    assert ("предложен" if language == "ru" else "suggested") in description.lower()
    graph = build_agent(model, guardrail=False, checkpointer=saver)
    invoke(Command(resume={paused.interrupts[0].id: {"decisions": [{"type": decision}]}}))
    if decision == "reject":
        assert calendar.writes == []
    else:
        assert len(calendar.writes) == 1
        saved = calendar.writes[0][2]
        assert saved["starts_at"] == datetime(2026, 11, 9, 9, tzinfo=settings.tz)
        assert saved["ends_at"] == datetime(2026, 11, 9, 10, 30, tzinfo=settings.tz)


def test_default_duration_crosses_midnight_with_full_dates_in_approval():
    from langchain_core.messages import HumanMessage
    from catix.agent.calendar_approval import _describe_calendar
    from catix.agent.calendar_tools import AddToAiCalendarArgs

    args = {"title": "Late meeting", "day": "2026-12-31", "start_time": "23:30", "proposed_duration_minutes": 90}
    description = _describe_calendar({"name": "add_to_ai_calendar", "args": args}, {"messages": [HumanMessage("Add a late meeting")]}, None)
    values = AddToAiCalendarArgs.model_validate(args).event_values()
    assert values["ends_at"] == datetime(2027, 1, 1, 1, tzinfo=settings.tz)
    assert all(value in description for value in ("2026", "2027", "23:30", "01:00", "90"))


def test_update_does_not_backfill_an_unknown_end_without_an_explicit_interval():
    from catix.agent.calendar_tools import UpdateAiCalendarArgs
    args = UpdateAiCalendarArgs.model_validate({"calendar_event_id": 274, "title": "renamed", "day": "2026-11-09", "start_time": "09:00"})
    assert args.event_values()["ends_at"] is None


def test_sql_keeps_previous_unknown_duration_but_not_past_all_day_or_finished_events(calendar_db):
    start = datetime(2026, 11, 9, tzinfo=settings.tz)
    end = datetime(2026, 11, 10, tzinfo=settings.tz)
    old = datetime(2026, 11, 8, 9, tzinfo=settings.tz)
    for title, begins, finishes, all_day in [
        ("Unknown ongoing", old, None, False),
        ("Past all day", old, None, True),
        ("Today all day", start.replace(hour=9), None, True),
        ("Ended at boundary", old, start, False),
        ("Overnight", old, start.replace(hour=1), False),
    ]:
        personal_calendar.add_event("ih:synthetic", title=title, starts_at=begins, ends_at=finishes, all_day=all_day)
    found = personal_calendar.between("ih:synthetic", start, end)
    assert {row.title for row in found} == {"Unknown ongoing", "Today all day", "Overnight"}
    unknown = next(row for row in found if row.title == "Unknown ongoing")
    assert unknown.ends_at is None
    assert personal_calendar.between("ih:other", start, end) == []


def test_sql_all_day_display_hour_does_not_hide_early_morning(calendar_db):
    start = datetime(2026, 11, 9, tzinfo=settings.tz)
    row = personal_calendar.add_event("ih:synthetic", title="Day off", starts_at=start.replace(hour=9), all_day=True)
    assert personal_calendar.between("ih:synthetic", start, start.replace(hour=8)) == [row]


@pytest.mark.parametrize("all_day", [False, True])
def test_sql_export_does_not_change_existing_unknown_end(calendar_db, all_day):
    row = personal_calendar.add_event("ih:synthetic", title="Existing", starts_at=datetime(2026, 11, 9, 9, tzinfo=settings.tz),
                                      ends_at=None, all_day=all_day)
    exported = Calendar.from_ical(personal_calendar.ics("ih:synthetic")).walk("VEVENT")[0]
    assert ("DTEND" in exported) is all_day
    assert personal_calendar.event_of("ih:synthetic", row.id) == row


def test_multi_day_all_day_agenda_matches_exclusive_dates_in_ics(monkeypatch):
    from catix.agent.schedule_tools import merge_schedule
    row = event(all_day=True, ends_at=datetime(2026, 11, 11, 9, tzinfo=settings.tz))
    exported = feed(monkeypatch, row)
    merged = merge_schedule(["2026-11-09", "2026-11-11"],
                            {"range": ["2026-11-09", "2026-11-11"], "schedule": [], "bookings": []},
                            {"range": ["2026-11-09", "2026-11-11"], "events": [calendar_item(row)]})
    actual = merged["events"][0]
    assert actual["starts_at"] == "2026-11-09T00:00:00+03:00"
    assert actual["ends_at"] == "2026-11-11T00:00:00+03:00"
    assert exported.decoded("DTSTART") == date(2026, 11, 9)
    assert exported.decoded("DTEND") == date(2026, 11, 11)


def test_all_day_normalization_does_not_repair_a_reversed_stored_interval():
    from catix.agent.schedule_tools import merge_schedule
    row = event(all_day=True, ends_at=datetime(2026, 11, 8, 9, tzinfo=settings.tz))
    merged = merge_schedule(["2026-11-09", "2026-11-09"],
                            {"range": ["2026-11-09", "2026-11-09"], "schedule": [], "bookings": []},
                            {"range": ["2026-11-09", "2026-11-09"], "events": [calendar_item(row)]})
    assert merged["complete"] is False and merged["not_read"]


def test_partly_verified_music_windows_remain_answer_evidence():
    from catix.agent import core
    result = {"range": ["2026-11-09", "2026-11-09"], "duration_minutes": None, "rules": {"step_minutes": 30},
              "service_checked_at": "2026-11-08T09:12:13+03:00", "complete": False, "truncated": False,
              "not_read": ["The end of test1 is unknown."], "total": 2, "excluded": [],
              "available": [{"start": "07:00", "end": "09:00", "starts_at": "2026-11-09T07:00:00+03:00",
                             "ends_at": "2026-11-09T09:00:00+03:00", "latest_start": "08:30", "max_duration_minutes": 120}],
              "unverified": [{"start": "20:30", "end": "21:00", "reason": "schedule_unverified"}]}
    assert core._read_parts("get_my_available_music_windows", result) is not None


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_overnight_suggested_event_can_be_renamed_without_losing_its_end(calendar, decision):
    from langgraph.types import Command
    from tests.test_calendar_approval import run_action, SITE
    row = event(id=5, title="Late meeting", starts_at=datetime(2026, 12, 31, 23, 30, tzinfo=settings.tz),
                ends_at=datetime(2027, 1, 1, 1, tzinfo=settings.tz))
    calendar.events["ih:u1", 5] = row
    args = {"calendar_event_id": 5, "title": "Renamed", "day": "2026-12-31", "start_time": "23:30",
            "end_day": "2027-01-01", "end_time": "01:00"}
    graph, config, _ = run_action("update_ai_calendar", args)
    pending = graph.get_state(config).interrupts
    assert len(pending) == 1 and calendar.writes == []
    description = pending[0].value["action_requests"][0]["description"]
    assert "2026" in description and "2027" in description and "предложенная" not in description
    graph.invoke(Command(resume={pending[0].id: {"decisions": [{"type": decision}]}}), config, context=SITE)
    saved = calendar.events["ih:u1", 5]
    assert saved.starts_at == row.starts_at and saved.ends_at == row.ends_at
    assert saved.title == ("Renamed" if decision == "approve" else "Late meeting")


@pytest.mark.parametrize("change", [{"end_day": "2026-11-08", "end_time": "10:00"},
                                   {"end_day": "2026-11-10"},
                                   {"all_day": True, "start_time": None, "end_day": "2026-11-10"}])
def test_end_day_requires_valid_explicit_timed_interval(change):
    from pydantic import ValidationError
    from catix.agent.calendar_tools import AddToAiCalendarArgs
    with pytest.raises(ValidationError):
        AddToAiCalendarArgs.model_validate({"title": "Exam", "day": "2026-11-09", "start_time": "09:00", **change})


def test_legacy_or_explicit_unknown_end_action_is_not_silently_changed(calendar):
    from langgraph.types import Command
    from tests.test_calendar_approval import run_action, SITE
    # An old pending action has no new proposal flag. Its user approved no end,
    # so a newer deployment must not silently turn that consent into 90 minutes.
    args = {"title": "Legacy", "day": "2026-11-09", "start_time": "09:00"}
    graph, config, _ = run_action("add_to_ai_calendar", args)
    pending = graph.get_state(config).interrupts[0]
    assert "без времени окончания" in pending.value["action_requests"][0]["description"]
    graph.invoke(Command(resume={pending.id: {"decisions": [{"type": "approve"}]}}), config, context=SITE)
    assert calendar.writes[0][2]["ends_at"] is None


def test_approved_suggestion_matches_real_sql_agent_read_and_ics(calendar_db):
    from langgraph.types import Command
    from tests.test_calendar_approval import run_action, SITE
    args = {"title": "Test", "day": "2026-11-09", "start_time": "09:00", "proposed_duration_minutes": 90}
    graph, config, _ = run_action("add_to_ai_calendar", args)
    pending = graph.get_state(config).interrupts[0]
    assert calendar_db.execute("SELECT count(*) AS n FROM personal_events").fetchone()["n"] == 0
    assert "10:30" in pending.value["action_requests"][0]["description"]
    graph.invoke(Command(resume={pending.id: {"decisions": [{"type": "approve"}]}}), config, context=SITE)
    rows = personal_calendar.between("ih:u1", datetime(2026, 11, 9, tzinfo=settings.tz), datetime(2026, 11, 10, tzinfo=settings.tz))
    assert len(rows) == 1 and rows[0].ends_at == datetime(2026, 11, 9, 10, 30, tzinfo=settings.tz)
    exported = Calendar.from_ical(personal_calendar.ics("ih:u1")).walk("VEVENT")[0]
    assert exported.decoded("DTEND") == rows[0].ends_at
    assert datetime.fromisoformat(calendar_item(rows[0])["ends_at"]) == rows[0].ends_at


def test_button_suggestion_and_legacy_offer_are_persisted_without_click_time_defaults(calendar_db):
    import json
    calendar_db.execute("CREATE TEMP TABLE calendar_proposals (id text PRIMARY KEY, event jsonb NOT NULL, created_at timestamptz DEFAULT now())")
    raw = {"title": "Proposed", "starts_at": "2026-11-09T09:00:00+03:00", "ends_at": None, "all_day": False}
    [(ident, shown)] = personal_calendar.propose([raw])
    assert shown["end_suggested"] is True and shown["ends_at"] == "2026-11-09T10:30:00+03:00"
    assert calendar_db.execute("SELECT count(*) AS n FROM personal_events").fetchone()["n"] == 0
    personal_calendar.add_proposal("ih:synthetic", ident)
    calendar_db.execute("INSERT INTO calendar_proposals(id,event) VALUES (%s,%s::jsonb)", ("legacy", json.dumps({**raw, "title": "Legacy"})))
    personal_calendar.add_proposal("ih:synthetic", "legacy")
    saved = calendar_db.execute("SELECT title,ends_at FROM personal_events ORDER BY title").fetchall()
    assert saved[0]["title"] == "Legacy" and saved[0]["ends_at"] is None
    assert saved[1]["title"] == "Proposed" and saved[1]["ends_at"] == datetime(2026, 11, 9, 10, 30, tzinfo=settings.tz)
