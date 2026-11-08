"""Explicit typed tools via real FastMCP, including direct and generic paths."""
import asyncio
from types import SimpleNamespace

import pytest
from fastmcp import Client, FastMCP

from catix.innohassle import actions, mcp_server, token
from tests.mcp_native_helpers import registered_tools

MAP = 'maps_scenes_search_areas'
PRINTER = 'printers_print_get_printers_status'
EVENTS = 'events_events_list_events'


@pytest.fixture
def policy(monkeypatch):
    calls = []
    def read(path, response_model, parameters, credential, *, action_id, note):
        name = action_id.replace('.', '_', 1).replace('music-room_', 'music_', 1)
        calls.append((name, parameters, credential))
        data = []
        if name == MAP:
            data = [{'scene_id': 'floor3', 'area': {'title': '301', 'ru_title': '301', 'description': None}}]
        if name == PRINTER:
            data = [{'printer': {'display_name': 'Library', 'cups_name': 'library'},
                     'offline': False, 'paper_percentage': 0, 'toner_percentage': None}]
        return {'action_id': action_id, 'data': data,
                'total': len(data), 'truncated': False, 'note': note}
    monkeypatch.setattr(actions, 'read', read)
    monkeypatch.setattr(token, 'claims', lambda value: {'uid': value} if value in {'alice', 'bob'} else None)
    return SimpleNamespace(calls=calls)


def test_static_search_schemas_describe_typed_parameters_and_projected_output(policy):
    async def run():
        async with mcp_server.adapter() as root, Client(root) as client:
            assert {t.name for t in await client.list_tools()} == {'search_tools', 'call_tool', 'service_status'}
            results = (await client.call_tool('search_tools', {'query': 'printer printers paper toner status'})).data
            found = next(t for t in results if t['name'] == PRINTER)
            assert found['inputSchema']['properties'] == {}
            assert found['inputSchema']['additionalProperties'] is False
            declared = registered_tools()[PRINTER]
            assert declared.annotations.read_only_hint is True
            assert 'Sign-in required' in found['description']
            assert 'outputSchema' not in found
            assert 'paper_percentage' in str(declared.output_schema)
            assert 'ipp' not in str(declared.output_schema)
            results = (await client.call_tool('search_tools', {'query': 'events'})).data
            event = next(t for t in results if t['name'] == EVENTS)
            assert set(event['inputSchema']['properties']) == {'from', 'to', 'club'}
            status = (await client.call_tool('service_status', {})).data
            assert sum(item['tools'] for item in status.values()) == 25 + 4
            assert status['maps']['registered'] is True and status['maps']['tools'] == 3
            assert set(status['maps']['tool_names']) == {'maps_find_room', MAP, 'maps_scenes_scenes'}
    asyncio.run(run())
    assert not policy.calls


def test_credentials_scoped_and_public_reads_drop_tokens(policy):
    async def run():
        async with mcp_server.adapter() as root:
            async with Client(root) as client:
                for generic in (False, True):
                    result = await client.call_tool('call_tool' if generic else PRINTER,
                        {'name': PRINTER} if generic else {}, raise_on_error=False)
                    assert result.is_error and 'sign in' in str(result.content).lower()
            assert not policy.calls
            async def user(value):
                with mcp_server.credentials(value):
                    async with Client(root) as client:
                        assert not (await client.call_tool('call_tool', {'name': PRINTER})).is_error
                        assert not (await client.call_tool(MAP, {'query': '301'})).is_error
            await asyncio.gather(user('alice'), user('bob'))
            assert sorted(c[2] for c in policy.calls if c[0] == PRINTER) == ['alice', 'bob']
            assert all(c[2] is None for c in policy.calls if c[0] == MAP)
            before = len(policy.calls)
            with mcp_server.credentials('invalid'):
                async with Client(root) as client:
                    assert (await client.call_tool(MAP, {'query': '301'}, raise_on_error=False)).is_error
            assert len(policy.calls) == before
    asyncio.run(run())


@pytest.mark.parametrize('extra', [{'url': 'https://evil.test'}, {'method': 'DELETE'},
    {'path': '/printers/v0/print'}, {'headers': {'Authorization': 'secret'}}, {'token': 'secret'},
    {'cookies': {'session': 'secret'}}, {'action_id': PRINTER}, {'runtime': {}}, {'uid': 'other'}])
def test_both_paths_reject_model_http_and_identity_controls(policy, extra):
    async def run():
        async with mcp_server.adapter() as root, Client(root) as client:
            args = {'query': '301', **extra}
            assert (await client.call_tool(MAP, args, raise_on_error=False)).is_error
            assert (await client.call_tool('call_tool', {'name': MAP, 'arguments': args}, raise_on_error=False)).is_error
            assert not policy.calls
            assert (await client.call_tool(MAP, {'query': '301'})).data['data'][0]['scene_id'] == 'floor3'
    asyncio.run(run())


@pytest.mark.parametrize('args,expected', [
    ({'from': None, 'to': None, 'club': None}, {'from': None, 'to': None, 'club': None}),
    ({'club': 0}, {'from': None, 'to': None, 'club': 0}),
    ({'from': '2026-11-07T12:00:00+03:00'}, {'from': '2026-11-07T12:00:00+03:00', 'to': None, 'club': None}),
])
def test_event_alias_and_null_zero_normalization_on_both_paths(policy, args, expected):
    async def run():
        async with mcp_server.adapter() as root, Client(root) as client:
            assert not (await client.call_tool(EVENTS, args)).is_error
            assert not (await client.call_tool('call_tool', {'name': EVENTS, 'arguments': args})).is_error
            assert policy.calls == [(EVENTS, expected, None)] * 2
    asyncio.run(run())


@pytest.mark.parametrize('args', [{'from': 'tomorrow'}, {'from': '2026-11-07'}, {'club': '0'},
                                 {'club': True}, {'from_': '2026-11-07T12:00:00+03:00'}])
def test_event_alias_invalid_types_and_formats_fail_before_dispatch(policy, args):
    async def run():
        async with mcp_server.adapter() as root, Client(root) as client:
            for generic in (False, True):
                result = await client.call_tool('call_tool' if generic else EVENTS,
                    {'name': EVENTS, 'arguments': args} if generic else args, raise_on_error=False)
                assert result.is_error
            assert not policy.calls
    asyncio.run(run())


def test_http_credentials_per_request_never_meta_or_process_state(policy, caplog):
    import httpx2
    from fastmcp.client.transports import StreamableHttpTransport
    from fastmcp.utilities.asgi_transport import StreamingASGITransport, run_asgi_lifespan
    async def run():
        async with mcp_server.adapter() as root:
            app = root.http_app(stateless_http=True)
            async with run_asgi_lifespan(app):
                clients = []
                def factory(**kwargs):
                    client = httpx2.AsyncClient(transport=StreamingASGITransport(app), **kwargs)
                    clients.append(client)
                    return client
                transport = StreamableHttpTransport('http://testserver/mcp', headers={
                    'X-Innohassle-Token': 'alice', 'Authorization': 'Bearer ignored-secret', 'Cookie': 'session=ignored-secret',
                }, httpx_client_factory=factory)
                with mcp_server.credentials('process-admin-secret'):
                    async with Client(transport) as client:
                        await client.call_tool(PRINTER, {})
                        for http in clients:
                            http.headers.pop('x-innohassle-token', None)
                        assert (await client.call_tool(PRINTER, {}, raise_on_error=False,
                            meta={'uid': 'alice', 'token': 'alice', 'x-innohassle-token': 'alice'})).is_error
                        await client.call_tool(MAP, {'query': '301'})
                        for http in clients:
                            http.headers['x-innohassle-token'] = 'bob'
                        await client.call_tool('call_tool', {'name': PRINTER})
            assert [c[2] for c in policy.calls if c[0] == PRINTER] == ['alice', 'bob']
            assert all(c[2] is None for c in policy.calls if c[0] == MAP)
    asyncio.run(run())
    assert 'ignored-secret' not in caplog.text and 'process-admin-secret' not in caplog.text


@pytest.mark.parametrize('safe', [True, False])
def test_errors_useful_but_do_not_leak_diagnostics(policy, monkeypatch, caplog, safe):
    def fail(*args, **kwargs):
        if safe:
            raise actions.ReadError('This account does not have permission for that API action.')
        raise RuntimeError('upstream-secret-body-token')
    monkeypatch.setattr(actions, 'read', fail)
    async def run():
        async with mcp_server.adapter() as root, Client(root) as client:
            result = await client.call_tool('call_tool', {'name': MAP, 'arguments': {'query': '301'}}, raise_on_error=False)
            assert result.is_error
            assert ('permission' if safe else 'unavailable') in str(result.content)
            assert 'upstream-secret' not in str(result)
    asyncio.run(run())
    assert 'upstream-secret' not in caplog.text


def test_main_serves_loopback_http_by_default(policy, monkeypatch):
    import sys
    options = []
    async def serve(self, **kwargs):
        options.append(kwargs)
        async with Client(self) as client:
            assert (await client.call_tool('service_status', {})).data['maps']['registered']
    monkeypatch.setattr(FastMCP, 'run_async', serve)
    monkeypatch.setattr(sys, 'argv', ['catix-mcp'])
    mcp_server.main()
    assert options == [{'transport': 'http', 'host': '127.0.0.1', 'port': 8010,
                        'path': '/mcp', 'stateless_http': True, 'show_banner': False}]
