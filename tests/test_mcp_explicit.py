"""Typed registration is entirely local; the trusted catalogue covers every leaf."""
import asyncio

from fastmcp import Client, FastMCP

from catix.innohassle import mcp_domain, mcp_server


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
        assert not hasattr(mcp_domain, 'Operation')
        assert not hasattr(mcp_domain, 'OPERATIONS')
        from catix.innohassle import mcp_tools
        declared = {name for name, fn in vars(mcp_tools).items() if callable(fn) and hasattr(fn, '__fastmcp__')}
        assert len(declared) == 23
        assert set(mcp_domain.definitions()) == declared
        for name in declared:
            assert mcp_domain.policy(name)['auth'] in {'public', 'innohassle', 'sport'}
            assert mcp_domain.schema(name) == (await root.get_tool(name)).parameters
        async with Client(root) as client:
            assert {t.name for t in await client.list_tools()} == {'search_tools', 'call_tool', 'service_status'}
            status = (await client.call_tool('service_status', {})).data
            assert sum(item['tools'] for item in status.values()) == 23
            assert all(item['registered'] for item in status.values())
    asyncio.run(run())
    assert not hasattr(mcp_server, '_EndpointTool')
    assert not hasattr(mcp_server, '_NativeTool')


def test_host_policy_lookup_never_imports_server_or_constructs_http_clients():
    import os
    import subprocess
    import sys

    code = '''
import sys
import httpx
import httpx2
from fastmcp import FastMCP
def forbidden(*args, **kwargs):
    raise AssertionError("Offline lookup constructed a server or HTTP client")
FastMCP.__init__ = forbidden
httpx.Client.__init__ = forbidden
httpx.AsyncClient.__init__ = forbidden
httpx2.AsyncClient.__init__ = forbidden
from catix.innohassle import mcp_domain
assert len(mcp_domain.definitions()) == 23
assert mcp_domain.policy("sport_sport_checkin") == {"auth": "sport", "write": True}
assert mcp_domain.schema("events_events_list_events")["properties"].keys() == {"from", "to", "club"}
assert "catix.innohassle.mcp_server" not in sys.modules
assert not any(name.startswith("catix.agent") for name in sys.modules)
assert "catix.personal_calendar" not in sys.modules
for name in ["unknown", "rooms_book_room_evil", "https://evil.test"]:
    try:
        mcp_domain.policy(name)
    except ValueError:
        pass
    else:
        raise AssertionError("Unknown target admitted")
'''
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True,
                            env={**os.environ, 'DATABASE_URL': '', 'REDIS_URL': ''}, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
