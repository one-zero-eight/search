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


def test_sync_client_bridge_works_on_event_loop_thread(mcp_connection):
    from catix.innohassle import mcp_client

    async def run():
        return mcp_client.request_sync("call_tool", {
            "name": "maps_rooms", "arguments": {"query": "301"}}, "user-a")

    assert asyncio.run(run())["data"] == [{"room": "301"}]
    assert mcp_connection == (["user-a"], ["301"])


def test_http_mutation_validation_is_definite_refusal_before_upstream(monkeypatch, caplog):
    from fastmcp.utilities.asgi_transport import StreamingASGITransport, run_asgi_lifespan
    from catix.innohassle import client as api, mcp_client, mcp_server
    from catix.settings import settings

    reads, writes = [], []
    monkeypatch.setattr(mcp_server.token_verifier, 'claims',
                        lambda token: {'uid': 'owner'} if token == 'ih' else None)
    monkeypatch.setattr(api, 'can_book_room', lambda *a: reads.append(a) or (True, None))
    monkeypatch.setattr(api, 'book_room', lambda *a: writes.append(a) or {'outlook_booking_id': 'booking'})
    monkeypatch.setattr(settings, 'innohassle_mcp_url', 'http://127.0.0.1/mcp')
    original = mcp_client._http_client
    valid = {'room_id': 'r', 'day': '2099-01-01', 'time_from': '10:30',
             'time_to': '11:30', 'title': 'Study'}

    async def run():
        root = await mcp_server.build_server()
        app = root.http_app(stateless_http=True)
        monkeypatch.setattr(mcp_client, '_http_client',
                            lambda **kw: original(transport=StreamingASGITransport(app), **kw))
        async with run_asgi_lifespan(app):
            result = await mcp_client.request('call_tool', {'name': 'rooms_book_room', 'arguments': {
                **valid, 'time_to': '10:00', 'title': 'private-input-secret'}}, 'ih')
            assert result == {'done': False, 'code': 'invalid_arguments', 'error':
                              'Invalid account operation arguments; nothing was done. '
                              'Value error, time_to must be after time_from.'}
            assert not reads and not writes
            allowed = await mcp_client.request('call_tool', {
                'name': 'rooms_book_room', 'arguments': valid}, 'ih')
            assert allowed['done'] is True

    asyncio.run(run())
    assert len(reads) == 1 and len(writes) == 1
    assert 'private-input-secret' not in caplog.text


def test_transport_failure_never_echoes_diagnostics_or_credentials(monkeypatch):
    from catix.innohassle import mcp_client

    @asynccontextmanager
    async def broken(token):
        raise RuntimeError("private-user-token: internal database diagnostic")
        yield

    monkeypatch.setattr(mcp_client, "_connection", broken)
    result = mcp_client.request_sync("search_tools", {"query": "printer"}, "private-user-token")
    assert "error" in result and "private-user-token" not in str(result) and "diagnostic" not in str(result)


def test_mutation_transport_failure_is_unknown_and_not_retryable(monkeypatch):
    from catix.innohassle import mcp_client

    attempted = []

    @asynccontextmanager
    async def broken(token, *, sport_token=None):
        attempted.append((token, sport_token))
        raise RuntimeError("private-token internal diagnostic")
        yield

    monkeypatch.setattr(mcp_client, "_connection", broken)
    result = mcp_client.request_sync("call_tool", {"name": "sport_sport_checkin", "arguments": {"training_id": 11}},
                                     "private-token", sport_token="sport-token")
    assert result["done"] is None and result["outcome"] == "unknown"
    assert "Do not retry automatically" in result["error"]
    assert "private-token" not in str(result) and "diagnostic" not in str(result)
    assert attempted == [("private-token", "sport-token")]


def test_mutation_protocol_error_after_execution_is_unknown(monkeypatch):
    from fastmcp.exceptions import ToolError
    from catix.innohassle import mcp_client

    writes = []
    server = FastMCP("uncertain", transforms=[BM25SearchTransform()])

    @server.tool
    def music_book_music_room() -> dict:
        writes.append("committed")
        raise ToolError("private-backend-diagnostic")

    @asynccontextmanager
    async def connection(token, **kwargs):
        async with Client(server, cache=False) as client:
            yield client

    monkeypatch.setattr(mcp_client, "_connection", connection)
    result = mcp_client.request_sync("call_tool", {"name": "music_book_music_room", "arguments": {}},
                                     "test-token")
    assert writes == ["committed"]
    assert result["done"] is None and result["outcome"] == "unknown"
    assert "Do not retry automatically" in result["error"] and "private-backend" not in str(result)


@pytest.mark.parametrize("value", [None, [], "unexpected", {"result": "not a receipt"},
                                   {"done": "true"}, {"done": True, "data": "x" * 40_001}])
def test_malformed_or_oversized_mutation_result_is_unknown_without_retry(monkeypatch, value):
    from types import SimpleNamespace
    from catix.innohassle import mcp_client

    called = []

    class Client:
        async def call_tool(self, method, arguments, **kwargs):
            called.append((method, arguments))
            return SimpleNamespace(is_error=False, data=value)

    @asynccontextmanager
    async def connection(token):
        yield Client()

    monkeypatch.setattr(mcp_client, "_connection", connection)
    result = mcp_client.request_sync("call_tool", {"name": "rooms_book_room", "arguments": {}}, "ih")
    assert result["done"] is None and result["outcome"] == "unknown"
    assert len(called) == 1


@pytest.mark.parametrize('inside_event_loop', [False, True])
def test_removed_preview_rpc_is_rejected_without_transport(monkeypatch, inside_event_loop):
    from catix.innohassle import mcp_client

    def forbidden(*args, **kwargs):
        pytest.fail('Removed preview must not open a transport connection')

    monkeypatch.setattr(mcp_client, "_connection", forbidden)
    payload = {"name": "rooms_book_room", "arguments": {}, "language": "en"}

    async def run():
        return await mcp_client.request("preview_tool", payload, "ih")

    result = asyncio.run(run()) if inside_event_loop else mcp_client.request_sync("preview_tool", payload, "ih")
    assert result == {"error": "Unsupported MCP interface operation."}


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
