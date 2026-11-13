"""Calendar mutations: real SQL in a session-local temporary table, never live personal_events.

Run DB cases with CALENDAR_TEST_DATABASE_URL pointing at a disposable PostgreSQL instance.
DATABASE_URL='' keeps the repository's session teardown away from the application database.
"""

import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import psycopg
import pytest
from psycopg.rows import dict_row

from catix import personal_calendar
from catix.db import pg
from catix.settings import settings


@pytest.fixture(autouse=True)
def no_application_database(monkeypatch):
    def forbidden():
        pytest.fail("Calendar actions must not connect to the application database")

    monkeypatch.setattr(pg, "connection", forbidden)


@pytest.fixture
def calendar_db(monkeypatch):
    url = os.environ.get("CALENDAR_TEST_DATABASE_URL")
    if not url:
        pytest.skip("CALENDAR_TEST_DATABASE_URL is not set (use a disposable PostgreSQL instance)")
    # Read only this table's DDL, not the schema's destructive migrations/extensions.
    schema = Path(__file__).parents[1].joinpath("db/schema.sql").read_text()
    ddl = schema[schema.index("CREATE TABLE IF NOT EXISTS personal_events ("):schema.index("-- Events the agent offered")]
    ddl = ddl.replace("CREATE TABLE IF NOT EXISTS personal_events", "CREATE TEMP TABLE personal_events")
    with psycopg.connect(url, row_factory=dict_row, autocommit=True) as conn:
        conn.execute(ddl)
        conn.commit()
        assert conn.execute("SELECT 'personal_events'::regclass::oid = 'pg_temp.personal_events'::regclass::oid AS isolated").fetchone()["isolated"]

        @contextmanager
        def connection():
            with conn.transaction():
                yield conn

        monkeypatch.setattr(pg, "connection", connection)
        yield conn


def at(day=20, hour=10):
    return datetime(2099, 11, day, hour, tzinfo=settings.tz)


def test_add_event_persists_manual_event_and_returns_readback(calendar_db):
    event = personal_calendar.add_event(
        "ih:alice", title="  Exam  ", starts_at=at(), ends_at=at(hour=11), all_day=False, room="  108  "
    )
    assert isinstance(event, personal_calendar.PersonalEvent)
    assert event.id > 0
    assert (event.title, event.starts_at, event.ends_at, event.all_day, event.room) == ("Exam", at(), at(hour=11), False, "108")
    assert event.source_url is None and event.source_note is None
    assert personal_calendar.event_of("ih:alice", event.id) == event
    assert personal_calendar.event_of("ih:bob", event.id) is None


def test_repeated_add_preserves_existing_details_and_provenance(calendar_db):
    original = personal_calendar.add_event("ih:alice", title="Exam", starts_at=at(), ends_at=at(hour=11), all_day=False, room="108")
    calendar_db.execute(
        "UPDATE personal_events SET source_url = %s, source_note = %s WHERE id = %s",
        ("https://t.me/c/1/2", "Original announcement", original.id),
    )
    repeated = personal_calendar.add_event("ih:alice", title=" Exam ", starts_at=at(), all_day=True, room="different")
    assert repeated.id == original.id
    assert (repeated.ends_at, repeated.all_day, repeated.room) == (at(hour=11), False, "108")
    assert (repeated.source_url, repeated.source_note) == ("https://t.me/c/1/2", "Original announcement")
    assert calendar_db.execute("SELECT count(*) AS n FROM personal_events").fetchone()["n"] == 1
    # The same title and instant in another account is an independent event.
    other = personal_calendar.add_event("ih:bob", title="Exam", starts_at=at(), all_day=False)
    assert other.id != original.id


def test_update_replaces_only_owned_event_details_clearing_stale_provenance(calendar_db):
    original = personal_calendar.add_event("ih:alice", title="Exam", starts_at=at(), ends_at=at(hour=11), all_day=False, room="108")
    calendar_db.execute(
        "UPDATE personal_events SET source_url = %s, source_note = %s WHERE id = %s",
        ("https://t.me/c/1/2", "Original announcement", original.id),
    )
    replacement = {"title": "  New exam  ", "starts_at": at(21), "all_day": True}
    assert personal_calendar.update_event("ih:bob", original.id, **replacement) is None
    assert personal_calendar.update_event("ih:alice", original.id + 100, **replacement) is None
    assert personal_calendar.event_of("ih:alice", original.id).title == "Exam"
    updated = personal_calendar.update_event("ih:alice", original.id, **replacement)
    assert (updated.id, updated.title, updated.starts_at, updated.all_day) == (original.id, "New exam", at(21), True)
    assert updated.ends_at is None and updated.room is None  # replacement clears omitted optional fields
    assert updated.source_url is None and updated.source_note is None
    assert personal_calendar.event_of("ih:alice", original.id) == updated


def test_update_refuses_duplicate_without_changing_either_event(calendar_db):
    original = personal_calendar.add_event("ih:alice", title="Exam", starts_at=at(), all_day=False, room="108")
    duplicate = personal_calendar.add_event("ih:alice", title="Other", starts_at=at(21), all_day=False)
    with pytest.raises(ValueError, match="already exists"):
        personal_calendar.update_event("ih:alice", original.id, title="Other", starts_at=at(21), all_day=False)
    assert personal_calendar.event_of("ih:alice", original.id) == original
    assert personal_calendar.event_of("ih:alice", duplicate.id) == duplicate
    # Repeating a successful update is fine; so is matching someone else's event.
    assert personal_calendar.update_event("ih:alice", duplicate.id, title="Other", starts_at=at(21), all_day=False) == duplicate
    personal_calendar.add_event("ih:bob", title="Foreign", starts_at=at(22), all_day=False)
    updated = personal_calendar.update_event("ih:alice", original.id, title="Foreign", starts_at=at(22), all_day=False)
    assert updated.id == original.id


@pytest.mark.parametrize("change", [
    {"title": "   "}, {"title": "x" * 301}, {"starts_at": datetime(2099, 11, 20, 10)},
    {"ends_at": datetime(2099, 11, 20, 11)}, {"ends_at": at()}, {"ends_at": at(hour=9)}, {"starts_at": None},
    {"user_key": ""}, {"user_key": "ih:"}, {"user_key": "tg:123"}, {"user_key": "ih:   "},
])
@pytest.mark.parametrize("operation", [personal_calendar.add_event, personal_calendar.update_event])
def test_backend_rejects_invalid_data_before_opening_database(change, operation):
    values: dict = {"user_key": "ih:alice", "title": "Exam", "starts_at": at(), "all_day": False}
    values.update(change)
    if operation is personal_calendar.update_event:
        values["event_id"] = 1
    with pytest.raises(ValueError):
        operation(**values)


def runtime(**changes):
    from pydantic import SecretStr

    context = {"innohassle_id": "alice", "innohassle_token": SecretStr("synthetic-site-token"), "user_telegram_id": None}
    context.update(changes)
    return SimpleNamespace(context=SimpleNamespace(**context))


def test_add_tool_saves_timed_event_in_local_timezone(calendar_db):
    from catix.agent import calendar_tools as tools

    assert hasattr(tools, "add_to_ai_calendar"), "explicit add tool is missing"
    result = tools.add_to_ai_calendar.func(
        runtime=runtime(), title="  Exam  ", day="2099-11-20", start_time="10:00", end_time="11:00", room=" 108 "
    )
    assert result["done"] is True
    event = personal_calendar.event_of("ih:alice", result["event"]["calendar_event_id"])
    assert event is not None
    assert (event.title, event.starts_at, event.ends_at, event.room, event.all_day) == ("Exam", at(), at(hour=11), "108", False)
    assert tools.add_to_ai_calendar in tools.CALENDAR_TOOLS


def test_update_tool_replaces_owned_event_and_returns_persisted_values(calendar_db):
    from catix.agent import calendar_tools as tools

    assert hasattr(tools, "update_ai_calendar"), "explicit update tool is missing"
    event = personal_calendar.add_event("ih:alice", title="Exam", starts_at=at(), ends_at=at(hour=11), all_day=False, room="108")
    args = {"calendar_event_id": event.id, "title": "  Updated  ", "day": "2099-11-21", "all_day": True}
    result = tools.update_ai_calendar.func(runtime=runtime(), **args)
    assert result["done"] is True
    updated = personal_calendar.event_of("ih:alice", event.id)
    assert updated is not None
    assert (updated.title, updated.starts_at, updated.ends_at, updated.room, updated.all_day) == ("Updated", at(21, 9), None, None, True)
    assert result["event"] == tools.calendar_item(updated)
    assert tools.update_ai_calendar in tools.CALENDAR_TOOLS
    assert tools.update_ai_calendar.func(runtime=runtime(innohassle_id="bob"), **args)["done"] is False
    assert personal_calendar.event_of("ih:alice", event.id) == updated


@pytest.mark.parametrize("tool_name", ["add_to_ai_calendar", "update_ai_calendar"])
@pytest.mark.parametrize("change", [
    {"start_time": None}, {"title": "  "}, {"title": "x" * 301}, {"day": "2099-02-30"},
    {"end_time": "10:00"}, {"end_time": "09:00"}, {"start_time": "25:00"},
    {"all_day": True}, {"all_day": True, "start_time": None, "end_time": "11:00"},
    {"start_time": "10:00+02:00"},
])
def test_direct_tool_calls_validate_before_any_lookup_or_write(monkeypatch, tool_name, change):
    from catix.agent import calendar_tools as tools

    def forbidden(*args, **kwargs):
        pytest.fail("Invalid arguments reached account lookup or database writes")

    for name in ("account_key", "telegram_key", "add_event", "update_event"):
        monkeypatch.setattr(personal_calendar, name, forbidden)
    args: dict = {"title": "Exam", "day": "2099-11-20", "start_time": "10:00"}
    if tool_name == "update_ai_calendar":
        args["calendar_event_id"] = 1
    args.update(change)
    result = getattr(tools, tool_name).func(runtime=runtime(user_telegram_id=42), **args)
    assert result["done"] is False and result["error"]


def test_calendar_read_preserves_raw_timestamps_and_all_day_flag():
    from catix.agent import calendar_tools as tools

    start = at().replace(second=12, microsecond=345678)
    end = at(hour=11).replace(second=23, microsecond=456789)
    for all_day in (False, True):
        event = personal_calendar.PersonalEvent(7, "Exam", start, end, all_day, "108")
        item = tools.calendar_item(event)
        assert item["all_day"] is all_day
        assert item["starts_at"] == start.isoformat()
        assert item["ends_at"] == end.isoformat()
    event = personal_calendar.PersonalEvent(8, "Deadline", at(), None, True, None)
    assert tools.calendar_item(event)["ends_at"] is None


@pytest.mark.parametrize("tool_name", ["add_to_ai_calendar", "update_ai_calendar", "remove_from_ai_calendar"])
@pytest.mark.parametrize("context", [
    {"innohassle_token": None}, {"innohassle_id": None}, {"innohassle_id": ""}, {"innohassle_id": "  "},
    {"innohassle_token": None, "innohassle_id": None, "user_telegram_id": 42},
])
def test_mutations_require_site_account_and_user_token(monkeypatch, tool_name, context):
    from catix.agent import calendar_tools as tools

    def forbidden(*args, **kwargs):
        pytest.fail("An unauthenticated mutation reached account lookup or database writes")

    for name in ("account_key", "telegram_key", "add_event", "update_event", "delete_event"):
        monkeypatch.setattr(personal_calendar, name, forbidden)
    args: dict = {"title": "Exam", "day": "2099-11-20", "start_time": "10:00"}
    if tool_name == "remove_from_ai_calendar":
        args = {}
    if tool_name != "add_to_ai_calendar":
        args["calendar_event_id"] = 1
    result = getattr(tools, tool_name).func(runtime=runtime(**context), **args)
    assert result["done"] is False and result["error"]


@pytest.mark.parametrize("tool_name", ["update_ai_calendar", "remove_from_ai_calendar"])
@pytest.mark.parametrize("event_id", [0, -1, "not-an-id"])
def test_direct_mutation_rejects_invalid_id_before_lookup(monkeypatch, tool_name, event_id):
    from catix.agent import calendar_tools as tools

    def forbidden(*args, **kwargs):
        pytest.fail("Invalid id reached account lookup")

    monkeypatch.setattr(personal_calendar, "account_key", forbidden)
    args = {"calendar_event_id": event_id}
    if tool_name == "update_ai_calendar":
        args.update(title="Exam", day="2099-11-20", start_time="10:00")
    result = getattr(tools, tool_name).func(runtime=runtime(), **args)
    assert result["done"] is False and result["error"]


def test_noop_storage_update_and_strict_tool_refusal_preserve_source_and_precision(calendar_db):
    from catix.agent import calendar_tools as tools

    start, end = at().replace(second=12, microsecond=345678), at(hour=11).replace(second=23, microsecond=456789)
    event = personal_calendar.add_event("ih:alice", title="Exam", starts_at=start, ends_at=end, all_day=False, room="108")
    calendar_db.execute("UPDATE personal_events SET source_url = %s, source_note = %s WHERE id = %s",
                        ("https://t.me/c/1/2", "Original announcement", event.id))
    original = personal_calendar.event_of("ih:alice", event.id)
    result = tools.update_ai_calendar.func(runtime=runtime(), calendar_event_id=event.id, title=" Exam ",
                                          day=start.date(), start_time=start.time(), end_time=end.time(), room="108")
    assert result["done"] is False and "HH:MM" in result["error"]
    assert personal_calendar.event_of("ih:alice", event.id) == original
    saved = personal_calendar.update_event("ih:alice", event.id, title=" Exam ", starts_at=start, ends_at=end, all_day=False, room="108")
    assert saved == original and saved is not None
    assert tools.calendar_item(saved)["source"] == "https://t.me/c/1/2"


def test_add_tool_all_day_uses_configured_calendar_button_time(calendar_db, monkeypatch):
    from datetime import time

    from catix.agent import calendar_tools as tools

    monkeypatch.setattr(settings, "changes_default_time", time(8, 30))
    result = tools.add_to_ai_calendar.func(runtime=runtime(), title="Deadline", day="2099-11-20", all_day=True)
    assert result["done"] is True
    saved = personal_calendar.event_of("ih:alice", result["event"]["calendar_event_id"])
    assert saved is not None and saved.all_day
    assert saved.starts_at == at(hour=8).replace(minute=30) and saved.ends_at is None
    assert "time" not in result["event"]


def test_add_tool_duplicate_returns_existing_details_not_requested_changes(calendar_db):
    from catix.agent import calendar_tools as tools

    original = personal_calendar.add_event("ih:alice", title="Exam", starts_at=at(), ends_at=at(hour=11), all_day=False, room="108")
    result = tools.add_to_ai_calendar.func(runtime=runtime(), title="Exam", day="2099-11-20", start_time="10:00", room="different")
    assert result["done"] is True and result["event"] == tools.calendar_item(original)
    assert calendar_db.execute("SELECT count(*) AS n FROM personal_events").fetchone()["n"] == 1


def test_update_tool_collision_returns_failure_without_writes(calendar_db):
    from catix.agent import calendar_tools as tools

    original = personal_calendar.add_event("ih:alice", title="Exam", starts_at=at(), all_day=False)
    duplicate = personal_calendar.add_event("ih:alice", title="Other", starts_at=at(21), all_day=False)
    result = tools.update_ai_calendar.func(runtime=runtime(), calendar_event_id=original.id, title="Other", day="2099-11-21", start_time="10:00")
    assert result["done"] is False and "already exists" in result["error"]
    assert personal_calendar.event_of("ih:alice", original.id) == original
    assert personal_calendar.event_of("ih:alice", duplicate.id) == duplicate


@pytest.mark.parametrize("tool_name", ["add_to_ai_calendar", "update_ai_calendar"])
def test_no_success_reported_without_saved_event_readback(calendar_db, monkeypatch, tool_name):
    from catix.agent import calendar_tools as tools

    args: dict = {"title": "New", "day": "2099-11-20", "start_time": "10:00"}
    if tool_name == "update_ai_calendar":
        original = personal_calendar.add_event("ih:alice", title="Exam", starts_at=at(), all_day=False)
        args["calendar_event_id"] = original.id
    monkeypatch.setattr(personal_calendar, "event_of", lambda *args: None)
    result = getattr(tools, tool_name).func(runtime=runtime(), **args)
    assert result["done"] is None and result["outcome"] == "unknown" and "read back" in result["error"]
    # The write happened; the tool must not invent a successful readback.
    assert calendar_db.execute("SELECT title FROM personal_events").fetchone()["title"] == "New"


def test_action_schemas_are_explicit_and_reject_extra_operations():
    from pydantic import ValidationError

    from catix.agent import calendar_tools as tools

    for schema in (tools.AddToAiCalendarArgs, tools.UpdateAiCalendarArgs):
        values: dict = {"title": "Exam", "day": "2099-11-20", "start_time": "10:00"}
        if schema is tools.UpdateAiCalendarArgs:
            values["calendar_event_id"] = 1
        args = schema.model_validate(values)
        assert args.all_day is False
        for extra in ({"recurrence": "weekly"}, {"notify": True}, {"user_key": "ih:bob"}):
            with pytest.raises(ValidationError):
                schema.model_validate({**values, **extra})
        clock = schema.model_json_schema()["properties"]["start_time"]
        assert clock["anyOf"][0]["pattern"] == "^([01][0-9]|2[0-3]):[0-5][0-9]$"
