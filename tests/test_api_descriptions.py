"""Confirmation templates describe exact action arguments, never execute reads."""

from copy import deepcopy

import pytest

from catix.agent.api_descriptions import describe_action
from catix.innohassle.mcp_access import CONFIRMATION_TOOLS


CASES = [
    ("rooms_book_room", {"room_id": "su-office", "day": "2099-01-02", "time_from": "10:00", "time_to": "11:00", "title": "Planning"},
     "Забронировать аудиторию su-office на 2099-01-02, 10:00–11:00: «Planning».",
     "Book room su-office for 2099-01-02, 10:00–11:00: “Planning”."),
    ("music_book_music_room", {"day": "2099-01-02", "time_from": "10:00", "time_to": "11:00"},
     "Забронировать музыкальную комнату (спорткомплекс) на 2099-01-02, 10:00–11:00.",
     "Book the music room (sports complex) for 2099-01-02, 10:00–11:00."),
    ("account_cancel_booking", {"service": "room", "booking_id": "AAMk=opaque+ID"},
     "Отменить вашу бронь аудитории: AAMk=opaque+ID.", "Cancel your room booking: AAMk=opaque+ID."),
    ("account_cancel_booking", {"service": "music_room", "booking_id": "123"},
     "Отменить вашу бронь музыкальной комнаты: 123.", "Cancel your music room booking: 123."),
    ("events_enroll_in_event", {"event_id": "0123456789abcdef01234567", "leave": False},
     "Записать вас на мероприятие 0123456789abcdef01234567.", "Enrol you in event 0123456789abcdef01234567."),
    ("events_enroll_in_event", {"event_id": "0123456789abcdef01234567", "leave": True},
     "Отменить вашу запись на мероприятие 0123456789abcdef01234567.", "Cancel your enrolment in event 0123456789abcdef01234567."),
    ("sport_sport_checkin", {"training_id": 7, "cancel": False},
     "Записать вас на тренировку #7.", "Check you in to the training #7."),
    ("sport_sport_checkin", {"training_id": 7, "cancel": True},
     "Отменить вашу запись на тренировку #7.", "Cancel your check-in to the training #7."),
    ("when2meet_create_meeting", {"name": "Planning", "slots": ["2099-01-02T10:00:00+03:00"],
                                "timezone": "Europe/Moscow", "specific_time": True, "description": "Team meeting"},
     "Создать опрос When2Meet «Planning». Часовой пояс: Europe/Moscow. Режим: время. Слоты: 2099-01-02T10:00:00+03:00. Описание: Team meeting.",
     "Create When2Meet poll “Planning”. Timezone: Europe/Moscow. Mode: times. Slots: 2099-01-02T10:00:00+03:00. Description: Team meeting."),
    ("when2meet_create_meeting", {"name": "Planning", "slots": ["2099-01-02T00:00:00+03:00"],
                                "timezone": "Europe/Moscow", "specific_time": False, "description": None},
     "Создать опрос When2Meet «Planning». Часовой пояс: Europe/Moscow. Режим: даты. Слоты: 2099-01-02T00:00:00+03:00. Описание: не задано.",
     "Create When2Meet poll “Planning”. Timezone: Europe/Moscow. Mode: dates. Slots: 2099-01-02T00:00:00+03:00. Description: none."),
    ("when2meet_set_my_availability", {"meeting_ref": "team-42", "availability": ["2099-01-02T10:00:00+03:00"]},
     "Заменить все ваши отмеченные слоты в When2Meet team-42 на: 2099-01-02T10:00:00+03:00.",
     "Replace all your marked slots in When2Meet team-42 with: 2099-01-02T10:00:00+03:00."),
    ("when2meet_set_my_availability", {"meeting_ref": "team-42", "availability": []},
     "Очистить все ваши отмеченные слоты в When2Meet team-42.",
     "Clear all your marked slots in When2Meet team-42."),
    ("events_create_draft", {"name": "Draft", "description": "Text", "locale": "en"},
     "Создать черновик мероприятия. Язык: en. Название: Draft. Описание: Text. Неуказанные поля останутся незаполненными. Без отправки на модерацию и публикации. Сохранение неатомарное.",
     "Create event draft. Language: en. Name: Draft. Description: Text. Unspecified fields remain unset. No submission for moderation or publication. Saving is not atomic."),
    ("events_update_draft", {"draft_id": "a" * 24, "locale": "ru", "description": ""},
     "Изменить черновик мероприятия aaaaaaaaaaaaaaaaaaaaaaaa. Язык: ru. Очистить описание. Остальные поля и языки не изменяются. Без отправки на модерацию и публикации. Сохранение неатомарное.",
     "Update event draft aaaaaaaaaaaaaaaaaaaaaaaa. Language: ru. Clear description. Other fields and languages stay unchanged. No submission for moderation or publication. Saving is not atomic."),
]


@pytest.mark.parametrize("name,arguments,ru,en", CASES)
@pytest.mark.parametrize("language", ["ru", "en"])
def test_known_action_description(name, arguments, ru, en, language):
    original = deepcopy(arguments)
    assert describe_action(name, arguments, language) == (ru if language == "ru" else en)
    assert arguments == original


def test_templates_cover_all_confirmed_operations():
    assert {name for name, *_ in CASES} == CONFIRMATION_TOOLS


@pytest.mark.parametrize("name", ["unknown", "preview_tool", "maps_scenes_scenes"])
def test_unknown_or_read_operations_have_no_confirmation(name):
    with pytest.raises(ValueError, match="confirmation template"):
        describe_action(name, {}, "en")
