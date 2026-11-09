"""Synchronous transactional account state. Source locks precede all message work."""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from catix import groups
from catix.db import pg, store
from psycopg.types.json import Jsonb
from .models import ProtocolError, db_chat_id, normalize_id


class ConfigurationConflict(Exception):
    pass


class SourceNotFound(Exception):
    pass


class SourceUnavailable(Exception):
    pass


class AccountMismatch(Exception):
    code = "account_mismatch"


SOURCE = """SELECT s.*, c.title, c.link, c.group_code, c.requires_verified_group, c.official
            FROM max_sources s JOIN chats c USING (chat_id)"""
ERRORS = frozenset({"login_required", "account_mismatch", "identity_range", "protocol_error", "processing_error",
    "metadata_error", "source_status_unknown", "catalog_pagination_unknown", "catalog_cursor_stalled",
    "history_error", "history_timestamp_boundary", "message_unavailable", "deletion_reconciliation_partial",
    "publication_error"})


def _code(value):
    return value if value in ERRORS else "processing_error"


@contextmanager
def _transaction():
    with pg.connection() as conn:
        conn.execute("SET LOCAL lock_timeout = '5s'")
        conn.execute("SET LOCAL statement_timeout = '5s'")
        yield conn


def _source(conn, chat_id):
    row = conn.execute(SOURCE + " WHERE s.chat_id = %s FOR UPDATE OF s", (chat_id,)).fetchone()
    if row is None:
        raise SourceNotFound()
    return row


def _version(source, version, generation):
    if source["config_version"] != version or source["generation"] != generation:
        raise ConfigurationConflict()


def _ready(source):
    return source["enabled"] and source["access"] == "ready"


def list_sources() -> list[dict]:
    with pg.connection() as conn:
        return conn.execute(SOURCE + " ORDER BY lower(c.title), s.raw_chat_id").fetchall()


def get_source(chat_id: int) -> dict | None:
    with pg.connection() as conn:
        return conn.execute(SOURCE + " WHERE s.chat_id = %s", (chat_id,)).fetchone()


def allowed(chat_id: int) -> bool:
    with pg.connection() as conn:
        row = conn.execute("SELECT enabled AND access = 'ready' AS allowed FROM max_sources WHERE chat_id = %s", (chat_id,)).fetchone()
        return bool(row and row["allowed"])


def get_account() -> dict | None:
    with pg.connection() as conn:
        return conn.execute("SELECT * FROM max_account WHERE singleton").fetchone()


def account_connected(account_id: int) -> None:
    account_id = normalize_id(account_id)
    with _transaction() as conn:
        conn.execute("INSERT INTO max_account(singleton) VALUES (true) ON CONFLICT DO NOTHING")
        row = conn.execute("SELECT * FROM max_account WHERE singleton FOR UPDATE").fetchone()
        if row["account_id"] is not None and row["account_id"] != account_id:
            raise AccountMismatch("account_mismatch")
        conn.execute("""UPDATE max_account SET account_id = %s, connected_at = now(), heartbeat_at = now(),
                        catalog_requested = true, catalog_error = NULL WHERE singleton""", (account_id,))


def heartbeat(*, connected=True) -> None:
    with _transaction() as conn:
        conn.execute("UPDATE max_account SET heartbeat_at = CASE WHEN %s THEN now() ELSE NULL END WHERE singleton", (connected,))


def account_error(code: str) -> None:
    with _transaction() as conn:
        conn.execute("""INSERT INTO max_account(singleton,catalog_status,catalog_error)
            VALUES(true,'failed',%s) ON CONFLICT(singleton) DO UPDATE SET heartbeat_at=NULL,
            catalog_status='failed',catalog_error=excluded.catalog_error""",(_code(code),))


def request_catalog() -> None:
    with _transaction() as conn:
        conn.execute("""INSERT INTO max_account(singleton, catalog_requested) VALUES(true, true)
                        ON CONFLICT(singleton) DO UPDATE SET catalog_requested = true""")
        conn.execute("UPDATE max_sources SET metadata_pending = true, metadata_available_at = now()")


def upsert_catalog(chats: list[dict], *, observed_at: datetime) -> None:
    # Only sanitized chat metadata is accepted; no users, contacts or message cache.
    with _transaction() as conn:
        for chat in chats:
            if chat.get("kind") not in {"chat", "channel"}:
                continue
            raw_id = normalize_id(chat["raw_chat_id"])
            chat_id = db_chat_id(raw_id)
            title = chat.get("title") or str(raw_id)
            if not isinstance(title, str):
                raise ProtocolError()
            # Existing sources follow configuration/ingest lock order.
            conn.execute("SELECT chat_id FROM max_sources WHERE chat_id=%s FOR UPDATE", (chat_id,))
            conn.execute("""INSERT INTO chats(chat_id,title,link,group_code,requires_verified_group)
                            VALUES(%s,%s,%s,'all',true) ON CONFLICT(chat_id) DO UPDATE
                            SET title=excluded.title,link=coalesce(excluded.link,chats.link)""", (chat_id, title, chat.get("link")))
            conn.execute("""INSERT INTO max_sources(chat_id,raw_chat_id,kind) VALUES(%s,%s,%s)
                            ON CONFLICT(chat_id) DO UPDATE SET kind=excluded.kind, metadata_pending=true,
                            metadata_available_at=least(max_sources.metadata_available_at,now())""", (chat_id, raw_id, chat["kind"]))


def _fresh(conn, source):
    now = datetime.now(timezone.utc)
    account = conn.execute("SELECT heartbeat_at FROM max_account WHERE singleton").fetchone()
    if (source["access"] != "ready" or source["checked_at"] is None
            or source["checked_at"] < now - timedelta(minutes=5)
            or not account or account["heartbeat_at"] is None
            or account["heartbeat_at"] < now - timedelta(seconds=60)):
        return False
    return True


def _history_reset(conn, chat_id):
    conn.execute("""UPDATE max_sources SET history_status='pending',history_before_ms=%s,
                    history_started_at=now(),history_last_id=NULL,history_available_at=now()
                    WHERE chat_id=%s""", (int(datetime.now(timezone.utc).timestamp()*1000)+1, chat_id))


def list_legacy() -> list[dict]:
    with pg.connection() as conn:
        return conn.execute("""SELECT c.chat_id,c.title,c.group_code,c.max_legacy_archived,
                (SELECT count(*) FROM messages m WHERE m.chat_id=c.chat_id) AS message_count,
                s.chat_id AS linked_chat_id FROM chats c LEFT JOIN max_sources s ON s.legacy_chat_id=c.chat_id
                WHERE c.chat_id > %s AND c.chat_id < %s ORDER BY lower(c.title),c.chat_id""",
                (groups.MAX_CHAT_BASE-10**13, groups.MAX_CHAT_BASE+10**13)).fetchall()


def save_configuration(chat_id: int, group_code: str, *, enabled: bool, expected_version: int,
                       expected_generation: int, legacy_chat_id: int | None = None) -> None:
    group_code = groups.normalize(group_code)
    if group_code is None:
        raise ValueError("invalid_group")
    # Refresh request must survive an unavailable result, not roll back with it.
    unavailable = False
    with _transaction() as conn:
        source = _source(conn, chat_id)
        _version(source, expected_version, expected_generation)
        if enabled and not _fresh(conn, source):
            conn.execute("UPDATE max_sources SET metadata_pending=true,metadata_available_at=now() WHERE chat_id=%s", (chat_id,))
            conn.execute("UPDATE max_account SET catalog_requested=true WHERE singleton")
            unavailable = True
        else:
            previous_legacy = source["legacy_chat_id"]
            if previous_legacy is not None:
                if legacy_chat_id is not None and previous_legacy != legacy_chat_id:
                    raise ConfigurationConflict()
                legacy_chat_id = previous_legacy
            if legacy_chat_id is not None:
                legacy_chat_id = normalize_id(legacy_chat_id)
                if not groups.MAX_CHAT_BASE-10**13 < legacy_chat_id < groups.MAX_CHAT_BASE+10**13:
                    raise ConfigurationConflict()
                legacy = conn.execute("SELECT chat_id FROM chats WHERE chat_id=%s FOR UPDATE", (legacy_chat_id,)).fetchone()
                linked = conn.execute("SELECT chat_id FROM max_sources WHERE legacy_chat_id=%s AND chat_id<>%s", (legacy_chat_id, chat_id)).fetchone()
                if not legacy or linked:
                    raise ConfigurationConflict()
            toggled = enabled != source["enabled"]
            changed = toggled or group_code != source["group_code"] or legacy_chat_id != previous_legacy
            conn.execute("UPDATE chats SET group_code=%s,requires_verified_group=%s WHERE chat_id=%s",
                         (group_code, group_code != groups.ALL, chat_id))
            conn.execute("""UPDATE max_sources SET enabled=%s,legacy_chat_id=%s,
                            config_version=config_version+%s,generation=generation+%s WHERE chat_id=%s""",
                         (enabled, legacy_chat_id, int(changed), int(toggled), chat_id))
            if enabled and legacy_chat_id is not None:
                conn.execute("UPDATE chats SET max_legacy_archived=true WHERE chat_id=%s", (legacy_chat_id,))
            if toggled and enabled:
                _history_reset(conn, chat_id)
                conn.execute("""UPDATE max_sources SET catchup_status='idle',catchup_before_ms=NULL,
                    catchup_after_ms=NULL,catchup_until_ms=NULL,sync_watermark_ms=%s WHERE chat_id=%s""",
                    (int(datetime.now(timezone.utc).timestamp()*1000),chat_id))
            elif toggled:
                conn.execute("""UPDATE max_sources SET history_status=CASE WHEN history_status IN ('pending','running')
                                THEN 'cancelled' ELSE history_status END WHERE chat_id=%s""", (chat_id,))
    if unavailable:
        raise SourceUnavailable()


def request_history(chat_id: int, *, expected_version: int, expected_generation: int) -> None:
    unavailable = False
    with _transaction() as conn:
        source = _source(conn, chat_id)
        _version(source, expected_version, expected_generation)
        if not _ready(source) or not _fresh(conn, source):
            conn.execute("UPDATE max_sources SET metadata_pending=true,metadata_available_at=now() WHERE chat_id=%s", (chat_id,))
            unavailable = True
        else:
            _history_reset(conn, chat_id)
            if source['catchup_status'] in {'partial','failed'}:
                conn.execute("""UPDATE max_sources SET catchup_status='pending',
                    catchup_before_ms=catchup_until_ms,catchup_available_at=now() WHERE chat_id=%s""",(chat_id,))
            conn.execute("UPDATE max_sources SET config_version=config_version+1 WHERE chat_id=%s", (chat_id,))
    if unavailable:
        raise SourceUnavailable()


def clear_history(chat_id: int, *, expected_version: int, expected_generation: int) -> int:
    """Clear content, not source policy/tombstones; fence all reads already in flight."""
    with _transaction() as conn:
        source = _source(conn, chat_id)
        _version(source, expected_version, expected_generation)
        deleted = store.clear_chat(chat_id, conn=conn)
        conn.execute('DELETE FROM max_publish_queue WHERE chat_id=%s', (chat_id,))
        # Cleared live identities must be restorable by an explicit full reload.
        # Permanent deletion tombstones remain authoritative.
        conn.execute('DELETE FROM max_message_state WHERE chat_id=%s AND NOT deleted', (chat_id,))
        conn.execute("""UPDATE max_sources SET generation=generation+1, config_version=config_version+1,
            history_status='cancelled',catchup_status='cancelled',deletion_scan_pending=false
            WHERE chat_id=%s""", (chat_id,))
        return deleted


def apply_access(chat_id: int, *, generation: int, access: str, observed_at: datetime,
                 error: str | None = None) -> None:
    if access not in {"unknown", "ready", "removed", "no_permission"}:
        raise ValueError("invalid_access")
    with _transaction() as conn:
        source = _source(conn, chat_id)
        if source["generation"] != generation or (source["checked_at"] and source["checked_at"] > observed_at):
            return
        revoke = access != "ready" and (source["enabled"] or source["access"] == "ready")
        conn.execute("""UPDATE max_sources SET access=%s,checked_at=%s,metadata_pending=false,
                        metadata_available_at=now()+interval '5 minutes',last_error=%s,
                        enabled=CASE WHEN %s THEN false ELSE enabled END,
                        generation=generation+%s,config_version=config_version+%s,
                        history_status=CASE WHEN %s AND history_status IN ('pending','running')
                        THEN 'cancelled' ELSE history_status END WHERE chat_id=%s""",
                     (access, observed_at, _code(error) if error else None, revoke, int(revoke), int(revoke), revoke, chat_id))


def catalog_due() -> bool:
    with _transaction() as conn:
        row = conn.execute("""UPDATE max_account SET catalog_requested=false,catalog_status='running'
            WHERE singleton AND (catalog_requested OR catalog_checked_at IS NULL
            OR catalog_checked_at < now()-interval '10 minutes') RETURNING singleton""").fetchone()
        return row is not None


def finish_catalog(status: str, error: str | None = None) -> None:
    if status not in {'complete','partial','failed'}:
        raise ValueError('invalid_catalog_status')
    with _transaction() as conn:
        conn.execute("""UPDATE max_account SET catalog_status=%s,catalog_error=%s,
                        catalog_checked_at=now() WHERE singleton""", (status, _code(error) if error else None))


def next_metadata() -> dict | None:
    with _transaction() as conn:
        row = conn.execute(SOURCE + """ WHERE s.metadata_available_at<=now()
            AND (s.metadata_pending OR s.enabled) ORDER BY s.metadata_available_at,s.chat_id
            LIMIT 1 FOR UPDATE OF s""").fetchone()
        if row:
            conn.execute("UPDATE max_sources SET metadata_available_at=now()+interval '60 seconds' WHERE chat_id=%s", (row['chat_id'],))
            row['observed_at'] = datetime.now(timezone.utc)
        return row


def fail_metadata(job: dict, code: str) -> None:
    with _transaction() as conn:
        source = _source(conn, job['chat_id'])
        if source['generation'] == job['generation']:
            conn.execute("""UPDATE max_sources SET metadata_pending=true,metadata_available_at=now()+interval '60 seconds',
                last_error=%s WHERE chat_id=%s""", (_code(code), source['chat_id']))


def receive_event(event: dict, *, observed_at: datetime, event_key: str) -> None:
    raw_id = normalize_id(event['raw_chat_id'])
    chat_id = db_chat_id(raw_id)
    kind = event.get('kind')
    if kind not in {'message','removed','metadata','reconcile_deleted','invalid'}:
        raise ProtocolError()
    with _transaction() as conn:
        source = conn.execute(SOURCE+' WHERE s.chat_id=%s FOR UPDATE OF s', (chat_id,)).fetchone()
        if not source:
            conn.execute("""INSERT INTO max_account(singleton,catalog_requested) VALUES(true,true)
                ON CONFLICT(singleton) DO UPDATE SET catalog_requested=true""")
            return
        if kind == 'metadata':
            # NOTIF_CHAT status cannot reopen admission; only fresh CHAT_INFO+probe.
            if event.get('status') != 'ACTIVE' and (source['enabled'] or source['access']=='ready'):
                conn.execute("""UPDATE max_sources SET enabled=false,access='unknown',generation=generation+1,
                    config_version=config_version+1,last_error='source_status_unknown',
                    history_status=CASE WHEN history_status IN ('pending','running') THEN 'cancelled' ELSE history_status END
                    WHERE chat_id=%s""", (chat_id,))
            conn.execute("UPDATE max_sources SET metadata_pending=true,metadata_available_at=now() WHERE chat_id=%s", (chat_id,))
            return
        if kind != 'removed' and not _ready(source):
            return
        payload = {'kind':kind}
        if kind in {'message','removed'}:
            ids = event.get('message_ids')
            if not isinstance(ids,list) or (kind=='message' and len(ids)!=1):
                raise ProtocolError()
            payload['message_ids'] = [normalize_id(value) for value in ids]
        conn.execute("""INSERT INTO max_inbox(event_key,chat_id,generation,payload,received_at)
            VALUES(%s,%s,%s,%s,%s) ON CONFLICT(event_key) DO NOTHING""",
            (event_key,chat_id,source['generation'],Jsonb(payload),observed_at))


def next_event() -> dict | None:
    with pg.connection() as conn:
        return conn.execute("""SELECT e.*,s.raw_chat_id FROM max_inbox e JOIN max_sources s USING(chat_id)
            WHERE e.processed_at IS NULL AND e.available_at<=now()
              AND NOT EXISTS(SELECT 1 FROM max_inbox p WHERE p.chat_id=e.chat_id AND p.id<e.id AND p.processed_at IS NULL)
            ORDER BY e.id LIMIT 1""").fetchone()


def _event(conn, event_id):
    location = conn.execute('SELECT chat_id FROM max_inbox WHERE id=%s',(event_id,)).fetchone()
    if not location:
        return None,None
    source = _source(conn,location['chat_id'])
    row = conn.execute('SELECT * FROM max_inbox WHERE id=%s FOR UPDATE',(event_id,)).fetchone()
    return source,row


def _finish(conn,event_id,code=None):
    conn.execute('UPDATE max_inbox SET processed_at=now(),payload=NULL,error_code=%s WHERE id=%s',
                 (_code(code) if code else None,event_id))


def begin_fetch(event_id: int, observed_at: datetime) -> None:
    with _transaction() as conn:
        source,row = _event(conn,event_id)
        if not row or row['processed_at']:
            return
        payload = dict(row['payload'])
        payload.pop('snapshot',None)
        payload['fetch_observed_at'] = observed_at.isoformat()
        conn.execute('UPDATE max_inbox SET payload=%s WHERE id=%s',(Jsonb(payload),event_id))


def save_fetched(event_id: int, snapshot: dict | None) -> None:
    with _transaction() as conn:
        source,row = _event(conn,event_id)
        if not row or row['processed_at']:
            return
        payload = dict(row['payload'])
        if 'fetch_observed_at' not in payload:
            raise ProtocolError()
        payload['snapshot'] = snapshot
        conn.execute('UPDATE max_inbox SET payload=%s WHERE id=%s',(Jsonb(payload),event_id))


def _identity(conn,chat_id,msg_id,observed_at):
    conn.execute("""INSERT INTO max_message_state(chat_id,msg_id,last_received_at) VALUES(%s,%s,%s)
        ON CONFLICT DO NOTHING""", (chat_id,msg_id,observed_at))
    return conn.execute('SELECT * FROM max_message_state WHERE chat_id=%s AND msg_id=%s FOR UPDATE',
                        (chat_id,msg_id)).fetchone()


def _delete(conn,source,msg_id,observed_at,live_id=None):
    identity = _identity(conn,source['chat_id'],msg_id,observed_at)
    fence = store._lock_ingest_state(conn.cursor(),[(source['chat_id'],msg_id)])[source['chat_id'],msg_id]
    observed_at = max(value for value in (observed_at,identity['last_received_at'],fence['observed_at']) if value is not None)
    conn.execute("""UPDATE max_message_state SET deleted=true,last_received_at=%s,
        last_live_id=coalesce(%s,last_live_id) WHERE chat_id=%s AND msg_id=%s""",
        (observed_at,live_id,source['chat_id'],msg_id))
    store.delete_message(source['chat_id'],msg_id,observed_at=observed_at,conn=conn)
    conn.execute('DELETE FROM max_publish_queue WHERE chat_id=%s AND msg_id=%s',(source['chat_id'],msg_id))


def _snapshot(conn,source,snapshot,observed_at,*,live_id=None,archive=False):
    msg_id = normalize_id(snapshot['message_id'])
    if normalize_id(snapshot['raw_chat_id']) != source['raw_chat_id']:
        raise ProtocolError()
    identity = _identity(conn,source['chat_id'],msg_id,observed_at)
    if snapshot.get('deleted'):
        _delete(conn,source,msg_id,observed_at,live_id)
        return False
    if identity['deleted'] or (archive and identity['last_live_id'] is not None):
        return False
    if observed_at < identity['last_received_at']:
        return False
    if observed_at == identity['last_received_at'] and live_id is not None and identity['last_live_id'] is not None and live_id<identity['last_live_id']:
        return False
    fence = store._lock_ingest_state(conn.cursor(),[(source['chat_id'],msg_id)])[source['chat_id'],msg_id]
    if fence['observed_at'] is not None and observed_at < fence['observed_at']:
        return False
    previous = conn.execute('SELECT id,text,image_caption,image_refs,image_source FROM messages WHERE chat_id=%s AND msg_id=%s',
                            (source['chat_id'],msg_id)).fetchone()
    photos = tuple(f"photo:{normalize_id(photo['photo_id'])}" for photo in snapshot['photos'])
    sender = snapshot.get('sender_id')
    name = snapshot.get('sender_name') or (str(sender) if sender is not None else source['title'])
    message = store.Message(source['chat_id'],msg_id,None,
        datetime.fromtimestamp(normalize_id(snapshot['created_ms'])/1000,timezone.utc),None,
        sender,name,snapshot.get('reply_to'),snapshot['text'],None,
        image_source='maxuserbot' if photos else None,image_refs=photos,observed_at=observed_at,live_edit=not archive)
    store.write_batch([], [message],conn=conn)
    conn.execute("""UPDATE max_message_state SET last_received_at=%s,last_live_id=coalesce(%s,last_live_id)
        WHERE chat_id=%s AND msg_id=%s""", (observed_at,live_id,source['chat_id'],msg_id))
    current = conn.execute('SELECT id,text,image_caption,image_refs,image_source FROM messages WHERE chat_id=%s AND msg_id=%s',
                           (source['chat_id'],msg_id)).fetchone()
    if current and current != previous:
        conn.execute('INSERT INTO max_publish_queue(chat_id,msg_id) VALUES(%s,%s)',(source['chat_id'],msg_id))
        return True
    return False


def apply_snapshot(chat_id: int,snapshot: dict,*,generation: int,observed_at: datetime) -> bool:
    with _transaction() as conn:
        source = _source(conn,chat_id)
        if source['generation']!=generation or not _ready(source):
            return False
        return _snapshot(conn,source,snapshot,observed_at)


def apply_event(event_id: int) -> None:
    with _transaction() as conn:
        source,row = _event(conn,event_id)
        if not row or row['processed_at']:
            return
        payload = row['payload']
        kind = payload['kind']
        if kind=='removed':
            for msg_id in sorted(set(payload['message_ids'])):
                _delete(conn,source,msg_id,row['received_at'],row['id'])
        elif row['generation']!=source['generation'] or not _ready(source):
            pass
        elif kind=='message':
            if 'snapshot' not in payload:
                raise ProtocolError()
            if payload['snapshot'] is None:
                conn.execute("UPDATE max_sources SET last_error='message_unavailable' WHERE chat_id=%s",(source['chat_id'],))
                _finish(conn,event_id,'message_unavailable')
                return
            _snapshot(conn,source,payload['snapshot'],datetime.fromisoformat(payload['fetch_observed_at']),live_id=row['id'])
        elif kind=='invalid':
            conn.execute("UPDATE max_sources SET last_error='protocol_error' WHERE chat_id=%s",(source['chat_id'],))
            _finish(conn,event_id,'protocol_error')
            return
        elif kind=='reconcile_deleted':
            conn.execute("""UPDATE max_sources SET deletion_scan_pending=true,
                deletion_scan_after_id=CASE WHEN deletion_scan_pending THEN deletion_scan_after_id ELSE NULL END,
                deletion_scan_until_id=(SELECT max(msg_id) FROM max_message_state WHERE chat_id=%s),
                deletion_scan_available_at=now() WHERE chat_id=%s""",(source['chat_id'],source['chat_id']))
        _finish(conn,event_id)


def fail_event(event_id: int,code: str) -> None:
    with _transaction() as conn:
        source,row = _event(conn,event_id)
        if not row or row['processed_at']:
            return
        conn.execute("""UPDATE max_inbox SET attempts=attempts+1,error_code=%s,
            available_at=now()+least(power(2,least(attempts+1,9)),300)*interval '1 second' WHERE id=%s""", (_code(code),event_id))
        conn.execute('UPDATE max_sources SET last_error=%s WHERE chat_id=%s',(_code(code),source['chat_id']))


def prune_inbox() -> int:
    with _transaction() as conn:
        return conn.execute("DELETE FROM max_inbox WHERE processed_at<now()-interval '14 days'").rowcount


def next_publication() -> dict | None:
    with pg.connection() as conn:
        return conn.execute("""SELECT q.*, EXISTS(SELECT 1 FROM messages m WHERE m.chat_id=q.chat_id AND m.msg_id=q.msg_id) AS exists
            FROM max_publish_queue q WHERE q.available_at<=now() ORDER BY q.id LIMIT 1""").fetchone()


def complete_publication(id: int) -> None:
    with _transaction() as conn:
        conn.execute('DELETE FROM max_publish_queue WHERE id=%s',(id,))


def fail_publication(id: int) -> None:
    with _transaction() as conn:
        conn.execute("""UPDATE max_publish_queue SET attempts=attempts+1,
            available_at=now()+least(power(2,least(attempts+1,9)),300)*interval '1 second' WHERE id=%s""",(id,))


def prepare_recovery(until_ms: int) -> None:
    until_ms = normalize_id(until_ms)
    with _transaction() as conn:
        sources = conn.execute('SELECT * FROM max_sources WHERE enabled ORDER BY chat_id FOR UPDATE').fetchall()
        for source in sources:
            # Older enabled sources may never have requested their first archive.
            # Resume every existing full-history state without resetting its cursor.
            if source['history_status'] == 'idle':
                _history_reset(conn, source['chat_id'])
            pending = source['catchup_status'] in {'pending','running','partial','failed'}
            lower = source['catchup_after_ms'] if pending else (
                source['sync_watermark_ms']-1 if source['sync_watermark_ms'] is not None else None)
            upper = max(until_ms,source['catchup_until_ms'] or 0)
            conn.execute("""UPDATE max_sources SET catchup_status='pending',catchup_before_ms=%s,
                catchup_until_ms=%s,catchup_after_ms=%s,catchup_available_at=now() WHERE chat_id=%s""",
                (upper,upper,lower,source['chat_id']))


def advance_watermark(observed_ms: int) -> None:
    with _transaction() as conn:
        conn.execute("""UPDATE max_sources SET sync_watermark_ms=greatest(sync_watermark_ms,%s)
            WHERE enabled AND access='ready' AND catchup_status NOT IN ('pending','running','failed','partial')""",
            (normalize_id(observed_ms),))


def _history_prefix(kind):
    if kind not in {'full','catchup'}:
        raise ValueError('invalid_history_kind')
    return 'history' if kind=='full' else 'catchup'


def next_history(kind: str) -> dict | None:
    prefix = _history_prefix(kind)
    with _transaction() as conn:
        source = conn.execute(SOURCE+f""" WHERE s.enabled AND s.access='ready'
            AND s.{prefix}_status IN ('pending','running') AND s.{prefix}_available_at<=now()
            ORDER BY s.{prefix}_available_at,s.chat_id LIMIT 1 FOR UPDATE OF s""").fetchone()
        if not source:
            return None
        conn.execute(f"UPDATE max_sources SET {prefix}_status='running',{prefix}_available_at=now()+interval '1 second' WHERE chat_id=%s",(source['chat_id'],))
        source[prefix+'_status']='running'
        source['kind']=kind
        source['observed_at']=datetime.now(timezone.utc)
        return source


def _history_current(source,job):
    prefix = _history_prefix(job['kind'])
    return (_ready(source) and source['generation']==job['generation']
        and source[prefix+'_status'] in {'pending','running'}
        and source[prefix+'_before_ms']==job[prefix+'_before_ms']
        and (source['history_started_at']==job['history_started_at'] if prefix=='history'
             else source['catchup_until_ms']==job['catchup_until_ms']))


def history_current(job: dict) -> bool:
    with _transaction() as conn:
        return _history_current(_source(conn,job['chat_id']),job)


def apply_history_page(job: dict,messages: list[dict]) -> bool:
    prefix = _history_prefix(job['kind'])
    cursor = job[prefix+'_before_ms']
    if cursor is None or not isinstance(messages,list):
        raise ProtocolError()
    ids = set()
    for message in messages:
        timestamp = normalize_id(message['created_ms'])
        if not 0<=timestamp<=cursor or normalize_id(message['raw_chat_id'])!=job['raw_chat_id']:
            raise ProtocolError()
        ids.add(normalize_id(message['message_id']))
    page_size = normalize_id(job.get('page_size',len(messages)))
    oldest = normalize_id(job.get('page_oldest_ms',min((m['created_ms'] for m in messages),default=cursor)))
    if not 0<=page_size<=100 or not 0<=oldest<=cursor:
        raise ProtocolError()
    with _transaction() as conn:
        source = _source(conn,job['chat_id'])
        if not _history_current(source,job):
            return False
        lower = source['catchup_after_ms'] if prefix=='catchup' else None
        new_ids = 0
        for message in messages:
            if lower is not None and message['created_ms']<lower:
                continue
            if not conn.execute('SELECT 1 FROM max_message_state WHERE chat_id=%s AND msg_id=%s',
                                (source['chat_id'],message['message_id'])).fetchone():
                new_ids+=1
            _snapshot(conn,source,message,job['observed_at'],archive=True)
        next_cursor = min(cursor,oldest+1)
        reached = lower is not None and page_size>0 and oldest<=lower
        complete = page_size<100 or reached
        stalled = not complete and next_cursor>=cursor and new_ids==0
        status = 'complete' if complete else 'partial' if stalled else 'running'
        conn.execute(f"""UPDATE max_sources SET {prefix}_status=%s,{prefix}_before_ms=%s,
            {prefix}_available_at=now(),last_error=CASE WHEN %s THEN 'history_timestamp_boundary'
            WHEN %s AND last_error IN ('history_error','history_timestamp_boundary') THEN NULL ELSE last_error END
            WHERE chat_id=%s""",(status,next_cursor,stalled,complete,source['chat_id']))
        if prefix=='history':
            conn.execute('UPDATE max_sources SET history_last_id=%s WHERE chat_id=%s',
                         (max(ids) if ids else source['history_last_id'],source['chat_id']))
        elif complete:
            conn.execute('UPDATE max_sources SET sync_watermark_ms=catchup_until_ms WHERE chat_id=%s',(source['chat_id'],))
        return True


def fail_history(job: dict,code: str,*,terminal=False) -> None:
    prefix = _history_prefix(job['kind'])
    with _transaction() as conn:
        source = _source(conn,job['chat_id'])
        if _history_current(source,job):
            status = 'partial' if code=='history_timestamp_boundary' else 'failed' if terminal else 'running'
            conn.execute(f"""UPDATE max_sources SET {prefix}_status=%s,{prefix}_available_at=now()+interval '60 seconds',
                last_error=%s WHERE chat_id=%s""",(status,_code(code),source['chat_id']))


def next_deletion_scan() -> dict | None:
    with _transaction() as conn:
        source = conn.execute(SOURCE+""" WHERE s.enabled AND s.access='ready' AND s.deletion_scan_pending
            AND s.deletion_scan_available_at<=now() ORDER BY s.deletion_scan_available_at,s.chat_id
            LIMIT 1 FOR UPDATE OF s""").fetchone()
        if not source:
            return None
        ids = pg.column(conn,"""SELECT msg_id FROM max_message_state WHERE chat_id=%s
            AND (%s::bigint IS NULL OR msg_id>%s) AND msg_id<=%s ORDER BY msg_id LIMIT 100""",
            (source['chat_id'],source['deletion_scan_after_id'],source['deletion_scan_after_id'],source['deletion_scan_until_id']))
        if not ids:
            conn.execute('UPDATE max_sources SET deletion_scan_pending=false WHERE chat_id=%s',(source['chat_id'],))
            return None
        conn.execute("UPDATE max_sources SET deletion_scan_available_at=now()+interval '1 second' WHERE chat_id=%s",(source['chat_id'],))
        source['ids']=ids
        source['observed_at']=datetime.now(timezone.utc)
        return source


def _scan_current(source,job):
    return (_ready(source) and source['generation']==job['generation'] and source['deletion_scan_pending']
        and source['deletion_scan_after_id']==job['deletion_scan_after_id']
        and source['deletion_scan_until_id']==job['deletion_scan_until_id'])


def deletion_scan_current(job: dict) -> bool:
    with _transaction() as conn:
        return _scan_current(_source(conn,job['chat_id']),job)


def apply_deletion_scan(job: dict,snapshots: list[dict],returned_ids: list[int]) -> None:
    with _transaction() as conn:
        source = _source(conn,job['chat_id'])
        if not _scan_current(source,job):
            return
        for snapshot in snapshots:
            if snapshot['message_id'] not in job['ids'] or snapshot['raw_chat_id']!=source['raw_chat_id']:
                raise ProtocolError()
            if snapshot['deleted']:
                _delete(conn,source,snapshot['message_id'],job['observed_at'])
        missing = bool(set(job['ids'])-set(returned_ids))
        conn.execute("""UPDATE max_sources SET deletion_scan_after_id=%s,
            deletion_scan_pending=%s,deletion_scan_available_at=now(),
            last_error=CASE WHEN %s THEN 'deletion_reconciliation_partial' ELSE last_error END WHERE chat_id=%s""",
            (max(job['ids']),max(job['ids'])<source['deletion_scan_until_id'],missing,source['chat_id']))


def fail_deletion_scan(job: dict) -> None:
    with _transaction() as conn:
        source = _source(conn,job['chat_id'])
        if _scan_current(source,job):
            conn.execute("""UPDATE max_sources SET deletion_scan_available_at=now()+interval '60 seconds',
                last_error='deletion_reconciliation_partial' WHERE chat_id=%s""",(source['chat_id'],))
