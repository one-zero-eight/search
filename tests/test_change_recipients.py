"""Schedule changes go to the users and each decides for themselves (worker/changes.py), without a model.

A change from a chat of a study group goes to the users of that group (/mygroup); from a chat for everybody, to every user
the bot knows. "✅ В мой календарь" puts it in that user's calendar only, and twice is once. A reschedule, room change or
cancellation of an event the user has changes or removes that event instead of adding another.
"""

from datetime import datetime, timedelta, timezone

import pytest

from catix import groups, personal_calendar
from catix.db import pg
from catix.worker import changes

GROUP = "B26-ZZ-98"
MINE, OTHER, EVERYBODY = "tg:999000011", "tg:999000012", "tg:999000013"


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
    for key, group in ((MINE, GROUP), (OTHER, "B26-ZZ-97"), (EVERYBODY, groups.ALL)):
        groups.set_user_group(key, group)
    yield found(chat, 0, "announcement", "Ботаника", SOON, "301")
    groups.set_chat_group(chat, groups.ALL)
    with pg.connection() as conn:
        conn.execute("DELETE FROM schedule_changes WHERE message_id IN (SELECT id FROM messages WHERE chat_id = %s)", (chat,))
        conn.execute("DELETE FROM user_groups WHERE user_key = ANY(%s)", ([MINE, OTHER, EVERYBODY],))
        conn.execute("DELETE FROM personal_events WHERE user_key = ANY(%s)", ([MINE, OTHER, EVERYBODY],))


def view(change_id: int):
    return next(c for c in changes.unnotified() if c.id == change_id)


def test_a_change_of_a_group_chat_goes_to_that_group_only(chat, change):
    groups.set_chat_group(chat, GROUP)
    sent = changes.recipients(view(change))
    assert 999000011 in sent
    assert 999000012 not in sent and 999000013 not in sent


def test_a_change_of_a_chat_for_everybody_goes_to_every_user(chat, change):
    sent = changes.recipients(view(change))
    assert {999000011, 999000012, 999000013} <= set(sent)


def test_accepting_puts_the_change_in_that_users_calendar_only(change):
    assert "Анонс: Ботаника" in changes.add_to_calendar(MINE, change)
    changes.add_to_calendar(MINE, change)  # Twice is once.
    mine = personal_calendar.upcoming(MINE)
    assert [e.title for e in mine] == ["Анонс: Ботаника"] and mine[0].room == "301"
    assert personal_calendar.upcoming(OTHER) == []
    assert "SUMMARY:Анонс: Ботаника" in personal_calendar.ics(MINE)
    assert changes.add_to_calendar(MINE, -1) is None


def test_a_reschedule_moves_the_event_the_user_has(chat, change):
    """The case of ОБЖ: an exam announced for the 1st, then moved to the 3rd, was two events."""
    changes.add_to_calendar(MINE, change)
    before = personal_calendar.upcoming(MINE)[0]
    later = SOON + timedelta(days=2)
    assert "Перенесено" in changes.add_to_calendar(MINE, found(chat, 1, "reschedule", "ботаника", later))
    after = personal_calendar.upcoming(MINE)
    assert [(e.id, e.title, e.starts_at, e.room) for e in after] == [(before.id, "Анонс: Ботаника", later, "301")]


def test_a_room_change_and_a_cancellation_change_the_event_the_user_has(chat, change):
    changes.add_to_calendar(MINE, change)
    changes.add_to_calendar(MINE, found(chat, 1, "room_change", "Ботаника", SOON, "108"))
    assert [(e.title, e.room) for e in personal_calendar.upcoming(MINE)] == [("Анонс: Ботаника", "108")]
    assert "Убрано" in changes.add_to_calendar(MINE, found(chat, 2, "cancel", "Ботаника", SOON))
    assert personal_calendar.upcoming(MINE) == []


def test_a_reschedule_of_an_event_the_user_does_not_have_is_a_new_event(chat, change):
    changes.add_to_calendar(MINE, found(chat, 1, "reschedule", "Птицефабрика", SOON))
    assert [e.title for e in personal_calendar.upcoming(MINE)] == ["Перенос: Птицефабрика"]
