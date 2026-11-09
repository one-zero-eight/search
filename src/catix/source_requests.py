"""Durable, moderated chat source requests. Never log invitations or exception payloads."""
import re
import uuid

from psycopg.errors import UniqueViolation

from catix import groups, userbot_config
from catix.db import pg

INVITE_RE = re.compile(r"(?:https://)?t\.me/(?:\+|joinchat/)([A-Za-z0-9_-]{16,128})", re.ASCII)
PUBLIC_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{3,30}[A-Za-z0-9]", re.ASCII)
MAX_LINK_RE = re.compile(r"(?:https://)?max\.ru/((?:join/)?[A-Za-z0-9_-]{1,128})", re.ASCII)
RESERVED_USERNAMES = frozenset({
    "joinchat", "share", "proxy", "socks", "login", "confirmphone", "setlanguage",
    "addstickers", "addemoji", "addtheme", "bg", "invoice", "giftcode", "addlist",
    "boost", "contact",
})


class RateLimited(ValueError):
    """Five new requests per account per rolling day; deduplicated retries cost nothing."""


class ExistingRequest(ValueError):
    """An already terminal request needs manual review or a new invitation, not a silent replay."""


def invite_hash(link: str) -> str:
    match = INVITE_RE.fullmatch(link)
    if not match:
        raise ValueError("Use a private https://t.me/+… or https://t.me/joinchat/… invitation")
    return match[1]


def public_username(link: str) -> str | None:
    """Return a canonical public username, or None for an accepted private invite."""
    if not isinstance(link, str):
        raise ValueError("Use a Telegram t.me public username or private invitation")
    if INVITE_RE.fullmatch(link):
        return None
    match = re.fullmatch(r"(?:https://)?t\.me/([^/?#]+)", link, re.ASCII)
    if not match:
        raise ValueError("Use a Telegram t.me public username or private invitation")
    username = match[1]
    if not PUBLIC_RE.fullmatch(username) or username.lower() in RESERVED_USERNAMES:
        raise ValueError("Telegram public link must contain a valid, non-reserved username")
    return username.lower()


def normalize_link(link: str) -> str:
    """Validate the entire submitted link and return its canonical HTTPS URL."""
    if isinstance(link, str):
        link = link.strip()
        if match := MAX_LINK_RE.fullmatch(link):
            if match[1] != "join":
                return f"https://max.ru/{match[1]}"
    username = public_username(link)
    if username is not None:
        return f"https://t.me/{username}"
    match = INVITE_RE.fullmatch(link)
    assert match is not None
    return f"https://t.me/+{match[1]}"


def submit(owner: str, email: str, invite_link: str, group_code: str, comment: str = "", *, consent: bool) -> dict:
    link = normalize_link(invite_link)
    code = groups.normalize(group_code)
    if not code:
        raise ValueError("A valid study group or all is required")
    if consent is not True:
        raise ValueError("Explicit consent is required")
    if len(comment) > 2000:
        raise ValueError("Comment is too long")
    with pg.connection() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 8173))", (owner,))
        existing = conn.execute("SELECT * FROM source_requests WHERE owner = %s AND invite_link = %s", (owner, link)).fetchone()
        if existing:
            if existing["status"] in ("rejected", "failed"):
                raise ExistingRequest("The existing request was rejected or failed. Contact an administrator or submit a new invitation.")
            return existing
        if pg.scalar(conn, "SELECT count(*) FROM source_requests WHERE owner = %s AND created_at > now() - interval '1 day'", (owner,)) >= 5:
            raise RateLimited("At most five new requests per day")
        return conn.execute(
            """INSERT INTO source_requests (id, owner, email, invite_link, group_code, comment, consented_at)
               VALUES (%s, %s, %s, %s, %s, %s, now())
               ON CONFLICT (owner, invite_link) DO UPDATE SET owner = excluded.owner RETURNING *""",
            (uuid.uuid4().hex, owner, email, link, code, comment),
        ).fetchone()


def list_owned(owner: str) -> list[dict]:
    with pg.connection() as conn:
        return conn.execute("SELECT * FROM source_requests WHERE owner = %s ORDER BY created_at DESC, id", (owner,)).fetchall()


def pending_requests(offset: int = 0, limit: int = 8) -> list[dict]:
    with pg.connection() as conn:
        return conn.execute(
            "SELECT * FROM source_requests WHERE status = 'pending' ORDER BY created_at, id OFFSET %s LIMIT %s",
            (max(0, offset), min(100, max(1, limit))),
        ).fetchall()


def get_request(id: str) -> dict | None:
    with pg.connection() as conn:
        return conn.execute("SELECT * FROM source_requests WHERE id = %s", (id,)).fetchone()


def approve(id: str, admin_id: int, group_code: str) -> bool:
    code = groups.normalize(group_code)
    if not code:
        raise ValueError("A valid study group or all is required")
    with pg.connection() as conn:
        if code == groups.ALL:
            current = conn.execute(
                "SELECT group_code FROM source_requests WHERE id = %s AND status = 'pending' FOR UPDATE", (id,),
            ).fetchone()
            if current and current["group_code"] != groups.ALL:
                raise ValueError("A group-only request cannot be made public without a new public-audience request")
        return conn.execute(
            """UPDATE source_requests SET status = 'approved', group_code = %s, decided_by = %s, decided_at = now()
               WHERE id = %s AND status = 'pending'""", (code, admin_id, id),
        ).rowcount == 1


def reject(id: str, admin_id: int, reason: str) -> bool:
    with pg.connection() as conn:
        return conn.execute(
            """UPDATE source_requests SET status = 'rejected', message = %s, decided_by = %s, decided_at = now()
               WHERE id = %s AND status = 'pending'""", (reason[:2000], admin_id, id),
        ).rowcount == 1


LEASE_SECONDS = 120  # Worker RPC deadline is shorter; crashes only resume by reconciliation.


def claim(messenger: str = "telegram") -> dict | None:
    if messenger not in {"telegram", "max"}:
        raise ValueError("Unknown messenger")
    with pg.connection() as conn:
        lease = conn.execute(
            """SELECT * FROM source_request_lease WHERE singleton AND available_at <= now()
               AND (lease_until IS NULL OR lease_until < now()) FOR UPDATE SKIP LOCKED""",
        ).fetchone()
        if not lease:
            return None
        job = conn.execute(
            """SELECT * FROM source_requests WHERE status IN ('approved', 'joining', 'waiting_join')
               AND available_at <= now() AND (lease_until IS NULL OR lease_until < now())
               AND starts_with(invite_link, %s)
               ORDER BY available_at, created_at, id FOR UPDATE SKIP LOCKED LIMIT 1""",
            ("https://max.ru/" if messenger == "max" else "https://t.me/",),
        ).fetchone()
        if not job:
            return None
        token = uuid.uuid4().hex
        conn.execute("UPDATE source_request_lease SET token = %s, lease_until = now() + %s * interval '1 second' WHERE singleton", (token, LEASE_SECONDS))
        return conn.execute(
            """UPDATE source_requests SET status = 'joining', token = %s, lease_until = now() + %s * interval '1 second'
               WHERE id = %s RETURNING *""", (token, LEASE_SECONDS, job["id"]),
        ).fetchone()


def _owned(conn, job: dict) -> dict | None:
    lease = conn.execute(
        "SELECT token FROM source_request_lease WHERE singleton AND token = %s AND lease_until > now() FOR UPDATE", (job["token"],),
    ).fetchone()
    if not lease:
        return None
    return conn.execute(
        """SELECT * FROM source_requests WHERE id = %s AND token = %s AND lease_until > now()
           AND status = 'joining' FOR UPDATE""", (job["id"], job["token"]),
    ).fetchone()


def begin_join(job: dict) -> bool:
    """Commit account-wide invite intent BEFORE the write, under the independent lease."""
    with pg.connection() as conn:
        current = _owned(conn, job)
        if not current or current["join_started_at"] is not None:
            return False
        created = conn.execute(
            """INSERT INTO source_request_join_intents (invite_link) VALUES (%s)
               ON CONFLICT DO NOTHING RETURNING started_at""", (current["invite_link"],),
        ).fetchone()
        conn.execute(
            """UPDATE source_requests SET join_started_at =
               (SELECT started_at FROM source_request_join_intents WHERE invite_link = %s)
               WHERE id = %s""", (current["invite_link"], current["id"]),
        )
        return created is not None


def _release(conn, job: dict) -> None:
    conn.execute("UPDATE source_request_lease SET token = NULL, lease_until = NULL WHERE singleton AND token = %s", (job["token"],))


def defer(job: dict, message: str, *, delay: int = 300, failed: bool = False, flood: bool = False, join_refused: bool = False) -> bool:
    with pg.connection() as conn:
        current = _owned(conn, job)
        if not current:
            return False
        if join_refused:
            conn.execute(
                "DELETE FROM source_request_join_intents WHERE invite_link = %s AND started_at = %s",
                (current["invite_link"], current["join_started_at"]),
            )
        started = None if join_refused else current["join_started_at"]
        status = "failed" if failed else ("waiting_join" if started else "approved")
        conn.execute(
            """UPDATE source_requests SET status = %s, message = %s, available_at = now() + %s * interval '1 second',
               join_started_at = %s, token = NULL, lease_until = NULL WHERE id = %s""",
            (status, message, max(1, delay), started, job["id"]),
        )
        if flood:
            conn.execute("UPDATE source_request_lease SET available_at = now() + %s * interval '1 second' WHERE singleton", (max(1, delay),))
        _release(conn, job)
        return True


def activate(job: dict, chat_id: int, title: str, username: str | None, forum: bool) -> bool:
    """Publish access policy and listener choice in ONE transaction, before any messages can be ingested."""
    with pg.connection() as conn:
        current = _owned(conn, job)
        if not current:
            return False
        try:
            with conn.transaction():  # Savepoint: a legacy listener conflict must undo the new chat too.
                conn.execute(
                    "INSERT INTO chats (chat_id, title, username, group_code, requires_verified_group) VALUES (%s, %s, %s, %s, %s)",
                    (chat_id, title, username, current["group_code"], current["group_code"] != groups.ALL),
                )
                conn.execute(
                    """INSERT INTO userbot_listen (chat_id, topic_ids, reader, topic_policy)
                       VALUES (%s, NULL, 'userbot', '{"default":"store","topics":{}}'::jsonb)""", (chat_id,),
                )
        except UniqueViolation:
            conn.execute(
                """UPDATE source_requests SET status = 'failed', message = %s, token = NULL, lease_until = NULL
                   WHERE id = %s""", ("Chat already configured; manual review required. Existing access was not changed.", job["id"]),
            )
            _release(conn, job)
            return False
        conn.execute(
            """INSERT INTO userbot_dialogs (chat_id, title, username, kind, forum) VALUES (%s, %s, %s, 'group', %s)
               ON CONFLICT (chat_id) DO UPDATE SET title = excluded.title, username = excluded.username, forum = excluded.forum""",
            (chat_id, title, username, forum),
        )

        conn.execute(
            """UPDATE source_requests SET status = 'connected', title = %s, chat_id = %s, message = %s,
               backfill_pending = true, token = NULL, lease_until = NULL WHERE id = %s""",
            (title, chat_id, "Source enabled for search; history is being indexed.", job["id"]),
        )
        _release(conn, job)
    userbot_config._forget()
    return True


def activate_max(job: dict, chat: dict, membership: dict) -> bool:
    """Enable only a confirmed MAX bot membership, preserving configured audiences."""
    from catix.maxbot import state

    if (chat.get("type") not in {"chat", "channel"} or chat.get("status") != "active"
            or membership.get("is_admin") is not True
            or "read_all_messages" not in (membership.get("permissions") or [])):
        return False
    try:
        link = normalize_link(chat.get("link"))
    except ValueError:
        return False
    if link != job["invite_link"]:
        return False
    with pg.connection() as conn:
        current = _owned(conn, job)
        if not current:
            return False
        source = state._discover(conn, chat["chat_id"], chat["type"])
        pristine = (not source["enabled"] and source["config_version"] == 0
                    and source["history_status"] == "idle" and source["group_code"] == groups.ALL
                    and source["requires_verified_group"])
        same_audience = (source["group_code"] == current["group_code"]
                         and source["requires_verified_group"] == (current["group_code"] != groups.ALL))
        if not pristine and not same_audience:
            conn.execute("""UPDATE source_requests SET status = 'failed', message = %s,
                            token = NULL, lease_until = NULL WHERE id = %s""",
                         ("Chat already configured; manual review required. Existing access was not changed.", job["id"]))
            _release(conn, job)
            return False
        conn.execute("""UPDATE chats SET title = %s, link = %s, group_code = %s, requires_verified_group = %s
                        WHERE chat_id = %s""",
                     (chat.get("title") or str(chat["chat_id"]), None if "/join/" in link else link, current["group_code"],
                      current["group_code"] != groups.ALL, source["chat_id"]))
        conn.execute("""UPDATE max_sources SET enabled = true, access = 'ready', generation = generation + 1,
                        config_version = config_version + 1, checked_at = now(), metadata_pending = false,
                        last_error = NULL WHERE chat_id = %s""", (source["chat_id"],))
        state._history_reset(conn, source["chat_id"])
        conn.execute("""UPDATE source_requests SET status = 'connected', title = %s, chat_id = %s,
                        message = %s, backfill_pending = true, token = NULL, lease_until = NULL WHERE id = %s""",
                     (chat.get("title"), source["chat_id"], "Source enabled for search; history is being indexed.", job["id"]))
        _release(conn, job)
        return True


def backfill_pending(messenger: str = "telegram") -> set[int]:
    with pg.connection() as conn:
        return set(pg.column(conn, """SELECT chat_id FROM source_requests WHERE status = 'connected' AND backfill_pending
                            AND starts_with(invite_link, %s)""",
                             ("https://max.ru/" if messenger == "max" else "https://t.me/",)))


def backfill_done(chat_id: int) -> None:
    with pg.connection() as conn:
        conn.execute("UPDATE source_requests SET backfill_pending = false WHERE chat_id = %s AND status = 'connected'", (chat_id,))
