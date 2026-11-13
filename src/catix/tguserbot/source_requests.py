"""Approved-only Telegram writes with durable intent and membership reconciliation."""
import asyncio
import logging

from telethon import errors, utils
from telethon.tl.functions.channels import GetParticipantRequest, JoinChannelRequest
from telethon.tl.functions.messages import CheckChatInviteRequest, ImportChatInviteRequest
from telethon.tl.types import (
    Channel, ChannelParticipant, ChannelParticipantAdmin, ChannelParticipantCreator,
    ChannelParticipantSelf, Chat, ChatInviteAlready, InputPeerSelf,
)

from catix import source_requests as queue

log = logging.getLogger(__name__)


async def _process(client, job: dict) -> None:
    username = queue.public_username(job["invite_link"])
    if username is not None:
        await _process_public(client, job, username)
        return
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


async def _process_public(client, job: dict, username: str) -> None:
    """Resolve public links, but activate only after Telegram confirms self membership."""
    try:
        chat = await client.get_entity(username)
    except (ValueError, errors.UsernameInvalidError, errors.UsernameNotOccupiedError, errors.ChannelPrivateError):
        queue.defer(job, "The public Telegram group or channel could not be found or accessed.", failed=True)
        return
    if not isinstance(chat, Channel) or not getattr(chat, "username", None):
        queue.defer(job, "This public link does not resolve to a Telegram group or channel.", failed=True)
        return
    input_channel = utils.get_input_channel(chat)
    if input_channel is None:
        queue.defer(job, "The public Telegram group or channel could not be resolved.", failed=True)
        return
    try:
        participant = await client(GetParticipantRequest(input_channel, InputPeerSelf()), flood_sleep_threshold=0)
        member = isinstance(participant.participant, _MEMBER_TYPES)
    except errors.UserNotParticipantError:
        member = False
    except (errors.ChannelPrivateError, errors.ChannelInvalidError):
        queue.defer(job, "The public Telegram group or channel is private or unavailable.", failed=True)
        return
    if not member:
        if not queue.begin_join(job):
            queue.defer(job, "Waiting for Telegram membership confirmation; the join will not be repeated.")
            return
        try:
            await client(JoinChannelRequest(input_channel), flood_sleep_threshold=0)
        except errors.FloodWaitError as e:
            queue.defer(job, "Telegram rate limit; retry scheduled.", delay=e.seconds + 1, flood=True, join_refused=True)
            return
        try:
            participant = await client(GetParticipantRequest(input_channel, InputPeerSelf()), flood_sleep_threshold=0)
        except errors.UserNotParticipantError:
            queue.defer(job, "Telegram did not confirm membership in this public chat.")
            return
        except (errors.ChannelPrivateError, errors.ChannelInvalidError):
            queue.defer(job, "The public Telegram group or channel is private or unavailable.", failed=True)
            return
        if not isinstance(participant.participant, _MEMBER_TYPES):
            queue.defer(job, "Telegram did not confirm active membership in this public chat.")
            return
    queue.activate(job, utils.get_peer_id(chat), chat.title, chat.username, bool(getattr(chat, "forum", False)))


_MEMBER_TYPES = (ChannelParticipant, ChannelParticipantAdmin, ChannelParticipantCreator, ChannelParticipantSelf)


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
