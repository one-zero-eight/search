"""Private admin moderation of proposed Telegram sources, linked from /listen."""

import asyncio
import html
import re

from aiogram import F, Router
from aiogram.enums import ChatType, ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InaccessibleMessage, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions, Message

from catix import groups
from catix import source_requests as store
from catix.worker import changes

Keyboard = list[list[InlineKeyboardButton]]
router = Router()
REQUEST_ID = re.compile(r"[0-9a-f]{32}")
PAGE_SIZE = 8
STATUS = {
    "pending": "На рассмотрении", "approved": "Заявка одобрена; ожидает userbot",
    "joining": "Подключается", "waiting_join": "Ожидает вступления в Telegram",
    "connected": "Источник подключён; история может ещё загружаться",
    "failed": "Не удалось подключить", "rejected": "Отклонена",
}


def _button(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def list_screen(page: int) -> tuple[str, Keyboard]:
    found = store.pending_requests(offset=page * PAGE_SIZE, limit=PAGE_SIZE + 1)
    rows = [[_button(f"{'Все пользователи cAtIx' if r['group_code'] == groups.ALL else r['group_code']} · {r['email'][:40]}", f"sr:show:{r['id']}")] for r in found[:PAGE_SIZE]]
    nav = []
    if page:
        nav.append(_button("◀", f"sr:list:{page - 1}"))
    nav.append(_button("Обновить", f"sr:list:{page}"))
    if len(found) > PAGE_SIZE:
        nav.append(_button("▶", f"sr:list:{page + 1}"))
    rows.extend([nav, [_button("← Чаты", "ls:l:keep")]])
    text = "<b>Заявки на Telegram-чаты</b>\n" + ("Выберите заявку для проверки." if found else "На этой странице заявок нет.")
    return text, rows


def request_screen(request: dict) -> tuple[str, Keyboard]:
    request_id = request["id"]
    group = "все пользователи cAtIx" if request["group_code"] == groups.ALL else html.escape(request["group_code"])
    visibility = (
        "Сообщения увидят все пользователи cAtIx, не только участники чата."
        if request["group_code"] == groups.ALL else
        "Сообщения увидят все пользователи с подтверждённой принадлежностью к этой учебной группе, не только участники чата."
    )
    text = (
        f"<b>Заявка на Telegram-чат</b>\n"
        f"От: {html.escape(request['email'])}\n"
        f"Ссылка: {html.escape(request['invite_link'])}\n"
        f"Аудитория: <b>{group}</b>\n"
        f"Статус: {STATUS[request['status']]}\n"
        f"Комментарий: {html.escape(request['comment'][:1000]) or '—'}{'…' if len(request['comment']) > 1000 else ''}\n\n"
        "Отправитель подтвердил согласие администратора Telegram-чата. "
        f"Перед подключением проверьте это согласие и целевую аудиторию. {visibility}"
    )
    if request.get("message"):
        text += "\n\n" + html.escape(request["message"])
    rows: Keyboard = []
    if request["status"] == "pending":
        rows.append([_button("Проверить и подключить…", f"sr:review:{request_id}")])
        rows.append([_button("Отклонить…", f"sr:reject:{request_id}")])
        text += (
            "\n\nДругая группа (команда сразу одобряет; сначала проверьте согласие):\n"
            f"<code>/source_approve {request_id} КОД_ГРУППЫ</code>\n"
            "all допустимо только для заявки, изначально поданной для всех пользователей cAtIx.\n"
            "Отклонить с причиной:\n"
            f"<code>/source_reject {request_id} причина</code>"
        )
    else:
        rows.append([_button("Обновить статус", f"sr:show:{request_id}")])
    rows.append([_button("← Заявки", "sr:list:0")])
    return text, rows


def review_screen(request: dict) -> tuple[str, Keyboard]:
    if request["status"] != "pending":
        return request_screen(request)
    request_id = request["id"]
    text, _ = request_screen(request)
    audience = "всех пользователей cAtIx" if request["group_code"] == groups.ALL else f"группы <b>{html.escape(request['group_code'])}</b>"
    text += (
        "\n\nПодтверждая, вы проверили согласие администратора Telegram-чата и разрешаете "
        f"вступление userbot и поиск для {audience}."
    )
    return text, [
        [_button("Согласие проверено — подключить", f"sr:approve:{request_id}")],
        [_button("← Назад", f"sr:show:{request_id}")],
    ]


async def _authorized(message, user_id: int) -> bool:
    return bool(message and not isinstance(message, InaccessibleMessage)
                and message.chat.type == ChatType.PRIVATE and user_id in await asyncio.to_thread(changes.admins))


async def _show(query: CallbackQuery, screen: tuple[str, Keyboard]) -> None:
    if query.message is None or isinstance(query.message, InaccessibleMessage):
        return
    text, rows = screen
    try:
        await query.message.edit_text(
            text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error).lower():
            raise


@router.callback_query(F.data.startswith("sr:"))
async def request_callback(query: CallbackQuery) -> None:
    if not await _authorized(query.message, query.from_user.id):
        await query.answer("Только для администратора в личном чате", show_alert=True)
        return
    parts = (query.data or "").split(":")
    if len(parts) == 3 and parts[1] == "list" and re.fullmatch(r"[0-9]{1,6}", parts[2]):
        await query.answer()
        await _show(query, await asyncio.to_thread(list_screen, int(parts[2])))
        return
    if len(parts) != 3 or not REQUEST_ID.fullmatch(parts[2]):
        await query.answer("Некорректная заявка", show_alert=True)
        return
    _, action, request_id = parts
    if action not in {"show", "review", "approve", "reject"}:
        await query.answer("Неизвестное действие", show_alert=True)
        return
    request = await asyncio.to_thread(store.get_request, request_id)
    if request is None:
        await query.answer("Заявка не найдена", show_alert=True)
        return
    if action == "reject" and request["status"] == "pending":
        await query.answer()
        await _show(query, (
            "Чтобы отклонить заявку, отправьте команду с причиной. Она будет видна отправителю:\n"
            f"<code>/source_reject {request_id} причина</code>",
            [[_button("← Назад", f"sr:show:{request_id}")]],
        ))
        return
    if action == "approve" and request["status"] == "pending":
        await asyncio.to_thread(store.approve, request_id, query.from_user.id, request["group_code"])
        request = await asyncio.to_thread(store.get_request, request_id)
        if request is None:
            await query.answer("Заявка больше не найдена", show_alert=True)
            return
    await query.answer()
    await _show(query, review_screen(request) if action == "review" else request_screen(request))


async def _answer(message: Message, screen: tuple[str, Keyboard]) -> None:
    text, rows = screen
    await message.answer(
        text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )


@router.message(F.chat.type == ChatType.PRIVATE, Command("requests"))
async def requests_command(message: Message) -> None:
    if not message.from_user or not await _authorized(message, message.from_user.id):
        await message.answer("Только для администратора в личном чате.")
        return
    await _answer(message, await asyncio.to_thread(list_screen, 0))


@router.message(F.chat.type == ChatType.PRIVATE, Command("source_approve"))
async def approve_command(message: Message) -> None:
    if not message.from_user or not await _authorized(message, message.from_user.id):
        await message.answer("Только для администратора в личном чате.")
        return
    parts = (message.text or "").split()
    code = groups.normalize(parts[2]) if len(parts) == 3 else None
    if not code or not REQUEST_ID.fullmatch(parts[1]):
        await message.answer("Формат: /source_approve ID КОД_ГРУППЫ (или all для общей заявки). Сначала проверьте согласие администратора чата на эту аудиторию.")
        return
    try:
        await asyncio.to_thread(store.approve, parts[1], message.from_user.id, code)
    except ValueError:
        await message.answer("Нельзя сделать групповую заявку общей: нужна новая заявка с согласием на доступ всех пользователей cAtIx и новой ссылкой-приглашением.")
        return
    request = await asyncio.to_thread(store.get_request, parts[1])
    if request is None:
        await message.answer("Заявка не найдена.")
        return
    await _answer(message, request_screen(request))


@router.message(F.chat.type == ChatType.PRIVATE, Command("source_reject"))
async def reject_command(message: Message) -> None:
    if not message.from_user or not await _authorized(message, message.from_user.id):
        await message.answer("Только для администратора в личном чате.")
        return
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) != 3 or not REQUEST_ID.fullmatch(parts[1]) or not 1 <= len(parts[2]) <= 500:
        await message.answer("Формат: /source_reject ID причина (до 500 символов).")
        return
    await asyncio.to_thread(store.reject, parts[1], message.from_user.id, parts[2])
    request = await asyncio.to_thread(store.get_request, parts[1])
    if request is None:
        await message.answer("Заявка не найдена.")
        return
    await _answer(message, request_screen(request))
