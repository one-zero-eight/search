"""What is listened to in Telegram: chats and forum topics, chosen by an admin in the bot (tgbot/listen.py).

Two readers share the choice. The userbot (tguserbot/userbot.py, an account that is a member of the chats) publishes the
chats and topics it can see and stores what a chosen chat says, history included. The Bot API bot (tgbot/bot.py) discovers
the chats it joins, but neither reader stores a new chat until an admin confirms its configuration.
The userbot publishes the chats and topics it can see; the admin turns chats on and off and
narrows a forum chat to some of its topics; the userbot picks the change up within seconds. The study group of a
chat is not kept here, it stays `chats.group_code` (groups.py).
TG_CHATS and TG_TOPICS from .env are copied here once (`seed`), after that this table is the truth.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from psycopg.types.json import Jsonb

from catix import groups
from catix.common import cache
from catix.db import pg
from catix.groups import MAX_CHAT_BASE
from catix.settings import settings

CACHE_TTL = 10.0  # Seconds: `topic_allowed` runs for every stored message. A change made here is seen at once (`_forget`).


@dataclass(frozen=True, slots=True)
class Dialog:
    chat_id: int
    title: str
    kind: str
    username: str | None
    forum: bool
    bot_only: bool = False  # Only the Bot API bot is in this chat, the userbot's account is not.
    bot_in: bool = False  # The Bot API bot is in this chat (alone or with the userbot's account).


@dataclass(frozen=True, slots=True)
class Topic:
    topic_id: int
    title: str
    closed: bool


# The chats of the userbot, then those only the Bot API bot is in (not Max chats, they have their own bot).
_DIALOGS = """
    SELECT d.chat_id, d.title, d.kind, d.username, d.forum, false AS bot_only,
           EXISTS (SELECT 1 FROM chats c WHERE c.chat_id = d.chat_id AND c.bot_member) AS bot_in
    FROM userbot_dialogs d
    UNION ALL
    SELECT c.chat_id, c.title, 'group', c.username, false, true, true FROM chats c
    WHERE c.bot_member AND c.chat_id < %(max)s AND NOT EXISTS (SELECT 1 FROM userbot_dialogs d WHERE d.chat_id = c.chat_id)
"""


def dialogs() -> list[Dialog]:
    with pg.connection() as conn:
        return pg.rows(conn, Dialog, f"SELECT * FROM ({_DIALOGS}) x ORDER BY lower(title), chat_id", {"max": MAX_CHAT_BASE // 2})  # noqa: S608


def dialog(chat_id: int) -> Dialog | None:
    with pg.connection() as conn:
        return pg.row(conn, Dialog, f"SELECT * FROM ({_DIALOGS}) x WHERE chat_id = %(chat)s", {"max": MAX_CHAT_BASE // 2, "chat": chat_id})  # noqa: S608


def userbot_chat_ids() -> set[int]:
    """The chats the userbot's account is in (only those can be read by it)."""
    with pg.connection() as conn:
        return set(pg.column(conn, "SELECT chat_id FROM userbot_dialogs"))


def topics(chat_id: int) -> list[Topic]:
    with pg.connection() as conn:
        return pg.rows(conn, Topic, "SELECT topic_id, title, closed FROM userbot_topics WHERE chat_id = %s ORDER BY topic_id", (chat_id,))


def replace_dialogs(found: list[Dialog]) -> None:
    """The userbot's current chats; the ones it no longer sees disappear from the list (and from the topics)."""
    with pg.connection() as conn, conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO userbot_dialogs (chat_id, title, kind, username, forum, refreshed_at) VALUES (%s, %s, %s, %s, %s, now())
               ON CONFLICT (chat_id) DO UPDATE SET title = excluded.title, kind = excluded.kind, username = excluded.username,
                   forum = excluded.forum, refreshed_at = excluded.refreshed_at""",
            [(d.chat_id, d.title, d.kind, d.username, d.forum) for d in found],
        )
        ids = [d.chat_id for d in found]
        cur.execute("DELETE FROM userbot_dialogs WHERE NOT chat_id = ANY(%s::bigint[])", (ids,))
        cur.execute("DELETE FROM userbot_topics WHERE NOT chat_id = ANY(%s::bigint[])", (ids,))
    _forget()


def replace_topics(chat_id: int, found: list[Topic]) -> None:
    with pg.connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM userbot_topics WHERE chat_id = %s", (chat_id,))
        cur.executemany(
            "INSERT INTO userbot_topics (chat_id, topic_id, title, closed) VALUES (%s, %s, %s, %s)",
            [(chat_id, t.topic_id, t.title, t.closed) for t in found],
        )


# ---- what is listened to ------------------------------------------------------------------------------------


READERS = ("auto", "userbot", "bot", "search")
MODES = ("store", "search", "off")


def _rows() -> dict[int, tuple]:
    with pg.connection() as conn:
        found = conn.execute("SELECT chat_id, topic_ids, reader, topic_policy FROM userbot_listen").fetchall()
    return {r["chat_id"]: (r["topic_ids"], r["reader"], r["topic_policy"]) for r in found}


def _policy(row: tuple | list) -> dict:
    """NULL policy keeps the old storage whitelist and unrestricted live search."""
    if len(row) > 2 and row[2] is not None:
        policy = {"default": row[2]["default"], "topics": {int(t): mode for t, mode in row[2]["topics"].items()}}
        if row[1] == "search":
            policy["default"] = "search" if policy["default"] == "store" else policy["default"]
            policy["topics"] = {t: "search" if mode == "store" else mode for t, mode in policy["topics"].items()}
        return policy
    scope, reader = row[0], row[1]
    if reader == "search":
        return {"default": "search", "topics": {}}
    return {"default": "store" if scope is None else "search", "topics": {t: "store" for t in scope or []}}


def get_policy(chat_id: int) -> dict:
    """Effective editable policy; an absent chat is NOT opted in by this default."""
    row = _rows().get(chat_id)
    return _policy(row) if row is not None else {"default": "search", "topics": {}}


def save_configuration(chat_id: int, group_code: str, default_mode: str, topic_modes: dict[int, str], reader: str = "auto") -> None:
    """Confirm policy and study group in one transaction, without touching stored messages."""
    if type(chat_id) is not int or not -(2**63) <= chat_id < 2**63:
        raise ValueError("Invalid chat id")
    code = groups.normalize(group_code) if isinstance(group_code, str) else None
    if code is None:
        raise ValueError("Invalid study group")
    if reader not in READERS or default_mode not in MODES or not isinstance(topic_modes, dict):
        raise ValueError("Invalid reader or topic policy")
    if any(type(t) is not int or not 1 <= t < 2**63 or mode not in MODES for t, mode in topic_modes.items()):
        raise ValueError("Invalid topic id or mode")
    policy = {"default": default_mode, "topics": dict(topic_modes)}
    scope = _storage_scope((None, reader, policy))
    with pg.connection() as conn:
        found = pg.row(conn, Dialog, f"SELECT * FROM ({_DIALOGS}) x WHERE chat_id = %(chat)s", {"max": MAX_CHAT_BASE // 2, "chat": chat_id})  # noqa: S608
        if found is None:
            raise ValueError("Chat is no longer accessible")
        if found.bot_only and (reader in ("userbot", "search") or _has_mode(policy, ("search",))):
            raise ValueError("Telegram live search requires the userbot to be in the chat")
        if reader == "bot" and not found.bot_in:
            raise ValueError("The Bot API bot is not in this chat")
        known = {1}  # General is sometimes absent from Telegram's topic listing.
        if found.forum:
            known.update(pg.column(conn, "SELECT topic_id FROM userbot_topics WHERE chat_id = %s", (chat_id,)))
        if not topic_modes.keys() <= known:
            raise ValueError("A selected topic is no longer available")
        conn.execute(
            """INSERT INTO chats (chat_id, title, username, group_code) VALUES (%s, %s, %s, %s)
               ON CONFLICT (chat_id) DO UPDATE SET title = excluded.title, username = excluded.username,
                   group_code = excluded.group_code""",
            (chat_id, found.title, found.username, code),
        )
        conn.execute(
            """INSERT INTO userbot_listen (chat_id, topic_ids, reader, topic_policy) VALUES (%s, %s, %s, %s)
               ON CONFLICT (chat_id) DO UPDATE SET topic_ids = excluded.topic_ids, reader = excluded.reader,
                   topic_policy = excluded.topic_policy""",
            (chat_id, scope, reader, Jsonb(policy)),
        )
    _forget()


def listened() -> dict[int, list[int] | None]:
    """Chat id -> the topics to store (None = the whole chat)."""
    return {chat_id: _storage_scope(row) for chat_id, row in _rows().items()}


def _storage_scope(row: tuple | list) -> list[int] | None:
    if row[1] == "search":
        return []
    policy = _policy(row)
    if policy["default"] == "store":
        return None  # Exact exclusions are checked by topic_allowed, not this coarse fetch scope.
    return sorted(t for t, mode in policy["topics"].items() if mode == "store")


def _has_mode(policy: dict, modes: tuple[str, ...]) -> bool:
    return policy["default"] in modes or any(mode in modes for mode in policy["topics"].values())


def readers() -> dict[int, str]:
    """Chat id -> who stores it: auto, userbot or bot."""
    return {chat_id: row[1] for chat_id, row in _rows().items()}


def set_reader(chat_id: int, reader: str) -> None:
    assert reader in READERS
    with pg.connection() as conn:
        conn.execute("UPDATE userbot_listen SET reader = %s WHERE chat_id = %s", (reader, chat_id))
    _forget()


def effective_reader(reader: str, userbot_has_chat: bool) -> str:
    """Who really stores a chat: `auto` is the userbot when its account is in the chat (it has the history), else the bot."""
    return ("userbot" if userbot_has_chat else "bot") if reader == "auto" else reader  # `search` stays: nobody stores it


def searchable_chats() -> set[int]:
    """The chats Telegram's search may be used on through the userbot: chosen in /listen (whatever the reader) and with the
    userbot's account in them. The admin's choice is the policy; a chat that is not chosen is never searched."""
    return set(search_policies())


def search_policies() -> dict[int, tuple]:
    """Fresh, batched policies for live search, including account membership revocations."""
    mine = userbot_chat_ids()
    return {c: row for c, row in _rows().items() if c in mine and _has_mode(_policy(row), ("store", "search"))}


def searchable_titles(allowed: "frozenset[int] | set[int] | None" = None) -> dict[int, str]:
    """`searchable_chats` with their titles, only those a question of this asker may use (its study group)."""
    ids = _cached_ids("searchable_ids", searchable_chats)
    names = _cached_by_chat("dialog_titles", _dialog_titles)
    return {c: names.get(c, str(c)) for c in ids if allowed is None or c in allowed}


def _dialog_titles() -> dict[int, str]:
    with pg.connection() as conn:
        return {r["chat_id"]: r["title"] for r in conn.execute("SELECT chat_id, title FROM userbot_dialogs").fetchall()}


def live_chat_titles(allowed: "frozenset[int] | set[int] | None" = None) -> dict[int, str]:
    """The live-search chats (title by id) a question may use: those of its study group, cached for a few seconds because the
    agent asks on every model call."""
    live = _cached_ids("live_ids", live_chats)
    ids = [c for c in live if allowed is None or c in allowed]
    if not ids:
        return {}

    def load() -> dict[int, str]:
        with pg.connection() as conn:
            found = conn.execute("SELECT chat_id, title FROM chats WHERE chat_id = ANY(%s::bigint[])", (sorted(live),)).fetchall()
        return {r["chat_id"]: r["title"] for r in found}

    titles = _cached_by_chat("live_titles", load)
    return {c: titles.get(c, str(c)) for c in ids}


def userbot_reads() -> dict[int, list[int] | None]:
    """The chats the userbot stores, with their topics: chosen, its account is in them, and not given to the bot."""
    mine = userbot_chat_ids()
    rows = _rows()
    # Batch-boundary checks also refresh the exact topic policy, even when Redis invalidation was unavailable.
    cache.put("listen:rows", rows, CACHE_TTL)
    return {c: scope for c, row in rows.items()
            if c in mine and row[1] in ("auto", "userbot") and (scope := _storage_scope(row)) != []}


def storage_fingerprints() -> dict[int, tuple[bool, tuple[int, ...]]]:
    """Exact storage scope, including exclusions hidden by a coarse None/all fetch scope."""
    result = {}
    for chat_id, row in _rows().items():
        policy = _policy(row)
        default = policy["default"] == "store" and row[1] != "search"
        exceptions = tuple(sorted(t for t, mode in policy["topics"].items()
                                  if (mode == "store" and row[1] != "search") != default))
        result[chat_id] = (default, exceptions)
    return result


def live_chats() -> set[int]:
    """Include mixed storage/search chats and legacy live-only readers."""
    mine = userbot_chat_ids()
    return {c for c, row in _rows().items() if c in mine
            and _has_mode(_policy(row), ("store", "search") if row[1] == "search" else ("search",))}


def set_listen(chat_id: int, on: bool) -> None:
    with pg.connection() as conn:
        if on:
            conn.execute("INSERT INTO userbot_listen (chat_id) VALUES (%s) ON CONFLICT DO NOTHING", (chat_id,))
        else:
            conn.execute("DELETE FROM userbot_listen WHERE chat_id = %s", (chat_id,))
    _forget()


def toggle_topic(chat_id: int, topic_id: int) -> None:
    """Compatibility toggle: removing the last stored topic means NONE, never ALL."""
    with pg.connection() as conn:
        row = conn.execute("SELECT topic_ids, reader, topic_policy FROM userbot_listen WHERE chat_id = %s FOR UPDATE", (chat_id,)).fetchone()
        if row is None:
            return
        if row["topic_policy"] is None:
            scope = list(row["topic_ids"] or [])
            if topic_id in scope:
                scope.remove(topic_id)
            else:
                scope.append(topic_id)
            conn.execute("UPDATE userbot_listen SET topic_ids = %s WHERE chat_id = %s", (scope, chat_id))
        else:
            policy = _policy((row["topic_ids"], row["reader"], row["topic_policy"]))
            current = policy["topics"].get(topic_id, policy["default"])
            policy["topics"][topic_id] = "search" if current == "store" else "store"
            conn.execute("UPDATE userbot_listen SET topic_ids = %s, topic_policy = %s WHERE chat_id = %s",
                         (_storage_scope((None, row["reader"], policy)), Jsonb(policy), chat_id))
    _forget()


def clear_topics(chat_id: int) -> None:
    with pg.connection() as conn:
        conn.execute("UPDATE userbot_listen SET topic_ids = NULL, topic_policy = NULL WHERE chat_id = %s", (chat_id,))
    _forget()


# What the bots and the userbot read for every message, kept in the shared cache (common/cache.py) for CACHE_TTL.
_CACHED = ("rows", "known", "mine", "searchable_ids", "dialog_titles", "live_ids", "live_titles")


def _forget() -> None:
    """The choice or the userbot's chats changed: every process reads them again."""
    cache.drop(*(f"listen:{name}" for name in _CACHED))


def _cached_ids(name: str, load: Callable[[], set[int]]) -> set[int]:
    return set(cache.cached(f"listen:{name}", CACHE_TTL, lambda: sorted(load())))


def _cached_by_chat(name: str, load: Callable[[], dict[int, Any]]) -> dict[int, Any]:
    """A dict by chat id: JSON keeps the ids as strings, and a tuple in it as a list."""
    return {int(chat_id): value for chat_id, value in cache.cached(f"listen:{name}", CACHE_TTL, load).items()}


def listened_cached() -> dict[int, list[int] | None]:
    return {c: _storage_scope(row) for c, row in _cached_by_chat("rows", _rows).items()}


def _known_chats_cached() -> set[int]:
    def load() -> set[int]:
        with pg.connection() as conn:
            return set(pg.column(conn, "SELECT chat_id FROM chats"))

    return _cached_ids("known", load)


def bot_listens(chat_id: int) -> bool:
    """Only an explicit configuration (or legacy seed) permits the bot to store messages."""
    rows = _cached_by_chat("rows", _rows)
    if chat_id not in rows or _storage_scope(rows[chat_id]) == []:
        return False
    return effective_reader(rows[chat_id][1], chat_id in _cached_ids("mine", userbot_chat_ids)) == "bot"


def register_bot_chat(chat_id: int, title: str, username: str | None, member: bool = True) -> None:
    """Discover Bot API chats without granting ingestion consent or deleting their history."""
    with pg.connection() as conn:
        if member:
            conn.execute(
                """INSERT INTO chats (chat_id, title, username, bot_member) VALUES (%s, %s, %s, true)
                   ON CONFLICT (chat_id) DO UPDATE SET title = excluded.title, username = excluded.username,
                       bot_member = true""",
                (chat_id, title, username),
            )
        else:
            conn.execute("UPDATE chats SET bot_member = false WHERE chat_id = %s", (chat_id,))
    _forget()


def seed_bot_chats() -> int:
    """Once: the chats the Bot API bot already stores become chosen, so that nothing stops when it starts to ask."""
    if meta("bot_chats_seeded"):
        return 0
    with pg.connection() as conn:
        ids = pg.column(conn, "SELECT chat_id FROM chats WHERE bot_member AND chat_id < %s", (MAX_CHAT_BASE // 2,))
        with conn.cursor() as cur:  # TG_TOPICS keeps limiting these chats, as it did.
            cur.executemany(
                "INSERT INTO userbot_listen (chat_id, topic_ids) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                [(chat_id, settings.tg_topics.get(chat_id)) for chat_id in ids],
            )
    set_meta("bot_chats_seeded", "1")
    _forget()
    return len(ids)


def topic_allowed(chat_id: int, topic_id: int | None, general_topic_id: int) -> bool:
    """Storage/OCR permission. No configured row means no consent to ingest."""
    row = _cached_by_chat("rows", _rows).get(chat_id)
    if row is None or row[1] == "search":
        return False
    policy = _policy(row)
    return policy["topics"].get(topic_id or general_topic_id, policy["default"]) == "store"


def search_topic_allowed(chat_id: int, topic_id: int | None, *, policies: dict | None = None) -> bool:
    """Store and search topics may be searched live; off and unconfigured chats may not.

    A caller can pass one fresh snapshot for a whole result batch, including the final revocation check.
    """
    rows = policies if policies is not None else _cached_by_chat("rows", _rows)
    row = rows.get(chat_id)
    if row is None:
        return False
    policy = _policy(row)
    return policy["topics"].get(topic_id or 1, policy["default"]) != "off"


# ---- meta ---------------------------------------------------------------------------------------------------


def meta(key: str) -> str | None:
    with pg.connection() as conn:
        return pg.scalar(conn, "SELECT value FROM userbot_meta WHERE key = %s", (key,))


def set_meta(key: str, value: str) -> None:
    with pg.connection() as conn:
        conn.execute(
            "INSERT INTO userbot_meta (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


def request_refresh() -> None:
    set_meta("refresh_requested", str(time.time()))


def seed(resolved: dict[int, list[int] | None]) -> bool:
    """Copy TG_CHATS / TG_TOPICS (already resolved to ids) into the table, once. True if it did."""
    if meta("seeded"):
        return False
    with pg.connection() as conn, conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO userbot_listen (chat_id, topic_ids) VALUES (%s, %s) ON CONFLICT DO NOTHING", list(resolved.items())
        )
    set_meta("seeded", "1")
    return True
