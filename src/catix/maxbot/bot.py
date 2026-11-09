"""Max messenger bot: stores messages from the chats and channels it is in.

Messages from both messengers are searched by the assistant on the InNoHassle website.
Private dialogs are not indexed; authorized chat administrators can configure chat groups there.
Run: `catix-maxbot`.

Max has no edit/removal handling beyond `message_edited`, so an edit re-saves the message. Long polling keeps no
position between restarts: messages written while the bot was down are lost (Max keeps events for a limited time).
Max chat ids are shifted by MAX_CHAT_BASE in the database so they never collide with Telegram ids.
"""

import asyncio
import contextlib
import logging
import ssl
import sys
from datetime import datetime, timedelta, timezone

import certifi
import httpx

from catix import groups
from catix.ingest import writer as ingest
from catix.ingest import images
from catix.db import pg
from catix.db import store
from catix.common.render import to_html
from catix.db.rows import ChatGroup
from catix.settings import settings
from catix.maxbot import source_requests

log = logging.getLogger("catix.max")

API = "https://platform-api2.max.ru"
MAX_CHAT_BASE = groups.MAX_CHAT_BASE  # Telegram ids stay below 10**13 in absolute value, Max ids are assumed to as well.
POLL_TIMEOUT = 30
UPDATE_TYPES = "message_created,message_edited,bot_started,bot_added"
HISTORY_PAGE = 100

GREETING = (
    "Привет! Я cAtIx. Сохраняю сообщения из чатов и каналов, куда меня добавили, "
    "для поиска и уведомлений об изменениях расписания.\n\n"
    "Задать вопрос ассистенту можно на сайте InNoHassle. В этом боте ответов на вопросы нет."
)

writer = ingest.Writer()


def db_chat_id(chat_id: int) -> int:
    return MAX_CHAT_BASE + chat_id


class Max:
    """The few Bot API calls we need. The token goes in the Authorization header."""

    def __init__(self, token: str) -> None:
        context = ssl.create_default_context(cafile=certifi.where())
        context.load_verify_locations(cafile=str(settings.max_root_ca))
        self.http = httpx.AsyncClient(
            base_url=API, headers={"Authorization": token}, verify=context, timeout=POLL_TIMEOUT + 15
        )
        self.chats: dict[int, dict] = {}

    async def call(self, method: str, path: str, **kwargs) -> dict:
        resp = await self.http.request(method, path, **kwargs)
        for attempt in range(1, 5):
            if resp.status_code != 429:
                break
            await asyncio.sleep(attempt)  # Rate limit: wait and try again.
            resp = await self.http.request(method, path, **kwargs)
        resp.raise_for_status()
        return resp.json()

    async def updates(self, marker: int | None) -> dict:
        params: dict = {"timeout": POLL_TIMEOUT, "types": UPDATE_TYPES, "limit": 100}
        if marker is not None:
            params["marker"] = marker
        return await self.call("GET", "/updates", params=params)

    async def chat(self, chat_id: int) -> dict:
        if chat_id not in self.chats:
            try:
                self.chats[chat_id] = await self.call("GET", f"/chats/{chat_id}")
            except httpx.HTTPError:
                return {}  # Not cached: asked again with the next message.
        return self.chats[chat_id]

    async def send(self, chat_id: int, text: str) -> None:
        body: dict = {"text": to_html(text), "format": "html"}
        try:
            await self.call("POST", "/messages", params={"chat_id": chat_id, "disable_link_preview": "true"}, json=body)
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 400:
                raise
            # The HTML was not accepted: send the plain text.
            body = {"text": text}
            await self.call("POST", "/messages", params={"chat_id": chat_id, "disable_link_preview": "true"}, json=body)

    async def admin_chats(self, user_id: int) -> list[ChatGroup]:
        """Known Max chats where this user is an administrator (asked from Max)."""
        chats = await asyncio.to_thread(groups.list_chats, "max")

        async def is_admin(chat: ChatGroup) -> bool:
            try:
                data = await self.call("GET", f"/chats/{chat.chat_id - MAX_CHAT_BASE}/members/admins")
            except httpx.HTTPError:
                return False  # The bot was removed or is not an admin there.
            return any(m.get("user_id") == user_id for m in data.get("members", []))

        flags = await asyncio.gather(*(is_admin(c) for c in chats))
        return [c for c, ok in zip(chats, flags) if ok]


def _text(message: dict) -> str:
    """Text of a message: its own, the attached file names, and a forwarded message's text."""
    body = message.get("body") or {}
    text = body.get("text") or ""
    for attachment in body.get("attachments") or []:
        if attachment.get("type") == "file" and (name := (attachment.get("filename") or attachment.get("payload", {}).get("filename"))):
            text = f"{text}\n[file: {name}]".strip()
    link = message.get("link") or {}
    if link.get("type") == "forward" and (forwarded := (link.get("message") or {}).get("text")):
        who = (link.get("sender") or {}).get("first_name")
        text = f"{text}\n{forwarded}".strip() if not who else f"{text}\n{who}: {forwarded}".strip()
    return text


def _name(user: dict | None) -> str | None:
    return " ".join(p for p in (user.get("first_name"), user.get("last_name")) if p) if user else None


def _image_refs(message: dict) -> tuple[str, ...]:
    # MAX calls these "image", not "photo". File names alone do not establish an image MIME type.
    return tuple(
        url for attachment in (message.get("body") or {}).get("attachments") or []
        if attachment.get("type") == "image"
        and isinstance(url := (attachment.get("payload") or {}).get("url"), str) and url
    )


async def _download_image(job: dict, ref: str) -> bytes:
    context = ssl.create_default_context(cafile=certifi.where())
    context.load_verify_locations(cafile=str(settings.max_root_ca))
    # Never send the bot's Authorization header to a CDN. The shared fetcher validates hosts and bounds bytes.
    return await images.download_url(ref, verify=context)


async def _prepare(max_: Max, message: dict, chat_id: int, *, edited: bool = False,
                   observed_at: datetime | None = None) -> tuple[store.ChatInfo, store.Message] | None:
    observed_at = observed_at or datetime.now(timezone.utc)
    if (message.get("recipient") or {}).get("chat_type") == "dialog":
        return None
    text = _text(message)
    refs = _image_refs(message)
    seq = (message.get("body") or {}).get("seq")
    sender = message.get("sender")
    if (not text and not refs and not edited) or seq is None or (sender or {}).get("is_bot"):
        return None
    chat = await max_.chat(chat_id)
    title = chat.get("title") or str(chat_id)
    link = message.get("link") or {}
    reply = (link.get("message") or {}).get("seq") if link.get("type") == "reply" else None
    chat_link = chat.get("link")
    if chat_link and chat_link.startswith(("https://max.ru/join/", "max.ru/join/")):
        chat_link = None
    db_id = db_chat_id(chat_id)
    return (
        store.ChatInfo(db_id, title, None, via_bot=False, link=chat_link),
        store.Message(
            chat_id=db_id,
            msg_id=seq,
            topic_id=None,
            date=datetime.fromtimestamp(message["timestamp"] / 1000, timezone.utc),
            edit_date=None,
            observed_at=observed_at,
            live_edit=edited,
            sender_id=sender["user_id"] if sender else None,
            sender_name=_name(sender) or title,  # Channel posts have no sender.
            reply_to=reply,
            text=text,
            image_source="maxbot" if refs else None,
            image_refs=refs,
            link=message.get("url"),  # Only channel posts have a public link.
            sender_link=f"https://max.ru/{sender['username']}" if sender and sender.get("username") else None,
        ),
    )


async def _save(max_: Max, message: dict, chat_id: int, *, edited: bool = False,
                observed_at: datetime | None = None) -> None:
    if prepared := await _prepare(max_, message, chat_id, edited=edited, observed_at=observed_at):
        await writer.put(*prepared)


def _latest_stored(chat_id: int) -> datetime | None:
    with pg.connection() as conn:
        return pg.scalar(conn, "SELECT max(date) FROM messages WHERE chat_id = %s", (db_chat_id(chat_id),))


async def backfill(max_: Max, chat_id: int) -> bool:
    """Load the history of a chat the bot has just met: everything since the newest stored message, or TG_SYNC_DAYS."""
    chat = await max_.chat(chat_id)
    if not chat or not await asyncio.to_thread(source_requests.observe, chat):
        return False
    now = datetime.now(timezone.utc)
    since = await asyncio.to_thread(_latest_stored, chat_id) or now - timedelta(days=settings.tg_sync_days)
    until, total = int(now.timestamp() * 1000), 0
    try:
        while True:
            observed_at = datetime.now(timezone.utc)  # The whole page predates any await below.
            page = (
                await max_.call(
                    "GET", "/messages", params={"chat_id": chat_id, "from": int(since.timestamp() * 1000), "to": until, "count": HISTORY_PAGE}
                )
            ).get("messages", [])
            for message in page:
                if prepared := await _prepare(max_, message, chat_id, observed_at=observed_at):
                    await writer.put(*prepared)
                    total += 1
            if len(page) < HISTORY_PAGE:
                break
            oldest = min(m["timestamp"] for m in page)
            if oldest >= until:
                break  # No progress: stop instead of looping.
            until = oldest - 1
    except httpx.HTTPError as e:
        log.warning("history of chat %s could not be loaded: %s", chat_id, e)
        return False
    log.info("history of chat %s: %d messages since %s", chat_id, total, since.date())
    return True


SEEN: set[int] = set()  # Chats whose history was requested during this run.
TASKS: set[asyncio.Task] = set()  # Strong references: the loop keeps only weak ones to running tasks.


def _load_history(max_: Max, chat_id: int) -> None:
    """Once per chat and run, in the background so polling goes on. Re-running is harmless: rows are upserted."""
    if chat_id in SEEN:
        return
    SEEN.add(chat_id)
    task = asyncio.create_task(backfill(max_, chat_id))
    TASKS.add(task)
    task.add_done_callback(TASKS.discard)


async def _handle(max_: Max, update: dict) -> None:
    observed_at = datetime.now(timezone.utc)  # Before any preparation/metadata await.
    kind = update["update_type"]
    if kind == "bot_added":
        chat = await max_.chat(update["chat_id"])
        if chat and await asyncio.to_thread(source_requests.observe, chat):
            _load_history(max_, update["chat_id"])
        return
    if kind == "bot_started":
        await max_.send(update["chat_id"], GREETING)
        return
    message = update["message"]
    recipient = message["recipient"]
    sender = message.get("sender") or {}
    if sender.get("is_bot"):
        return
    chat_type = recipient["chat_type"]
    text = (message.get("body") or {}).get("text") or ""

    if chat_type == "dialog":
        if kind == "message_created" and text:
            chat_id = recipient.get("chat_id") or sender["user_id"]
            # Settings are changed in the dialog with the bot, never in a group.
            command, _, args = text.partition(" ")
            if command == "/group":
                await max_.send(chat_id, groups.group_command(args, await max_.admin_chats(sender["user_id"])))
            elif command == "/start":
                await max_.send(chat_id, GREETING)
        return

    chat_id = recipient["chat_id"]
    if (message.get("body") or {}).get("seq") is None:
        return
    chat = await max_.chat(chat_id)
    if not chat or not await asyncio.to_thread(source_requests.observe, chat):
        return
    _load_history(max_, chat_id)
    await _save(max_, message, chat_id, edited=kind == "message_edited", observed_at=observed_at)


async def poll(max_: Max) -> None:
    marker: int | None = None
    delay = 1.0
    while True:
        try:
            data = await max_.updates(marker)
        except (httpx.HTTPError, ssl.SSLError) as e:
            log.warning("polling failed (%s), retrying in %.0fs", e, delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)
            continue
        delay = 1.0
        marker = data.get("marker", marker)
        for update in data.get("updates", []):
            try:
                await _handle(max_, update)
            except Exception:
                log.exception("update failed: %s", update.get("update_type"))


async def run() -> None:
    if not settings.max_bot_token:
        sys.exit("Set MAX_BOT_TOKEN in .env (get it from the «MAX для бизнеса» bot).")
    if not settings.max_root_ca.exists():
        sys.exit(
            f"{settings.max_root_ca} is missing. Download the Russian root certificate: "
            f"curl -L https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt -o {settings.max_root_ca}"
        )
    max_ = Max(settings.max_bot_token.get_secret_value())
    me = await max_.call("GET", "/me")
    log.info("Running as @%s", me.get("username"))
    writing = asyncio.create_task(writer.run())
    recognizing = asyncio.create_task(images.run("maxbot", _download_image))
    requests = asyncio.create_task(source_requests.run(max_, backfill))
    try:
        await poll(max_)
    finally:
        requests.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await requests
        recognizing.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await recognizing
        writing.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await writing
        await max_.http.aclose()
        pg.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
