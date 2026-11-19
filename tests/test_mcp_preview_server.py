"""Preview RPC is retired; execution keeps validation and authentication."""
import asyncio
from contextlib import asynccontextmanager

import pytest

from catix.innohassle import client as api, sport, mcp_server

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
@pytest.mark.parametrize('interface', ['list_tools', 'preview_tool', 'call_tool'])
def test_preview_rpc_is_absent_and_unavailable(verified, monkeypatch, remote, interface):
    reads, writes = [], []
    monkeypatch.setattr(sport, 'training', lambda *a: reads.append(a) or {})
    monkeypatch.setattr(sport, 'check_in', lambda *a: writes.append(a))

    async def run():
        async with connection(remote) as client:
            payload = {'name': 'sport_sport_checkin', 'arguments': {'training_id': 7}}
            if interface == 'list_tools':
                assert 'preview_tool' not in {tool.name for tool in await client.list_tools()}
            else:
                if interface == 'call_tool':
                    payload = {'name': 'preview_tool', 'arguments': payload}
                result = await client.call_tool(interface, payload, raise_on_error=False)
                assert result.is_error
            assert not reads and not writes
            # A standalone authenticated mutation remains available without a preview.
            assert (await client.call_tool('sport_sport_checkin', {'training_id': 7})).data['done'] is True
    asyncio.run(run())
    assert not reads and writes == [('sport', 7, True)]


@pytest.mark.parametrize('remote', [False, True])
def test_missing_title_mutation_returns_safe_validation_error(verified, monkeypatch, caplog, remote):
    reads, writes = [], []
    monkeypatch.setattr(api, 'bookable_rooms', lambda *a: reads.append(a) or [])
    monkeypatch.setattr(api, 'can_book_room', lambda *a: reads.append(a) or (True, None))
    monkeypatch.setattr(api, 'book_room', lambda *a, **kw: writes.append((a, kw)))
    monkeypatch.setattr(api, 'room_bookings', lambda *a, **kw: reads.append((a, kw)) or [])
    arguments = {'room_id': 'private-input-value', 'day': '2099-01-01',
                 'time_from': '10:30', 'time_to': '11:30'}

    async def run():
        async with connection(remote) as client:
            for interface in ['rooms_book_room', 'call_tool']:
                payload = arguments if interface == 'rooms_book_room' else {
                    'name': 'rooms_book_room', 'arguments': arguments}
                result = await client.call_tool(interface, payload, raise_on_error=False)
                assert not result.is_error and result.data['done'] is False
                assert result.data['code'] == 'invalid_arguments'
                assert 'title' in str(result.content)
                assert 'private-input-value' not in str(result)
    asyncio.run(run())
    assert not reads and not writes
    assert 'private-input-value' not in caplog.text


@pytest.mark.parametrize('remote', [False, True])
@pytest.mark.parametrize('token,sport_token', [(None, None), (None, 'sport'), ('invalid', 'sport'), ('ih', None)])
@pytest.mark.parametrize('generic', [False, True])
@pytest.mark.parametrize('invalid', [False, True])
def test_mutation_authentication_precedes_upstream_writes(verified, monkeypatch, remote, token, sport_token, generic, invalid):
    writes = []
    monkeypatch.setattr(sport, 'training', lambda *a: pytest.fail('Unexpected display lookup'))
    monkeypatch.setattr(sport, 'check_in', lambda *a: writes.append(a))
    name, arguments = 'sport_sport_checkin', {'training_id': 7}
    interface = 'call_tool' if generic else name
    payload = {'name': name, 'arguments': arguments} if generic else arguments

    async def run():
        async with connection(remote, token, sport_token) as client:
            invalid_payload = {'name': name, 'arguments': {}} if generic else {}
            result = await client.call_tool(interface, invalid_payload if invalid else payload, raise_on_error=False)
            assert result.is_error
            assert 'sign' in str(result.content)
        assert not writes
        async with connection(remote) as client:
            assert (await client.call_tool(interface, payload)).data['done'] is True
    asyncio.run(run())
    assert writes == [('sport', 7, True)]


@pytest.mark.parametrize('remote', [False, True])
def test_invalid_mutations_and_nested_controls_never_execute(verified, monkeypatch, remote):
    monkeypatch.setattr(api, 'can_book_room', lambda *a: pytest.fail('Invalid mutation read'))
    monkeypatch.setattr(api, 'room_bookings', lambda *a, **kw: pytest.fail('Invalid mutation occupancy read'))
    monkeypatch.setattr(api, 'book_room', lambda *a: pytest.fail('Invalid mutation write'))
    monkeypatch.setattr(sport, 'check_in', lambda *a: pytest.fail('Invalid mutation write'))
    room = {'room_id': 'r', 'day': '2099-01-01', 'time_from': '10:30', 'time_to': '11:30', 'title': 'Study'}
    invalid_arguments = [
        {'name': 'rooms_book_room', 'arguments': {**room, 'time_from': '10:30:59+05:00'}},
        {'name': 'rooms_book_room', 'arguments': {**room, 'room_id': '../escape'}},
        {'name': 'rooms_book_room', 'arguments': {**room, 'day': '2000-01-01'}},
        {'name': 'sport_sport_checkin', 'arguments': {'training_id': 7, 'cancel': 0}},
        {'name': 'sport_sport_checkin', 'arguments': False},
        {'name': 'sport_sport_checkin', 'arguments': {}},
    ]
    malformed = [
        {'name': 'sport_sport_checkin', 'arguments': {'training_id': 7}, 'language': 'en'},
        {'name': 'sport_sport_checkin', 'arguments': {'training_id': 7}, 'uid': 'other'},
    ]
    malformed += [{'name': name, 'arguments': {}} for name in ['unknown', 'call_tool', 'preview_tool', 'search_tools', 'service_status']]
    async def run():
        async with connection(remote) as client:
            for arguments in invalid_arguments:
                for generic in [False, True]:
                    result = await client.call_tool('call_tool' if generic else arguments['name'],
                        arguments if generic else arguments['arguments'], raise_on_error=False)
                    assert not result.is_error and result.data['done'] is False
                    assert result.data['code'] == 'invalid_arguments'
            for arguments in malformed:
                assert (await client.call_tool('call_tool', arguments, raise_on_error=False)).is_error
            for name in ['preview_tool', 'call_tool', 'search_tools', 'service_status']:
                assert (await client.call_tool('call_tool', {'name': name, 'arguments': {}}, raise_on_error=False)).is_error
    asyncio.run(run())


@pytest.mark.parametrize('remote', [False, True])
@pytest.mark.parametrize('generic', [False, True])
def test_mutation_validation_preserves_raw_types_and_hides_private_inputs(verified, monkeypatch, caplog, remote, generic):
    reads, writes = [], []
    monkeypatch.setattr(api, 'bookable_rooms', lambda *a: reads.append(a) or [])
    monkeypatch.setattr(api, 'can_book_room', lambda *a: reads.append(a) or (True, None))
    monkeypatch.setattr(api, 'book_room', lambda *a: writes.append(a) or {'outlook_booking_id': 'booking'})
    monkeypatch.setattr(api, 'room_bookings', lambda *a, **kw: reads.append((a, kw)) or [])
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
                payload = {'name': name, 'arguments': arguments} if generic else arguments
                result = await client.call_tool('call_tool' if generic else name, payload, raise_on_error=False)
                assert not result.is_error and result.data['done'] is False
                assert result.data['code'] == 'invalid_arguments'
                assert 'private-' not in str(result)
                assert 'input_value' not in str(result) and 'ctx' not in str(result)
                if arguments.get('time_to') == '10:00':
                    assert 'time_to must be after time_from' in str(result.content)
                assert not reads and not writes
            for name, arguments in [('rooms_book_room', {**room, 'title': 'Study'}),
                                    ('sport_sport_checkin', {'training_id': 7})]:
                payload = {'name': name, 'arguments': arguments} if generic else arguments
                assert (await client.call_tool('call_tool' if generic else name, payload)).data['done'] is True
    asyncio.run(run())
    assert len(reads) == 2 and len(writes) == 2
    assert reads == [('ih', 'r', *writes[0][3:]), (('ih', *writes[0][3:]), {'room_id': 'r'})]
    assert writes[-1] == ('sport', 7, True)
    assert 'private-' not in caplog.text


@pytest.mark.parametrize('name', ['calendar_get_my_ai_calendar', 'calendar_add_to_ai_calendar',
                                 'calendar_update_ai_calendar', 'calendar_remove_from_ai_calendar'])
def test_calendar_rpc_names_are_absent_and_refused_on_every_path(verified, monkeypatch, name):
    async def run():
        async with connection(False) as client:
            assert (await client.call_tool(name, {}, raise_on_error=False)).is_error
            assert (await client.call_tool('call_tool', {'name': name, 'arguments': {}}, raise_on_error=False)).is_error
    asyncio.run(run())


@pytest.mark.parametrize('remote', [False, True])
@pytest.mark.parametrize('generic', [False, True])
@pytest.mark.parametrize('failure_kind', ['value', 'pydantic', 'sdk'])
def test_validation_exception_during_execution_is_not_a_definite_refusal(verified, monkeypatch, caplog, remote, generic, failure_kind):
    writes = []

    def uncertain(*args):
        from fastmcp.exceptions import ValidationError as SDKValidationError
        from pydantic import ValidationError

        writes.append(args)
        if failure_kind == 'value':
            raise ValueError('private-upstream-diagnostic')
        error = ValidationError.from_exception_data('Upstream', [
            {'type': 'int_parsing', 'loc': ('value',), 'input': 'private-upstream-diagnostic'},
        ])
        if failure_kind == 'pydantic':
            raise error
        raise SDKValidationError('private-upstream-diagnostic') from error

    monkeypatch.setattr(sport, 'check_in', uncertain)

    async def run():
        async with connection(remote) as client:
            name, arguments = 'sport_sport_checkin', {'training_id': 7}
            result = await client.call_tool('call_tool' if generic else name,
                {'name': name, 'arguments': arguments} if generic else arguments)
            assert result.data['done'] is None and result.data['outcome'] == 'unknown'
            assert 'invalid_arguments' not in str(result.data)
            assert 'private-upstream-diagnostic' not in str(result)
    asyncio.run(run())
    assert writes == [('sport', 7, True)]
    assert 'private-upstream-diagnostic' not in caplog.text
