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


def test_tonight_is_the_evening_of_the_day_written():
    """'room 108 tonight between 18:30-19:10' was told as 'в ночь с 23 на 24 октября': tonight is the day itself."""
    posted = datetime(2026, 10, 23, 17, 26, tzinfo=TZ)
    assert dates.resolve("you can pass by to the room 108 tonight between 18:30-19:10", posted, NOW) == ["'tonight' = 2026-10-23 Fri (in 2 days)"]


def test_what_is_coming_is_a_day_from_today_or_a_recent_message_without_one():
    """For a question about what is coming the chat searches keep only these (agent/tools.py asks_upcoming), with a period
    given by the model or not: it gave one a time and not the next."""
    written = datetime(2026, 10, 1, tzinfo=TZ)
    assert not dates.coming("Концерт 4 октября в 15:00", written, NOW)  # over
    assert dates.coming("Регистрация до 4 октября, финал 25 октября", written, NOW)  # one day still ahead
    assert dates.coming("Сегодня квиз в 18:00", NOW, NOW)
    # A message that names no day: recent, it may be of something near; months old, it is not ("registration is open" of June).
    assert dates.coming("Регистрация на кубок открыта", datetime(2026, 10, 10, tzinfo=TZ), NOW)
    assert not dates.coming("Регистрация на кубок открыта", datetime(2026, 6, 10, tzinfo=TZ), NOW)
    # A period: from today at the earliest ("в октябре" asked on the 21st), to its end.
    assert not dates.coming("Квиз 20 октября", written, NOW, date(2026, 10, 1), date(2026, 10, 31))
    assert dates.coming("Квиз 30 октября", written, NOW, date(2026, 10, 1), date(2026, 10, 31))
    assert not dates.coming("Квиз 3 ноября", written, NOW, date(2026, 10, 1), date(2026, 10, 31))
    # A period ahead ("на следующей неделе"): a message without a day says nothing of it, however recent.
    assert not dates.coming("Регистрация на кубок открыта", NOW, NOW, date(2026, 10, 26), date(2026, 11, 1))


def test_a_weekly_digest_is_of_its_own_week():
    """"Много событий недели ждет тебя" of three weeks ago names no day, but it is about its own week, which is over."""
    digest = "Много событий недели ждет тебя в Инно\n• открытый микрофон\n• классический квиз\nВсе мероприятия недели"
    assert not dates.coming(digest, datetime(2026, 10, 12, tzinfo=TZ), NOW)
    assert dates.coming(digest, datetime(2026, 10, 19, tzinfo=TZ), NOW)  # this week: it ends on Sunday the 25th
    next_week = datetime(2026, 10, 14, tzinfo=TZ)  # a Wednesday: its next week is 19-25 October
    assert dates.coming("На следующей неделе квиз", next_week, NOW) and dates.coming("Quiz next week", next_week, NOW)
    assert not dates.coming("На этой неделе квиз", next_week, NOW)


def test_what_is_coming_is_told_from_what_happens_if():
    from catix.agent.tools import asks_upcoming

    coming = ["какой интернациональный ивент будет в университете?", "когда будет мидтерм по матану?", "ближайшие дедлайны",
              "upcoming exams?", "what events are coming this week"]  # fmt: skip
    other = ["что будет если я пропущу экзамен?", "what happens if I miss the exam", "будет ли стипендия?",
             "когда был мидтерм по матану?", "какие тесты были с сентября"]  # fmt: skip
    assert [q for q in coming if not asks_upcoming(q)] == [] and [q for q in other if asks_upcoming(q)] == []


def test_a_period_lists_a_message_by_the_soonest_of_its_days_in_it():
    """read_chats with event_from/event_to lists what is on in a period by this day (agent/tools.py): an olympiad of
    15 November announced on 13 October is in the week of 9-15 November, a hackathon of 13-16 November from its 13th."""
    written, week = datetime(2026, 10, 13, tzinfo=TZ), (date(2026, 11, 9), date(2026, 11, 15))
    assert dates.first_day_in("Олимпиада пройдёт 15 ноября, заявки до 9 октября", written, NOW, *week) == date(2026, 11, 15)
    assert dates.first_day_in("Хакатон 13–16 ноября", written, NOW, *week) == date(2026, 11, 13)  # a range, not its end
    assert dates.first_day_in("Фестиваль с 5 по 10 ноября", written, NOW, *week) == date(2026, 11, 9)  # begun before
    assert dates.first_day_in("Квиз 20 ноября", written, NOW, *week) is None
    assert dates.first_day_in("На следующей неделе квиз", datetime(2026, 11, 6, tzinfo=TZ), NOW, *week) == date(2026, 11, 9)


def test_the_days_a_question_names_are_worked_out_for_the_model():
    """On Friday 6 November the model took "на прошлой неделе" for 2-6 November (agent/core.py QuestionNoteMiddleware)."""
    friday = datetime(2026, 11, 6, 18, 0, tzinfo=TZ)
    assert dates.question_dates("что было на прошлой неделе?", friday) == ["'прошлой неделе' = 2026-10-26 Mon to 2026-11-01 Sun"]
    assert dates.question_dates("какие мероприятия будут на следующей неделе?", friday) == [
        "'следующей неделе' = 2026-11-09 Mon to 2026-11-15 Sun"
    ]
    # What was: the last Monday and this January; what will be: the next Monday and the next January.
    assert dates.question_dates("что было в понедельник?", friday) == ["'в понедельник' = 2026-11-02 Mon (4 days ago)"]
    assert dates.question_dates("что будет в понедельник?", friday) == ["'в понедельник' = 2026-11-09 Mon (in 3 days)"]
    assert dates.question_dates("что было 15 января", friday) == ["'15 января' = 2026-01-15 Thu (295 days ago)"]
    assert dates.question_dates("когда экзамен 15 января", friday) == ["'15 января' = 2027-01-15 Fri (in 70 days)"]
    assert dates.question_dates("что было на прошлых выходных", friday) == ["'на прошлых выходных' = 2026-10-31 Sat to 2026-11-01 Sun"]
    assert dates.question_dates("что писали в прошлом месяце?", friday) == ["'в прошлом месяце' = 2026-10-01 Thu to 2026-10-31 Sat"]
    assert dates.question_dates("когда мидтерм по итп", friday) == []
