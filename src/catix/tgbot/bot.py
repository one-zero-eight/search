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
import html
import logging
import re
import sys
import time
import uuid
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatMemberStatus, ChatType, ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import (
    BotCommand,
    BotCommandScopeChat,
    CallbackQuery,
    ChatMemberUpdated,
    ChosenInlineResult,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    LinkPreviewOptions,
    Message,
    MessageOriginChannel,
    MessageOriginChat,
    MessageOriginHiddenUser,
    MessageOriginUser,
)
from aiogram.utils.chat_action import ChatActionSender

from catix.tgbot import abuse as abuse_commands
from catix.tgbot import admin
from catix.tgbot import listen
from catix.tgbot import official
from catix.worker import changes
from catix import bot_users, groups, personal_calendar, userbot_config
from catix.ingest import writer as ingest
from catix.ingest import images
from catix.db import pg
from catix.agent import sqlquery
from catix.db import store
from catix.tgbot import stream
from catix.agent import events as calendar_events
from catix.agent import tracing
from catix.agent.core import build_agent, final_answer
from catix.agent.questions import QuestionQueue
from catix.common import cache
from catix.common.render import chunks as _chunks
from catix.common.render import to_html as _to_html
from catix.common.llm_down import UNAVAILABLE, unreachable
from catix.settings import settings
from catix.agent.tools import AgentContext

log = logging.getLogger("catix.bot")
router = Router()
agent = build_agent()
# Private chats, groups and inline queries take turns at the agent (agent/questions.py).
questions = QuestionQueue(settings.agent_parallel_questions)
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


async def _run_agent(
    question: str,
    thread_id: str,
    user_id: int | None,
    streamer: stream.DraftStreamer | None,
    brief: bool = False,
) -> tuple[str, str | None]:
    """Ask the agent; it may use the chats of the asker's study group (found by Telegram id).
    Returns the answer and the root span of its trace in Phoenix (for the 👍/👎 under it)."""
    allowed = await asyncio.to_thread(groups.scoped_chat_ids, f"tg:{user_id or 0}", user_id)
    group = await asyncio.to_thread(groups.effective_group, f"tg:{user_id or 0}", user_id)
    config = tracing.run_config(thread_id, str(user_id) if user_id else None)
    context = AgentContext(
        allowed_chat_ids=None if allowed is None else frozenset(allowed),
        user_telegram_id=user_id,
        brief=brief,
        study_group=None if group == groups.ALL else group,
    )
    on_wait = streamer.queued if streamer else None
    async with questions.turn(f"tg:{user_id or 0}", on_wait, stream.QUEUE_REPEAT_SECONDS):
        with tracing.question(thread_id, str(user_id) if user_id else None, question) as traced:
            state = await stream.run(agent, {"messages": [{"role": "user", "content": question}]}, config, context, streamer)
            answer = final_answer(state["messages"], state.get("sources") or {}) or "Не получилось сформулировать ответ."
            traced.answer(answer)
    return answer, traced.id


def _event_label(event: dict) -> str:
    start = datetime.fromisoformat(event["starts_at"]).astimezone(settings.tz)
    when = f"{start:%d.%m.%Y}" if event.get("all_day") else f"{start:%d.%m.%Y %H:%M}"
    if not event.get("all_day") and event.get("ends_at"):
        end = datetime.fromisoformat(event["ends_at"]).astimezone(settings.tz)
        when += f"–{end:%H:%M}" if start.date() == end.date() else f" – {end:%d.%m.%Y %H:%M}"
        if event.get("end_suggested"):
            when += f" · предлагается {personal_calendar.PROPOSED_DURATION_MINUTES} мин"
    return f"➕ В мой календарь: {event['title'][:28]} · {when}"


def _feedback_keyboard(
    trace: str | None, chosen: bool | None = None, extra: list[list[InlineKeyboardButton]] | None = None
) -> InlineKeyboardMarkup | None:
    """👍/👎 under an answer (they annotate the trace in Phoenix; after a vote only the chosen one is shown), then one
    "add to my calendar" button per event the agent offered."""
    if not trace and not extra:
        return None
    rows = list(extra or [])
    if trace:
        if chosen is not None:
            rows.insert(0, [InlineKeyboardButton(text=f"Оценка: {'👍' if chosen else '👎'}", callback_data="fb:done")])
        else:
            rows.insert(0, [InlineKeyboardButton(text="👍", callback_data=f"fb:1:{trace}"), InlineKeyboardButton(text="👎", callback_data=f"fb:0:{trace}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.startswith("fb:"))
async def feedback(query: CallbackQuery, bot: Bot) -> None:
    parts = query.data.split(":")
    if parts[1] == "done":
        await query.answer("Спасибо за оценку")
        return
    good, trace = parts[1] == "1", parts[2]
    try:
        await asyncio.to_thread(tracing.score_feedback, trace, f"tg:{query.from_user.id}", good)
    except Exception:  # noqa: BLE001 - a vote must never break the bot
        log.exception("could not save the feedback")
    await query.answer("Спасибо!" if good else "Спасибо, разберём")
    kept = query.message.reply_markup.inline_keyboard[1:] if query.message and query.message.reply_markup else None
    markup = _feedback_keyboard(trace, good, kept)
    with contextlib.suppress(TelegramAPIError):
        if query.inline_message_id:
            await bot.edit_message_reply_markup(inline_message_id=query.inline_message_id, reply_markup=markup)
        elif query.message:
            await query.message.edit_reply_markup(reply_markup=markup)


# ---- calendar: /calendar and the "add to my calendar" buttons -----------------------------------------------------


def _calendar_screen(user_id: int) -> tuple[str, InlineKeyboardMarkup | None]:
    lines = [
        "🗓 <b>Ваш личный календарь</b>: события, которые вы добавили кнопкой «➕ В мой календарь» под ответами здесь и на сайте.",
        "Он хранится в вашем аккаунте InNoHassle и виден в календаре innohassle.ru/calendar.",
    ]
    try:
        user_key = personal_calendar.telegram_key(user_id)
    except personal_calendar.NoAccount as e:
        return "\n".join([*lines, "", html.escape(str(e))]), None
    rows = []
    events = personal_calendar.upcoming(user_key, 5)
    if events:
        lines += ["", "<b>Ближайшие ваши события</b>:"]
        for event in events:
            start = event.starts_at.astimezone(settings.tz)
            lines.append(f"• {html.escape(event.title)}: {start:%d.%m} " + ("" if event.all_day else f"{start:%H:%M}"))
            rows.append([InlineKeyboardButton(text=f"❌ Убрать: {event.title[:30]}", callback_data=f"cal:del:{event.id}")])
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


@router.message(F.chat.type == ChatType.PRIVATE, Command("calendar"))
async def calendar_command(message: Message) -> None:
    text, keyboard = await asyncio.to_thread(_calendar_screen, message.from_user.id)
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=keyboard, disable_web_page_preview=True)


@router.callback_query(F.data.startswith("cal:"))
async def calendar_callback(query: CallbackQuery) -> None:
    _, action, *args = query.data.split(":")
    if action == "done":
        await query.answer("Уже в вашем календаре")
        return
    try:
        user_key = await asyncio.to_thread(personal_calendar.telegram_key, query.from_user.id)
    except personal_calendar.NoAccount as e:  # Nothing is added: the button stays for after the Telegram is linked.
        await query.answer(str(e), show_alert=True)
        return
    if action == "add":  # Anyone can add an offered event to their own calendar, in a group too.
        title = await asyncio.to_thread(personal_calendar.add_proposal, user_key, args[0])
        if title is None:
            await query.answer("Предложение устарело", show_alert=True)
            return
        await query.answer("Добавлено в ваш календарь: /calendar")
        with contextlib.suppress(TelegramAPIError):
            rows = [
                [InlineKeyboardButton(text="✅ Добавлено", callback_data="cal:done")] if b.callback_data == query.data else [b]
                for row in query.message.reply_markup.inline_keyboard
                for b in row
            ] if query.message and query.message.reply_markup else []
            await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
        return
    if action != "del":
        return
    await asyncio.to_thread(personal_calendar.delete_event, user_key, int(args[0]))
    await query.answer("Убрано")
    text, keyboard = await asyncio.to_thread(_calendar_screen, query.from_user.id)
    with contextlib.suppress(TelegramAPIError):
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard, disable_web_page_preview=True)


_background: set[asyncio.Task] = set()


async def _offer_events(sent: Message, answer: str, trace: str) -> None:
    """If the answer names upcoming events, add an "add to my calendar" button for each under it."""
    try:
        events = await asyncio.to_thread(calendar_events.extract, answer)
        if not events:
            return
        offered = await asyncio.to_thread(personal_calendar.propose, events)
        rows = [[InlineKeyboardButton(text=_event_label(event), callback_data=f"cal:add:{pid}")] for pid, event in offered]
        await sent.edit_reply_markup(reply_markup=_feedback_keyboard(trace, extra=rows))
    except TelegramAPIError as e:
        log.info("calendar buttons not added: %s", e)
    except Exception:  # noqa: BLE001 - the answer is already delivered; this is a bonus
        log.exception("could not offer calendar events")


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
    # Drafts exist only in private chats; groups get the typing indicator and one message at the end.
    streamer = (
        stream.DraftStreamer(message.bot, message.chat.id, message.message_thread_id if message.is_topic_message else None, _to_html)
        if message.chat.type == ChatType.PRIVATE
        else None
    )
    async with ChatActionSender.typing(chat_id=message.chat.id, bot=message.bot, message_thread_id=message.message_thread_id):
        try:
            answer, trace = await _run_agent(question, thread_id, message.from_user.id if message.from_user else None, streamer)
            log.info("answered in %.1fs, %d chars", time.monotonic() - started, len(answer))
        except Exception as e:
            log.exception("agent failed")
            answer, trace = UNAVAILABLE if unreachable(e) else "Не получилось ответить: ошибка на стороне ассистента. Попробуйте ещё раз позже.", None

    parts = _chunks(answer, 4096)
    if streamer and parts:  # The draft must begin like the answer, or Telegram Desktop leaves it next to it (stream.py).
        await streamer.finish(_to_html(parts[0]))
    sent = None
    for i, chunk in enumerate(parts):
        keyboard = _feedback_keyboard(trace) if i == len(parts) - 1 else None  # Under the last piece.
        try:
            sent = await message.reply(_to_html(chunk), parse_mode=ParseMode.HTML, disable_web_page_preview=True, reply_markup=keyboard)
        except TelegramBadRequest:
            # Converter produced HTML Telegram does not accept: fall back to plain text.
            sent = await message.reply(chunk, disable_web_page_preview=True, reply_markup=keyboard)
    if sent and trace:
        task = asyncio.create_task(_offer_events(sent, answer, trace))  # After the answer: it does not delay it.
        _background.add(task)
        task.add_done_callback(_background.discard)


@router.message(CommandStart())
async def start(message: Message) -> None:
    is_admin = message.from_user is not None and message.from_user.id in await asyncio.to_thread(changes.admins)
    await message.answer(
        "Привет! Я cAtIx, ассистент Innopolis University: клубы, аудитории, события, а также экзамены, дедлайны и советы "
        "из чатов, куда меня добавили.\n\nСюда я присылаю переносы, отмены и новые события, которые нашёл в чатах "
        "вашей учебной группы (/mygroup) и в общих: кнопка «✅ В мой календарь» добавит событие в /calendar.\n\n"
        "В личке просто пишите вопрос. В группе: /ask вопрос, упоминание или ответ "
        "на моё сообщение.\n\n/mygroup: ваша учебная группа (по умолчанию ищу везде).\n"
        "/clear: забыть наш разговор и начать заново."
        + ("\n/listen и /admin: для администратора: чаты и учебные группы, другие администраторы." if is_admin else "")
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


# The study group of a chat is set by an admin in /listen (listen.py), together with what the userbot listens to.


@router.message(F.chat.type == ChatType.PRIVATE, Command("mygroup"))
async def my_group(message: Message, command: CommandObject) -> None:
    user_id = message.from_user.id
    may_set = groups.manual_group_allowed(user_id in await asyncio.to_thread(changes.admins))
    await message.answer(await asyncio.to_thread(lambda: groups.mygroup_command(command.args or "", f"tg:{user_id}", user_id, may_set=may_set)))


@router.message(Command("clear", "new"))
async def clear_context(message: Message) -> None:
    """Forget the conversation: the agent keeps the earlier questions and answers of this chat, per user."""
    thread_id = f"tg:{message.chat.id}:{message.from_user.id if message.from_user else 0}"
    await asyncio.to_thread(agent.checkpointer.delete_thread, thread_id)
    await message.reply("Память диалога очищена: следующий вопрос начнёт разговор заново.")


@router.message(Command("ask"))
async def ask(message: Message, command: CommandObject) -> None:
    # Questions to the bot are not saved: they would show up as search results for the same question.
    await _reply(message, command.args or "")


@router.message(F.chat.type == ChatType.PRIVATE, F.text)
async def private(message: Message) -> None:
    await _reply(message, message.text)


@router.message(F.chat.type.in_(GROUPS))
async def group(message: Message, bot: Bot) -> None:
    observed_at = datetime.now(timezone.utc)
    me = await bot.me()
    text = message.text or message.caption or ""
    mention = f"@{me.username}"
    is_reply_to_bot = bool(message.reply_to_message and message.reply_to_message.from_user and message.reply_to_message.from_user.id == me.id)
    if mention.lower() in text.lower() or is_reply_to_bot or re.match(r"^/ask(?:@\w+)?(?:\s|$)", text):
        question = re.sub(re.escape(mention), "", text, flags=re.I)
        await _reply(message, re.sub(r"^/ask(?:@\w+)?(?:\s|$)", "", question))
    else:
        await _save(message, observed_at=observed_at)


async def _delete_excluded_edit(message: Message, *, observed_at: datetime) -> None:
    # Match _save's listener/topic boundary and migrated storage identity.
    if not await asyncio.to_thread(userbot_config.bot_listens, message.chat.id):
        return
    topic_id = message.message_thread_id if message.is_topic_message else None
    if not store.topic_allowed(message.chat.id, topic_id):
        return
    await asyncio.to_thread(
        store.delete_message, MIGRATED.get(message.chat.id, message.chat.id), message.message_id,
        edit_date=datetime.fromtimestamp(message.edit_date, timezone.utc) if message.edit_date else message.date,
        observed_at=observed_at,
    )


@router.edited_message(F.chat.type.in_(GROUPS))
async def edited(message: Message) -> None:
    observed_at = datetime.now(timezone.utc)
    text = message.text or message.caption or ""
    if re.match(r"^/ask(?:@\w+)?(?:\s|$)", text):
        await _delete_excluded_edit(message, observed_at=observed_at)
        return
    if text or message.reply_to_message:
        me = await message.bot.me()
        if (f"@{me.username}".lower() in text.lower()
                or (message.reply_to_message and message.reply_to_message.from_user
                    and message.reply_to_message.from_user.id == me.id)):
            await _delete_excluded_edit(message, observed_at=observed_at)
            return
    await _save(message, observed_at=observed_at)


# Channels deliver posts as channel_post updates, and only to bots that are channel admins.
# The bot never answers in channels, it only stores posts.
@router.channel_post()
@router.edited_channel_post()
async def channel_post(message: Message) -> None:
    await _save(message)


# ---- inline mode: `@bot question` in any chat -----------------------------------------------------------------------
# The answer goes into the result card itself, so picking the card sends it ready. A client sends a query on every
# keystroke, so the agent starts only after the user stops typing (INLINE_DEBOUNCE). If it is not done within
# INLINE_WAIT, the query is answered with a placeholder card anyway (Telegram drops a query that waits too long), and
# when that card is picked the finished answer replaces it (chosen_inline_result, enable it with @BotFather ->
# /setinlinefeedback -> 100%). Telegram gives an inline_message_id only for results that carry a keyboard, hence the button.
INLINE_DEBOUNCE = 1.2  # Seconds without a new keystroke.
INLINE_WAIT = 8.0  # Seconds the query may wait for the agent.
INLINE_KEEP = 600  # Seconds an unclaimed answer is kept.

_inline_latest: dict[int, str] = {}  # user id -> id of their newest inline query
_inline_tasks: dict[tuple[int, str], tuple[float, asyncio.Task[tuple[str, str | None]]]] = {}


async def _inline_answer(user_id: int, question: str) -> tuple[str, str | None]:
    """The answer and the root span of its trace."""
    log.info("inline question from %s: %s", user_id, question[:200])
    # Every inline question starts fresh: its own thread, dropped when the answer is ready.
    thread_id = f"tg:inline:{user_id}:{uuid.uuid4().hex}"
    try:
        # One answer per message, an inline message cannot be followed by more.
        answer, trace = await _run_agent(question, thread_id, user_id, None, brief=True)  # No calendar buttons in a card.
        return _chunks(answer, 3500)[0], trace
    except Exception as e:
        log.exception("inline agent failed")
        return UNAVAILABLE if unreachable(e) else "Не получилось ответить: ошибка на стороне ассистента. Попробуйте ещё раз позже.", None
    finally:
        agent.checkpointer.delete_thread(thread_id)


def _inline_task(user_id: int, question: str) -> asyncio.Task[tuple[str, str | None]]:
    """The running or finished answer to this question; asking again while it works does not start another run."""
    now = time.monotonic()
    for key in [k for k, (started, _) in _inline_tasks.items() if now - started > INLINE_KEEP]:
        del _inline_tasks[key]
    if (user_id, question) not in _inline_tasks:
        _inline_tasks[user_id, question] = (now, asyncio.create_task(_inline_answer(user_id, question)))
    return _inline_tasks[user_id, question][1]


def _inline_text(question: str, answer: str) -> InputTextMessageContent:
    return InputTextMessageContent(message_text=_to_html(f"❓ {question}\n\n{answer}"), parse_mode=ParseMode.HTML, link_preview_options=LinkPreviewOptions(is_disabled=True))


@router.inline_query()
async def inline_query(query: InlineQuery) -> None:
    question = query.query.strip()
    if not question:
        hint = InlineQueryResultArticle(
            id="hint",
            title="Введите вопрос",
            description="Например: когда мидтерм по матану?",
            input_message_content=InputTextMessageContent(message_text="Чтобы спросить cAtIx: @имя_бота вопрос"),
        )
        await query.answer([hint], cache_time=0, is_personal=True)
        return

    _inline_latest[query.from_user.id] = query.id
    await asyncio.sleep(INLINE_DEBOUNCE)
    if _inline_latest.get(query.from_user.id) != query.id:
        return  # The user typed on: a newer query will be answered.

    task = _inline_task(query.from_user.id, question)
    await asyncio.wait({task}, timeout=INLINE_WAIT)
    if task.done():
        answer, trace = task.result()
        result = InlineQueryResultArticle(
            id=f"ans:{uuid.uuid4().hex}",
            title=answer.split("\n", 1)[0][:100] or "Ответ",
            description=answer[:200],
            input_message_content=_inline_text(question, answer),
            reply_markup=_feedback_keyboard(trace),
        )
    else:
        result = InlineQueryResultArticle(
            id=f"wait:{uuid.uuid4().hex}",
            title="Спросить cAtIx",
            description=f"{question}\nОтвет появится после выбора",
            input_message_content=InputTextMessageContent(message_text=f"❓ {question}\n\n⏳ Ищу ответ…"),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⏳ Ищу ответ…", callback_data="inline:wait")]]),
        )
    try:
        await query.answer([result], cache_time=0, is_personal=True)
    except TelegramBadRequest as e:
        log.warning("inline query answered too late or rejected: %s", e)


@router.chosen_inline_result(F.result_id.startswith("wait:"))
async def inline_chosen(chosen: ChosenInlineResult, bot: Bot) -> None:
    """A placeholder card was picked: the answer replaces it as soon as the agent is done."""
    if not chosen.inline_message_id:
        return
    question = chosen.query.strip()
    answer, trace = await _inline_task(chosen.from_user.id, question)
    text = _inline_text(question, answer)
    keyboard = _feedback_keyboard(trace)  # Replaces the "searching" button.
    try:
        await bot.edit_message_text(
            text.message_text, inline_message_id=chosen.inline_message_id, parse_mode=ParseMode.HTML,
            link_preview_options=text.link_preview_options, reply_markup=keyboard,
        )
    except TelegramBadRequest:
        await bot.edit_message_text(f"❓ {question}\n\n{answer}", inline_message_id=chosen.inline_message_id, reply_markup=keyboard)


@router.callback_query(F.data == "inline:wait")
async def inline_wait(query: CallbackQuery) -> None:
    await query.answer("Ещё думаю…")


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
        done = await asyncio.to_thread(changes.add_to_calendar, user_key, int(change_id))
        verdict = f"✅ {done[:180]}. /calendar" if done else "Изменение не найдено"
    else:
        verdict = "❌ Не добавлено"
    await query.answer(verdict)
    if query.message:
        await query.message.edit_text(f"{query.message.html_text}\n\n{verdict}", parse_mode=ParseMode.HTML, reply_markup=None, disable_web_page_preview=True)


COMMANDS = [
    BotCommand(command="start", description="Что я умею"),
    BotCommand(command="ask", description="Задать вопрос (в группе)"),
    BotCommand(command="mygroup", description="Моя учебная группа"),
    BotCommand(command="clear", description="Очистить память диалога"),
    BotCommand(command="calendar", description="Мой календарь"),
    BotCommand(command="id", description="ID чата и топика"),
]
ADMIN_COMMANDS = [
    *COMMANDS,
    BotCommand(command="listen", description="Чаты для прослушки и учебные группы"),
    BotCommand(command="admin", description="Администраторы бота"),
]


async def set_commands(bot: Bot) -> None:
    """The command menu in Telegram: the same for everybody, plus /listen for the admins (in their private chats)."""
    await bot.set_my_commands(COMMANDS)
    try:
        admin_ids = await asyncio.to_thread(changes.admins)
    except Exception:  # noqa: BLE001 - the menu is a convenience, the bot must start without it
        log.warning("could not look up the admins, /listen is not in their menu", exc_info=True)
        return
    for admin_id in admin_ids:
        try:
            await bot.set_my_commands(ADMIN_COMMANDS, scope=BotCommandScopeChat(chat_id=admin_id))
        except TelegramAPIError as e:
            log.warning("menu for admin %s not set (they have not started the bot yet?): %s", admin_id, e)


def profile_texts(username: str) -> dict[str | None, tuple[str, str]]:
    """The bot's profile by the language of a person's Telegram (None: any other, Russian as the rest of the bot): the
    description an empty chat with the bot shows above Start (at most 512 characters) and the short description of its
    profile and of a link to it (at most 120)."""
    return {
        None: (
            "Привет! Я cAtIx, ассистент Университета Иннополис.\n\n"
            "Отвечаю на вопросы об учёбе и кампусе: положения и приказы, учебные программы, аудитории, клубы, события, "
            "а также экзамены, дедлайны и советы из учебных чатов. В ответе указываю источники.\n\n"
            "Присылаю переносы и отмены занятий, найденные в чатах вашей группы, и по кнопке добавляю их в ваш календарь.\n\n"
            f"Нажмите «Старт» и напишите вопрос. В группе: /ask или упоминание, в любом чате: @{username} вопрос.",
            "Ассистент Университета Иннополис: документы, аудитории, клубы, события и ответы из учебных чатов с источниками.",
        ),
        "en": (
            "Hi! I'm cAtIx, the Innopolis University assistant.\n\n"
            "I answer questions about studies and campus life: regulations and orders, course programmes, rooms, clubs, "
            "events, and exams, deadlines and tips from the study chats. Every answer cites its sources.\n\n"
            "I send you the reschedules and cancellations I find in your group's chats and add them to your calendar with "
            "one tap.\n\n"
            f"Press Start and ask a question. In a group: /ask or a mention; in any chat: @{username} question.",
            "Innopolis University assistant: documents, rooms, clubs, events and answers from the study chats, with sources.",
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
    dp.include_router(abuse_commands.router)  # /abuse: repeated attacks, lift a pause
    dp.include_router(router)
    me = await bot.me()
    log.info("Running as @%s", me.username)
    await set_commands(bot)
    await set_profile(bot, me.username or "")
    log.info("%d chats the bot already stores became chosen in /listen", await asyncio.to_thread(userbot_config.seed_bot_chats))
    tracing.log_status()
    await asyncio.to_thread(sqlquery.reset_context)  # Rows left behind by a crash.
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
        tracing.flush()
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
