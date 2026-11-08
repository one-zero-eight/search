"""FastMCP registration owns the catalogue, schemas and native dependencies."""
import asyncio
import importlib.util

import pytest
from fastmcp import Client, FastMCP
from fastmcp.dependencies import Depends
from fastmcp.tools import tool

from catix.innohassle import mcp_server


def test_startup_registers_all_typed_tools_without_schema_network(monkeypatch):
    import httpx
    import httpx2

    attempts = []
    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError('Startup must not construct HTTP clients or fetch schemas')

    monkeypatch.setattr(httpx.Client, 'send', forbidden)
    monkeypatch.setattr(httpx2, 'AsyncClient', forbidden)
    monkeypatch.setattr(FastMCP, 'from_openapi', forbidden)

    async def run():
        root = await mcp_server.build_server()
        assert not attempts
        from catix.innohassle import mcp_tools
        names = {name for name, fn in vars(mcp_tools).items() if callable(fn) and hasattr(fn, '__fastmcp__')}
        assert len(names) == 23
        for name in names:
            declared = await root.get_tool(name)
            assert declared.parameters['additionalProperties'] is False
            assert 'token' not in declared.parameters['properties']
            assert not hasattr(declared.fn, '_args_model')
        async with Client(root) as client:
            assert {t.name for t in await client.list_tools()} == {'search_tools', 'call_tool', 'service_status'}
            status = (await client.call_tool('service_status', {})).data
            assert sum(item['tools'] for item in status.values()) == 23
            assert {name for item in status.values() for name in item['tool_names']} == names
            assert all(item['registered'] for item in status.values())
    asyncio.run(run())
    assert importlib.util.find_spec('catix.innohassle.mcp_domain') is None


def test_registered_tool_is_callable_without_an_offline_catalogue():
    async def run():
        root = await mcp_server.build_server()
        def identity():
            return 'dependency-value'
        @tool(annotations={'readOnlyHint': True})
        def native_echo(value: int, *, injected: str = Depends(identity)) -> dict:
            return {'value': value, 'injected': injected}
        root.add_tool(native_echo)
        async with Client(root) as client:
            for name, args in [('native_echo', {'value': 7}),
                               ('call_tool', {'name': 'native_echo', 'arguments': {'value': 7}})]:
                result = await client.call_tool(name, args, raise_on_error=False)
                assert not result.is_error, result
                assert result.data == {'value': 7, 'injected': 'dependency-value'}
    asyncio.run(run())


def test_duplicate_tool_registration_fails(monkeypatch):
    from catix.innohassle import mcp_tools
    monkeypatch.setattr(mcp_tools, 'duplicate', mcp_tools.rooms_book_room, raising=False)
    with pytest.raises(ValueError):
        asyncio.run(mcp_server.build_server())


def test_native_inputs_are_checked_once_and_dependencies_are_not_model_inputs(monkeypatch):
    from typing import Annotated
    from pydantic import BeforeValidator
    from catix.innohassle.mcp_declarations import metadata, require_sport, result_boundary

    checked, bodies = [], []
    monkeypatch.setattr(mcp_server.token_verifier, 'claims', lambda token: {'uid': 'owner'})
    def observe(value):
        checked.append(value)
        return value
    @tool(**metadata(write=True))
    @result_boundary(write=True)
    def native_write(value: Annotated[int, BeforeValidator(observe)], *, token: str = Depends(require_sport)) -> dict:
        bodies.append((value, token))
        return {'done': True}

    async def run():
        root = await mcp_server.build_server()
        declared = root.add_tool(native_write)
        assert set(declared.parameters['properties']) == {'value'}
        for generic in (False, True):
            with mcp_server.credentials('ih', sport_token='sport'):
                async with Client(root) as client:
                    payload = {'name': 'native_write', 'arguments': {'value': 7}} if generic else {'value': 7}
                    assert (await client.call_tool('call_tool' if generic else 'native_write', payload)).data['done']
            with mcp_server.credentials('ih'):
                async with Client(root) as client:
                    denied = await client.call_tool('native_write', {}, raise_on_error=False)
                    assert denied.is_error and 'Sport sign-in' in str(denied.content)
    asyncio.run(run())
    assert checked == [7, 7]
    assert bodies == [(7, 'sport'), (7, 'sport')]
