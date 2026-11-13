"""Native tools through standalone MCP clients; no cAtIx host or live writes."""

import asyncio

import pytest
from fastmcp import Client

from catix.innohassle import mcp_server
from tests.mcp_native_helpers import registered_tools
from tests.mcp_native_helpers import connection


def test_clock_time_rejects_non_hhmm_native_values():
    from datetime import time
    from pydantic import TypeAdapter, ValidationError
    from catix.common.dates import ClockTime

    assert TypeAdapter(ClockTime).validate_python("10:30") == time(10, 30)
    for invalid in ("10:30:00", "10:30:00.000", "10:30+03:00", 1030, True):
        with pytest.raises(ValidationError):
            TypeAdapter(ClockTime).validate_python(invalid)


@pytest.fixture
def native(monkeypatch):
    from catix.innohassle import sport as sport_api
    monkeypatch.setattr(mcp_server.token_verifier, 'claims', lambda token: {'uid': 'owner-' + token} if token in {'alice', 'bob'} else None)
    calls = []
    monkeypatch.setattr(sport_api, 'check_in', lambda *args: calls.append(args))
    monkeypatch.setattr(sport_api, 'sports', lambda token: [{'name': {'sport-alice': 'Volleyball', 'sport-bob': 'Basketball'}[token]}])
    return calls


def test_native_search_schema_and_direct_read_with_separate_credentials(native):
    async def run():
        async with connection(token='alice', sport_token='sport-alice') as client:
            result = (await client.call_tool('search_tools', {'query': 'sport checkin training'})).data
            sport = next(item for item in result if item['name'] == 'sport_sport_checkin')
            assert set(sport) == {'name', 'description', 'inputSchema'}
            assert 'runtime' not in sport['inputSchema']['properties']
            assert sport['inputSchema']['additionalProperties'] is False
            annotations = registered_tools()['sport_sport_checkin'].annotations
            assert annotations.read_only_hint is False
            assert annotations.destructive_hint is True
            assert (await client.call_tool('sport_get_sports', {})).data['sports'] == ['Volleyball']
            assert (await client.call_tool('call_tool', {'name': 'sport_get_sports'})).data['sports'] == ['Volleyball']
        async with connection() as client:
            assert (await client.call_tool('sport_get_sports', {}, raise_on_error=False)).is_error
        assert native == []
    asyncio.run(run())


@pytest.mark.parametrize('remote', [False, True], ids=['inprocess', 'http'])
@pytest.mark.parametrize('generic', [False, True], ids=['direct', 'generic'])
def test_standalone_writes_require_credentials_not_host_consent(native, remote, generic):
    name, args = 'sport_sport_checkin', {'training_id': 7}
    async def run():
        for token, sport in [(None, None), (None, 'sport-alice'), ('invalid', 'sport-alice'), ('alice', None)]:
            async with connection(remote, token, sport) as client:
                result = await client.call_tool('call_tool' if generic else name,
                    {'name': name, 'arguments': args} if generic else args, raise_on_error=False)
                assert result.is_error
                assert not native
        async with connection(remote, 'alice', 'sport-alice') as client:
            for extra in [{'approved': True}, {'approval': 'arbitrary'}, {'runtime': {}}, {'uid': 'bob'}]:
                arguments = {**args, **extra}
                result = await client.call_tool('call_tool' if generic else name,
                    {'name': name, 'arguments': arguments} if generic else arguments, raise_on_error=False)
                assert not result.is_error and result.data['done'] is False
                assert result.data['code'] == 'invalid_arguments'
                assert not native
            # Repeated explicit requests reach business logic; no capability replay gate.
            for _ in range(2):
                result = await client.call_tool('call_tool' if generic else name,
                    {'name': name, 'arguments': args} if generic else args)
                assert result.data['done'] is True
    asyncio.run(run())
    assert native == [('sport-alice', 7, True)] * 2


@pytest.mark.parametrize('remote', [False, True], ids=['inprocess', 'http'])
@pytest.mark.parametrize('generic', [False, True], ids=['direct', 'generic'])
@pytest.mark.parametrize('name,args', [
    ('rooms_book_room', {'room_id': 'r', 'title': 'meeting', 'day': '2099-01-01', 'time_from': '10:00', 'time_to': '11:00'}),
    ('music_book_music_room', {'day': '2099-01-01', 'time_from': '10:00', 'time_to': '11:00'}),
    ('account_cancel_booking', {'service': 'room', 'booking_id': 'outlook-id'}),
    ('events_enroll_in_event', {'event_id': 'a' * 24}),
    ('sport_sport_checkin', {'training_id': 3}),
])
def test_every_native_write_authenticates_on_both_dispatch_paths(native, monkeypatch, name, args, remote, generic):
    writes = []
    from catix.innohassle import client as api, sport
    monkeypatch.setattr(api, 'can_book_room', lambda *a: (True, None))
    occupancy = []
    monkeypatch.setattr(api, 'room_bookings', lambda *a, **kw: occupancy.append((a, kw)) or [])
    monkeypatch.setattr(api, 'book_room', lambda *a: writes.append(a) or {'outlook_booking_id': 'new'})
    if name == 'music_book_music_room':
        from datetime import datetime
        from catix.innohassle import mcp_account
        from catix.settings import settings
        monkeypatch.setattr(mcp_account, '_now', lambda: datetime(2099, 1, 1, 8, tzinfo=settings.tz))
    monkeypatch.setattr(api, 'my_music_room_profile', lambda token: {'status': 'free'})
    monkeypatch.setattr(api, 'music_room_bookings', lambda *a, **kwargs: [])
    monkeypatch.setattr(api, 'music_room_hours_left', lambda *a: (2, 3))
    monkeypatch.setattr(api, 'book_music_room', lambda *a: writes.append(a) or {'id': 1})
    monkeypatch.setattr(api, 'cancel_room', lambda *a: writes.append(a))
    monkeypatch.setattr(api, 'my_event', lambda *a: {'id': 'a' * 24, 'enrolled': bool(writes), 'enrolled_count': 0,
                        'data': {'starts_at': '2099-01-01T10:00:00+03:00', 'duration_hours': 1.5,
                                 'locales': {'en': {'name': 'Meeting'}}, 'location': {'display_name': '301'},
                                 'enrollment': {'type': 'internal'}}})
    monkeypatch.setattr(api, 'enroll', lambda *a: writes.append(a))
    monkeypatch.setattr(sport, 'check_in', lambda *a: writes.append(a))
    async def run():
        for token in [None, 'invalid']:
            async with connection(remote, token, 'sport-alice') as client:
                denied = await client.call_tool('call_tool' if generic else name,
                    {'name': name, 'arguments': args} if generic else args, raise_on_error=False)
                assert denied.is_error
        assert not writes
        assert not occupancy
        async with connection(remote, 'alice', 'sport-alice') as client:
            result = await client.call_tool('call_tool' if generic else name,
                {'name': name, 'arguments': args} if generic else args)
            assert result.data['done'] is True
        assert len(writes) == 1
        assert writes[0][0] == ('sport-alice' if name.startswith('sport_') else 'alice')
        assert occupancy == ([(('alice', *writes[0][3:]), {'room_id': 'r'})]
                             if name == 'rooms_book_room' else [])
    asyncio.run(run())


def test_http_native_credentials_are_verified_per_request(native, caplog):
    import httpx2
    from fastmcp.client.transports import StreamableHttpTransport
    from fastmcp.utilities.asgi_transport import StreamingASGITransport, run_asgi_lifespan

    async def run():
        async with mcp_server.adapter() as root:
            app = root.http_app(stateless_http=True)
            async with run_asgi_lifespan(app):
                clients = []
                def factory(**kwargs):
                    http = httpx2.AsyncClient(transport=StreamingASGITransport(app), **kwargs)
                    clients.append(http)
                    return http
                transport = StreamableHttpTransport('http://testserver/mcp', headers={
                    'X-Innohassle-Token': 'alice', 'X-Sport-Token': 'sport-alice',
                    'X-Catix-Approval': 'obsolete-ignored-header',
                    'Authorization': 'Bearer ignored-secret', 'Cookie': 'session=ignored-secret',
                }, httpx_client_factory=factory)
                with mcp_server.credentials('process-secret', sport_token='process-sport-secret'):
                    async with Client(transport) as client:
                        await client.call_tool('sport_get_sports', {})
                        for http in clients:
                            http.headers.pop('x-innohassle-token', None)
                        denied = await client.call_tool('sport_sport_checkin', {'training_id': 7}, raise_on_error=False,
                            meta={'uid': 'alice', 'token': 'alice', 'sport_token': 'sport-alice', 'approved': True})
                        assert denied.is_error and not native
                        for http in clients:
                            http.headers['x-innohassle-token'] = 'invalid'
                        assert (await client.call_tool('sport_sport_checkin', {'training_id': 7}, raise_on_error=False)).is_error
                        assert not native
                        for http in clients:
                            http.headers['x-innohassle-token'] = 'bob'
                            http.headers['x-sport-token'] = 'sport-bob'
                        assert (await client.call_tool('sport_get_sports', {})).data['sports'] == ['Basketball']
                        assert (await client.call_tool('call_tool', {'name': 'sport_sport_checkin', 'arguments': {'training_id': 7}})).data['done'] is True
                        for http in clients:
                            http.headers.pop('x-sport-token', None)
                        assert (await client.call_tool('sport_get_sports', {}, raise_on_error=False)).is_error
        assert native == [('sport-bob', 7, True)]
    asyncio.run(run())
    assert all(secret not in caplog.text for secret in ['ignored-secret', 'process-secret', 'process-sport-secret', 'obsolete-ignored-header'])


@pytest.mark.parametrize('generic', [False, True], ids=['direct', 'generic'])
def test_http_writes_verify_real_jwt_without_host_or_redis(monkeypatch, generic):
    from datetime import datetime, timedelta, timezone
    import httpx
    import jwt
    import redis
    from cryptography.hazmat.primitives.asymmetric import rsa
    from catix.innohassle import client as backend, sport, token

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    forged_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(token._keys, 'get_signing_keys', lambda: [key.public_key()])
    monkeypatch.setattr(redis, 'from_url', lambda *a, **kw: pytest.fail('MCP writes require no Redis proof store'))
    now = datetime.now(timezone.utc)
    valid_claims = {'uid': 'synthetic-owner', 'exp': now + timedelta(hours=1)}
    valid = jwt.encode(valid_claims, key, algorithm='RS256')
    invalid = [
        None,
        jwt.encode(valid_claims, forged_key, algorithm='RS256'),
        jwt.encode({**valid_claims, 'exp': now - timedelta(hours=1)}, key, algorithm='RS256'),
        jwt.encode({**valid_claims, 'aud': 'sport'}, key, algorithm='RS256'),
        jwt.encode({**valid_claims, 'uid': ' '}, key, algorithm='RS256'),
        jwt.encode({**valid_claims, 'uid': 42}, key, algorithm='RS256'),
    ]
    requests = []
    def reply(request):
        requests.append(request)
        return httpx.Response(200, json={})
    name, args = 'sport_sport_checkin', {'training_id': 7}
    async def run():
        with backend._http_client('https://synthetic.test', transport=httpx.MockTransport(reply)) as http:
            monkeypatch.setattr(sport, '_client', http)
            for credential in invalid:
                async with connection(True, credential, 'separate-sport-token') as client:
                    result = await client.call_tool('call_tool' if generic else name,
                        {'name': name, 'arguments': args} if generic else args, raise_on_error=False)
                    assert result.is_error
                    assert not requests
            async with connection(True, valid, 'separate-sport-token') as client:
                result = await client.call_tool('call_tool' if generic else name,
                    {'name': name, 'arguments': args} if generic else args)
                assert result.data['done'] is True
    asyncio.run(run())
    assert len(requests) == 1
    assert requests[0].method == 'POST' and requests[0].url.path == '/trainings/7/checkin'
    assert dict(requests[0].url.params) == {'checkin': 'true'}
    assert requests[0].headers['authorization'] == 'Bearer separate-sport-token'


def test_native_public_aggregated_reads_remain_public_and_drop_credentials(native, monkeypatch):
    from catix.innohassle import client as api
    seen = []
    monkeypatch.setattr(api, 'music_room_bookings', lambda day, **kwargs: seen.append(day) or [])
    monkeypatch.setattr(api, 'events', lambda start, end: seen.append((start, end)) or [])
    async def run():
        for credential in (None, 'alice'):
            async with connection(token=credential, sport_token='sport-alice') as client:
                music = (await client.call_tool('music_get_music_room_schedule', {'date_from': '2099-01-01'})).data
                assert music['days'][0]['booked'] == 'nothing booked' and music['music_room']
                events = (await client.call_tool('events_get_university_events', {'date_from': '2099-01-01'})).data
                assert events['events'] == [] and events['total'] == 0 and 'published' in events['note']
    asyncio.run(run())
    assert len(seen) == 4


@pytest.mark.parametrize('remote', [False, True], ids=['inprocess', 'http'])
def test_native_unknown_http_write_outcome_does_not_retry(monkeypatch, caplog, remote):
    import httpx
    from catix.innohassle import client as backend, sport
    monkeypatch.setattr(mcp_server.token_verifier, 'claims', lambda token: {'uid': 'owner'})
    requests = []
    def response(request):
        requests.append(request)
        return httpx.Response(503, json={'detail': 'sensitive-upstream-body'})
    async def run():
        with backend._http_client('https://backend.test', transport=httpx.MockTransport(response)) as http:
            monkeypatch.setattr(sport, '_client', http)
            async with connection(remote, 'alice', 'sport-alice') as client:
                result = (await client.call_tool('sport_sport_checkin', {'training_id': 7})).data
                assert result['done'] is None and result['outcome'] == 'unknown'
                assert 'retry automatically' in result['error']
                assert 'sensitive-upstream-body' not in str(result)
    asyncio.run(run())
    assert len(requests) == 1
    assert requests[0].headers['authorization'] == 'Bearer sport-alice'
    assert 'sensitive-upstream-body' not in caplog.text
