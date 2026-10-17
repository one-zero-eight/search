"""Telegram bot (Bot API): stores group messages and answers questions with the agent.

In groups it saves every text message, and answers only when @mentioned, replied to, or on /ask.
In channels (the bot must be an admin) it only saves posts.
Saved messages go to Postgres in batches (ingest.py) and are announced on a Redis stream; the worker
(worker.py, `catix-worker`) adds their vectors and looks for schedule changes.
In private chat it answers every message. Run: `catix-tgbot`.

Note: a bot sees group messages only with privacy mode disabled (@BotFather -> /setprivacy -> Disable)
or with admin rights, and never sees history from before it was added.
"""

import asyncio
import contextlib
import logging
import re
import sys
import time
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatMemberStatus, ChatType, ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (
    CallbackQuery,
    Message,
    MessageOriginChannel,
    MessageOriginChat,
    MessageOriginHiddenUser,
    MessageOriginUser,
)
from aiogram.utils.chat_action import ChatActionSender

from catix.tgbot import access
from catix.worker import changes
from catix import groups
from catix.ingest import writer as ingest
from catix.db import pg
from catix.agent import sqlquery
from catix.db import store
from catix.tgbot import stream
from catix.agent import tracing
from catix.agent.core import build_agent, final_answer
from catix.common.render import chunks as _chunks
from catix.common.render import to_html as _to_html
from catix.db.rows import ChatGroup
from catix.settings import settings
from catix.agent.tools import AgentContext

log = logging.getLogger("catix.bot")
router = Router()
agent = build_agent()
# Set after every write: tells the embedding workers there is something new to embed.
writer = ingest.Writer()

GROUPS = {ChatType.GROUP, ChatType.SUPERGROUP}


def _link(message: Message) -> str | None:
    chat = message.chat
    if chat.username:
        return f"https://t.me/{chat.username}/{message.message_id}"
    if chat.type in (ChatType.SUPERGROUP, ChatType.CHANNEL):
        # Private supergroup/channel: strip the -100 prefix; the link works for members only.
        return f"https://t.me/c/{str(chat.id).removeprefix('-100')}/{message.message_id}"
    return None  # Basic groups have no message links.


def _origin(message: Message) -> tuple[str | None, datetime] | None:
    """Original author and date of a forwarded message, so recency reflects when it was first said."""
    match message.forward_origin:
        case MessageOriginUser(sender_user=user, date=date):
            return user.full_name, date
        case MessageOriginHiddenUser(sender_user_name=name, date=date):
            return name, date
        case MessageOriginChannel(chat=chat, author_signature=signature, date=date):
            return signature or chat.title, date
        case MessageOriginChat(sender_chat=chat, author_signature=signature, date=date):
            return signature or chat.title, date
    return None


CHAT_LINKS: dict[int, str | None] = {}


async def _chat_link(message: Message) -> str | None:
    """Link to a chat whose messages have no links (basic groups): its public name or invite link.
    Telegram shows the invite link only to a bot that is an admin; without it there is no link, and that is cached."""
    chat = message.chat
    if chat.id not in CHAT_LINKS:
        try:
            full = await message.bot.get_chat(chat.id)
            CHAT_LINKS[chat.id] = f"https://t.me/{full.username}" if full.username else full.invite_link
        except TelegramAPIError as e:
            log.warning("no link for chat %s: %s", chat.id, e)
            CHAT_LINKS[chat.id] = None
    return CHAT_LINKS[chat.id]


async def _save(message: Message) -> None:
    text = message.text or message.caption or ""
    if message.document and message.document.file_name:
        text = f"{text}\n[file: {message.document.file_name}]".strip()
    if not text:
        return
    # In General the Bot API may omit the thread id; topic_allowed treats None as General.
    topic_id = message.message_thread_id if message.is_topic_message else None
    if not store.topic_allowed(message.chat.id, topic_id):
        return
    sender = message.from_user
    # Channel posts have no from_user: use the post signature, if enabled, or the channel name.
    sender_name = sender.full_name if sender else message.author_signature or message.chat.title
    date = message.date
    origin_seen = False
    if origin := _origin(message):
        origin_seen = True  # The author is the original sender, not whoever forwarded it.
        author, date = origin
        sender_name = f"{author} (forwarded by {sender_name})"
    chat_id = MIGRATED.get(message.chat.id, message.chat.id)
    link = await _chat_link(message) if _link(message) is None else None
    chat = store.ChatInfo(chat_id, message.chat.title or str(chat_id), message.chat.username, via_bot=True, link=link)
    await writer.put(
        chat,
        store.Message(
            chat_id=chat_id,
            msg_id=message.message_id,
            topic_id=topic_id,
            date=date,
            # Bot API gives edit_date as a unix timestamp, unlike `date`.
            edit_date=datetime.fromtimestamp(message.edit_date, timezone.utc) if message.edit_date else None,
            sender_id=sender.id if sender else None,
            sender_name=sender_name,
            reply_to=message.reply_to_message.message_id if message.reply_to_message else None,
            text=text,
            link=_link(message),
            sender_link=f"https://t.me/{sender.username}" if sender and sender.username and not origin_seen else None,
        ),
    )


async def _reply(message: Message, question: str) -> None:
    question = question.strip()
    if not question:
        await message.reply("Задайте вопрос, например: /ask когда мидтерм по матану?")
        return
    await _answer(message, question)


async def _answer(message: Message, question: str) -> None:
    # One conversation per user per chat, so people in a group do not share context.
    thread_id = f"tg:{message.chat.id}:{message.from_user.id if message.from_user else 0}"
    log.info("question in %s: %s", thread_id, question[:200])
    started = time.monotonic()
    async with ChatActionSender.typing(chat_id=message.chat.id, bot=message.bot, message_thread_id=message.message_thread_id):
        try:
            allowed = await access.visible_chats(
                message.bot, message.from_user.id if message.from_user else 0, message.chat.id, message.chat.type
            )
            user_key = f"tg:{message.from_user.id if message.from_user else 0}"
            allowed = groups.narrow(allowed, await asyncio.to_thread(groups.scoped_chat_ids, user_key, message.from_user.id if message.from_user else None))
            # Drafts exist only in private chats; groups get the typing indicator and one message at the end.
            streamer = (
                stream.DraftStreamer(
                    message.bot, message.chat.id, message.message_thread_id if message.is_topic_message else None, _to_html
                )
                if message.chat.type == ChatType.PRIVATE
                else None
            )
            messages = await stream.run(
                agent,
                {"messages": [{"role": "user", "content": question}]},
                tracing.run_config(thread_id, str(message.from_user.id) if message.from_user else None),
                AgentContext(
                    allowed_chat_ids=None if allowed is None else frozenset(allowed),
                    user_telegram_id=message.from_user.id if message.from_user else None,
                ),
                streamer,
            )
            answer = final_answer(messages) or "Не получилось сформулировать ответ."
            log.info("answered in %.1fs, %d chars, %d messages in thread", time.monotonic() - started, len(answer), len(messages))
        except Exception:
            log.exception("agent failed")
            answer = "Не получилось ответить: ошибка на стороне ассистента. Попробуйте ещё раз позже."

    for chunk in _chunks(answer, 4096):
        try:
            await message.reply(_to_html(chunk), parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        except TelegramBadRequest:
            # Converter produced HTML Telegram does not accept: fall back to plain text.
            await message.reply(chunk, disable_web_page_preview=True)


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(
        "Привет! Я cAtIx, ассистент Innopolis University: клубы, аудитории, события, а также экзамены, дедлайны и советы "
        "из чатов, куда меня добавили.\n\nВ личке просто пишите вопрос. В группе: /ask вопрос, упоминание или ответ "
        "на моё сообщение.\n\n/mygroup: ваша учебная группа (по умолчанию ищу везде).\n"
        "/group: указать группу чата, где вы сделали меня администратором."
    )


@router.message(Command("id"))
async def show_ids(message: Message) -> None:
    """Chat and topic ids for TG_CHATS / TG_TOPICS; send it inside the topic you want."""
    topic = message.message_thread_id if message.is_topic_message else None
    lines = [f"chat id: <code>{message.chat.id}</code>"]
    lines.append(f"topic id: <code>{topic}</code>" if topic else "topic id: none (General topic or no topics)")
    await message.reply("\n".join(lines), parse_mode=ParseMode.HTML)


# When Telegram upgrades a basic group to a supergroup the chat id changes. It sends a service message to the old
# group (migrate_to_chat_id) and one to the new one (migrate_from_chat_id); either is enough, the move is repeatable.
# This handler must come before the generic group handler.
MIGRATED: dict[int, int] = {}  # old id -> new id, for messages that are still on their way under the old id


@router.message(F.migrate_to_chat_id | F.migrate_from_chat_id)
async def chat_migrated(message: Message) -> None:
    old, new = (
        (message.chat.id, message.migrate_to_chat_id) if message.migrate_to_chat_id else (message.migrate_from_chat_id, message.chat.id)
    )
    MIGRATED[old] = new
    await writer.wait_idle()  # Messages of the old chat that are still queued must be stored before they move.
    counts = await asyncio.to_thread(store.migrate_chat, old, new)
    log.info("chat %s became a supergroup %s: %s", old, new, counts)


ADMIN_STATUSES = {ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR}


async def _admin_chats(bot: Bot, user_id: int) -> list[ChatGroup]:
    """Chats the bot is in where this user is an administrator (checked with Telegram, not with the stored data)."""
    chats = await asyncio.to_thread(groups.list_chats, "tg")

    async def is_admin(chat_id: int) -> bool:
        try:
            return (await bot.get_chat_member(chat_id, user_id)).status in ADMIN_STATUSES
        except TelegramAPIError:
            return False  # The bot was removed, or the user is not there.

    flags = await asyncio.gather(*(is_admin(c.chat_id) for c in chats))
    return [c for c, ok in zip(chats, flags) if ok]


# The group of a chat is set in a private chat with the bot, never in the group itself, so that chatting people
# cannot change it; Telegram confirms the admin rights.
@router.message(F.chat.type == ChatType.PRIVATE, Command("group"))
async def set_group(message: Message, command: CommandObject, bot: Bot) -> None:
    admin_chats = await _admin_chats(bot, message.from_user.id)
    await message.answer(groups.group_command(command.args or "", admin_chats))


@router.message(F.chat.type == ChatType.PRIVATE, Command("mygroup"))
async def my_group(message: Message, command: CommandObject) -> None:
    user_id = message.from_user.id
    await message.answer(await asyncio.to_thread(groups.mygroup_command, command.args or "", f"tg:{user_id}", user_id))


@router.message(Command("ask"))
async def ask(message: Message, command: CommandObject) -> None:
    # Questions to the bot are not saved: they would show up as search results for the same question.
    await _reply(message, command.args or "")


@router.message(F.chat.type == ChatType.PRIVATE, F.text)
async def private(message: Message) -> None:
    await _reply(message, message.text)


@router.message(F.chat.type.in_(GROUPS))
async def group(message: Message, bot: Bot) -> None:
    me = await bot.me()
    text = message.text or ""
    mention = f"@{me.username}"
    is_reply_to_bot = bool(message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.id == me.id)
    if mention.lower() in text.lower() or is_reply_to_bot:
        await _reply(message, re.sub(re.escape(mention), "", text, flags=re.I))
    else:
        await _save(message)


@router.edited_message(F.chat.type.in_(GROUPS))
async def edited(message: Message) -> None:
    await _save(message)


# Channels deliver posts as channel_post updates, and only to bots that are channel admins.
# The bot never answers in channels, it only stores posts.
@router.channel_post()
@router.edited_channel_post()
async def channel_post(message: Message) -> None:
    await _save(message)


# ---- schedule changes: the admin approves what the worker (worker.py) found in chats ------------------------------


@router.callback_query(F.data.startswith("chg:"))
async def decide_change(query: CallbackQuery) -> None:
    if query.from_user.id not in changes.admins():
        await query.answer("Только для администратора", show_alert=True)
        return
    _, action, change_id = query.data.split(":")
    done = await asyncio.to_thread(changes.decide, int(change_id), action == "ok")
    verdict = ("✅ Добавлено в календарь" if action == "ok" else "❌ Отклонено") if done else "Уже обработано"
    await query.answer(verdict)
    if query.message and done:
        await query.message.edit_text(f"{query.message.html_text}\n\n{verdict}", parse_mode=ParseMode.HTML, reply_markup=None, disable_web_page_preview=True)


async def run() -> None:
    if not settings.tg_bot_token:
        sys.exit("Set TG_BOT_TOKEN in .env (create a bot with @BotFather).")
    bot = Bot(settings.tg_bot_token.get_secret_value())
    dp = Dispatcher()
    dp.include_router(router)
    me = await bot.me()
    log.info("Running as @%s", me.username)
    tracing.log_status()
    await asyncio.to_thread(sqlquery.reset_context)  # Rows left behind by a crash.
    writing = asyncio.create_task(writer.run())
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        tracing.flush()
        writing.cancel()  # Flushes what is already collected before stopping.
        with contextlib.suppress(asyncio.CancelledError):
            await writing
        pg.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
