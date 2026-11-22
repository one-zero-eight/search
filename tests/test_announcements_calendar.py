"""Schedule changes are applied by the user to their own calendar (worker/changes.py), without a model.

`add_to_calendar` puts the change in that user's calendar only, and twice is once; a change of a chat that is not among
the user's chats is not found. A reschedule, room change or cancellation of an event the user has changes or removes that
event instead of adding another.
"""

from datetime import datetime, timedelta, timezone

import pytest

from catix import personal_calendar
from catix.db import pg
from catix.worker import changes

MINE, OTHER = "tg:999000011", "tg:999000012"

SOON = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=2)


def found(chat, nth: int, kind: str, subject: str, starts_at: datetime, room: str | None = None) -> int:
    """A change found in the nth message of the synthetic chat (a message has at most one)."""
    with pg.connection() as conn:
        message_id = pg.scalar(conn, "SELECT id FROM messages WHERE chat_id = %s ORDER BY id OFFSET %s LIMIT 1", (chat, nth))
        return pg.scalar(
            conn,
            """INSERT INTO schedule_changes (message_id, kind, subject, starts_at, room, summary)
               VALUES (%s, %s, %s, %s, %s, 'тест') RETURNING id""",
            (message_id, kind, subject, starts_at, room),
        )


@pytest.fixture
def change(chat):
    yield found(chat, 0, "announcement", "Ботаника", SOON, "301")
    with pg.connection() as conn:
        conn.execute("DELETE FROM schedule_changes WHERE message_id IN (SELECT id FROM messages WHERE chat_id = %s)", (chat,))
        conn.execute("DELETE FROM personal_events WHERE user_key = ANY(%s)", ([MINE, OTHER],))


def test_accepting_puts_the_change_in_that_users_calendar_only(chat, change):
    assert changes.add_to_calendar(MINE, change, chat_ids={chat}) == ("added", "Анонс: Ботаника")
    changes.add_to_calendar(MINE, change, chat_ids={chat})  # Twice is once.
    mine = personal_calendar.upcoming(MINE)
    assert [e.title for e in mine] == ["Анонс: Ботаника"] and mine[0].room == "301"
    assert personal_calendar.upcoming(OTHER) == []
    assert "SUMMARY:Анонс: Ботаника" in personal_calendar.ics(MINE)
    assert "DESCRIPTION:Из чата «" in personal_calendar.ics(MINE)  # The message it was read from, a link or not.
    assert changes.add_to_calendar(MINE, -1, chat_ids={chat}) is None
    assert changes.add_to_calendar(OTHER, change, chat_ids=set()) is None  # Not a chat of the user.
    assert personal_calendar.upcoming(OTHER) == []


def test_a_reschedule_moves_the_event_the_user_has(chat, change):
    """The case of ОБЖ: an exam announced for the 1st, then moved to the 3rd, was two events."""
    changes.add_to_calendar(MINE, change, chat_ids={chat})
    before = personal_calendar.upcoming(MINE)[0]
    later = SOON + timedelta(days=2)
    assert changes.add_to_calendar(MINE, found(chat, 1, "reschedule", "ботаника", later), chat_ids={chat})[0] == "moved"
    after = personal_calendar.upcoming(MINE)
    assert [(e.id, e.title, e.starts_at, e.room) for e in after] == [(before.id, "Анонс: Ботаника", later, "301")]


def test_a_room_change_and_a_cancellation_change_the_event_the_user_has(chat, change):
    changes.add_to_calendar(MINE, change, chat_ids={chat})
    changes.add_to_calendar(MINE, found(chat, 1, "room_change", "Ботаника", SOON, "108"), chat_ids={chat})
    assert [(e.title, e.room) for e in personal_calendar.upcoming(MINE)] == [("Анонс: Ботаника", "108")]
    assert changes.add_to_calendar(MINE, found(chat, 2, "cancel", "Ботаника", SOON), chat_ids={chat})[0] == "removed"
    assert personal_calendar.upcoming(MINE) == []


def test_a_reschedule_of_an_event_the_user_does_not_have_is_a_new_event(chat, change):
    changes.add_to_calendar(MINE, found(chat, 1, "reschedule", "Птицефабрика", SOON), chat_ids={chat})
    assert [e.title for e in personal_calendar.upcoming(MINE)] == ["Перенос: Птицефабрика"]
