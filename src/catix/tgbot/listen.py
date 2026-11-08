"""Private-admin Telegram group configuration, also reachable through /listen.

Chat, study group, topic modes and reader stay in a nonce-bound draft until confirmation.
The backend saves the configuration atomically; disabling never deletes message history.
"""

import asyncio
import html
import logging
import re
import secrets
from dataclasses import dataclass, field

from aiogram import F, Router
from aiogram.enums import ChatType, ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from catix import groups, official, userbot_config
from catix.db import pg, store
from catix.tgbot import source_requests
from catix.worker import changes

log = logging.getLogger("catix.listen")
router = Router()
router.include_router(source_requests.router)

PAGE_SIZE = 8
BUTTON_TITLE = 32


PAGE: dict[int, int] = {}  # admin -> the page of the chat list they were on, to come back to it
PENDING_GROUP: dict[int, int] = {}  # Legacy cancellation hook; new prompts live in Session.

Keyboard = list[list[InlineKeyboardButton]]
MODES = {"store": "Хранить", "search": "Только поиск", "off": "Выключен"}
HISTORY_NOTE = ("Выключен — новые сообщения не сохраняются, поиск Telegram отключён. "
                "Сохранённые сообщения остаются в базе знаний до явной очистки истории.")


@dataclass
class Session:
    private_chat: int
    nonce: str = field(default_factory=lambda: secrets.token_hex(4))
    stage: str = "pick"
    chat_id: int = 0
    group: str = groups.ALL
    default: str = "search"
    topics: dict[int, str] = field(default_factory=dict)
    reader: str = "auto"
    codes: list[str] = field(default_factory=list)
    target_topic: int = 0
    page: int = 0
    search: str = ""
    prompt: str = ""


SESSIONS: dict[int, Session] = {}


def cancel_pending(user_id: int) -> None:
    """Called by /admin and navigation: discard every unsaved choice and text prompt."""
    SESSIONS.pop(user_id, None)
    PENDING_GROUP.pop(user_id, None)


def _cancel_admin_prompt(user_id: int) -> None:
    from catix.tgbot import admin

    admin.PENDING.discard(user_id)


def _draft_button(s: Session, text: str, action: str, value: str | int = "") -> InlineKeyboardButton:
    return _button(text, f"ls:d:{s.nonce}:{action}:{value}")


def _topics(chat_id: int) -> list[userbot_config.Topic]:
    found = userbot_config.topics(chat_id)
    if not any(t.topic_id == store.GENERAL_TOPIC_ID for t in found):
        found = [userbot_config.Topic(store.GENERAL_TOPIC_ID, "General / Общий", False), *found]
    return found


def _topic_summary(chat_id: int, default: str, topics: dict[int, str]) -> list[str]:
    found = _topics(chat_id)
    lines = []
    for mode, label in MODES.items():
        names = [t.title for t in found if topics.get(t.topic_id, default) == mode]
        examples = ", ".join(html.escape(_short(name, 60)) for name in names[:3])
        if len(names) > 3:
            examples += f" и ещё {len(names) - 3}"
        lines.append(f"{label}: {len(names)}" + (f" — {examples}" if examples else ""))
    return lines


def _draft_screen(s: Session) -> tuple[str, Keyboard]:
    if s.prompt:
        text = ("Отправьте название или ID чата. /cancel — отменить." if s.prompt == "search" else
                "Отправьте код учебной группы, например B26-CSE-01; all — для всех. /cancel — отменить.")
        rows = [[_draft_button(s, "← Назад", "back", s.stage)]]
    else:
        text, rows = _draft_body(s)
        previous = {"mode": "topics", "reader": "topics", "review": "topics", "topics": "group"}.get(s.stage)
        if previous:
            rows.append([_draft_button(s, "← Назад", "back", previous)])
    if not any(b.callback_data == f"ls:d:{s.nonce}:cancel:" for row in rows for b in row):
        rows.append([_draft_button(s, "Отмена", "cancel")])
    return text, rows


def _draft_body(s: Session) -> tuple[str, Keyboard]:
    if s.stage == "pick":
        chosen = userbot_config.listened()
        found = [d for d in userbot_config.dialogs() if d.chat_id not in chosen
                 and (s.search.casefold() in d.title.casefold() or s.search in str(d.chat_id))]
        pages = max(1, (len(found) + PAGE_SIZE - 1) // PAGE_SIZE)
        s.page = max(0, min(s.page, pages - 1))
        rows = [[_draft_button(s, _short(d.title), "pick", d.chat_id)]
                for d in found[s.page * PAGE_SIZE:(s.page + 1) * PAGE_SIZE]]
        nav = []
        if s.page:
            nav.append(_draft_button(s, "◀", "page", s.page - 1))
        nav.append(_button(f"{s.page + 1}/{pages}", "ls:n"))
        if s.page < pages - 1:
            nav.append(_draft_button(s, "▶", "page", s.page + 1))
        rows.extend([nav, [_draft_button(s, "🔎 Найти по названию / ID", "search")]])
        return "<b>Добавить группу</b> — выберите чат" + ("\nНичего не найдено." if not found else ""), rows
    dialog = userbot_config.dialog(s.chat_id)
    if dialog is None:
        return "Чат больше недоступен. Вернитесь к списку групп.", []
    title = html.escape(dialog.title) if dialog else str(s.chat_id)
    forum = bool(dialog and dialog.forum and not dialog.bot_only)
    scope = "Остальные и новые" if forum else "Весь чат"
    if s.stage in ("clear", "disable"):
        text = (_clear_screen(s.chat_id)[0] if s.stage == "clear" else
                f"Отключить группу «{title}»? Сохранённые сообщения останутся в базе.")
        label = "✅ Да, удалить" if s.stage == "clear" else "Да, отключить"
        return text, [[_draft_button(s, label, s.stage)], [_draft_button(s, "Отмена", "cancel")]]
    if s.stage == "group":
        pages = max(1, (len(s.codes) + PAGE_SIZE - 1) // PAGE_SIZE)
        s.page = max(0, min(s.page, pages - 1))
        nav = []
        if s.page:
            nav.append(_draft_button(s, "◀", "page", s.page - 1))
        nav.append(_button(f"{s.page + 1}/{pages}", "ls:n"))
        if s.page < pages - 1:
            nav.append(_draft_button(s, "▶", "page", s.page + 1))
        return f"<b>{title}</b>\nУчебная группа: {html.escape(s.group)}", [
            *[[_draft_button(s, code, "group", i)] for i, code in enumerate(s.codes)
              if s.page * PAGE_SIZE <= i < (s.page + 1) * PAGE_SIZE], nav,
            [_draft_button(s, "🎓 Другая группа…", "custom")],
            [_draft_button(s, "Отмена", "cancel")],
        ]
    if s.stage == "reader":
        options = [("auto", "Авто")]
        if dialog and not dialog.bot_only:
            options.append(("userbot", "userbot"))
        if dialog and (dialog.bot_in or dialog.bot_only):
            options.append(("bot", "🤖 бот"))
        return f"<b>{title}</b>\nКто читает сообщения для хранения:", [
            [_draft_button(s, label, "reader", code)] for code, label in options]
    if s.stage == "mode":
        return f"<b>{title}</b>\nРежим топика:", [
            [_draft_button(s, label, "mode", mode)] for mode, label in MODES.items()
            if mode != "search" or not (dialog and dialog.bot_only)
        ]
    if s.stage == "review":
        lines = [f"<b>Проверка: {title}</b>", f"Учебная группа: {html.escape(s.group)}",
                 f"{scope}: {MODES[s.default]}",
                 *(_topic_summary(s.chat_id, s.default, s.topics) if forum else []),
                 f"Читает: {s.reader}", HISTORY_NOTE]
        return "\n".join(lines), [[_draft_button(s, "✅ Подтвердить", "save")],
                                  [_draft_button(s, "Отмена", "cancel")]]
    if not forum:
        text = f"<b>{title}</b>\nВесь чат: {MODES[s.default]}"
        if dialog and dialog.bot_only:
            text += "\nТолько бот: поиск Telegram недоступен. Можно хранить новые сообщения; истории нет."
        return text, [[_draft_button(s, "Весь чат — выбрать режим", "default")],
                      [_draft_button(s, "Проверить →", "review")]]
    found = _topics(s.chat_id)
    pages = max(1, (len(found) + PAGE_SIZE - 1) // PAGE_SIZE)
    s.page = max(0, min(s.page, pages - 1))
    rows = [[_draft_button(s, "Остальные и новые", "default")]]
    rows.extend([_draft_button(s, f"{_short(t.title)} · {MODES[s.topics.get(t.topic_id, s.default)]}", "topic", t.topic_id)]
                for t in found[s.page * PAGE_SIZE:(s.page + 1) * PAGE_SIZE])
    nav = []
    if s.page:
        nav.append(_draft_button(s, "◀", "page", s.page - 1))
    nav.append(_button(f"{s.page + 1}/{pages}", "ls:n"))
    if s.page < pages - 1:
        nav.append(_draft_button(s, "▶", "page", s.page + 1))
    rows.append(nav)
    rows.append([_draft_button(s, "Проверить →", "review")])
    return f"<b>{title}</b>\nОстальные и новые: {MODES[s.default]}", rows


async def _draft_callback(query: CallbackQuery, args: list[str]) -> None:
    user_id = query.from_user.id
    s = SESSIONS.get(user_id)
    if (s is None or len(args) != 3 or s.nonce != args[0]
            or not query.message or s.private_chat != query.message.chat.id):
        await query.answer("Этот экран устарел. Откройте настройки заново.", show_alert=True)
        return
    _, rows = await asyncio.to_thread(_draft_screen, s)
    if (query.data not in {b.callback_data for row in rows for b in row}
            or SESSIONS.get(user_id) is not s or s.nonce != args[0]):
        await query.answer("Недопустимая или устаревшая кнопка", show_alert=True)
        return
    # Claim this screen before awaiting I/O: a repeated confirmation cannot write twice.
    s.nonce = secrets.token_hex(4)
    s.prompt = ""
    action, value = args[1], args[2]
    if action == "cancel":
        SESSIONS.pop(user_id, None)
        await query.answer("Отменено")
        await _show(query, await asyncio.to_thread(_list_screen, user_id))
        return
    if action in ("clear", "disable") and s.stage == action:
        del SESSIONS[user_id]
        if action == "clear":
            deleted = await asyncio.to_thread(store.clear_chat, s.chat_id)
            remaining, _ = await asyncio.to_thread(store.chat_message_counts, s.chat_id)
            notice = f"Удалено сообщений: {deleted}" if not remaining else "Не удалось подтвердить очистку: в базе есть сообщения."
        else:
            await asyncio.to_thread(userbot_config.set_listen, s.chat_id, False)
            chosen = await asyncio.to_thread(userbot_config.listened)
            notice = ("Группа отключена. Сохранённые сообщения остаются." if s.chat_id not in chosen else
                      "Не удалось подтвердить отключение группы.")
        await query.answer(notice)
        await _show(query, await asyncio.to_thread(_advanced_screen, s.chat_id))
        return
    if action == "pick":
        s.chat_id = int(value)
        dialog = await asyncio.to_thread(userbot_config.dialog, s.chat_id)
        s.default = "off" if dialog and dialog.bot_only else "search"
        s.codes = await asyncio.to_thread(_known_groups)
        s.page = 0
        s.stage = "group"
    elif action in ("search", "custom"):
        s.prompt = action
        await query.answer()
        await _show(query, await asyncio.to_thread(_draft_screen, s))
        return
    elif action == "group":
        s.group = s.codes[int(value)]
        s.page = 0
        s.stage = "topics"
    elif action == "back":
        s.stage = value
        if value == "group":
            s.page = 0
    elif action == "page":
        s.page = int(value)
    elif action == "default":
        s.target_topic = 0
        s.stage = "mode"
    elif action == "topic":
        s.target_topic = int(value)
        s.stage = "mode"
    elif action == "mode":
        if s.target_topic:
            s.topics[s.target_topic] = value
        else:
            s.default = value
        s.stage = "topics"
    elif action == "reader":
        s.reader = value
        s.stage = "topics"
    elif action == "review":
        s.stage = "review"
    elif action == "save" and s.stage == "review":
        del SESSIONS[user_id]
        try:
            await asyncio.to_thread(userbot_config.save_configuration, s.chat_id, s.group, s.default, s.topics, s.reader)
            policy = await asyncio.to_thread(userbot_config.get_policy, s.chat_id)
            group = await asyncio.to_thread(_group_of, s.chat_id)
            readers = await asyncio.to_thread(userbot_config.readers)
            expected = {tid: mode for tid, mode in s.topics.items() if mode != s.default}
            actual = {tid: mode for tid, mode in policy["topics"].items() if mode != policy["default"]}
            verified = (policy["default"] == s.default and actual == expected
                        and group == s.group and readers.get(s.chat_id) == s.reader)
        except ValueError:
            await query.answer("Не удалось сохранить: чат или настройки изменились. Откройте их заново.", show_alert=True)
            return
        except Exception:
            log.exception("configuration save/readback failed for chat %s", s.chat_id)
            await query.answer("Не удалось подтвердить сохранение. Проверьте настройки перед повтором.", show_alert=True)
            return
        if verified:
            await query.answer("Сохранено")
        else:
            await query.answer("Не удалось подтвердить сохранение. Проверьте настройки.", show_alert=True)
        await _show(query, await asyncio.to_thread(_list_screen, user_id))
        return
    s.nonce = secrets.token_hex(4)
    await query.answer()
    await _show(query, await asyncio.to_thread(_draft_screen, s))


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
    chosen = userbot_config.listened()
    dialogs = [d for d in userbot_config.dialogs() if d.chat_id in chosen]
    pages = max(1, (len(dialogs) - 1) // PAGE_SIZE + 1)
    page = min(PAGE.get(user_id, 0), pages - 1)
    PAGE[user_id] = page
    shown = dialogs[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]
    codes = _groups_of([d.chat_id for d in shown])
    official_flags = official.flags([d.chat_id for d in shown])
    readers = userbot_config.readers()
    rows: Keyboard = []
    for d in shown:
        code = codes.get(d.chat_id, groups.ALL)
        label = f"{'✅' if d.chat_id in chosen else '⬜'} {_short(d.title)}{' 🧵' if d.forum else ''}{' 🤖' if d.bot_in else ''}{' 🔎' if readers.get(d.chat_id) == 'search' else ''}{' 🏛' if official_flags.get(d.chat_id) else ''}{'' if code == groups.ALL else ' · ' + code}"
        rows.append([_button(label, f"ls:c:{d.chat_id}")])
    nav = []
    if page > 0:
        nav.append(_button("◀", f"ls:l:{page - 1}"))
    nav.append(_button(f"{page + 1}/{pages}", "ls:n"))
    if page < pages - 1:
        nav.append(_button("▶", f"ls:l:{page + 1}"))
    rows.append(nav)
    rows.append([_button("➕ Добавить группу", "ls:add")])
    rows.append([_button("🔄 Обновить список", "ls:r")])
    rows.append([_button("📥 Заявки на чаты", "sr:list:0")])
    rows.append([_button("← Администрирование", "adm:home")])
    text = (
        f"<b>Подключённые группы</b>: {len(dialogs)}.\n"
        "✅ — слушаю, 🧵 — форум с топиками, 🤖 — в чате есть бот, 🔎 — только поиск Telegram (не хранится), 🏛 — официальный чат, после · — учебная группа чата. "
        "Нажмите на чат, чтобы настроить."
    )
    return text, rows


def _reader_line(dialog: userbot_config.Dialog, choice: str) -> str:
    if choice == "search":
        return "Только поиск Telegram: сообщения не сохраняются, userbot ищет в чате по запросу пользователя"
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
    on = chat_id in userbot_config.listened()
    policy = userbot_config.get_policy(chat_id)
    forum = dialog.forum and not dialog.bot_only
    lines = [f"<b>{html.escape(dialog.title)}</b>", f"Подключена: {'да' if on else 'нет'}",
             f"Учебная группа: {html.escape(_group_of(chat_id))}",
             f"{'Остальные и новые' if forum else 'Весь чат'}: {MODES[policy['default']]}"]
    if forum:
        lines.extend(_topic_summary(chat_id, policy["default"], policy["topics"]))
    rows = [[_button("✏️ Изменить настройки" if on else "➕ Настроить подключение", f"ls:edit:{chat_id}")],
            [_button("⚙️ Дополнительно", f"ls:adv:{chat_id}")],
            [_button("← К списку", "ls:l:keep")]]
    return "\n".join(lines), rows


def _advanced_screen(chat_id: int) -> tuple[str, Keyboard]:
    dialog = userbot_config.dialog(chat_id)
    if dialog is None:
        return _chat_screen(chat_id)
    is_official = official.flags([chat_id]).get(chat_id, False)
    stored, _ = store.chat_message_counts(chat_id)
    lines = [f"<b>{html.escape(dialog.title)} — дополнительно</b>",
             _reader_line(dialog, userbot_config.readers().get(chat_id, "auto")),
             f"Официальный чат: {'да' if is_official else 'нет'} (только такие сообщения агент называет официальными)",
             f"Сообщений в базе: {stored}", HISTORY_NOTE]
    rows = [[_button("Кто читает — изменить", f"ls:reader:{chat_id}")],
            [_button("🏛 Снять отметку «официальный»" if is_official else "🏛 Сделать официальным", f"ls:of:{chat_id}")]]
    if stored:
        rows.append([_button(f"🗑 Очистить сообщения ({stored})", f"ls:cl:{chat_id}")])
    if chat_id in userbot_config.listened():
        rows.append([_button("🔕 Отключить группу", f"ls:o:{chat_id}")])
    rows.append([_button("← Назад", f"ls:c:{chat_id}")])
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
    return text.strip(), []  # Confirmation buttons are bound to the active draft nonce.


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
    cancel_pending(message.from_user.id)
    _cancel_admin_prompt(message.from_user.id)
    if not await _is_admin(message.from_user.id):
        await message.answer("Только для администратора.")
        return
    text, rows = await asyncio.to_thread(_list_screen, message.from_user.id)
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.message(F.chat.type == ChatType.PRIVATE, Command("cancel"))
async def cancel_command(message: Message) -> None:
    cancel_pending(message.from_user.id)
    _cancel_admin_prompt(message.from_user.id)
    if not await _is_admin(message.from_user.id):
        await message.answer("Только для администратора.")
        return
    await message.answer("Отменено. Несохранённые настройки отброшены.")


def _toggle_official(chat_id: int) -> str | None:
    """Switch the "official" mark of a chat of the list; the notice for the admin, or None if the chat is gone."""
    dialog = userbot_config.dialog(chat_id)
    if dialog is None:
        return None
    _ensure_chat(dialog)  # the chat row holds the mark and may not exist yet
    value = not official.flags([chat_id]).get(chat_id, False)
    official.set_official(chat_id, value)
    if official.flags([chat_id]).get(chat_id, False) != value:
        return "Не удалось подтвердить изменение отметки."
    return "Чат отмечен официальным: его сообщения можно называть официальными" if value else "Отметка «официальный» снята"


@router.callback_query(F.data.startswith("ls:"))
async def listen_callback(query: CallbackQuery) -> None:
    user_id = query.from_user.id
    _cancel_admin_prompt(user_id)
    if not query.message or query.message.chat.type != ChatType.PRIVATE or not await _is_admin(user_id):
        await query.answer("Только для администратора в личном чате", show_alert=True)
        return
    parts = (query.data or "").split(":")
    if len(parts) < 2:
        await query.answer("Недопустимая кнопка", show_alert=True)
        return
    _, action, *args = parts
    if action not in ("d", "n"):
        cancel_pending(user_id)
    chat_actions = {"c", "edit", "reader", "adv", "o", "cl", "of"}
    if action in chat_actions or action == "l":
        if (len(args) != 1 or not (re.fullmatch(r"-?[0-9]{1,19}", args[0]) or action == "l" and args[0] == "keep")):
            await query.answer("Недопустимая кнопка", show_alert=True)
            return
        if action in chat_actions and not await asyncio.to_thread(userbot_config.dialog, int(args[0])):
            await query.answer("Чат больше недоступен", show_alert=True)
            return
    notice = None
    match action:
        case "add":
            s = Session(private_chat=query.message.chat.id)
            SESSIONS[user_id] = s
            screen = await asyncio.to_thread(_draft_screen, s)
        case "d":
            await _draft_callback(query, args)
            return
        case "edit" | "reader":
            chat_id = int(args[0])
            policy = await asyncio.to_thread(userbot_config.get_policy, chat_id)
            dialog = await asyncio.to_thread(userbot_config.dialog, chat_id)
            if dialog and dialog.bot_only and chat_id not in await asyncio.to_thread(userbot_config.listened):
                policy = {"default": "off", "topics": {}}
            s = Session(private_chat=query.message.chat.id, chat_id=chat_id, stage="reader" if action == "reader" else "group",
                        group=await asyncio.to_thread(_group_of, chat_id), default=policy["default"],
                        topics=dict(policy["topics"]), codes=await asyncio.to_thread(_known_groups),
                        reader=(await asyncio.to_thread(userbot_config.readers)).get(chat_id, "auto"))
            if s.reader == "search":
                s.reader = "auto"
            SESSIONS[user_id] = s
            screen = await asyncio.to_thread(_draft_screen, s)
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
        case "adv":
            screen = await asyncio.to_thread(_advanced_screen, int(args[0]))
        case "o" | "cl":
            chat_id = int(args[0])
            if action == "o" and chat_id not in await asyncio.to_thread(userbot_config.listened):
                await query.answer("Сначала настройте подключение группы", show_alert=True)
                return
            s = Session(private_chat=query.message.chat.id, chat_id=chat_id,
                        stage="disable" if action == "o" else "clear")
            SESSIONS[user_id] = s
            screen = await asyncio.to_thread(_draft_screen, s)
        case "of":
            chat_id = int(args[0])
            notice = await asyncio.to_thread(_toggle_official, chat_id)
            screen = await asyncio.to_thread(_advanced_screen, chat_id)
        case _:
            await query.answer()
            return
    await query.answer(notice)
    await _show(query, screen)


def _waiting_for_group(message: Message) -> bool:
    if message.from_user and (message.text or "").startswith("/"):
        cancel_pending(message.from_user.id)
        return False
    return bool(message.from_user and message.text and not message.text.startswith("/")
                and (message.from_user.id in PENDING_GROUP
                     or (message.from_user.id in SESSIONS and SESSIONS[message.from_user.id].prompt)))


@router.message(F.chat.type == ChatType.PRIVATE, F.text, _waiting_for_group)
async def group_code(message: Message) -> None:
    if not message.from_user:
        return
    user_id = message.from_user.id
    if message.chat.type != ChatType.PRIVATE or not await _is_admin(user_id):
        cancel_pending(user_id)
        await message.answer("Только для администратора в личном чате.")
        return
    s = SESSIONS.get(user_id)
    if not s or s.private_chat != message.chat.id or not s.prompt:
        await message.answer("Этот экран устарел. Откройте настройки заново.")
        return
    if not message.text or message.text.startswith("/"):
        cancel_pending(user_id)
        return
    if s.prompt:
        if s.prompt == "search":
            s.search = message.text.strip()
        else:
            code = groups.normalize(message.text)
            if code is None:
                await message.answer("Код группы: латиница, цифры, точка, дефис или подчёркивание, до 40 символов.")
                return
            s.group = code
            s.stage = "topics"
        s.prompt = ""
        s.page = 0
        s.nonce = secrets.token_hex(4)
        text, rows = await asyncio.to_thread(_draft_screen, s)
        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
        return
