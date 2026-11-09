"""Study groups of chats and of users: who sees what.

Every chat belongs to one group (a code like B26-CSE-01) and starts in `all`. Administrators configure
chat groups through the bot; users configure their study group on the website.
A user of group `all` (the default) is answered from the chats of group
`all` only; a user of another group from the chats of `all` and of their own group. A chat of a group is never searched for a
user of another group, and the model cannot change that: the scope is worked out here, in code, from the user's key.
Telegram administration configures both Telegram and passive MAX account sources.
"""

import logging
import re

import httpx

from catix.common import cache
from catix.innohassle import client as innohassle
from catix.db import pg
from catix.settings import settings

log = logging.getLogger("catix.groups")

ALL = "all"
MAX_CHAT_BASE = 2 * 10**15  # Legacy MAX Bot API archive namespace; userbot identities use a separate base.
CODE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$")



def normalize(code: str) -> str | None:
    """`all` in lower case, other codes in upper case (B26-cse-01 = B26-CSE-01); None if it is not a valid code."""
    code = code.strip()
    if not CODE_RE.match(code):
        return None
    return ALL if code.lower() == ALL else code.upper()




def set_chat_group(chat_id: int, code: str) -> None:
    with pg.connection() as conn:
        conn.execute("UPDATE chats SET group_code = %s WHERE chat_id = %s", (code, chat_id))


AUTO_TTL = 3600.0  # A found group is trusted for an hour,
AUTO_MISS_TTL = 600.0  # a miss (not registered, no token) is asked again after ten minutes.
_warned_token = False


def auto_group(telegram_id: int | None) -> str | None:
    """The user's study group from InNoHassle by Telegram id, cached; None if unknown."""
    global _warned_token
    if telegram_id is None or not settings.innohassle_groups or not settings.innohassle_service_token:
        return None
    key = f"group:tg:{telegram_id}"
    found, kept = cache.get(key)
    if found:
        return kept
    group: str | None = None
    try:
        raw = innohassle.study_group_by_telegram_id(telegram_id)
        group = normalize(raw) if raw else None
        if raw and not group:
            log.warning("InNoHassle group %r of telegram id %s is not a usable group code", raw, telegram_id)
        ttl = AUTO_TTL if group else AUTO_MISS_TTL
    except innohassle.ServiceTokenError as e:
        if not _warned_token:
            log.warning("cannot look up groups: %s", e)
            _warned_token = True
        ttl = AUTO_MISS_TTL
    except Exception:  # noqa: BLE001 - InNoHassle being down must not break answering
        log.exception("group lookup for telegram id %s failed", telegram_id)
        ttl = 60.0
    return cache.put(key, group, ttl)


def website_groups(token: str | None) -> list[str]:
    """Fresh verified memberships for the website; no Telegram or manual fallback."""
    if not token:
        return []
    try:
        return innohassle.my_student_groups(token)
    except (httpx.HTTPError, innohassle.ServiceError, ValueError):
        # Upstream diagnostics may contain credentials or private response bodies.
        log.warning("Website study group verification unavailable; group sources denied")
        return []


def effective_group(user_key: str, telegram_id: int | None = None) -> str:
    """What decides where the user may search: the group InNoHassle knows, else the one they chose, else `all`."""
    return auto_group(telegram_id) or user_group(user_key)


def user_group(user_key: str) -> str:
    with pg.connection() as conn:
        group = pg.scalar(conn, "SELECT group_code FROM user_groups WHERE user_key = %s", (user_key,))
    return group or ALL


def set_user_group(user_key: str, code: str) -> None:
    with pg.connection() as conn:
        conn.execute(
            """INSERT INTO user_groups (user_key, group_code) VALUES (%s, %s)
               ON CONFLICT (user_key) DO UPDATE SET group_code = excluded.group_code""",
            (user_key, code),
        )


def website_chat_ids(verified_groups: list[str]) -> set[int]:
    """Website access uses verified memberships only, including legacy group chats."""
    with pg.connection() as conn:
        return set(pg.column(conn,
            """SELECT chat_id FROM chats
               WHERE NOT max_legacy_archived
                 AND ((group_code = 'all' AND NOT requires_verified_group)
                      OR (group_code <> 'all' AND group_code = ANY(%s)))""", (verified_groups,)))


def scoped_chat_ids(user_key: str, telegram_id: int | None = None) -> set[int]:
    """Legacy chats keep manual fallback. Requested private sources require a verified, matching study group."""
    verified = auto_group(telegram_id)
    group = verified or user_group(user_key)
    with pg.connection() as conn:
        return set(pg.column(conn,
            """SELECT chat_id FROM chats WHERE NOT max_legacy_archived AND group_code IN (%s, %s)
               AND (NOT requires_verified_group OR (group_code <> 'all' AND group_code = %s))""", (ALL, group, verified)))




