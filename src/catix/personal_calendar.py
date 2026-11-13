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
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from psycopg.errors import UniqueViolation

from catix.common import cache
from catix.db import pg
from catix.innohassle import client as innohassle
from catix.settings import settings

log = logging.getLogger("catix.calendar")

MAX_PROPOSALS = 3
PROPOSED_DURATION_MINUTES = 90
PROPOSAL_TTL_HOURS = 48
ACCOUNT_TTL = 3600.0  # The InNoHassle account of a Telegram id is trusted for an hour; a miss is asked again each time.

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
    key = f"innohassle-account:tg:{telegram_id}"
    found, account = cache.get(key)
    if found:
        return account_key(account, telegram_id)
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
    cache.put(key, account, ACCOUNT_TTL)
    return account_key(account, telegram_id)


# ---- events ---------------------------------------------------------------------------------------------------


def propose(events: list[dict]) -> list[tuple[str, dict]]:
    """Keep the events the agent offered under an answer until someone presses the button; returns (id, event)."""
    events = [proposed_event(event) for event in events[:MAX_PROPOSALS]]
    out = []
    with pg.connection() as conn:
        # Worker cards have durable callbacks; their displayed interval must outlive answer-offer expiry.
        conn.execute(
            "DELETE FROM calendar_proposals WHERE created_at < now() - make_interval(hours => %s) AND NOT (event ? 'change_id')",
            (PROPOSAL_TTL_HOURS,),
        )
        for event in events[:MAX_PROPOSALS]:
            pid = secrets.token_hex(6)
            conn.execute("INSERT INTO calendar_proposals (id, event) VALUES (%s, %s::jsonb)", (pid, json.dumps(event)))
            out.append((pid, event))
    return out


def proposed_event(event: dict) -> dict:
    """Prepare a visible duration suggestion, without changing the source event."""
    event = dict(event)
    event["end_suggested"] = False
    start, _ = _proposal_interval(event)
    if not event.get("all_day") and event.get("ends_at") is None:
        event["ends_at"] = (start + timedelta(minutes=PROPOSED_DURATION_MINUTES)).isoformat()
        event["end_suggested"] = True
    return event


def _proposal_interval(event: dict) -> tuple[datetime, datetime | None]:
    """Validate before storage; malformed ends are not unknown ends."""
    try:
        start = datetime.fromisoformat(event["starts_at"])
        end = datetime.fromisoformat(event["ends_at"]) if event.get("ends_at") is not None else None
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid calendar proposal interval.") from exc
    if start.utcoffset() is None or (end is not None and (end.utcoffset() is None or end <= start)):
        raise ValueError("Calendar proposal dates must be aware and the end after the start.")
    if event.get("end_suggested") and (event.get("all_day") or end is None):
        raise ValueError("A suggested duration requires a timed interval.")
    return start, end


def add_proposal(user_key: str, proposal_id: str) -> str | None:
    """Copy an offered event into the user's calendar; its title, or None if the offer expired. The same event twice is one."""
    if proposal_id.startswith("change:"):
        return None  # Worker callbacks apply rescheduling semantics, not answer-offer insertion.
    with pg.connection() as conn:
        event = pg.scalar(conn, "SELECT event FROM calendar_proposals WHERE id = %s", (proposal_id,))
        if event is None:
            return None
        _proposal_interval(event)  # Never synthesize an end for an older offer at click time.
        conn.execute(
            """INSERT INTO personal_events (user_key, title, starts_at, ends_at, all_day, room, source_url)
               VALUES (%s, %s, %s::timestamptz, %s::timestamptz, %s, %s, %s) ON CONFLICT DO NOTHING""",
            (user_key, event["title"], event["starts_at"], event.get("ends_at"), bool(event.get("all_day")), event.get("room"), event.get("source_url")),
        )
    return event["title"]


MAX_TITLE_LENGTH = 300


def _validate_manual_event(user_key: str, title: str, starts_at: datetime, ends_at: datetime | None) -> None:
    """Guard the storage API too: callers need not have used the agent's argument schema."""
    if not isinstance(user_key, str) or not user_key.startswith("ih:") or not user_key[3:].strip():
        raise ValueError("A known InNoHassle account is required.")
    if not isinstance(title, str) or not 1 <= len(title.strip()) <= MAX_TITLE_LENGTH:
        raise ValueError(f"The title must contain 1–{MAX_TITLE_LENGTH} characters.")
    for value in (starts_at,) + ((ends_at,) if ends_at is not None else ()):
        if not isinstance(value, datetime) or value.utcoffset() is None:
            raise ValueError("Calendar dates must be timezone-aware datetimes.")
    if ends_at is not None and ends_at <= starts_at:
        raise ValueError("The end must be after the start.")


def add_event(
    user_key: str, *, title: str, starts_at: datetime, all_day: bool,
    ends_at: datetime | None = None, room: str | None = None,
) -> PersonalEvent:
    """Add a manual event without inventing a source; return its committed readback."""
    _validate_manual_event(user_key, title, starts_at, ends_at)
    title = title.strip()
    room = room.strip() if room is not None else None
    with pg.connection() as conn:
        event_id = pg.scalar(
            conn,
            """INSERT INTO personal_events (user_key, title, starts_at, ends_at, all_day, room)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (user_key, title, starts_at) DO NOTHING RETURNING id""",
            (user_key, title, starts_at, ends_at, all_day, room),
        )
        if event_id is None:
            event_id = pg.scalar(
                conn, "SELECT id FROM personal_events WHERE user_key = %s AND title = %s AND starts_at = %s",
                (user_key, title, starts_at),
            )
    event = event_of(user_key, event_id)
    if event is None:
        raise RuntimeError("The saved calendar event could not be read back.")
    return event


def update_event(
    user_key: str, event_id: int, *, title: str, starts_at: datetime, all_day: bool,
    ends_at: datetime | None = None, room: str | None = None,
) -> PersonalEvent | None:
    """Replace owned details, clearing stale provenance only on a material change. None means no owned event."""
    _validate_manual_event(user_key, title, starts_at, ends_at)
    title = title.strip()
    room = room.strip() if room is not None else None
    try:
        with pg.connection() as conn:
            changed = conn.execute(
                """UPDATE personal_events SET title = %s, starts_at = %s, ends_at = %s, all_day = %s, room = %s,
                       source_url = NULL, source_note = NULL
                   WHERE id = %s AND user_key = %s
                     AND (title, starts_at, ends_at, all_day, room) IS DISTINCT FROM (%s, %s, %s, %s, %s)""",
                (title, starts_at, ends_at, all_day, room, event_id, user_key, title, starts_at, ends_at, all_day, room),
            ).rowcount
    except UniqueViolation as e:
        raise ValueError("An event with this title and start already exists in your AI Calendar; neither event was changed.") from e
    if not changed:
        return event_of(user_key, event_id)
    event = event_of(user_key, event_id)
    if event is None:
        raise RuntimeError("The saved calendar event could not be read back.")
    return event


def upcoming(user_key: str, limit: int = 6) -> list[PersonalEvent]:
    with pg.connection() as conn:
        return pg.rows(
            conn,
            PersonalEvent,
            """SELECT id, title, starts_at, ends_at, all_day, room FROM personal_events
               WHERE user_key = %s AND coalesce(ends_at, starts_at) >= now() - interval '1 day' ORDER BY starts_at LIMIT %s""",
            (user_key, limit),
        )


def between(user_key: str, start: datetime, end: datetime, limit: int = 40) -> list[PersonalEvent]:
    """Events possibly occupying [start, end); an unknown timed end is not an implicit day boundary."""
    with pg.connection() as conn:
        return pg.rows(
            conn,
            PersonalEvent,
            """SELECT id, title, starts_at, ends_at, all_day, room, source_url FROM personal_events
               WHERE user_key = %s AND
                 (CASE WHEN all_day THEN date_trunc('day', starts_at AT TIME ZONE %s) AT TIME ZONE %s
                       ELSE starts_at END) < %s AND (
                 (NOT all_day AND (ends_at IS NULL OR ends_at > %s))
                 OR (all_day AND (GREATEST((starts_at AT TIME ZONE %s)::date + 1,
                                          (ends_at AT TIME ZONE %s)::date)::timestamp AT TIME ZONE %s) > %s)
               ) ORDER BY starts_at LIMIT %s""",
            (user_key, str(settings.tz), str(settings.tz), end, start,
             str(settings.tz), str(settings.tz), str(settings.tz), start, limit),
        )


def event_of(user_key: str, event_id: int) -> PersonalEvent | None:
    """One event of the user's, or None when they have no such event."""
    with pg.connection() as conn:
        return pg.row(
            conn,
            PersonalEvent,
            """SELECT id, title, starts_at, ends_at, all_day, room, source_url, source_note
               FROM personal_events WHERE id = %s AND user_key = %s""",
            (event_id, user_key),
        )


def delete_event(user_key: str, event_id: int) -> bool:
    with pg.connection() as conn:
        return conn.execute("DELETE FROM personal_events WHERE id = %s AND user_key = %s", (event_id, user_key)).rowcount > 0


# ---- the feed -------------------------------------------------------------------------------------------------


def ics(user_key: str, *, include_sources: bool = True) -> str:
    """The user's events as an iCalendar document (all of them: a calendar app shows what it wants).

    Public subscription exports omit source links and notes; private calendar consumers keep the historical default.
    """
    from datetime import timedelta
    from catix.worker.changes import _escape, _fold

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
        lines += ["BEGIN:VEVENT", f"UID:personal-{r.id}@ctx", f"DTSTAMP:{stamp(now)}"]
        if r.all_day:
            first = starts.astimezone(settings.tz).date()
            last = r.ends_at.astimezone(settings.tz).date() if r.ends_at else first + timedelta(days=1)
            last = max(last, first + timedelta(days=1))
            lines += [f"DTSTART;VALUE=DATE:{first:%Y%m%d}", f"DTEND;VALUE=DATE:{last:%Y%m%d}"]
        else:
            lines.append(f"DTSTART:{stamp(starts)}")
            if r.ends_at is not None:
                lines.append(f"DTEND:{stamp(r.ends_at)}")
        lines.append(f"SUMMARY:{_escape(r.title)}")
        if r.room:
            lines.append(f"LOCATION:{_escape(r.room)}")
        if include_sources and r.source_url:
            lines += [f"URL:{r.source_url}", f"X-WR-LINK:{r.source_url}"]  # The message the event comes from.
        if include_sources and r.source_note:  # Where it comes from in words: a message of a basic group has no link.
            lines.append(f"DESCRIPTION:{_escape(r.source_note)}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
