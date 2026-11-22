"""Button consent uses the interval shown, never a click-time duration default."""
import asyncio
import json
from contextlib import contextmanager
from unittest.mock import Mock

import pytest

from catix import personal_calendar


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
