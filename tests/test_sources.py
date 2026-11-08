"""The website catalogue uses actual policies and verified access, never admin discovery."""
import os
from pathlib import Path

import psycopg
import pytest
import httpx
from fastapi.testclient import TestClient
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import SecretStr

from catix import groups
from catix.api.app import app
from catix.api.auth import UserTokenData, verify_user
from catix.db import pg


@pytest.fixture(scope="module")
def sources_database():
    dsn = os.environ.get("SOURCES_TEST_DSN")
    if not dsn:
        pytest.skip("set SOURCES_TEST_DSN to disposable ParadeDB")
    with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as conn:
        assert conn.execute("SELECT current_database() AS name").fetchone()["name"] == "catix_sources_test"
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.execute("CREATE EXTENSION IF NOT EXISTS pg_search")
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = 'ctx_reader'").fetchone():
            conn.execute("CREATE ROLE ctx_reader")
        schema = Path(__file__).resolve().parents[1].joinpath("db/schema.sql").read_text().replace("__TZ__", "UTC")
        conn.execute(schema)
        conn.execute(schema)
    return dsn


@pytest.fixture
def db(sources_database, monkeypatch):
    def connect():
        return psycopg.connect(sources_database, row_factory=dict_row)
    monkeypatch.setattr(pg, "connection", connect)
    with connect() as conn:
        conn.execute("TRUNCATE chats, userbot_dialogs, userbot_topics, userbot_listen, user_groups CASCADE")
    return connect


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(groups.innohassle, "my_student_groups", lambda _: ["B26", "B27"])
    app.dependency_overrides[verify_user] = lambda: UserTokenData(
        innohassle_id="owner", email="owner@example.org", token=SecretStr("test-user-token"),
    )
    yield TestClient(app)
    app.dependency_overrides.pop(verify_user, None)


def add_chat(db, chat_id, title, group="all", *, protected=False, mode="store", reader="auto",
             userbot=True, bot=False, forum=False, topics=None, legacy=False, scope=None, history=False):
    with db() as conn:
        conn.execute(
            "INSERT INTO chats (chat_id, title, group_code, requires_verified_group, bot_member, link) VALUES (%s,%s,%s,%s,%s,%s)",
            (chat_id, title, group, protected, bot, "https://t.me/+PrivateInviteNotForCatalogue"),
        )
        if userbot:
            conn.execute("INSERT INTO userbot_dialogs (chat_id,title,kind,forum) VALUES (%s,%s,'group',%s)", (chat_id, title, forum))
        if mode is not None:
            policy = None if legacy else Jsonb({"default": mode, "topics": topics or {}})
            conn.execute("INSERT INTO userbot_listen (chat_id,reader,topic_ids,topic_policy) VALUES (%s,%s,%s,%s)",
                         (chat_id, reader, scope, policy))
        if history:
            conn.execute("INSERT INTO messages (chat_id,msg_id,date,text) VALUES (%s,1,now(),'Saved message')", (chat_id,))


def test_catalogue_includes_common_and_every_verified_group_only(db, client, monkeypatch):
    tokens = []
    monkeypatch.setattr(groups, "website_groups", lambda token: tokens.append(token) or ["B26", "B27"])
    add_chat(db, -10, "Common")
    add_chat(db, -20, "First group", "B26", protected=True)
    add_chat(db, -30, "Second group", "B27")
    add_chat(db, -40, "Other group", "B28")
    add_chat(db, -50, "Protected all", protected=True)
    add_chat(db, -60, "Discovered but never enabled", mode=None)
    response = client.get("/sources")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["verified_groups"] == ["B26", "B27"]
    assert [source["title"] for source in payload["sources"]] == ["Common", "First group", "Second group"]
    assert payload["sources"][0] == {
        "chat_id": "-10", "title": "Common", "group_code": "all", "forum": False,
        "default_mode": "store", "topics": [], "has_stored_messages": False,
    }
    assert "PrivateInvite" not in response.text
    assert tokens == ["test-user-token"]
    assert response.headers["cache-control"] == "private, no-store"


def test_forum_reports_exact_topic_modes_and_general_even_when_not_discovered(db, client):
    add_chat(db, -10, "Forum", forum=True, mode="search", topics={"1": "store", "12": "off", "99": "store"})
    with db() as conn:
        conn.execute("INSERT INTO userbot_topics (chat_id,topic_id,title) VALUES (-10,12,'Excluded'),(-10,15,'Questions')")
    source = client.get("/sources").json()["sources"][0]
    assert source["default_mode"] == "search"
    assert source["topics"] == [
        {"topic_id": "1", "title": "General", "mode": "store"},
        {"topic_id": "12", "title": "Excluded", "mode": "off"},
        {"topic_id": "15", "title": "Questions", "mode": "search"},
        {"topic_id": "99", "title": "99", "mode": "store"},
    ]


def test_stopped_sources_keep_history_without_claiming_active_collection(db, client):
    add_chat(db, -10, "Archived", mode=None, history=True)
    add_chat(db, -20, "Disabled with history", mode="off", history=True)
    add_chat(db, -30, "Disabled empty", mode="off")
    add_chat(db, -40, "Never enabled", mode=None)
    sources = client.get("/sources").json()["sources"]
    assert [s["title"] for s in sources] == ["Archived", "Disabled with history"]
    assert all(s["has_stored_messages"] and s["default_mode"] == "off" for s in sources)


@pytest.mark.parametrize("reader,userbot,bot,mode,expected", [
    ("auto", True, False, "store", "store"),
    ("auto", False, True, "store", "store"),
    ("auto", False, False, "store", "off"),
    ("userbot", False, True, "store", "off"),
    ("userbot", True, False, "store", "store"),
    ("bot", True, False, "store", "search"),
    ("bot", True, True, "store", "store"),
    ("bot", False, True, "search", "off"),
    ("search", True, True, "store", "search"),
    ("search", False, True, "search", "off"),
])
def test_effective_mode_accounts_for_reader_membership(db, client, reader, userbot, bot, mode, expected):
    add_chat(db, -10, "Source", reader=reader, userbot=userbot, bot=bot, mode=mode, history=True)
    source = client.get("/sources").json()["sources"][0]
    assert source["default_mode"] == expected
    assert source["has_stored_messages"]


@pytest.mark.parametrize("mode,override,expected", [("off", "store", "store"), ("store", "off", "off")])
def test_general_override_in_nonforum_is_the_whole_chat(db, client, mode, override, expected):
    add_chat(db, -10, "Plain chat", mode=mode, topics={"1": override}, history=True)
    source = client.get("/sources").json()["sources"][0]
    assert source["forum"] is False
    assert source["topics"] == []
    assert source["default_mode"] == expected


def test_telegram_catalogue_does_not_mislabel_max_history(db, client):
    add_chat(db, groups.MAX_CHAT_BASE + 123, "Max history", mode=None, userbot=False, history=True)
    assert client.get("/sources").json()["sources"] == []


def test_verification_is_fresh_fails_closed_and_never_uses_manual_or_telegram_group(db, client, monkeypatch):
    add_chat(db, -10, "Common")
    add_chat(db, -20, "Own private", "B26", protected=True, history=True)
    add_chat(db, -30, "Other private", "B28", protected=True)
    add_chat(db, -40, "Protected all", protected=True)
    groups.set_user_group("web:owner", "B28")
    assert len(client.get("/sources").json()["sources"]) == 2
    def unavailable(_):
        raise httpx.ConnectError("Upstream unavailable")
    monkeypatch.setattr(groups.innohassle, "my_student_groups", unavailable)
    monkeypatch.setattr(groups, "auto_group", lambda _: pytest.fail("No Telegram fallback"))
    monkeypatch.setattr(groups, "user_group", lambda _: pytest.fail("No manual fallback"))
    response = client.get("/sources?group_code=B28")
    assert response.status_code == 200
    assert response.json()["verified_groups"] == []
    assert [s["title"] for s in response.json()["sources"]] == ["Common"]
    assert "private" not in response.text


@pytest.mark.parametrize("scope,reader,default,overrides", [
    (None, "auto", "store", {}),
    ([], "auto", "search", {}),
    ([12], "auto", "search", {"12": "store"}),
    ([12], "search", "search", {}),
])
def test_legacy_policy_uses_the_same_interpretation_as_search(db, client, scope, reader, default, overrides):
    add_chat(db, -10, "Legacy", forum=True, legacy=True, scope=scope, reader=reader)
    source = client.get("/sources").json()["sources"][0]
    assert source["default_mode"] == default
    assert {t["topic_id"]: t["mode"] for t in source["topics"] if t["mode"] != default} == overrides


def test_unauthenticated_catalogue_is_rejected_before_storage(monkeypatch):
    monkeypatch.setattr(pg, "connection", lambda: pytest.fail("Unauthenticated storage access"))
    response = TestClient(app).get("/sources")
    assert response.status_code == 401


def test_empty_catalogue_is_explicit(db, client):
    assert client.get("/sources").json() == {"verified_groups": ["B26", "B27"], "sources": []}
