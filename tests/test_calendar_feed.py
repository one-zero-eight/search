"""The personal calendar of the HTTP API (api/users.py): the InNoHassle token of the user opens their calendar and adds to it,
no other token does. The tokens are signed here by a key of our own, put in place of InNoHassle's keys. The last tests use
the database: the events of the Telegram bot move to the InNoHassle account."""

import time
from datetime import datetime

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from catix import personal_calendar
from catix.api import ask
from catix.api.app import app
from catix.db import pg
from catix.innohassle import client as innohassle
from catix.innohassle import token as innohassle_token
from catix.settings import settings
from tests.test_api import FakeChats

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class Keys:
    def get_signing_keys(self):
        return [jwt.PyJWK.from_dict({**jwt.algorithms.RSAAlgorithm.to_jwk(KEY.public_key(), as_dict=True), "use": "sig", "kid": "public"})]


def token(key=KEY, **claims) -> str:
    """Like InNoHassle's: RS256 and no `kid` in the header."""
    return jwt.encode({"uid": "u1", "scope": "me", "exp": int(time.time()) + 3600, **claims}, key, algorithm="RS256")


@pytest.fixture
def accounts(monkeypatch):
    """The (InNoHassle id, Telegram id) of every request, without the database."""
    seen = []

    def account_key(innohassle_id, telegram_id=None):
        seen.append((innohassle_id, telegram_id))
        return f"ih:{innohassle_id}"

    monkeypatch.setattr(innohassle_token, "_keys", Keys())
    monkeypatch.setattr(personal_calendar, "account_key", account_key)
    monkeypatch.setattr(personal_calendar, "ics", lambda user_key: f"BEGIN:VCALENDAR\r\nX-USER:{user_key}\r\nEND:VCALENDAR\r\n")
    return seen


@pytest.fixture
def client(accounts):
    return TestClient(app)


def get(client, bearer: str | None):
    return client.get("/users/my-calendar.ics", headers={"Authorization": f"Bearer {bearer}"} if bearer else {})


def test_the_token_of_a_user_opens_the_calendar_of_their_account(client, accounts):
    resp = get(client, token(telegram_id=42))
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/calendar")
    assert "X-USER:ih:u1" in resp.text
    assert accounts == [("u1", 42)]  # the events the bot kept under the Telegram id move in


def test_no_token_or_a_foreign_signature_or_an_expired_token_opens_nothing(client):
    assert get(client, None).status_code == 401
    assert get(client, token(OTHER, telegram_id=42)).status_code == 401
    assert get(client, token(telegram_id=42, exp=int(time.time()) - 10)).status_code == 401
    assert get(client, "not-a-jwt").status_code == 401
    assert get(client, jwt.encode({"scope": "me", "exp": int(time.time()) + 3600}, KEY, algorithm="RS256")).status_code == 401


def test_an_account_without_telegram_or_email_has_a_calendar(client, accounts):
    resp = get(client, token())
    assert resp.status_code == 200 and "X-USER:ih:u1" in resp.text
    assert accounts == [("u1", None)]


def test_the_button_under_an_answer_adds_the_event_to_the_account(client, monkeypatch):
    added = []
    monkeypatch.setattr(personal_calendar, "add_proposal", lambda key, pid: added.append((key, pid)) or ("Экзамен" if pid == "p1" else None))
    headers = {"Authorization": f"Bearer {token(telegram_id=42)}"}
    resp = client.post("/users/my-calendar/events/p1", headers=headers)
    assert resp.status_code == 200 and resp.json() == {"proposal_id": "p1", "title": "Экзамен"}
    assert client.post("/users/my-calendar/events/gone", headers=headers).status_code == 404
    assert added == [("ih:u1", "p1"), ("ih:u1", "gone")]
    assert client.post("/users/my-calendar/events/p1").status_code == 401


def test_an_answer_offers_its_events_for_the_calendar(client, monkeypatch):
    async def _run(query, chat_id, user, events=None, decision=None):
        return "Экзамен 20 ноября в 10:00", [], [], None, "cp-1"

    event = {"title": "Экзамен", "starts_at": "2026-11-20T10:00:00+03:00", "ends_at": None, "all_day": False, "room": "108", "source_url": None}
    kept = FakeChats()
    monkeypatch.setattr(ask, "chats", kept)
    monkeypatch.setattr(ask.titles, "name", lambda question: None)
    monkeypatch.setattr(ask, "_run", _run)
    monkeypatch.setattr(ask.calendar_events, "extract", lambda answer: [event])
    monkeypatch.setattr(personal_calendar, "propose", lambda events: [("p1", e) for e in events])
    monkeypatch.setattr(innohassle_token, "claims", lambda t: {"uid": "u1", "email": "a@innopolis.university"})
    offers = client.post("/ask/", json={"query": "когда экзамен"}, headers={"Authorization": "Bearer x"}).json()["calendar_events"]
    assert [(o["id"], o["title"], o["room"]) for o in offers] == [("p1", "Экзамен", "108")]
    assert [o.id for o in kept.answers[0]["response"].calendar_events] == ["p1"]  # the chat's history shows them too


def test_an_answer_whose_events_cannot_be_read_still_comes(client, monkeypatch):
    async def _run(query, chat_id, user, events=None, decision=None):
        return "Экзамен 20 ноября", [], [], None, "cp-1"

    def broken(answer):
        raise RuntimeError("the model is down")

    monkeypatch.setattr(ask, "chats", FakeChats())
    monkeypatch.setattr(ask.titles, "name", lambda question: None)
    monkeypatch.setattr(ask, "_run", _run)
    monkeypatch.setattr(ask.calendar_events, "extract", broken)
    monkeypatch.setattr(innohassle_token, "claims", lambda t: {"uid": "u1", "email": "a@innopolis.university"})
    resp = client.post("/ask/", json={"query": "когда экзамен"}, headers={"Authorization": "Bearer x"})
    assert resp.status_code == 200 and resp.json()["calendar_events"] == []


def test_the_calendar_is_in_the_api_docs(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/users/my-calendar.ics" in paths and "/users/my-calendar/events/{proposal_id}" in paths


# --- the database: one calendar per InNoHassle account ---

TELEGRAM_ID = 999_000_001
TG, IH = f"tg:{TELEGRAM_ID}", "ih:test-calendar-account"


@pytest.fixture
def events():
    def add(key: str, title: str, day: int) -> None:
        with pg.connection() as conn:
            conn.execute(
                "INSERT INTO personal_events (user_key, title, starts_at) VALUES (%s, %s, %s::timestamptz)",
                (key, title, f"2099-01-{day:02d}T10:00:00+03:00"),
            )

    def titles(key: str) -> list[str]:
        return [e.title for e in personal_calendar.upcoming(key)]

    def clean() -> None:
        personal_calendar._accounts.pop(TELEGRAM_ID, None)
        with pg.connection() as conn:
            conn.execute("DELETE FROM personal_events WHERE user_key = ANY(%s)", ([TG, IH],))

    clean()
    yield add, titles
    clean()


def test_the_events_of_the_bot_move_to_the_account_once(events):
    add, titles = events
    add(TG, "Экзамен", 10)
    add(TG, "Дедлайн", 12)
    add(IH, "Экзамен", 10)  # added on the site too
    assert personal_calendar.account_key("test-calendar-account", TELEGRAM_ID) == IH
    assert titles(IH) == ["Экзамен", "Дедлайн"] and titles(TG) == []


def test_the_bot_keeps_the_events_under_the_account_inno_hassle_knows(events, monkeypatch):
    add, titles = events
    add(TG, "Экзамен", 10)
    monkeypatch.setattr(innohassle, "user_id_by_telegram_id", lambda telegram_id: "test-calendar-account")
    assert personal_calendar.telegram_key(TELEGRAM_ID) == IH
    assert titles(IH) == ["Экзамен"]


def test_without_an_account_the_bot_keeps_nothing_and_says_why(events, monkeypatch):
    """Only an InNoHassle account has a calendar: a Telegram id InNoHassle does not know gets none, not one of its own."""

    def down(telegram_id):
        raise RuntimeError("InNoHassle is down")

    monkeypatch.setattr(innohassle, "user_id_by_telegram_id", down)
    with pytest.raises(personal_calendar.NoAccount, match="не отвечает"):
        personal_calendar.telegram_key(TELEGRAM_ID)
    monkeypatch.setattr(innohassle, "user_id_by_telegram_id", lambda telegram_id: None)  # not registered
    with pytest.raises(personal_calendar.NoAccount) as no:
        personal_calendar.telegram_key(TELEGRAM_ID)
    assert str(no.value) == personal_calendar.NOT_LINKED and personal_calendar.CONNECT_TELEGRAM in str(no.value)
    assert len(personal_calendar.NOT_LINKED) <= 200  # Telegram shows at most 200 characters in the alert of a button.
    # Linked just now: the next press finds the account, the miss was not kept.
    monkeypatch.setattr(innohassle, "user_id_by_telegram_id", lambda telegram_id: "test-calendar-account")
    assert personal_calendar.telegram_key(TELEGRAM_ID) == IH


def test_the_feed_says_which_chat_message_an_event_comes_from(events):
    """A message of a basic group has no link: the event says in words where it was read (the site shows DESCRIPTION)."""
    with pg.connection() as conn:
        conn.execute(
            "INSERT INTO personal_events (user_key, title, starts_at, source_note) VALUES (%s, %s, %s::timestamptz, %s)",
            (IH, "Анонс: экзамен", "2099-01-10T10:00:00+03:00", "Из чата «Test-2», 05.11 21:10, Дмитрий:\nЗАВТРА ЭКЗАМЕН, 104"),
        )
    feed = personal_calendar.ics(IH).replace("\r\n ", "")  # unfolded
    assert "DESCRIPTION:Из чата «Test-2»\\, 05.11 21:10\\, Дмитрий:\\nЗАВТРА ЭКЗАМЕН\\, 104\r\n" in feed
    assert "X-WR-LINK" not in feed


def test_the_agent_reads_the_events_of_a_period_and_removes_one_of_its_own(events):
    """agent/calendar_tools.py: the AI Calendar of a period, one event by its id (for the approval) and its removal."""
    add, titles = events
    add(IH, "Экзамен", 10)
    add(IH, "Дедлайн", 12)
    at = lambda day: datetime(2099, 1, day, tzinfo=settings.tz)  # noqa: E731
    assert [e.title for e in personal_calendar.between(IH, at(10), at(11))] == ["Экзамен"]
    assert [e.title for e in personal_calendar.between(IH, at(11), at(13))] == ["Дедлайн"]
    exam = personal_calendar.between(IH, at(10), at(11))[0]
    assert personal_calendar.event_of(IH, exam.id).title == "Экзамен" and personal_calendar.event_of(TG, exam.id) is None
    assert not personal_calendar.delete_event(TG, exam.id), "not someone else's"
    assert personal_calendar.delete_event(IH, exam.id) and not personal_calendar.delete_event(IH, exam.id)
    assert titles(IH) == ["Дедлайн"]
