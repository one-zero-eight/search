"""Native operations reuse domain tools, not generated HTTP write endpoints."""

import json

import pytest
from tests.mcp_native_helpers import call
from catix.innohassle import mcp_server

@pytest.fixture(autouse=True)
def verified_identity(monkeypatch):
    monkeypatch.setattr(mcp_server.token_verifier, "claims", lambda token: {"uid": "owner"})



def test_server_registration_is_complete_and_keeps_flat_arguments():
    from tests.mcp_native_helpers import registered_tools

    expected = {
        'printers_print_get_printers_status', 'maps_scenes_search_areas', 'maps_scenes_scenes',
        'clubs_get_clubs_list_clubs__get', 'music_bookings_daily_bookings', 'events_events_list_events',
        'schedule_get_schedule', 'timetable_get_courses', 'timetable_get_room_timetable',
        'timetable_get_instructor_schedule',
        'maps_find_room', 'clubs_get_clubs',
        'account_get_my_schedule', 'rooms_get_free_rooms', 'rooms_book_room', 'account_cancel_booking',
        'music_get_music_room_schedule', 'music_get_available_windows', 'music_book_music_room', 'events_get_university_events',
        'events_enroll_in_event', 'events_create_draft', 'events_update_draft',
        'sport_get_my_sport', 'sport_get_sport_trainings', 'sport_get_sports',
        'sport_sport_checkin', 'sport_get_training', 'events_get_event', 'account_get_booking',
        'when2meet_get_my_meetings', 'when2meet_get_meeting',
        'when2meet_create_meeting', 'when2meet_set_my_availability',
    }
    declared = registered_tools()
    assert set(declared) == expected
    for name, operation in declared.items():
        assert operation.name == name and operation.description
        assert operation.parameters['additionalProperties'] is False
        assert not {'runtime', 'token', 'sport_token', 'uid', 'user'} & operation.parameters['properties'].keys()
    assert declared['sport_sport_checkin'].parameters['properties']['cancel']['default'] is False
    assert 'title' in declared['rooms_book_room'].parameters['required']


@pytest.mark.parametrize('name,arguments', [
    ('music_book_music_room', {'day': '2000-01-01', 'time_from': '10:00', 'time_to': '11:00'}),
    ('events_enroll_in_event', {'event_id': 'not-a-mongo-id'}),
    ('account_cancel_booking', {'service': 'music_room', 'booking_id': 'not-an-int'}),
    ('rooms_book_room', {'room_id': 'r', 'day': '2000-01-01', 'time_from': '10:00', 'time_to': '11:00', 'title': 'meeting'}),
    ('sport_sport_checkin', {'training_id': '7'}),
    ('sport_sport_checkin', {'training_id': 7, 'runtime': {'uid': 'other'}}),
])
def test_invalid_business_arguments_are_definite_refusals(name, arguments):
    result = call(name, arguments, token='ih', sport_token='sport')
    assert result['done'] is False and result['code'] == 'invalid_arguments'


def test_unknown_write_outcome_is_not_a_decline_or_a_retry(monkeypatch, caplog):
    import httpx
    from catix.innohassle import sport as sport_api

    calls = []
    def fail(*args):
        calls.append(args)
        raise httpx.ReadTimeout('secret upstream body')
    monkeypatch.setattr(sport_api, 'check_in', fail)
    result = call('sport_sport_checkin', {'training_id': 7}, token='ih', sport_token='sport', uid='owner')
    assert result['done'] is None and result['outcome'] == 'unknown'
    assert 'retry automatically' in result['error']
    assert len(calls) == 1
    assert 'secret upstream' not in str(result) + caplog.text


def test_business_refusal_redacts_reflected_credentials(monkeypatch, caplog):
    from catix.innohassle import sport as sport_api
    from catix.innohassle.client import ServiceError

    def refuse(*args):
        raise ServiceError(403, 'Training full; token=ih-secret and sport-secret')
    monkeypatch.setattr(sport_api, 'check_in', refuse)
    result = call('sport_sport_checkin', {'training_id': 7},
        token='ih-secret', sport_token='sport-secret', uid='owner')
    assert result['done'] is False
    assert 'Training full' in result['error']
    assert 'ih-secret' not in str(result) + caplog.text
    assert 'sport-secret' not in str(result) + caplog.text


def test_sport_summary_reuses_aggregation_without_model_runtime(monkeypatch):
    from catix.innohassle import sport as sport_api

    seen = []
    monkeypatch.setattr(sport_api, 'me', lambda token: seen.append(token) or {'user_id': 22, 'student_info': {'medical_group': 'main'}})
    monkeypatch.setattr(sport_api, 'hours', lambda token, uid: seen.append((token, uid)) or {'hours_from_groups': 5, 'self_sport_hours': 2, 'required_hours': 20, 'debt': 3})
    monkeypatch.setattr(sport_api, 'current_semester', lambda token: {})
    monkeypatch.setattr(sport_api, 'my_trainings', lambda *args: [])
    result = call('sport_get_my_sport', {}, token='ih-secret', sport_token='sport-secret', uid='owner')
    assert result['hours'] == {'done': 7, 'from_trainings': 5, 'self_sport': 2, 'required': 20, 'debt': 3, 'left': 16}
    assert result['medical_group'] == 'main'
    assert seen == ['sport-secret', ('sport-secret', 22)]


def test_room_music_and_event_domain_rules_survive_native_dispatch(monkeypatch):
    from catix.innohassle import client as api, mcp_account as account_tools

    writes = []
    kwargs = {'token': 'ih-secret', 'sport_token': None, 'uid': 'owner'}
    room = {'room_id': 'r', 'title': 'meeting', 'day': '2099-01-01', 'time_from': '10:00', 'time_to': '11:00'}
    monkeypatch.setattr(api, 'can_book_room', lambda *a: (False, 'students only'))
    occupancy = []
    monkeypatch.setattr(api, 'room_bookings', lambda *a, **kw: occupancy.append((a, kw)) or [])
    monkeypatch.setattr(api, 'book_room', lambda *a: writes.append(a) or {'outlook_booking_id': 'outlook-returned-id'})
    assert call('rooms_book_room', room, **kwargs)['done'] is False
    assert not writes
    assert not occupancy
    monkeypatch.setattr(api, 'can_book_room', lambda *a: (True, None))
    result = call('rooms_book_room', room, **kwargs)
    assert result['done'] is True and result['booked']['booking_id'] == 'outlook-returned-id'
    assert writes[-1][:3] == ('ih-secret', 'r', 'meeting')
    assert occupancy == [(('ih-secret', *writes[-1][3:]), {'room_id': 'r'})]
    monkeypatch.setattr(api, 'cancel_room', lambda *a: writes.append(a))
    assert call('account_cancel_booking', {'service': 'room', 'booking_id': 'outlook-returned-id'}, **kwargs)['done'] is True
    assert writes[-1] == ('ih-secret', 'outlook-returned-id')
    music = {k: v for k, v in room.items() if k not in {'room_id', 'title'}}
    from datetime import datetime
    from catix.settings import settings
    monkeypatch.setattr(account_tools, '_now', lambda: datetime(2099, 1, 1, 8, tzinfo=settings.tz))
    monkeypatch.setattr(api, 'my_music_room_profile', lambda token: {'status': 'free'})
    monkeypatch.setattr(api, 'music_room_hours_left', lambda *a: (2, 3))
    monkeypatch.setattr(api, 'music_room_bookings', lambda *a, **kwargs: [{'time_start': '2099-01-01T10:30:00', 'time_end': '2099-01-01T11:30:00'}])
    monkeypatch.setattr(api, 'book_music_room', lambda *a: writes.append(a) or {'id': 4})
    assert call('music_book_music_room', music, **kwargs)['done'] is False
    count = len(writes)
    monkeypatch.setattr(api, 'music_room_bookings', lambda *a, **kwargs: [])
    monkeypatch.setattr(api, 'music_room_hours_left', lambda *a: (0.5, 2))
    assert call('music_book_music_room', music, **kwargs)['done'] is False
    assert len(writes) == count
    monkeypatch.setattr(api, 'music_room_hours_left', lambda *a: (2, 3))
    assert call('music_book_music_room', music, **kwargs)['booked']['booking_id'] == '4'
    monkeypatch.setattr(api, 'my_event', lambda *a: {'id': 'a' * 24, 'enrolled': False,
                        'data': {'enrollment': {'type': 'external', 'url': 'https://organizer.test/join'}}})
    monkeypatch.setattr(api, 'enroll', lambda *a: writes.append(a))
    count = len(writes)
    result = call('events_enroll_in_event', {'event_id': 'a' * 24}, **kwargs)
    assert result['done'] is False and 'external registration' in result['error']
    assert len(writes) == count
    monkeypatch.setattr(api, 'my_event', lambda *a: {'id': 'a' * 24, 'enrolled': len(writes) > count, 'enrolled_count': 0,
                        'data': {'starts_at': '2099-01-01T10:00:00+03:00', 'duration_hours': 1.5,
                                 'locales': {'en': {'name': 'Meeting'}}, 'location': {'display_name': '301'},
                                 'enrollment': {'type': 'internal'}}})
    assert call('events_enroll_in_event', {'event_id': 'a' * 24}, **kwargs)['enrolled'] is True
    assert writes[-1] == ('ih-secret', 'a' * 24)


def test_room_availability_and_account_schedule_keep_aggregations(monkeypatch):
    from datetime import date
    from catix.innohassle import client as api, mcp_account as account_tools

    kwargs = {'token': 'ih-secret', 'sport_token': 'sport-secret', 'uid': 'verified'}
    monkeypatch.setattr(api, 'bookable_rooms', lambda token: [
        {'id': 'free', 'title': 'Free', 'capacity': 10, 'access_level': 'yellow'},
        {'id': 'busy', 'title': 'Busy', 'capacity': 5}])
    monkeypatch.setattr(api, 'room_bookings', lambda *a: [
        {'room_id': 'busy', 'start': '2099-01-01T10:30:00', 'end': '2099-01-01T11:30:00'}])
    permissions = []
    monkeypatch.setattr(api, 'can_book_room', lambda *a: permissions.append(a) or (True, None))
    result = call('rooms_get_free_rooms', {'day': '2099-01-01', 'time_from': '10:00', 'time_to': '11:00'}, **kwargs)
    assert result['free'] == [{'room_id': 'free', 'title': 'Free', 'capacity': 10, 'who': 'students'}]
    assert result['booked'] == ['busy']
    assert len(permissions) == 1 and permissions[0][:2] == ('ih-secret', 'free')
    assert (permissions[0][2].hour, permissions[0][3].hour) == (10, 11)
    monkeypatch.setattr(account_tools, '_calendar', lambda *a: ([{'kind': 'class', 'title': 'Math'}], {}))
    monkeypatch.setattr(account_tools, '_bookings', lambda *a: ([{'booking_id': 'outlook-id'}], []))
    result = call('account_get_my_schedule', {'date_from': '2099-01-01', 'date_to': '2099-01-02'}, **kwargs)
    assert result['schedule'] == [{'kind': 'class', 'title': 'Math'}]
    assert result['bookings'] == [{'booking_id': 'outlook-id'}]
    assert 'ai_calendar' not in result
