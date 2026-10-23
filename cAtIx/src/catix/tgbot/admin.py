"""Admins of the bot in the bot: /admin.

An admin sees who the admins are, adds another one (by Telegram id, or by forwarding a message of that person) and
removes the ones that were added here. The admins from ADMIN_TELEGRAM_IDS are fixed. Only in a private chat with the bot.
"""

import asyncio
import html
import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatType, ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import (
    BotCommandScopeChat,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    MessageOriginUser,
)

from catix import admins

log = logging.getLogger("catix.admin")
router = Router()

PENDING: set[int] = set()  # Admins who pressed "add" and are about to send an id.


async def _is_admin(user_id: int) -> bool:
    return user_id in await asyncio.to_thread(admins.everyone)


async def _name(bot: Bot, user_id: int) -> str:
    """A person's name for the list; Telegram tells it only for people who have talked to the bot."""
    try:
        chat = await bot.get_chat(user_id)
    except TelegramAPIError:
        return str(user_id)
    return f"{chat.full_name} (@{chat.username})" if chat.username else chat.full_name


async def _screen(bot: Bot) -> tuple[str, InlineKeyboardMarkup]:
    fixed, added = await asyncio.to_thread(admins.configured), await asyncio.to_thread(admins.added)
    lines = ["<b>Администраторы бота</b>"]
    for user_id in fixed:
        lines.append(f"• {html.escape(await _name(bot, user_id))}: <code>{user_id}</code> (из настроек, не удаляется)")
    rows = []
    for user_id in added:
        name = await _name(bot, user_id)
        lines.append(f"• {html.escape(name)}: <code>{user_id}</code>")
        rows.append([InlineKeyboardButton(text=f"❌ Убрать {name[:28]}", callback_data=f"adm:rm:{user_id}")])
    rows.append([InlineKeyboardButton(text="➕ Добавить администратора", callback_data="adm:add")])
    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=rows)


async def _menu(bot: Bot, user_id: int, *, admin: bool) -> None:
    """Add /admin (and /listen, which every admin has) to the person's command menu, or give the plain menu back."""
    from catix.tgbot import bot as main  # Imported late: bot.py imports this module.

    scope = BotCommandScopeChat(chat_id=user_id)
    try:
        if admin:
            await bot.set_my_commands([*main.ADMIN_COMMANDS], scope=scope)
        else:
            await bot.delete_my_commands(scope=scope)
    except TelegramAPIError as e:
        log.info("menu of %s not changed (they have not started the bot yet?): %s", user_id, e)


@router.message(F.chat.type == ChatType.PRIVATE, Command("admin"))
async def admin_command(message: Message, bot: Bot) -> None:
    if not await _is_admin(message.from_user.id):
        await message.answer("Только для администратора.")
        return
    PENDING.discard(message.from_user.id)
    text, keyboard = await _screen(bot)
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)


@router.callback_query(F.data.startswith("adm:"))
async def admin_callback(query: CallbackQuery, bot: Bot) -> None:
    user_id = query.from_user.id
    if not await _is_admin(user_id):
        await query.answer("Только для администратора", show_alert=True)
        return
    _, action, *args = query.data.split(":")
    notice = None
    if action == "add":
        PENDING.add(user_id)
        await query.answer()
        await query.message.answer(
            "Пришлите Telegram id нового администратора (число) или перешлите мне любое его сообщение. "
            "Узнать свой id можно у @userinfobot. Другая команда отменит ввод."
        )
        return
    if action == "rm":
        target = int(args[0])
        if target == user_id:
            notice = "Себя убрать нельзя"
        elif await asyncio.to_thread(admins.remove, target):
            await _menu(bot, target, admin=False)
            notice = "Убран"
        else:
            notice = "Его нет среди добавленных"
    await query.answer(notice)
    text, keyboard = await _screen(bot)
    try:
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
    except TelegramBadRequest as e:
        if "not modified" not in str(e):
            raise


def _waiting_for_id(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id in PENDING and not (message.text or "").startswith("/"))


@router.message(F.chat.type == ChatType.PRIVATE, _waiting_for_id)
async def new_admin(message: Message, bot: Bot) -> None:
    if isinstance(message.forward_origin, MessageOriginUser):
        target = message.forward_origin.sender_user.id
    elif message.text and message.text.strip().isdigit():
        target = int(message.text.strip())
    else:
        await message.answer(
            "Не получилось понять. Пришлите число (Telegram id) или перешлите сообщение этого человека. "
            "Если у него скрыта пересылка, нужен id."
        )
        return
    PENDING.discard(message.from_user.id)
    if await asyncio.to_thread(admins.add, target, message.from_user.id):
        await _menu(bot, target, admin=True)
        log.info("admin %s added by %s", target, message.from_user.id)
        reply = f"Добавлен администратор <code>{target}</code>. Пусть он напишет боту /start: иначе я не смогу присылать ему карточки."
    else:
        reply = f"<code>{target}</code> уже администратор."
    text, keyboard = await _screen(bot)
    await message.answer(f"{reply}\n\n{text}", parse_mode=ParseMode.HTML, reply_markup=keyboard)
