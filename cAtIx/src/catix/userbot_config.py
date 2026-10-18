"""What the Telegram userbot listens to: chats and forum topics, chosen by an admin in the bot (tgbot/listen.py).

The userbot (tguserbot/userbot.py) publishes the chats and topics it can see; the admin turns chats on and off and
narrows a forum chat to some of its topics; the userbot picks the change up within seconds. The study group of a
chat is not kept here, it stays `chats.group_code` (groups.py).
TG_CHATS and TG_TOPICS from .env are copied here once (`seed`), after that this table is the truth.
"""

import time
from dataclasses import dataclass

from catix.db import pg
from catix.settings import settings

CACHE_TTL = 10.0  # Seconds: `topic_allowed` runs for every stored message.


@dataclass(frozen=True, slots=True)
class Dialog:
    chat_id: int
    title: str
    kind: str
    username: str | None
    forum: bool


@dataclass(frozen=True, slots=True)
class Topic:
    topic_id: int
    title: str
    closed: bool


def dialogs() -> list[Dialog]:
    with pg.connection() as conn:
        return pg.rows(conn, Dialog, "SELECT chat_id, title, kind, username, forum FROM userbot_dialogs ORDER BY lower(title), chat_id")


def dialog(chat_id: int) -> Dialog | None:
    with pg.connection() as conn:
        return pg.row(conn, Dialog, "SELECT chat_id, title, kind, username, forum FROM userbot_dialogs WHERE chat_id = %s", (chat_id,))


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


def listened() -> dict[int, list[int] | None]:
    """Chat id -> the topics to store (None = the whole chat)."""
    with pg.connection() as conn:
        return {r["chat_id"]: r["topic_ids"] for r in conn.execute("SELECT chat_id, topic_ids FROM userbot_listen").fetchall()}


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


_cache: dict[str, tuple[float, dict[int, list[int] | None]]] = {}


def listened_cached() -> dict[int, list[int] | None]:
    hit = _cache.get("listened")
    if hit and time.monotonic() < hit[0]:
        return hit[1]
    value = listened()
    _cache["listened"] = (time.monotonic() + CACHE_TTL, value)
    return value


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
