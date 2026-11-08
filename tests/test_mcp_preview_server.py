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
def test_missing_title_preview_returns_safe_validation_result(verified, monkeypatch, caplog, remote):
    reads, writes = [], []
    monkeypatch.setattr(api, 'bookable_rooms', lambda *a: reads.append(a) or [])
    monkeypatch.setattr(api, 'can_book_room', lambda *a: reads.append(a) or (True, None))
    monkeypatch.setattr(api, 'book_room', lambda *a, **kw: writes.append((a, kw)))
    arguments = {'room_id': 'private-input-value', 'day': '2099-01-01',
                 'time_from': '10:30', 'time_to': '11:30'}

    async def run():
        async with connection(remote) as client:
            result = await client.call_tool('preview_tool', {
                'name': 'rooms_book_room', 'arguments': arguments}, raise_on_error=False)
            assert not result.is_error
            assert set(result.data) == {'error', 'code'}
            assert result.data['code'] == 'invalid_arguments'
            assert 'title' in result.data['error']
            assert 'private-input-value' not in str(result)
            for interface in ['rooms_book_room', 'call_tool']:
                payload = arguments if interface == 'rooms_book_room' else {
                    'name': 'rooms_book_room', 'arguments': arguments}
                assert (await client.call_tool(interface, payload, raise_on_error=False)).is_error
    asyncio.run(run())
    assert not reads and not writes
    assert 'private-input-value' not in caplog.text


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
@pytest.mark.parametrize('arguments', [{'training_id': 7}, {}])
def test_preview_authentication_precedes_read_lookups(verified, monkeypatch, remote, token, sport_token, arguments):
    monkeypatch.setattr(sport, 'training', lambda *a: pytest.fail('Unauthenticated preview read'))
    async def run():
        async with connection(remote, token, sport_token) as client:
            result = await client.call_tool('preview_tool', {
                'name': 'sport_sport_checkin', 'arguments': arguments}, raise_on_error=False)
            assert result.is_error
            assert 'sign' in str(result.content)
    asyncio.run(run())


@pytest.mark.parametrize('remote', [False, True])
def test_invalid_preview_and_nested_controls_never_read(verified, monkeypatch, remote):
    monkeypatch.setattr(api, 'bookable_rooms', lambda *a: pytest.fail('Invalid preview read'))
    monkeypatch.setattr(sport, 'training', lambda *a: pytest.fail('Invalid preview read'))
    room = {'room_id': 'r', 'day': '2099-01-01', 'time_from': '10:30', 'time_to': '11:30', 'title': 'Study'}
    invalid_arguments = [
        {'name': 'rooms_book_room', 'arguments': {**room, 'time_from': '10:30:59+05:00'}},
        {'name': 'rooms_book_room', 'arguments': {**room, 'room_id': '../escape'}},
        {'name': 'rooms_book_room', 'arguments': {**room, 'day': '2000-01-01'}},
        {'name': 'sport_sport_checkin', 'arguments': {'training_id': 7, 'cancel': 0}},
    ]
    malformed = [
        {'name': 'sport_sport_checkin', 'arguments': {'training_id': 7}, 'language': 'xx'},
        {'name': 'sport_sport_checkin', 'arguments': {'training_id': 7}, 'uid': 'other'},
        {'name': 'sport_sport_checkin', 'arguments': False},
        {'name': 'sport_sport_checkin'},
        {'name': 'maps_scenes_scenes', 'arguments': {}},
    ]
    malformed += [{'name': name, 'arguments': {}} for name in ['unknown', 'call_tool', 'preview_tool', 'search_tools', 'service_status']]
    async def run():
        async with connection(remote) as client:
            for arguments in invalid_arguments:
                result = await client.call_tool('preview_tool', arguments, raise_on_error=False)
                assert not result.is_error and result.data['code'] == 'invalid_arguments'
            for arguments in malformed:
                assert (await client.call_tool('preview_tool', arguments, raise_on_error=False)).is_error
            for name in ['preview_tool', 'call_tool', 'search_tools', 'service_status']:
                assert (await client.call_tool('call_tool', {'name': name, 'arguments': {}}, raise_on_error=False)).is_error
    asyncio.run(run())


@pytest.mark.parametrize('remote', [False, True])
@pytest.mark.parametrize('failure', [httpx.ReadTimeout, ValueError, mcp_domain.InvalidArguments])
def test_preview_callback_or_transport_failure_is_safe(verified, monkeypatch, caplog, remote, failure):
    def fail(*args):
        raise failure('private credential ih sport upstream diagnostic')
    if failure is httpx.ReadTimeout:
        monkeypatch.setattr(sport, 'training', fail)
    else:
        monkeypatch.setattr(mcp_domain.definitions()['sport_sport_checkin'].fn, '_preview', fail)
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


@pytest.mark.parametrize('remote', [False, True])
def test_preview_validation_preserves_raw_types_and_hides_private_inputs(verified, monkeypatch, caplog, remote):
    reads, writes = [], []
    monkeypatch.setattr(api, 'bookable_rooms', lambda *a: reads.append(a) or [])
    monkeypatch.setattr(api, 'can_book_room', lambda *a: reads.append(a) or (True, None))
    monkeypatch.setattr(api, 'book_room', lambda *a: writes.append(a))
    monkeypatch.setattr(sport, 'training', lambda *a: reads.append(a) or {})
    monkeypatch.setattr(sport, 'check_in', lambda *a: writes.append(a))
    room = {'room_id': 'r', 'day': '2099-01-01', 'time_from': '10:30',
            'time_to': '11:30', 'title': 'private-input-secret'}
    cases = [('rooms_book_room', {**room, 'time_from': value}) for value in [
        '10:30:59+05:00', '10:30:59', '10:30+05:00', '10:30:00.123456',
        '10:30:00', '10:30:00.000000', '10:30Z', 0, False,
    ]]
    cases += [('sport_sport_checkin', {'training_id': value}) for value in [False, True, '7', 0]]
    cases += [('sport_sport_checkin', {'training_id': 7, 'cancel': value})
              for value in [0, 1, 'false', 'true', None]]
    cases += [
        ('rooms_book_room', {**room, 'private-extra-key': 'private-extra-value'}),
        ('rooms_book_room', {**room, 'time_to': '10:00'}),
        ('rooms_book_room', {**room, 'room_id': '../private-path-secret'}),
    ]

    async def run():
        async with connection(remote) as client:
            for name, arguments in cases:
                result = await client.call_tool('preview_tool', {
                    'name': name, 'arguments': arguments}, raise_on_error=False)
                assert not result.is_error and result.data['code'] == 'invalid_arguments'
                assert set(result.data) == {'error', 'code'}
                assert 'private-' not in str(result)
                assert 'input_value' not in str(result) and 'ctx' not in str(result)
                if arguments.get('time_to') == '10:00':
                    assert 'time_to must be after time_from' in result.data['error']
                assert not reads and not writes
    asyncio.run(run())
    assert 'private-' not in caplog.text


@pytest.mark.parametrize('remote', [False, True])
def test_valid_room_preview_keeps_id_when_name_lookup_is_unavailable(verified, monkeypatch, remote):
    reads, writes = [], []
    def unavailable(*args):
        reads.append(args)
        raise api.ServiceError(503, 'private-upstream-diagnostic')
    monkeypatch.setattr(api, 'bookable_rooms', unavailable)
    monkeypatch.setattr(api, 'book_room', lambda *a: writes.append(a))
    arguments = {'room_id': 'room-id', 'day': '2099-01-01', 'time_from': '10:30',
                 'time_to': '11:30', 'title': 'Study'}

    async def run():
        async with connection(remote) as client:
            result = await client.call_tool('preview_tool', {
                'name': 'rooms_book_room', 'arguments': arguments}, raise_on_error=False)
            assert not result.is_error
            assert set(result.data) == {'name', 'arguments', 'description'}
            assert result.data['arguments'] == arguments
            assert 'room-id' in result.data['description'] and 'Study' in result.data['description']
            assert 'private-upstream-diagnostic' not in str(result)
    asyncio.run(run())
    assert reads == [('ih',)] and not writes


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
