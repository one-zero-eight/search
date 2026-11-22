"""Button consent uses the interval shown, never a click-time duration default."""
import asyncio
import json
from contextlib import contextmanager
from datetime import date, datetime, time
from unittest.mock import Mock

import pytest

from catix import personal_calendar
from catix.db.rows import ChangeView


@pytest.fixture
def storage(monkeypatch):
    conn = Mock()
    offers = {}

    def execute(sql, args=()):
        if "INSERT INTO calendar_proposals" in sql:
            offers[args[0]] = json.loads(args[1])
        return Mock()

    conn.execute.side_effect = execute

    @contextmanager
    def connection():
        yield conn

    monkeypatch.setattr(personal_calendar.pg, "connection", connection)
    monkeypatch.setattr(personal_calendar.pg, "scalar", lambda conn, sql, args: offers.get(args[0]))
    return conn, offers


def event(**overrides):
    return {"title": "Study", "starts_at": "2026-11-08T23:30:00+03:00", "ends_at": None, "all_day": False, **overrides}


def test_new_timed_offer_shows_and_saves_exact_suggested_end_only_after_click(storage):
    conn, offers = storage
    original = event()
    [(pid, proposed)] = personal_calendar.propose([original])
    assert proposed["ends_at"] == "2026-11-09T01:00:00+03:00"
    assert proposed["end_suggested"] is True
    assert original["ends_at"] is None
    assert offers[pid] == proposed
    assert not any("personal_events" in call.args[0] for call in conn.execute.call_args_list)
    assert personal_calendar.add_proposal("ih:owner", pid) == "Study"
    args = conn.execute.call_args.args[1]
    assert args[3] == proposed["ends_at"]
    assert args[6] is None  # No fabricated source attribution.
    assert personal_calendar.PROPOSED_DURATION_MINUTES == 90


@pytest.mark.parametrize("overrides", [{"all_day": True}, {"ends_at": "2026-11-09T02:15:00+03:00"}])
def test_all_day_and_known_end_are_not_suggested(storage, overrides):
    original = event(**overrides)
    [(pid, proposed)] = personal_calendar.propose([original])
    assert proposed["ends_at"] == original["ends_at"]
    assert proposed["end_suggested"] is False
    personal_calendar.add_proposal("ih:owner", pid)
    assert storage[0].execute.call_args.args[1][3] == original["ends_at"]


def test_old_offer_without_marker_does_not_gain_an_end_on_click(storage):
    conn, offers = storage
    offers["legacy"] = event()
    personal_calendar.add_proposal("ih:owner", "legacy")
    assert conn.execute.call_args.args[1][3] is None


@pytest.mark.parametrize("end", ["bad", "", "2026-11-08T23:30:00+03:00", "2026-11-08T23:00:00+03:00", "2026-11-09T01:00:00"])
def test_malformed_end_refused_before_proposal_io(monkeypatch, end):
    connect = Mock(side_effect=AssertionError("No DB access allowed"))
    monkeypatch.setattr(personal_calendar.pg, "connection", connect)
    with pytest.raises(ValueError):
        personal_calendar.propose([event(ends_at=end)])
    connect.assert_not_called()


@pytest.mark.parametrize("overrides", [{"ends_at": "bad"}, {"end_suggested": True}, {"starts_at": "2026-11-08T23:30:00"}])
def test_invalid_stored_offer_refused_before_insert(storage, overrides):
    conn, offers = storage
    offers["invalid"] = event(**overrides)
    with pytest.raises(ValueError):
        personal_calendar.add_proposal("ih:owner", "invalid")
    conn.execute.assert_not_called()


def test_api_offer_marker_is_boolean_with_false_default():
    from catix.api.schemas import CalendarEventOffer

    assert CalendarEventOffer(id="legacy", **event()).end_suggested is False
    assert CalendarEventOffer(id="suggested", **event(end_suggested=True)).model_dump()["end_suggested"] is True


def test_api_offer_pipeline_keeps_visible_suggestion_and_serialized_interval(storage, monkeypatch):
    from catix.api import ask

    monkeypatch.setattr(ask.calendar_events, "extract", lambda answer, **kwargs: [event()])
    [offer] = asyncio.run(ask.calendar_offers("Study on 8 November at 23:30", "chat"))
    payload = offer.model_dump(mode="json")
    assert payload["end_suggested"] is True
    assert payload["ends_at"] == "2026-11-09T01:00:00+03:00"
    assert storage[1][payload["id"]]["ends_at"] == payload["ends_at"]


def change(**overrides):
    return ChangeView(
        **{
            "id": 15, "message_id": 20, "kind": "announcement", "subject": "Study",
            "starts_at": datetime.fromisoformat(event()["starts_at"]), "ends_at": None,
            "all_day": False, "room": None, "summary": "Study", "link": None,
            "chat_link": None, "chat_title": "Group", "text": "Study at 23:30",
            "date": datetime.fromisoformat(event()["starts_at"]), "sender_name": None,
            "chat_id": 7, "decided_at": None, "created_at": datetime.fromisoformat(event()["starts_at"]),
            "status": "pending", "group_code": "all", **overrides,
        }
    )


@pytest.mark.parametrize("kind,earlier", [("announcement", None), ("reschedule", None), ("reschedule", 42)])
def test_worker_card_then_click_saves_displayed_suggestion(storage, monkeypatch, kind, earlier):
    from catix.worker import changes

    conn, _ = storage
    item = change(kind=kind)
    monkeypatch.setattr(changes.pg, "row", lambda *args: item)
    monkeypatch.setattr(changes, "_earlier_event", lambda *args: earlier)
    changes._save_suggestion(storage[0], item.id, item.kind, item.starts_at, item.ends_at, item.all_day)
    assert not any("personal_events" in call.args[0] for call in conn.execute.call_args_list)
    changes.add_to_calendar("ih:owner", item.id, chat_ids={7})
    call = conn.execute.call_args
    end = call.args[1][1 if earlier else 3]
    assert end == datetime.fromisoformat("2026-11-09T01:00:00+03:00")
    assert item.ends_at is None


def test_click_without_saved_suggestion_keeps_unknown_end(storage, monkeypatch):
    from catix.worker import changes

    item = change()
    monkeypatch.setattr(changes.pg, "row", lambda *args: item)
    changes.add_to_calendar("ih:owner", item.id, chat_ids={7})
    assert storage[0].execute.call_args.args[1][3] is None


@pytest.mark.parametrize("overrides", [{"all_day": True}, {"ends_at": datetime.fromisoformat("2026-11-09T03:00:00+03:00")}, {"kind": "cancel"}, {"kind": "room_change"}])
def test_worker_does_not_suggest_for_all_day_known_end_or_non_time_changes(storage, monkeypatch, overrides):
    from catix.worker import changes

    item = change(**overrides)
    monkeypatch.setattr(changes.pg, "row", lambda *args: item)
    monkeypatch.setattr(changes, "_earlier_event", lambda *args: None)
    changes._save_suggestion(storage[0], item.id, item.kind, item.starts_at, item.ends_at, item.all_day)
    assert storage[1] == {}
    changes.add_to_calendar("ih:owner", item.id, chat_ids={7})
    assert storage[0].execute.call_args.args[1][3] == item.ends_at


@pytest.mark.parametrize("kind", ["cancel", "room_change"])
def test_worker_existing_event_non_time_change_preserves_semantics(storage, monkeypatch, kind):
    from catix.worker import changes

    item = change(kind=kind)
    monkeypatch.setattr(changes.pg, "row", lambda *args: item)
    monkeypatch.setattr(changes, "_earlier_event", lambda *args: 42)
    changes._save_suggestion(storage[0], item.id, item.kind, item.starts_at, item.ends_at, item.all_day)
    changes.add_to_calendar("ih:owner", item.id, chat_ids={7})
    sql = storage[0].execute.call_args.args[0]
    assert "DELETE FROM personal_events" in sql if kind == "cancel" else "SET room =" in sql
    assert "ends_at" not in sql


def test_worker_invalid_explicit_end_is_not_replaced_with_suggestion(storage, monkeypatch):
    from catix.worker import changes

    item = change(ends_at=datetime.fromisoformat("2026-11-08T22:00:00+03:00"))
    monkeypatch.setattr(changes.pg, "row", lambda *args: item)
    with pytest.raises(ValueError):
        changes.add_to_calendar("ih:owner", item.id, chat_ids={7})
    storage[0].execute.assert_not_called()


def test_worker_extraction_does_not_downgrade_invalid_end_to_unknown():
    from catix.worker import changes

    with pytest.raises(ValueError):
        changes.when(changes.Change(is_change=True, kind="announcement", day=date(2026, 11, 8), start_time=time(15), end_time=time(14), subject=None, room=None, summary=""))


@pytest.mark.parametrize("kind", ["cancel", "room_change"])
def test_worker_non_time_change_keeps_existing_extraction_semantics(kind):
    from catix.worker import changes

    _, end, _ = changes.when(changes.Change(is_change=True, kind=kind, day=date(2026, 11, 8), start_time=time(15), end_time=time(14), subject=None, room=None, summary=""))
    assert end is None


def test_saved_worker_proposal_is_not_accepted_as_an_answer_offer(storage):
    from catix.worker import changes

    item = change()
    changes._save_suggestion(storage[0], item.id, item.kind, item.starts_at, item.ends_at, item.all_day)
    storage[0].execute.reset_mock()
    assert personal_calendar.add_proposal("ih:owner", "change:15") is None
    storage[0].execute.assert_not_called()


