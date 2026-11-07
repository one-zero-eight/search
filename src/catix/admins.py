"""Admins of the bot: who sets up /listen and gets the alerts.

Two sources: ADMIN_TELEGRAM_IDS, which only a restart changes, and the
admins added by another admin in the bot (/admin, tgbot/admin.py), kept in the database.
"""

from catix.db import pg
from catix.settings import settings


def configured() -> list[int]:
    """Admins from the settings; they cannot be removed in the bot."""
    return settings.admin_telegram_ids


def added() -> list[int]:
    with pg.connection() as conn:
        return pg.column(conn, "SELECT telegram_id FROM bot_admins ORDER BY added_at")


def everyone() -> list[int]:
    return list(dict.fromkeys([*configured(), *added()]))


def add(telegram_id: int, by: int) -> bool:
    """False if they already were an admin."""
    if telegram_id in everyone():
        return False
    with pg.connection() as conn:
        conn.execute("INSERT INTO bot_admins (telegram_id, added_by) VALUES (%s, %s) ON CONFLICT DO NOTHING", (telegram_id, by))
    return True


def remove(telegram_id: int) -> bool:
    """False if they are not among the admins added in the bot (the configured ones stay)."""
    with pg.connection() as conn:
        return conn.execute("DELETE FROM bot_admins WHERE telegram_id = %s", (telegram_id,)).rowcount > 0
