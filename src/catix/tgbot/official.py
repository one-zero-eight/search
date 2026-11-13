"""/official: an admin marks chats as official (see catix/official.py). Only in a private chat with the bot."""

import asyncio

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from catix import admins, official

router = Router()


@router.message(F.chat.type == ChatType.PRIVATE, Command("official"))
async def official_command(message: Message, command: CommandObject) -> None:
    if not message.from_user or message.from_user.id not in await asyncio.to_thread(admins.everyone):
        await message.answer("Только для администраторов.")
        return
    await message.answer(await asyncio.to_thread(official.command, command.args or ""))
