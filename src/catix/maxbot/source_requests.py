"""Resolve moderated MAX proposals against chats the administrator added the bot to."""
import asyncio
import logging

import httpx

from catix import groups, source_requests as queue
from catix.db import pg
from catix.maxbot import state

log = logging.getLogger(__name__)


def _chat_ids() -> list[int]:
    with pg.connection() as conn:
        return pg.column(conn, """SELECT raw_chat_id FROM max_sources UNION
                         SELECT chat_id - %s FROM chats WHERE chat_id >= %s""",
                         (groups.MAX_CHAT_BASE, 10**15))


def observe(chat: dict) -> bool:
    """Discover membership, blocking proposed content until its approved activation."""
    try:
        link = queue.normalize_link(chat.get("link"))
    except ValueError:
        link = None
    with pg.connection() as conn:
        source = state._discover(conn, chat["chat_id"], chat["type"])
        requests = conn.execute("""SELECT status, chat_id FROM source_requests
                                   WHERE invite_link = %s OR chat_id = %s""", (link, source["chat_id"])).fetchall()
        return not requests or (source["enabled"] and source["access"] == "ready"
                                and any(row["status"] == "connected" and row["chat_id"] == source["chat_id"]
                                        for row in requests))


async def process_one(client) -> bool:
    job = await asyncio.to_thread(queue.claim, "max")
    if job is None:
        return False
    try:
        for chat_id in await asyncio.to_thread(_chat_ids):
            try:
                chat = await client.call("GET", f"/chats/{chat_id}")
                link = queue.normalize_link(chat.get("link"))
            except ValueError:
                continue
            except httpx.HTTPStatusError as error:
                if error.response.status_code in {403, 404}:
                    continue
                raise
            if link != job["invite_link"]:
                continue
            membership = await client.call("GET", f"/chats/{chat_id}/members/me")
            if await asyncio.to_thread(queue.activate_max, job, chat, membership):
                return True
            current = await asyncio.to_thread(queue.get_request, job["id"])
            if current and current["status"] == "failed":
                return True
            break
        await asyncio.to_thread(queue.defer, job,
                                "Ask the MAX chat administrator to add the cAtIx bot as an administrator with read access. Membership will be checked again.")
    except Exception:  # Never expose invitations, tokens or upstream response payloads.
        await asyncio.to_thread(queue.defer, job, "MAX access could not be confirmed. Verification will be retried.")
    return True


async def run(client, load_history) -> None:
    while True:
        try:
            await asyncio.wait_for(process_one(client), timeout=90)
            for chat_id in await asyncio.to_thread(queue.backfill_pending, "max"):
                if await load_history(client, chat_id - groups.MAX_CHAT_BASE):
                    await asyncio.to_thread(queue.backfill_done, chat_id)
        except Exception:
            log.warning("MAX source request worker unavailable; retrying.")
        await asyncio.sleep(5)
