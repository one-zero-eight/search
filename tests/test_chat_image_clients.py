"""Chat image ingestion adapters: no messenger, model, database or CDN traffic."""
import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace as NS
from unittest.mock import ANY, AsyncMock, Mock

import pytest
from telethon.tl.custom.message import Message as TgMessage
from telethon.tl.types import (
    Chat, Document, DocumentAttributeAnimated, DocumentAttributeFilename,
    DocumentAttributeSticker, DocumentAttributeVideo, InputStickerSetEmpty,
    MessageMediaDocument, MessageMediaPhoto, MessageMediaWebPage, PeerChat,
    Photo, PhotoSize, WebPageEmpty,
)

from catix.tguserbot import userbot
from catix.ingest.images import download_url as real_download_url

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
ENTITY = Chat(id=42, title="Study", photo=None, participants_count=2, date=NOW, version=1)


def tg_message(media=None, text="", **kwargs):
    return TgMessage(id=7, peer_id=PeerChat(42), date=NOW, message=text, media=media, **kwargs)


def photo(id=11):
    return MessageMediaPhoto(photo=Photo(id=id, access_hash=1, file_reference=b"ref", date=NOW,
                                  sizes=[PhotoSize(type="x", w=100, h=100, size=100)], dc_id=1))


def document(mime="image/png", attributes=(), size=100):
    return MessageMediaDocument(document=Document(id=12, access_hash=1, file_reference=b"ref", date=NOW,
                                        mime_type=mime, size=size, dc_id=1, attributes=list(attributes)))


@pytest.mark.parametrize("media,ref", [
    (photo(), "photo:11"),
    (document(), "document:12"),
    (document("image/jpeg"), "document:12"),
    (document("image/webp"), "document:12"),
])
@pytest.mark.parametrize("caption", ["", "Original caption"])
def test_userbot_stores_image_metadata_without_inline_ocr(media, ref, caption):
    row = userbot._to_store(tg_message(media, caption), -42, ENTITY)
    assert row is not None
    assert row.text == caption
    assert row.image_source == "tguserbot"
    assert row.image_refs == (ref,)
    assert row.msg_id == 7 and row.date == NOW


@pytest.mark.parametrize("media", [
    document("image/gif"),
    document(attributes=[DocumentAttributeSticker(alt="x", stickerset=InputStickerSetEmpty())]),
    document(attributes=[DocumentAttributeAnimated()]),
    document(attributes=[DocumentAttributeVideo(duration=1, w=100, h=100)]),
    MessageMediaWebPage(WebPageEmpty(id=15)),
])
def test_userbot_does_not_queue_stickers_animation_or_web_previews(media):
    row = userbot._to_store(tg_message(media, "caption"), -42, ENTITY)
    assert row.text == "caption"
    assert row.image_refs == ()


def test_userbot_image_file_keeps_filename():
    row = userbot._to_store(tg_message(document(attributes=[DocumentAttributeFilename("schedule.png")]), "caption"), -42, ENTITY)
    assert row.text == "caption\n[file: schedule.png]"
    assert row.image_refs == ("document:12",)


def test_userbot_empty_edit_clears_old_image_but_empty_new_is_ignored():
    assert userbot._to_store(tg_message(), -42, ENTITY) is None
    row = userbot._to_store(tg_message(edit_date=NOW), -42, ENTITY)
    assert row is not None
    assert row.text == "" and row.image_refs == ()


@pytest.mark.parametrize("media,ref,problem", [
    (photo(22), "photo:11", "changed"),
    (document(size=11 * 1024 * 1024), "document:12", "size"),
    (photo(), "photo:11", None),
])
def test_userbot_download_refetches_exact_message_and_checks_metadata(media, ref, problem):
    client = NS(get_messages=AsyncMock(return_value=tg_message(media)), download_media=AsyncMock())

    async def download(message, file):
        file.write(b"image")
    client.download_media.side_effect = download
    job = {"chat_id": -42, "msg_id": 7}
    if problem:
        with pytest.raises(ValueError, match=problem):
            asyncio.run(userbot._download_image(client, job, ref))
        client.download_media.assert_not_awaited()
    else:
        assert asyncio.run(userbot._download_image(client, job, ref)) == b"image"
    client.get_messages.assert_awaited_once_with(-42, ids=7)


def test_userbot_live_worker_checks_current_permissions_and_stops_before_client(monkeypatch):
    from catix.ingest import images
    order, workers, handlers, saved = [], [], [], []
    wanted = {-42: None}
    topic_ok = [True]
    monkeypatch.setattr(userbot.userbot_config, "userbot_reads", lambda: wanted)
    monkeypatch.setattr(userbot.store, "topic_allowed", lambda chat, topic: topic_ok[0])
    monkeypatch.setattr(userbot.store, "upsert_messages", lambda rows: saved.extend(rows))
    monkeypatch.setattr(userbot.publish, "publish", AsyncMock())
    monkeypatch.setattr(userbot, "_publish_dialogs", AsyncMock())
    monkeypatch.setattr(userbot, "_seed", AsyncMock())

    async def idle(*args):
        await asyncio.Event().wait()

    async def follow(client, entities):
        entities[-42] = ENTITY
        await idle()

    async def worker(source, download, allowed=None):
        workers.append(source)
        assert await allowed({"chat_id": -42, "topic_id": None})
        topic_ok[0] = False
        assert not await allowed({"chat_id": -42, "topic_id": 99})
        topic_ok[0] = True
        wanted.clear()
        assert not await allowed({"chat_id": -42, "topic_id": None})
        wanted[-42] = None
        try:
            await idle()
        finally:
            await asyncio.sleep(0)
            order.append("worker stopped")

    class Client:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            order.append("client closed")
        start = AsyncMock()
        def add_event_handler(self, callback, event):
            handlers.append(callback)
        async def run_until_disconnected(self):
            await asyncio.sleep(0)
            event = NS(chat_id=-42, message=tg_message(photo()))
            await handlers[0](event)
            topic_ok[0] = False
            await handlers[0](event)
            topic_ok[0] = True
            wanted.clear()  # The entities poll is stale; current choice must win.
            await handlers[0](event)
            await handlers[0](NS(chat_id=-999, message=tg_message(photo())))

    monkeypatch.setattr(userbot, "_client", lambda **kwargs: Client())
    monkeypatch.setattr(userbot, "_follow_choice", follow)
    monkeypatch.setattr(userbot, "_serve_search", idle)
    monkeypatch.setattr(userbot, "_heartbeat", idle)
    monkeypatch.setattr(images, "run", worker, raising=False)
    asyncio.run(userbot._listen_once())
    assert workers == ["tguserbot"]
    assert order == ["worker stopped", "client closed"]
    assert len(saved) == 1 and saved[0].image_refs == ("photo:11",)


def bot_message(**kwargs):
    from aiogram.types import Message
    return Message.model_validate({"message_id": 7, "date": NOW,
        "chat": {"id": -10042, "type": "supergroup", "title": "Study"}, **kwargs})


@pytest.fixture
def tgbot(monkeypatch):
    from catix.tgbot import bot
    monkeypatch.setattr(bot.writer, "put", AsyncMock())
    monkeypatch.setattr(bot.writer, "wait_idle", AsyncMock())
    monkeypatch.setattr(bot.store, "delete_message", Mock())
    monkeypatch.setattr(bot.userbot_config, "bot_listens", lambda chat: True)
    monkeypatch.setattr(bot.userbot_config, "register_bot_chat", Mock())
    monkeypatch.setattr(bot, "IGNORED", set())
    monkeypatch.setattr(bot.store, "topic_allowed", lambda chat, topic: True)
    return bot


BOT_PHOTO = [{"file_id": "small", "file_unique_id": "s", "width": 10, "height": 10},
             {"file_id": "large", "file_unique_id": "l", "width": 100, "height": 100}]
BOT_DOCUMENT = {"file_id": "document", "file_unique_id": "d", "mime_type": "image/png", "file_name": "schedule.png"}


@pytest.mark.parametrize("caption", [None, "caption"])
@pytest.mark.parametrize("media,refs", [(dict(photo=BOT_PHOTO), ("large",)),
                                        (dict(document=BOT_DOCUMENT), ("document",))])
def test_tgbot_saves_caption_and_image_metadata_only(tgbot, caption, media, refs):
    asyncio.run(tgbot._save(bot_message(caption=caption, **media)))
    tgbot.writer.put.assert_awaited_once()
    row = tgbot.writer.put.await_args.args[1]
    assert row.image_source == "tgbot" and row.image_refs == refs
    expected = caption or ""
    if "document" in media:
        expected = f"{expected}\n[file: schedule.png]".strip()
    assert row.text == expected


@pytest.mark.parametrize("listener,topic", [(False, True), (True, False)])
def test_tgbot_excluded_chat_or_topic_never_enqueues(tgbot, monkeypatch, listener, topic):
    monkeypatch.setattr(tgbot.userbot_config, "bot_listens", lambda chat: listener)
    monkeypatch.setattr(tgbot.store, "topic_allowed", lambda chat, thread: topic)
    asyncio.run(tgbot._save(bot_message(photo=BOT_PHOTO)))
    tgbot.writer.put.assert_not_awaited()


def test_tgbot_empty_edit_removes_ocr(tgbot):
    asyncio.run(tgbot._save(bot_message()))
    tgbot.writer.put.assert_not_awaited()
    asyncio.run(tgbot.edited(bot_message(edit_date=int(NOW.timestamp()))))
    row = tgbot.writer.put.await_args.args[1]
    assert row.text == "" and row.image_refs == () and row.edit_date == NOW


@pytest.mark.parametrize("size,stream_bytes,success", [(100, b"image", True), (11 * 1024 * 1024, b"", False), (1, b"x" * (10 * 1024 * 1024 + 1), False)], ids=["valid", "metadata-limit", "stream-limit"])
def test_tgbot_download_bounds_metadata_and_stream(tgbot, size, stream_bytes, success):
    client = NS(get_file=AsyncMock(return_value=NS(file_size=size)), download=AsyncMock())
    async def download(ref, destination):
        assert ref == "file-id"
        destination.write(stream_bytes)
    client.download.side_effect = download
    if success:
        assert asyncio.run(tgbot._download_image(client, {}, "file-id")) == b"image"
    else:
        with pytest.raises(ValueError):
            asyncio.run(tgbot._download_image(client, {}, "file-id"))
    if size > 10 * 1024 * 1024:
        client.download.assert_not_awaited()


def test_tgbot_worker_cancelled_before_bot_session_and_db_close(tgbot, monkeypatch):
    from catix.ingest import images
    from pydantic import SecretStr
    order, sources = [], []
    ready = asyncio.Event()
    client = NS(me=AsyncMock(return_value=NS(username="catix")), session=NS(aclose=None))
    client.session.close = AsyncMock(side_effect=lambda: order.append("bot closed"))
    monkeypatch.setattr(tgbot.settings, "tg_bot_token", SecretStr("test"))
    monkeypatch.setattr(tgbot, "Bot", lambda token: client)
    monkeypatch.setattr(tgbot, "set_commands", AsyncMock())
    monkeypatch.setattr(tgbot, "set_profile", AsyncMock())
    monkeypatch.setattr(tgbot.userbot_config, "seed_bot_chats", lambda: 0)
    monkeypatch.setattr(tgbot.pg, "close", lambda: order.append("db closed"))

    async def idle():
        await asyncio.Event().wait()
    async def worker(source, download, allowed=None):
        sources.append(source)
        assert await allowed({"chat_id": -10042, "topic_id": None})
        monkeypatch.setattr(tgbot.userbot_config, "bot_listens", lambda chat: False)
        assert not await allowed({"chat_id": -10042, "topic_id": None})
        ready.set()
        try:
            await idle()
        finally:
            await asyncio.sleep(0)
            order.append("worker stopped")
    async def polling(bot, **kwargs):
        await asyncio.sleep(0)
        if sources:
            await asyncio.wait_for(ready.wait(), 1)
        assert kwargs.get("close_bot_session") is False
    dispatcher = NS(message=NS(outer_middleware=lambda f: None), include_router=lambda r: None,
                    start_polling=polling, resolve_used_update_types=lambda: [])
    monkeypatch.setattr(tgbot, "Dispatcher", lambda: dispatcher)
    monkeypatch.setattr(tgbot.writer, "run", idle)
    monkeypatch.setattr(images, "run", worker, raising=False)
    asyncio.run(tgbot.run())
    assert sources == ["tgbot"]
    assert order[0] == "worker stopped"
    assert set(order[1:]) == {"bot closed", "db closed"}


def max_message(text="caption", attachments=None, **changes):
    return {"id": 7, "chatId": 42, "time": int(NOW.timestamp() * 1000),
            "sender": 3, "text": text, "attaches": attachments if attachments is not None else [MAX_IMAGE],
            **changes}


MAX_IMAGE = {"_type": "PHOTO", "photoId": 11, "baseUrl": "https://i.oneme.ru/fresh"}


@pytest.fixture
def max_media(monkeypatch):
    from catix.maxuserbot import media
    from catix.maxuserbot.client import AccountClient
    from catix.maxuserbot.models import db_chat_id

    source = {"chat_id": db_chat_id(42), "raw_chat_id": 42, "enabled": True,
              "access": "ready", "generation": 4}
    monkeypatch.setattr(media.state, "get_source", Mock(return_value=source))
    monkeypatch.setattr(media.state, "apply_snapshot", Mock(return_value=True))
    monkeypatch.setattr(media.image_queue, "discard", Mock(return_value=True))
    monkeypatch.setattr(media.images, "download_url", AsyncMock(return_value=b"image"))
    client = AccountClient.__new__(AccountClient)
    client._rpc = AsyncMock(return_value={"messages": [max_message()]})
    job = {"message_id": 17, "chat_id": source["chat_id"], "raw_chat_id": 42, "msg_id": 7,
           "generation": 4, "image_source": "maxuserbot", "image_caption": "caption",
           "refs": ["photo:11"], "token": "claim"}
    return media, client, job, source


@pytest.mark.parametrize("caption", ["", "caption", "/ask explain", "@catix explain"])
def test_maxuserbot_native_photos_refetch_fresh_url(max_media, caption):
    media, client, job, source = max_media
    job["image_caption"] = caption
    client._rpc.return_value = {"messages": [max_message(caption)]}
    assert asyncio.run(media.download(client, job, "photo:11")) == b"image"
    client._rpc.assert_awaited_once_with(71, {"chatId": 42, "messageIds": [7]})
    media.images.download_url.assert_awaited_once_with(MAX_IMAGE["baseUrl"])
    media.state.apply_snapshot.assert_not_called()


@pytest.mark.parametrize("changes", [
    {"text": "edited caption"},
    {"attaches": [{"_type": "PHOTO", "photoId": 12, "baseUrl": "https://i.oneme.ru/new"}]},
    {"attaches": []},
    {"status": "REMOVED"},
])
def test_maxuserbot_changed_or_removed_snapshot_invalidates_old_claim(max_media, changes):
    media, client, job, source = max_media
    client._rpc.return_value = {"messages": [max_message(**changes)]}
    before = datetime.now(timezone.utc)
    with pytest.raises(ValueError, match="message_changed"):
        asyncio.run(media.download(client, job, "photo:11"))
    args, kwargs = media.state.apply_snapshot.call_args
    assert args[0] == job["chat_id"] and args[1]["message_id"] == 7
    assert kwargs["generation"] == 4 and before <= kwargs["observed_at"] <= datetime.now(timezone.utc)
    assert args[1]["deleted"] == (changes.get("status") == "REMOVED")
    media.image_queue.discard.assert_called_once_with(job)
    media.images.download_url.assert_not_awaited()


def test_maxuserbot_reordered_album_rejects_old_claim(max_media):
    media, client, job, source = max_media
    job["refs"] = ["photo:11", "photo:12"]
    client._rpc.return_value = {"messages": [max_message(attachments=[
        {"_type": "PHOTO", "photoId": 12, "baseUrl": "https://i.oneme.ru/new"}, MAX_IMAGE])]} 
    with pytest.raises(ValueError, match="message_changed"):
        asyncio.run(media.download(client, job, "photo:11"))
    assert list(media.state.apply_snapshot.call_args.args[1]["photos"]) == [{"photo_id": 12}, {"photo_id": 11}]
    media.images.download_url.assert_not_awaited()


@pytest.mark.parametrize("rows", [[], [max_message(postId=9)]])
def test_maxuserbot_missing_or_comment_message_never_implies_deletion(max_media, rows):
    media, client, job, source = max_media
    client._rpc.return_value = {"messages": rows}
    with pytest.raises(ValueError, match="message_unavailable"):
        asyncio.run(media.download(client, job, "photo:11"))
    media.state.apply_snapshot.assert_not_called()
    media.images.download_url.assert_not_awaited()


@pytest.mark.parametrize("change", [{"enabled": False}, {"access": "removed"}, {"generation": 6}])
def test_maxuserbot_revoke_or_reenable_stops_before_rpc(max_media, change):
    media, client, job, source = max_media
    source.update(change)
    assert not asyncio.run(media.allowed(job))
    with pytest.raises(ValueError, match="source_unavailable"):
        asyncio.run(media.download(client, job, "photo:11"))
    client._rpc.assert_not_awaited()


def test_maxuserbot_revoke_during_refetch_stops_before_cdn(max_media):
    media, client, job, source = max_media
    async def response(*args):
        source["enabled"] = False
        return {"messages": [max_message()]}
    client._rpc.side_effect = response
    with pytest.raises(ValueError, match="source_unavailable"):
        asyncio.run(media.download(client, job, "photo:11"))
    media.images.download_url.assert_not_awaited()


@pytest.mark.parametrize("ref", ["https://i.oneme.ru/legacy", "photo:011", "photo:12", "photo:opaque"])
def test_maxuserbot_legacy_or_wrong_photo_ref_never_reaches_transport(max_media, ref):
    from catix.maxuserbot.models import ProtocolError
    media, client, job, source = max_media
    with pytest.raises(ProtocolError):
        asyncio.run(media.download(client, job, ref))
    client._rpc.assert_not_awaited()


@pytest.mark.parametrize("kind", ["VIDEO", "STICKER", "FILE"])
def test_maxuserbot_only_native_photo_attachments_are_ocr_sources(kind):
    from catix.maxuserbot.models import normalize_message
    snapshot = normalize_message(max_message(attachments=[{"_type": kind, "photoId": 11,
                                                         "baseUrl": MAX_IMAGE["baseUrl"]}]), 42)
    assert snapshot.photos == ()


def test_maxuserbot_does_not_truncate_native_album():
    from catix.maxuserbot.models import normalize_message
    snapshot = normalize_message(max_message(attachments=[dict(MAX_IMAGE, photoId=i) for i in range(11)]), 42)
    assert len(snapshot.photos) == 11


@pytest.mark.parametrize("command", ["/start", "/mygroup", "/calendar", "/clear", "/ask", "/new", "/group"])
def test_maxuserbot_dialog_notifications_ignore_commands(command):
    from catix.maxuserbot.models import normalize_event, normalize_chat
    assert normalize_chat({"type": "DIALOG", "id": 42, "lastMessage": {"text": command}}) is None
    assert normalize_event(135, {"chat": {"type": "DIALOG", "id": 42,
                                          "lastMessage": {"text": command}}}) is None


def test_maxuserbot_ocr_uses_transactional_outbox_not_best_effort_publish(max_media, monkeypatch):
    from catix.ingest import publish
    media, client, job, source = max_media
    monkeypatch.setattr(media.images, "transcribe", AsyncMock(return_value="OCR"))
    monkeypatch.setattr(media.image_queue, "finish", Mock(return_value=True))
    monkeypatch.setattr(publish, "publish", AsyncMock())
    async def download(job, ref):
        return await media.download(client, job, ref)
    assert asyncio.run(media.images.process(job, download, media.allowed))
    publish.publish.assert_not_awaited()


@pytest.mark.parametrize("caption", ["@catix explain", "/ask explain"])
def test_tgbot_image_mentions_and_old_commands_are_indexed(tgbot, caption):
    asyncio.run(tgbot.group(bot_message(photo=BOT_PHOTO, caption=caption)))
    row = tgbot.writer.put.await_args.args[1]
    assert row.text == caption and row.image_refs == ("large",)


@pytest.mark.parametrize("kind", ["mention", "ask", "reply"])
@pytest.mark.parametrize("migrated", [False, True])
def test_tgbot_edited_image_mentions_and_replies_are_stored(tgbot, monkeypatch, kind, migrated):
    kwargs = {"caption": {"mention": "@catix explain", "ask": "/ask explain", "reply": "explain"}[kind]}
    if kind == "reply":
        kwargs["reply_to_message"] = bot_message(from_user={"id": 99, "is_bot": True, "first_name": "Bot"})
    if migrated:
        monkeypatch.setitem(tgbot.MIGRATED, -10042, -10077)
    listens, topic = Mock(return_value=True), Mock(return_value=True)
    monkeypatch.setattr(tgbot.userbot_config, "bot_listens", listens)
    monkeypatch.setattr(tgbot.store, "topic_allowed", topic)
    message = bot_message(photo=BOT_PHOTO, edit_date=int(NOW.timestamp()),
                          is_topic_message=True, message_thread_id=11, **kwargs)
    asyncio.run(tgbot.edited(message))
    row = tgbot.writer.put.await_args.args[1]
    assert row.chat_id == (-10077 if migrated else -10042)
    assert row.text == kwargs["caption"] and row.image_refs == ("large",)
    assert row.edit_date == NOW
    listens.assert_called_once_with(-10042)
    topic.assert_called_once_with(-10042, 11)


@pytest.mark.parametrize("listener,topic", [(False, True), (True, False)])
def test_tgbot_excluded_edit_cannot_delete_outside_listener_or_topic(tgbot, monkeypatch, listener, topic):
    monkeypatch.setattr(tgbot.userbot_config, "bot_listens", lambda chat: listener)
    monkeypatch.setattr(tgbot.store, "topic_allowed", lambda chat, thread: topic)
    asyncio.run(tgbot.edited(bot_message(photo=BOT_PHOTO, caption="/ask explain", edit_date=int(NOW.timestamp()))))
    tgbot.writer.put.assert_not_awaited()
    tgbot.writer.wait_idle.assert_not_awaited()
    tgbot.store.delete_message.assert_not_called()




def test_userbot_sync_stream_checks_current_choice_before_reading(monkeypatch):
    from unittest.mock import Mock
    client = NS(iter_messages=Mock(side_effect=AssertionError("unselected chat read")))
    monkeypatch.setattr(userbot.userbot_config, "userbot_reads", lambda: {})
    monkeypatch.setattr(userbot.store, "last_msg_id", lambda *args: 0)
    assert asyncio.run(userbot._sync_stream(client, ENTITY, -42, None)) == 0


def test_userbot_backfill_checks_permissions_per_batch_not_per_message(monkeypatch):
    from unittest.mock import Mock
    wanted = Mock(return_value={-42: None})
    monkeypatch.setattr(userbot.userbot_config, "userbot_reads", wanted)
    monkeypatch.setattr(userbot.store, "last_msg_id", lambda *args: 0)
    monkeypatch.setattr(userbot.store, "topic_allowed", lambda *args: True)
    monkeypatch.setattr(userbot.store, "upsert_messages", lambda rows: None)
    async def messages(*args, **kwargs):
        for n in range(4):
            yield tg_message(photo(n + 1), "caption")
    assert asyncio.run(userbot._sync_stream(NS(iter_messages=messages), ENTITY, -42, None)) == 4
    assert wanted.call_count == 2  # Before fetching and before committing, not two SQL reads per message.




def test_userbot_sync_image_metadata_only_and_revoked_topic(monkeypatch):
    saved = []
    wanted = {-42: [99]}
    monkeypatch.setattr(userbot.userbot_config, "userbot_reads", lambda: wanted)
    monkeypatch.setattr(userbot.store, "last_msg_id", lambda *args: 0)
    monkeypatch.setattr(userbot.store, "topic_allowed", lambda chat, topic: topic == 99)
    monkeypatch.setattr(userbot.store, "upsert_messages", lambda rows: saved.extend(rows))
    from telethon.tl.types import MessageReplyHeader
    async def messages(*args, **kwargs):
        yield tg_message(photo(), "caption", reply_to=MessageReplyHeader(reply_to_msg_id=99, forum_topic=True))
        wanted.clear()
        yield tg_message(photo(22), "revoked", reply_to=MessageReplyHeader(reply_to_msg_id=99, forum_topic=True))
    client = NS(iter_messages=messages)
    # A choice revoked during a buffered backfill must not enqueue its pending images.
    assert asyncio.run(userbot._sync_stream(client, ENTITY, -42, 99)) == 0
    assert saved == []


@pytest.mark.parametrize("revoked", [False, True])
def test_userbot_backfill_keeps_only_currently_allowed_topics(monkeypatch, revoked):
    from telethon.tl.types import MessageReplyHeader
    saved, topics = [], {99}
    monkeypatch.setattr(userbot.userbot_config, "userbot_reads", lambda: {-42: list(topics)})
    monkeypatch.setattr(userbot.store, "last_msg_id", lambda *args: 0)
    monkeypatch.setattr(userbot.store, "topic_allowed", lambda chat, topic: topic in topics)
    monkeypatch.setattr(userbot.store, "upsert_messages", lambda rows: saved.extend(rows))
    async def messages(*args, **kwargs):
        yield tg_message(photo(), "caption", reply_to=MessageReplyHeader(reply_to_msg_id=99, forum_topic=True))
        yield tg_message(photo(22), "excluded", reply_to=MessageReplyHeader(reply_to_msg_id=100, forum_topic=True))
        if revoked:
            topics.clear()  # Choice changed while the final batch was buffered.
    count = asyncio.run(userbot._sync_stream(NS(iter_messages=messages), ENTITY, -42, None))
    assert count == (0 if revoked else 1)
    if not revoked:
        assert saved[0].image_refs == ("photo:11",) and saved[0].text == "caption"
    else:
        assert saved == []


@pytest.mark.parametrize("adapter", ["userbot", "tgbot"])
def test_telegram_download_cancellation_closes_buffer(adapter, tgbot):
    module = userbot if adapter == "userbot" else tgbot
    buffers = []
    async def run():
        ready = asyncio.Event()
        async def download(*args, **kwargs):
            buffers.append(kwargs.get("file", kwargs.get("destination")))
            ready.set()
            await asyncio.Event().wait()
        client = NS(get_file=AsyncMock(return_value=NS(file_size=10)), download=download,
                    get_messages=AsyncMock(return_value=tg_message(photo())), download_media=download)
        task = asyncio.create_task(module._download_image(client, {"chat_id": -42, "msg_id": 7}, "photo:11"))
        await ready.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(run())
    assert buffers[0].closed


def test_maxuserbot_real_cdn_transport_has_no_account_authorization(max_media, monkeypatch):
    import httpx
    media, client, job, source = max_media
    seen = []
    def receive(request):
        seen.append(request)
        return httpx.Response(200, content=b"image")
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(receive), **kwargs))
    monkeypatch.setattr(media.images, "download_url", real_download_url)
    assert asyncio.run(media.download(client, job, "photo:11")) == b"image"
    assert len(seen) == 1
    assert "authorization" not in seen[0].headers and "cookie" not in seen[0].headers


def test_maxuserbot_cancelled_database_operation_drains_before_worker_exit():
    from threading import Event
    from catix.ingest import images
    entered, release = Event(), Event()
    order = []
    def sql():
        entered.set()
        assert release.wait(2)
        order.append("SQL done")
    async def run():
        operation = asyncio.create_task(images.database_call(sql))
        assert await asyncio.to_thread(entered.wait, 2)
        operation.cancel()
        await asyncio.sleep(0)
        assert not operation.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await operation
        order.append("worker done")
    asyncio.run(run())
    assert order == ["SQL done", "worker done"]
