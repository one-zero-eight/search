"""Real policy persistence, guarded against accidentally using the application DB."""

import os
from pathlib import Path

import psycopg
import pytest
from psycopg.rows import dict_row

from catix import userbot_config as config
from catix.db import pg


@pytest.fixture(scope="module")
def policy_database():
    dsn = os.environ.get("TOPIC_POLICY_TEST_DSN")
    if not dsn:
        pytest.skip("set TOPIC_POLICY_TEST_DSN to a disposable ParadeDB database")
    assert psycopg.conninfo.conninfo_to_dict(dsn).get("dbname") == "catix_topic_policy_test"
    with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as conn:
        assert conn.execute("SELECT current_database() AS name").fetchone()["name"] == "catix_topic_policy_test"
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.execute("CREATE EXTENSION IF NOT EXISTS pg_search")
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = 'ctx_reader'").fetchone():
            conn.execute("CREATE ROLE ctx_reader")
        # Seed the pre-policy layout, then apply the actual migration twice.
        conn.execute("CREATE TABLE IF NOT EXISTS userbot_listen (chat_id bigint PRIMARY KEY, topic_ids bigint[], reader text NOT NULL DEFAULT 'auto')")
        conn.execute("INSERT INTO userbot_listen (chat_id, topic_ids, reader) VALUES (-81001, NULL, 'auto'), (-81002, ARRAY[1,7], 'bot'), (-81003, ARRAY[]::bigint[], 'userbot'), (-81004, ARRAY[7], 'search') ON CONFLICT DO NOTHING")
        schema = Path(__file__).resolve().parents[1].joinpath("db/schema.sql").read_text().replace("__TZ__", "UTC")
        conn.execute(schema)
        conn.execute(schema)
    return dsn


@pytest.fixture
def db(policy_database, monkeypatch):
    def connect():
        return psycopg.connect(policy_database, row_factory=dict_row)
    monkeypatch.setattr(pg, "connection", connect)
    config._forget()
    with connect() as conn:
        conn.execute("DELETE FROM userbot_listen WHERE chat_id BETWEEN -82099 AND -82000")
        conn.execute("DELETE FROM userbot_dialogs WHERE chat_id BETWEEN -82099 AND -82000")
        conn.execute("DELETE FROM userbot_topics WHERE chat_id BETWEEN -82099 AND -82000")
        conn.execute("DELETE FROM messages WHERE chat_id BETWEEN -82099 AND -82000")
        conn.execute("DELETE FROM chats WHERE chat_id BETWEEN -82099 AND -82000")
        conn.execute("INSERT INTO userbot_dialogs (chat_id,title,kind,forum) VALUES (-82001,'Forum','group',true)")
        conn.execute("INSERT INTO userbot_topics (chat_id,topic_id,title) VALUES (-82001,7,'Stored'),(-82001,8,'Off')")
    yield connect
    config._forget()


def test_schema_preserves_legacy_rows_after_repeated_migration(db):
    with db() as conn:
        rows = conn.execute("SELECT * FROM userbot_listen WHERE chat_id BETWEEN -81004 AND -81001 ORDER BY chat_id DESC").fetchall()
    assert len(rows) == 4
    assert all("topic_policy" in row for row in rows), "nullable migration is missing"
    assert all(row["topic_policy"] is None for row in rows)
    assert [config.get_policy(row["chat_id"]) for row in rows] == [
        {"default": "store", "topics": {}},
        {"default": "search", "topics": {1: "store", 7: "store"}},
        {"default": "search", "topics": {}},
        {"default": "search", "topics": {}},
    ]


def test_confirmation_saves_group_and_policy_together_without_deleting_history(db):
    assert hasattr(config, "save_configuration"), "wizard confirmation API is missing"
    assert -82001 not in config.listened()
    config.save_configuration(-82001, " b26-cse-01 ", "search", {1: "store", 7: "store", 8: "off"})
    assert config.get_policy(-82001) == {"default": "search", "topics": {1: "store", 7: "store", 8: "off"}}
    assert config.userbot_reads()[-82001] == [1, 7]
    with db() as conn:
        chat = conn.execute("SELECT * FROM chats WHERE chat_id=-82001").fetchone()
        assert chat["group_code"] == "B26-CSE-01" and chat["title"] == "Forum"
        conn.execute("INSERT INTO messages (chat_id,msg_id,date,text) VALUES (-82001,99,now(),'historical text')")
    config.save_configuration(-82001, "all", "search", {})
    assert -82001 not in config.userbot_reads()
    assert not config.topic_allowed(-82001, 7, 1)
    with db() as conn:
        assert conn.execute("SELECT text FROM messages WHERE chat_id=-82001 AND msg_id=99").fetchone()["text"] == "historical text"


@pytest.mark.parametrize("changes", [
    {"chat_id": -82002}, {"chat_id": True}, {"chat_id": "-82001"},
    {"group_code": "bad group"}, {"group_code": None},
    {"default_mode": "bogus"}, {"topic_modes": {7: "bogus"}},
    {"topic_modes": {0: "store"}}, {"topic_modes": {-1: "store"}},
    {"topic_modes": {True: "store"}}, {"topic_modes": {"7": "store"}},
    {"topic_modes": {999: "store"}}, {"topic_modes": None},
    {"reader": "invalid"}, {"reader": "bot"},
])
def test_invalid_confirmation_is_a_value_error_and_writes_nothing(db, changes):
    kwargs = dict(chat_id=-82001, group_code="all", default_mode="search", topic_modes={1: "store"}, reader="auto")
    kwargs.update(changes)
    with pytest.raises(ValueError):
        config.save_configuration(**kwargs)
    with db() as conn:
        assert conn.execute("SELECT 1 FROM chats WHERE chat_id BETWEEN -82099 AND -82000").fetchone() is None
        assert conn.execute("SELECT 1 FROM userbot_listen WHERE chat_id BETWEEN -82099 AND -82000").fetchone() is None


@pytest.mark.parametrize("default,topics,reader", [
    ("search", {}, "auto"), ("off", {1: "search"}, "bot"),
    ("store", {}, "search"), ("store", {}, "userbot"),
])
def test_bot_only_cannot_promise_telegram_live_search_or_userbot(db, default, topics, reader):
    with db() as conn:
        conn.execute("INSERT INTO chats (chat_id,title,bot_member) VALUES (-82002,'Bot only',true)")
    with pytest.raises(ValueError):
        config.save_configuration(-82002, "all", default, topics, reader)
    assert -82002 not in config.listened()


def test_save_rolls_back_chat_group_when_policy_write_fails(db):
    config.save_configuration(-82001, "all", "store", {})
    with db() as conn:
        conn.execute("ALTER TABLE userbot_listen ADD CONSTRAINT topic_policy_test_refusal CHECK (chat_id != -82001 OR reader != 'userbot')")
    try:
        with pytest.raises(psycopg.errors.CheckViolation):
            config.save_configuration(-82001, "b26-cse-01", "off", {}, "userbot")
        with db() as conn:
            assert conn.execute("SELECT group_code FROM chats WHERE chat_id=-82001").fetchone()["group_code"] == "all"
        assert config.get_policy(-82001) == {"default": "store", "topics": {}}
    finally:
        with db() as conn:
            conn.execute("ALTER TABLE userbot_listen DROP CONSTRAINT topic_policy_test_refusal")


def test_bot_discovery_never_opts_in_and_departure_preserves_configuration(db):
    assert hasattr(config, "register_bot_chat"), "bot discovery must not enable ingestion"
    assert not config.bot_listens(-82002)
    config.register_bot_chat(-82002, "Bot only", "test_group")
    assert config.dialog(-82002).bot_only
    assert not config.bot_listens(-82002)
    assert -82002 not in config.listened()
    config.save_configuration(-82002, "b26-cse-01", "store", {}, "bot")
    assert config.bot_listens(-82002)
    with db() as conn:
        conn.execute("INSERT INTO messages (chat_id,msg_id,date,text) VALUES (-82002,99,now(),'retained')")
    config.register_bot_chat(-82002, "Renamed", None, member=False)
    assert config.dialog(-82002) is None
    assert config.get_policy(-82002) == {"default": "store", "topics": {}}
    with db() as conn:
        assert conn.execute("SELECT text FROM messages WHERE chat_id=-82002").fetchone()["text"] == "retained"
        assert conn.execute("SELECT group_code FROM chats WHERE chat_id=-82002").fetchone()["group_code"] == "B26-CSE-01"


def test_unknown_bot_chat_does_not_implicitly_enable_storage(db):
    assert not config.bot_listens(-82002)
    assert -82002 not in config.listened()


def test_legacy_toggle_last_topic_never_reenables_every_topic(db):
    with db() as conn:
        conn.execute("INSERT INTO userbot_listen (chat_id,topic_ids) VALUES (-82001,ARRAY[7])")
    config.toggle_topic(-82001, 7)
    assert config.listened()[-82001] == []
    assert -82001 not in config.userbot_reads()
    assert not config.topic_allowed(-82001, 99, 1)


def test_toggle_on_policy_preserves_other_topic_choices(db):
    config.save_configuration(-82001, "all", "search", {7: "store", 8: "off"})
    config.toggle_topic(-82001, 7)
    assert config.get_policy(-82001) == {"default": "search", "topics": {7: "search", 8: "off"}}
    config.toggle_topic(-82001, 1)
    assert config.userbot_reads()[-82001] == [1]
    config.clear_topics(-82001)
    assert config.get_policy(-82001) == {"default": "store", "topics": {}}
