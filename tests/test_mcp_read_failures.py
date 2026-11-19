"""Upstream read diagnostics survive the native MCP wire without private data."""

import asyncio
import logging

import httpx
import pytest
from fastmcp.utilities.asgi_transport import StreamingASGITransport, run_asgi_lifespan

from catix.innohassle import actions, mcp_client, mcp_declarations, mcp_server, sport
from catix.settings import settings
from tests.mcp_native_helpers import connection


def test_sport_timeout_keeps_safe_code_across_http_mcp(monkeypatch, caplog):
    requests = []

    def respond(request):
        requests.append(request.url.path)
        raise httpx.ReadTimeout('private-body synthetic-ih synthetic-sport', request=request)

    monkeypatch.setattr(sport, '_client', httpx.Client(
        base_url='https://sport.test/api/v3/', transport=httpx.MockTransport(respond)))
    monkeypatch.setattr(mcp_server.token_verifier, 'claims', lambda token: {'uid': 'synthetic-owner'})
    monkeypatch.setattr(settings, 'innohassle_mcp_url', 'http://127.0.0.1/mcp')
    ticks = iter((10.0, 10.125))
    monkeypatch.setattr(mcp_declarations, 'perf_counter', lambda: next(ticks))
    caplog.set_level(logging.WARNING, logger='catix.mcp.server')
    original = mcp_client._http_client

    async def run():
        root = await mcp_server.build_server()
        app = root.http_app(stateless_http=True)
        monkeypatch.setattr(mcp_client, '_http_client',
                            lambda **kw: original(transport=StreamingASGITransport(app), **kw))
        async with run_asgi_lifespan(app):
            return await mcp_client.request('call_tool', {
                'name': 'sport_get_sport_trainings',
                'arguments': {'date_from': '2026-11-09', 'date_to': '2026-11-09'},
            }, 'synthetic-ih', sport_token='synthetic-sport')

    result = asyncio.run(run())
    assert result.get('code') == 'upstream_timeout'
    assert 'timed out' in result['error']
    assert requests == ['/api/v3/users/me/schedule'], 'No automatic retries'
    records = [record for record in caplog.records if record.name == 'catix.mcp.server']
    assert len(records) == 1
    message = records[0].getMessage()
    assert 'sport_get_sport_trainings' in message and 'ReadTimeout' in message and 'elapsed_ms=125.0' in message
    assert records[0].exc_info is None
    for secret in ('private-body', 'synthetic-ih', 'synthetic-sport'):
        assert secret not in caplog.text + str(result)


@pytest.mark.parametrize('generic', [False, True])
@pytest.mark.parametrize('error_type', [httpx.ReadTimeout, httpx.ConnectTimeout, httpx.WriteTimeout, httpx.PoolTimeout])
def test_timeout_is_structured_protocol_error_on_both_native_paths(monkeypatch, generic, error_type):
    attempts = []

    def fail(*args):
        attempts.append(True)
        raise error_type('private-diagnostic')

    monkeypatch.setattr(sport, 'my_trainings', fail)
    monkeypatch.setattr(mcp_server.token_verifier, 'claims', lambda token: {'uid': 'owner'})

    async def run():
        async with connection(token='synthetic-ih', sport_token='synthetic-sport') as client:
            arguments = {'date_from': '2026-11-09', 'date_to': '2026-11-09'}
            return await client.call_tool('call_tool' if generic else 'sport_get_sport_trainings',
                {'name': 'sport_get_sport_trainings', 'arguments': arguments} if generic else arguments,
                raise_on_error=False)

    result = asyncio.run(run())
    assert result.is_error
    assert isinstance(result.structured_content, dict)
    assert result.structured_content['code'] == 'upstream_timeout'
    assert mcp_client._data(result)['code'] == 'upstream_timeout'
    assert 'private-diagnostic' not in str(result)
    assert attempts == [True]


@pytest.mark.parametrize('failure', ['malformed', 'authentication', 'network'])
def test_other_failures_are_not_classified_as_timeout(monkeypatch, caplog, failure):
    def respond(request):
        if failure == 'malformed':
            return httpx.Response(200, text='private-invalid-json')
        if failure == 'authentication':
            return httpx.Response(401, json={'detail': 'private-auth-diagnostic'})
        raise httpx.ConnectError('private-network-diagnostic', request=request)

    monkeypatch.setattr(sport, '_client', httpx.Client(
        base_url='https://sport.test/api/v3/', transport=httpx.MockTransport(respond)))
    monkeypatch.setattr(mcp_server.token_verifier, 'claims', lambda token: {'uid': 'owner'})

    async def run():
        async with connection(token='synthetic-ih', sport_token='synthetic-sport') as client:
            return mcp_client._data(await client.call_tool('call_tool', {
                'name': 'sport_get_sport_trainings',
                'arguments': {'date_from': '2026-11-09', 'date_to': '2026-11-09'},
            }, raise_on_error=False))

    result = asyncio.run(run())
    assert 'error' in result and result.get('code') != 'upstream_timeout'
    assert 'private-' not in caplog.text + str(result)
    if failure == 'authentication':
        assert 'sign' in result['error']
    else:
        assert ('JSONDecodeError' if failure == 'malformed' else 'ConnectError') in caplog.text


def test_timeout_during_write_stays_unknown_and_is_logged_without_retry(monkeypatch, caplog):
    attempts = []

    def fail(*args):
        attempts.append(True)
        raise httpx.ReadTimeout('private-write-diagnostic')

    monkeypatch.setattr(sport, 'check_in', fail)
    monkeypatch.setattr(mcp_server.token_verifier, 'claims', lambda token: {'uid': 'owner'})

    async def run():
        async with connection(token='synthetic-ih', sport_token='synthetic-sport') as client:
            return mcp_client._data(await client.call_tool('call_tool', {
                'name': 'sport_sport_checkin', 'arguments': {'training_id': 7},
            }))

    result = asyncio.run(run())
    assert result['done'] is None and result['outcome'] == 'unknown'
    assert result.get('code') != 'upstream_timeout' and attempts == [True]
    assert 'sport_sport_checkin' in caplog.text and 'ReadTimeout' in caplog.text
    assert 'private-write-diagnostic' not in caplog.text + str(result)


def test_client_never_echoes_structured_timeout_diagnostics():
    from types import SimpleNamespace

    result = mcp_client._data(SimpleNamespace(is_error=True, structured_content={
        'code': 'upstream_timeout', 'error': 'private-body', 'token': 'private-token',
    }))
    assert result['code'] == 'upstream_timeout' and 'private-' not in str(result)


def test_timeout_result_preserves_typed_tool_output_schema(monkeypatch):
    def fail(*args, **kwargs):
        raise httpx.ReadTimeout('private-diagnostic')

    monkeypatch.setattr(actions, 'read', fail)

    async def run():
        async with connection() as client:
            result = await client.call_tool('maps_scenes_search_areas', {'query': '301'}, raise_on_error=False)
            assert result.is_error
            assert isinstance(result.structured_content, dict)
            assert result.structured_content['code'] == 'upstream_timeout'
        root = await mcp_server.build_server()
        declared = await root.get_tool('maps_scenes_search_areas')
        assert declared is not None and declared.output_schema is not None
        assert 'data' in declared.output_schema['required'], 'Do not weaken normal result validation'

    asyncio.run(run())


@pytest.mark.parametrize('token,sport_token', [(None, None), ('forged', 'synthetic-sport'), ('synthetic-ih', None)])
def test_timeout_handling_does_not_bypass_authentication(monkeypatch, token, sport_token):
    monkeypatch.setattr(mcp_server.token_verifier, 'claims',
                        lambda value: {'uid': 'owner'} if value == 'synthetic-ih' else None)
    monkeypatch.setattr(sport, 'my_trainings', lambda *a: pytest.fail('Credentials must be checked before service I/O'))

    async def run():
        async with connection(token=token, sport_token=sport_token) as client:
            result = await client.call_tool('call_tool', {'name': 'sport_get_sport_trainings'}, raise_on_error=False)
            assert result.is_error
            assert mcp_client._data(result).get('code') != 'upstream_timeout'

    asyncio.run(run())
