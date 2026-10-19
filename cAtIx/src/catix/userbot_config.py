"""What is listened to in Telegram: chats and forum topics, chosen by an admin in the bot (tgbot/listen.py).

Two readers share the choice. The userbot (tguserbot/userbot.py, an account that is a member of the chats) publishes the
chats and topics it can see and stores what a chosen chat says, history included. The Bot API bot (tgbot/bot.py) stores
the chats it was added to from then on; a chat it meets for the first time is turned on, an admin can turn it off.
The userbot publishes the chats and topics it can see; the admin turns chats on and off and
narrows a forum chat to some of its topics; the userbot picks the change up within seconds. The study group of a
chat is not kept here, it stays `chats.group_code` (groups.py).
TG_CHATS and TG_TOPICS from .env are copied here once (`seed`), after that this table is the truth.
"""

import time
from dataclasses import dataclass
from typing import Any

from catix.db import pg
from catix.groups import MAX_CHAT_BASE
from catix.settings import settings

CACHE_TTL = 10.0  # Seconds: `topic_allowed` runs for every stored message.


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


def replace_topics(chat_id: int, found: list[Topic]) -> None:
    with pg.connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM userbot_topics WHERE chat_id = %s", (chat_id,))
        cur.executemany(
            "INSERT INTO userbot_topics (chat_id, topic_id, title, closed) VALUES (%s, %s, %s, %s)",
            [(chat_id, t.topic_id, t.title, t.closed) for t in found],
        )


# ---- what is listened to ------------------------------------------------------------------------------------


READERS = ("auto", "userbot", "bot", "search")


def _rows() -> dict[int, tuple[list[int] | None, str]]:
    with pg.connection() as conn:
        found = conn.execute("SELECT chat_id, topic_ids, reader FROM userbot_listen").fetchall()
    return {r["chat_id"]: (r["topic_ids"], r["reader"]) for r in found}


def listened() -> dict[int, list[int] | None]:
    """Chat id -> the topics to store (None = the whole chat)."""
    return {chat_id: topics for chat_id, (topics, _) in _rows().items()}


def readers() -> dict[int, str]:
    """Chat id -> who stores it: auto, userbot or bot."""
    return {chat_id: reader for chat_id, (_, reader) in _rows().items()}


def set_reader(chat_id: int, reader: str) -> None:
    assert reader in READERS
    with pg.connection() as conn:
        conn.execute("UPDATE userbot_listen SET reader = %s WHERE chat_id = %s", (reader, chat_id))
    _cache.clear()


def effective_reader(reader: str, userbot_has_chat: bool) -> str:
    """Who really stores a chat: `auto` is the userbot when its account is in the chat (it has the history), else the bot."""
    return ("userbot" if userbot_has_chat else "bot") if reader == "auto" else reader  # `search` stays: nobody stores it


def live_chat_titles(allowed: "frozenset[int] | set[int] | None" = None) -> dict[int, str]:
    """The live-search chats (title by id) a question may use: those of its study group, cached for a few seconds because the
    agent asks on every model call."""
    live = _cached("live_ids", live_chats)
    ids = [c for c in live if allowed is None or c in allowed]
    if not ids:
        return {}

    def load() -> dict[int, str]:
        with pg.connection() as conn:
            found = conn.execute("SELECT chat_id, title FROM chats WHERE chat_id = ANY(%s::bigint[])", (sorted(live),)).fetchall()
        return {r["chat_id"]: r["title"] for r in found}

    titles = _cached("live_titles", load)
    return {c: titles.get(c, str(c)) for c in ids}


def userbot_reads() -> dict[int, list[int] | None]:
    """The chats the userbot stores, with their topics: chosen, its account is in them, and not given to the bot."""
    mine = userbot_chat_ids()
    return {c: topics for c, (topics, reader) in _rows().items() if c in mine and reader in ("auto", "userbot")}


def live_chats() -> set[int]:
    """The chats that are searched live with Telegram's search (reader `search`) and that the userbot's account is in."""
    mine = userbot_chat_ids()
    return {c for c, (_, reader) in _rows().items() if reader == "search" and c in mine}


def set_listen(chat_id: int, on: bool) -> None:
    with pg.connection() as conn:
        if on:
            conn.execute("INSERT INTO userbot_listen (chat_id) VALUES (%s) ON CONFLICT DO NOTHING", (chat_id,))
        else:
            conn.execute("DELETE FROM userbot_listen WHERE chat_id = %s", (chat_id,))
    _cache.clear()


def toggle_topic(chat_id: int, topic_id: int) -> None:
    """Add or remove a topic of a listened chat; with none left the whole chat is stored again."""
    with pg.connection() as conn:
        conn.execute(
            """UPDATE userbot_listen SET topic_ids = nullif(
                   CASE WHEN topic_ids IS NOT NULL AND %(t)s = ANY(topic_ids) THEN array_remove(topic_ids, %(t)s)
                        ELSE array_append(coalesce(topic_ids, ARRAY[]::bigint[]), %(t)s) END, ARRAY[]::bigint[])
               WHERE chat_id = %(c)s""",
            {"t": topic_id, "c": chat_id},
        )
    _cache.clear()


def clear_topics(chat_id: int) -> None:
    with pg.connection() as conn:
        conn.execute("UPDATE userbot_listen SET topic_ids = NULL WHERE chat_id = %s", (chat_id,))
    _cache.clear()


_cache: dict[str, tuple[float, Any]] = {}


def _cached(key: str, load) -> Any:
    hit = _cache.get(key)
    if hit and time.monotonic() < hit[0]:
        return hit[1]
    value = load()
    _cache[key] = (time.monotonic() + CACHE_TTL, value)
    return value


def listened_cached() -> dict[int, list[int] | None]:
    return {c: topics for c, (topics, _) in _cached("rows", _rows).items()}


def _known_chats_cached() -> set[int]:
    def load() -> set[int]:
        with pg.connection() as conn:
            return set(pg.column(conn, "SELECT chat_id FROM chats"))

    return _cached("known", load)


def bot_listens(chat_id: int) -> bool:
    """Whether the Bot API bot stores this chat: it is chosen in /listen and the bot is its reader (`auto` gives a chat
    the userbot's account is in to the userbot). A chat the bot has never seen is turned on now (adding the bot to a chat
    is the consent); a known chat that is not chosen was turned off by an admin."""
    rows = _cached("rows", _rows)
    if chat_id not in rows:
        if chat_id in _known_chats_cached():
            return False
        set_listen(chat_id, True)
        _cache.pop("known", None)
        rows = _cached("rows", _rows)
    return effective_reader(rows[chat_id][1], chat_id in _cached("mine", userbot_chat_ids)) == "bot"


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
    _cache.clear()
    return len(ids)


def topic_allowed(chat_id: int, topic_id: int | None, general_topic_id: int) -> bool:
    """Whether a message should be stored: a chat chosen in the bot follows that choice, any other (the Bot API bot's
    chats) follows TG_TOPICS."""
    chosen = listened_cached()
    allowed = chosen[chat_id] if chat_id in chosen else settings.tg_topics.get(chat_id)
    return allowed is None or (topic_id or general_topic_id) in allowed


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
