"""Durable owner-scoped credentials for read-only AI Calendar subscriptions."""

import re
import secrets

from catix.db import pg

_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43}$")


def valid_key_shape(key: str | None) -> bool:
    return isinstance(key, str) and _KEY_PATTERN.fullmatch(key) is not None


def get_key(owner: str) -> str | None:
    with pg.connection() as conn:
        return pg.scalar(conn, "SELECT access_key FROM calendar_export_keys WHERE user_key = %s AND revoked_at IS NULL", (owner,))


def create_key(owner: str) -> str:
    """Atomically retrieve an active key or replace a revoked key with a fresh random one."""
    candidate = secrets.token_urlsafe(32)
    with pg.connection() as conn:
        return pg.scalar(
            conn,
            """INSERT INTO calendar_export_keys (user_key, access_key)
               VALUES (%s, %s)
               ON CONFLICT (user_key) DO UPDATE SET
                 access_key = CASE WHEN calendar_export_keys.revoked_at IS NULL
                                   THEN calendar_export_keys.access_key ELSE EXCLUDED.access_key END,
                 revoked_at = NULL
               RETURNING access_key""",
            (owner, candidate),
        )


def revoke_key(owner: str) -> None:
    with pg.connection() as conn:
        conn.execute("UPDATE calendar_export_keys SET revoked_at = now() WHERE user_key = %s AND revoked_at IS NULL", (owner,))


def owner_for_key(key: str) -> str | None:
    if not valid_key_shape(key):
        return None
    with pg.connection() as conn:
        return pg.scalar(conn, "SELECT user_key FROM calendar_export_keys WHERE access_key = %s AND revoked_at IS NULL", (key,))
