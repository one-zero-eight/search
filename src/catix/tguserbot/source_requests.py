"""Approved-only Telegram writes with durable intent and membership reconciliation."""
import asyncio
import logging

from telethon import errors, utils
from telethon.tl.functions.messages import CheckChatInviteRequest, ImportChatInviteRequest
from telethon.tl.types import Channel, Chat, ChatInviteAlready

from catix import source_requests as queue

log = logging.getLogger(__name__)


async def _process(client, job: dict) -> None:
    invite = queue.invite_hash(job["invite_link"])
    result = await client(CheckChatInviteRequest(invite), flood_sleep_threshold=0)
    if not isinstance(result, ChatInviteAlready) and queue.begin_join(job):
        try:
            await client(ImportChatInviteRequest(invite), flood_sleep_threshold=0)
        except errors.FloodWaitError as e:
            # This RPC was explicitly refused; unlike timeouts it is safe to attempt after the wait.
            queue.defer(job, "Telegram rate limit; retry scheduled.", delay=e.seconds + 1, flood=True, join_refused=True)
            return
        result = await client(CheckChatInviteRequest(invite), flood_sleep_threshold=0)
    if isinstance(result, ChatInviteAlready) and isinstance(result.chat, (Chat, Channel)):
        chat = result.chat
        queue.activate(job, utils.get_peer_id(chat), chat.title, getattr(chat, "username", None), bool(getattr(chat, "forum", False)))
    else:
        queue.defer(job, "Waiting for Telegram membership confirmation; the invitation will not be submitted again.")


async def process_one(client) -> bool:
    job = queue.claim()
    if job is None:
        return False
    try:
        await asyncio.wait_for(_process(client, job), timeout=60)
    except errors.InviteRequestSentError:
        queue.defer(job, "Waiting for the Telegram chat administrator to approve membership.")
    except (errors.InviteHashInvalidError, errors.InviteHashExpiredError, errors.InviteHashEmptyError):
        queue.defer(job, "Invitation is invalid or expired. Submit a new invitation for review.", failed=True)
    except (errors.ChannelsTooMuchError, errors.UsersTooMuchError):
        queue.defer(job, "Telegram membership limit reached. Contact a cAtIx administrator before submitting again.", failed=True)
    except errors.UserBannedInChannelError:
        queue.defer(job, "The userbot cannot join this chat. Ask the Telegram chat administrator to review its access.", failed=True)
    except errors.FloodWaitError as e:
        queue.defer(job, "Telegram rate limit; verification scheduled.", delay=e.seconds + 1, flood=True)
    except Exception:  # Includes uncertain writes: retain intent, never expose/log exceptions containing invitations.
        queue.defer(job, "Telegram result could not be confirmed. Verification will be retried; no repeated join is sent.")
    return True


async def run(client) -> None:
    while True:
        try:
            await process_one(client)
        except Exception:  # Database failures must not kill the durable queue; never log exception payloads.
            log.warning("Source request worker unavailable; retrying.")
        await asyncio.sleep(5)
