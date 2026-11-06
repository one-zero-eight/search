"""A user's personal calendar: the events they added with "➕ В мой календарь" under an answer.

The events are kept under the person's InNoHassle account, 'ih:<InNoHassle id>', and only there. The site (api/users.py:
the button POST /users/my-calendar/events/{id} and the calendar GET /users/my-calendar.ics) takes the account from the
token, the Telegram bot asks InNoHassle for the account linked to the Telegram id (accounts/v0/users/by-telegram-id). A
user of the bot InNoHassle does not know adds nothing: the bot asks them to link the Telegram to InNoHassle first.
Events added under 'tg:<telegram id>' before move to the account as soon as it is known.
"""

import json
import logging
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from catix.db import pg
from catix.innohassle import client as innohassle
from catix.settings import settings

log = logging.getLogger("catix.calendar")

MAX_PROPOSALS = 3
PROPOSAL_TTL_HOURS = 48
ACCOUNT_TTL = 3600.0  # The InNoHassle account of a Telegram id is trusted for an hour; a miss is asked again each time.
_accounts: dict[int, tuple[float, str]] = {}

CONNECT_TELEGRAM = "https://innohassle.ru/account/connect-telegram"
NOT_LINKED = (
    "Календарь хранится в вашем аккаунте InNoHassle, а этот Telegram к нему не привязан. "
    f"Привяжите его: {CONNECT_TELEGRAM}, и нажмите ещё раз."
)
UNAVAILABLE = "InNoHassle сейчас не отвечает, а календарь хранится там. Попробуйте позже."


@dataclass(frozen=True, slots=True)
class PersonalEvent:
    id: int
    title: str
    starts_at: datetime
    ends_at: datetime | None
    all_day: bool
    room: str | None
    source_url: str | None = None  # The chat message the event comes from.
    source_note: str | None = None  # The chat, time, author and text of that message.


# ---- whose events ---------------------------------------------------------------------------------------------


def account_key(innohassle_id: str, telegram_id: int | None = None) -> str:
    """The key of an InNoHassle account's calendar. The events its Telegram account added in the bot under the Telegram id
    (before the calendar was only the account's) move into it (an event the account has already is kept once)."""
    key = f"ih:{innohassle_id}"
    if telegram_id:
        old = f"tg:{telegram_id}"
        with pg.connection() as conn:
            conn.execute(
                """DELETE FROM personal_events t USING personal_events a
                   WHERE t.user_key = %s AND a.user_key = %s AND a.title = t.title AND a.starts_at = t.starts_at""",
                (old, key),
            )
            conn.execute("UPDATE personal_events SET user_key = %s WHERE user_key = %s", (key, old))
    return key


class NoAccount(Exception):
    """No InNoHassle account to keep a Telegram user's events under; the message is what to tell them."""


def telegram_key(telegram_id: int) -> str:
    """The calendar key of a user of the Telegram bot: the InNoHassle account linked to their Telegram id. Raises
    NoAccount when InNoHassle knows no such account (NOT_LINKED) or cannot be asked: no service token, down (UNAVAILABLE)."""
    hit = _accounts.get(telegram_id)
    if hit and time.monotonic() < hit[0]:
        return account_key(hit[1], telegram_id)
    try:
        account = innohassle.user_id_by_telegram_id(telegram_id)
    except innohassle.ServiceTokenError as e:
        log.warning("no InNoHassle account lookup for telegram id %s: %s", telegram_id, e)
        raise NoAccount(UNAVAILABLE) from e
    except Exception as e:
        log.exception("InNoHassle account lookup for telegram id %s failed", telegram_id)
        raise NoAccount(UNAVAILABLE) from e
    if account is None:
        raise NoAccount(NOT_LINKED)
    _accounts[telegram_id] = (time.monotonic() + ACCOUNT_TTL, account)
    return account_key(account, telegram_id)


# ---- events ---------------------------------------------------------------------------------------------------


def propose(events: list[dict]) -> list[tuple[str, dict]]:
    """Keep the events the agent offered under an answer until someone presses the button; returns (id, event)."""
    out = []
    with pg.connection() as conn:
        conn.execute("DELETE FROM calendar_proposals WHERE created_at < now() - make_interval(hours => %s)", (PROPOSAL_TTL_HOURS,))
        for event in events[:MAX_PROPOSALS]:
            pid = secrets.token_hex(6)
            conn.execute("INSERT INTO calendar_proposals (id, event) VALUES (%s, %s::jsonb)", (pid, json.dumps(event)))
            out.append((pid, event))
    return out


def add_proposal(user_key: str, proposal_id: str) -> str | None:
    """Copy an offered event into the user's calendar; its title, or None if the offer expired. The same event twice is one."""
    with pg.connection() as conn:
        event = pg.scalar(conn, "SELECT event FROM calendar_proposals WHERE id = %s", (proposal_id,))
        if event is None:
            return None
        conn.execute(
            """INSERT INTO personal_events (user_key, title, starts_at, ends_at, all_day, room, source_url)
               VALUES (%s, %s, %s::timestamptz, %s::timestamptz, %s, %s, %s) ON CONFLICT DO NOTHING""",
            (user_key, event["title"], event["starts_at"], event.get("ends_at"), bool(event.get("all_day")), event.get("room"), event.get("source_url")),
        )
    return event["title"]


def upcoming(user_key: str, limit: int = 6) -> list[PersonalEvent]:
    with pg.connection() as conn:
        return pg.rows(
            conn,
            PersonalEvent,
            """SELECT id, title, starts_at, ends_at, all_day, room FROM personal_events
               WHERE user_key = %s AND coalesce(ends_at, starts_at) >= now() - interval '1 day' ORDER BY starts_at LIMIT %s""",
            (user_key, limit),
        )


def delete_event(user_key: str, event_id: int) -> bool:
    with pg.connection() as conn:
        return conn.execute("DELETE FROM personal_events WHERE id = %s AND user_key = %s", (event_id, user_key)).rowcount > 0


# ---- the feed -------------------------------------------------------------------------------------------------


def ics(user_key: str) -> str:
    """The user's events as an iCalendar document (all of them: a calendar app shows what it wants)."""
    from catix.worker.changes import DEFAULT_LENGTH, _escape, _fold

    with pg.connection() as conn:
        rows = pg.rows(
            conn,
            PersonalEvent,
            """SELECT id, title, starts_at, ends_at, all_day, room, source_url, source_note FROM personal_events
               WHERE user_key = %s ORDER BY starts_at""",
            (user_key,),
        )
    stamp = lambda t: t.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")  # noqa: E731
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ctx//personal//RU", "CALSCALE:GREGORIAN", "X-WR-CALNAME:Мои события (cAtIx)"]
    now = datetime.now(timezone.utc)
    for r in rows:
        starts = r.starts_at
        if r.all_day:  # InNoHassle does not show all-day events: the same start time as for schedule changes.
            starts = datetime.combine(r.starts_at.astimezone(settings.tz).date(), settings.changes_default_time, settings.tz)
        end = starts + (r.ends_at - r.starts_at if r.ends_at and not r.all_day else DEFAULT_LENGTH)
        lines += ["BEGIN:VEVENT", f"UID:personal-{r.id}@ctx", f"DTSTAMP:{stamp(now)}", f"DTSTART:{stamp(starts)}",
                  f"DTEND:{stamp(end)}", f"SUMMARY:{_escape(r.title)}"]  # fmt: skip
        if r.room:
            lines.append(f"LOCATION:{_escape(r.room)}")
        if r.source_url:
            lines += [f"URL:{r.source_url}", f"X-WR-LINK:{r.source_url}"]  # The message the event comes from.
        if r.source_note:  # Where it comes from in words: a message of a basic group has no link.
            lines.append(f"DESCRIPTION:{_escape(r.source_note)}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
