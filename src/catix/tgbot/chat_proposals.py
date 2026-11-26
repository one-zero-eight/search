"""Private Telegram admin list of the chats proposed to catix: the links Moodle courses point to (proposed_chats, filled by
moodle_chats.py when a course is synced). Read-only, straight from Postgres: nothing here joins or approves a chat."""

import asyncio
import html
import logging

from aiogram import F, Router
from aiogram.enums import ChatType, ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from catix import admins
from catix.db import pg

log = logging.getLogger("catix.chat_proposals")
router = Router()
PAGE_SIZE = 8
COURSE_TITLE = 60


def screen(page: int) -> tuple[str, InlineKeyboardMarkup]:
    with pg.connection() as conn:
        total = pg.scalar(conn, "SELECT count(*) FROM proposed_chats") or 0
        page = min(max(page, 0), max((total - 1) // PAGE_SIZE, 0))
        rows = conn.execute("SELECT p.link, p.owner, p.course, p.found_at, coalesce(a.study_groups, '{}') AS study_groups "
                            "FROM proposed_chats p LEFT JOIN moodle_accounts a ON a.innohassle_id = p.owner ORDER BY p.found_at DESC, p.link "
                            "OFFSET %s LIMIT %s", (page * PAGE_SIZE, PAGE_SIZE)).fetchall()
    lines = [f"<b>Заявки на чаты</b> · {total}",
             "Ссылки на чаты из курсов Moodle пользователей. Список только для просмотра: к чатам ничего не подключается."]
    for row in rows:
        course = row["course"] if len(row["course"]) <= COURSE_TITLE else row["course"][:COURSE_TITLE - 1] + "…"
        study_groups = ", ".join(row["study_groups"]) or "группа не указана"
        lines.append(f"\n<code>{html.escape(row['link'])}</code>\n{html.escape(study_groups)}\n"
                     f"{html.escape(course or 'курс не указан')} · "
                     f"{row['found_at']:%Y-%m-%d} · <code>{html.escape(row['owner'])}</code>")
    if not rows:
        lines.append("\nПока ни одной ссылки.")
    else:
        lines.append(f"\nСтраница {page + 1}/{(total - 1) // PAGE_SIZE + 1}")
    nav = []
    if page:
        nav.append(InlineKeyboardButton(text="←", callback_data=f"sr:list:{page - 1}"))
    if (page + 1) * PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(text="→", callback_data=f"sr:list:{page + 1}"))
    keyboard = [nav] if nav else []
    keyboard.append([InlineKeyboardButton(text="← Группы и источники", callback_data="ls:l:keep")])
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.callback_query(F.data.startswith("sr:list:"))
async def proposals_callback(query: CallbackQuery) -> None:
    arg = (query.data or "").split(":")[2]
    if not isinstance(query.message, Message) or query.message.chat.type != ChatType.PRIVATE or query.from_user.id not in await asyncio.to_thread(admins.everyone):
        await query.answer("Только для администратора в личном чате", show_alert=True)
        return
    if not (arg.isascii() and arg.isdigit() and len(arg) <= 9):
        await query.answer("Недопустимая кнопка", show_alert=True)
        return
    text, markup = await asyncio.to_thread(screen, int(arg))
    try:
        await query.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
    await query.answer()
