"""/abuse: an admin sees who keeps attacking the bot, reads the stopped messages and lifts a pause (see catix/abuse.py).
Only in a private chat with the bot; plain text, because the previews are what the attackers wrote."""

import asyncio

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from catix import abuse, admins

router = Router()


@router.message(F.chat.type == ChatType.PRIVATE, Command("abuse"))
async def abuse_command(message: Message, command: CommandObject) -> None:
    if not message.from_user or message.from_user.id not in await asyncio.to_thread(admins.everyone):
        await message.answer("Только для администраторов.")
        return
    await message.answer(await asyncio.to_thread(abuse.command, command.args or ""), parse_mode=None)
