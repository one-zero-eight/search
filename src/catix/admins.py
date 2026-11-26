"""cAtIx admins by InNoHassle id: they configure sources on the site (/search/admin), and the alerts go to their Telegram.

Two sources: ADMIN_INNOHASSLE_IDS, which only a restart changes, and the admins added on the site, kept in the database.
"""

import re
from dataclasses import dataclass
from datetime import datetime

from catix.db import pg
from catix.settings import settings

ID_RE = re.compile(r"^[0-9a-f]{24}$")  # InNoHassle ids are Mongo ObjectIds


@dataclass(frozen=True, slots=True)
class Admin:
    innohassle_id: str
    email: str | None
    telegram_id: int | None
    fixed: bool  # from ADMIN_INNOHASSLE_IDS: cannot be removed on the site
    added_by: str | None
    added_at: datetime | None


def configured() -> list[str]:
    return settings.admin_innohassle_ids


def is_admin(innohassle_id: str) -> bool:
    if innohassle_id in configured():
        return True
    with pg.connection() as conn:
        row = conn.execute("SELECT 1 FROM admins WHERE innohassle_id = %s AND added_by IS NOT NULL", (innohassle_id,)).fetchone()
    return row is not None


def listing() -> list[Admin]:
    with pg.connection() as conn:
        rows = conn.execute("SELECT innohassle_id, added_by, added_at, email, telegram_id FROM admins ORDER BY added_at").fetchall()
    by_id = {row["innohassle_id"]: row for row in rows}
    fixed = configured()
    result = []
    for innohassle_id in dict.fromkeys(fixed):
        row = by_id.get(innohassle_id)
        result.append(Admin(innohassle_id, row["email"] if row else None, row["telegram_id"] if row else None, True, None, None))
    result.extend(
        Admin(row["innohassle_id"], row["email"], row["telegram_id"], False, row["added_by"], row["added_at"])
        for row in rows
        if row["innohassle_id"] not in fixed and row["added_by"] is not None
    )
    return result


def add(innohassle_id: str, by: str) -> bool:
    """False if they already were an admin."""
    if is_admin(innohassle_id):
        return False
    with pg.connection() as conn:
        conn.execute(
            "INSERT INTO admins (innohassle_id, added_by) VALUES (%s, %s) "
            "ON CONFLICT (innohassle_id) DO UPDATE SET added_by = excluded.added_by, added_at = now()",
            (innohassle_id, by),
        )
    return True


def remove(innohassle_id: str) -> bool:
    """False if they are not among the admins added on the site (the configured ones stay)."""
    with pg.connection() as conn:
        return conn.execute("DELETE FROM admins WHERE innohassle_id = %s AND added_by IS NOT NULL", (innohassle_id,)).rowcount > 0


def seen(innohassle_id: str, email: str | None, telegram_id: int | None) -> None:
    """Copy the contacts from the admin's own token (the alerts go to telegram_id)."""
    with pg.connection() as conn:
        conn.execute(
            "INSERT INTO admins (innohassle_id, email, telegram_id) VALUES (%s, %s, %s) "
            "ON CONFLICT (innohassle_id) DO UPDATE SET email = excluded.email, telegram_id = excluded.telegram_id",
            (innohassle_id, email, telegram_id),
        )


def telegram_ids() -> list[int]:
    fixed = configured()
    with pg.connection() as conn:
        rows = conn.execute(
            "SELECT telegram_id FROM admins WHERE telegram_id IS NOT NULL AND (added_by IS NOT NULL OR innohassle_id = ANY(%s)) ORDER BY added_at",
            (fixed,),
        ).fetchall()
    return list(dict.fromkeys([*settings.admin_telegram_ids, *(row["telegram_id"] for row in rows)]))
