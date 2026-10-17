"""Telegram userbot: read-only ingestion of whitelisted chats into the message store.

Usage:
    catix-tguserbot login    # once: interactive login (phone, code, 2FA password)
    catix-tguserbot chats    # list your groups/channels with ids, to fill TG_CHATS
    catix-tguserbot topics <chat>   # list the topics of a forum chat, to fill TG_TOPICS
    catix-tguserbot sync     # fetch new history of TG_CHATS
    catix-tguserbot listen   # keep running, store new and edited messages live
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone

from telethon import TelegramClient, errors, events, utils
from telethon.tl.custom.message import Message as TgMessage
from telethon.tl.functions.messages import GetForumTopicsRequest
from telethon.tl.types import Channel, Chat, ForumTopic, PeerChannel

from catix.db import pg
from catix.db import store
from catix.ingest import publish
from catix.settings import settings

BATCH = 500


def _client() -> TelegramClient:
    if not settings.tg_api_id or not settings.tg_api_hash:
        sys.exit("Set TG_API_ID and TG_API_HASH in .env (https://my.telegram.org -> API development tools).")
    settings.tg_session.parent.mkdir(parents=True, exist_ok=True)
    return TelegramClient(str(settings.tg_session), settings.tg_api_id, settings.tg_api_hash.get_secret_value())


def _link(entity: Channel | Chat, msg_id: int) -> str | None:
    if getattr(entity, "username", None):
        return f"https://t.me/{entity.username}/{msg_id}"
    if isinstance(entity, Channel):
        # Private supergroups/channels: link works for members only.
        return f"https://t.me/c/{entity.id}/{msg_id}"
    return None  # Basic groups have no message links.


def _to_store(msg: TgMessage, chat_id: int, entity: Channel | Chat) -> store.Message | None:
    text = msg.message or ""
    if msg.file and msg.file.name:
        # Keep file names: "exam_2025.pdf" is useful even without the content.
        text = f"{text}\n[file: {msg.file.name}]".strip()
    if not text:
        return None
    reply = msg.reply_to
    topic_id = None
    if reply and getattr(reply, "forum_topic", False):
        topic_id = reply.reply_to_top_id or reply.reply_to_msg_id
    sender_name = utils.get_display_name(msg.sender) if msg.sender else msg.post_author
    date = msg.date
    if fwd := msg.forward:
        # Keep the original author and date, so recency reflects when it was first said.
        origin = fwd.sender or fwd.chat
        author = fwd.post_author or (utils.get_display_name(origin) if origin else fwd.from_name)
        sender_name = f"{author or 'unknown'} (forwarded by {sender_name})"
        date = fwd.date
    return store.Message(
        chat_id=chat_id,
        msg_id=msg.id,
        topic_id=topic_id,
        date=date,
        edit_date=msg.edit_date,
        sender_id=msg.sender_id,
        sender_name=sender_name or None,
        reply_to=reply.reply_to_msg_id if reply and reply.reply_to_msg_id != topic_id else None,
        text=text,
        link=_link(entity, msg.id),
        sender_link=(
            f"https://t.me/{username}" if not msg.forward and (username := getattr(msg.sender, "username", None)) else None
        ),
    )


def _require_whitelist() -> None:
    if not settings.tg_chats:
        sys.exit("TG_CHATS is empty. Run `catix-tguserbot chats` and put the ids you want into .env, e.g. TG_CHATS='[-1001234567890]'")


async def _resolve_whitelist(client: TelegramClient) -> list[Channel | Chat]:
    entities = []
    for ref in settings.tg_chats:
        entity = await client.get_entity(ref)
        if isinstance(entity, Chat) and getattr(entity, "migrated_to", None):
            new_id = utils.get_peer_id(PeerChannel(entity.migrated_to.channel_id))
            print(
                f"{ref} was upgraded to a supergroup, its new id is {new_id}. Run `catix-db migrate-chat {utils.get_peer_id(entity)} {new_id}` "
                f"to move what is stored, and replace the id in TG_CHATS. Skipping it for now.",
                file=sys.stderr,
            )
            continue
        if not isinstance(entity, (Channel, Chat)):
            sys.exit(f"{ref} is a private dialog, not a group or channel; refusing to ingest it.")
        entities.append(entity)
    return entities


async def login() -> None:
    async with _client() as client:
        await client.start()
        settings.tg_session.with_suffix(".session").chmod(0o600)
        me = await client.get_me()
        print(f"Logged in as {utils.get_display_name(me)} (@{me.username}). Session: {settings.tg_session}.session")


async def list_chats() -> None:
    async with _client() as client:
        await client.start()
        async for dialog in client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                kind = "channel" if dialog.is_channel and not dialog.is_group else "group"
                print(f"{dialog.id:>16}  {kind:<7}  {dialog.name}")


async def list_topics(chat: str | None) -> None:
    if not chat:
        sys.exit("Usage: catix-tguserbot topics <chat id or @username>")
    ref = int(chat) if chat.lstrip("-").isdigit() else chat
    async with _client() as client:
        await client.start()
        entity = await client.get_entity(ref)
        if not getattr(entity, "forum", False):
            sys.exit(f"{utils.get_display_name(entity)} has no topics (it is not a forum).")
        result = await client(GetForumTopicsRequest(peer=entity, offset_date=None, offset_id=0, offset_topic=0, limit=100))
        print(f"chat id: {utils.get_peer_id(entity)}")
        for topic in result.topics:
            if isinstance(topic, ForumTopic):
                print(f"{topic.id:>8}  {topic.title}{'  (closed)' if topic.closed else ''}")
        print('\nPut the ones you need into .env, e.g. TG_TOPICS=\'{"%d": [<topic ids>]}\'' % utils.get_peer_id(entity))


async def sync() -> None:
    _require_whitelist()
    async with _client() as client:
        await client.start()
        for entity in await _resolve_whitelist(client):
            chat_id = utils.get_peer_id(entity)
            title = utils.get_display_name(entity)
            store.upsert_chat(chat_id, title, getattr(entity, "username", None))

            # A chat with a topic whitelist is read topic by topic; otherwise as one stream.
            topics = settings.tg_topics.get(chat_id)
            total = 0
            for topic_id in topics if topics is not None else [None]:
                total += await _sync_stream(client, entity, chat_id, topic_id)
            members = await _sync_members(client, entity, chat_id)
            store.mark_synced(chat_id)
            print(f"{title}: +{total} messages, {members}")


async def _sync_stream(client: TelegramClient, entity: Channel | Chat, chat_id: int, topic_id: int | None) -> int:
    """Fetch new messages of a whole chat (topic_id None) or of one topic."""
    last_id = store.last_msg_id(chat_id, topic_id)
    if last_id:
        kwargs = {"min_id": last_id}
    else:
        kwargs = {"offset_date": datetime.now(timezone.utc) - timedelta(days=settings.tg_sync_days)}
    if topic_id not in (None, store.GENERAL_TOPIC_ID):
        # Server-side: only this topic's messages are transferred.
        kwargs["reply_to"] = topic_id
    # General has no thread to ask for: walk the chat and keep its messages (filtered below).

    batch, total = [], 0
    # reverse=True walks oldest -> newest, so an interrupted sync resumes from the right place.
    async for msg in client.iter_messages(entity, reverse=True, **kwargs):
        row = _to_store(msg, chat_id, entity)
        if row and store.topic_allowed(chat_id, row.topic_id) and (topic_id is None or _in_topic(row, topic_id)):
            batch.append(row)
        if len(batch) >= BATCH:
            store.upsert_messages(batch)
            total += len(batch)
            batch = []
    store.upsert_messages(batch)
    return total + len(batch)


def _in_topic(row: store.Message, topic_id: int) -> bool:
    return (row.topic_id or store.GENERAL_TOPIC_ID) == topic_id


async def _sync_members(client: TelegramClient, entity: Channel | Chat, chat_id: int) -> str:
    """Record who is in a private group, so the bot can show its content to members only."""
    if getattr(entity, "username", None):
        return "public, members not needed"
    if isinstance(entity, Channel) and entity.broadcast:
        # Subscribers of a channel are visible to its admins only.
        return "private channel: members unknown, add it to TG_OPEN_CHATS or the bot as admin to share it"
    try:
        users = {u.id async for u in client.iter_participants(entity) if not u.bot}
    except (errors.ChatAdminRequiredError, errors.ChatAdminInviteRequiredError):
        return "members hidden by admins: only message senders are known"
    store.set_members({(chat_id, user_id) for user_id in users}, True)
    return f"{len(users)} members"


async def listen() -> None:
    _require_whitelist()
    async with _client() as client:
        await client.start()
        entities = {utils.get_peer_id(e): e for e in await _resolve_whitelist(client)}
        for chat_id, entity in entities.items():
            store.upsert_chat(chat_id, utils.get_display_name(entity), getattr(entity, "username", None))

        async def save(event: events.NewMessage.Event | events.MessageEdited.Event) -> None:
            row = _to_store(event.message, event.chat_id, entities[event.chat_id])
            if row and store.topic_allowed(row.chat_id, row.topic_id):
                store.upsert_messages([row])
                await publish.publish([(row.chat_id, row.msg_id)])  # the worker looks for schedule changes in it

        client.add_event_handler(save, events.NewMessage(chats=list(entities)))
        client.add_event_handler(save, events.MessageEdited(chats=list(entities)))
        print(f"Listening to {len(entities)} chats. Ctrl+C to stop.")
        await client.run_until_disconnected()


def main() -> None:
    commands = {"login": login, "chats": list_chats, "topics": None, "sync": sync, "listen": listen}
    parser = argparse.ArgumentParser(prog="catix-tguserbot", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=commands)
    parser.add_argument("chat", nargs="?", help="chat id or @username, for `topics`")
    args = parser.parse_args()
    try:
        asyncio.run(list_topics(args.chat) if args.command == "topics" else commands[args.command]())
    except KeyboardInterrupt:
        pass
    finally:
        pg.close()
