"""Exact read-only action details through direct and generic MCP protocols."""
import asyncio

import httpx
import pytest
from fastmcp import Client

from catix.innohassle import client as api, mcp_server, sport


@pytest.fixture
def identity(monkeypatch):
    monkeypatch.setattr(mcp_server.token_verifier, 'claims',
                        lambda token: {'uid': 'owner'} if token == 'synthetic-ih' else None)


def invoke(name, arguments, *, token: str | None = 'synthetic-ih', sport_token: str | None = 'synthetic-sport'):
    async def run():
        root = await mcp_server.build_server()
        with mcp_server.credentials(token, sport_token=sport_token):
            async with Client(root) as client:
                results = []
                for generic in (False, True):
                    result = await client.call_tool(
                        'call_tool' if generic else name,
                        {'name': name, 'arguments': arguments} if generic else arguments,
                        raise_on_error=False,
                    )
                    results.append(result)
                return results
    return asyncio.run(run())


def training(**changes):
    return {'id': 7, 'sport_name': 'Swimming', 'start': '2099-01-01T20:30:00Z',
            'end': '2099-01-01T22:00:00Z', 'is_all_day': False,
            'training_location': {'name': 'Pool'}, 'participant_emails': ['secret@example.test'],
            **changes}


def test_training_exact_read_preserves_cross_day_interval(identity, monkeypatch):
    calls = []
    monkeypatch.setattr(sport, 'training', lambda *args: calls.append(args) or training())
    for result in invoke('sport_get_training', {'training_id': 7}):
        assert not result.is_error, result
        assert result.data == {'training': {
            'training_id': 7, 'name': 'Swimming', 'date': '2099-01-01 Thu',
            'time': '23:30-01:00', 'place': 'Pool', 'timezone': 'Europe/Moscow',
            'starts_at': '2099-01-01T23:30:00+03:00', 'ends_at': '2099-01-02T01:00:00+03:00',
        }}
    assert calls == [('synthetic-sport', 7)] * 2


def test_training_all_day_is_explicit(identity, monkeypatch):
    monkeypatch.setattr(sport, 'training', lambda *args: training(is_all_day=True))
    for result in invoke('sport_get_training', {'training_id': 7}):
        assert not result.is_error
        assert result.data['training']['all_day'] is True
        assert 'time' not in result.data['training']


@pytest.mark.parametrize('name,arguments', [
    ('sport_get_sport_trainings', {'date_from': '2099-01-01', 'date_to': '2099-01-02'}),
    ('sport_get_my_sport', {}),
])
def test_reused_training_all_day_description_preserves_date_range(identity, monkeypatch, name, arguments):
    from catix.agent.api_context import from_result

    monkeypatch.setattr(sport, 'me', lambda *args: {'user_id': 1, 'student_info': {'medical_group': 'main'}})
    monkeypatch.setattr(sport, 'hours', lambda *args: {})
    monkeypatch.setattr(sport, 'current_semester', lambda *args: {})
    monkeypatch.setattr(sport, 'my_trainings', lambda *args: [{
        'checked_in': True,
        'training': training(is_all_day=True, start='2099-01-01T00:00:00+03:00',
                             end='2099-01-03T00:00:00+03:00'),
    }])
    for result in invoke(name, arguments):
        assert not result.is_error, result
        description = from_result('sport_sport_checkin', {'training_id': 7}, name, result.data)
        assert description is not None
        assert '2099-01-01' in description and '2099-01-03' in description
        assert 'all day' in description
        item = result.data['checked_in' if name == 'sport_get_my_sport' else 'trainings'][0]
        assert item['all_day'] is True
        assert 'time' not in item


@pytest.mark.parametrize('changes', [
    {'id': 8}, {'id': '7'}, {'start': 'not-a-date'}, {'end': '2098-01-01T00:00:00Z'},
    {'sport_name': None}, {'sport_name': {'private': 'secret@example.test'}},
    {'is_all_day': 'true'}, {'training_location': {'name': ['secret@example.test']}},
])
def test_training_malformed_or_mismatched_result_is_safe(identity, monkeypatch, changes):
    monkeypatch.setattr(sport, 'training', lambda *args: training(**changes))
    for result in invoke('sport_get_training', {'training_id': 7}):
        assert result.is_error or 'error' in result.data
        assert 'training' not in (result.data or {})
        assert 'secret@example.test' not in str(result)


def event(**changes):
    return {'id': 'a' * 24, 'data': {
        'starts_at': '2099-01-01T20:30:00Z', 'duration_hours': 2,
        'locales': {'ru': {'name': 'Встреча'}, 'en': {'name': 'Meeting'}},
        'location': {'display_name': '301'}, 'participants': ['secret@example.test'],
        **changes,
    }}


def test_event_exact_read_is_fresh_anonymous_single_fetch(identity, monkeypatch):
    calls = []
    def send(request):
        calls.append(request)
        return httpx.Response(200, json=event(), request=request)
    monkeypatch.setattr(api, '_client', httpx.Client(base_url='https://api.test/', transport=httpx.MockTransport(send)))
    monkeypatch.setattr(api.cache, 'cached', lambda *a, **kw: pytest.fail('Exact event must bypass cache'))
    for result in invoke('events_get_event', {'event_id': 'a' * 24}):
        assert not result.is_error, result
        assert result.data == {'event': {
            'id': 'a' * 24, 'title': 'Meeting', 'names': {'en': 'Meeting', 'ru': 'Встреча'},
            'start': '2099-01-01 23:30 Thu', 'end': '2099-01-02 01:30 Fri',
            'starts_at': '2099-01-01T23:30:00+03:00', 'ends_at': '2099-01-02T01:30:00+03:00',
            'location': '301', 'page': 'https://innohassle.ru/events/p/' + 'a' * 24,
            'timezone': 'Europe/Moscow',
        }}
    assert len(calls) == 2
    assert all(r.method == 'GET' and r.url.path == '/events/v1/events/' + 'a' * 24 for r in calls)
    assert all('authorization' not in r.headers and 'x-sport-token' not in r.headers for r in calls)


@pytest.mark.parametrize('body', [None, {}, {**event(), 'id': 'b' * 24},
    event(starts_at='2099-01-01T20:30:00'), event(starts_at='not-a-date'),
    event(locales={}), event(locales={'en': {'name': '  '}}),
    event(duration_hours=-2), event(duration_hours=True),
    event(location={'display_name': {'email': 'secret@example.test'}}),
])
def test_event_malformed_or_mismatched_result_is_safe(identity, monkeypatch, body):
    monkeypatch.setattr(api, 'event', lambda *args, **kwargs: body)
    for result in invoke('events_get_event', {'event_id': 'a' * 24}, token=None, sport_token=None):
        assert result.is_error or 'error' in result.data
        assert 'event' not in (result.data or {})
        assert 'secret@example.test' not in str(result)


@pytest.mark.parametrize('event_id', ['../other', 'A' * 24, 'a' * 24 + '?x=1', 'a' * 24 + '\n'])
def test_backend_event_rejects_invalid_ids_before_io(monkeypatch, event_id):
    monkeypatch.setattr(api, '_get', lambda *a, **kw: pytest.fail('Invalid identifier reached cache/HTTP'))
    monkeypatch.setattr(api._client, 'get', lambda *a, **kw: pytest.fail('Invalid identifier reached HTTP'))
    for fresh in (False, True):
        with pytest.raises(ValueError):
            api.event(event_id, fresh=fresh)


def room(**changes):
    return {'outlook_booking_id': 'AA/B+Q==', 'related_to_me': True,
            'start': '2099-01-01T20:30:00Z', 'end': '2099-01-01T22:00:00Z',
            'room_id': '301', 'title': 'Project meeting',
            'participant_emails': ['secret@example.test'], **changes}


def test_room_exact_read_quotes_opaque_id_and_preserves_dates(identity, monkeypatch):
    calls = []
    def send(request):
        calls.append(request)
        return httpx.Response(200, json=room(), request=request)
    monkeypatch.setattr(api, '_client', httpx.Client(base_url='https://api.test/', transport=httpx.MockTransport(send)))
    for result in invoke('account_get_booking', {'service': 'room', 'booking_id': 'AA/B+Q=='}):
        assert not result.is_error, result
        assert result.data == {'booking': {
            'service': 'room', 'booking_id': 'AA/B+Q==', 'title': 'Project meeting',
            'date': '2099-01-01 Thu', 'time': '23:30-01:00', 'room': '301', 'place': '301',
            'starts_at': '2099-01-01T23:30:00+03:00', 'ends_at': '2099-01-02T01:00:00+03:00',
            'timezone': 'Europe/Moscow',
        }}
    assert len(calls) == 2
    assert all(r.method == 'GET' and r.url.raw_path == b'/room-booking/v0/bookings/AA%2FB%2BQ%3D%3D' for r in calls)
    assert all(r.headers['authorization'] == 'Bearer synthetic-ih' for r in calls)


def test_music_exact_read_searches_all_owned_bookings(identity, monkeypatch):
    calls = []
    rows = [{'id': i} for i in range(1, 61)] + [{
        'id': 987, 'time_start': '2099-01-01T23:30:00', 'time_end': '2099-01-02T01:00:00',
        'alias': 'private-alias', 'email': 'secret@example.test',
    }]
    monkeypatch.setattr(api, 'my_music_room_bookings', lambda token: calls.append(token) or rows)
    for result in invoke('account_get_booking', {'service': 'music_room', 'booking_id': '987'}):
        assert not result.is_error, result
        assert result.data == {'booking': {
            'service': 'music_room', 'booking_id': '987', 'title': 'Music room', 'place': 'Music room',
            'date': '2099-01-01 Thu', 'time': '23:30-01:00', 'timezone': 'Europe/Moscow',
            'starts_at': '2099-01-01T23:30:00+03:00', 'ends_at': '2099-01-02T01:00:00+03:00',
        }}
    assert calls == ['synthetic-ih'] * 2


@pytest.mark.parametrize('body', [None, {}, room(outlook_booking_id='someone-else'),
    room(related_to_me=False), room(related_to_me=None), room(related_to_me=1), room(related_to_me='true'),
    {k: v for k, v in room().items() if k != 'related_to_me'},
    room(end='2098-01-01T00:00:00Z'), room(title=None), room(title={'private': 'secret@example.test'}),
    room(room_id=None), room(room_id={'email': 'secret@example.test'}),
])
def test_room_must_match_be_owned_and_have_safe_details(identity, monkeypatch, body):
    monkeypatch.setattr(api, 'room_booking', lambda *args: body)
    for result in invoke('account_get_booking', {'service': 'room', 'booking_id': 'AA/B+Q=='}):
        assert result.is_error or 'error' in result.data
        assert 'booking' not in (result.data or {})
        assert 'secret@example.test' not in str(result)


@pytest.mark.parametrize('booking_id,rows', [
    ('007', [{'id': 7, 'time_start': '2099-01-01T10:00:00', 'time_end': '2099-01-01T11:00:00'}]),
    ('7', []), ('7', None), ('7', [{'id': 7}]),
    ('7', [{'id': 7, 'time_start': '2099-01-01T11:00:00', 'time_end': '2099-01-01T10:00:00'}]),
    ('7', [{'id': 7, 'time_start': '2099-01-01T10:00:00', 'time_end': '2099-01-01T11:00:00'}] * 2),
    ('True', [{'id': True, 'time_start': '2099-01-01T10:00:00', 'time_end': '2099-01-01T11:00:00'}]),
])
def test_music_absent_malformed_or_ambiguous_booking_is_safe(identity, monkeypatch, booking_id, rows):
    monkeypatch.setattr(api, 'my_music_room_bookings', lambda *args: rows)
    for result in invoke('account_get_booking', {'service': 'music_room', 'booking_id': booking_id}):
        assert result.is_error or 'error' in result.data
        assert 'booking' not in (result.data or {})


@pytest.mark.parametrize('name,arguments', [
    ('sport_get_training', {'training_id': value}) for value in (0, -1, True, '7', 1.5)
] + [
    ('events_get_event', {'event_id': value}) for value in ('A' * 24, 'a' * 23, 'a' * 24 + '\n', '../x', 7)
] + [
    ('account_get_booking', {'service': service, 'booking_id': value})
    for service in ('room', 'music_room')
    for value in ('', '..', '../x', 'x?y=1', '%252F', 'x\\y', 'x\n', 7)
] + [('account_get_booking', {'service': 'other', 'booking_id': '7'})])
def test_invalid_detail_ids_never_reach_upstream(identity, monkeypatch, name, arguments):
    def forbidden(*args, **kwargs):
        pytest.fail('Invalid input reached upstream')
    monkeypatch.setattr(sport, 'training', forbidden)
    monkeypatch.setattr(api, 'event', forbidden)
    monkeypatch.setattr(api, 'room_booking', forbidden)
    monkeypatch.setattr(api, 'my_music_room_bookings', forbidden)
    for result in invoke(name, arguments):
        assert result.is_error


@pytest.fixture
def signed_identity(monkeypatch):
    from datetime import datetime, timedelta, timezone
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(mcp_server.token_verifier._keys, 'get_signing_keys', lambda: [key.public_key()])
    return jwt.encode({'uid': 'synthetic-owner', 'exp': datetime.now(timezone.utc) + timedelta(hours=1)},
                      key, algorithm='RS256')


@pytest.mark.parametrize('name,arguments', [
    ('sport_get_training', {'training_id': 7}),
    ('account_get_booking', {'service': 'room', 'booking_id': 'AA/B+Q=='}),
    ('account_get_booking', {'service': 'music_room', 'booking_id': '7'}),
])
def test_signed_identity_valid_controls_and_auth_denials(signed_identity, monkeypatch, name, arguments):
    calls = []
    monkeypatch.setattr(sport, 'training', lambda *a: calls.append(a) or training())
    monkeypatch.setattr(api, 'room_booking', lambda *a: calls.append(a) or room())
    monkeypatch.setattr(api, 'my_music_room_bookings', lambda *a: calls.append(a) or [{
        'id': 7, 'time_start': '2099-01-01T10:00:00', 'time_end': '2099-01-01T11:00:00'}])
    for result in invoke(name, arguments, token=signed_identity):
        assert not result.is_error
    assert len(calls) == 2
    calls.clear()
    for token in (None, 'forged.invalid.signature'):
        for result in invoke(name, arguments, token=token):
            assert result.is_error
    if name == 'sport_get_training':
        for result in invoke(name, arguments, token=signed_identity, sport_token=None):
            assert result.is_error
    assert not calls


@pytest.mark.parametrize('name,arguments,target', [
    ('sport_get_training', {'training_id': 7}, 'training'),
    ('events_get_event', {'event_id': 'a' * 24}, 'event'),
    ('account_get_booking', {'service': 'room', 'booking_id': 'AA/B+Q=='}, 'room_booking'),
    ('account_get_booking', {'service': 'music_room', 'booking_id': '7'}, 'my_music_room_bookings'),
])
@pytest.mark.parametrize('status', [403, 404, 500])
def test_detail_upstream_errors_never_expose_diagnostics(identity, monkeypatch, name, arguments, target, status):
    def refused(*args, **kwargs):
        raise api.ServiceError(status, 'secret@example.test private-alias synthetic-sport')
    monkeypatch.setattr(sport if target == 'training' else api, target, refused)
    for result in invoke(name, arguments):
        assert result.is_error or 'error' in result.data
        assert 'secret@example.test' not in str(result)
        assert 'private-alias' not in str(result)


@pytest.mark.parametrize('name,field', [('sport_get_training', 'training_id'),
                                       ('events_get_event', 'event_id'),
                                       ('account_get_booking', 'booking_id')])
def test_detail_discovery_is_anonymous_read_only_with_flat_schema(name, field):
    async def run():
        root = await mcp_server.build_server()
        declared = await root.get_tool(name)
        assert declared is not None and declared.annotations is not None
        assert declared.annotations.read_only_hint is True
        assert declared.annotations.destructive_hint is False
        async with Client(root) as client:
            found = (await client.call_tool('search_tools', {'query': name})).data
            schema = next(item['inputSchema'] for item in found if item['name'] == name)
            assert field in schema['required']
            assert not {'token', 'uid', 'sport_token'} & schema['properties'].keys()
            assert schema['additionalProperties'] is False
    asyncio.run(run())


@pytest.mark.parametrize('identifier', ['', '..', '../42', '%252e%252e%252f42', 'x?other', 'x#other', 'x\\y'])
def test_backend_room_detail_rejects_path_syntax(monkeypatch, identifier):
    monkeypatch.setattr(api, '_as_user', lambda *a, **kw: pytest.fail('Invalid identifier reached HTTP'))
    with pytest.raises(ValueError):
        api.room_booking('synthetic-ih', identifier)


@pytest.mark.parametrize('locales,title', [
    ({'ru': {'name': 'Встреча'}}, 'Встреча'),
    ({'zz': {'name': 'Last'}, 'aa': {'name': 'First'}}, 'First'),
])
def test_public_event_title_fallback_and_unknown_end(monkeypatch, locales, title):
    monkeypatch.setattr(api, 'event', lambda *a, **kw: event(locales=locales, duration_hours=None))
    for result in invoke('events_get_event', {'event_id': 'a' * 24}, token=None, sport_token=None):
        assert not result.is_error
        assert result.data['event']['title'] == title
        assert 'end' not in result.data['event'] and 'ends_at' not in result.data['event']
