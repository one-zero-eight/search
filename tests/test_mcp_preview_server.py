"""Mutation previews are authenticated reads, not an execution prerequisite."""
import asyncio
from contextlib import asynccontextmanager

import httpx
import pytest

from catix.innohassle import client as api, sport, mcp_domain, mcp_server
from tests.mcp_native_helpers import connection as native_connection


@asynccontextmanager
async def connection(remote, token='ih', sport_token='sport'):
    async with native_connection(remote, token, sport_token) as client:
        yield client


@pytest.fixture
def verified(monkeypatch):
    monkeypatch.setattr(mcp_server.token_verifier, 'claims',
                        lambda token: {'uid': 'owner'} if token == 'ih' else None)


@pytest.mark.parametrize('remote', [False, True])
def test_preview_is_readonly_and_keeps_sport_credentials(verified, monkeypatch, remote):
    reads, writes = [], []
    monkeypatch.setattr(sport, 'training', lambda *a: reads.append(a) or {
        'start': '2099-01-01T10:00:00+03:00', 'end': '2099-01-01T11:00:00+03:00',
        'sport_name': 'Volleyball', 'training_location': {'name': 'Court A'}})
    monkeypatch.setattr(sport, 'check_in', lambda *a: writes.append(a))
    name, args = 'sport_sport_checkin', {'training_id': 7}
    normalized = mcp_domain.validate(name, args)

    async def run():
        async with connection(remote) as client:
            for language in ['ru', 'en']:
                result = (await client.call_tool('preview_tool', {
                    'name': name, 'arguments': args, 'language': language})).data
                assert result['name'] == name and result['arguments'] == normalized
                assert 'Volleyball' in result['description'] and 'Court A' in result['description']
                assert ('Записать' if language == 'ru' else 'Check you in') in result['description']
                assert not writes
            assert (await client.call_tool(name, args)).data['done'] is True
    asyncio.run(run())
    assert reads == [('sport', 7), ('sport', 7)]
    assert writes == [('sport', 7, True)]


@pytest.mark.parametrize('remote', [False, True])
@pytest.mark.parametrize('token,sport_token', [(None, None), (None, 'sport'), ('invalid', 'sport'), ('ih', None)])
def test_preview_authentication_precedes_read_lookups(verified, monkeypatch, remote, token, sport_token):
    monkeypatch.setattr(sport, 'training', lambda *a: pytest.fail('Unauthenticated preview read'))
    async def run():
        async with connection(remote, token, sport_token) as client:
            result = await client.call_tool('preview_tool', {
                'name': 'sport_sport_checkin', 'arguments': {'training_id': 7}}, raise_on_error=False)
            assert result.is_error
    asyncio.run(run())


@pytest.mark.parametrize('remote', [False, True])
def test_invalid_preview_and_nested_controls_never_read(verified, monkeypatch, remote):
    monkeypatch.setattr(api, 'bookable_rooms', lambda *a: pytest.fail('Invalid preview read'))
    monkeypatch.setattr(sport, 'training', lambda *a: pytest.fail('Invalid preview read'))
    room = {'room_id': 'r', 'day': '2099-01-01', 'time_from': '10:30', 'time_to': '11:30', 'title': 'Study'}
    malformed = [
        {'name': 'rooms_book_room', 'arguments': {**room, 'time_from': '10:30:59+05:00'}},
        {'name': 'rooms_book_room', 'arguments': {**room, 'room_id': '../escape'}},
        {'name': 'rooms_book_room', 'arguments': {**room, 'day': '2000-01-01'}},
        {'name': 'sport_sport_checkin', 'arguments': {'training_id': 7, 'cancel': 0}},
        {'name': 'sport_sport_checkin', 'arguments': {'training_id': 7}, 'language': 'xx'},
        {'name': 'sport_sport_checkin', 'arguments': {'training_id': 7}, 'uid': 'other'},
        {'name': 'sport_sport_checkin', 'arguments': False},
        {'name': 'sport_sport_checkin'},
        {'name': 'maps_scenes_scenes', 'arguments': {}},
    ]
    malformed += [{'name': name, 'arguments': {}} for name in ['unknown', 'call_tool', 'preview_tool', 'search_tools', 'service_status']]
    async def run():
        async with connection(remote) as client:
            for arguments in malformed:
                assert (await client.call_tool('preview_tool', arguments, raise_on_error=False)).is_error
            for name in ['preview_tool', 'call_tool', 'search_tools', 'service_status']:
                assert (await client.call_tool('call_tool', {'name': name, 'arguments': {}}, raise_on_error=False)).is_error
    asyncio.run(run())


@pytest.mark.parametrize('remote', [False, True])
def test_preview_transport_failure_is_safe_and_does_not_mutate(verified, monkeypatch, caplog, remote):
    def fail(*args):
        raise httpx.ReadTimeout('private credential ih sport upstream diagnostic')
    monkeypatch.setattr(sport, 'training', fail)
    writes = []
    monkeypatch.setattr(sport, 'check_in', lambda *a: writes.append(a))
    async def run():
        async with connection(remote) as client:
            result = await client.call_tool('preview_tool', {
                'name': 'sport_sport_checkin', 'arguments': {'training_id': 7}}, raise_on_error=False)
            assert result.is_error
            assert 'unavailable' in str(result.content)
            assert 'upstream diagnostic' not in str(result)
    asyncio.run(run())
    assert not writes and 'upstream diagnostic' not in caplog.text


@pytest.mark.parametrize('language', ['ru', 'en'])
def test_account_preview_callbacks_keep_human_labels(verified, monkeypatch, language):
    for method in ['book_music_room', 'cancel_music_room', 'enroll', 'unenroll']:
        monkeypatch.setattr(api, method, lambda *a: pytest.fail('Approval preview mutated'))
    monkeypatch.setattr(api, 'my_music_room_bookings', lambda token: [
        {'id': 42, 'time_start': '2099-01-01T10:00:00+03:00', 'time_end': '2099-01-01T11:00:00+03:00'}])
    monkeypatch.setattr(api, 'event', lambda event_id: {'data': {
        'locales': {'ru': {'name': 'Мастерская'}, 'en': {'name': 'Workshop'}},
        'starts_at': '2099-01-01T10:00:00+03:00', 'location': {'display_name': 'Room 108'}}})
    cases = [
        ('music_book_music_room', {'day': '2099-01-01', 'time_from': '10:00', 'time_to': '11:00'}, '10:00–11:00'),
        ('account_cancel_booking', {'service': 'music_room', 'booking_id': '42'}, '10:00–11:00'),
        ('events_enroll_in_event', {'event_id': 'a' * 24}, 'Мастерская' if language == 'ru' else 'Workshop'),
        ('events_enroll_in_event', {'event_id': 'a' * 24, 'leave': True}, 'Отменить' if language == 'ru' else 'Cancel'),
    ]
    async def run():
        async with connection(False) as client:
            for name, arguments, label in cases:
                result = (await client.call_tool('preview_tool', {
                    'name': name, 'arguments': arguments, 'language': language})).data
                assert result['name'] == name and result['arguments'] == mcp_domain.validate(name, arguments)
                assert label in result['description']
    asyncio.run(run())


@pytest.mark.parametrize('language', [[], {}, None, 0])
def test_preview_rejects_nonstring_language_without_internal_error(verified, language):
    async def run():
        async with connection(False) as client:
            result = await client.call_tool('preview_tool', {
                'name': 'sport_sport_checkin', 'arguments': {'training_id': 7}, 'language': language}, raise_on_error=False)
            assert result.is_error and 'Invalid account operation arguments' in str(result.content)
    asyncio.run(run())


@pytest.mark.parametrize('name', ['calendar_get_my_ai_calendar', 'calendar_add_to_ai_calendar',
                                 'calendar_update_ai_calendar', 'calendar_remove_from_ai_calendar'])
def test_calendar_rpc_names_are_absent_and_refused_on_every_path(verified, monkeypatch, name):
    for lookup in [mcp_domain.policy, mcp_domain.schema]:
        with pytest.raises(ValueError):
            lookup(name)
    async def run():
        async with connection(False) as client:
            assert (await client.call_tool(name, {}, raise_on_error=False)).is_error
            for interface in ['call_tool', 'preview_tool']:
                assert (await client.call_tool(interface, {'name': name, 'arguments': {}}, raise_on_error=False)).is_error
    asyncio.run(run())
