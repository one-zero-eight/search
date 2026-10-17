"""Which chats an answer may quote, depending on who asks and where (only when RESTRICT_CHAT_ACCESS is on).

- In a group, the answer is seen by everyone there: only public chats and that group itself.
- In a private chat: public chats plus chats the user is a member of. Membership comes from the
  cache (message senders, userbot participant lists) and, for chats the bot is in, from getChatMember.
- Private chats whose membership cannot be verified are hidden.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.exceptions import TelegramAPIError

from catix.db import store
from catix.settings import settings

log = logging.getLogger("catix.access")

# A "yes" is trusted longer than a "no": people rarely leave, while a fresh join should show up soon.
MEMBER_TTL = timedelta(days=7)
NOT_MEMBER_TTL = timedelta(hours=1)
MEMBER_STATUSES = {ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER}


async def _bot_says_member(bot: Bot, chat_id: int, user_id: int) -> bool | None:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
    except TelegramAPIError as e:
        # The bot was removed, or the chat migrated to a supergroup: membership unknown.
        log.warning("getChatMember(%s, %s) failed: %s", chat_id, user_id, e)
        return None
    # "restricted" users can still be members (e.g. muted ones).
    return member.status in MEMBER_STATUSES or getattr(member, "is_member", False)


async def visible_chats(bot: Bot, user_id: int, chat_id: int, chat_type: ChatType) -> set[int] | None:
    """Chats an answer may quote; None means all of them (RESTRICT_CHAT_ACCESS is off)."""
    if not settings.restrict_chat_access:
        return None
    return await allowed_chat_ids(bot, user_id, chat_id, chat_type)


async def allowed_chat_ids(bot: Bot, user_id: int, chat_id: int, chat_type: ChatType) -> set[int]:
    allowed = await asyncio.to_thread(store.public_chat_ids)
    if chat_type != ChatType.PRIVATE:
        return allowed | {chat_id}

    now = datetime.now().astimezone()
    to_check = set(await asyncio.to_thread(store.bot_chat_ids)) - allowed
    for cid, (is_member, checked_at) in (await asyncio.to_thread(store.membership, user_id)).items():
        if now - checked_at < (MEMBER_TTL if is_member else NOT_MEMBER_TTL):
            to_check.discard(cid)
            if is_member:
                allowed.add(cid)

    if to_check:
        checks = dict(zip(to_check, await asyncio.gather(*(_bot_says_member(bot, cid, user_id) for cid in to_check))))
        await asyncio.to_thread(store.set_members, {(cid, user_id) for cid, ok in checks.items() if ok}, True)
        await asyncio.to_thread(store.set_members, {(cid, user_id) for cid, ok in checks.items() if ok is False}, False)
        for cid in (cid for cid, ok in checks.items() if ok is None):
            # Stop asking until the bot sees a message there again.
            await asyncio.to_thread(store.unmark_bot_chat, cid)
        allowed |= {cid for cid, ok in checks.items() if ok}
    return allowed
