"""Real Telegram result conversion and policy checks, no Telegram or database I/O."""

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace as NS

import pytest
from telethon.tl.types import Chat, Message, MessageReplyHeader, PeerChat

from catix import userbot_config as config
from catix.tguserbot import userbot


ENTITY = Chat(id=42, title="Forum", photo=None, participants_count=2, date=datetime.now(timezone.utc), version=1)


def message(n, topic):
    msg = Message(id=n, peer_id=PeerChat(42), date=datetime.now(timezone.utc), message=f"topic {topic}",
                  reply_to=MessageReplyHeader(reply_to_msg_id=topic, forum_topic=True) if topic else None)
    async def get_chat():
        return ENTITY
    msg.get_chat = get_chat
    return msg


@pytest.mark.parametrize("global_search", [False, True])
def test_live_search_filters_off_topics_and_keeps_store_search_general(monkeypatch, global_search):
    rows = {-42: (None, "auto", {"default": "search", "topics": {"1": "off", "7": "store", "8": "off"}})}
    ids = {-42, -43, -44, -45} if global_search else {-42}
    monkeypatch.setattr(config, "_rows", lambda: rows)
    monkeypatch.setattr(config, "userbot_chat_ids", lambda: ids)
    monkeypatch.setattr(config, "searchable_chats", lambda: ids)
    config._forget()
    calls = []
    async def messages(entity, **kwargs):
        calls.append(entity)
        for n, topic in enumerate([None, 7, 8, 99], 1):
            yield message(n, topic)
    async def get_entity(chat):
        return ENTITY
    result = asyncio.run(userbot._search_chats(NS(iter_messages=messages, get_entity=get_entity),
        {"chat_ids": sorted(ids), "keywords": ["topic"], "per_chat": 10}))
    assert [hit["msg_id"] for hit in result["hits"]] == [2, 4]
    assert all(hit["chat_id"] == -42 for hit in result["hits"])
    assert calls == ([None] if global_search else [ENTITY])
    config._forget()


@pytest.mark.parametrize("global_search", [False, True])
@pytest.mark.parametrize("revocation", ["topic", "chat", "membership"])
def test_live_search_rechecks_buffered_hits_after_revocation(monkeypatch, global_search, revocation):
    rows = {-42: (None, "auto", {"default": "search", "topics": {}})}
    ids = {-42, -43, -44, -45} if global_search else {-42}
    monkeypatch.setattr(config, "_rows", lambda: rows)
    monkeypatch.setattr(config, "userbot_chat_ids", lambda: set(ids))
    monkeypatch.setattr(config, "searchable_chats", lambda: set(ids))
    config._forget()
    async def messages(entity, **kwargs):
        yield message(1, 7)
        yield message(2, 8)
        # Simulate another process changing policy: even a cached per-hit check is stale.
        if revocation == "topic":
            rows[-42] = (None, "auto", {"default": "search", "topics": {"7": "off"}})
        elif revocation == "chat":
            rows.clear()
        else:
            ids.discard(-42)
    async def get_entity(chat):
        return ENTITY
    result = asyncio.run(userbot._search_chats(NS(iter_messages=messages, get_entity=get_entity),
        {"chat_ids": sorted(ids), "keywords": ["topic"], "per_chat": 10}))
    assert [hit["msg_id"] for hit in result["hits"]] == ([2] if revocation == "topic" else [])
    config._forget()
