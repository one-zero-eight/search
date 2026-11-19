"""Telegram users the bot may write to first (table bot_users).

Telegram lets a bot send a message only to a person who opened a private chat with it: pressed /start or wrote there.
So the found schedule changes (worker/app.py) can reach only them, and the bot remembers them: on /start and on every
message in a private chat (tgbot/bot.py). A user who blocks the bot is marked (Telegram tells the bot, and a message
the worker sends is refused) and is not written to until they start the bot again.
"""

from catix.db import pg


def remember(telegram_id: int) -> None:
    """The user opened a private chat with the bot or unblocked it."""
    with pg.connection() as conn:
        conn.execute(
            """INSERT INTO bot_users (telegram_id) VALUES (%s)
               ON CONFLICT (telegram_id) DO UPDATE SET blocked_at = NULL WHERE bot_users.blocked_at IS NOT NULL""",
            (telegram_id,),
        )


def blocked(telegram_id: int) -> None:
    """The user blocked the bot: no more messages until they start it again."""
    with pg.connection() as conn:
        conn.execute(
            """INSERT INTO bot_users (telegram_id, blocked_at) VALUES (%s, now())
               ON CONFLICT (telegram_id) DO UPDATE SET blocked_at = now()""",
            (telegram_id,),
        )


def reachable() -> list[int]:
    """Telegram ids the bot may write to now."""
    with pg.connection() as conn:
        return pg.column(conn, "SELECT telegram_id FROM bot_users WHERE blocked_at IS NULL ORDER BY telegram_id")
