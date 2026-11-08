"""MCP owns integrations independently of the agent and local calendar."""
import asyncio
import importlib

from fastmcp import Client

from catix.innohassle import mcp_server
from tests.mcp_native_helpers import registered_tools


def test_no_calendar_or_legacy_implementation_metadata():
    definitions = registered_tools()
    assert len(definitions) == 24 + 4 + 2 + 1 + 3
    assert not any(name.startswith('calendar_') for name in definitions)
    for definition in definitions.values():
        assert 'catix' not in (definition.meta or {})
        assert not hasattr(definition.fn, '_args_model')
        assert not hasattr(definition.fn, '_preview')
    assert importlib.util.find_spec('catix.innohassle.mcp_domain') is None


def test_sport_implementation_runs_without_agent_import(monkeypatch):
    from catix.innohassle import sport
    called = []
    monkeypatch.setattr(sport, 'check_in', lambda *args: called.append(args))
    monkeypatch.setattr(mcp_server.token_verifier, 'claims', lambda token: {'uid': 'owner'})

    original = importlib.import_module
    def guarded(name, *args, **kwargs):
        assert not name.startswith('catix.agent')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(importlib, 'import_module', guarded)
    async def run():
        root = await mcp_server.build_server()
        with mcp_server.credentials('ih', sport_token='sport'):
            async with Client(root) as client:
                result = await client.call_tool('sport_sport_checkin', {'training_id': 7})
                assert result.data['signed_up'] is True
    asyncio.run(run())
    assert called == [('sport', 7, True)]


def test_mutation_discovery_never_reads_display_labels_or_mutates(monkeypatch):
    from catix.innohassle import client as api
    seen = []
    monkeypatch.setattr(mcp_server.token_verifier, 'claims', lambda token: {'uid': 'owner'})
    monkeypatch.setattr(api, 'book_room', lambda *a: seen.append(a))
    monkeypatch.setattr(api, 'bookable_rooms', lambda token: seen.append(token) or [])
    async def run():
        root = await mcp_server.build_server()
        with mcp_server.credentials('ih', sport_token='unused'):
            async with Client(root) as client:
                assert 'preview_tool' not in {tool.name for tool in await client.list_tools()}
                search = await client.call_tool('search_tools', {'query': 'book room'})
                assert 'preview_tool' not in str(search.data)
                assert any(tool['name'] == 'rooms_book_room' for tool in search.data)
    asyncio.run(run())
    assert not seen
