"""Timeout provenance across the HTTP projection and MCP client boundary."""

import asyncio
from contextlib import asynccontextmanager

import httpx
import httpx2
import pytest
from fastmcp.utilities.asgi_transport import StreamingASGITransport, run_asgi_lifespan
from mcp.shared.exceptions import MCPError

from catix.innohassle import mcp_client, mcp_server
from catix.settings import settings


@pytest.mark.parametrize("remote", [False, True])
def test_actions_timeout_survives_real_mcp_with_actual_mock_http(monkeypatch, remote):
    requests = []

    def respond(request):
        requests.append(request.url.path)
        raise httpx.ReadTimeout("private-body synthetic-token", request=request)

    from catix.innohassle import client as backend
    monkeypatch.setattr(backend, "_client", httpx.Client(
        base_url="https://maps.test/", transport=httpx.MockTransport(respond)))
    monkeypatch.setattr(mcp_server.token_verifier, "claims", lambda token: {"uid": "owner"})
    monkeypatch.setattr(settings, "innohassle_mcp_url", "http://127.0.0.1/mcp")
    original_factory = mcp_client._http_client

    async def run():
        root = await mcp_server.build_server()
        app = root.http_app(stateless_http=True)
        if remote:
            monkeypatch.setattr(mcp_client, "_http_client", lambda **kw: original_factory(
                transport=StreamingASGITransport(app), **kw))
            async with run_asgi_lifespan(app):
                return await mcp_client.request("call_tool", {
                    "name": "maps_scenes_search_areas", "arguments": {"query": "301"},
                })
        from fastmcp import Client
        async with Client(root) as client:
            return mcp_client._data(await client.call_tool(
                "maps_scenes_search_areas", {"query": "301"}, raise_on_error=False))

    result = asyncio.run(run())
    assert result.get("code") == "upstream_timeout"
    assert "timed out" in result["error"]
    assert requests == ["/maps/v0/scenes/areas/search"]


@pytest.mark.parametrize("exception", [httpx2.ReadTimeout, httpx2.ConnectTimeout, httpx2.PoolTimeout])
def test_mcp_transport_timeout_is_distinct_from_server_timeout(monkeypatch, exception):
    @asynccontextmanager
    async def connection(token, **kwargs):
        class Client:
            async def call_tool(self, *args, **kw):
                raise exception("private transport diagnostic")
        yield Client()

    monkeypatch.setattr(mcp_client, "_connection", connection)
    result = asyncio.run(mcp_client.request("call_tool", {
        "name": "maps_scenes_search_areas", "arguments": {"query": "301"},
    }))
    assert result.get("code") == "mcp_timeout"
    assert "private" not in str(result)


def test_mcp_deadline_is_classified_without_retry_and_cancellation_propagates(monkeypatch):
    calls = []

    @asynccontextmanager
    async def connection(token, **kwargs):
        class Client:
            async def call_tool(self, *args, **kw):
                calls.append("called")
                await asyncio.sleep(1)
        yield Client()

    monkeypatch.setattr(mcp_client, "_connection", connection)
    monkeypatch.setattr(mcp_client, "TIMEOUT", 0.01)
    result = asyncio.run(mcp_client.request("call_tool", {
        "name": "maps_scenes_search_areas", "arguments": {"query": "301"},
    }))
    assert result.get("code") == "mcp_timeout"
    assert calls == ["called"]

    async def cancelled():
        task = asyncio.create_task(mcp_client.request("call_tool", {
            "name": "maps_scenes_search_areas", "arguments": {"query": "301"},
        }))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(cancelled())


def test_actual_httpx2_mock_transport_timeout_is_classified(monkeypatch):
    from catix.settings import settings

    seen = []

    async def respond(request):
        seen.append(request.url.path)
        raise httpx2.ConnectTimeout("private transport diagnostics", request=request)

    monkeypatch.setattr(settings, "innohassle_mcp_url", "http://127.0.0.1/mcp")
    monkeypatch.setattr(mcp_client, "_http_client", lambda **kw: httpx2.AsyncClient(
        transport=httpx2.MockTransport(respond), **kw))
    result = asyncio.run(mcp_client.request("call_tool", {
        "name": "maps_scenes_search_areas", "arguments": {"query": "301"},
    }))
    assert result.get("code") == "mcp_timeout"
    assert seen


def test_unknown_operation_name_is_not_reflected_in_client_log(monkeypatch, caplog):
    @asynccontextmanager
    async def connection(token, **kwargs):
        class Client:
            async def call_tool(self, *args, **kw):
                raise RuntimeError("private exception text")
        yield Client()

    monkeypatch.setattr(mcp_client, "_connection", connection)
    private_name = "private-dynamic-operation"
    result = asyncio.run(mcp_client.request("call_tool", {
        "name": private_name, "arguments": {"secret": "private-argument"},
    }))
    assert "error" in result
    assert "tool=unknown" in caplog.text
    assert private_name not in caplog.text and "private-argument" not in caplog.text
    assert "private exception text" not in caplog.text
    assert "exception=RuntimeError" in caplog.text and "elapsed_ms=" in caplog.text


@pytest.mark.parametrize("error", [
    RuntimeError("operation timed out in private backend"),
    MCPError(1234, "timed out"),
])
def test_timeout_word_or_non_timeout_protocol_error_is_not_classified(monkeypatch, error):
    @asynccontextmanager
    async def connection(token, **kwargs):
        class Client:
            async def call_tool(self, *args, **kw):
                raise error
        yield Client()

    monkeypatch.setattr(mcp_client, "_connection", connection)
    result = asyncio.run(mcp_client.request("call_tool", {
        "name": "maps_scenes_search_areas", "arguments": {"query": "301"},
    }))
    assert "error" in result and result.get("code") != "mcp_timeout"


def test_sdk_request_timeout_code_is_classified_without_message_parsing(monkeypatch):
    from fastmcp import Client, FastMCP

    root = FastMCP("sdk-timeout")

    @root.tool
    async def call_tool(name: str, arguments: dict) -> dict:
        await asyncio.sleep(0.2)
        return {"ok": True}

    @asynccontextmanager
    async def connection(token, **kwargs):
        async with Client(root, timeout=0.01) as client:
            yield client

    monkeypatch.setattr(mcp_client, "_connection", connection)
    result = asyncio.run(mcp_client.request("call_tool", {
        "name": "maps_scenes_search_areas", "arguments": {"query": "301"},
    }))
    assert result.get("code") == "mcp_timeout"
    assert "timed out" in result["error"]


def test_timeout_controls_and_lost_mutation_response_remain_conservative(monkeypatch, caplog):
    from types import SimpleNamespace

    class Client:
        async def call_tool(self, method, arguments, **kwargs):
            if arguments.get("name") == "maps_scenes_search_areas":
                return SimpleNamespace(is_error=False, data={"ok": True})
            raise httpx2.ReadTimeout("private lost response")

    @asynccontextmanager
    async def connection(token, **kwargs):
        yield Client()

    monkeypatch.setattr(mcp_client, "_connection", connection)
    read = asyncio.run(mcp_client.request("call_tool", {
        "name": "maps_scenes_search_areas", "arguments": {"query": "301"},
    }))
    write = asyncio.run(mcp_client.request("call_tool", {
        "name": "sport_sport_checkin", "arguments": {"training_id": 11},
    }))
    assert read == {"ok": True}
    assert write["done"] is None and write["outcome"] == "unknown"
    assert "Do not retry automatically" in write["error"]
    assert "private" not in caplog.text + str(write)
