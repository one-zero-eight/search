"""Passive MAX account runtime; durability starts at our inbox commit.

MAX supplies neither a durable acknowledgement nor guaranteed replay. A frame
lost before admission, and offline edits/deletes, are not guaranteed recoverable.
Only sanitized metadata and normalized message identities enter the inbox.
"""

import asyncio
from datetime import datetime, timezone
from functools import partial
import logging
from pathlib import Path
import random
import time

from catix.db import pg
from catix.ingest import images, publish
from catix.settings import settings

from . import media, requests, state
from .client import AccountClient, LoginRequired, classify_error
from .models import ProtocolError, normalize_event, normalize_id, normalize_message

log = logging.getLogger("catix.maxuserbot")


class WorkerBusy(Exception):
    """Another MAX worker holds the dedicated account lock."""

    code = "worker_locked"


class _LockLost(Exception):
    """Losing the advisory-lock connection terminates this listener."""

    code = "worker_lock_lost"


def _check_lock(conn):
    try:
        conn.execute("SELECT 1")
        conn.commit()
    except Exception:
        raise _LockLost("worker_lock_lost") from None


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _sql(operation, *args, **kwargs):
    """Cancellation cannot roll back a running thread: drain it before closing DB."""
    task = asyncio.create_task(asyncio.to_thread(operation, *args, **kwargs))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        try:
            await task
        except Exception:
            # The caller is already stopping; do not leak SQL/driver messages.
            log.warning("processing_error: database operation failed during shutdown")
        raise


def _acquire_lock():
    conn = pg.connect()
    try:
        conn.execute("SET statement_timeout = '5s'")
        conn.execute("SET lock_timeout = '5s'")
        row = conn.execute("SELECT pg_try_advisory_lock(1296128077, 1) AS locked").fetchone()
        conn.commit()
        if not row or not row["locked"]:
            raise WorkerBusy("worker_locked: another MAX listener is running")
        return conn
    except BaseException:
        conn.close()
        raise


async def _open_lock():
    # If cancellation wins the acquisition race, the resulting lock still needs
    # its own close; generic fire-and-forget to_thread would leak ownership.
    task = asyncio.create_task(asyncio.to_thread(_acquire_lock))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        try:
            conn = await task
        except Exception:
            pass
        else:
            await _sql(conn.close)
        raise


async def _close_client(client):
    task = asyncio.create_task(client.close())
    try:
        await asyncio.shield(task)
    except asyncio.CancelledError:
        await task
        raise
    except Exception:
        log.warning("processing_error: transport shutdown failed")


def _check_login(exc: Exception) -> None:
    if isinstance(exc, LoginRequired) or classify_error(exc) == "login_required":
        raise LoginRequired() from None


def _error_code(exc: Exception, fallback: str) -> str:
    code = classify_error(exc)
    return code if code in {"protocol_error", "identity_range"} else fallback


class _Worker:
    def __init__(self, lock):
        # If saving a successful network result fails, retry that same read,
        # rather than assigning a new observation to older content.
        self.unsaved: dict[int, dict | None] = {}
        self.next_prune = time.monotonic() + 3600
        self.lock = lock
        self.connected_since = None

    async def sink(self, opcode, payload, observed_at, event_key):
        event = normalize_event(opcode, payload)
        if event is not None:
            # No network, bodies, or upstream exception text in this boundary.
            await _sql(state.receive_event, event, observed_at=observed_at, event_key=event_key)

    async def consume_one(self, client, event):
        event_id = event["id"]
        payload = event["payload"]
        if payload.get("kind") == "message":
            source = await _sql(state.get_source, event["chat_id"])
            if (source is None or not source["enabled"] or source["access"] != "ready"
                    or source["generation"] != event["generation"]):
                self.unsaved.pop(event_id, None)
                await _sql(state.apply_event, event_id)
                return
        if "snapshot" in payload:
            # A previous save may have committed before its acknowledgement was
            # lost. The persisted snapshot is authoritative on the next retry.
            self.unsaved.pop(event_id, None)
        if payload.get("kind") == "message" and "snapshot" not in payload:
            if event_id not in self.unsaved:
                if source is None:
                    raise ProtocolError()
                observation = _now()
                await _sql(state.begin_fetch, event_id, observation)
                messages = await client.messages(source["raw_chat_id"], payload["message_ids"])
                snapshot = None
                for raw in messages:
                    value = normalize_message(raw, source["raw_chat_id"])
                    if value is not None:
                        snapshot = value.to_dict()
                        break
                if snapshot is None:
                    log.warning("message_unavailable: message fetch returned no usable message for chat %s",
                                source["raw_chat_id"])
                self.unsaved[event_id] = snapshot
            await _sql(state.save_fetched, event_id, self.unsaved[event_id])
            del self.unsaved[event_id]
        # State rereads the persisted payload, including fetch observation, and
        # atomically applies the message/fence/outbox and clears the inbox body.
        await _sql(state.apply_event, event_id)

    async def consume(self, client):
        while True:
            event = await _sql(state.next_event)
            if event is None:
                await asyncio.sleep(0.25)
                continue
            try:
                await self.consume_one(client, event)
            except Exception as exc:
                _check_login(exc)
                code = _error_code(exc, "processing_error")
                log.warning("%s: inbox processing deferred", code)
                await _sql(state.fail_event, event["id"], code)

    async def refresh_history(self, client, job):
        if not await _sql(state.history_current, job):
            return
        cursor = job["history_before_ms" if job["kind"] == "full" else "catchup_before_ms"]
        messages = await client.history(job["raw_chat_id"], cursor)
        if not isinstance(messages, list) or len(messages) > 100:
            raise ProtocolError()
        snapshots = []
        oldest_ms = None
        for raw in messages:
            snapshot = normalize_message(raw, job["raw_chat_id"])
            normalize_id(raw.get("id"))
            if raw.get("chatId") is not None and normalize_id(raw["chatId"]) != job["raw_chat_id"]:
                raise ProtocolError()
            # Even excluded comments count towards the server's page boundary.
            created_ms = normalize_id(raw.get("time"))
            if not 0 <= created_ms <= cursor:
                raise ProtocolError()
            oldest_ms = created_ms if oldest_ms is None else min(oldest_ms, created_ms)
            if snapshot is not None:
                snapshots.append(snapshot.to_dict())
        page_job = {**job, "page_size": len(messages), "page_oldest_ms": oldest_ms if oldest_ms is not None else cursor}
        await _sql(state.apply_history_page, page_job, snapshots)

    async def history(self, client, kind):
        while True:
            job = await _sql(state.next_history, kind)
            if job is None:
                await asyncio.sleep(0.25)
                continue
            try:
                await self.refresh_history(client, job)
            except Exception as exc:
                _check_login(exc)
                code = _error_code(exc, "history_error")
                if isinstance(exc, ProtocolError) and exc.code == "history_timestamp_boundary":
                    code = exc.code
                log.warning("%s: %s history deferred for chat %s", code, kind, job["raw_chat_id"])
                await _sql(state.fail_history, job, code,
                           terminal=isinstance(exc, ProtocolError))
            # next_history rotates its database order after each selected page.
            # Let ready live-event work run before asking for another page.
            await asyncio.sleep(0)

    async def refresh_deletion_scan(self, client, job):
        if not await _sql(state.deletion_scan_current, job):
            return
        messages = await client.messages(job["raw_chat_id"], job["ids"])
        if not isinstance(messages, list):
            raise ProtocolError()
        snapshots = []
        returned_ids = []
        for raw in messages:
            snapshot = normalize_message(raw, job["raw_chat_id"])
            message_id = normalize_id(raw.get("id"))
            if raw.get("chatId") is not None and normalize_id(raw["chatId"]) != job["raw_chat_id"]:
                raise ProtocolError()
            if message_id not in job["ids"]:
                raise ProtocolError()
            returned_ids.append(message_id)
            if snapshot is not None and snapshot.deleted:
                snapshots.append(snapshot.to_dict())
        # Missing IDs are only a partial-reconciliation warning, never proof of
        # removal. The state operation checks generation and advances one batch.
        await _sql(state.apply_deletion_scan, job, snapshots, returned_ids)

    async def deletion_scans(self, client):
        while True:
            job = await _sql(state.next_deletion_scan)
            if job is None:
                await asyncio.sleep(0.25)
                continue
            try:
                await self.refresh_deletion_scan(client, job)
            except Exception as exc:
                _check_login(exc)
                log.warning("%s: deletion reconciliation deferred for chat %s",
                            _error_code(exc, "processing_error"), job["raw_chat_id"])
                await _sql(state.fail_deletion_scan, job)
            await asyncio.sleep(0)

    async def publications(self):
        while True:
            item = await _sql(state.next_publication)
            if item is None:
                await asyncio.sleep(1)
                continue
            try:
                if item["exists"]:
                    await publish.publish([(item["chat_id"], item["msg_id"])], strict=True)
                await _sql(state.complete_publication, item["id"])
            except Exception:
                log.warning("publication_error: publication deferred")
                await _sql(state.fail_publication, item["id"])

    async def refresh_catalog(self, client):
        marker = time.time_ns() // 1_000_000
        seen = set()
        while True:
            if marker in seen:
                await _sql(state.finish_catalog, "partial", "catalog_cursor_stalled")
                return
            seen.add(marker)
            observation = _now()
            try:
                chats, next_marker = await client.catalog_page(marker)
            except ProtocolError as exc:
                # A valid page with an unknown continuation is still useful.
                page = getattr(exc, "page", None)
                if page is not None:
                    await _sql(state.upsert_catalog, page, observed_at=observation)
                await _sql(state.finish_catalog, "partial", _error_code(exc, "protocol_error")
                           if exc.code != "catalog_pagination_unknown" else exc.code)
                return
            await _sql(state.upsert_catalog, chats, observed_at=observation)
            if next_marker is None:
                await _sql(state.finish_catalog, "complete")
                return
            marker = next_marker

    async def catalog(self, client):
        while True:
            if not await _sql(state.catalog_due):
                await asyncio.sleep(1)
                continue
            try:
                await self.refresh_catalog(client)
            except Exception as exc:
                _check_login(exc)
                code = _error_code(exc, "metadata_error")
                log.warning("%s: catalog refresh deferred", code)
                await _sql(state.finish_catalog, "failed", code)

    async def refresh_metadata(self, client, job):
        observation = _now()
        chat = await client.chat(job["raw_chat_id"])
        if not chat:
            await _sql(state.apply_access, job["chat_id"], generation=job["generation"],
                       access="removed", observed_at=observation)
            return
        await _sql(state.upsert_catalog, [chat], observed_at=observation)
        if chat["status"] != "ACTIVE":
            await _sql(state.apply_access, job["chat_id"], generation=job["generation"],
                       access="unknown", observed_at=observation, error="source_status_unknown")
            return
        # Validate read access, but discard probe bodies even for enabled sources.
        await client.history(job["raw_chat_id"], time.time_ns() // 1_000_000 + 1, backward=1)
        await _sql(state.apply_access, job["chat_id"], generation=job["generation"],
                   access="ready", observed_at=observation)

    async def metadata(self, client):
        while True:
            job = await _sql(state.next_metadata)
            if job is None:
                await asyncio.sleep(0.25)
                continue
            try:
                await self.refresh_metadata(client, job)
            except Exception as exc:
                _check_login(exc)
                code = _error_code(exc, "metadata_error")
                log.warning("%s: metadata refresh deferred for chat %s", code, job["raw_chat_id"])
                # Transport/API errors are not evidence that access was revoked.
                await _sql(state.fail_metadata, job, code)

    async def heartbeat(self, client):
        while True:
            await asyncio.sleep(20)
            if not client.connected:
                return
            await _sql(_check_lock, self.lock)
            async def ordered_update():
                observed_ms = time.time_ns() // 1_000_000
                await _sql(state.heartbeat)
                await _sql(state.advance_watermark, observed_ms)

            await client.ordered_heartbeat(ordered_update)

    async def prune(self):
        while True:
            await asyncio.sleep(max(0, self.next_prune - time.monotonic()))
            await _sql(state.prune_inbox)
            self.next_prune = time.monotonic() + 3600

    async def session(self, client):
        tasks = []
        try:
            await _sql(state.prepare_recovery, time.time_ns() // 1_000_000 + 1)
            await client.connect()
            await _sql(state.account_connected, client.account_id)
            self.connected_since = time.monotonic()
            client.sink = self.sink
            # Keep the captured lower bound while covering frames ignored during
            # login, before account ownership and admission were established.
            await _sql(state.prepare_recovery, time.time_ns() // 1_000_000 + 1)
            # login_chats is already sanitized by the adapter; never persist the
            # upstream login cache, contacts, lastMessage, or pinnedMessage.
            await _sql(state.upsert_catalog, client.login_chats, observed_at=_now())
            tasks = [asyncio.create_task(loop) for loop in (
                client.wait_closed(), self.consume(client), self.publications(),
                self.catalog(client), self.metadata(client), self.heartbeat(client), self.prune(),
                self.history(client, "full"), self.history(client, "catchup"),
                self.deletion_scans(client),
                requests.run(client),
                images.run('maxuserbot', partial(media.download, client), allowed=media.allowed),
            )]
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            # Retrieve every finished exception; never log its potentially secret text.
            errors = [task.exception() for task in done if not task.cancelled()]
            for exc in errors:
                if exc is not None:
                    _check_login(exc)
                    raise exc
        finally:
            client.sink = None
            # Stop new work immediately; shielded SQL calls finish before their
            # cancelled tasks exit. Record offline before waiting for the drains.
            for task in tasks:
                task.cancel()
            try:
                await _sql(state.heartbeat, connected=False)
            except Exception:
                log.warning("processing_error: could not mark account offline")
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            # A heartbeat already executing in a thread may have committed after
            # the first offline write. Fence it once all SQL tasks have drained.
            if tasks:
                try:
                    await _sql(state.heartbeat, connected=False)
                except Exception:
                    log.warning("processing_error: could not confirm account offline")


async def run() -> None:
    """Run one account; the CLI already owns its local SQLite session flock."""
    lock = None
    try:
        lock = await _open_lock()
        worker = _Worker(lock)
        delay = 1
        while True:
            await _sql(_check_lock, lock)
            client = AccountClient(Path(settings.max_session))
            worker.connected_since = None
            try:
                await worker.session(client)
            except (LoginRequired, state.AccountMismatch) as exc:
                await _sql(state.account_error, exc.code)
                raise
            except _LockLost:
                raise
            except Exception as exc:
                _check_login(exc)
                log.warning("%s: connection interrupted", _error_code(exc, "processing_error"))
            finally:
                await _close_client(client)
            if worker.connected_since is not None and time.monotonic() - worker.connected_since >= 300:
                delay = 1
            await asyncio.sleep(random.uniform(delay, min(delay * 1.2, 60)))
            delay = min(delay * 2, 60)
    finally:
        try:
            if lock is not None:
                await _sql(lock.close)
        finally:
            await _sql(pg.close)
