"""Background worker: embeddings and schedule changes, a separate app that the Telegram and Max bots feed.

    bots --(ids of stored messages)--> Redis stream --> this worker --> schedule_changes (Postgres)
                                                                    --> cards to the users of the chat's group (Telegram)

The worker also serves the users' personal calendars (feed.py, GET /users/my-calendar.ics).

Embedding threads (embedder.py) turn every stored message into a vector; they read their queue from Postgres and
are woken by the same stream. The bots only store messages, they compute nothing.

The changes part reads the stream in a consumer group, so a crash or a model outage loses nothing: a message is acknowledged only
after it was looked at, and unacknowledged ones are read again. The users' buttons are handled by the Telegram bot
(it owns the update polling), which puts the change in the user's calendar. Run: `catix-worker`.
"""

import asyncio
import contextlib
import logging
import threading

import redis.asyncio as redis
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from catix.worker import changes
from catix.worker import embedder
from catix.worker import feed
from catix.worker import health
from catix.db import pg
from catix.agent import tracing
from catix.settings import settings
from catix.ingest.publish import STREAM

log = logging.getLogger("catix.worker")

GROUP = "changes"
CONSUMER = "worker-1"
READ_COUNT = 20
BLOCK_MS = 5000
RETRY_SECONDS = 10


SEND_PAUSE = 0.05  # Telegram allows about 30 messages a second to different users.


def change_keyboard(change_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ В мой календарь", callback_data=f"chg:ok:{change_id}"),
            InlineKeyboardButton(text="❌ Не нужно", callback_data=f"chg:no:{change_id}"),
        ]]
    )  # fmt: skip


async def notify_users(bot: Bot) -> None:
    """Send every newly found change to the users it is for; each puts it in their own calendar or not."""
    while True:
        try:
            for change in await asyncio.to_thread(changes.unnotified):
                for user in await asyncio.to_thread(changes.recipients, change):
                    with contextlib.suppress(TelegramAPIError):  # Blocked the bot, never started it, ...
                        await bot.send_message(
                            user, changes.card(change), parse_mode=ParseMode.HTML, reply_markup=change_keyboard(change.id), disable_web_page_preview=True
                        )
                    await asyncio.sleep(SEND_PAUSE)
                await asyncio.to_thread(changes.mark_notified, change.id)
        except Exception:
            log.exception("notifying about schedule changes failed")
        await asyncio.sleep(5)


async def consume(client: redis.Redis, model) -> None:
    try:
        # "$": the group starts at the end of the stream, so messages from before the first run are not scanned.
        await client.xgroup_create(STREAM, GROUP, id="$", mkstream=True)
    except redis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise
    cursor = "0"  # First what was delivered but never acknowledged (a crash, a model outage), then new messages.
    while True:
        try:
            reply: list[tuple[bytes, list[tuple[bytes, dict[bytes, bytes]]]]] | None = await client.xreadgroup(
                GROUP, CONSUMER, {STREAM: cursor}, count=READ_COUNT, block=BLOCK_MS
            )  # type: ignore[assignment] - redis-py types the reply of every command as a union of all of them
            entries = reply[0][1] if reply else []
            if cursor != ">" and not entries:
                cursor = ">"
                continue
            for entry_id, fields in entries:
                chat_id, msg_id = int(fields[b"chat_id"]), int(fields[b"msg_id"])
                await asyncio.to_thread(changes.process, model, chat_id, msg_id)
                await client.xack(STREAM, GROUP, entry_id)
        except (redis.ConnectionError, redis.TimeoutError) as e:
            log.warning("redis is unreachable (%s), retrying in %ds", e, RETRY_SECONDS)
            await asyncio.sleep(RETRY_SECONDS)
        except Exception:  # noqa: BLE001 - mostly the model server being down: the entry stays unacknowledged
            log.exception("reading a message failed, retrying in %ds", RETRY_SECONDS)
            cursor = "0"
            await asyncio.sleep(RETRY_SECONDS)


async def wake_on_new(client: redis.Redis, wake: threading.Event) -> None:
    """Wake the embedding threads when a bot publishes a message, so a new message gets its vector without waiting
    for the next poll. (Without Redis they simply poll the queue in the database once a second.)"""
    last = "$"  # Only entries that arrive from now on.
    while True:
        try:
            reply: list[tuple[bytes, list[tuple[bytes, dict[bytes, bytes]]]]] | None = await client.xread(
                {STREAM: last}, count=100, block=BLOCK_MS
            )  # type: ignore[assignment] - redis-py types every reply as a union
            if reply:
                last = reply[0][1][-1][0]
                wake.set()
        except (redis.ConnectionError, redis.TimeoutError):
            await asyncio.sleep(RETRY_SECONDS)


async def run() -> None:
    tracing.log_status()
    stop, wake = threading.Event(), threading.Event()
    embedder.start(stop, wake)
    monitoring = asyncio.create_task(health.run())  # Alerts to the admins, independent of Redis and the changes part.
    calendar = asyncio.create_task(feed.serve())  # The users' personal calendars, independent of Redis too.
    if not settings.redis_url:
        log.warning("REDIS_URL is not set: only embeddings run (polling the queue); schedule changes need Redis")
        await asyncio.Event().wait()
        return
    # The socket timeout must be longer than the blocking read, or an idle stream looks like a broken connection.
    client = redis.from_url(settings.redis_url, socket_timeout=BLOCK_MS / 1000 + 25, health_check_interval=30)
    await client.ping()
    waking = asyncio.create_task(wake_on_new(client, wake))
    if not settings.changes_enabled:
        log.info("CHANGES_ENABLED is off: only embeddings run")
        await waking
        return
    bot = Bot(settings.tg_bot_token.get_secret_value()) if settings.tg_bot_token else None  # Only sends; the bot app polls.
    notifying = asyncio.create_task(notify_users(bot)) if bot else None
    if not bot:
        log.warning("TG_BOT_TOKEN is not set: found changes are not sent to the users")
    log.info("watching %s", STREAM)
    try:
        await consume(client, changes._model())
    finally:
        tracing.flush()
        stop.set()
        monitoring.cancel()
        calendar.cancel()
        waking.cancel()
        if notifying:
            notifying.cancel()
        if bot:
            await bot.session.close()
        await client.aclose()
        pg.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
