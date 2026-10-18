"""Calendars the bot hands out: a feed per study group and a personal one per user.

- Group: /feed/g/<signature>/<GROUP>.ics, the approved schedule changes of the group's chats (worker/changes.py).
  The signature is an HMAC of the group name under FEED_TOKEN, so the link of one group does not reveal another's, and
  FEED_TOKEN itself (the admin's all-groups link for InNoHassle) is never given to users.
- Personal: /feed/me/<token>.ics, the events the user added with "➕ В мой календарь" under an answer. The token is
  random, belongs to one user and can be replaced (the old link stops working).
Both are subscribed to by URL in any calendar app.
"""

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

from catix.db import pg
from catix.settings import settings

MAX_PROPOSALS = 3
PROPOSAL_TTL_HOURS = 48


@dataclass(frozen=True, slots=True)
class PersonalEvent:
    id: int
    title: str
    starts_at: datetime
    ends_at: datetime | None
    all_day: bool
    room: str | None


def configured() -> bool:
    return bool(settings.feed_public_url and settings.feed_token)


def _base() -> str:
    return str(settings.feed_public_url).rstrip("/")


# ---- links ----------------------------------------------------------------------------------------------------


def group_signature(group: str) -> str:
    assert settings.feed_token
    key = settings.feed_token.get_secret_value().encode()
    return hmac.new(key, f"group:{group}".encode(), hashlib.sha256).hexdigest()[:32]


def group_url(group: str) -> str:
    return f"{_base()}/feed/g/{group_signature(group)}/{group}.ics"


def user_token(user_key: str) -> str:
    with pg.connection() as conn:
        token = pg.scalar(conn, "SELECT token FROM user_calendars WHERE user_key = %s", (user_key,))
        if token:
            return token
        token = secrets.token_urlsafe(24)
        conn.execute("INSERT INTO user_calendars (user_key, token) VALUES (%s, %s) ON CONFLICT DO NOTHING", (user_key, token))
        return pg.scalar(conn, "SELECT token FROM user_calendars WHERE user_key = %s", (user_key,))


def rotate_token(user_key: str) -> str:
    token = secrets.token_urlsafe(24)
    with pg.connection() as conn:
        conn.execute(
            """INSERT INTO user_calendars (user_key, token) VALUES (%s, %s)
               ON CONFLICT (user_key) DO UPDATE SET token = excluded.token, created_at = now()""",
            (user_key, token),
        )
    return token


def personal_url(user_key: str) -> str:
    return f"{_base()}/feed/me/{user_token(user_key)}.ics"


def user_by_token(token: str) -> str | None:
    with pg.connection() as conn:
        return pg.scalar(conn, "SELECT user_key FROM user_calendars WHERE token = %s", (token,))


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
            """INSERT INTO personal_events (user_key, title, starts_at, ends_at, all_day, room)
               VALUES (%s, %s, %s::timestamptz, %s::timestamptz, %s, %s) ON CONFLICT DO NOTHING""",
            (user_key, event["title"], event["starts_at"], event.get("ends_at"), bool(event.get("all_day")), event.get("room")),
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
            "SELECT id, title, starts_at, ends_at, all_day, room FROM personal_events WHERE user_key = %s ORDER BY starts_at",
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
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
