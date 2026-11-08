"""Ingestion and follower behavior using actual policy decisions."""

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace as NS

import pytest
from telethon.tl.types import Chat, Message, MessageReplyHeader, PeerChat

from catix import userbot_config as config
from catix.tguserbot import userbot


ENTITY = Chat(id=42, title="Forum", photo=None, participants_count=2, date=datetime.now(timezone.utc), version=1)


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
    assert backfills == [None], "None fetch scope alone hides changes to its excluded topics"
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
    assert backfills == [[1, 7], [1, 7, 8]]
    config._forget()
