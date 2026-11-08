"""Real PostgreSQL contract tests; opt in with IMAGE_QUEUE_TEST_DSN.

Use a disposable ParadeDB database named catix_image_queue_test, never DATABASE_URL.
The full application schema (including the real embedding triggers) is applied twice.
"""

import os
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
import pytest
from psycopg.rows import dict_row

from catix.db import pg, store
from catix.ingest import noise


@pytest.fixture(scope="module")
def image_database():
    dsn = os.environ.get("IMAGE_QUEUE_TEST_DSN")
    if not dsn:
        pytest.skip("set IMAGE_QUEUE_TEST_DSN to a disposable ParadeDB database")
    with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as conn:
        assert conn.execute("SELECT current_database() AS name").fetchone()["name"] == "catix_image_queue_test"
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.execute("CREATE EXTENSION IF NOT EXISTS pg_search")
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = 'ctx_reader'").fetchone():
            conn.execute("CREATE ROLE ctx_reader")
        schema = Path(__file__).resolve().parents[1].joinpath("db/schema.sql").read_text().replace("__TZ__", "UTC")
        conn.execute(schema)
        conn.execute(schema)
    return dsn


@pytest.fixture
def db(image_database, monkeypatch):
    def connect():
        return psycopg.connect(image_database, row_factory=dict_row)

    monkeypatch.setattr(pg, "connection", connect)
    monkeypatch.setattr(noise, "enabled", lambda: True)
    with connect() as conn:
        conn.execute("TRUNCATE chats, message_ingest_state CASCADE")
        conn.execute("UPDATE image_queue_lease SET token = NULL, lease_until = NULL")
    yield connect
    with connect() as conn:
        conn.execute("TRUNCATE chats, message_ingest_state CASCADE")


def message(**changes):
    return replace(store.Message(
        100, 1, 7, datetime(2026, 1, 1, tzinfo=timezone.utc), None,
        9, "Author", None, "Original caption", None,
    ), **changes)


def write(*messages):
    store.write_batch([store.ChatInfo(100, "Image test", None)], list(messages))


def row(db, table="messages", msg_id=1):
    with db() as conn:
        if table == "messages":
            return conn.execute("SELECT * FROM messages WHERE msg_id = %s", (msg_id,)).fetchone()
        return conn.execute(f"SELECT * FROM {table}").fetchone()


def test_empty_image_caption_is_stored_and_durably_queued(db):
    assert "image_source" in store.Message.__dataclass_fields__, "Message needs optional image metadata"
    write(message(text="", image_source="tguserbot", image_refs=("opaque-image-id",)))
    stored = row(db)
    assert stored["text"] == stored["image_caption"] == ""
    assert stored["image_source"] == "tguserbot"
    assert stored["image_refs"] == ["opaque-image-id"]
    queued = row(db, "image_queue")
    assert queued["message_id"] == stored["id"]


def test_claim_finish_keeps_caption_separate_and_triggers_embedding(db):
    from importlib.util import find_spec

    assert find_spec("catix.ingest.image_queue") is not None, "durable queue API is missing"
    from catix.ingest import image_queue

    write(message(image_source="tgbot", image_refs=("telegram-file-id",)))
    with db() as conn:
        conn.execute("DELETE FROM embedding_queue")
    job = image_queue.claim("tgbot")
    assert job is not None
    assert {key: job[key] for key in ("chat_id", "msg_id", "topic_id", "refs")} == {
        "chat_id": 100, "msg_id": 1, "topic_id": 7, "refs": ["telegram-file-id"],
    }
    assert job["token"]
    assert image_queue.finish(job, "  Reading from image  ") is True
    stored = row(db)
    assert stored["image_caption"] == "Original caption"
    assert stored["image_text"] == "Reading from image"
    assert stored["text"] == "Original caption\n\n[image text, OCR]\nReading from image"
    assert row(db, "image_queue") is None
    assert row(db, "embedding_queue")["message_id"] == stored["id"]
    assert image_queue.finish(job, "Repeated output") is False


@pytest.mark.parametrize("completed", [False, True])
@pytest.mark.parametrize("metadata_edit", [False, True])
def test_unchanged_caption_refs_replay_preserves_claim_or_ocr(db, completed, metadata_edit):
    from catix.ingest import image_queue

    original = message(image_source="maxbot", image_refs=("https://max.example/image",))
    write(original)
    job = image_queue.claim("maxbot")
    if completed:
        assert image_queue.finish(job, "Recognized text")
    before = row(db)
    queued = row(db, "image_queue")
    replay = replace(original, edit_date=original.date + timedelta(seconds=1)) if metadata_edit else original
    write(replay)
    after = row(db)
    assert after["text"] == before["text"]
    assert after["image_text"] == before["image_text"]
    assert row(db, "image_queue") == queued
    if not completed:
        assert image_queue.finish(job, "Recognized text")


@pytest.mark.parametrize("completed", [False, True])
@pytest.mark.parametrize("change", [
    {"text": "Changed caption"},
    {"image_refs": ("different-opaque-id",)},
    {"image_source": "tguserbot"},
    {"image_refs": (), "image_source": None},
])
def test_changed_image_invalidates_previous_work(db, completed, change):
    from catix.ingest import image_queue

    original = message(image_source="tgbot", image_refs=("file-id",))
    write(original)
    old_job = image_queue.claim("tgbot")
    if completed:
        assert image_queue.finish(old_job, "Old OCR")
    changed = replace(original, **change)
    write(changed)
    stored = row(db)
    assert stored["text"] == stored["image_caption"] == changed.text
    assert stored["image_text"] is None
    assert stored["image_refs"] == list(changed.image_refs)
    assert image_queue.finish(old_job, "Stale OCR") is False
    if changed.image_refs:
        fresh_job = image_queue.claim(changed.image_source)
        assert fresh_job is not None
        assert fresh_job["token"] != old_job["token"]
        assert fresh_job["refs"] == list(changed.image_refs)
        assert image_queue.finish(fresh_job, "New OCR")
    else:
        assert row(db, "image_queue") is None


@pytest.mark.parametrize("older_edit", [None, datetime(2026, 1, 1, 0, 0, 1, tzinfo=timezone.utc)])
def test_stale_edit_cannot_replace_newer_caption_or_claim(db, older_edit):
    from catix.ingest import image_queue

    current = message(image_source="tgbot", image_refs=("new-file",),
                      edit_date=datetime(2026, 1, 1, 0, 0, 2, tzinfo=timezone.utc))
    write(current)
    job = image_queue.claim("tgbot")
    before = row(db)
    queued = row(db, "image_queue")
    write(replace(current, text="Older caption", image_refs=("old-file",), edit_date=older_edit))
    assert row(db) == before
    assert row(db, "image_queue") == queued
    assert image_queue.finish(job, "Current OCR")


@pytest.mark.parametrize("completed", [False, True])
@pytest.mark.parametrize("keep_source", [False, True])
def test_removing_image_with_empty_caption_cancels_work_without_storing_new_noise(db, completed, keep_source):
    from catix.ingest import image_queue

    original = message(text="", image_source="tgbot", image_refs=("file-id",))
    write(original, message(msg_id=2, text=""), message(msg_id=3, text="👍"))
    assert row(db, msg_id=2) is None
    assert row(db, msg_id=3) is None
    job = image_queue.claim("tgbot")
    if completed:
        assert image_queue.finish(job, "Old OCR")
    write(replace(original, image_refs=(), image_source="tgbot" if keep_source else None))
    assert row(db)["image_refs"] == []
    assert row(db)["text"] == ""
    assert row(db)["image_text"] is None
    assert row(db, "image_queue") is None
    assert image_queue.finish(job, "Stale OCR") is False


@pytest.mark.parametrize("caption", ["", "Caption preserved exactly  "])
def test_empty_recognition_succeeds_without_ocr_marker(db, caption):
    from catix.ingest import image_queue

    write(message(text=caption, image_source="tgbot", image_refs=("image",)))
    job = image_queue.claim("tgbot")
    assert image_queue.finish(job, "  \n ")
    assert row(db)["text"] == row(db)["image_caption"] == caption
    assert row(db)["image_text"] == ""
    assert image_queue.claim("tgbot") is None


@pytest.mark.parametrize("parallel", [False, True])
def test_only_one_global_live_claim_across_sources(db, parallel):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from catix.ingest import image_queue

    sources = ["tguserbot", "tgbot", "maxbot"]
    write(*(message(msg_id=i, image_source=source, image_refs=(f"ref-{i}",))
            for i, source in enumerate(sources, 1)))
    if parallel:
        barrier = Barrier(3)

        def claim(source):
            barrier.wait(timeout=5)
            return image_queue.claim(source)

        with ThreadPoolExecutor(max_workers=3) as pool:
            claims = list(pool.map(claim, sources))
    else:
        claims = [image_queue.claim(source) for source in sources]
    jobs = [job for job in claims if job is not None]
    assert len(jobs) == 1
    with db() as conn:
        live = conn.execute("SELECT * FROM image_queue WHERE status = 'claimed'").fetchone()
    assert (live["lease_until"] - live["available_at"]).total_seconds() >= 299
    assert all(image_queue.claim(source) is None for source in sources)
    assert image_queue.finish(jobs[0], "OCR")
    assert any(image_queue.claim(source) is not None for source in sources)


@pytest.mark.parametrize("invalidate", ["edit", "remove", "delete"])
@pytest.mark.parametrize("complete", ["finish", "fail", "discard"])
def test_invalidated_job_holds_global_lease_until_worker_returns(db, invalidate, complete):
    from catix.ingest import image_queue

    original = message(image_source="tgbot", image_refs=("file-id",))
    write(original, message(msg_id=2, image_source="maxbot", image_refs=("max-url",)))
    job = image_queue.claim("tgbot")
    if invalidate == "edit":
        write(replace(original, text="Edited caption"))
    elif invalidate == "remove":
        write(replace(original, text="", image_refs=()))
    else:
        with db() as conn:
            conn.execute("DELETE FROM messages WHERE id = %s", (job["message_id"],))
    assert image_queue.claim("maxbot") is None
    operation = getattr(image_queue, complete, None)
    assert operation is not None
    assert operation(job, *(["Stale text"] if complete == "finish" else [])) is False
    assert image_queue.claim("maxbot") is not None


def expire(db):
    with db() as conn:
        conn.execute("UPDATE image_queue SET lease_until = now() - interval '1 second' WHERE status = 'claimed'")
        conn.execute("UPDATE image_queue_lease SET lease_until = now() - interval '1 second'")


@pytest.mark.parametrize("complete", ["finish", "fail", "discard"])
def test_expired_claim_is_recovered_after_process_restart(db, complete):
    import importlib

    from catix.ingest import image_queue

    write(message(image_source="tgbot", image_refs=("file-id",)),
          message(msg_id=2, image_source="maxbot", image_refs=("max-url",)))
    stale = image_queue.claim("tgbot")
    expire(db)
    importlib.reload(image_queue)
    current = image_queue.claim("tgbot")
    assert current is not None
    assert current["token"] != stale["token"]
    operation = getattr(image_queue, complete)
    assert operation(stale, *(["Late output"] if complete == "finish" else [])) is False
    assert image_queue.claim("maxbot") is None  # A stale completion cannot release the new token.
    assert image_queue.finish(current, "Current output")


def test_expired_worker_cannot_write_before_reclaim(db):
    from catix.ingest import image_queue

    write(message(image_source="tgbot", image_refs=("file-id",)))
    stale = image_queue.claim("tgbot")
    expire(db)
    assert image_queue.finish(stale, "Expired output") is False
    assert row(db)["image_text"] is None
    assert image_queue.claim("tgbot") is not None


@pytest.mark.parametrize("crash", [False, True])
def test_three_claim_retry_ceiling_keeps_explicit_failed_job(db, crash):
    from catix.ingest import image_queue

    if not crash:
        assert hasattr(image_queue, "fail"), "retry API is missing"
    original = message(image_source="tgbot", image_refs=("file-id",))
    write(original)
    for attempt in range(1, 4):
        job = image_queue.claim("tgbot")
        assert job is not None
        assert row(db, "image_queue")["attempts"] == attempt
        if crash:
            expire(db)
        else:
            assert image_queue.fail(job) is True
            assert image_queue.fail(job) is False
            assert image_queue.finish(job, "Late success") is False
            assert image_queue.claim("tgbot") is None
            queued = row(db, "image_queue")
            with db() as conn:
                delay = conn.execute("SELECT extract(epoch FROM available_at - now()) AS seconds FROM image_queue").fetchone()["seconds"]
                assert 0 < delay <= 300
                conn.execute("UPDATE image_queue SET available_at = now() - interval '1 second'")
            if attempt < 3:
                assert queued["status"] == "pending"
    assert image_queue.claim("tgbot") is None
    assert row(db, "image_queue")["status"] == "failed"
    assert row(db, "image_queue")["attempts"] == 3
    assert row(db)["image_text"] is None
    before = row(db, "image_queue")
    write(original)
    assert row(db, "image_queue") == before
    write(replace(original, image_refs=("new-file",)))
    assert image_queue.claim("tgbot") is not None


def test_discard_cancels_claim_without_writing_ocr_or_requeueing_replay(db):
    from catix.ingest import image_queue

    assert hasattr(image_queue, "discard"), "access-removal cancellation API is missing"
    original = message(image_source="tgbot", image_refs=("file-id",))
    write(original, message(msg_id=2, image_source="maxbot", image_refs=("max-url",)))
    job = image_queue.claim("tgbot")
    before = row(db)
    assert image_queue.discard(job)
    assert row(db) == before
    assert image_queue.discard(job) is False
    assert image_queue.finish(job, "Late text") is False
    write(original)
    assert image_queue.claim("tgbot") is None
    assert image_queue.claim("maxbot") is not None


def test_unversioned_snapshot_cannot_remove_previously_edited_image(db):
    from catix.ingest import image_queue

    original = message(image_source="tgbot", image_refs=("file-id",),
                       edit_date=datetime(2026, 1, 1, 0, 0, 2, tzinfo=timezone.utc))
    write(original)
    job = image_queue.claim("tgbot")
    write(replace(original, text="", image_source=None, image_refs=(), edit_date=None))
    assert row(db)["image_refs"] == ["file-id"]
    assert row(db)["text"] == original.text
    assert row(db)["edit_date"] == original.edit_date
    assert image_queue.finish(job, "Current text") is True


@pytest.mark.parametrize("source", ["tgbot", "maxbot"])
@pytest.mark.parametrize("completed", [False, True])
def test_excluded_edit_deletes_row_and_ocr_but_keeps_live_worker_lease(db, monkeypatch, source, completed):
    import asyncio
    from unittest.mock import AsyncMock
    from catix.ingest import image_queue, images, publish

    original = message(image_source=source, image_refs=("image-ref",))
    write(original)
    job = image_queue.claim(source)
    assert job is not None
    if completed:
        assert image_queue.finish(job, "Previously indexed OCR")
    assert hasattr(store, "delete_message"), "excluded edits need version-checked row deletion"
    assert store.delete_message(100, 1, edit_date=original.date if source == "tgbot" else None) == 1
    assert row(db) is None
    assert row(db, "image_queue") is None
    assert row(db, "embedding_queue") is None
    write(message(msg_id=2, image_source="tguserbot", image_refs=("other-image",)))
    if not completed:
        assert row(db, "image_queue_lease")["token"] == job["token"]
        assert image_queue.claim("tguserbot") is None
    monkeypatch.setattr(images, "transcribe", AsyncMock(return_value="Stale OCR"))
    monkeypatch.setattr(publish, "publish", AsyncMock())
    assert not asyncio.run(images.process(job, AsyncMock(return_value=b"image")))
    publish.publish.assert_not_awaited()
    assert row(db) is None
    assert image_queue.claim("tguserbot") is not None


@pytest.mark.parametrize("edit_offset,deleted", [(None, False), (-1, False), (0, True), (1, True)])
def test_excluded_edit_only_deletes_matching_row_unless_newer_is_known(db, edit_offset, deleted):
    from catix.ingest import image_queue

    current = message(image_source="tgbot", image_refs=("new-file",),
                      edit_date=datetime(2026, 1, 1, 0, 0, 2, tzinfo=timezone.utc))
    write(current, message(msg_id=2, text="Other message"))
    store.write_batch([store.ChatInfo(200, "Other chat", None)], [replace(current, chat_id=200)])
    job = image_queue.claim("tgbot")
    before, queued = row(db), row(db, "image_queue")
    edit_date = None if edit_offset is None else current.edit_date + timedelta(seconds=edit_offset)
    assert store.delete_message(100, 1, edit_date=edit_date) == int(deleted)
    with db() as conn:
        assert conn.execute("SELECT 1 FROM messages WHERE chat_id = 200 AND msg_id = 1").fetchone()
    assert row(db, msg_id=2) is not None
    if not deleted:
        assert row(db) == before
        assert row(db, "image_queue") == queued
    assert image_queue.finish(job, "Current OCR") is not deleted


@pytest.mark.parametrize("source", ["tgbot", "maxbot"])
def test_exclusion_before_original_write_survives_replay(db, source):
    original = message(image_source=source, image_refs=("old-image",))
    # No chat/message row exists yet; the exclusion must still be durable.
    store.delete_message(100, 1, edit_date=original.date if source == "tgbot" else None)
    write(original)
    assert row(db) is None
    assert row(db, "image_queue") is None
    assert row(db, "embedding_queue") is None


@pytest.mark.parametrize("source", ["tgbot", "maxbot"])
def test_newer_correction_reenters_but_stale_and_unknown_snapshots_do_not(db, source):
    assert "observed_at" in store.Message.__dataclass_fields__, "MAX needs trusted pre-await observation ordering"
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t1, t2, t3 = (t0 + timedelta(seconds=i) for i in (1, 2, 3))
    original = message(image_source=source, image_refs=("original",), observed_at=t0,
                       link="original-link", sender_link="author-link", reply_to=8)
    write(original)
    store.delete_message(100, 1, edit_date=t1 if source == "tgbot" else None, observed_at=t1)
    store.clear_chat(100)  # Routine maintenance must leave the fence intact.
    with db() as conn:
        conn.execute("DELETE FROM chats WHERE chat_id = 100")
    write(replace(original, observed_at=None))
    write(replace(original, observed_at=t0, live_edit=True))
    write(replace(original, observed_at=t2))  # A later history read is not an explicit correction.
    assert row(db) is None
    corrected = replace(original, text="Corrected announcement", image_refs=("corrected",),
                        edit_date=t2 if source == "tgbot" else None, observed_at=t2, live_edit=True,
                        date=t3, topic_id=99, sender_id=999, reply_to=None, link=None, sender_link=None)
    write(corrected)
    stored = row(db)
    assert stored is not None
    assert stored["image_caption"] == "Corrected announcement"
    assert stored["image_refs"] == ["corrected"]
    for key in ("date", "topic_id", "sender_id", "reply_to", "link", "sender_link"):
        assert stored[key] == getattr(original, key), key
    assert stored["edit_date"] == corrected.edit_date  # MAX creation time is never an edit version.
    # A delayed exclusion, old preparation and unknown freshness cannot undo reentry.
    store.delete_message(100, 1, edit_date=t1 if source == "tgbot" else None, observed_at=t1)
    write(original)
    write(replace(original, observed_at=None))
    assert row(db) == stored
    assert row(db, "image_queue") is not None


@pytest.mark.parametrize("source", ["tgbot", "maxbot"])
@pytest.mark.parametrize("pause", ["prepare", "write", "retry"])
@pytest.mark.parametrize("original_edit", [False, True])
def test_real_writer_exclusion_fences_suspended_work_and_allows_live_correction(db, monkeypatch, source, pause, original_edit):
    import asyncio
    import contextlib
    import threading
    from types import SimpleNamespace as NS
    from unittest.mock import AsyncMock
    from catix.ingest import writer, publish
    from catix.tgbot import bot as tg
    from catix.maxbot import bot as mx
    from tests.test_chat_image_clients import bot_message, BOT_PHOTO, max_message, MAX_IMAGE

    module = tg if source == "tgbot" else mx
    ingest = writer.Writer()
    monkeypatch.setattr(module, "writer", ingest)  # Real run, retry and wait_idle; no flush mock.
    monkeypatch.setattr(publish, "publish", AsyncMock())
    monkeypatch.setattr(tg.userbot_config, "bot_listens", lambda chat: True)
    monkeypatch.setattr(store, "topic_allowed", lambda *args: True)
    monkeypatch.setattr(mx, "_load_history", lambda *args: None)
    started, release = threading.Event(), threading.Event()
    real_write = store.write_batch
    calls = 0

    def slow_write(chats, messages):
        nonlocal calls
        calls += 1
        if calls == 1 and pause in {"write", "retry"}:
            started.set()
            if pause == "retry":
                raise psycopg.OperationalError("synthetic transient write failure")
            assert release.wait(10)
        if calls == 2 and pause == "retry":
            assert release.wait(10)
        return real_write(chats, messages)

    monkeypatch.setattr(store, "write_batch", slow_write)

    async def run():
        preparing, resume = asyncio.Event(), asyncio.Event()
        async def chat(*args):
            if pause == "prepare" and not preparing.is_set():
                preparing.set()
                await resume.wait()
            return {"title": "Study"}
        async def tg_link(*args):
            await chat()
            return None
        monkeypatch.setattr(tg, "_chat_link", tg_link)
        monkeypatch.setattr(tg, "_link", lambda msg: None)
        client = NS(chat=chat, me={"username": "catix", "user_id": 99})
        telegram = NS(me=AsyncMock(return_value=NS(username="catix", id=99)))
        async def event(text, edited=False):
            if source == "tgbot":
                msg = bot_message(photo=BOT_PHOTO, caption=text,
                                  edit_date=1767225602 if text == "Correction" else 1767225601 if edited else None)
                msg = msg.as_(telegram)
                await (tg.edited(msg) if edited else tg._save(msg))
            else:
                await mx._handle(client, client.me, {"update_type": "message_edited" if edited else "message_created",
                                                    "message": max_message(text, [MAX_IMAGE])})
        writing = asyncio.create_task(ingest.run())
        original = asyncio.create_task(event("Original caption", edited=original_edit))
        try:
            if pause == "prepare":
                await asyncio.wait_for(preparing.wait(), 2)
            else:
                assert await asyncio.to_thread(started.wait, 2)
            await event("/ask excluded", edited=True)
            assert row(db, msg_id=7) is None
            release.set()
            resume.set()
            await original
            await ingest.wait_idle(timeout=10)
            assert row(db, msg_id=7) is None
            assert row(db, "image_queue") is None
            await event("Correction", edited=True)
            await ingest.wait_idle(timeout=10)
            stored = row(db, msg_id=7)
            assert stored is not None, "a later explicit non-question edit must reenter"
            assert stored["image_caption"] == "Correction"
            assert stored["image_refs"]
            assert row(db, "image_queue") is not None
            assert stored["edit_date"] is None if source == "maxbot" else stored["edit_date"] is not None
        finally:
            release.set()
            resume.set()
            await original
            writing.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await writing
    asyncio.run(run())


@pytest.mark.parametrize("pause", ["request", "page-preparation"])
def test_max_history_read_started_before_exclusion_cannot_overwrite_later_correction(db, monkeypatch, pause):
    import asyncio
    import contextlib
    from types import SimpleNamespace as NS
    from unittest.mock import AsyncMock
    from catix.ingest import writer, publish
    from catix.maxbot import bot
    from tests.test_chat_image_clients import max_message, MAX_IMAGE

    ingest = writer.Writer()
    monkeypatch.setattr(bot, "writer", ingest)
    monkeypatch.setattr(bot, "_load_history", lambda *args: None)
    monkeypatch.setattr(publish, "publish", AsyncMock())

    async def run():
        ready, release = asyncio.Event(), asyncio.Event()
        old = max_message("Old history", [MAX_IMAGE])
        first = max_message("Page first", [MAX_IMAGE])
        first["body"]["seq"] = 6
        async def call(*args, **kwargs):
            if pause == "request":
                ready.set()
                await release.wait()
            return {"messages": [first, old]}
        async def chat(*args):
            if pause == "page-preparation" and not ready.is_set():
                ready.set()
                await release.wait()
            return {"title": "Study"}
        client = NS(call=call, chat=chat, me={"username": "catix", "user_id": 99})
        writing = asyncio.create_task(ingest.run())
        history = asyncio.create_task(bot.backfill(client, 42))
        try:
            await asyncio.wait_for(ready.wait(), 2)
            for text in ("/ask excluded", "Correction"):
                await bot._handle(client, client.me, {"update_type": "message_edited",
                                                      "message": max_message(text, [MAX_IMAGE])})
            await ingest.wait_idle()
            assert row(db, msg_id=7)["image_caption"] == "Correction"
            release.set()
            await history
            await ingest.wait_idle()
            assert row(db, msg_id=7)["image_caption"] == "Correction"
            assert row(db, msg_id=6)["image_caption"] == "Page first"  # History still ingests other rows.
        finally:
            release.set()
            await history
            writing.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await writing
    asyncio.run(run())


def test_source_edit_version_is_authoritative_over_local_observation_order(db):
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t1, t2, t3 = (t0 + timedelta(seconds=i) for i in (1, 2, 3))
    original = message(image_source="tgbot", image_refs=("original",), observed_at=t3)
    write(original)
    # Another Telegram client has a source edit but no trusted local read timestamp.
    newer = replace(original, text="Known source edit", edit_date=t1, observed_at=None)
    write(newer)
    assert row(db)["image_caption"] == newer.text
    store.delete_message(100, 1, edit_date=t2, observed_at=t1)
    write(replace(newer, edit_date=t2, observed_at=t3))
    assert row(db) is None  # An equal-version snapshot is not an explicit live correction.
    write(replace(newer, edit_date=t3, observed_at=t0))
    assert row(db)["image_caption"] == newer.text  # Source version beats reversed local order.
    store.delete_message(100, 1, edit_date=t2, observed_at=t3)
    write(replace(original, observed_at=t3, live_edit=True))
    assert row(db)["edit_date"] == t3


def test_same_second_telegram_live_correction_uses_preawait_observation(db):
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t1, t2 = (t0 + timedelta(microseconds=i) for i in (1, 2))
    original = message(image_source="tgbot", image_refs=("original",), edit_date=t0, observed_at=t0, live_edit=True)
    write(original)
    store.delete_message(100, 1, edit_date=t0, observed_at=t1)
    write(replace(original, text="Same-second correction", observed_at=t2))
    assert row(db) is not None, "Telegram timestamps have only second precision"
    assert row(db)["image_caption"] == "Same-second correction"
    write(original)  # The suspended older live edit must still lose.
    store.delete_message(100, 1, edit_date=t0, observed_at=t1)
    assert row(db)["image_caption"] == "Same-second correction"


@pytest.mark.parametrize("first", ["write", "exclude"])
def test_database_fence_serializes_exclusion_with_write_before_commit(db, monkeypatch, first):
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
    from threading import Event

    original = message(image_source="tgbot", image_refs=("original",))
    locked, release, follower_entered = Event(), Event(), Event()
    real_lock = store._lock_ingest_state

    def paused_lock(cur, keys):
        if locked.is_set():
            follower_entered.set()
            return real_lock(cur, keys)
        states = real_lock(cur, keys)
        locked.set()
        assert release.wait(5)
        return states

    monkeypatch.setattr(store, "_lock_ingest_state", paused_lock)
    def exclude():
        return store.delete_message(100, 1, edit_date=original.date)
    def save():
        write(original)
    operations = {"write": (save, exclude), "exclude": (exclude, save)}[first]
    with ThreadPoolExecutor(max_workers=2) as pool:
        leader = pool.submit(operations[0])
        try:
            assert locked.wait(2)
            follower = pool.submit(operations[1])
            assert follower_entered.wait(2)
            with pytest.raises(FutureTimeout):
                follower.result(timeout=0.1)  # A separate connection cannot cross the uncommitted fence.
        finally:
            release.set()
        leader.result(timeout=3)
        follower.result(timeout=3)
    assert row(db) is None
    assert row(db, "image_queue") is None
    assert row(db, "embedding_queue") is None
    assert row(db, "message_ingest_state")["excluded"]


def test_concurrent_reverse_order_batches_lock_keys_deterministically(db, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    start = Barrier(2)
    real_lock = store._lock_ingest_state
    def simultaneous(cur, keys):
        start.wait(timeout=3)
        return real_lock(cur, keys)
    monkeypatch.setattr(store, "_lock_ingest_state", simultaneous)
    batch = [message(msg_id=i, image_source="tgbot", image_refs=(f"image-{i}",)) for i in range(1, 17)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(write, *batch)
        b = pool.submit(write, *reversed(batch))
        a.result(timeout=5)
        b.result(timeout=5)
    with db() as conn:
        assert conn.execute("SELECT count(*) AS n FROM messages").fetchone()["n"] == len(batch)
        assert conn.execute("SELECT count(*) AS n FROM image_queue").fetchone()["n"] == len(batch)


def test_message_and_queue_insert_roll_back_together(db):
    with pytest.raises(psycopg.errors.CheckViolation):
        write(message(image_source="tgbot", image_refs=("file-id",)),
              message(msg_id=2, image_source="not-a-source", image_refs=("invalid",)))
    assert row(db) is None
    assert row(db, "image_queue") is None
    assert row(db, "embedding_queue") is None
    assert row(db, "chats") is None
    assert row(db, "message_ingest_state") is None


def test_plain_text_positional_messages_preserve_noop_replay_and_edit_behavior(db):
    plain = message()
    assert plain.image_source is None
    assert plain.image_refs == ()
    write(plain)
    with db() as conn:
        conn.execute("DELETE FROM embedding_queue")
        before = conn.execute("SELECT xmin::text AS version FROM messages").fetchone()
    write(plain)
    with db() as conn:
        assert conn.execute("SELECT xmin::text AS version FROM messages").fetchone() == before
    assert row(db, "embedding_queue") is None
    assert row(db, "image_queue") is None
    write(replace(plain, text="An edited text message"))
    assert row(db)["text"] == "An edited text message"
    assert row(db, "embedding_queue") is not None
    assert row(db, "image_queue") is None


def test_noise_cleanup_keeps_captionless_images_but_removes_plain_noise(db):
    from catix.db import init
    write(message(text="", image_source="tgbot", image_refs=("file-id",)))
    with db() as conn:
        conn.execute("INSERT INTO messages (chat_id, msg_id, date, text) VALUES (100, 2, now(), '👍')")
    init.prune_noise(["yes"])
    assert row(db) is not None
    assert row(db, "image_queue") is not None
    assert row(db, msg_id=2) is None


def test_text_deduplication_does_not_merge_different_images_with_same_caption(db):
    from catix.db import init
    write(message(image_source="tgbot", image_refs=("file-1",)),
          message(msg_id=2, image_source="tgbot", image_refs=("file-2",)),
          message(msg_id=3, text="Repeated plain message"), message(msg_id=4, text="Repeated plain message"))
    init.dedupe(["yes"])
    assert row(db) is not None and row(db, msg_id=2) is not None
    assert row(db, msg_id=3) is None and row(db, msg_id=4) is not None


@pytest.mark.parametrize("source", ["tguserbot", "tgbot", "maxbot"])
def test_writer_to_ocr_to_real_bm25_and_embedding_queue(db, monkeypatch, source):
    """Real storage/index and HTTP decoding; only the messenger bytes/model reply are synthetic."""
    import asyncio
    import contextlib
    import io
    import json

    import httpx
    from PIL import Image
    from catix.ingest import image_queue, images, writer

    image = io.BytesIO()
    Image.new("RGB", (100, 100), "white").save(image, format="PNG")
    recognized = "Квантовая робототехника\n12 ноября, 18:30, аудитория 305"
    client = httpx.AsyncClient
    monkeypatch.setattr(images.httpx, "AsyncClient", lambda **kwargs: client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps({"text": recognized}, ensure_ascii=False)}}]})
    ), **kwargs))

    async def run():
        ingest = writer.Writer()
        writing = asyncio.create_task(ingest.run())
        try:
            await ingest.put(store.ChatInfo(100, "Image test", None),
                             message(text="", image_source=source, image_refs=("opaque-id",)))
            await ingest.wait_idle()
        finally:
            writing.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await writing
        job = image_queue.claim(source)
        assert job is not None
        async def download(job, ref):
            assert ref == "opaque-id"
            return image.getvalue()
        assert await images.process(job, download)
    asyncio.run(run())
    stored = row(db)
    assert stored["image_caption"] == ""
    assert stored["image_text"] == recognized
    assert stored["sender_id"] == 9 and stored["topic_id"] == 7
    assert row(db, "embedding_queue")["message_id"] == stored["id"]
    assert stored["id"] in store._bm25("робототехника", [100], None, None)
    assert store._bm25("робототехника", [999], None, None) == []
