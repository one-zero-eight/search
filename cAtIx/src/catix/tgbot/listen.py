"""Admin settings of the chats in the bot: /listen (it replaced the Telegram /group).

An admin (ADMIN_TELEGRAM_IDS) sees the chats the userbot is in and those only the Bot API bot (🤖) is in, turns
listening to them on and off, narrows a forum chat of the userbot to some of its topics and sets the study group of a
chat. All of it is kept in the database
(userbot_config.py); the userbot follows it within seconds and fetches the history of a chat that was just turned on.
Only in a private chat with the bot, so that nobody chatting in a group can change it.
"""

import asyncio
import html
import logging

from aiogram import F, Router
from aiogram.enums import ChatType, ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from catix import groups, userbot_config
from catix.db import pg, store
from catix.worker import changes

log = logging.getLogger("catix.listen")
router = Router()

PAGE_SIZE = 8
BUTTON_TITLE = 32
MAX_TOPIC_BUTTONS = 40
MAX_CODE_BUTTON = 24  # callback_data is limited to 64 bytes: "ls:s:<chat id>:<code>".

PAGE: dict[int, int] = {}  # admin -> the page of the chat list they were on, to come back to it
PENDING_GROUP: dict[int, int] = {}  # admin -> chat whose group code they are about to send

Keyboard = list[list[InlineKeyboardButton]]


def _button(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def _short(title: str, size: int = BUTTON_TITLE) -> str:
    return title if len(title) <= size else title[: size - 1] + "…"


async def _is_admin(user_id: int) -> bool:
    return user_id in await asyncio.to_thread(changes.admins)


def _group_of(chat_id: int) -> str:
    with pg.connection() as conn:
        return pg.scalar(conn, "SELECT group_code FROM chats WHERE chat_id = %s", (chat_id,)) or groups.ALL


def _groups_of(chat_ids: list[int]) -> dict[int, str]:
    with pg.connection() as conn:
        found = conn.execute("SELECT chat_id, group_code FROM chats WHERE chat_id = ANY(%s::bigint[])", (chat_ids,)).fetchall()
    return {r["chat_id"]: r["group_code"] for r in found}


def _known_groups() -> list[str]:
    """`all` first, then the other codes in use, the most used first."""
    with pg.connection() as conn:
        used = pg.column(conn, "SELECT group_code FROM chats WHERE group_code <> %s GROUP BY 1 ORDER BY count(*) DESC, 1", (groups.ALL,))
    return [groups.ALL, *used]


def _ensure_chat(dialog: userbot_config.Dialog) -> None:
    """The chat row holds the study group; it exists before the userbot has stored anything from the chat."""
    store.upsert_chat(dialog.chat_id, dialog.title, dialog.username)


# ---- screens --------------------------------------------------------------------------------------------------


def _list_screen(user_id: int) -> tuple[str, Keyboard]:
    dialogs = userbot_config.dialogs()
    if not dialogs:
        return (
            "Userbot пока не прислал список своих чатов: он делает это при запуске и раз в 10 минут. "
            "Если он запущен (<code>catix-tguserbot listen</code>), нажмите «Обновить».",
            [[_button("🔄 Обновить", "ls:r")]],
        )
    chosen = userbot_config.listened()
    pages = (len(dialogs) - 1) // PAGE_SIZE + 1
    page = min(PAGE.get(user_id, 0), pages - 1)
    PAGE[user_id] = page
    shown = dialogs[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]
    codes = _groups_of([d.chat_id for d in shown])
    rows: Keyboard = []
    for d in shown:
        code = codes.get(d.chat_id, groups.ALL)
        label = f"{'✅' if d.chat_id in chosen else '⬜'} {_short(d.title)}{' 🧵' if d.forum else ''}{' 🤖' if d.bot_in else ''}{'' if code == groups.ALL else ' · ' + code}"
        rows.append([_button(label, f"ls:c:{d.chat_id}")])
    nav = []
    if page > 0:
        nav.append(_button("◀", f"ls:l:{page - 1}"))
    nav.append(_button(f"{page + 1}/{pages}", "ls:n"))
    if page < pages - 1:
        nav.append(_button("▶", f"ls:l:{page + 1}"))
    rows.append(nav)
    rows.append([_button("🔄 Обновить список", "ls:r")])
    text = (
        f"<b>Чаты userbot</b>: слушаю {len(chosen)} из {len(dialogs)}.\n"
        "✅ — слушаю, 🧵 — форум с топиками, 🤖 — в чате есть бот, после · — учебная группа чата. "
        "Нажмите на чат, чтобы настроить."
    )
    return text, rows


def _reader_line(dialog: userbot_config.Dialog, choice: str) -> str:
    if dialog.bot_only:
        return "Читает: бот (сообщения с момента добавления, истории нет)"
    if not dialog.bot_in:
        return "Читает: userbot (с историей)"
    effective = userbot_config.effective_reader(choice, True)
    who = "userbot (с историей)" if effective == "userbot" else "бот (с момента добавления, без истории)"
    return f"Читает: {who}" + (" (авто)" if choice == "auto" else "") + ". В чате есть и userbot, и бот: читает один из них."


def _chat_screen(chat_id: int) -> tuple[str, Keyboard]:
    dialog = userbot_config.dialog(chat_id)
    if dialog is None:
        return "Этого чата больше нет в списке userbot.", [[_button("← К списку", "ls:l:keep")]]
    chosen = userbot_config.listened()
    on = chat_id in chosen
    lines = [
        f"<b>{html.escape(dialog.title)}</b>",
        f"Тип: {'канал' if dialog.kind == 'channel' else 'группа'}{', форум' if dialog.forum else ''}",
        _reader_line(dialog, userbot_config.readers().get(chat_id, "auto")),
        f"Слушаю: {'да' if on else 'нет'}",
    ]
    rows: Keyboard = [[_button("🔕 Перестать слушать" if on else "🔔 Слушать", f"ls:o:{chat_id}")]]
    if on and dialog.bot_in and not dialog.bot_only:  # Both can read it: one of them must (two copies of everything otherwise).
        current = userbot_config.readers().get(chat_id, "auto")
        rows.append([
            _button(f"{'✅ ' if current == code else ''}{name}", f"ls:w:{chat_id}:{code}")
            for code, name in (("auto", "Авто"), ("userbot", "👤 userbot"), ("bot", "🤖 бот"))
        ])
    if dialog.forum and not dialog.bot_only:  # The Bot API gives no list of topics.
        selected = chosen.get(chat_id)
        total = len(userbot_config.topics(chat_id))
        lines.append("Топики: " + (f"выбраны {len(selected)} из {total}" if selected else "все"))
        if on:
            rows.append([_button("🧵 Топики", f"ls:t:{chat_id}")])
    lines.append(f"Учебная группа: {html.escape(_group_of(chat_id))}")
    current = _group_of(chat_id)
    # Codes already in use (and `all`) are one tap; any other code is typed.
    known = [c for c in _known_groups() if len(c) <= MAX_CODE_BUTTON]
    rows.append([_button(f"{'✅ ' if c == current else ''}{c}", f"ls:s:{chat_id}:{c}") for c in known[:4]] or [])
    rows.append([_button("🎓 Другая группа…", f"ls:g:{chat_id}")])
    stored, _ = store.chat_message_counts(chat_id)
    lines.append(f"Сообщений в базе: {stored}")
    if stored:
        rows.append([_button(f"🗑 Очистить сообщения ({stored})", f"ls:cl:{chat_id}")])
    rows.append([_button("← К списку", "ls:l:keep")])
    return "\n".join(lines), rows


def _clear_screen(chat_id: int) -> tuple[str, Keyboard]:
    dialog = userbot_config.dialog(chat_id)
    title = html.escape(dialog.title) if dialog else str(chat_id)
    stored, changes = store.chat_message_counts(chat_id)
    text = (
        f"Удалить все <b>{stored}</b> сообщений чата «{title}» и их эмбеддинги? Это необратимо.\n"
        + (f"Вместе с ними удалятся найденные в них изменения расписания: {changes}.\n" if changes else "")
        + "Сам чат, его учебная группа и выбор «слушать» остаются. "
        + ("Пока чат включён, новые сообщения продолжат сохраняться." if chat_id in userbot_config.listened() else "")
    )
    return text.strip(), [
        [_button("✅ Да, удалить", f"ls:cy:{chat_id}"), _button("← Отмена", f"ls:c:{chat_id}")],
    ]


def _topics_screen(chat_id: int) -> tuple[str, Keyboard]:
    dialog = userbot_config.dialog(chat_id)
    found = userbot_config.topics(chat_id)
    selected = userbot_config.listened().get(chat_id)
    title = html.escape(dialog.title) if dialog else str(chat_id)
    if not found:
        return (
            f"<b>{title}</b>: список топиков ещё не получен. Нажмите «Обновить» на экране списка чатов.",
            [[_button("← Назад", f"ls:c:{chat_id}")]],
        )
    rows: Keyboard = [[_button(f"{'✅' if not selected else '⬜'} Все топики", f"ls:a:{chat_id}")]]
    for t in found[:MAX_TOPIC_BUTTONS]:
        mark = "✅" if selected and t.topic_id in selected else "⬜"
        rows.append([_button(f"{mark} {_short(t.title)}{' 🔒' if t.closed else ''}", f"ls:x:{chat_id}:{t.topic_id}")])
    rows.append([_button("← Назад", f"ls:c:{chat_id}")])
    note = f"\nПоказаны первые {MAX_TOPIC_BUTTONS} топиков." if len(found) > MAX_TOPIC_BUTTONS else ""
    return f"<b>{title}</b>: какие топики сохранять.\nЕсли не выбран ни один, сохраняется весь чат.{note}", rows


async def _show(query: CallbackQuery, screen: tuple[str, Keyboard]) -> None:
    text, rows = screen
    try:
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    except TelegramBadRequest as e:
        if "not modified" not in str(e):
            raise


# ---- handlers -------------------------------------------------------------------------------------------------


@router.message(F.chat.type == ChatType.PRIVATE, Command("listen"))
async def listen_command(message: Message) -> None:
    if not await _is_admin(message.from_user.id):
        await message.answer("Только для администратора.")
        return
    PENDING_GROUP.pop(message.from_user.id, None)
    text, rows = await asyncio.to_thread(_list_screen, message.from_user.id)
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data.startswith("ls:"))
async def listen_callback(query: CallbackQuery) -> None:
    user_id = query.from_user.id
    if not await _is_admin(user_id):
        await query.answer("Только для администратора", show_alert=True)
        return
    _, action, *args = query.data.split(":")
    notice = None
    match action:
        case "n":
            await query.answer()
            return
        case "r":
            await asyncio.to_thread(userbot_config.request_refresh)
            notice = "Попросил userbot обновить список, это занимает до 15 секунд"
            screen = await asyncio.to_thread(_list_screen, user_id)
        case "l":
            if args[0] != "keep":
                PAGE[user_id] = int(args[0])
            screen = await asyncio.to_thread(_list_screen, user_id)
        case "c":
            screen = await asyncio.to_thread(_chat_screen, int(args[0]))
        case "o":
            chat_id = int(args[0])
            dialog = await asyncio.to_thread(userbot_config.dialog, chat_id)
            if dialog and chat_id not in await asyncio.to_thread(userbot_config.listened):
                await asyncio.to_thread(_ensure_chat, dialog)
                await asyncio.to_thread(userbot_config.set_listen, chat_id, True)
                notice = "Слушаю. Бот сохраняет сообщения с этого момента" if dialog.bot_only else "Слушаю. Историю userbot подгрузит в течение минуты"
            else:
                await asyncio.to_thread(userbot_config.set_listen, chat_id, False)
                notice = "Больше не слушаю (сохранённые сообщения остаются)"
            screen = await asyncio.to_thread(_chat_screen, chat_id)
        case "w":  # Who reads the chat (its own letter: "r" is the refresh above).
            chat_id, code = int(args[0]), args[1]
            if code in userbot_config.READERS:
                await asyncio.to_thread(userbot_config.set_reader, chat_id, code)
                notice = {"auto": "Читает userbot, если он в чате", "userbot": "Читает userbot", "bot": "Читает бот"}[code]
            screen = await asyncio.to_thread(_chat_screen, chat_id)
        case "cl":
            screen = await asyncio.to_thread(_clear_screen, int(args[0]))
        case "cy":
            chat_id = int(args[0])
            deleted = await asyncio.to_thread(store.clear_chat, chat_id)
            log.info("admin %s cleared %d messages of chat %s", user_id, deleted, chat_id)
            notice = f"Удалено сообщений: {deleted}"
            screen = await asyncio.to_thread(_chat_screen, chat_id)
        case "t":
            screen = await asyncio.to_thread(_topics_screen, int(args[0]))
        case "x":
            await asyncio.to_thread(userbot_config.toggle_topic, int(args[0]), int(args[1]))
            screen = await asyncio.to_thread(_topics_screen, int(args[0]))
        case "a":
            await asyncio.to_thread(userbot_config.clear_topics, int(args[0]))
            screen = await asyncio.to_thread(_topics_screen, int(args[0]))
        case "s":
            chat_id, code = int(args[0]), ":".join(args[1:])
            dialog = await asyncio.to_thread(userbot_config.dialog, chat_id)
            if dialog and groups.normalize(code):
                await asyncio.to_thread(_ensure_chat, dialog)
                await asyncio.to_thread(groups.set_chat_group, chat_id, groups.normalize(code))
                notice = f"Группа чата: {code}"
            screen = await asyncio.to_thread(_chat_screen, chat_id)
        case "g":
            PENDING_GROUP[user_id] = int(args[0])
            await query.answer()
            await query.message.answer(
                "Отправьте код учебной группы этого чата, например B26-CSE-01. "
                f"<code>{groups.ALL}</code> значит «для всех». Другая команда отменит ввод.",
                parse_mode=ParseMode.HTML,
            )
            return
        case _:
            await query.answer()
            return
    await query.answer(notice)
    await _show(query, screen)


def _waiting_for_group(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id in PENDING_GROUP and message.text and not message.text.startswith("/"))


@router.message(F.chat.type == ChatType.PRIVATE, F.text, _waiting_for_group)
async def group_code(message: Message) -> None:
    chat_id = PENDING_GROUP[message.from_user.id]
    code = groups.normalize(message.text)
    if code is None:
        await message.answer("Код группы: латинские буквы, цифры, точка, дефис или подчёркивание, до 40 символов. Попробуйте ещё раз.")
        return
    del PENDING_GROUP[message.from_user.id]
    dialog = await asyncio.to_thread(userbot_config.dialog, chat_id)
    if dialog:
        await asyncio.to_thread(_ensure_chat, dialog)
    await asyncio.to_thread(groups.set_chat_group, chat_id, code)
    text, rows = await asyncio.to_thread(_chat_screen, chat_id)
    await message.answer(f"Группа чата: {html.escape(code)}.\n\n{text}", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
