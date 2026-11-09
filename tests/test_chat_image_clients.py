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


def max_message(text="", attachments=None, chat_type="chat"):
    return {"timestamp": int(NOW.timestamp() * 1000), "recipient": {"chat_id": 42, "chat_type": chat_type},
            "sender": {"user_id": 3, "first_name": "Alice"},
            "body": {"seq": 7, "mid": "mid-7", "text": text, "attachments": attachments or []}}


@pytest.fixture
def maxbot(monkeypatch):
    from catix.maxbot import bot
    monkeypatch.setattr(bot.writer, "put", AsyncMock())
    monkeypatch.setattr(bot.writer, "wait_idle", AsyncMock())
    monkeypatch.setattr(bot.store, "delete_message", Mock())
    monkeypatch.setattr(bot, "_load_history", lambda *args: None)
    monkeypatch.setattr(bot.source_requests, "observe", lambda chat: True)
    async def request_worker(*args):
        await asyncio.Event().wait()
    monkeypatch.setattr(bot.source_requests, "run", request_worker)
    return bot


MAX_IMAGE = {"type": "image", "payload": {"url": "https://i.oneme.ru/image"}}


@pytest.mark.parametrize("caption", ["", "caption"])
def test_maxbot_image_metadata_and_caption(maxbot, caption):
    client = NS(chat=AsyncMock(return_value={"title": "Study"}))
    prepared = asyncio.run(maxbot._prepare(client, max_message(caption, [MAX_IMAGE]), 42))
    assert prepared is not None
    chat, row = prepared
    assert row.text == caption and row.image_source == "maxbot"
    assert row.image_refs == (MAX_IMAGE["payload"]["url"],)
    assert row.chat_id == chat.chat_id == maxbot.db_chat_id(42)
    assert row.date == NOW and row.edit_date is None and row.sender_name == "Alice"


def test_maxbot_does_not_truncate_image_list(maxbot):
    attachments = [{"type": "image", "payload": {"url": f"https://i.oneme.ru/{i}"}} for i in range(11)]
    client = NS(chat=AsyncMock(return_value={}))
    _, row = asyncio.run(maxbot._prepare(client, max_message(attachments=attachments), 42))
    assert len(row.image_refs) == 11  # The worker must fail the whole oversized job, not index a subset.


@pytest.mark.parametrize("kind", ["photo", "video", "sticker", "file"])
def test_maxbot_only_actual_image_type_is_ocr_source(maxbot, kind):
    attachment = {"type": kind, "payload": {"url": "https://i.oneme.ru/image", "filename": "schedule.png"}}
    client = NS(chat=AsyncMock(return_value={}))
    _, row = asyncio.run(maxbot._prepare(client, max_message("caption", [attachment]), 42))
    assert row.image_refs == ()
    assert row.text == ("caption\n[file: schedule.png]" if kind == "file" else "caption")


def test_maxbot_empty_edit_removes_old_ocr(maxbot):
    client = NS(chat=AsyncMock(return_value={"chat_id": 42, "type": "chat", "title": "Study"}))
    asyncio.run(maxbot._handle(client, {"update_type": "message_edited", "message": max_message()}))
    row = maxbot.writer.put.await_args.args[1]
    assert row.text == "" and row.image_refs == () and row.edit_date is None
    maxbot.writer.put.reset_mock()
    asyncio.run(maxbot._save(client, max_message(), 42))
    maxbot.writer.put.assert_not_awaited()


@pytest.mark.parametrize("text", ["@catix what is this?", "/ask what is this?", "what is this?"])
def test_maxbot_does_not_store_or_answer_private_messages(maxbot, text):
    client = NS(send=AsyncMock())
    message = max_message(text, [MAX_IMAGE], "dialog")
    asyncio.run(maxbot._handle(client, {"update_type": "message_created", "message": message}))
    maxbot.writer.put.assert_not_awaited()
    client.send.assert_not_awaited()


def test_maxbot_download_uses_unauthenticated_bounded_fetch_with_root_ca(maxbot, monkeypatch):
    from catix.ingest import images
    from unittest.mock import Mock
    context = NS(load_verify_locations=Mock())
    monkeypatch.setattr(maxbot.ssl, "create_default_context", lambda **kwargs: context)
    fetch = AsyncMock(return_value=b"image")
    monkeypatch.setattr(images, "download_url", fetch)
    assert asyncio.run(maxbot._download_image({"chat_id": maxbot.db_chat_id(42)}, MAX_IMAGE["payload"]["url"])) == b"image"
    fetch.assert_awaited_once_with(MAX_IMAGE["payload"]["url"], verify=context)
    context.load_verify_locations.assert_called_once_with(cafile=str(maxbot.settings.max_root_ca))


def test_maxbot_worker_cancelled_before_http_and_db_close(maxbot, monkeypatch, tmp_path):
    from catix.ingest import images
    from pydantic import SecretStr
    order, sources = [], []
    client = NS(call=AsyncMock(return_value={"username": "catix"}),
                http=NS(aclose=AsyncMock(side_effect=lambda: order.append("http closed"))))
    ca = tmp_path / "ca.pem"
    ca.write_text("")
    monkeypatch.setattr(maxbot.settings, "max_bot_token", SecretStr("test-token"))
    monkeypatch.setattr(maxbot.settings, "max_root_ca", ca)
    monkeypatch.setattr(maxbot, "Max", lambda token: client)
    monkeypatch.setattr(maxbot.pg, "close", lambda: order.append("db closed"))
    async def idle():
        await asyncio.Event().wait()
    async def worker(source, download, allowed=None):
        sources.append(source)
        try:
            await idle()
        finally:
            await asyncio.sleep(0)
            order.append("worker stopped")
    async def poll(*args):
        await asyncio.sleep(0)
    monkeypatch.setattr(maxbot, "poll", poll)
    monkeypatch.setattr(maxbot.writer, "run", idle)
    monkeypatch.setattr(images, "run", worker, raising=False)
    asyncio.run(maxbot.run())
    assert sources == ["maxbot"]
    assert order == ["worker stopped", "http closed", "db closed"]


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


@pytest.mark.parametrize("kind", ["mention", "ask", "reply"])
@pytest.mark.parametrize("update_type", ["message_created", "message_edited"])
def test_maxbot_mentions_commands_and_replies_are_indexed(maxbot, kind, update_type):
    client = NS(chat=AsyncMock(return_value={"chat_id": 42, "type": "chat", "title": "Study"}), send=AsyncMock())
    text = {"mention": "@catix explain", "ask": "/ask explain", "reply": "explain"}[kind]
    message = max_message(text, [MAX_IMAGE])
    if kind == "reply":
        message["link"] = {"type": "reply", "sender": {"user_id": 99}, "message": {"seq": 6}}
    asyncio.run(maxbot._handle(client, {"update_type": update_type, "message": message}))
    maxbot.writer.put.assert_awaited_once()
    row = maxbot.writer.put.await_args.args[1]
    assert row.text == text
    assert row.image_refs == (MAX_IMAGE["payload"]["url"],)
    assert row.reply_to == (6 if kind == "reply" else None)
    assert row.live_edit == (update_type == "message_edited")
    assert isinstance(row.observed_at, datetime)
    maxbot.store.delete_message.assert_not_called()
    client.send.assert_not_awaited()


@pytest.mark.parametrize("excluded", ["dialog", "bot-sender", "missing-seq"])
def test_maxbot_non_indexable_image_edits_remain_excluded(maxbot, excluded):
    message = max_message("@catix explain", [MAX_IMAGE], "dialog" if excluded == "dialog" else "chat")
    if excluded == "bot-sender":
        message["sender"]["is_bot"] = True
    if excluded == "missing-seq":
        del message["body"]["seq"]
    asyncio.run(maxbot._handle(NS(), {"update_type": "message_edited", "message": message}))
    maxbot.writer.put.assert_not_awaited()
    maxbot.store.delete_message.assert_not_called()


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


@pytest.mark.parametrize("text", ["caption", "/ask explain", "@catix explain"])
def test_maxbot_backfill_conversion_excludes_dialogs(maxbot, text):
    client = NS(chat=AsyncMock(return_value={}))
    assert asyncio.run(maxbot._prepare(client, max_message(text, [MAX_IMAGE], "dialog"), 42)) is None
    client.chat.assert_not_awaited()


@pytest.mark.parametrize("text", ["/ask explain", "@catix explain"])
def test_maxbot_backfill_keeps_mentions_and_former_commands(maxbot, monkeypatch, text):
    monkeypatch.setattr(maxbot, "_latest_stored", lambda chat_id: NOW)
    client = NS(chat=AsyncMock(return_value={"chat_id": 42, "type": "chat", "title": "Study"}),
                call=AsyncMock(return_value={"messages": [max_message(text, [MAX_IMAGE])]}))
    asyncio.run(maxbot.backfill(client, 42))
    maxbot.writer.put.assert_awaited_once()
    row = maxbot.writer.put.await_args.args[1]
    assert row.text == text and row.image_refs == (MAX_IMAGE["payload"]["url"],)


@pytest.mark.parametrize("command", ["/mygroup", "/calendar", "/clear", "/ask", "/new"])
def test_maxbot_removed_private_commands_are_ignored(maxbot, command):
    client = NS(send=AsyncMock(), admin_chats=AsyncMock())
    asyncio.run(maxbot._handle(client, {"update_type": "message_created",
                                        "message": max_message(command, chat_type="dialog")}))
    client.send.assert_not_awaited()
    client.admin_chats.assert_not_awaited()
    maxbot.writer.put.assert_not_awaited()


@pytest.mark.parametrize("update_type", ["bot_started", "message_created"])
def test_maxbot_greeting_directs_users_to_website(maxbot, update_type):
    client = NS(send=AsyncMock())
    update = {"update_type": update_type, "chat_id": 42}
    if update_type == "message_created":
        update["message"] = max_message("/start", chat_type="dialog")
    asyncio.run(maxbot._handle(client, update))
    client.send.assert_awaited_once()
    chat_id, text = client.send.await_args.args
    assert chat_id == 42
    assert "сайте InNoHassle" in text
    assert all(command not in text for command in ("/ask", "/mygroup", "/group", "/calendar", "/clear", "/new"))


@pytest.mark.parametrize("is_admin", [False, True])
def test_maxbot_manual_group_command_changes_only_admin_chats(maxbot, monkeypatch, is_admin):
    chat = maxbot.ChatGroup(maxbot.db_chat_id(42), "Study", "all")
    monkeypatch.setattr(maxbot.groups, "list_chats", lambda platform: [chat])
    saved = Mock()
    monkeypatch.setattr(maxbot.groups, "set_chat_group", saved)
    call = AsyncMock(return_value={"members": [{"user_id": 3 if is_admin else 9}]})
    client = NS(call=call, send=AsyncMock())
    client.admin_chats = lambda user_id: maxbot.Max.admin_chats(client, user_id)
    asyncio.run(maxbot._handle(client, {"update_type": "message_created",
                                        "message": max_message("/group 1 B26-CSE-01", chat_type="dialog")}))
    call.assert_awaited_once_with("GET", "/chats/42/members/admins")
    client.send.assert_awaited_once()
    if is_admin:
        saved.assert_called_once_with(chat.chat_id, "B26-CSE-01")
    else:
        saved.assert_not_called()
    maxbot.writer.put.assert_not_awaited()


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


def test_maxbot_real_download_transport_does_not_receive_bot_authorization(maxbot, monkeypatch):
    import httpx
    from pathlib import Path
    seen = []
    def receive(request):
        seen.append(request)
        return httpx.Response(200, content=b"image")
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(receive), **kwargs))
    monkeypatch.setattr(maxbot.settings, "max_root_ca", Path(maxbot.certifi.where()))
    async def run():
        client = maxbot.Max("must-not-forward")
        try:
            assert client.http.headers["Authorization"] == "must-not-forward"
            assert await maxbot._download_image({}, MAX_IMAGE["payload"]["url"]) == b"image"
        finally:
            await client.http.aclose()
    asyncio.run(run())
    assert len(seen) == 1
    assert "authorization" not in seen[0].headers
