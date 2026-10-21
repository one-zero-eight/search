"""Repeated attacks: a warning, then a pause.

The guardrail (agent/guardrail.py) stops a message that tries to change the agent's rules or is abuse. One such message
gets the usual refusal. If the same user keeps trying, the refusals change and in the end the user is paused:

- strikes are counted in a rolling window (ABUSE_WINDOW_HOURS), and only since the last pause;
- from ABUSE_WARN_AT the refusal says that such requests break the usage rules;
- at ABUSE_PAUSE_AT the user is paused for ABUSE_PAUSE_MINUTES, doubled for each repeat, at most ABUSE_PAUSE_MAX_HOURS
  (the repeats are forgotten after ABUSE_FORGET_DAYS without a pause); every message of a paused user, normal ones too, gets
  a short notice and costs no model call; nobody is told: the admins look at `/abuse` when they want to;
- only what the screen stops is counted (an off-topic request is refused by the agent itself and is not), and admins are never counted.

Admins look and lift a pause with `/abuse` in the bot (tgbot/abuse.py). Previews of the stopped messages are kept for
30 days. The user key is `tg:<id>` or `max:<id>`.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from catix.db import pg
from catix.db.rows import AbuseEntry, AbuseUser
from catix.settings import settings

log = logging.getLogger("catix.abuse")

COUNTED = {"prompt_injection", "abuse"}  # the screen's two ways to stop a message; the agent refuses off-topic requests itself
KEEP_DAYS = 30
PREVIEW_CHARS = 200


@dataclass(frozen=True, slots=True)
class Outcome:
    strikes: int  # in the window, since the last pause
    warn: bool
    paused_until: datetime | None
    newly_paused: bool


def user_key(telegram_id: int | None) -> str | None:
    """`tg:<id>` for Telegram users, `max:<id>` for Max users (they come with a negative id, see maxbot), None without a user."""
    if telegram_id is None or telegram_id == 0:
        return None
    return f"tg:{telegram_id}" if telegram_id > 0 else f"max:{-telegram_id}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def paused_until(key: str) -> datetime | None:
    """When the user's pause ends, or None if they are not paused."""
    with pg.connection() as conn:
        until = pg.scalar(conn, "SELECT paused_until FROM abuse_state WHERE user_key = %s", (key,))
    return until if until and until > _now() else None


def record(key: str, category: str, text: str) -> Outcome:
    """Count a stopped message. Only attacks and abuse count; the outcome says whether to warn or that the user is now paused."""
    now = _now()
    if category not in COUNTED:
        return Outcome(0, False, None, False)
    with pg.connection() as conn:
        conn.execute("DELETE FROM abuse_log WHERE at < %s", (now - timedelta(days=KEEP_DAYS),))
        conn.execute("INSERT INTO abuse_log (user_key, category, at, preview) VALUES (%s, %s, %s, %s)", (key, category, now, " ".join(text.split())[:PREVIEW_CHARS]))
        state = conn.execute("SELECT pauses, last_pause_at, paused_until FROM abuse_state WHERE user_key = %s", (key,)).fetchone()
        last_pause = state["last_pause_at"] if state else None
        since = max(now - timedelta(hours=settings.abuse_window_hours), last_pause) if last_pause else now - timedelta(hours=settings.abuse_window_hours)
        strikes = pg.scalar(conn, "SELECT count(*) FROM abuse_log WHERE user_key = %s AND at > %s", (key, since))
        if state and state["paused_until"] and state["paused_until"] > now:
            return Outcome(strikes, False, state["paused_until"], False)
        if strikes >= settings.abuse_pause_at:
            quiet = last_pause is None or now - last_pause > timedelta(days=settings.abuse_forget_days)
            pauses = 0 if quiet else state["pauses"]
            minutes = min(settings.abuse_pause_minutes * 2**pauses, settings.abuse_pause_max_hours * 60)
            until = now + timedelta(minutes=minutes)
            conn.execute(
                """INSERT INTO abuse_state (user_key, pauses, last_pause_at, paused_until) VALUES (%s, %s, %s, %s)
                   ON CONFLICT (user_key) DO UPDATE SET pauses = excluded.pauses, last_pause_at = excluded.last_pause_at,
                       paused_until = excluded.paused_until""",
                (key, pauses + 1, now, until),
            )
            log.warning("paused %s until %s (%d stopped messages, pause no. %d)", key, until, strikes, pauses + 1)
            return Outcome(strikes, False, until, True)
        return Outcome(strikes, strikes >= settings.abuse_warn_at, None, False)


def forgive(key: str) -> bool:
    """Lift the pause and forget the user's stopped messages. False if there was nothing about them."""
    with pg.connection() as conn:
        a = conn.execute("DELETE FROM abuse_log WHERE user_key = %s", (key,)).rowcount
        b = conn.execute("DELETE FROM abuse_state WHERE user_key = %s", (key,)).rowcount
    return bool(a or b)


def offenders() -> list[AbuseUser]:
    """Users with stopped messages in the window, or paused now, worst first."""
    since = _now() - timedelta(hours=settings.abuse_window_hours)
    with pg.connection() as conn:
        return pg.rows(
            conn,
            AbuseUser,
            """SELECT k.user_key, k.strikes, coalesce(s.pauses, 0) AS pauses,
                      CASE WHEN s.paused_until > now() THEN s.paused_until END AS paused_until
               FROM (SELECT user_key, count(*) AS strikes FROM abuse_log WHERE at > %s GROUP BY user_key) k
               LEFT JOIN abuse_state s USING (user_key)
               UNION
               SELECT s.user_key, 0, s.pauses, s.paused_until FROM abuse_state s
               WHERE s.paused_until > now() AND s.user_key NOT IN (SELECT user_key FROM abuse_log WHERE at > %s)
               ORDER BY 2 DESC, 1""",
            (since, since),
        )


def recent(key: str, limit: int = 5) -> list[AbuseEntry]:
    with pg.connection() as conn:
        return pg.rows(conn, AbuseEntry, "SELECT category, at, preview FROM abuse_log WHERE user_key = %s ORDER BY at DESC LIMIT %s", (key, limit))


# ---- the texts the user sees ----------------------------------------------------------------------------------


def _ru(text: str) -> bool:
    return bool(re.search(r"[а-яё]", text.lower()))


def _clock(until: datetime) -> str:
    return until.astimezone(settings.tz).strftime("%H:%M")


def warning_text(message: str) -> str:
    if _ru(message):
        return "Повторяющиеся запросы такого рода нарушают правила использования бота. При продолжении доступ будет временно ограничен."
    return "Repeated requests like this break the usage rules of the bot. If they continue, your access will be restricted for a while."


def pause_text(message: str, until: datetime) -> str:
    minutes = max(1, round((until - _now()).total_seconds() / 60))
    if _ru(message):
        return f"Из-за повторяющихся запросов, нарушающих правила использования, доступ ограничен на {minutes} мин (до {_clock(until)})."
    return f"Because of repeated requests that break the usage rules, your access is restricted for {minutes} min (until {_clock(until)})."


def paused_reply(message: str, until: datetime) -> str:
    if _ru(message):
        return f"Доступ временно ограничен до {_clock(until)} из-за повторяющихся запросов, нарушающих правила использования."
    return f"Your access is restricted until {_clock(until)} because of repeated requests that break the usage rules."


# ---- /abuse ---------------------------------------------------------------------------------------------------

USAGE = "Подробности: /abuse ключ (например /abuse tg:123456). Снять ограничение и забыть нарушения: /abuse clear ключ."


def _key(text: str) -> str:
    text = text.strip()
    return text if ":" in text else f"tg:{text}"


def command(args: str) -> str:
    """Reply to `/abuse [key | clear key]` for an admin."""
    parts = args.split()
    if parts and parts[0] == "clear":
        if len(parts) != 2:
            return USAGE
        return f"Снято: {_key(parts[1])}." if forgive(_key(parts[1])) else f"О {_key(parts[1])} ничего нет."
    if parts:
        key = _key(parts[0])
        entries = recent(key)
        until = paused_until(key)
        if not entries and not until:
            return f"О {key} ничего нет."
        lines = [f"{key}: " + (f"пауза до {_clock(until)}" if until else "не на паузе")]
        lines += [f"{e.at.astimezone(settings.tz):%d.%m %H:%M} [{e.category}] {e.preview}" for e in entries]
        return "\n".join(lines)
    users = offenders()
    if not users:
        return "Нарушителей нет."
    lines = [
        f"{u.user_key}: {u.strikes} за сутки" + (f", пауза до {_clock(u.paused_until)} (№{u.pauses})" if u.paused_until else "")
        for u in users
    ]
    return "Нарушители за сутки (порог паузы: %d):\n" % settings.abuse_pause_at + "\n".join(lines) + "\n\n" + USAGE
