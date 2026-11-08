"""Telegram reader and calendar-notification bot.

Stores messages from configured groups/topics and channels. The worker indexes them
and sends calendar changes; questions and calendar management live on innohassle.ru.
Run: `catix-tgbot`.

Note: a bot sees group messages only with privacy mode disabled (@BotFather -> /setprivacy -> Disable)
or with admin rights, and never sees history from before it was added.
"""

import asyncio
import contextlib
import logging
import sys
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatMemberStatus, ChatType, ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BotCommand,
    BotCommandScopeChat,
    CallbackQuery,
    ChatMemberUpdated,
    Message,
    MessageOriginChannel,
    MessageOriginChat,
    MessageOriginHiddenUser,
    MessageOriginUser,
)
from catix.tgbot import abuse as abuse_commands
from catix.tgbot import admin
from catix.tgbot import listen
from catix.tgbot import official
from catix.worker import changes
from catix import bot_users, personal_calendar, userbot_config
from catix.ingest import writer as ingest
from catix.ingest import images
from catix.db import pg
from catix.db import store
from catix.common import cache
from catix.settings import settings

log = logging.getLogger("catix.bot")
router = Router()
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


CHAT_LINK_TTL = 86400.0  # A chat's link is asked again after a day (an invite link may be revoked),
CHAT_LINK_MISS_TTL = 600.0  # a chat without a link after ten minutes: the bot may have become an admin.
IGNORED: set[int] = set()


async def _chat_link(message: Message) -> str | None:
    """Link to a chat whose messages have no links (basic groups): its public name or invite link, cached (common/cache.py).
    Telegram shows the invite link only to a bot that is an admin; without it there is no link for a while."""
    chat = message.chat
    key = f"tg-chat-link:{chat.id}"
    found, link = cache.get(key)
    if found:
        return link
    try:
        full = await message.bot.get_chat(chat.id)
        link = f"https://t.me/{full.username}" if full.username else full.invite_link
    except TelegramAPIError as e:
        log.warning("no link for chat %s: %s", chat.id, e)
        link = None
    return cache.put(key, link, CHAT_LINK_TTL if link else CHAT_LINK_MISS_TTL)


def _image_refs(message: Message) -> tuple[str, ...]:
    if message.photo:
        return (message.photo[-1].file_id,)
    if (message.document and message.document.mime_type in {"image/jpeg", "image/png", "image/webp"}
            and not (message.sticker or message.animation or message.video)):
        return (message.document.file_id,)
    return ()


async def _download_image(bot: Bot, job: dict, ref: str) -> bytes:
    metadata = await bot.get_file(ref)
    if (metadata.file_size or 0) > images.MAX_BYTES:
        raise ValueError("Image size limit")
    with images.LimitedBuffer() as output:
        await bot.download(ref, destination=output)
        return output.getvalue()


async def _save(message: Message, *, observed_at: datetime | None = None) -> None:
    observed_at = observed_at or datetime.now(timezone.utc)
    text = message.text or message.caption or ""
    refs = _image_refs(message)
    if message.document and message.document.file_name:
        text = f"{text}\n[file: {message.document.file_name}]".strip()
    if not text and not refs and not message.edit_date:
        return
    if not await asyncio.to_thread(userbot_config.bot_listens, message.chat.id):
        if message.chat.id not in IGNORED:  # Once per chat: why a chat the bot is in stays empty.
            await asyncio.to_thread(userbot_config.register_bot_chat, message.chat.id,
                                    message.chat.title or str(message.chat.id), message.chat.username)
            IGNORED.add(message.chat.id)
            log.info("chat %s (%s): the bot does not store it (not chosen in /listen, or read by the userbot)", message.chat.id, message.chat.title)
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
            observed_at=observed_at,
            live_edit=bool(message.edit_date),
            sender_id=sender.id if sender else None,
            sender_name=sender_name,
            reply_to=message.reply_to_message.message_id if message.reply_to_message else None,
            text=text,
            image_source="tgbot" if refs else None,
            image_refs=refs,
            link=_link(message),
            sender_link=f"https://t.me/{sender.username}" if sender and sender.username and not origin_seen else None,
        ),
    )




@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(
        "Привет! Я cAtIx. Читаю подключённые чаты и присылаю уведомления об изменениях календаря.\n\n"
        "Вопросы ассистенту, выбор учебной группы и управление календарём — на https://innohassle.ru.\n"
        "Для уведомлений привяжите Telegram к вашему аккаунту InNoHassle."
    )


@router.message(Command("id"))
async def show_ids(message: Message) -> None:
    """Chat and topic ids for TG_CHATS / TG_TOPICS; send it inside the topic you want."""
    if not message.from_user or message.from_user.id not in await asyncio.to_thread(changes.admins):
        return
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
    await writer.wait_idle()  # Messages of the old chat that are still queued must be stored before they move.
    counts = await asyncio.to_thread(store.migrate_chat, old, new)
    MIGRATED[old] = new  # Never redirect private messages when migration was refused by the access-policy guard.
    log.info("chat %s became a supergroup %s: %s", old, new, counts)




@router.message(F.chat.type.in_(GROUPS))
async def group(message: Message) -> None:
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




# ---- schedule changes: each user decides on what the worker (worker.py) found in the chats of their group ---------


async def remember_private(handler, message: Message, data: dict):
    """Outer middleware: whoever writes to the bot in private (/start first) may be written to, so the found changes are
    sent to them (bot_users.py)."""
    if message.chat.type == ChatType.PRIVATE and message.from_user and not message.from_user.is_bot:
        try:
            await asyncio.to_thread(bot_users.remember, message.from_user.id)
        except Exception:  # The database being down must not stop the answer.
            log.exception("could not remember user %s", message.from_user.id)
    return await handler(message, data)


@router.my_chat_member(F.chat.type.in_(GROUPS | {ChatType.CHANNEL}))
async def group_status(update: ChatMemberUpdated) -> None:
    """Discover a bot's group without enabling ingestion before admin confirmation."""
    member = update.new_chat_member.status not in {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}
    if update.new_chat_member.status == ChatMemberStatus.RESTRICTED:
        member = update.new_chat_member.is_member
    await asyncio.to_thread(userbot_config.register_bot_chat, update.chat.id,
                            update.chat.title or str(update.chat.id), update.chat.username, member=member)
    IGNORED.discard(update.chat.id)


@router.my_chat_member(F.chat.type == ChatType.PRIVATE)
async def private_status(update: ChatMemberUpdated) -> None:
    """The user blocked the bot (no more changes for them) or unblocked it."""
    if update.new_chat_member.status == ChatMemberStatus.KICKED:
        await asyncio.to_thread(bot_users.blocked, update.from_user.id)
    else:
        await asyncio.to_thread(bot_users.remember, update.from_user.id)


@router.callback_query(F.data.startswith("chg:"))
async def decide_change(query: CallbackQuery) -> None:
    _, action, change_id = query.data.split(":")
    if action == "ok":
        try:
            user_key = await asyncio.to_thread(personal_calendar.telegram_key, query.from_user.id)
        except personal_calendar.NoAccount as e:  # The card keeps its buttons for after the Telegram is linked.
            await query.answer(str(e), show_alert=True)
            return
        done = await asyncio.to_thread(changes.add_to_calendar, user_key, int(change_id), telegram_id=query.from_user.id)
        verdict = f"✅ {done[:180]}. https://innohassle.ru/calendar" if done else "Изменение не найдено"
    else:
        verdict = "❌ Не добавлено"
    await query.answer(verdict)
    if query.message:
        await query.message.edit_text(f"{query.message.html_text}\n\n{verdict}", parse_mode=ParseMode.HTML, reply_markup=None, disable_web_page_preview=True)


COMMANDS = [BotCommand(command="start", description="Уведомления календаря")]


async def set_commands(bot: Bot) -> None:
    """Publish only /start; clear old administrator-specific menus."""
    await bot.set_my_commands(COMMANDS)
    try:
        admin_ids = await asyncio.to_thread(changes.admins)
    except Exception:  # The menu is a convenience; database failure must not stop ingestion.
        log.warning("could not look up old admin menus", exc_info=True)
        return
    for admin_id in admin_ids:
        try:
            await bot.delete_my_commands(scope=BotCommandScopeChat(chat_id=admin_id))
        except TelegramAPIError as e:
            log.warning("old menu for admin %s not cleared: %s", admin_id, e)


def profile_texts(username: str) -> dict[str | None, tuple[str, str]]:
    """The bot's profile by the language of a person's Telegram (None: any other, Russian as the rest of the bot): the
    description an empty chat with the bot shows above Start (at most 512 characters) and the short description of its
    profile and of a link to it (at most 120)."""
    return {
        None: (
            "Привет! Я cAtIx. Читаю подключённые чаты Университета Иннополис и присылаю изменения календаря.\n\n"
            "Нажмите «Старт» и привяжите Telegram к аккаунту InNoHassle для уведомлений.\n\n"
            "Вопросы ассистенту, учебная группа и календарь — на https://innohassle.ru.",
            "Чтение учебных чатов и уведомления календаря. Ассистент — на innohassle.ru.",
        ),
        "en": (
            "Hi! I'm cAtIx. I read configured Innopolis University chats and send calendar changes.\n\n"
            "Press Start and link Telegram to your InNoHassle account for notifications.\n\n"
            "Ask the assistant, choose your study group and manage your calendar at https://innohassle.ru.",
            "Study chat reader and calendar notifications. Ask the assistant at innohassle.ru.",
        ),
    }


async def set_profile(bot: Bot, username: str) -> None:
    """Writes the description and the short description where they differ from what Telegram has (a restart changes
    nothing)."""
    for language, (description, short) in profile_texts(username).items():
        try:
            if (await bot.get_my_description(language_code=language)).description != description:
                await bot.set_my_description(description, language_code=language)
            if (await bot.get_my_short_description(language_code=language)).short_description != short:
                await bot.set_my_short_description(short, language_code=language)
        except TelegramAPIError as e:  # The profile is a convenience, the bot must start without it.
            log.warning("the bot's description (%s) not set: %s", language or "default", e)


async def run() -> None:
    if not settings.tg_bot_token:
        sys.exit("Set TG_BOT_TOKEN in .env (create a bot with @BotFather).")
    bot = Bot(settings.tg_bot_token.get_secret_value())
    dp = Dispatcher()
    dp.message.outer_middleware(remember_private)  # every private message, whichever router answers it
    dp.include_router(admin.router)  # before the generic handlers: /admin, /listen and their buttons
    dp.include_router(listen.router)
    dp.include_router(official.router)  # /official: an admin marks chats as official
    dp.include_router(abuse_commands.router)  # Administrative moderation remains available outside the menu.
    dp.include_router(router)
    me = await bot.me()
    log.info("Running as @%s", me.username)
    await set_commands(bot)
    await set_profile(bot, me.username or "")
    log.info("%d chats the bot already stores became chosen in /listen", await asyncio.to_thread(userbot_config.seed_bot_chats))
    writing = asyncio.create_task(writer.run())
    async def download(job: dict, ref: str) -> bytes:
        return await _download_image(bot, job, ref)

    async def allowed(job: dict) -> bool:
        return (await asyncio.to_thread(userbot_config.bot_listens, job["chat_id"])
                and store.topic_allowed(job["chat_id"], job["topic_id"]))

    recognizing = asyncio.create_task(images.run("tgbot", download, allowed=allowed))
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types(), close_bot_session=False)
    finally:
        recognizing.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await recognizing
        writing.cancel()  # Flushes what is already collected before stopping.
        with contextlib.suppress(asyncio.CancelledError):
            await writing
        pg.close()
        await bot.session.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
