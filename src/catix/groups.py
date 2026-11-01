"""Study groups of chats and of users: who sees what.

Every chat belongs to one group (a code like B26-CSE-01) and starts in `all`. The person who made the bot an admin
of a chat sets the group in a private chat with the bot (`/group`), never in the group itself. A user can pick the
group whose chats they want answers from (`/mygroup`). A user of group `all` (the default) is answered from the chats of group
`all` only; a user of another group from the chats of `all` and of their own group. A chat of a group is never searched for a
user of another group, and the model cannot change that: the scope is worked out here, in code, from the user's key.
Both bots use this module; only the admin check (is this user an admin of that chat?) differs by messenger.
"""

import logging
import re
import time

from catix.innohassle import client as innohassle
from catix.db import pg
from catix.settings import settings
from catix.db.rows import ChatGroup

log = logging.getLogger("catix.groups")

ALL = "all"
MAX_CHAT_BASE = 2 * 10**15  # Max chat ids are stored shifted by this, so they never collide with Telegram ids.
CODE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$")

USAGE_GROUP = (
    "Чтобы указать группу чата, напишите: /group номер группа\n"
    f"Например: /group 2 B26-CSE-01. Группа {ALL} значит «для всех»."
)


def normalize(code: str) -> str | None:
    """`all` in lower case, other codes in upper case (B26-cse-01 = B26-CSE-01); None if it is not a valid code."""
    code = code.strip()
    if not CODE_RE.match(code):
        return None
    return ALL if code.lower() == ALL else code.upper()


def list_chats(platform: str) -> list[ChatGroup]:
    """Chats of one messenger the bot knows, in a stable order (the numbers in /group refer to this order)."""
    condition = "chat_id >= %s" if platform == "max" else "bot_member AND chat_id < %s"
    with pg.connection() as conn:
        return pg.rows(
            conn,
            ChatGroup,
            f"SELECT chat_id, title, group_code FROM chats WHERE {condition} ORDER BY title, chat_id",  # noqa: S608
            (MAX_CHAT_BASE // 2,),
        )


def set_chat_group(chat_id: int, code: str) -> None:
    with pg.connection() as conn:
        conn.execute("UPDATE chats SET group_code = %s WHERE chat_id = %s", (code, chat_id))


AUTO_TTL = 3600.0  # A found group is trusted for an hour,
AUTO_MISS_TTL = 600.0  # a miss (not registered, no token) is asked again after ten minutes.
_auto: dict[int, tuple[float, str | None]] = {}
_warned_token = False


def auto_group(telegram_id: int | None) -> str | None:
    """The user's study group from InNoHassle by Telegram id, cached; None if unknown (then /mygroup decides)."""
    global _warned_token
    if telegram_id is None or not settings.innohassle_groups or not settings.innohassle_service_token:
        return None
    hit = _auto.get(telegram_id)
    if hit and time.monotonic() < hit[0]:
        return hit[1]
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
    _auto[telegram_id] = (time.monotonic() + ttl, group)
    return group


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


def scoped_chat_ids(user_key: str, telegram_id: int | None = None) -> set[int]:
    """Chats a user's answers may come from: those of group `all` and of the user's own group (for `all`: only the first)."""
    group = effective_group(user_key, telegram_id)
    with pg.connection() as conn:
        return set(pg.column(conn, "SELECT chat_id FROM chats WHERE group_code IN (%s, %s)", (ALL, group)))


def group_command(args: str, admin_chats: list[ChatGroup]) -> str:
    """Reply to `/group [number group]` from a user who is admin of `admin_chats` (already filtered and ordered)."""
    parts = args.split()
    if not admin_chats:
        return (
            "Я не нашёл чатов, где вы администратор и где есть я. Добавьте меня в чат, сделайте администратором "
            "и напишите там любое сообщение, а затем повторите /group здесь."
        )
    if len(parts) != 2 or not parts[0].isdigit() or not 1 <= int(parts[0]) <= len(admin_chats):
        lines = [f"{i}. {c.title}: группа {c.group_code}" for i, c in enumerate(admin_chats, 1)]
        return "Ваши чаты:\n" + "\n".join(lines) + "\n\n" + USAGE_GROUP
    code = normalize(parts[1])
    if not code:
        return "Группа: латиница, цифры, точка, дефис и подчёркивание, до 40 символов, например B26-CSE-01."
    chat = admin_chats[int(parts[0]) - 1]
    set_chat_group(chat.chat_id, code)
    return f"Готово: чат «{chat.title}» теперь в группе {code}."


def manual_group_allowed(is_admin: bool) -> bool:
    """Choosing a group by hand (`/mygroup`) is open while groups are not taken from InNoHassle (INNOHASSLE_GROUPS off).
    With them on, it is closed for everybody but the admins until the service token is set: without it nobody can check
    the group a person names, so it would only be a claim."""
    return is_admin or not settings.innohassle_groups or settings.innohassle_service_token is not None


def mygroup_command(args: str, user_key: str, telegram_id: int | None = None, *, may_set: bool = True) -> str:
    """Reply to `/mygroup [group]`. A group InNoHassle knows cannot be changed by hand."""
    if known := auto_group(telegram_id):
        return f"Ваша группа определена по InNoHassle: {known}. Я ищу в её чатах и в общих; изменить вручную нельзя."
    if not may_set:
        return (
            "Выбор группы вручную сейчас закрыт: она будет определяться автоматически по InNoHassle. "
            f"Пока я ищу только в общих чатах (группа {ALL})."
        )
    if not args.strip():
        return (
            f"Ваша группа: {user_group(user_key)}. Чтобы изменить: /mygroup B26-CSE-01. "
            f"{ALL}: только общие чаты (группа {ALL})."
        )
    code = normalize(args)
    if not code:
        return "Группа: латиница, цифры, точка, дефис и подчёркивание, до 40 символов, например B26-CSE-01."
    set_user_group(user_key, code)
    return f"Ваша группа: {code}. " + (f"Ищу только в общих чатах (группа {ALL})." if code == ALL else f"Ищу в чатах группы {code} и общих.")
