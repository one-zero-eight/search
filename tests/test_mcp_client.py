"""cAtIx uses the MCP protocol, not the old local catalogue, and never gives credentials to the model."""

import asyncio
from contextlib import asynccontextmanager

import pytest
from fastmcp import Client, FastMCP
from fastmcp.server.transforms.search import BM25SearchTransform


@pytest.fixture
def mcp_connection(monkeypatch):
    from catix.innohassle import mcp_client

    server = FastMCP("test", transforms=[BM25SearchTransform(always_visible=["service_status"])])
    tokens, calls = [], []

    @server.tool
    def maps_rooms(query: str) -> dict:
        """Find rooms by number on the campus map."""
        calls.append(query)
        return {"data": [{"room": query}], "total": 1, "truncated": False}

    @server.tool
    def service_status() -> dict:
        return {"available": ["maps"], "unavailable": ["clubs"]}

    @asynccontextmanager
    async def connection(token):
        tokens.append(token)
        async with Client(server, cache=False) as client:
            yield client

    monkeypatch.setattr(mcp_client, "_connection", connection)
    return tokens, calls


def test_client_search_and_call_go_through_real_mcp_and_report_partial_catalogue(mcp_connection):
    from catix.innohassle import mcp_client

    found = mcp_client.request_sync("search_tools", {"query": "rooms"}, "private-user-token")
    assert found["tools"][0]["name"] == "maps_rooms"
    assert found["tools"][0]["inputSchema"]["required"] == ["query"]
    assert found["services"]["unavailable"] == ["clubs"]
    result = mcp_client.request_sync("call_tool", {"name": "maps_rooms", "arguments": {"query": "301"}}, "private-user-token")
    assert result["data"] == [{"room": "301"}]
    assert mcp_connection == (["private-user-token", "private-user-token"], ["301"])
    assert "private-user-token" not in str(found) + str(result)


def test_async_client_handles_simultaneous_users_without_shared_credentials(mcp_connection):
    from catix.innohassle import mcp_client

    async def run():
        return await asyncio.gather(*(mcp_client.request("call_tool", {"name": "maps_rooms", "arguments": {"query": room}}, token)
                                      for room, token in [("301", "user-a"), ("302", "user-b")]))

    results = asyncio.run(run())
    assert {r["data"][0]["room"] for r in results} == {"301", "302"}
    assert sorted(mcp_connection[0]) == ["user-a", "user-b"]


def test_transport_failure_never_echoes_diagnostics_or_credentials(monkeypatch):
    from catix.innohassle import mcp_client

    @asynccontextmanager
    async def broken(token):
        raise RuntimeError("private-user-token: internal database diagnostic")
        yield

    monkeypatch.setattr(mcp_client, "_connection", broken)
    result = mcp_client.request_sync("search_tools", {"query": "printer"}, "private-user-token")
    assert "error" in result and "private-user-token" not in str(result) and "diagnostic" not in str(result)


@pytest.mark.parametrize("url", ["http://outside.example/mcp", "https://user:password@outside.example/mcp", "https://outside.example/mcp?token=secret"])
def test_remote_credentials_require_https_or_loopback_without_url_credentials(url):
    from catix.innohassle import mcp_client

    with pytest.raises(ValueError):
        mcp_client.validate_url(url)


def test_mcp_sdk_cannot_follow_same_origin_redirects_with_delegated_credentials(monkeypatch):
    import httpx2
    from catix.innohassle import mcp_client
    from catix.settings import settings

    asked = []
    original = mcp_client._http_client

    def respond(request):
        asked.append((request.url.path, request.headers.get("x-innohassle-token")))
        if request.url.path == "/mcp":
            return httpx2.Response(307, headers={"Location": "/collect-credentials"})
        return httpx2.Response(400, text="not an MCP endpoint")

    def factory(**kwargs):
        return original(transport=httpx2.MockTransport(respond), **kwargs)

    monkeypatch.setattr(mcp_client, "_http_client", factory)
    monkeypatch.setattr(settings, "innohassle_mcp_url", "https://adapter.test/mcp")
    out = mcp_client.request_sync("search_tools", {"query": "printer"}, "private-user-token")
    assert "error" in out and "private-user-token" not in str(out)
    assert asked and all(path == "/mcp" for path, _ in asked), asked
