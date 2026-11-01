"""Which chats are official: the university's own announcements, as opposed to students talking.

Everything in a chat is unofficial by default. An admin marks a chat as official (`/official` in the bot, or
`catix-db official`); search results then carry `official: true` for its messages, the source list says so, and only
then may an answer call something official (agent/claims.py checks that in code).
"""

from dataclasses import dataclass

from catix.db import pg


@dataclass(frozen=True, slots=True)
class OfficialChat:
    chat_id: int
    title: str
    official: bool


def chats() -> list[OfficialChat]:
    """Every known chat in a stable order (the numbers shown to the admin refer to it)."""
    with pg.connection() as conn:
        return pg.rows(conn, OfficialChat, "SELECT chat_id, title, official FROM chats ORDER BY title, chat_id")


def set_official(chat_id: int, value: bool) -> bool:
    """False if there is no such chat."""
    with pg.connection() as conn:
        return pg.scalar(conn, "UPDATE chats SET official = %s WHERE chat_id = %s RETURNING chat_id", (value, chat_id)) is not None


def flags(chat_ids: list[int]) -> dict[int, bool]:
    """chat id -> official, for the chats that exist."""
    with pg.connection() as conn:
        rows = conn.execute("SELECT chat_id, official FROM chats WHERE chat_id = ANY(%s::bigint[])", (chat_ids,)).fetchall()
    return {r["chat_id"]: r["official"] for r in rows}


def ids() -> set[int]:
    with pg.connection() as conn:
        return set(pg.column(conn, "SELECT chat_id FROM chats WHERE official"))


USAGE = "Чтобы отметить чат: /official номер (переключить) или /official номер on|off."


def command(args: str) -> str:
    """Reply to `/official [number [on|off]]`: the list of chats, or switch one chat."""
    known = chats()
    if not known:
        return "Чатов пока нет."
    parts = args.split()
    if not parts:
        lines = [f"{i}. {'✔' if c.official else '–'} {c.title}" for i, c in enumerate(known, 1)]
        return "Официальные чаты отмечены ✔: их сообщения можно называть официальными, остальные нет.\n\n" + "\n".join(lines) + "\n\n" + USAGE
    if not parts[0].isdigit() or not 1 <= int(parts[0]) <= len(known) or (len(parts) > 1 and parts[1].lower() not in ("on", "off")):
        return USAGE
    chat = known[int(parts[0]) - 1]
    value = (parts[1].lower() == "on") if len(parts) > 1 else not chat.official
    set_official(chat.chat_id, value)
    return f"«{chat.title}»: {'официальный чат ✔' if value else 'обычный чат (неофициальный)'}."
