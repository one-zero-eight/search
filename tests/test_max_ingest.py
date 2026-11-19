"""Account catalog and native inbox contracts on opt-in disposable PostgreSQL.

No credentials or real MAX transport are used.
"""

import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
import pytest
from psycopg.rows import dict_row

from catix import groups, official
from catix.db import pg, store
from catix.ingest import image_queue, noise
from catix.maxuserbot import state
from catix.maxuserbot.models import normalize_message


RAW_CHAT_ID = -42001
CHAT_ID = 4 * 10**15 + RAW_CHAT_ID
LEGACY_ID = groups.MAX_CHAT_BASE + RAW_CHAT_ID
GROUP = "B26-CSE-01"
OBSERVED = datetime(2026, 1, 1, tzinfo=timezone.utc)


def now():
    return datetime.now(timezone.utc)


def schema_sql():
    return Path(__file__).resolve().parents[1].joinpath("db/schema.sql").read_text().replace("__TZ__", "UTC")


@pytest.fixture(scope="module")
def max_database():
    dsn = os.environ.get("IMAGE_QUEUE_TEST_DSN")
    if not dsn:
        pytest.skip("set IMAGE_QUEUE_TEST_DSN to a disposable ParadeDB database")
    with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as conn:
        assert conn.execute("SELECT current_database() AS name").fetchone()["name"] == "catix_image_queue_test"
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.execute("CREATE EXTENSION IF NOT EXISTS pg_search")
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = 'ctx_reader'").fetchone():
            conn.execute("CREATE ROLE ctx_reader")
        conn.execute(schema_sql())
        conn.execute(schema_sql())
    return dsn


@pytest.fixture
def db(max_database, monkeypatch):
    def connect():
        return psycopg.connect(max_database, row_factory=dict_row)

    monkeypatch.setattr(pg, "connection", connect)
    monkeypatch.setattr(noise, "enabled", lambda: True)
    with connect() as conn:
        conn.execute("TRUNCATE chats, message_ingest_state, max_account, query_context CASCADE")
        conn.execute("UPDATE image_queue_lease SET token = NULL, lease_until = NULL")
    yield connect
    with connect() as conn:
        conn.execute("TRUNCATE chats, message_ingest_state, max_account, query_context CASCADE")


def fetch(db, sql, params=()):
    with db() as conn:
        return conn.execute(sql, params).fetchone()


def count(db, table):
    # Literal test-owned names only.
    return fetch(db, f"SELECT count(*) AS n FROM {table}")["n"]


def discover(raw_id=RAW_CHAT_ID, *, kind="chat", title="Robotics source"):
    state.upsert_catalog([{"raw_chat_id": raw_id, "kind": kind, "title": title,
                           "status": "ACTIVE", "link": None}], observed_at=now())
    return state.get_source(4 * 10**15 + raw_id)


def ready_source(*, raw_id=RAW_CHAT_ID):
    source = discover(raw_id)
    state.account_connected(12345)
    state.heartbeat(connected=True)
    state.apply_access(source["chat_id"], generation=source["generation"], access="ready", observed_at=now())
    return state.get_source(source["chat_id"])


def save(source, *, enabled=True, group=GROUP, legacy_chat_id=None):
    state.save_configuration(source["chat_id"], group, enabled=enabled,
                             expected_version=source["config_version"],
                             expected_generation=source["generation"], legacy_chat_id=legacy_chat_id)
    return state.get_source(source["chat_id"])


def message(chat_id=CHAT_ID, *, image=False):
    return store.Message(chat_id, 101, None, OBSERVED, None, 9, "Author", None,
                         "Durable robotics laboratory storage contract", None,
                         image_source="maxuserbot" if image else None,
                         image_refs=("photo:123",) if image else (), observed_at=OBSERVED)


def stored(db, chat_id=CHAT_ID):
    return fetch(db, "SELECT * FROM messages WHERE chat_id = %s AND msg_id = 101", (chat_id,))


def seed_legacy():
    store.write_batch([store.ChatInfo(LEGACY_ID, "Legacy robotics", None)], [message(LEGACY_ID)])


def test_discovery_is_private_disabled_and_round_trips_joined_metadata(db):
    source = discover()
    assert source["chat_id"] == CHAT_ID and source["raw_chat_id"] == RAW_CHAT_ID
    assert source["kind"] == "chat" and source["title"] == "Robotics source"
    assert source["link"] is None and source["group_code"] == "all"
    assert source["requires_verified_group"] is True
    assert source["enabled"] is False and source["access"] == "unknown"
    assert source["generation"] == source["config_version"] == 0
    assert source["metadata_pending"] is True and source["history_status"] == "idle"
    assert source["legacy_chat_id"] is None
    assert state.list_sources() == [source]
    assert not state.allowed(CHAT_ID)
    assert CHAT_ID not in groups.website_chat_ids([])
    assert state.get_source(-100) is None


def test_catalog_refresh_preserves_audience_configuration_and_content(db):
    source = save(ready_source())
    store.write_batch([], [message()])
    refreshed = discover(title="Renamed source", kind="channel")
    assert refreshed["title"] == "Renamed source" and refreshed["kind"] == "channel"
    for key in ("enabled", "generation", "config_version", "group_code", "requires_verified_group"):
        assert refreshed[key] == source[key]
    assert stored(db) is not None


def test_enable_requires_explicit_valid_audience(db):
    source = ready_source()
    with pytest.raises((ValueError, state.ConfigurationConflict)):
        save(source, group="")
    assert state.get_source(CHAT_ID) == source
    assert CHAT_ID not in groups.website_chat_ids([])


def test_off_on_versions_and_stale_writers_preserve_history(db):
    initial = ready_source()
    enabled = save(initial)
    assert enabled["enabled"] and state.allowed(CHAT_ID)
    assert enabled["generation"] > initial["generation"]
    store.write_batch([], [message()])
    off = save(enabled, enabled=False)
    assert not state.allowed(CHAT_ID) and not off["enabled"]
    assert off["generation"] > enabled["generation"]
    assert off["config_version"] > enabled["config_version"]
    with pytest.raises(state.ConfigurationConflict):
        save(enabled)
    with pytest.raises(state.ConfigurationConflict):
        state.save_configuration(CHAT_ID, GROUP, enabled=True,
                                 expected_version=off["config_version"], expected_generation=enabled["generation"])
    again = save(off)
    assert again["generation"] > off["generation"] and again["history_status"] == "pending"
    assert stored(db) is not None


@pytest.mark.parametrize("stale_field", ["checked_at", "heartbeat_at"])
def test_enable_rejects_stale_access_or_worker_and_requests_refresh(db, stale_field):
    source = ready_source()
    with db() as conn:
        if stale_field == "checked_at":
            conn.execute("UPDATE max_sources SET checked_at = %s WHERE chat_id = %s", (now() - timedelta(minutes=6), CHAT_ID))
        else:
            conn.execute("UPDATE max_account SET heartbeat_at = %s", (now() - timedelta(seconds=61),))
    with pytest.raises(state.SourceUnavailable):
        save(source)
    assert not state.get_source(CHAT_ID)["enabled"]
    assert state.get_account()["catalog_requested"] is True


def test_access_revoke_fences_configuration_and_stale_access_update(db):
    source = save(ready_source())
    state.apply_access(CHAT_ID, generation=source["generation"], access="removed", observed_at=now())
    revoked = state.get_source(CHAT_ID)
    assert revoked["access"] == "removed" and not revoked["enabled"]
    assert revoked["generation"] > source["generation"]
    assert revoked["config_version"] > source["config_version"]
    state.apply_access(CHAT_ID, generation=source["generation"], access="ready", observed_at=now())
    assert state.get_source(CHAT_ID) == revoked
    with pytest.raises(state.SourceUnavailable):
        save(revoked)


def test_manual_history_and_audience_change_are_independent(db):
    source = save(ready_source())
    with db() as conn:
        conn.execute("UPDATE max_sources SET history_status = 'complete', history_before_ms = 123 WHERE chat_id = %s", (CHAT_ID,))
    changed = save(source, group="all")
    assert changed["history_status"] == "complete" and changed["history_before_ms"] == 123
    assert changed["generation"] == source["generation"]
    assert changed["config_version"] > source["config_version"]
    assert changed["requires_verified_group"] is False
    state.request_history(CHAT_ID, expected_version=changed["config_version"], expected_generation=changed["generation"])
    requested = state.get_source(CHAT_ID)
    assert requested["history_status"] == "pending"
    assert requested["group_code"] == "all" and requested["requires_verified_group"] is False
    with pytest.raises(state.ConfigurationConflict):
        state.request_history(CHAT_ID, expected_version=source["config_version"], expected_generation=source["generation"])


def test_account_identity_is_singleton_and_mismatch_does_not_replace_it(db):
    state.account_connected(12345)
    state.account_connected(12345)
    assert state.get_account()["account_id"] == 12345
    with pytest.raises(state.AccountMismatch, match="account_mismatch"):
        state.account_connected(99999)
    assert state.get_account()["account_id"] == 12345
    assert count(db, "max_account") == 1
    state.request_catalog()
    assert state.get_account()["catalog_requested"] is True


def test_legacy_mapping_is_explicit_and_archived_only_on_enable(db):
    seed_legacy()
    source = ready_source()
    assert source["legacy_chat_id"] is None
    assert not fetch(db, "SELECT max_legacy_archived FROM chats WHERE chat_id = %s", (LEGACY_ID,))["max_legacy_archived"]
    configured = save(source, enabled=False, legacy_chat_id=LEGACY_ID)
    assert configured["legacy_chat_id"] == LEGACY_ID
    assert not fetch(db, "SELECT max_legacy_archived FROM chats WHERE chat_id = %s", (LEGACY_ID,))["max_legacy_archived"]
    enabled = save(configured, legacy_chat_id=LEGACY_ID)
    assert fetch(db, "SELECT max_legacy_archived FROM chats WHERE chat_id = %s", (LEGACY_ID,))["max_legacy_archived"]
    save(enabled, enabled=False, legacy_chat_id=LEGACY_ID)
    assert stored(db, LEGACY_ID) is not None
    assert fetch(db, "SELECT max_legacy_archived FROM chats WHERE chat_id = %s", (LEGACY_ID,))["max_legacy_archived"]


def test_legacy_link_conflict_rolls_back_configuration_and_archive(db):
    seed_legacy()
    first = save(ready_source(), legacy_chat_id=LEGACY_ID)
    other = ready_source(raw_id=RAW_CHAT_ID - 1)
    with pytest.raises(state.ConfigurationConflict):
        save(other, legacy_chat_id=LEGACY_ID)
    assert state.get_source(other["chat_id"]) == other
    assert state.get_source(CHAT_ID) == first
    with pytest.raises(state.ConfigurationConflict):
        save(first, legacy_chat_id=-100)
    assert state.get_source(CHAT_ID) == first


def test_stale_legacy_save_cannot_archive_or_mutate_audience(db):
    seed_legacy()
    source = ready_source()
    updated = save(source, enabled=False, group="all")
    with pytest.raises(state.ConfigurationConflict):
        save(source, legacy_chat_id=LEGACY_ID, group="all")
    assert state.get_source(CHAT_ID) == updated
    assert not fetch(db, "SELECT max_legacy_archived FROM chats WHERE chat_id = %s", (LEGACY_ID,))["max_legacy_archived"]


@pytest.mark.parametrize("scope", [None, [LEGACY_ID], [LEGACY_ID, CHAT_ID]])
def test_archived_legacy_hidden_from_latest_and_visible_sql_even_explicit_scope(db, scope, monkeypatch):
    seed_legacy()
    save(ready_source(), legacy_chat_id=LEGACY_ID)
    store.write_batch([], [message()])
    expected = 0 if scope == [LEGACY_ID] else 1
    assert store.latest(chat_ids=scope)[0] == expected
    assert all(row["title"] != "Legacy robotics" for row in store.visible_chats(scope))
    assert store.latest(chat="Legacy robotics", chat_ids=scope) is None
    with db() as conn:
        conn.execute("INSERT INTO query_context (backend_pid, chat_ids) VALUES (pg_backend_pid(), %s)", (scope,))
        assert LEGACY_ID not in conn.execute("SELECT visible.allowed_chats() AS ids").fetchone()["ids"]
        assert conn.execute("SELECT count(*) AS n FROM visible.messages").fetchone()["n"] == expected
    assert LEGACY_ID not in groups.website_chat_ids([GROUP])
    monkeypatch.setattr(groups, "auto_group", lambda _: GROUP)
    assert LEGACY_ID not in groups.scoped_chat_ids("tg:test", 123)


def test_native_and_legacy_message_numbers_do_not_collide_or_migrate_telegram(db):
    seed_legacy()
    discover()
    store.write_batch([store.ChatInfo(-100, "Telegram", None)], [message(), message(-100)])
    assert CHAT_ID != LEGACY_ID
    assert all(stored(db, chat_id) is not None for chat_id in (CHAT_ID, LEGACY_ID, -100))
    with db() as conn:
        conn.execute(schema_sql())
        conn.execute(schema_sql())
    assert state.get_source(LEGACY_ID) is None and state.get_source(-100) is None
    assert len(state.list_sources()) == 1
    assert all(stored(db, chat_id) is not None for chat_id in (CHAT_ID, LEGACY_ID, -100))


def test_store_caller_owned_write_rollback_includes_fence_ocr_and_outbox(db):
    discover()
    conn = db()
    try:
        store.write_batch([], [message(image=True)], conn=conn)
        conn.execute("INSERT INTO max_publish_queue (chat_id, msg_id) VALUES (%s, 101)", (CHAT_ID,))
        assert not conn.closed
        assert conn.execute("SELECT count(*) AS n FROM messages").fetchone()["n"] == 1
        assert stored(db) is None
        conn.rollback()
        for table in ("messages", "message_ingest_state", "image_queue", "embedding_queue", "max_publish_queue"):
            assert count(db, table) == 0
    finally:
        conn.close()


def test_store_delete_caller_rollback_and_default_commit(db):
    discover()
    store.write_batch([], [message(image=True)])
    assert stored(db) is not None and count(db, "image_queue") == 1
    conn = db()
    try:
        assert store.delete_message(CHAT_ID, 101, observed_at=OBSERVED, conn=conn) == 1
        assert not conn.closed
        assert conn.execute("SELECT count(*) AS n FROM messages").fetchone()["n"] == 0
        assert stored(db) is not None
        conn.rollback()
    finally:
        conn.close()
    assert stored(db) is not None and count(db, "image_queue") == 1
    assert fetch(db, "SELECT excluded FROM message_ingest_state WHERE chat_id = %s AND msg_id = 101", (CHAT_ID,))["excluded"] is False
    assert store.delete_message(CHAT_ID, 101, observed_at=OBSERVED) == 1
    assert stored(db) is None and count(db, "image_queue") == 0
    assert fetch(db, "SELECT excluded FROM message_ingest_state WHERE chat_id = %s AND msg_id = 101", (CHAT_ID,))["excluded"] is True


def test_enabled_audience_is_only_visible_to_matching_verified_group(db, monkeypatch):
    save(ready_source())
    assert CHAT_ID in groups.website_chat_ids([GROUP])
    assert CHAT_ID not in groups.website_chat_ids(["B27-CSE-01"])
    assert CHAT_ID not in groups.website_chat_ids([])
    monkeypatch.setattr(groups, "auto_group", lambda _: "B27-CSE-01")
    assert CHAT_ID not in groups.scoped_chat_ids("tg:other", 999)


def test_missing_source_cannot_be_configured_or_requested(db):
    with pytest.raises(state.SourceNotFound):
        state.save_configuration(CHAT_ID, GROUP, enabled=False, expected_version=0, expected_generation=0)
    with pytest.raises(state.SourceNotFound):
        state.request_history(CHAT_ID, expected_version=0, expected_generation=0)
    assert not state.allowed(CHAT_ID)


def test_account_offline_blocks_enable_without_modifying_configuration(db):
    source = ready_source()
    state.heartbeat(connected=False)
    with pytest.raises(state.SourceUnavailable):
        save(source)
    current = state.get_source(CHAT_ID)
    for key in ("enabled", "generation", "config_version", "group_code"):
        assert current[key] == source[key]


def test_catalog_does_not_import_legacy_sources_or_personal_dialogs(db):
    seed_legacy()
    state.upsert_catalog([{"raw_chat_id": 555, "kind": "dialog", "title": "Private conversation",
                           "status": "ACTIVE", "link": None}], observed_at=now())
    assert state.list_sources() == []
    assert count(db, "chats") == 1
    assert stored(db, LEGACY_ID) is not None


def native_snapshot(text="Durable robotics laboratory event version A", *, msg_id=101):
    return normalize_message({"id": msg_id, "chatId": RAW_CHAT_ID,
                              "time": int(OBSERVED.timestamp() * 1000),
                              "sender": 9, "text": text, "attaches": []}, RAW_CHAT_ID).to_dict()


def admit(key, *, kind="message", msg_id=101, raw_id=RAW_CHAT_ID, observed_at=None, **extra):
    state.receive_event({"kind": kind, "raw_chat_id": raw_id, "message_ids": [msg_id], **extra},
                        observed_at=observed_at or now(), event_key=key)


def fetch_event(snapshot=None, *, observed_at=None):
    event = state.next_event()
    assert event is not None
    state.begin_fetch(event["id"], observed_at or now())
    state.save_fetched(event["id"], snapshot or native_snapshot())
    return event


def inbox(db, event_id):
    return fetch(db, "SELECT * FROM max_inbox WHERE id=%s", (event_id,))


def test_native_inbox_two_edits_and_return_to_original_content(db):
    save(ready_source())
    captions = ["Durable robotics laboratory event version A",
                "Durable robotics laboratory event version B",
                "Durable robotics laboratory event version A"]
    original = now()
    ids = []
    for index, caption in enumerate(captions):
        observation = original + timedelta(seconds=index)
        admit(f"native-edit:{index}", observed_at=observation)
        event = fetch_event(native_snapshot(caption), observed_at=observation)
        ids.append(event["id"])
        state.apply_event(event["id"])
        assert stored(db)["text"] == caption
        processed = inbox(db, event["id"])
        assert processed["processed_at"] is not None and processed["payload"] is None
        identity = fetch(db, "SELECT * FROM max_message_state WHERE chat_id=%s AND msg_id=101", (CHAT_ID,))
        assert identity["last_live_id"] == event["id"]
        assert not identity["deleted"]
    assert ids == sorted(set(ids))
    assert count(db, "messages") == 1


def test_explicit_native_delete_before_create_is_permanent(db):
    save(ready_source())
    admit("delete-first", kind="removed")
    deleted = state.next_event()
    state.apply_event(deleted["id"])
    assert stored(db) is None
    identity = fetch(db, "SELECT * FROM max_message_state WHERE chat_id=%s AND msg_id=101", (CHAT_ID,))
    assert identity["deleted"]
    admit("late-create")
    event = fetch_event()
    state.apply_event(event["id"])
    assert stored(db) is None
    assert count(db, "image_queue") == 0
    assert count(db, "max_publish_queue") == 0
    assert inbox(db, event["id"])["payload"] is None


def test_off_generation_rejects_previously_fetched_snapshot(db):
    enabled = save(ready_source())
    admit("pre-off")
    event = fetch_event()
    disabled = save(enabled, enabled=False)
    current = save(disabled)
    assert current["generation"] > enabled["generation"]
    state.apply_event(event["id"])
    assert stored(db) is None
    assert count(db, "max_publish_queue") == 0
    assert inbox(db, event["id"])["processed_at"] is not None


def test_known_explicit_removal_is_admitted_while_disabled(db):
    enabled = save(ready_source())
    admit("initial-content")
    event = fetch_event()
    state.apply_event(event["id"])
    save(enabled, enabled=False)
    admit("off-removal", kind="removed")
    removal = state.next_event()
    assert removal is not None
    state.apply_event(removal["id"])
    assert stored(db) is None
    assert fetch(db, "SELECT deleted FROM max_message_state WHERE chat_id=%s AND msg_id=101", (CHAT_ID,))["deleted"]


def test_unknown_and_disabled_messages_never_persist_private_payloads(db):
    discover()
    secret = "private-body-author-attachment-MUST-NOT-PERSIST"
    for raw_id in (RAW_CHAT_ID, RAW_CHAT_ID - 1):
        admit(f"privacy:{raw_id}", raw_id=raw_id, text=secret, sender=secret, attaches=[secret])
    assert count(db, "max_inbox") == 0
    assert count(db, "messages") == 0
    assert count(db, "max_sources") == 1
    assert state.get_account()["catalog_requested"]
    save(ready_source())
    admit("enabled-sanitized", text=secret, sender=secret, attaches=[secret])
    event = state.next_event()
    assert event is not None
    assert secret not in repr(inbox(db, event["id"])["payload"])


def test_apply_commit_failure_keeps_original_observations_and_fetched_snapshot(db, monkeypatch):
    save(ready_source())
    received = now()
    observed = received + timedelta(seconds=1)
    admit("commit-retry", observed_at=received)
    event = fetch_event(native_snapshot(), observed_at=observed)
    before = inbox(db, event["id"])

    @contextmanager
    def failing_commit():
        with db() as conn:
            yield conn
            raise psycopg.OperationalError("synthetic transaction commit failure")

    with monkeypatch.context() as patch:
        patch.setattr(pg, "connection", failing_commit)
        with pytest.raises(psycopg.OperationalError):
            state.apply_event(event["id"])
    after = inbox(db, event["id"])
    assert after["received_at"] == received == before["received_at"]
    assert after["payload"] == before["payload"]
    assert after["payload"]["snapshot"] == {**native_snapshot(), "photos": []}
    assert datetime.fromisoformat(after["payload"]["fetch_observed_at"]) == observed
    assert after["processed_at"] is None
    assert stored(db) is None
    assert count(db, "max_message_state") == 0
    assert count(db, "max_publish_queue") == 0
    state.fail_event(event["id"], "processing_error")
    retried = inbox(db, event["id"])
    assert retried["payload"] == before["payload"]
    assert retried["received_at"] == received
    state.apply_event(event["id"])
    assert stored(db)["text"] == native_snapshot()["text"]
    assert inbox(db, event["id"])["payload"] is None


def test_admission_commit_failure_has_no_false_success_or_partial_inbox(db, monkeypatch):
    save(ready_source())
    observed = now()

    @contextmanager
    def failing_commit():
        with db() as conn:
            yield conn
            raise psycopg.OperationalError("synthetic admission commit failure")

    with monkeypatch.context() as patch:
        patch.setattr(pg, "connection", failing_commit)
        with pytest.raises(psycopg.OperationalError):
            admit("same-frame-key", observed_at=observed)
    assert count(db, "max_inbox") == 0
    admit("same-frame-key", observed_at=observed)
    admit("same-frame-key", observed_at=observed)
    assert count(db, "max_inbox") == 1
    event = state.next_event()
    assert event["received_at"] == observed


def test_retry_preserves_same_chat_order_without_blocking_other_chats(db):
    save(ready_source())
    other_raw_id = RAW_CHAT_ID - 1
    save(ready_source(raw_id=other_raw_id))
    admit("ordered:first")
    first = state.next_event()
    admit("ordered:second", msg_id=102)
    admit("other-chat", raw_id=other_raw_id)
    state.fail_event(first["id"], "processing_error")
    retry = inbox(db, first["id"])
    assert retry["attempts"] == 1
    assert retry["available_at"] > now()
    other = state.next_event()
    assert other["chat_id"] == 4 * 10**15 + other_raw_id
    state.begin_fetch(other["id"], now())
    state.save_fetched(other["id"], None)
    state.apply_event(other["id"])
    assert state.next_event() is None
    with db() as conn:
        conn.execute("UPDATE max_inbox SET available_at=now()-interval '1 second' WHERE id=%s", (first["id"],))
    assert state.next_event()["id"] == first["id"]
    state.begin_fetch(first["id"], now())
    state.save_fetched(first["id"], None)
    state.apply_event(first["id"])
    second = state.next_event()
    assert second["chat_id"] == CHAT_ID
    assert second["id"] > first["id"]


def test_unavailable_create_does_not_infer_deletion(db):
    save(ready_source())
    admit("available")
    event = fetch_event()
    state.apply_event(event["id"])
    admit("not-returned")
    missing = state.next_event()
    state.begin_fetch(missing["id"], now())
    state.save_fetched(missing["id"], None)
    state.apply_event(missing["id"])
    assert stored(db) is not None
    row = inbox(db, missing["id"])
    assert row["processed_at"] is not None and row["payload"] is None
    assert row["error_code"] == "message_unavailable"
    assert not fetch(db, "SELECT deleted FROM max_message_state WHERE chat_id=%s AND msg_id=101", (CHAT_ID,))["deleted"]


def test_publication_failure_retries_without_losing_committed_message(db):
    save(ready_source())
    admit("publish-outbox")
    event = fetch_event()
    state.apply_event(event["id"])
    publication = state.next_publication()
    assert publication is not None and publication["exists"]
    state.fail_publication(publication["id"])
    pending = fetch(db, "SELECT * FROM max_publish_queue WHERE id=%s", (publication["id"],))
    assert pending["attempts"] == 1 and pending["available_at"] > now()
    assert stored(db) is not None
    assert state.next_publication() is None
    with db() as conn:
        conn.execute("UPDATE max_publish_queue SET available_at=now()-interval '1 second' WHERE id=%s", (publication["id"],))
    assert state.next_publication()["id"] == publication["id"]
    state.complete_publication(publication["id"])
    assert count(db, "max_publish_queue") == 0


def test_older_fetched_observation_cannot_overwrite_newer_live_snapshot(db):
    enabled = save(ready_source())
    original = now()
    admit("old-read", observed_at=original)
    event = fetch_event(native_snapshot("Durable robotics laboratory older fetched version"), observed_at=original)
    newest = native_snapshot("Durable robotics laboratory newer fetched version")
    assert state.apply_snapshot(CHAT_ID, newest, generation=enabled["generation"],
                                observed_at=original + timedelta(seconds=10))
    state.apply_event(event["id"])
    assert stored(db)["text"] == newest["text"]


def test_new_fetch_attempt_replaces_unfinished_observation_not_successful_snapshot(db):
    save(ready_source())
    admit("fetch-attempt")
    first = now()
    event = fetch_event(observed_at=first)
    state.begin_fetch(event["id"], first + timedelta(seconds=2))
    payload = inbox(db, event["id"])["payload"]
    assert "snapshot" not in payload
    assert datetime.fromisoformat(payload["fetch_observed_at"]) == first + timedelta(seconds=2)
    with pytest.raises(state.ProtocolError):
        state.apply_event(event["id"])
    assert stored(db) is None


def test_metadata_unknown_status_closes_admission_without_storing_body(db):
    enabled = save(ready_source())
    state.receive_event({"kind": "metadata", "raw_chat_id": RAW_CHAT_ID,
                         "status": "UNCONFIRMED", "text": "private metadata body"},
                        observed_at=now(), event_key="metadata-revoke")
    source = state.get_source(CHAT_ID)
    assert not source["enabled"] and source["access"] == "unknown"
    assert source["generation"] > enabled["generation"]
    assert source["config_version"] > enabled["config_version"]
    assert source["last_error"] == "source_status_unknown"
    assert source["metadata_pending"]
    assert count(db, "max_inbox") == 0
    state.receive_event({"kind": "metadata", "raw_chat_id": RAW_CHAT_ID, "status": "ACTIVE"},
                        observed_at=now(), event_key="metadata-active-not-proof")
    assert not state.allowed(CHAT_ID), "notification cannot replace fresh metadata and history probe"


def test_invalid_known_event_clears_payload_and_keeps_visible_protocol_warning(db):
    save(ready_source())
    admit("invalid-event", kind="invalid", text="discard malformed private content")
    event = state.next_event()
    state.apply_event(event["id"])
    row = inbox(db, event["id"])
    assert row["payload"] is None and row["processed_at"] is not None
    assert row["error_code"] == "protocol_error"
    assert state.get_source(CHAT_ID)["last_error"] == "protocol_error"
    assert count(db, "messages") == 0


def archive_snapshot(msg_id, created_ms, *, raw_id=RAW_CHAT_ID, text=None, photos=(), deleted=False):
    raw = {"id": msg_id, "chatId": raw_id, "time": created_ms, "sender": 9,
           "text": text or f"Durable robotics laboratory archive lecture material number {msg_id}",
           "attaches": [{"_type": "PHOTO", "photoId": photo_id} for photo_id in photos]}
    if deleted:
        raw["status"] = "REMOVED"
    return normalize_message(raw, raw_id).to_dict()


def archive_page(anchor_ms, days, first_id, *, raw_id=RAW_CHAT_ID, size=100):
    oldest_period = anchor_ms - days * 24 * 60 * 60 * 1000
    return [archive_snapshot(first_id + index, oldest_period - index, raw_id=raw_id)
            for index in range(size)]


def archived(db, msg_id, chat_id=CHAT_ID):
    return fetch(db, "SELECT * FROM messages WHERE chat_id=%s AND msg_id=%s", (chat_id, msg_id))


def request_native_history():
    source = state.get_source(CHAT_ID)
    state.request_history(CHAT_ID, expected_version=source["config_version"],
                          expected_generation=source["generation"])


def schedule_deletion_marker(key="archive-range", *, raw_id=RAW_CHAT_ID):
    admit(key, kind="reconcile_deleted", raw_id=raw_id)
    event = state.next_event()
    assert event is not None
    state.apply_event(event["id"])
    return event


def test_full_archive_keeps_current_message_and_resumes_pages_back_two_years(db):
    save(ready_source())
    anchor = int(now().timestamp() * 1000)
    current = archive_snapshot(101, anchor - 1000, text="Durable robotics laboratory current live announcement")
    admit("current-before-archive")
    live = fetch_event(current)
    state.apply_event(live["id"])
    original_start = state.get_source(CHAT_ID)["history_started_at"]
    previous_cursor = None
    oldest_id = None
    for days, first_id in [(7, 1000), (45, 2000), (730, 3000)]:
        # A fresh scheduler selection reads committed state, as after a process restart.
        job = state.next_history("full")
        assert job is not None and job["kind"] == "full"
        assert job["history_started_at"] == original_start
        assert job["observed_at"] <= now()
        if previous_cursor is not None:
            assert job["history_before_ms"] == previous_cursor
        page = archive_page(anchor, days, first_id)
        if days == 7:
            page[0] = archive_snapshot(101, current["created_ms"], text="Durable robotics laboratory stale archive announcement")
        assert state.apply_history_page(job, page)
        source = state.get_source(CHAT_ID)
        previous_cursor = min(item["created_ms"] for item in page) + 1
        assert source["history_before_ms"] == previous_cursor
        assert source["history_status"] == "running"
        assert not state.apply_history_page(job, page), "a committed old cursor cannot replay its page"
        assert stored(db)["text"] == current["text"]
        oldest_id = page[-1]["message_id"]
        assert archived(db, oldest_id)["date"] == datetime.fromtimestamp(page[-1]["created_ms"] / 1000, timezone.utc)
    final = state.next_history("full")
    assert final["history_before_ms"] == previous_cursor
    assert state.apply_history_page(final, [])
    assert state.get_source(CHAT_ID)["history_status"] == "complete"
    assert state.next_history("full") is None
    assert archived(db, oldest_id) is not None


def test_history_page_commit_failure_rolls_back_cursor_messages_fences_images_and_outbox(db, monkeypatch):
    save(ready_source())
    job = state.next_history("full")
    before = state.get_source(CHAT_ID)
    page = archive_page(job["history_before_ms"], 7, 1000)
    page[0] = archive_snapshot(1000, page[0]["created_ms"], photos=(123,))

    @contextmanager
    def failing_commit():
        with db() as conn:
            yield conn
            raise psycopg.OperationalError("synthetic archive transaction commit failure")

    with monkeypatch.context() as patch:
        patch.setattr(pg, "connection", failing_commit)
        with pytest.raises(psycopg.OperationalError):
            state.apply_history_page(job, page)
    assert state.get_source(CHAT_ID) == before
    for table in ("messages", "max_message_state", "message_ingest_state", "image_queue", "max_publish_queue"):
        assert count(db, table) == 0
    assert state.history_current(job)
    assert state.apply_history_page(job, page)
    assert count(db, "messages") == 100
    assert count(db, "max_message_state") == 100
    assert count(db, "max_publish_queue") == 100
    assert count(db, "image_queue") == 1
    assert state.get_source(CHAT_ID)["history_before_ms"] == min(item["created_ms"] for item in page) + 1


@pytest.mark.parametrize("revoke", [False, True], ids=["off", "access-revoked"])
def test_history_fetch_cannot_commit_after_source_stops_being_allowed(db, revoke):
    source = save(ready_source())
    job = state.next_history("full")
    page = archive_page(job["history_before_ms"], 7, 1000)
    if revoke:
        state.apply_access(CHAT_ID, generation=source["generation"], access="removed", observed_at=now())
    else:
        save(source, enabled=False)
    stopped = state.get_source(CHAT_ID)
    assert not state.history_current(job)
    assert not state.apply_history_page(job, page)
    assert state.get_source(CHAT_ID) == stopped
    assert state.next_history("full") is None
    for table in ("messages", "max_message_state", "message_ingest_state", "max_publish_queue"):
        assert count(db, table) == 0


def test_off_on_generation_fences_in_flight_archive_page(db):
    enabled = save(ready_source())
    old_job = state.next_history("full")
    off = save(enabled, enabled=False)
    again = save(off)
    assert again["generation"] > old_job["generation"]
    assert not state.apply_history_page(old_job, archive_page(old_job["history_before_ms"], 730, 1000))
    assert state.get_source(CHAT_ID) == again
    assert count(db, "messages") == 0
    new_job = state.next_history("full")
    assert new_job["generation"] == again["generation"]
    assert state.apply_history_page(new_job, archive_page(new_job["history_before_ms"], 730, 1000, size=1))
    assert archived(db, 1000) is not None


@pytest.mark.parametrize("live_before_claim", [False, True])
def test_archive_never_overwrites_accepted_live_edit_even_with_later_page_observation(db, live_before_claim):
    save(ready_source())
    anchor = int(now().timestamp() * 1000)
    if not live_before_claim:
        job = state.next_history("full")
    newest = archive_snapshot(101, anchor - 7 * 24 * 60 * 60 * 1000,
                              text="Durable robotics laboratory edited live announcement")
    admit("live-during-archive")
    event = fetch_event(newest)
    state.apply_event(event["id"])
    if live_before_claim:
        job = state.next_history("full")
    page = archive_page(anchor, 7, 1000)
    page[0] = archive_snapshot(101, newest["created_ms"], text="Durable robotics laboratory outdated archive announcement")
    assert state.apply_history_page(job, page)
    assert stored(db)["text"] == newest["text"]
    identity = fetch(db, "SELECT * FROM max_message_state WHERE chat_id=%s AND msg_id=101", (CHAT_ID,))
    assert identity["last_live_id"] == event["id"]
    assert archived(db, 1099) is not None


def test_full_archive_cannot_revive_native_tombstone(db):
    save(ready_source())
    job = state.next_history("full")
    admit("delete-before-full-page", kind="removed")
    removal = state.next_event()
    state.apply_event(removal["id"])
    assert state.apply_history_page(job, [archive_snapshot(101, job["history_before_ms"] - 1000)])
    assert stored(db) is None
    assert fetch(db, "SELECT deleted FROM max_message_state WHERE chat_id=%s AND msg_id=101", (CHAT_ID,))["deleted"]
    assert count(db, "max_publish_queue") == 0


def test_timestamp_only_pagination_stall_is_visible_partial_not_skipped_millisecond(db):
    save(ready_source())
    first = state.next_history("full")
    timestamp = first["history_before_ms"] - 7 * 24 * 60 * 60 * 1000
    page = [archive_snapshot(msg_id, timestamp) for msg_id in range(1000, 1100)]
    assert state.apply_history_page(first, page)
    overlap = state.next_history("full")
    assert overlap["history_before_ms"] == timestamp + 1
    assert state.apply_history_page(overlap, page)
    partial = state.get_source(CHAT_ID)
    assert partial["history_status"] == "partial"
    assert partial["last_error"] == "history_timestamp_boundary"
    assert partial["history_before_ms"] == timestamp + 1
    assert count(db, "messages") == 100
    assert state.next_history("full") is None


def test_temporary_history_failure_keeps_cursor_and_separate_metadata_schedule(db):
    save(ready_source())
    first = state.next_history("full")
    assert state.apply_history_page(first, archive_page(first["history_before_ms"], 45, 1000))
    job = state.next_history("full")
    before = state.get_source(CHAT_ID)
    failed_at = now()
    state.fail_history(job, "history_error")
    failed = state.get_source(CHAT_ID)
    assert failed["history_status"] in {"pending", "running"}
    assert failed["history_before_ms"] == before["history_before_ms"]
    assert failed["history_last_id"] == before["history_last_id"]
    assert failed["metadata_available_at"] == before["metadata_available_at"]
    assert failed["checked_at"] == before["checked_at"]
    assert failed["history_available_at"] >= failed_at + timedelta(seconds=59)
    assert failed["last_error"] == "history_error"
    assert state.next_history("full") is None
    with db() as conn:
        conn.execute("UPDATE max_sources SET history_available_at=now() WHERE chat_id=%s", (CHAT_ID,))
    resumed = state.next_history("full")
    assert resumed["history_before_ms"] == job["history_before_ms"]
    assert state.apply_history_page(resumed, [])
    assert state.get_source(CHAT_ID)["history_status"] == "complete"


@pytest.mark.parametrize("invalid", ["negative-time", "beyond-cursor", "foreign-chat"])
def test_malformed_history_page_never_commits_good_prefix_or_reports_complete(db, invalid):
    save(ready_source())
    job = state.next_history("full")
    good = archive_snapshot(1000, job["history_before_ms"] - 1000)
    bad = archive_snapshot(1001, good["created_ms"])
    if invalid == "negative-time":
        bad["created_ms"] = -1
    elif invalid == "beyond-cursor":
        bad["created_ms"] = job["history_before_ms"] + 1
    else:
        bad["raw_chat_id"] = RAW_CHAT_ID - 1
    with pytest.raises(state.ProtocolError):
        state.apply_history_page(job, [good, bad])
    assert state.history_current(job)
    for table in ("messages", "max_message_state", "message_ingest_state", "max_publish_queue"):
        assert count(db, table) == 0
    state.fail_history(job, "protocol_error", terminal=True)
    failed = state.get_source(CHAT_ID)
    assert failed["history_status"] == "failed"
    assert failed["history_before_ms"] == job["history_before_ms"]
    assert failed["last_error"] == "protocol_error"
    assert state.next_history("full") is None


def test_history_scheduler_rotates_sources_and_does_not_hold_up_live_inbox(db):
    save(ready_source())
    other = save(ready_source(raw_id=RAW_CHAT_ID - 1))
    first = state.next_history("full")
    assert first["chat_id"] == CHAT_ID
    assert state.apply_history_page(first, archive_page(first["history_before_ms"], 7, 1000))
    admit("archive-yields-to-live")
    event = fetch_event()
    state.apply_event(event["id"])
    assert stored(db) is not None
    second = state.next_history("full")
    assert second["chat_id"] == other["chat_id"]
    assert state.apply_history_page(second, archive_page(second["history_before_ms"], 45, 2000, raw_id=other["raw_chat_id"]))
    again = state.next_history("full")
    assert again["chat_id"] == CHAT_ID
    assert again["history_before_ms"] == state.get_source(CHAT_ID)["history_before_ms"]


def test_startup_initializes_unrequested_archive_and_indexes_past_messages_once(db):
    enabled = save(ready_source())
    disabled = ready_source(raw_id=RAW_CHAT_ID - 1)
    official.set_official(CHAT_ID, True)
    with db() as conn:
        conn.execute("""UPDATE max_sources SET history_status='idle',history_before_ms=NULL,
                        history_started_at=NULL,history_last_id=NULL WHERE chat_id=%s""", (CHAT_ID,))
    before = state.get_source(CHAT_ID)
    upper = enabled["sync_watermark_ms"] + 10000
    state.prepare_recovery(upper)
    started = state.get_source(CHAT_ID)
    assert started["history_status"] == "pending"
    assert started["history_started_at"] is not None
    assert started["history_before_ms"] is not None
    for key in ("enabled", "access", "generation", "config_version", "group_code",
                "requires_verified_group", "legacy_chat_id", "official"):
        assert started[key] == before[key]
    assert state.get_source(disabled["chat_id"]) == disabled
    job = state.next_history("full")
    assert job is not None and job["chat_id"] == CHAT_ID
    page = archive_page(job["history_before_ms"], 730, 1000)
    assert state.apply_history_page(job, page)
    cursor = state.get_source(CHAT_ID)["history_before_ms"]
    state.prepare_recovery(upper + 10000)
    resumed = state.next_history("full")
    assert resumed["history_before_ms"] == cursor
    assert resumed["history_started_at"] == started["history_started_at"]
    assert state.apply_history_page(resumed, [])
    assert archived(db, 1099) is not None
    state.prepare_recovery(upper + 20000)
    assert state.get_source(CHAT_ID)["history_status"] == "complete"
    assert state.next_history("full") is None


@pytest.mark.parametrize("status", ["pending", "running", "complete", "partial", "failed", "cancelled"])
def test_startup_preserves_existing_full_history_status_and_durable_cursor(db, status):
    enabled = save(ready_source())
    with db() as conn:
        conn.execute("""UPDATE max_sources SET history_status=%s,history_before_ms=123,
                        history_last_id=456 WHERE chat_id=%s""", (status, CHAT_ID))
    before = state.get_source(CHAT_ID)
    state.prepare_recovery(enabled["sync_watermark_ms"] + 10000)
    after = state.get_source(CHAT_ID)
    for key in ("history_status", "history_before_ms", "history_last_id", "history_started_at",
                "history_available_at", "generation", "config_version"):
        assert after[key] == before[key]


def test_gap_recovery_uses_watermark_and_completes_interval_without_finishing_full_archive(db):
    enabled = save(ready_source())
    full = state.next_history("full")
    assert state.apply_history_page(full, archive_page(full["history_before_ms"], 45, 1000))
    full_cursor = state.get_source(CHAT_ID)["history_before_ms"]
    watermark = enabled["sync_watermark_ms"]
    upper = watermark + 10000
    state.prepare_recovery(upper)
    pending = state.get_source(CHAT_ID)
    assert pending["catchup_after_ms"] == watermark - 1
    assert pending["catchup_until_ms"] == upper
    assert pending["catchup_before_ms"] == upper
    assert pending["history_before_ms"] == full_cursor
    state.advance_watermark(upper + 1000)
    assert state.get_source(CHAT_ID)["sync_watermark_ms"] == watermark
    job = state.next_history("catchup")
    lower = job["catchup_after_ms"]
    page = [archive_snapshot(5000 + index, lower + 100 - index) for index in range(98)]
    page += [archive_snapshot(5098, lower), archive_snapshot(5099, lower - 1)]
    assert state.apply_history_page(job, page)
    complete = state.get_source(CHAT_ID)
    assert complete["catchup_status"] == "complete"
    assert complete["sync_watermark_ms"] == upper
    assert complete["history_status"] == "running"
    assert complete["history_before_ms"] == full_cursor
    assert archived(db, 5098) is not None
    assert archived(db, 5099) is None
    assert state.next_history("catchup") is None
    state.advance_watermark(upper + 1000)
    assert state.get_source(CHAT_ID)["sync_watermark_ms"] == upper + 1000
    assert state.next_history("full")["history_before_ms"] == full_cursor


def test_reconnect_extends_existing_gap_and_preserves_full_cursor_and_old_gap_lower_bound(db):
    enabled = save(ready_source())
    full = state.next_history("full")
    assert state.apply_history_page(full, archive_page(full["history_before_ms"], 7, 1000))
    full_cursor = state.get_source(CHAT_ID)["history_before_ms"]
    upper = enabled["sync_watermark_ms"] + 20000
    state.prepare_recovery(upper)
    job = state.next_history("catchup")
    assert state.apply_history_page(job, [archive_snapshot(5000 + index, upper - 1000 - index) for index in range(100)])
    old_page = state.next_history("catchup")
    state.prepare_recovery(upper + 10000)
    restarted = state.get_source(CHAT_ID)
    assert restarted["catchup_after_ms"] == enabled["sync_watermark_ms"] - 1
    assert restarted["catchup_before_ms"] == restarted["catchup_until_ms"] == upper + 10000
    assert restarted["history_before_ms"] == full_cursor
    assert restarted["sync_watermark_ms"] == enabled["sync_watermark_ms"]
    assert not state.history_current(old_page)
    assert not state.apply_history_page(old_page, [])
    next_gap = state.next_history("catchup")
    assert next_gap["catchup_before_ms"] == upper + 10000
    assert next_gap["catchup_after_ms"] == job["catchup_after_ms"]


def test_missing_watermark_recovers_unbounded_history_without_resetting_full_job(db):
    save(ready_source())
    full_before = state.get_source(CHAT_ID)
    with db() as conn:
        conn.execute("UPDATE max_sources SET sync_watermark_ms=NULL WHERE chat_id=%s", (CHAT_ID,))
    upper = int(now().timestamp() * 1000)
    state.prepare_recovery(upper)
    job = state.next_history("catchup")
    assert job["catchup_after_ms"] is None
    assert state.apply_history_page(job, archive_page(upper, 730, 1000))
    next_page = state.next_history("catchup")
    assert next_page["catchup_before_ms"] == upper - 730 * 24 * 60 * 60 * 1000 - 98
    assert state.apply_history_page(next_page, [])
    recovered = state.get_source(CHAT_ID)
    assert recovered["catchup_status"] == "complete"
    assert recovered["sync_watermark_ms"] == upper
    assert recovered["history_before_ms"] == full_before["history_before_ms"]
    assert recovered["history_status"] == full_before["history_status"]
    assert archived(db, 1099) is not None


@pytest.mark.parametrize("repeat", ["manual", "reenable"])
def test_repeat_archive_restarts_at_present_and_reaches_two_years_after_partial(db, repeat):
    enabled = save(ready_source())
    first = state.next_history("full")
    assert state.apply_history_page(first, archive_page(first["history_before_ms"], 7, 1000))
    state.fail_history(state.next_history("full"), "history_timestamp_boundary", terminal=True)
    state.prepare_recovery(enabled["sync_watermark_ms"] + 10000)
    gap = state.next_history("catchup")
    state.fail_history(gap, "history_error", terminal=True)
    failed = state.get_source(CHAT_ID)
    if repeat == "manual":
        request_native_history()
        restarted = state.get_source(CHAT_ID)
        assert restarted["catchup_status"] == "pending"
        assert restarted["catchup_after_ms"] == gap["catchup_after_ms"]
        assert restarted["catchup_before_ms"] == gap["catchup_until_ms"]
        assert restarted["last_error"] == failed["last_error"]
    else:
        save(save(failed, enabled=False))
        restarted = state.get_source(CHAT_ID)
        assert restarted["catchup_status"] == "idle"
        assert restarted["catchup_after_ms"] is None
        assert restarted["generation"] > failed["generation"]
    assert restarted["history_status"] == "pending"
    assert restarted["history_before_ms"] > failed["history_before_ms"]
    anchor = restarted["history_before_ms"]
    for days, first_id in [(7, 2000), (45, 3000), (730, 4000)]:
        page_job = state.next_history("full")
        assert state.apply_history_page(page_job, archive_page(anchor, days, first_id))
        assert state.get_source(CHAT_ID)["history_status"] == "running"
    assert state.apply_history_page(state.next_history("full"), [])
    assert state.get_source(CHAT_ID)["history_status"] == "complete"
    assert archived(db, 4099) is not None


def test_range_marker_is_processed_without_blocking_explicit_inbox_removal(db):
    save(ready_source())
    page_job = state.next_history("full")
    page = archive_page(page_job["history_before_ms"], 7, 1000)
    assert state.apply_history_page(page_job, page)
    marker = schedule_deletion_marker()
    processed = inbox(db, marker["id"])
    assert processed["processed_at"] is not None and processed["payload"] is None
    source = state.get_source(CHAT_ID)
    assert source["deletion_scan_pending"]
    assert source["deletion_scan_until_id"] == 1099
    assert source["deletion_scan_after_id"] is None
    job = state.next_deletion_scan()
    assert job["ids"] == list(range(1000, 1100))
    state.fail_deletion_scan(job)
    admit("individual-after-deferred-range", kind="removed", msg_id=1000)
    removal = state.next_event()
    assert removal is not None and removal["id"] > marker["id"]
    state.apply_event(removal["id"])
    assert archived(db, 1000) is None
    assert fetch(db, "SELECT deleted FROM max_message_state WHERE chat_id=%s AND msg_id=1000", (CHAT_ID,))["deleted"]
    assert state.get_source(CHAT_ID)["deletion_scan_pending"]
    assert state.next_deletion_scan() is None


def test_deletion_scan_only_explicit_removed_tombstones_and_preserves_missing_warning(db):
    save(ready_source())
    first = state.next_history("full")
    assert state.apply_history_page(first, archive_page(first["history_before_ms"], 7, 1000))
    second = state.next_history("full")
    assert state.apply_history_page(second, archive_page(first["history_before_ms"], 45, 1100, size=1))
    schedule_deletion_marker()
    job = state.next_deletion_scan()
    assert len(job["ids"]) == 100
    removed = archive_snapshot(1000, 0, deleted=True)
    unchanged = archive_snapshot(1001, first["history_before_ms"] - 1000,
                                  text="Durable robotics laboratory scan must not rewrite live contents")
    state.apply_deletion_scan(job, [removed, unchanged], [1000, 1001])
    source = state.get_source(CHAT_ID)
    assert source["deletion_scan_after_id"] == 1099
    assert source["deletion_scan_pending"]
    assert source["last_error"] == "deletion_reconciliation_partial"
    assert archived(db, 1000) is None
    assert archived(db, 1001)["text"] != unchanged["text"]
    assert archived(db, 1002) is not None, "absence from MSG_GET is not deletion evidence"
    next_job = state.next_deletion_scan()
    assert next_job["ids"] == [1100]
    present = archive_snapshot(1100, 0)
    state.apply_deletion_scan(next_job, [present], [1100])
    completed = state.get_source(CHAT_ID)
    assert not completed["deletion_scan_pending"]
    assert completed["last_error"] == "deletion_reconciliation_partial"
    assert archived(db, 1100) is not None
    assert state.next_deletion_scan() is None
    assert fetch(db, "SELECT deleted FROM max_message_state WHERE chat_id=%s AND msg_id=1000", (CHAT_ID,))["deleted"]


def test_range_scan_fixed_upper_bound_does_not_expand_to_later_native_ids(db):
    enabled = save(ready_source())
    first = state.next_history("full")
    assert state.apply_history_page(first, archive_page(first["history_before_ms"], 7, 1000, size=2))
    schedule_deletion_marker()
    later = archive_snapshot(9999, first["history_before_ms"] - 1000)
    assert state.apply_snapshot(CHAT_ID, later, generation=enabled["generation"], observed_at=now())
    job = state.next_deletion_scan()
    assert job["deletion_scan_until_id"] == 1001
    assert job["ids"] == [1000, 1001]
    state.apply_deletion_scan(job, [], job["ids"])
    assert not state.get_source(CHAT_ID)["deletion_scan_pending"]
    assert archived(db, 9999) is not None


def test_deletion_scan_commit_failure_rolls_back_tombstone_cursor_and_outbox_removal(db, monkeypatch):
    save(ready_source())
    history = state.next_history("full")
    assert state.apply_history_page(history, archive_page(history["history_before_ms"], 7, 1000, size=2))
    schedule_deletion_marker()
    job = state.next_deletion_scan()
    before = state.get_source(CHAT_ID)
    removed = archive_snapshot(1000, 0, deleted=True)

    @contextmanager
    def failing_commit():
        with db() as conn:
            yield conn
            raise psycopg.OperationalError("synthetic deletion scan commit failure")

    with monkeypatch.context() as patch:
        patch.setattr(pg, "connection", failing_commit)
        with pytest.raises(psycopg.OperationalError):
            state.apply_deletion_scan(job, [removed], job["ids"])
    assert state.get_source(CHAT_ID) == before
    assert archived(db, 1000) is not None
    assert not fetch(db, "SELECT deleted FROM max_message_state WHERE chat_id=%s AND msg_id=1000", (CHAT_ID,))["deleted"]
    assert count(db, "max_publish_queue") == 2
    assert state.deletion_scan_current(job)
    state.apply_deletion_scan(job, [removed], job["ids"])
    assert archived(db, 1000) is None
    assert count(db, "max_publish_queue") == 1
    assert not state.get_source(CHAT_ID)["deletion_scan_pending"]


def test_off_source_defers_range_rpc_but_does_not_block_known_explicit_removal(db):
    enabled = save(ready_source())
    history = state.next_history("full")
    assert state.apply_history_page(history, archive_page(history["history_before_ms"], 7, 1000, size=2))
    schedule_deletion_marker()
    job = state.next_deletion_scan()
    off = save(enabled, enabled=False)
    assert not state.deletion_scan_current(job)
    state.apply_deletion_scan(job, [archive_snapshot(1000, 0, deleted=True)], job["ids"])
    assert archived(db, 1000) is not None
    assert state.next_deletion_scan() is None
    assert state.get_source(CHAT_ID)["deletion_scan_after_id"] is None
    admit("individual-while-range-off", kind="removed", msg_id=1001)
    event = state.next_event()
    state.apply_event(event["id"])
    assert archived(db, 1001) is None
    save(off)
    assert not state.deletion_scan_current(job), "off/on must fence the original network observation"
    with db() as conn:
        conn.execute("UPDATE max_sources SET deletion_scan_available_at=now() WHERE chat_id=%s", (CHAT_ID,))
    resumed = state.next_deletion_scan()
    assert resumed["ids"] == job["ids"]
    assert resumed["generation"] > job["generation"]
    state.apply_deletion_scan(resumed, [archive_snapshot(1000, 0, deleted=True)], resumed["ids"])
    assert archived(db, 1000) is None
    assert not state.get_source(CHAT_ID)["deletion_scan_pending"]


def clear_native(source):
    return state.clear_history(source["chat_id"], expected_version=source["config_version"],
                               expected_generation=source["generation"])


def test_clear_preserves_policy_tombstones_legacy_and_other_sources_but_fences_all_work(db):
    seed_legacy()
    source = save(ready_source(), legacy_chat_id=LEGACY_ID)
    other = save(ready_source(raw_id=RAW_CHAT_ID + 1), group="B27")
    official.set_official(CHAT_ID, True)
    official.set_official(LEGACY_ID, True)
    anchor = int(now().timestamp() * 1000) - 1000
    live = archive_snapshot(101, anchor, photos=(123,))
    admit("clear-live-photo")
    accepted = fetch_event(live)
    state.apply_event(accepted["id"])
    other_snapshot = archive_snapshot(201, anchor, raw_id=other["raw_chat_id"])
    assert state.apply_snapshot(other["chat_id"], other_snapshot,
                                generation=other["generation"], observed_at=now())
    admit("clear-tombstone", kind="removed", msg_id=777)
    removal = state.next_event()
    state.apply_event(removal["id"])
    tombstone = fetch(db, "SELECT * FROM max_message_state WHERE chat_id=%s AND msg_id=777", (CHAT_ID,))
    assert tombstone["deleted"]
    job = image_queue.claim("maxuserbot")
    assert job is not None and job["chat_id"] == CHAT_ID
    with db() as conn:
        conn.execute("""INSERT INTO schedule_changes(message_id,kind,starts_at,summary)
                        VALUES (%s,'announcement',now(),'Synthetic course change')""", (job["message_id"],))
    admit("clear-fetched-before-confirm", msg_id=102)
    pending = fetch_event(native_snapshot(msg_id=102))
    full = state.next_history("full")
    assert full is not None and full["chat_id"] == CHAT_ID
    state.prepare_recovery(source["sync_watermark_ms"] + 10000)
    catchup = state.next_history("catchup")
    assert catchup is not None and catchup["chat_id"] == CHAT_ID
    before = state.get_source(CHAT_ID)
    legacy_before = fetch(db, "SELECT * FROM chats WHERE chat_id=%s", (LEGACY_ID,))
    other_before = state.get_source(other["chat_id"])
    assert clear_native(before) == 1
    cleared = state.get_source(CHAT_ID)
    for key in ("enabled", "access", "raw_chat_id", "group_code", "requires_verified_group", "legacy_chat_id"):
        assert cleared[key] == before[key]
    assert cleared["enabled"] and official.flags([CHAT_ID])[CHAT_ID]
    assert cleared["generation"] == before["generation"] + 1
    assert cleared["config_version"] == before["config_version"] + 1
    assert cleared["history_status"] == cleared["catchup_status"] == "cancelled"
    assert stored(db) is None and stored(db, LEGACY_ID) is not None
    assert archived(db, 201, other["chat_id"]) is not None
    assert state.get_source(other["chat_id"]) == other_before
    assert fetch(db, "SELECT * FROM chats WHERE chat_id=%s", (LEGACY_ID,)) == legacy_before
    assert fetch(db, "SELECT * FROM max_message_state WHERE chat_id=%s AND msg_id=777", (CHAT_ID,)) == tombstone
    assert fetch(db, "SELECT count(*) AS n FROM max_publish_queue WHERE chat_id=%s", (CHAT_ID,))["n"] == 0
    assert count(db, "image_queue") == count(db, "schedule_changes") == 0
    assert fetch(db, "SELECT 1 FROM embedding_queue WHERE message_id=%s", (job["message_id"],)) is None
    assert fetch(db, "SELECT 1 FROM message_embeddings WHERE message_id=%s", (job["message_id"],)) is None
    assert state.next_history("full")["chat_id"] == other["chat_id"]
    assert state.next_history("catchup")["chat_id"] == other["chat_id"]
    assert not state.history_current(full) and not state.history_current(catchup)
    assert not state.apply_history_page(full, [archive_snapshot(301, anchor)])
    assert not state.apply_history_page(catchup, [archive_snapshot(302, anchor)])
    state.apply_event(pending["id"])
    assert inbox(db, pending["id"])["processed_at"] is not None
    assert archived(db, 102) is None
    assert not state.apply_snapshot(CHAT_ID, native_snapshot(msg_id=103),
                                    generation=before["generation"], observed_at=now())
    assert not image_queue.finish(job, "Stale recognition must never resurrect cleared content")
    assert stored(db) is None and archived(db, 103) is None
    assert fetch(db, "SELECT count(*) AS n FROM max_publish_queue WHERE chat_id=%s", (CHAT_ID,))["n"] == 0


def test_clear_cancels_archive_recovery_and_range_scan_until_explicit_repeat(db):
    source = save(ready_source())
    anchor = int(now().timestamp() * 1000) - 1000
    admit("clear-repeat-initial")
    accepted = fetch_event(archive_snapshot(101, anchor))
    state.apply_event(accepted["id"])
    admit("clear-repeat-tombstone", kind="removed", msg_id=777)
    state.apply_event(state.next_event()["id"])
    schedule_deletion_marker("clear-range")
    scan = state.next_deletion_scan()
    assert scan is not None
    full = state.next_history("full")
    state.prepare_recovery(source["sync_watermark_ms"] + 10000)
    catchup = state.next_history("catchup")
    assert clear_native(state.get_source(CHAT_ID)) == 1
    assert state.allowed(CHAT_ID)
    assert state.next_history("full") is None and state.next_history("catchup") is None
    assert state.next_deletion_scan() is None
    assert not state.history_current(full) and not state.history_current(catchup)
    assert not state.deletion_scan_current(scan)
    state.apply_deletion_scan(scan, [archive_snapshot(101, anchor, deleted=True)], [101])
    identity = fetch(db, "SELECT * FROM max_message_state WHERE chat_id=%s AND msg_id=101", (CHAT_ID,))
    assert identity is None or not identity["deleted"]
    request_native_history()
    repeat = state.next_history("full")
    assert repeat is not None and repeat["generation"] > full["generation"]
    assert state.apply_history_page(repeat, [archive_snapshot(101, anchor), archive_snapshot(777, anchor)])
    assert stored(db) is not None, "manual reload must restore cleared former live content"
    assert archived(db, 777) is None, "manual reload cannot revive deletion tombstones"
    assert fetch(db, "SELECT deleted FROM max_message_state WHERE chat_id=%s AND msg_id=777", (CHAT_ID,))["deleted"]
    # New ingress remains enabled independently of the cancelled old archive.
    admit("after-clear-new-message", msg_id=102)
    fresh = fetch_event(native_snapshot(msg_id=102))
    state.apply_event(fresh["id"])
    assert archived(db, 102) is not None


@pytest.mark.parametrize("field", ["config_version", "generation"])
def test_clear_rejects_stale_expected_configuration_without_partial_deletion(db, field):
    source = save(ready_source())
    store.write_batch([], [message(image=True)])
    official.set_official(CHAT_ID, True)
    before = state.get_source(CHAT_ID)
    expected = dict(source)
    expected[field] -= 1
    with pytest.raises(state.ConfigurationConflict):
        clear_native(expected)
    assert state.get_source(CHAT_ID) == before
    assert stored(db) is not None and count(db, "image_queue") == 1
    assert official.flags([CHAT_ID])[CHAT_ID]


def test_clear_commit_failure_rolls_back_content_policy_jobs_and_outbox(db, monkeypatch):
    save(ready_source())
    official.set_official(CHAT_ID, True)
    anchor = int(now().timestamp() * 1000) - 1000
    admit("clear-rollback-photo")
    accepted = fetch_event(archive_snapshot(101, anchor, photos=(123,)))
    state.apply_event(accepted["id"])
    before = state.get_source(CHAT_ID)
    content = stored(db)
    identity = fetch(db, "SELECT * FROM max_message_state WHERE chat_id=%s AND msg_id=101", (CHAT_ID,))

    @contextmanager
    def failing_commit():
        with db() as conn:
            yield conn
            raise psycopg.OperationalError("synthetic clear transaction commit failure")

    with monkeypatch.context() as patch:
        patch.setattr(pg, "connection", failing_commit)
        with pytest.raises(psycopg.OperationalError):
            clear_native(before)
    assert state.get_source(CHAT_ID) == before and stored(db) == content
    assert fetch(db, "SELECT * FROM max_message_state WHERE chat_id=%s AND msg_id=101", (CHAT_ID,)) == identity
    assert count(db, "image_queue") == count(db, "max_publish_queue") == 1
    assert official.flags([CHAT_ID])[CHAT_ID]
    assert clear_native(before) == 1
    assert stored(db) is None and count(db, "image_queue") == count(db, "max_publish_queue") == 0


def test_clear_disabled_source_keeps_it_disabled_and_missing_source_cannot_clear_legacy(db):
    source = save(ready_source())
    store.write_batch([], [message(image=True)])
    disabled = save(source, enabled=False)
    assert clear_native(disabled) == 1
    assert not state.allowed(CHAT_ID) and not state.get_source(CHAT_ID)["enabled"]
    assert state.next_history("full") is None and state.next_history("catchup") is None
    seed_legacy()
    with pytest.raises(state.SourceNotFound):
        state.clear_history(LEGACY_ID, expected_version=0, expected_generation=0)
    assert stored(db, LEGACY_ID) is not None
