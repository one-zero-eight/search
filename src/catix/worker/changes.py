"""Schedule changes announced in chats (a test moved, a lecture in another room, a cancelled class).

The worker (worker.py, `catix-worker`) gets the id of every new message from a Redis stream. The model decides
whether the message puts something on the calendar (a reschedule, a room change, a cancellation or a new event) and,
if so, when and where. A found change is sent to the users of the chat's study group (of a chat for everybody: to every
user) who started the bot, the only ones it may write to (bot_users.py). Each decides for themselves: "✅ В мой
календарь" puts it in their personal calendar (personal_calendar.py, /users/my-calendar.ics). The stream carries only new messages, so history is not scanned.
"""

import html
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from catix import admins as admins_module
from catix import bot_users, groups, personal_calendar
from catix.common import dates
from catix.common.dates import ClockTime
from catix.db import pg
from catix.agent import tracing
from catix.db.rows import ChangeKind, ChangeView, MessageToRead
from catix.settings import settings

log = logging.getLogger("catix.changes")

MIN_CHARS = 15  # "ок", "спасибо", a sticker caption: nothing to decide, so the model is not asked.
LOOKUPS = 8  # Groups of the users asked from InNoHassle at once.
KIND_TITLE = {"reschedule": "Перенос", "room_change": "Смена аудитории", "cancel": "Отмена", "announcement": "Анонс"}

PROMPT = """\
You read one chat message of Innopolis University students and decide whether it puts something on the calendar: \
- reschedule: a class, lecture, test, exam or event moved to another time;
- room_change: it is held in another room;
- cancel: it is cancelled;
- announcement: a NEW event with a date (a guest lecture, a test, an exam, a deadline, a meeting, a contest).
Questions, rumours ("кажется перенесут"), jokes, events in the past, advice, links, and general talk are NOT calendar \
items: is_change=false.

Message sent: {sent} ({weekday}). Chat: {chat}.
{parent}Message: {text}
{hints}
Fill the fields:
- is_change: true only if the message clearly states one of the four things above.
- kind: reschedule, room_change, cancel or announcement.
- subject: the course or event named in the message text (not the chat name), short, in the message's language.
- day: the date (YYYY-MM-DD) the class happens NEW, or for a cancellation the date it was planned. Use the resolved \
dates above, never invent one; if the day is not given, is_change=false.
- start_time: local start time HH:MM only if the message states it, else null. Never guess a time.
- end_time: local end time HH:MM only if stated, else null.
- room: the new room as written, else null.
- summary: one short sentence in Russian: what changed.
"""


# The prompt as a template: the message text is a variable, so braces in it are data and never parsed.
TEMPLATE = ChatPromptTemplate.from_messages([("human", PROMPT)])


class Change(BaseModel):
    """Every string bounded, the times HH:MM: the model loops to the token limit in an unbounded field (agent/events.py)."""

    is_change: bool
    kind: ChangeKind | None = None
    subject: str | None = Field(None, max_length=120)
    day: date | None = None
    start_time: ClockTime | None = None
    end_time: ClockTime | None = None
    room: str | None = Field(None, max_length=80)
    summary: str = Field("", max_length=200, description="One short sentence in Russian.")


def when(change: Change) -> tuple[datetime, datetime | None, bool]:
    """Start, end and whether the event lasts the whole day (no time was stated)."""
    day = change.day
    assert day is not None  # extract() only returns changes with a day
    if change.start_time is None:
        return datetime.combine(day, time(0), settings.tz), None, True
    start = datetime.combine(day, change.start_time, settings.tz)
    end = datetime.combine(day, change.end_time, settings.tz) if change.end_time else None
    if end is not None and end <= start:
        if change.kind in ("announcement", "reschedule"):
            raise ValueError("The end must be after the start.")
        end = None
    return start, end, False


def _model():
    return ChatOpenAI(
        base_url=str(settings.llm_route),
        api_key="not-needed",
        model=settings.llm_model,
        max_tokens=400,
        temperature=0,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    ).with_structured_output(Change, method="json_schema")


def extract(model, row: MessageToRead) -> Change | None:
    """The change a message announces, or None."""
    now = datetime.now(settings.tz)
    sent = row.date.astimezone(settings.tz)
    resolved = dates.resolve(row.text, row.date, now)
    parent = f"Message it replies to: {row.parent_text}\n" if row.parent_text else ""
    variables = dict(
        sent=f"{sent:%Y-%m-%d %H:%M}",
        weekday=f"{sent:%A}",
        chat=row.chat_title,
        parent=parent,
        text=row.text[:1500],
        hints=("Dates in the message, resolved: " + "; ".join(resolved) + "\n") if resolved else "",
    )
    result: Change = (TEMPLATE | model).invoke(variables, config=tracing.run_config("changes", name="schedule-change-detection"))
    if not (result.is_change and result.kind and result.day):
        return None
    if result.day < now.date():
        return None  # Already over: nothing to put on the calendar (and a wrong year is the usual mistake).
    return result


ROW = """
SELECT m.id, m.date, m.text, c.title AS chat_title, p.text AS parent_text,
       EXISTS (SELECT 1 FROM schedule_changes s WHERE s.message_id = m.id) AS known
FROM messages m JOIN chats c ON c.chat_id = m.chat_id
LEFT JOIN messages p ON p.chat_id = m.chat_id AND p.msg_id = m.reply_to
WHERE m.chat_id = %s AND m.msg_id = %s
"""


def process(model, chat_id: int, msg_id: int) -> Change | None:
    """Look at one stored message; a change it announces is saved as pending. Raises if the model is unreachable."""
    with pg.connection() as conn:
        row = pg.row(conn, MessageToRead, ROW, (chat_id, msg_id))
    # An edited message arrives again: one already turned into a change is not read twice.
    if not row or row.known or len(row.text) < MIN_CHARS:
        return None
    change = extract(model, row)
    if change:
        start, end, all_day = when(change)
        with pg.connection() as conn:
            conn.execute(
                """INSERT INTO schedule_changes (message_id, kind, subject, starts_at, ends_at, all_day, room, summary)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (message_id) DO NOTHING""",
                (row.id, change.kind, change.subject, start, end, all_day, change.room, change.summary),
            )
        log.info("found a %s in message %s: %s", change.kind, row.id, change.summary)
    return change


def admins() -> list[int]:
    """Telegram ids that approve changes (settings plus those added in the bot, see admins.py)."""
    return admins_module.everyone()


# ---- approval ---------------------------------------------------------------------------------------------


CHANGE_VIEW = """
SELECT s.id, s.message_id, s.kind, s.subject, s.starts_at, s.ends_at, s.all_day, s.room, s.summary, s.status,
       s.created_at, s.notified_at, s.decided_at,
       m.text, m.date, m.link, m.sender_name, c.title AS chat_title, c.link AS chat_link, c.group_code, c.requires_verified_group
FROM schedule_changes s JOIN messages m ON m.id = s.message_id JOIN chats c ON c.chat_id = m.chat_id
"""


def unnotified() -> list[ChangeView]:
    """Changes the users have not been told about yet, with the message they came from."""
    with pg.connection() as conn:
        return pg.rows(conn, ChangeView, CHANGE_VIEW + " WHERE s.notified_at IS NULL ORDER BY s.id")


def mark_notified(change_id: int) -> None:
    with pg.connection() as conn:
        conn.execute("UPDATE schedule_changes SET notified_at = now() WHERE id = %s", (change_id,))


def recipients(change: ChangeView) -> list[int]:
    """Telegram ids of the users a change is for, among those the bot may write to (they started it, bot_users.py): for a
    chat of group `all`, all of them; for a chat of a study group, the users of that group: the one InNoHassle knows, else
    the previously chosen group, as for search (groups.effective_group). The Max users are not told: the worker
    sends through Telegram only."""
    users = bot_users.reachable()
    if change.requires_verified_group:
        if change.group_code == groups.ALL:
            return []  # A later manual edit to 'all' must not make a private source public.
        with ThreadPoolExecutor(LOOKUPS) as pool:
            known = list(pool.map(groups.auto_group, users))
        return [user for user, group in zip(users, known, strict=True) if group == change.group_code]
    if change.group_code == groups.ALL:
        return users
    with pg.connection() as conn:
        rows = conn.execute("SELECT user_key, group_code FROM user_groups WHERE user_key LIKE 'tg:%'").fetchall()  # no parameters: % as is
    chosen = {row["user_key"]: row["group_code"] for row in rows}
    with ThreadPoolExecutor(LOOKUPS) as pool:  # One request to InNoHassle per user (cached for an hour).
        known = list(pool.map(groups.auto_group, users))
    return [user for user, group in zip(users, known, strict=True) if (group or chosen.get(f"tg:{user}", groups.ALL)) == change.group_code]


def _words(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.casefold()))


def _same_subject(subject: str, title: str) -> bool:
    """Whether an event of the calendar ("Анонс: ОБЖ", "Экзамен по ОБЖ") is about the subject of a change ("ОБЖ"):
    the words of one are among the words of the other."""
    prefix = next((p for p in KIND_TITLE.values() if title.startswith(f"{p}: ")), None)
    a, b = _words(subject), _words(title.removeprefix(f"{prefix}: ") if prefix else title)
    return bool(a and b) and (f" {a} " in f" {b} " or f" {b} " in f" {a} ")


def _earlier_event(conn, user_key: str, subject: str) -> int | None:
    """The user's event a reschedule, room change or cancellation is about: the latest added upcoming one of its subject."""
    rows = conn.execute(
        """SELECT id, title FROM personal_events
           WHERE user_key = %s AND coalesce(ends_at, starts_at) >= now() - interval '1 day' ORDER BY created_at DESC""",
        (user_key,),
    ).fetchall()
    return next((r["id"] for r in rows if _same_subject(subject, r["title"])), None)


def add_to_calendar(user_key: str, change_id: int, *, telegram_id: int | None = None) -> str | None:
    """Put a change in the user's personal calendar and say what was done; None if there is no such change.

    A reschedule or a room change of an event the user already has changes that event (it keeps its id, so calendar apps
    move it), a cancellation removes it; anything else is a new event. Twice is once."""
    with pg.connection() as conn:
        change = pg.row(conn, ChangeView, CHANGE_VIEW + " WHERE s.id = %s", (change_id,))
        if change is None:
            return None
        if change.requires_verified_group and (change.group_code == groups.ALL or groups.auto_group(telegram_id) != change.group_code):
            return None  # Guessed/forwarded callback IDs cannot disclose a protected source.
        end, _ = _offered_end(conn, change)
        link = change.link or change.chat_link
        note = f"Из чата {_origin(change)}:\n{change.text[:600]}"  # A basic group has no link: the message itself, then.
        subject = change.subject or change.summary
        earlier = _earlier_event(conn, user_key, subject) if change.kind != "announcement" and change.subject else None
        if earlier is not None and change.kind == "cancel":
            conn.execute("DELETE FROM personal_events WHERE id = %s", (earlier,))
            return f"Убрано из вашего календаря: {subject}"
        if earlier is not None and change.kind == "room_change":
            conn.execute(
                "UPDATE personal_events SET room = %s, source_url = coalesce(%s, source_url), source_note = %s WHERE id = %s",
                (change.room, link, note, earlier),
            )
            return f"Аудитория изменена в вашем календаре: {subject}"
        if earlier is not None:  # A reschedule.
            title = pg.scalar(conn, "SELECT title FROM personal_events WHERE id = %s", (earlier,))
            # The same event already at the new time (added twice) would break the uniqueness of (user, title, start).
            conn.execute("DELETE FROM personal_events WHERE user_key = %s AND title = %s AND starts_at = %s AND id <> %s",
                         (user_key, title, change.starts_at, earlier))
            conn.execute(
                """UPDATE personal_events SET starts_at = %s, ends_at = %s, all_day = %s, room = coalesce(%s, room),
                          source_url = coalesce(%s, source_url), source_note = %s WHERE id = %s""",
                (change.starts_at, end, change.all_day, change.room, link, note, earlier),
            )
            return f"Перенесено в вашем календаре: {subject}"
        title = f"{KIND_TITLE[change.kind]}: {subject}"
        conn.execute(
            """INSERT INTO personal_events (user_key, title, starts_at, ends_at, all_day, room, source_url, source_note)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
            (user_key, title, change.starts_at, end, change.all_day, change.room, link, note),
        )
    return f"Добавлено в ваш календарь: {title}"


def _origin(change: ChangeView) -> str:
    """Where a change was read (plain text): «chat», when, who."""
    sent = change.date.astimezone(settings.tz)
    return ", ".join(filter(None, [f"«{change.chat_title}»", f"{sent:%d.%m %H:%M}", change.sender_name]))


def card(change: ChangeView) -> str:
    """The text a user sees (Telegram HTML): what changed, and the message it was read from, as a link if it has one."""
    when = change.starts_at.astimezone(settings.tz)
    _validate_interval(change)
    end, suggested = change.ends_at, False
    if change.kind in ("announcement", "reschedule") and not change.all_day and end is None:
        with pg.connection() as conn:
            end, suggested = _offered_end(conn, change, prepare=True)
    lines = [f"<b>{html.escape(KIND_TITLE[change.kind])}: {html.escape(change.subject or '?')}</b>"]
    interval = f"{when:%d.%m.%Y}" + ("" if change.all_day else f" {when:%H:%M}")
    if end is not None and not change.all_day:
        end = end.astimezone(settings.tz)
        interval += f" – {end:%H:%M}" if when.date() == end.date() else f" – {end:%d.%m.%Y %H:%M}"
    lines.append(f"Когда: {interval}")
    if suggested:
        lines.append(f"Предлагаемая длительность: {personal_calendar.PROPOSED_DURATION_MINUTES} минут (окончание не указано в источнике).")
    if change.room:
        lines.append(f"Аудитория: {html.escape(change.room)}")
    source = html.escape(_origin(change))
    if link := change.link or change.chat_link:
        source = f'<a href="{html.escape(link)}">{source}</a>'
    lines += ["", f"Источник: {source}", html.escape(change.text[:600])]
    return "\n".join(lines)


def _validate_interval(change: ChangeView) -> None:
    if change.kind in ("announcement", "reschedule"):
        personal_calendar._proposal_interval({
            "starts_at": change.starts_at.isoformat(),
            "ends_at": change.ends_at.isoformat() if change.ends_at is not None else None,
            "all_day": change.all_day,
        })


def _offered_end(conn, change: ChangeView, *, prepare: bool = False) -> tuple[datetime | None, bool]:
    """Save suggestions before displaying new cards; old callbacks never invent an unseen end."""
    _validate_interval(change)
    if change.kind not in ("announcement", "reschedule") or change.all_day or change.ends_at is not None:
        return change.ends_at, False
    proposal_id = f"change:{change.id}"
    offer = pg.scalar(conn, "SELECT event FROM calendar_proposals WHERE id = %s", (proposal_id,))
    if offer is None and prepare and change.notified_at is None:
        offer = personal_calendar.proposed_event({"starts_at": change.starts_at.isoformat(), "change_id": change.id})
        conn.execute(
            "INSERT INTO calendar_proposals (id, event) VALUES (%s, %s::jsonb) ON CONFLICT DO NOTHING",
            (proposal_id, json.dumps(offer)),
        )
        offer = pg.scalar(conn, "SELECT event FROM calendar_proposals WHERE id = %s", (proposal_id,))
    if offer is None:
        return None, False
    start, end = personal_calendar._proposal_interval(offer)
    if start != change.starts_at or offer.get("change_id") != change.id or not offer.get("end_suggested"):
        raise ValueError("The saved change proposal no longer matches the event.")
    return end, True


# ---- iCalendar text (personal_calendar.py) -----------------------------------------------------------------


def _escape(text: str) -> str:
    for char, escaped in (("\\", "\\\\"), (";", "\\;"), (",", "\\,"), ("\n", "\\n")):
        text = text.replace(char, escaped)
    return text


def _fold(line: str) -> str:
    """Content lines are at most 75 octets: longer ones continue on the next line after a space."""
    out, raw = [], line.encode()
    while len(raw) > 75:
        cut = 75
        while raw[cut] & 0xC0 == 0x80:  # Not inside a multi-byte character.
            cut -= 1
        out.append(raw[:cut].decode())
        raw = b" " + raw[cut:]
    return "\r\n".join([*out, raw.decode()])
