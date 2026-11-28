"""External-service business behavior exercised through the actual MCP leaves."""
from datetime import datetime, timedelta

import httpx
import pytest
from icalendar import Calendar, Event

from catix.innohassle import client as api, sport, mcp_server
from catix.settings import settings
from tests.mcp_native_helpers import call


AUTH = {'token': 'synthetic-ih-credential', 'sport_token': 'synthetic-sport-credential', 'uid': 'owner'}


@pytest.fixture(autouse=True)
def verified(monkeypatch):
    monkeypatch.setattr(mcp_server.token_verifier, 'claims', lambda token: {'uid': 'owner'})


def training(number=7, *, name='Volleyball', checked=False, available=True, **extra):
    return {'checked_in': checked, 'can_check_in': available, 'training': {
        'id': number, 'sport_name': name, 'group_name': 'Beginners',
        'start': '2099-01-01T10:00:00+03:00', 'end': '2099-01-01T11:30:00+03:00',
        'max_checkins': 20, 'checkins_count': 3, 'training_location': {'name': 'Court A'}, **extra}}


def test_trainings_keep_filter_capacity_signup_flags_and_truncation(monkeypatch):
    rows = [training(), training(8, checked=True), training(9, available=False, checkins_count=25),
            training(10, name='Swimming')]
    observed = []
    monkeypatch.setattr(sport, 'my_trainings', lambda *a: observed.append(a) or rows)
    args = {'date_from': '2099-01-01', 'date_to': '2099-01-01', 'sport': 'volley'}
    result = call('sport_get_sport_trainings', args, **AUTH)
    assert [item['training_id'] for item in result['trainings']] == [7, 8, 9]
    assert result['trainings'][0] == {'training_id': 7, 'date': '2099-01-01 Thu',
        'name': 'Volleyball (Beginners)', 'time': '10:00-11:30', 'place': 'Court A',
        'starts_at': '2099-01-01T10:00:00+03:00', 'ends_at': '2099-01-01T11:30:00+03:00',
        'places_left': 17, 'checked_in': False, 'can_check_in': True}
    assert result['trainings'][1]['checked_in'] is True and 'can_check_in' not in result['trainings'][1]
    assert result['trainings'][2]['places_left'] == 0 and result['trainings'][2]['can_check_in'] is False
    assert 'no places left' in result['rules']
    assert observed[0][0] == AUTH['sport_token'] and observed[0][1].tzinfo == settings.tz
    assert observed[0][2] - observed[0][1] == timedelta(days=1)
    empty = call('sport_get_sport_trainings', {**args, 'sport': 'Tennis'}, **AUTH)
    assert empty['trainings'] == [] and 'Swimming' in empty['note']
    rows[:] = [training(i) for i in range(45)]
    limited = call('sport_get_sport_trainings', args, **AUTH)
    assert len(limited['trainings']) == 40 and limited['more'] == 5


def test_sports_details_keep_trainers_rules_and_safe_refusals(monkeypatch):
    monkeypatch.setattr(sport, 'sports', lambda token: [{'id': 2, 'name': 'Yoga',
        'description': '  Mind   and body ', 'groups': [{'display_name': 'Group A', 'capacity': 8,
        'trainers': [{'full_name': 'Teacher', 'email': 'teacher@example.test'}],
        'allowed_medical_groups': ['main'], 'is_accredited': False, 'is_paid': True, 'is_club': True}]}])
    detail = call('sport_get_sports', {'sport': ' yoga '}, **AUTH)['sports'][0]
    assert detail['description'] == 'Mind and body'
    assert detail['groups'] == [{'name': 'Group A', 'capacity': 8,
        'trainers': [{'name': 'Teacher', 'email': 'teacher@example.test'}], 'medical_groups': ['main'],
        'accredited': False, 'paid': True, 'club': True}]
    assert call('sport_get_sports', {}, **AUTH)['sports'] == ['Yoga']
    assert 'No sport' in call('sport_get_sports', {'sport': 'Running'}, **AUTH)['error']
    monkeypatch.setattr(sport, 'me', lambda token: {'student_info': None})
    assert 'no sport hours' in call('sport_get_my_sport', {}, **AUTH)['error']


def test_external_account_schedule_has_ics_and_bookings_but_no_local_calendar(monkeypatch):
    start = datetime(2099, 1, 1, 10, tzinfo=settings.tz)
    calendars = {}
    for kind in ['class', 'sport', 'event']:
        calendar, event = Calendar(), Event()
        event.add('uid', kind)
        event.add('summary', kind.title())
        event.add('dtstart', start)
        event.add('dtend', start + timedelta(hours=1))
        calendar.add_component(event)
        calendars[kind] = calendar.to_ical()
    seen = []
    def read(token, kind):
        seen.append((token, kind))
        return calendars[kind]
    monkeypatch.setattr(api, 'my_calendar_ics', read)
    monkeypatch.setattr(api, 'my_calendar_groups', lambda token: (1, ['core']))
    monkeypatch.setattr(api, 'event_groups', lambda **kw: [{'alias': 'core', 'tags': []}])
    monkeypatch.setattr(api, 'my_group_calendar_ics', lambda token, user_id, alias: read(token, 'class'))
    monkeypatch.setattr(api, 'my_music_room_bookings', lambda token: [
        {'id': 42, 'time_start': start.isoformat(), 'time_end': (start + timedelta(hours=1)).isoformat()}])
    monkeypatch.setattr(api, 'my_room_bookings', lambda *a: [{'outlook_booking_id': 'AA+/BB==',
        'room_id': 'r', 'title': 'Study', 'start': start.isoformat(), 'end': (start + timedelta(hours=1)).isoformat()}])
    args = {'date_from': '2099-01-01', 'date_to': '2099-01-01'}
    result = call('account_get_my_schedule', args, **AUTH)
    assert {item['kind'] for item in result['schedule']} == {'class', 'sport', 'event'}
    assert {item['booking_id'] for item in result['bookings']} == {'42', 'AA+/BB=='}
    assert 'ai_calendar' not in result and 'not_read' not in result
    assert set(seen) == {(AUTH['token'], kind) for kind in calendars}
    def slow(token, kind):
        if kind == 'sport':
            raise httpx.ReadTimeout('sensitive detail')
        return calendars[kind]
    monkeypatch.setattr(api, 'my_calendar_ics', slow)
    partial = call('account_get_my_schedule', args, **AUTH)
    assert {item['kind'] for item in partial['schedule']} == {'class', 'event'}
    assert partial['not_read'] == ['sport: InNoHassle did not answer (ReadTimeout)']
    assert 'sensitive detail' not in str(partial)


def test_event_details_enrolment_leave_and_music_cancel_keep_native_contract(monkeypatch):
    writes = []
    event_id = 'a' * 24
    event = {'id': event_id, 'enrolled_count': 2, 'data': {
        'starts_at': '2099-01-01T10:00:00+03:00', 'duration_hours': 2,
        'locales': {'en': {'name': 'Workshop', 'description': 'Build things'}},
        'enrollment': {'type': 'innohassle', 'capacity': 20},
        'location': {'display_name': 'Room 108'}, 'hosts': [{'display_name': 'Club'}]}}
    monkeypatch.setattr(api, 'events', lambda *a: [event])
    monkeypatch.setattr(api, 'event', lambda identifier, **kw: event)
    monkeypatch.setattr(api, 'my_event', lambda *a: {**event, 'enrolled': not writes})
    monkeypatch.setattr(api, 'unenroll', lambda *a: writes.append(a))
    monkeypatch.setattr(api, 'cancel_music_room', lambda *a: writes.append(a))
    listing = call('events_get_university_events', {'date_from': '2099-01-01', 'query': 'Workshop'})
    assert listing['total'] == 1
    details = listing['events'][0]
    assert details['title'] == 'Workshop' and details['location'] == 'Room 108'
    assert details['description'] == 'Build things' and '2 enrolled of 20 places' in details['enrollment']
    assert call('events_enroll_in_event', {'event_id': event_id, 'leave': True}, **AUTH)['enrolled'] is False
    assert call('account_cancel_booking', {'service': 'music_room', 'booking_id': '42'}, **AUTH)['done'] is True
    assert writes == [(AUTH['token'], event_id), (AUTH['token'], 42)]
