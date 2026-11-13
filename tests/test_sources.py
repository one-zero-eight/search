"""The website catalogue uses actual policies and verified access, never admin discovery."""
import os
from pathlib import Path

import psycopg
import pytest
import httpx
from fastapi.testclient import TestClient
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import SecretStr, ValidationError

from catix import groups, sources
from catix.api.app import app
from catix.api.auth import UserTokenData, verify_user
from catix.api.sources import SourceView
from catix.db import pg
from catix.maxuserbot.models import MAX_USER_CHAT_BASE


@pytest.fixture(scope="module")
def sources_database():
    dsn = os.environ.get("SOURCE_REQUESTS_TEST_DSN")
    if not dsn:
        pytest.skip("set SOURCE_REQUESTS_TEST_DSN to disposable ParadeDB")
    with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as conn:
        assert conn.execute("SELECT current_database() AS name").fetchone()["name"] == "catix_source_requests_test"
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
             userbot=True, bot=False, forum=False, topics=None, legacy=False, scope=None, history=False,
             link="https://t.me/+PrivateInviteNotForCatalogue", username=None, kind="group", archived=False):
    with db() as conn:
        conn.execute(
            """INSERT INTO chats (chat_id, title, group_code, requires_verified_group, bot_member, link, username,
                                  max_legacy_archived) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (chat_id, title, group, protected, bot, link, username, archived),
        )
        if userbot:
            conn.execute("INSERT INTO userbot_dialogs (chat_id,title,kind,forum) VALUES (%s,%s,%s,%s)",
                         (chat_id, title, kind, forum))
        if mode is not None:
            policy = None if legacy else Jsonb({"default": mode, "topics": topics or {}})
            conn.execute("INSERT INTO userbot_listen (chat_id,reader,topic_ids,topic_policy) VALUES (%s,%s,%s,%s)",
                         (chat_id, reader, scope, policy))
        if history:
            conn.execute("INSERT INTO messages (chat_id,msg_id,date,text) VALUES (%s,1,now(),'Saved message')", (chat_id,))


def add_max_source(db, raw_chat_id, title, group="all", *, enabled=True, access="ready", history=False,
                   protected=False, link=None, kind="chat"):
    chat_id = MAX_USER_CHAT_BASE + raw_chat_id
    add_chat(db, chat_id, title, group, protected=protected, mode=None, userbot=False, history=history, link=link)
    with db() as conn:
        conn.execute("INSERT INTO max_sources (chat_id,raw_chat_id,kind,enabled,access) VALUES (%s,%s,%s,%s,%s)",
                     (chat_id, raw_chat_id, kind, enabled, access))
    return chat_id


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
        "platform": "telegram", "link": "https://t.me/+PrivateInviteNotForCatalogue",
        "default_mode": "store", "topics": [], "has_stored_messages": False,
    }
    assert all(source["platform"] == "telegram" for source in payload["sources"])
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


def test_legacy_bot_api_history_is_not_automatically_a_source(db, client):
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


@pytest.mark.parametrize("platform,link,expected", [
    ("telegram", "https://t.me/Public_Chat", "https://t.me/public_chat"),
    ("telegram", "https://t.me/+AbCdEfGhIjKlMnOp", "https://t.me/+AbCdEfGhIjKlMnOp"),
    ("telegram", "https://t.me/joinchat/AbCdEfGhIjKlMnOp", "https://t.me/+AbCdEfGhIjKlMnOp"),
    ("max", "https://max.ru/Public_Chat-1", "https://max.ru/Public_Chat-1"),
    ("max", "https://max.ru/join/AbCdEfGhIjKlMnOp", "https://max.ru/join/AbCdEfGhIjKlMnOp"),
    ("telegram", None, None),
    ("max", None, None),
])
def test_source_links_accept_only_platform_chat_names_and_saved_invites(platform, link, expected):
    assert sources._source_link(link, platform) == expected


@pytest.mark.parametrize("platform,link", [
    ("telegram", "https://t.me/+short"),
    ("telegram", "https://t.me/joinchat"),
    ("telegram", "https://t.me/SHARE"),
    ("telegram", "https://t.me/PublicChat/123"),
    ("telegram", "https://t.me/c/123/456"),
    ("telegram", "https://t.me/s/PublicChat"),
    ("telegram", "t.me/PublicChat"),
    ("telegram", "http://t.me/PublicChat"),
    ("telegram", "https://t.me@evil.example/PublicChat"),
    ("telegram", "https://user:password@t.me/PublicChat"),
    ("telegram", "https://t.me:443/PublicChat"),
    ("telegram", "https://t.me/PublicChat?start=secret"),
    ("telegram", "https://t.me/PublicChat#fragment"),
    ("telegram", "https://t.me/+AbCdEfGhIjKlMnOp?secret=1"),
    ("telegram", "https://t.me/joinchat/AbCdEfGhIjKlMnOp#secret"),
    ("telegram", "https://t.me/%50ublicChat"),
    ("telegram", "https://t.me/PublicChat/"),
    ("telegram", " https://t.me/PublicChat"),
    ("telegram", "https://t.me/PublicChat\n"),
    ("telegram", "https://max.ru/PublicChat"),
    ("max", "https://max.ru/join"),
    ("max", "https://max.ru/JOIN"),
    ("max", "https://max.ru/joinchat"),
    ("max", "https://max.ru/+AbCdEfGhIjKlMnOp"),
    ("max", "https://max.ru/join/"),
    ("max", "https://max.ru/PublicChat/123"),
    ("max", "max.ru/PublicChat"),
    ("max", "http://max.ru/PublicChat"),
    ("max", "https://max.ru.evil.example/PublicChat"),
    ("max", "https://user:password@max.ru/PublicChat"),
    ("max", "https://max.ru:443/PublicChat"),
    ("max", "https://max.ru/PublicChat?secret=1"),
    ("max", "https://max.ru/PublicChat#secret"),
    ("max", "https://max.ru/join/AbCdEfGhIjKlMnOp?secret=1"),
    ("max", "https://max.ru/join/AbCdEfGhIjKlMnOp#secret"),
    ("max", "https://max.ru/%50ublicChat"),
    ("max", "https://max.ru/PublicChat/"),
    ("max", "https://max.ru/PublicChat\n"),
    ("max", "https://t.me/PublicChat"),
])
def test_source_links_reject_messages_actions_and_url_metadata(platform, link):
    assert sources._source_link(link, platform) is None


@pytest.mark.parametrize("username,link,expected", [
    ("Public_Chat", "https://t.me/+AbCdEfGhIjKlMnOp", "https://t.me/public_chat"),
    ("Public_Chat", None, "https://t.me/public_chat"),
    ("joinchat", "https://t.me/PublicChat", "https://t.me/publicchat"),
    ("bad/name", "https://t.me/+AbCdEfGhIjKlMnOp", "https://t.me/+AbCdEfGhIjKlMnOp"),
    ("+OtherPrivateInvitation", "https://t.me/PublicChat", "https://t.me/publicchat"),
])
def test_telegram_public_username_precedes_stored_link(username, link, expected):
    assert sources._source_link(link, "telegram", username=username) == expected


@pytest.mark.parametrize("changes", [
    {"platform": "other"}, {"platform": 1}, {"link": 123},
])
def test_source_view_rejects_invalid_platform_or_link(changes):
    payload = {"chat_id": "-10", "title": "Source", "group_code": "all", "platform": "telegram",
               "link": None, "forum": False, "default_mode": "store", "topics": [], "has_stored_messages": False}
    with pytest.raises(ValidationError):
        SourceView.model_validate(payload | changes)


@pytest.mark.parametrize("field", ["platform", "link"])
def test_source_view_requires_platform_and_nullable_link(field):
    payload = {"chat_id": "-10", "title": "Source", "group_code": "all", "platform": "max",
               "link": None, "forum": False, "default_mode": "off", "topics": [], "has_stored_messages": True}
    assert SourceView.model_validate(payload).link is None
    del payload[field]
    with pytest.raises(ValidationError):
        SourceView.model_validate(payload)


def test_telegram_catalogue_prefers_public_name_and_validates_stored_fallback(db, client):
    add_chat(db, -10, "A public", username="PublicChat")
    add_chat(db, -20, "B stored", link="https://t.me/StoredChat")
    add_chat(db, -30, "C invite", link="https://t.me/joinchat/AbCdEfGhIjKlMnOp")
    add_chat(db, -40, "D invalid", link="https://t.me/PublicChat/123")
    add_chat(db, -50, "E dialog name", link=None)
    with db() as conn:
        conn.execute("UPDATE userbot_dialogs SET username = 'DialogName' WHERE chat_id = -50")
    rows = client.get("/sources").json()["sources"]
    assert [row["link"] for row in rows] == [
        "https://t.me/publicchat", "https://t.me/storedchat", "https://t.me/+AbCdEfGhIjKlMnOp", None,
        "https://t.me/dialogname",
    ]
    assert all(row["platform"] == "telegram" for row in rows)


@pytest.mark.parametrize("enabled,access,history,expected", [
    (True, "ready", False, "store"),
    (True, "ready", True, "store"),
    (False, "ready", False, None),
    (False, "ready", True, "off"),
    (True, "unknown", False, None),
    (True, "unknown", True, "off"),
    (True, "removed", True, "off"),
    (True, "no_permission", True, "off"),
])
def test_max_catalogue_uses_native_enablement_access_and_saved_history(db, client, enabled, access, history, expected):
    chat_id = add_max_source(db, -123, "MAX source", enabled=enabled, access=access, history=history,
                             link="https://max.ru/PublicChat", kind="channel")
    payload = client.get("/sources").json()["sources"]
    if expected is None:
        assert payload == []
    else:
        assert payload == [{
            "chat_id": str(chat_id), "title": "MAX source", "group_code": "all", "platform": "max",
            "link": "https://max.ru/PublicChat", "forum": False, "default_mode": expected,
            "topics": [], "has_stored_messages": history,
        }]


@pytest.mark.parametrize("link,expected", [
    (None, None),
    ("https://max.ru/join/PrivateInvite", "https://max.ru/join/PrivateInvite"),
    ("https://max.ru/ChatName/123", None),
    ("https://t.me/PublicChat", None),
])
def test_max_catalogue_never_fabricates_links_or_uses_telegram_usernames(db, client, link, expected):
    chat_id = add_max_source(db, 123, "MAX source", link=link)
    with db() as conn:
        conn.execute("UPDATE chats SET username = 'WrongPlatform' WHERE chat_id = %s", (chat_id,))
    source = client.get("/sources").json()["sources"][0]
    assert source["platform"] == "max"
    assert source["link"] == expected


def test_messenger_sources_share_verified_scope_without_leaking_other_invites(db, client):
    add_chat(db, -10, "A Telegram public", username="PublicChat")
    add_max_source(db, 10, "B MAX common", link="https://max.ru/Common")
    add_max_source(db, 20, "C MAX B26", "B26", protected=True, link="https://max.ru/join/OwnInvite")
    add_max_source(db, 30, "D MAX B27", "B27", protected=True)
    add_max_source(db, 40, "Hidden B28", "B28", protected=True, link="https://max.ru/join/OtherAudienceSecret")
    add_max_source(db, 50, "Hidden protected all", protected=True, link="https://max.ru/join/ProtectedAllSecret")
    add_chat(db, -60, "Hidden Telegram B28", "B28", link="https://t.me/+OtherAudienceSecret")
    response = client.get("/sources?group_code=B28")
    rows = response.json()["sources"]
    assert [row["title"] for row in rows] == ["A Telegram public", "B MAX common", "C MAX B26", "D MAX B27"]
    assert [row["platform"] for row in rows] == ["telegram", "max", "max", "max"]
    assert rows[2]["link"] == "https://max.ru/join/OwnInvite"
    assert "OtherAudienceSecret" not in response.text
    assert "ProtectedAllSecret" not in response.text


def test_max_sources_fail_closed_when_group_verification_is_unavailable(db, client, monkeypatch):
    add_max_source(db, 10, "Common", link="https://max.ru/Common")
    add_max_source(db, 20, "Verified only", "B26", protected=True, link="https://max.ru/join/PrivateSecret")
    def unavailable(_):
        raise httpx.ConnectError("Upstream unavailable")
    monkeypatch.setattr(groups.innohassle, "my_student_groups", unavailable)
    response = client.get("/sources")
    assert response.json()["verified_groups"] == []
    assert [row["title"] for row in response.json()["sources"]] == ["Common"]
    assert "PrivateSecret" not in response.text


def test_catalogue_omits_private_dialogs_archives_and_unregistered_max_history(db, client):
    add_chat(db, -10, "Private dialog", kind="private", history=True)
    add_chat(db, -20, "Archived legacy", history=True, archived=True)
    add_chat(db, groups.MAX_CHAT_BASE + 123, "Legacy MAX", mode=None, userbot=False, history=True)
    add_chat(db, MAX_USER_CHAT_BASE + 456, "Unregistered MAX", mode=None, userbot=False, history=True)
    assert client.get("/sources").json()["sources"] == []
