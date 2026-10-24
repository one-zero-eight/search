"""Telegram userbot: read-only ingestion of whitelisted chats into the message store.

Usage:
    catix-tguserbot login    # once: interactive login (phone, code, 2FA password)
    catix-tguserbot login --qr   # the same by a QR code scanned in the Telegram app, when the code does not come
    catix-tguserbot chats    # list your groups/channels with ids
    catix-tguserbot topics <chat>   # list the topics of a forum chat
    catix-tguserbot sync     # fetch new history of the chats being listened to
    catix-tguserbot listen   # keep running, store new and edited messages live

What is listened to (chats, and which topics of a forum chat) is set by an admin in the Telegram bot: /listen.
TG_CHATS and TG_TOPICS from .env are only the starting list: they are copied once, after that the bot decides.
"""

import argparse
import asyncio
import getpass
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote, urlsplit

import redis.asyncio as aioredis
from telethon import TelegramClient, errors, events, utils
from telethon.tl.custom.message import Message as TgMessage
from telethon.tl.functions.auth import ResendCodeRequest, SendCodeRequest
from telethon.tl.functions.messages import GetForumTopicsRequest
from telethon.tl.types import Channel, Chat, CodeSettings, ForumTopic, PeerChannel, auth

from catix import live_search, userbot_config
from catix.db import pg
from catix.db import store
from catix.ingest import publish
from catix.settings import settings

BATCH = 500


PROXY_SCHEMES = ("socks5", "socks4", "http")


def proxy_args(url: str | None) -> dict:
    """TelegramClient arguments for TG_PROXY (see settings.py); {} without a proxy. A malformed value stops the start."""
    if not url:
        return {}
    parts = urlsplit(url)
    if not parts.hostname or not parts.port:
        raise ValueError("TG_PROXY needs a host and a port, e.g. socks5://127.0.0.1:1080")
    if parts.scheme == "https":
        raise ValueError("TG_PROXY: Telethon cannot talk TLS to a proxy; an HTTP proxy (http://host:port, CONNECT) carries Telegram's "
                         "traffic, already encrypted")
    if parts.scheme == "mtproxy":
        from telethon.network.connection import ConnectionTcpMTProxyRandomizedIntermediate

        secret = unquote(parts.username or "")
        if not secret:
            raise ValueError("TG_PROXY: an MTProxy needs its secret, mtproxy://SECRET@host:port")
        if secret.startswith("ee"):
            raise ValueError("TG_PROXY: fake-TLS MTProxy secrets (ee...) are not supported by Telethon; use a dd... secret or SOCKS5")
        return {"connection": ConnectionTcpMTProxyRandomizedIntermediate, "proxy": (parts.hostname, parts.port, secret)}
    if parts.scheme in PROXY_SCHEMES:
        return {"proxy": {
            "proxy_type": parts.scheme, "addr": parts.hostname, "port": parts.port, "rdns": True,
            "username": unquote(parts.username) if parts.username else None,
            "password": unquote(parts.password) if parts.password else None,
        }}  # fmt: skip
    raise ValueError(f"TG_PROXY: unknown scheme {parts.scheme!r}; one of {', '.join(PROXY_SCHEMES)}, mtproxy")


def _client() -> TelegramClient:
    if not settings.tg_api_id or not settings.tg_api_hash:
        sys.exit("Set TG_API_ID and TG_API_HASH in .env (https://my.telegram.org -> API development tools).")
    try:
        proxy = proxy_args(settings.tg_proxy.get_secret_value() if settings.tg_proxy else None)
    except ValueError as e:
        sys.exit(str(e))
    settings.tg_session.parent.mkdir(parents=True, exist_ok=True)
    return TelegramClient(str(settings.tg_session), settings.tg_api_id, settings.tg_api_hash.get_secret_value(), **proxy)


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


async def _resolve(client: TelegramClient, refs: list[int | str]) -> list[Channel | Chat]:
    entities = []
    for ref in refs:
        try:
            entity = await client.get_entity(ref)
        except (ValueError, errors.RPCError) as e:
            print(f"{ref}: cannot be found by the userbot ({e}), skipping it.", file=sys.stderr)
            continue
        if isinstance(entity, Chat) and getattr(entity, "migrated_to", None):
            new_id = utils.get_peer_id(PeerChannel(entity.migrated_to.channel_id))
            print(
                f"{ref} was upgraded to a supergroup, its new id is {new_id}. Run `catix-db migrate-chat {utils.get_peer_id(entity)} {new_id}` "
                f"to move what is stored, and choose the new chat in the bot (/listen). Skipping it for now.",
                file=sys.stderr,
            )
            continue
        if not isinstance(entity, (Channel, Chat)):
            print(f"{ref} is a private dialog, not a group or channel; refusing to ingest it.", file=sys.stderr)
            continue
        entities.append(entity)
    return entities


async def _forum_topics(client: TelegramClient, entity: Channel) -> list[userbot_config.Topic]:
    result = await client(GetForumTopicsRequest(peer=entity, offset_date=None, offset_id=0, offset_topic=0, limit=100))
    return [userbot_config.Topic(t.id, t.title, bool(t.closed)) for t in result.topics if isinstance(t, ForumTopic)]


async def _publish_dialogs(client: TelegramClient) -> None:
    """Tell the bot which chats (and forum topics) it can offer for listening."""
    found, forums = [], []
    async for dialog in client.iter_dialogs():
        if not (dialog.is_group or dialog.is_channel):
            continue
        forum = bool(getattr(dialog.entity, "forum", False))
        kind = "channel" if dialog.is_channel and not dialog.is_group else "group"
        found.append(userbot_config.Dialog(dialog.id, dialog.name, kind, getattr(dialog.entity, "username", None), forum))
        if forum:
            forums.append(dialog.entity)
    userbot_config.replace_dialogs(found)
    for entity in forums:
        try:
            userbot_config.replace_topics(utils.get_peer_id(entity), await _forum_topics(client, entity))
        except errors.RPCError as e:
            print(f"topics of {utils.get_display_name(entity)} not read: {e}", file=sys.stderr)


async def _seed(client: TelegramClient) -> None:
    """The first time, TG_CHATS and TG_TOPICS become the list of chats being listened to."""
    if userbot_config.meta("seeded"):
        return
    resolved = {}
    for entity in await _resolve(client, settings.tg_chats):
        chat_id = utils.get_peer_id(entity)
        resolved[chat_id] = settings.tg_topics.get(chat_id)
    if userbot_config.seed(resolved):
        print(f"Copied {len(resolved)} chats from TG_CHATS into the database; change them in the bot with /listen.")


# Where Telegram says it sent the login code (auth.SentCode.type, and next_type: what a resend would use).
CODE_SENT = {
    "SentCodeTypeApp": "to the Telegram app: the chat 'Telegram' on a device where this account is logged in",
    "SentCodeTypeSms": "by SMS",
    "SentCodeTypeSmsWord": "by SMS (a word)",
    "SentCodeTypeSmsPhrase": "by SMS (a phrase)",
    "SentCodeTypeFragmentSms": "to the anonymous number on fragment.com",
    "SentCodeTypeFirebaseSms": "by an SMS only the official apps can request (Firebase): it may never come here",
    "SentCodeTypeEmailCode": "to the login e-mail",
    "SentCodeTypeCall": "by a phone call",
    "SentCodeTypeFlashCall": "by a flash call (the code is the caller's number)",
    "SentCodeTypeMissedCall": "by a missed call (the code is the last digits of the caller's number)",
    "CodeTypeSms": "by SMS",
    "CodeTypeCall": "by a phone call",
    "CodeTypeFlashCall": "by a flash call",
    "CodeTypeMissedCall": "by a missed call",
    "CodeTypeFragmentSms": "to the anonymous number on fragment.com",
}


def where(code_type: object) -> str:
    name = type(code_type).__name__
    return CODE_SENT.get(name, name)


async def _sign_in(client: TelegramClient) -> None:
    """Phone, code, 2FA password, saying where Telegram sent the code (client.start() keeps that to itself)."""
    phone = input("Phone, international format (+7...): ").strip()
    sent = await client(SendCodeRequest(phone, client.api_id, client.api_hash, CodeSettings()))  # (client.send_code_request breaks on
    # a payment request: it has no type)
    while True:
        if isinstance(sent, auth.SentCodePaymentRequired):
            sys.exit("Telegram asks to pay for the login SMS of this number (SentCodePaymentRequired): log in once with an "
                     "official app on this number, then the code comes to the app.")
        if isinstance(sent, auth.SentCodeSuccess):
            return
        if isinstance(sent.type, auth.SentCodeTypeSetUpEmailRequired):
            sys.exit("Telegram wants a login e-mail on this account first: in an official app, Settings -> Privacy and Security "
                     "-> Login E-mail, then try again.")
        print(f"Telegram sent the code {where(sent.type)}." + (f" Enter r to have it sent {where(sent.next_type)} instead"
              + (f" (after {sent.timeout} s)" if sent.timeout else "") + "." if sent.next_type else ""))
        code = input("Code: ").strip()
        if code.lower() == "r":
            try:
                sent = await client(ResendCodeRequest(phone, sent.phone_code_hash))
            except errors.RPCError as e:
                print(f"Not resent: {e}")
            continue
        try:
            await client.sign_in(phone, code, phone_code_hash=sent.phone_code_hash)
            return
        except errors.SessionPasswordNeededError:
            await client.sign_in(password=getpass.getpass("2FA password: "))
            return
        except (errors.PhoneCodeInvalidError, errors.PhoneCodeEmptyError):
            print("Wrong code, try again.")


async def _sign_in_qr(client: TelegramClient) -> None:
    """Login by a QR code scanned in the Telegram app (Settings -> Devices -> Link Desktop Device): no code to wait for."""
    import segno

    qr = await client.qr_login()
    while True:
        segno.make(qr.url).terminal(compact=True)
        print("Scan it in the Telegram app: Settings -> Devices -> Link Desktop Device.")
        try:
            await qr.wait()
            return
        except asyncio.TimeoutError:
            await qr.recreate()  # (a code lives about 30 s)
        except errors.SessionPasswordNeededError:
            await client.sign_in(password=getpass.getpass("2FA password: "))
            return


async def login(qr: bool = False) -> None:
    client = _client()
    await client.connect()
    try:
        if not await client.is_user_authorized():
            await (_sign_in_qr if qr else _sign_in)(client)
        settings.tg_session.with_suffix(".session").chmod(0o600)
        me = await client.get_me()
        print(f"Logged in as {utils.get_display_name(me)} (@{me.username}). Session: {settings.tg_session}.session")
    finally:
        await client.disconnect()


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
        print(f"chat id: {utils.get_peer_id(entity)}")
        for topic in await _forum_topics(client, entity):
            print(f"{topic.topic_id:>8}  {topic.title}{'  (closed)' if topic.closed else ''}")
        print("\nChoose the ones to listen to in the bot: /listen")


async def _sync_chat(client: TelegramClient, entity: Channel | Chat, topics: list[int] | None) -> str:
    """Fetch the new history of one chat (only `topics` of it, if given) and note the chat as synced."""
    chat_id = utils.get_peer_id(entity)
    store.upsert_chat(chat_id, utils.get_display_name(entity), getattr(entity, "username", None))
    # A chat with a topic whitelist is read topic by topic; otherwise as one stream.
    total = 0
    for topic_id in topics if topics is not None else [None]:
        total += await _sync_stream(client, entity, chat_id, topic_id)
    store.mark_synced(chat_id)
    return f"{utils.get_display_name(entity)}: +{total} messages"


async def sync() -> None:
    async with _client() as client:
        await client.start()
        await _publish_dialogs(client)
        await _seed(client)
        wanted = userbot_config.listened()
        if not wanted:
            sys.exit("Nothing is being listened to. In the Telegram bot, send /listen and choose the chats.")
        for entity in await _resolve(client, list(wanted)):
            print(await _sync_chat(client, entity, wanted[utils.get_peer_id(entity)]))


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


POLL_SECONDS = 15  # How often the choice made in the bot is looked at.
DIALOGS_EVERY = 600  # How often the list of chats offered in the bot is refreshed (it is also refreshed on request).


async def listen() -> None:
    async with _client() as client:
        await client.start()
        await _publish_dialogs(client)
        await _seed(client)
        entities: dict[int, Channel | Chat] = {}  # Chats being listened to right now.

        async def save(event: events.NewMessage.Event | events.MessageEdited.Event) -> None:
            entity = entities.get(event.chat_id)
            if entity is None:
                return  # Not a chat chosen in the bot.
            row = _to_store(event.message, event.chat_id, entity)
            if row and store.topic_allowed(row.chat_id, row.topic_id):
                store.upsert_messages([row])
                await publish.publish([(row.chat_id, row.msg_id)])  # the worker looks for schedule changes in it

        client.add_event_handler(save, events.NewMessage())
        client.add_event_handler(save, events.MessageEdited())
        follower = asyncio.create_task(_follow_choice(client, entities))
        searching = asyncio.create_task(_serve_search(client))
        print("Listening. The chats are chosen in the bot: /listen. Ctrl+C to stop.")
        try:
            await client.run_until_disconnected()
        finally:
            follower.cancel()
            searching.cancel()


async def _follow_choice(client: TelegramClient, entities: dict[int, Channel | Chat]) -> None:
    """Keep `entities` equal to the chats chosen in the bot; fetch the history of a chat that was just turned on
    (or got more topics). What was chosen before this start is not fetched again: that is `sync`."""
    applied: dict[int, list[int] | None] | None = None
    backfills: set[asyncio.Task] = set()
    last_refresh, last_request = time.monotonic(), float(userbot_config.meta("refresh_requested") or 0)
    while True:
        try:
            # Not a chat only the Bot API bot is in (this account cannot open it), nor one an admin gave to the bot.
            wanted = userbot_config.userbot_reads()
            for chat_id in set(entities) - set(wanted):
                del entities[chat_id]
                print(f"No longer listening to {chat_id}.")
            for entity in await _resolve(client, [c for c in wanted if c not in entities]):
                # The chat row first: messages refer to it, and it keeps the title and @username up to date.
                store.upsert_chat(utils.get_peer_id(entity), utils.get_display_name(entity), getattr(entity, "username", None))
                entities[utils.get_peer_id(entity)] = entity
            for chat_id, entity in entities.items():
                topics = wanted[chat_id]
                if applied is not None and applied.get(chat_id, ...) != _same(topics):
                    print(f"Now listening to {utils.get_display_name(entity)}, fetching its history.")
                    task = asyncio.create_task(_backfill(client, entity, topics))
                    backfills.add(task)
                    task.add_done_callback(backfills.discard)
            applied = {c: _same(wanted[c]) for c in entities}

            request = float(userbot_config.meta("refresh_requested") or 0)
            if request > last_request or time.monotonic() - last_refresh > DIALOGS_EVERY:
                await _publish_dialogs(client)
                last_refresh, last_request = time.monotonic(), request
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 - the database or Telegram being away for a moment must not stop listening
            print(f"Could not follow the choice made in the bot: {e!r}", file=sys.stderr)
        await asyncio.sleep(POLL_SECONDS)


SEARCH_CONCURRENCY = 3  # Telegram searches at the same time: the account must not look like a scraper.
SEARCH_BUDGET = 8.0  # Seconds one request may take; the bot stops waiting a little later.
CHATS_AT_ONCE = 8  # Chats of one request searched at the same time.
GLOBAL_FROM = 3  # More chats than this: one search over all dialogs per keyword instead of one per chat.
GLOBAL_LIMIT = 150  # Newest messages of all dialogs looked at per keyword.


async def _serve_search(client: TelegramClient) -> None:
    """Answer the bot's live-search requests (live_search.py): Telegram's own search in the chats set to `search`."""
    if not settings.redis_url:
        print("REDIS_URL is not set: live search is off.")
        return
    redis_client = aioredis.from_url(settings.redis_url, socket_timeout=live_search.REQUEST_TTL + 10)
    slots = asyncio.Semaphore(SEARCH_CONCURRENCY)
    tasks: set[asyncio.Task] = set()

    async def handle(payload: dict) -> None:
        async with slots:
            try:
                answer = await asyncio.wait_for(_search_chats(client, payload), SEARCH_BUDGET)
            except asyncio.TimeoutError:
                answer = {"hits": [], "error": "Telegram search took too long"}
            except Exception as e:  # noqa: BLE001 - the bot is waiting: it gets the problem, not silence
                print(f"Live search failed: {e!r}", file=sys.stderr)
                answer = {"hits": [], "error": f"search failed: {type(e).__name__}"}
        key = live_search.reply_key(payload["id"])
        await redis_client.rpush(key, json.dumps(answer, ensure_ascii=False))
        await redis_client.expire(key, 60)

    while True:
        try:
            item = await redis_client.blpop([live_search.REQUESTS], timeout=5)
            if item is None:
                continue
            payload = json.loads(item[1])
            if time.time() - payload.get("sent", 0) > live_search.REQUEST_TTL:
                continue  # Nobody waits for it any more.
            task = asyncio.create_task(handle(payload))
            tasks.add(task)
            task.add_done_callback(tasks.discard)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 - Redis away for a moment must not stop the service
            print(f"Live search service: {e!r}", file=sys.stderr)
            await asyncio.sleep(5)


async def _search_chats(client: TelegramClient, payload: dict) -> dict:
    """Every keyword in every requested chat: the hits as dicts, or the problem."""
    allowed = userbot_config.searchable_chats()  # Only chats an admin chose in /listen, whatever the request says.
    date_from = datetime.fromisoformat(payload["date_from"]).replace(tzinfo=timezone.utc) if payload.get("date_from") else None
    date_to = datetime.fromisoformat(payload["date_to"]).replace(tzinfo=timezone.utc) + timedelta(days=1) if payload.get("date_to") else None
    hits: dict[tuple[int, int], dict] = {}
    problem: str | None = None

    async def one_chat(chat_id: int) -> None:
        nonlocal problem
        try:
            entity = await client.get_entity(chat_id)
        except (ValueError, errors.RPCError) as e:
            problem = f"chat {chat_id} cannot be opened by the userbot: {e}"
            return
        title = utils.get_display_name(entity)
        for word in payload["keywords"]:
            try:
                async for message in client.iter_messages(entity, search=word, limit=payload["per_chat"], offset_date=date_to):
                    if date_from and message.date < date_from:
                        break
                    row = _to_store(message, chat_id, entity)
                    if row and (chat_id, row.msg_id) not in hits:
                        hits[chat_id, row.msg_id] = {
                            "chat_id": chat_id, "msg_id": row.msg_id, "chat_title": title, "date": row.date.isoformat(),
                            "author": row.sender_name, "sender_link": row.sender_link, "link": row.link, "text": row.text,
                        }
            except errors.FloodWaitError as e:
                problem = f"Telegram asked to wait {e.seconds} s"
                return

    wanted = [c for c in payload["chat_ids"] if c in allowed]
    if len(wanted) > GLOBAL_FROM:
        # Many chats: one search over all dialogs per keyword (a search per chat took many seconds when one chat was slow, and
        # held up the others), the hits of other chats are dropped at once, unread.
        for word in payload["keywords"]:
            try:
                async for message in client.iter_messages(None, search=word, limit=GLOBAL_LIMIT, offset_date=date_to):
                    if date_from and message.date < date_from:
                        break
                    if message.chat_id not in wanted:
                        continue
                    entity = await message.get_chat()
                    row = _to_store(message, message.chat_id, entity)
                    if row and (message.chat_id, row.msg_id) not in hits:
                        hits[message.chat_id, row.msg_id] = {
                            "chat_id": message.chat_id, "msg_id": row.msg_id, "chat_title": utils.get_display_name(entity), "date": row.date.isoformat(),
                            "author": row.sender_name, "sender_link": row.sender_link, "link": row.link, "text": row.text,
                        }
            except errors.FloodWaitError as e:
                problem = f"Telegram asked to wait {e.seconds} s"
                break
        return {"hits": list(hits.values()), "error": problem}

    gate = asyncio.Semaphore(CHATS_AT_ONCE)

    async def limited(chat_id: int) -> None:
        async with gate:
            await one_chat(chat_id)

    tasks = [asyncio.create_task(limited(c)) for c in wanted]
    # Telegram answers some searches in many seconds: what is there when the time is up is returned, the slow chats are left out.
    _, pending = await asyncio.wait(tasks, timeout=SEARCH_BUDGET - 1) if tasks else (set(), set())
    for task in pending:
        task.cancel()
    if pending and not problem:
        problem = f"{len(pending)} chat(s) answered too slowly and were skipped"
    return {"hits": list(hits.values()), "error": problem}


def _same(topics: list[int] | None) -> list[int] | None:
    """Topics in a fixed order, so choosing the same ones in another order is not a change."""
    return None if topics is None else sorted(topics)


async def _backfill(client: TelegramClient, entity: Channel | Chat, topics: list[int] | None) -> None:
    try:
        print(await _sync_chat(client, entity, topics))
    except Exception as e:  # noqa: BLE001
        print(f"History of {utils.get_display_name(entity)} not fetched: {e!r}", file=sys.stderr)


def main() -> None:
    commands = {"login": login, "chats": list_chats, "topics": None, "sync": sync, "listen": listen}
    parser = argparse.ArgumentParser(prog="catix-tguserbot", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=commands)
    parser.add_argument("chat", nargs="?", help="chat id or @username, for `topics`")
    parser.add_argument("--qr", action="store_true", help="`login` by a QR code scanned in the Telegram app")
    args = parser.parse_args()
    run = {"topics": lambda: list_topics(args.chat), "login": lambda: login(args.qr)}.get(args.command, commands[args.command])
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
    finally:
        pg.close()
