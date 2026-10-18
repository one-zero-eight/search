"""Schedule changes announced in chats (a test moved, a lecture in another room, a cancelled class) as a calendar feed.

The worker (worker.py, `catix-worker`) gets the id of every new message from a Redis stream. The model decides
whether the message puts something on the calendar (a reschedule, a room change, a cancellation or a new event) and,
if so, when and where. A found change is stored as `pending`; an admin approves it in Telegram (bot.py) and only
approved changes are published as an iCalendar feed (feed.py serves it) that InNoHassle links as an external
calendar (`catix-feed link`). The stream carries only new messages, so history is not scanned.
"""

import html
import logging
from datetime import date, datetime, time, timedelta, timezone

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from catix import admins as admins_module
from catix.common import dates
from catix.db import pg
from catix.agent import tracing
from catix.db.rows import ChangeKind, ChangeView, MessageToRead
from catix.settings import settings

log = logging.getLogger("catix.changes")

DEFAULT_LENGTH = timedelta(minutes=90)  # A class; used when the message gives no end.

MIN_CHARS = 15  # "ок", "спасибо", a sticker caption: nothing to decide, so the model is not asked.
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


class Change(BaseModel):
    is_change: bool
    kind: ChangeKind | None = None
    subject: str | None = None
    day: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    room: str | None = None
    summary: str = Field("", description="One short sentence in Russian.")


def when(change: Change) -> tuple[datetime, datetime | None, bool]:
    """Start, end and whether the event lasts the whole day (no time was stated)."""
    day = change.day
    assert day is not None  # extract() only returns changes with a day
    if change.start_time is None:
        return datetime.combine(day, time(0), settings.tz), None, True
    start = datetime.combine(day, change.start_time, settings.tz)
    end = datetime.combine(day, change.end_time, settings.tz) if change.end_time else None
    return start, end if end and end > start else None, False


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
    prompt = PROMPT.format(
        sent=f"{sent:%Y-%m-%d %H:%M}",
        weekday=f"{sent:%A}",
        chat=row.chat_title,
        parent=parent,
        text=row.text[:1500],
        hints=("Dates in the message, resolved: " + "; ".join(resolved) + "\n") if resolved else "",
    )
    result: Change = model.invoke(prompt, config=tracing.run_config("changes", name="schedule-change-detection"))
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
       m.text, m.date, m.link, m.sender_name, c.title AS chat_title, c.link AS chat_link, c.group_code
FROM schedule_changes s JOIN messages m ON m.id = s.message_id JOIN chats c ON c.chat_id = m.chat_id
"""


def unnotified() -> list[ChangeView]:
    """Pending changes the admins have not been told about yet, with the message they came from."""
    with pg.connection() as conn:
        return pg.rows(conn, ChangeView, CHANGE_VIEW + " WHERE s.status = 'pending' AND s.notified_at IS NULL ORDER BY s.id")


def mark_notified(change_id: int) -> None:
    with pg.connection() as conn:
        conn.execute("UPDATE schedule_changes SET notified_at = now() WHERE id = %s", (change_id,))


def decide(change_id: int, approved: bool) -> bool:
    """Approve or reject a pending change; False if it was already decided."""
    with pg.connection() as conn:
        done = pg.scalar(
            conn,
            "UPDATE schedule_changes SET status = %s, decided_at = now() WHERE id = %s AND status = 'pending' RETURNING id",
            ("approved" if approved else "rejected", change_id),
        )
    return done is not None


def card(change: ChangeView) -> str:
    """The text an admin sees (Telegram HTML): what changed, and the message it was read from, as a link if it has one."""
    when = change.starts_at.astimezone(settings.tz)
    lines = [f"<b>{html.escape(KIND_TITLE[change.kind])}: {html.escape(change.subject or '?')}</b>"]
    lines.append(f"Когда: {when:%d.%m.%Y}" + ("" if change.all_day else f" {when:%H:%M}"))
    if change.room:
        lines.append(f"Аудитория: {html.escape(change.room)}")
    sent = change.date.astimezone(settings.tz)
    source = f"«{html.escape(change.chat_title)}», {sent:%d.%m %H:%M}, {html.escape(change.sender_name or '')}"
    if link := change.link or change.chat_link:
        source = f'<a href="{html.escape(link)}">{source}</a>'
    lines += ["", f"Источник: {source}", html.escape(change.text[:600])]
    return "\n".join(lines)


# ---- feed -------------------------------------------------------------------------------------------------


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


def feed_ics(group: str | None = None) -> str:
    """Approved changes as an iCalendar document. With a group: changes of its chats and of chats for everybody."""
    since = datetime.now(timezone.utc) - timedelta(days=settings.feed_days_back)
    with pg.connection() as conn:
        rows = pg.rows(
            conn,
            ChangeView,
            CHANGE_VIEW
            + """ WHERE s.status = 'approved' AND s.starts_at >= %s
                   AND (%s::text IS NULL OR c.group_code IN ('all', %s::text)) ORDER BY s.starts_at""",
            (since, group, group),
        )
    stamp = lambda t: t.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")  # noqa: E731
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ctx//schedule changes//RU", "CALSCALE:GREGORIAN",
             "X-WR-CALNAME:Изменения расписания (из чатов)"]  # fmt: skip
    for r in rows:
        title = f"{KIND_TITLE[r.kind]}: {r.subject or r.summary}"
        starts = r.starts_at
        if r.all_day:
            # No time was stated. All-day events (VALUE=DATE) are not shown by InNoHassle, so the event gets the
            # same form as any other: a start time (CHANGES_DEFAULT_TIME) and the usual length, and says so.
            starts = datetime.combine(r.starts_at.astimezone(settings.tz).date(), settings.changes_default_time, settings.tz)
        end = starts + (r.ends_at - r.starts_at if r.ends_at and not r.all_day else DEFAULT_LENGTH)
        span = [f"DTSTART:{stamp(starts)}", f"DTEND:{stamp(end)}"]
        description = f"{r.summary}\nИсточник: «{r.chat_title}», {r.date.astimezone(settings.tz):%d.%m.%Y}"
        if r.all_day:
            description += "\nВремя в сообщении не указано"
        link = r.link or r.chat_link
        if link:
            description += f"\n{link}"
        lines += ["BEGIN:VEVENT", f"UID:change-{r.id}@ctx", f"DTSTAMP:{stamp(r.decided_at or r.created_at)}",
                  *span, f"SUMMARY:{_escape(title)}",
                  f"DESCRIPTION:{_escape(description)}"]  # fmt: skip
        if r.room:
            lines.append(f"LOCATION:{_escape(r.room)}")
        if link:
            lines.append(f"URL:{link}")  # Calendar apps show it as a clickable link.
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
