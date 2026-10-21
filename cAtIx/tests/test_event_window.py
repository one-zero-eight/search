"""A period of events is not a period of writing (common/dates.py `mentions_between`), without a model."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from catix.common import dates

TZ = ZoneInfo("Europe/Moscow")
NOW = datetime(2026, 10, 21, 13, 0, tzinfo=TZ)
WEEK = (date(2026, 10, 19), date(2026, 10, 25))
ANNOUNCEMENT = "The Midterm exam details:\nDate: 23 October 2026\nTime: 09:00-(~)10:00"


def test_an_announcement_of_an_earlier_day_is_about_the_week_of_the_event():
    posted = datetime(2026, 10, 5, 11, 22, tzinfo=TZ)  # two weeks before: a filter on the writing day would drop it
    assert dates.mentions_between(ANNOUNCEMENT, posted, NOW, *WEEK)


def test_a_message_about_another_week_is_not():
    assert not dates.mentions_between(ANNOUNCEMENT, datetime(2026, 10, 5, tzinfo=TZ), NOW, date(2026, 10, 26), date(2026, 11, 1))


def test_loose_words_count_relative_to_the_day_written():
    assert dates.mentions_between("Завтра мидтерм", datetime(2026, 10, 22, tzinfo=TZ), NOW, *WEEK)
    assert not dates.mentions_between("Завтра мидтерм", datetime(2026, 9, 1, tzinfo=TZ), NOW, *WEEK)


def test_resolve_still_gives_the_same_lines():
    assert dates.resolve(ANNOUNCEMENT, datetime(2026, 10, 5, tzinfo=TZ), NOW) == ["'23 October 2026' = 2026-10-23 Fri (in 2 days)"]
