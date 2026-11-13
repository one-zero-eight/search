"""Approved-only MAX joins. A committed intent permits exactly one write attempt."""

import asyncio
from datetime import datetime, timezone
import logging
import time

from catix import source_requests as queue
from catix.ingest.images import database_call

from . import state
from .client import LoginRequired, classify_error
from .models import MAX_USER_CHAT_BASE, ProtocolError, db_chat_id, normalize_id

log = logging.getLogger(__name__)
WAITING = 'Waiting for MAX membership confirmation; the invitation will not be submitted again.'
RETRY = 'MAX access could not be confirmed; verification will be retried safely.'


async def _member(client, raw_id: int) -> dict | None:
    """Only fresh CHAT_INFO plus a successful discarded history probe prove access."""
    chat = await client.chat(raw_id)
    if not chat:
        return None
    if chat['raw_chat_id'] != raw_id or chat.get('kind') not in {'chat', 'channel'}:
        raise ProtocolError()
    if chat.get('status') != 'ACTIVE':
        return None
    await client.history(raw_id, time.time_ns() // 1_000_000 + 1, backward=1)
    return chat


async def _process(client, job: dict) -> None:
    try:
        link = queue.normalize_link(job['invite_link'])
    except ValueError:
        await database_call(queue.defer, job, 'MAX source link is invalid; manual review required.', failed=True)
        return
    if not link.startswith('https://max.ru/'):
        await database_call(queue.defer, job, 'MAX source link is invalid; manual review required.', failed=True)
        return
    if job.get('chat_id') is not None:
        raw_id = normalize_id(job['chat_id']) - MAX_USER_CHAT_BASE
        db_chat_id(raw_id)
        known = await database_call(state.get_source, job['chat_id'])
        if known is None or known['raw_chat_id'] != raw_id:
            await database_call(queue.defer, job, 'MAX source identity is unavailable; manual review required.', failed=True)
            return
        source = await database_call(queue.remember_max, job, known)
        if source is None:
            return
        observed_at = datetime.now(timezone.utc)
        member = await _member(client, raw_id)
        if member is not None:
            await database_call(queue.activate_max, job, member,
                                expected_version=source['config_version'], expected_generation=source['generation'],
                                observed_at=observed_at)
            return
    # An expired invitation must not prevent native identity reconciliation.
    try:
        resolved = await client.resolve_link(link)
    except Exception as exc:
        if (job.get('chat_id') is None or isinstance(exc, LoginRequired)
                or classify_error(exc) == 'login_required'):
            raise
        resolved = None
    if resolved is None and job.get('chat_id') is None:
        await database_call(queue.defer, job, 'MAX link is invalid, expired or unavailable.', failed=True)
        return
    if resolved is not None:
        source = await database_call(queue.remember_max, job, resolved)
    else:
        raw_id = normalize_id(job['chat_id']) - MAX_USER_CHAT_BASE
        if db_chat_id(raw_id) != job['chat_id']:
            raise ProtocolError('identity_range')
        known = await database_call(state.get_source, job['chat_id'])
        if known is None or known['raw_chat_id'] != raw_id:
            await database_call(queue.defer, job, 'MAX source identity is unavailable; manual review required.', failed=True)
            return
        source = await database_call(queue.remember_max, job, known)
    if source is None:
        return  # Ownership was lost or the configured source requires manual review.
    raw_id = source['raw_chat_id']
    observed_at = datetime.now(timezone.utc)
    member = await _member(client, raw_id)
    if member is None:
        if resolved is None:
            await database_call(queue.defer, job, WAITING)
            return
        if await database_call(queue.begin_join, job):
            # Even cancellation or a lost response leaves intent durable. Never
            # clear it on unknown errors, and never trust the join response alone.
            try:
                joined = await client.join_link(link)
                if joined is not None and joined['raw_chat_id'] != raw_id:
                    await database_call(queue.defer, job, 'MAX join returned a different source identity; manual review required.', failed=True)
                    return
            finally:
                await database_call(state.request_catalog)
        observed_at = datetime.now(timezone.utc)
        member = await _member(client, raw_id)
    if member is None:
        await database_call(queue.defer, job, WAITING)
        return
    await database_call(queue.activate_max, job, member,
                        expected_version=source['config_version'], expected_generation=source['generation'],
                        observed_at=observed_at)


async def process_one(client) -> bool:
    job = await database_call(queue.claim, messenger='max')
    if job is None:
        return False
    try:
        # Three reads and one optional write must fit the durable account lease.
        async with asyncio.timeout(90):
            await _process(client, job)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        if isinstance(exc, LoginRequired) or classify_error(exc) == 'login_required':
            raise LoginRequired() from None
        await database_call(queue.defer, job, RETRY)
        # Never include invitation, raw protocol payload or upstream exception text.
        log.warning('source_request_verification_deferred')
    return True


async def run(client) -> None:
    while True:
        await process_one(client)
        await asyncio.sleep(5)
