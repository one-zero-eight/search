"""Ingestion and follower behavior using actual policy decisions."""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS

import pytest
from telethon.tl.types import Chat, Message, MessageReplyHeader, PeerChat

from catix import userbot_config as config
from catix.tguserbot import userbot


ENTITY = Chat(id=42, title="Forum", photo=None, participants_count=2, date=datetime.now(timezone.utc), version=1)


@pytest.fixture(autouse=True)
def no_source_request_database(monkeypatch):
    monkeypatch.setattr(userbot.source_requests, "backfill_pending", lambda: set())
    monkeypatch.setattr(userbot.source_requests, "backfill_done", lambda chat_id: None)


def message(n, topic):
    return Message(id=n, peer_id=PeerChat(42), date=datetime.now(timezone.utc), message="history",
                   reply_to=MessageReplyHeader(reply_to_msg_id=topic, forum_topic=True))


def test_buffered_history_rechecks_policy_even_if_shared_cache_is_stale(monkeypatch):
    rows = {-42: (None, "auto", {"default": "store", "topics": {}})}
    monkeypatch.setattr(config, "_rows", lambda: rows)
    monkeypatch.setattr(config, "userbot_chat_ids", lambda: {-42})
    monkeypatch.setattr(userbot.store, "last_msg_id", lambda *args: 0)
    stored = []
    monkeypatch.setattr(userbot.store, "upsert_messages", lambda batch: stored.extend(batch))
    config._forget()
    async def messages(*args, **kwargs):
        yield message(1, 7)
        yield message(2, 8)
        rows[-42] = (None, "auto", {"default": "store", "topics": {"7": "off"}})
    result = asyncio.run(userbot._sync_stream(NS(iter_messages=messages), ENTITY, -42, None))
    assert result == 1
    assert [row.msg_id for row in stored] == [2]
    config._forget()


def test_follower_detects_store_default_exclusion_change(monkeypatch):
    rows = {-42: (None, "auto", {"default": "store", "topics": {"7": "off"}})}
    monkeypatch.setattr(config, "_rows", lambda: rows)
    monkeypatch.setattr(config, "userbot_chat_ids", lambda: {-42})
    monkeypatch.setattr(config, "meta", lambda key: None)
    monkeypatch.setattr(userbot.store, "upsert_chat", lambda *args: None)
    backfills, pauses = [], []
    async def resolve(client, ids):
        return [ENTITY] if -42 in ids else []
    async def backfill(client, entity, topics):
        backfills.append(topics)
    sleep = asyncio.sleep
    async def pause(delay):
        pauses.append(delay)
        await sleep(0)
        await sleep(0)  # Let startup replay release its task slot before the next poll.
        if len(pauses) == 1:
            rows[-42] = (None, "auto", {"default": "store", "topics": {}})
        else:
            raise asyncio.CancelledError
    monkeypatch.setattr(userbot, "_resolve", resolve)
    monkeypatch.setattr(userbot, "_backfill", backfill)
    monkeypatch.setattr(userbot.asyncio, "sleep", pause)
    config._forget()
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(userbot._follow_choice(NS(), {}))
    assert backfills == [None, None], "Startup and a changed exclusion must both replay history"
    config._forget()


def test_policy_change_backfill_does_not_skip_newly_allowed_old_messages(monkeypatch):
    rows = {-42: (None, "auto", {"default": "store", "topics": {}})}
    monkeypatch.setattr(config, "_rows", lambda: rows)
    monkeypatch.setattr(config, "userbot_chat_ids", lambda: {-42})
    monkeypatch.setattr(userbot.store, "last_msg_id", lambda *args: 900)
    monkeypatch.setattr(userbot.store, "upsert_chat", lambda *args: None)
    monkeypatch.setattr(userbot.store, "mark_synced", lambda *args: None)
    stored, requests = [], []
    monkeypatch.setattr(userbot.store, "upsert_messages", lambda batch: stored.extend(batch))
    async def messages(*args, **kwargs):
        requests.append(kwargs)
        if kwargs.get("min_id", 0) < 100:
            yield message(100, 7)
    config._forget()
    asyncio.run(userbot._backfill(NS(iter_messages=messages), ENTITY, None))
    assert [row.msg_id for row in stored] == [100]
    assert "min_id" not in requests[0] and "offset_date" in requests[0]
    config._forget()


def test_follower_retries_scope_change_that_arrives_during_active_backfill(monkeypatch):
    rows = {-42: (None, "auto", {"default": "off", "topics": {"1": "store"}})}
    monkeypatch.setattr(config, "_rows", lambda: rows)
    monkeypatch.setattr(config, "userbot_chat_ids", lambda: {-42})
    monkeypatch.setattr(config, "meta", lambda key: None)
    monkeypatch.setattr(userbot.store, "upsert_chat", lambda *args: None)
    backfills, pauses = [], []
    release = asyncio.Event()
    async def resolve(client, ids):
        return [ENTITY] if -42 in ids else []
    async def backfill(client, entity, topics):
        backfills.append(topics)
        if len(backfills) == 1:
            await release.wait()
    sleep = asyncio.sleep
    async def pause(delay):
        pauses.append(delay)
        await sleep(0)
        if len(pauses) == 1:
            rows[-42] = (None, "auto", {"default": "off", "topics": {"1": "store", "7": "store"}})
        elif len(pauses) == 2:
            rows[-42] = (None, "auto", {"default": "off", "topics": {"1": "store", "7": "store", "8": "store"}})
        elif len(pauses) == 3:
            release.set()
            await sleep(0)
            await sleep(0)  # Let completion callback release the chat's backfill slot.
        else:
            raise asyncio.CancelledError
    monkeypatch.setattr(userbot, "_resolve", resolve)
    monkeypatch.setattr(userbot, "_backfill", backfill)
    monkeypatch.setattr(userbot.asyncio, "sleep", pause)
    config._forget()
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(userbot._follow_choice(NS(), {}))
    assert backfills == [[1], [1, 7, 8]]
    config._forget()


@pytest.mark.parametrize("topics", [None, [1, 7]])
def test_listen_startup_replays_window_despite_live_high_watermark(monkeypatch, topics):
    policy = ({"default": "store", "topics": {"8": "search"}} if topics is None else
              {"default": "search", "topics": {"1": "store", "7": "store"}})
    rows = {
        -42: (None, "userbot", policy),
        -43: (None, "bot", None),
        -44: (None, "search", None),
        -45: (None, "auto", {"default": "off", "topics": {}}),
        -46: (None, "auto", None),  # Not in the userbot account's dialogs.
    }
    monkeypatch.setattr(config, "_rows", lambda: rows)
    monkeypatch.setattr(config, "userbot_chat_ids", lambda: {-42, -43, -44, -45})
    monkeypatch.setattr(config, "meta", lambda key: None)
    monkeypatch.setattr(userbot.store, "upsert_chat", lambda *args: None)
    synced, stored, requests = [], {}, []
    monkeypatch.setattr(userbot.store, "mark_synced", synced.append)

    def save(batch):
        stored.update((row.msg_id, row) for row in batch)

    def last_id(*args):
        raise AssertionError("Startup replay must not use a high-water mark advanced by live writes")

    monkeypatch.setattr(userbot.store, "last_msg_id", last_id)
    monkeypatch.setattr(userbot.store, "upsert_messages", save)

    class Client:
        async def get_entity(self, chat_id):
            assert chat_id == -42, "Bot-only, search-only, disabled and nonmember chats must not be fetched"
            return ENTITY

        async def iter_messages(self, entity, **kwargs):
            requests.append(kwargs)
            assert kwargs["reverse"] is True
            assert "min_id" not in kwargs
            cutoff = datetime.now(timezone.utc) - timedelta(days=userbot.settings.tg_sync_days)
            assert abs((kwargs["offset_date"] - cutoff).total_seconds()) < 5
            for msg_id, topic in ((100, 7), (101, 8), (102, 1)):
                yield message(msg_id, topic)

    sleep = asyncio.sleep

    async def scenario():
        entities = {}
        pauses = 0

        async def pause(delay):
            nonlocal pauses
            # A live message is stored after registration but before the history task runs.
            if pauses == 0:
                assert entities == {-42: ENTITY}
                save([userbot._to_store(message(900, 7), -42, ENTITY)])
            pauses += 1
            await sleep(0)
            await sleep(0)  # Let the completed backfill release its task slot.
            if pauses == 2:
                raise asyncio.CancelledError

        monkeypatch.setattr(userbot.asyncio, "sleep", pause)
        with pytest.raises(asyncio.CancelledError):
            await userbot._follow_choice(Client(), entities)

    config._forget()
    try:
        # A reconnect creates a new follower and must replay again, not trust the live max id.
        asyncio.run(scenario())
        asyncio.run(scenario())
        assert set(stored) == {100, 102, 900}
        assert synced == [-42, -42]
        assert len(requests) == (2 if topics is None else 4)
        assert {request.get("reply_to") for request in requests} == ({None} if topics is None else {None, 7})
    finally:
        config._forget()
