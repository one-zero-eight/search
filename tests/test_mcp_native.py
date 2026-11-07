"""MCP owns integrations independently of the agent and local calendar."""
import asyncio
import importlib

import pytest
from fastmcp import Client

from catix.innohassle import mcp_domain, mcp_server


def test_no_calendar_or_legacy_implementation_metadata():
    definitions = mcp_domain.definitions()
    assert len(definitions) == 23
    assert not any(name.startswith('calendar_') for name in definitions)
    for definition in definitions.values():
        assert set(definition.meta['catix']) == {'auth', 'write'}
    assert not hasattr(mcp_domain, '_resolve')
    assert not hasattr(mcp_domain, 'invoke')


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


def test_preview_reads_labels_and_never_mutates(monkeypatch):
    from catix.innohassle import client as api
    seen = []
    monkeypatch.setattr(mcp_server.token_verifier, 'claims', lambda token: {'uid': 'owner'})
    monkeypatch.setattr(api, 'book_room', lambda *a: pytest.fail('Preview mutated'))
    monkeypatch.setattr(api, 'bookable_rooms', lambda token: seen.append(token) or [
        {'id': 'r', 'title': 'Meeting room', 'ru_title': 'Переговорная'}])
    arguments = {'room_id': 'r', 'day': '2099-01-01', 'time_from': '10:00', 'time_to': '11:00', 'title': 'Study'}
    async def run():
        root = await mcp_server.build_server()
        with mcp_server.credentials('ih', sport_token='unused'):
            async with Client(root) as client:
                result = (await client.call_tool('preview_tool', {'name': 'rooms_book_room', 'arguments': arguments, 'language': 'en'})).data
                assert result['name'] == 'rooms_book_room'
                assert result['arguments'] == arguments
                assert 'Meeting room' in result['description'] and 'Study' in result['description']
                assert 'preview_tool' in {tool.name for tool in await client.list_tools()}
                search = await client.call_tool('search_tools', {'query': 'book room'})
                assert 'preview_tool' not in str(search.data)
    asyncio.run(run())
    assert seen == ['ih']
