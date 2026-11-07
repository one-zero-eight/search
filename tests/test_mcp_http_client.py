"""Exercise cAtIx's configured HTTP client branch against the actual adapter ASGI app."""

import asyncio

from fastmcp.utilities.asgi_transport import StreamingASGITransport, run_asgi_lifespan

from catix.innohassle import mcp_client, mcp_server, token
from catix.settings import settings
from tests.test_mcp_server import policy  # noqa: F401 - reviewed synthetic upstream fixture


def test_configured_http_client_isolates_tokens_refuses_cookies_and_closes_connections(policy, monkeypatch):
    requests, clients = [], []
    original = mcp_client._http_client
    monkeypatch.setattr(settings, "innohassle_mcp_url", "http://127.0.0.1/mcp")
    monkeypatch.setattr(token, "claims", lambda value: {"uid": value} if value in {"alice", "bob"} else None)

    class InjectCookie:
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            if scope["type"] == "http":
                headers = dict(scope["headers"])
                requests.append(headers)

            async def reply(message):
                if message["type"] == "http.response.start":
                    message = {**message, "headers": [*message["headers"], (b"set-cookie", b"session=must-not-be-replayed; Path=/; HttpOnly")]}
                await send(message)

            await self.app(scope, receive, reply)

    async def run():
        async with mcp_server.adapter() as root:
            app = root.http_app(stateless_http=True)
            app.add_middleware(InjectCookie)

            def factory(**kwargs):
                client = original(transport=StreamingASGITransport(app), **kwargs)
                clients.append(client)
                return client

            monkeypatch.setattr(mcp_client, "_http_client", factory)
            async with run_asgi_lifespan(app):
                responses = await asyncio.gather(*(
                    mcp_client.request("call_tool", {"name": "printers_list", "arguments": {}}, identity)
                    for identity in ("alice", "bob")
                ))
                assert all(response["data"] == [{"printer": "visible"}] for response in responses)
                public = await mcp_client.request("call_tool", {"name": "maps_list", "arguments": {}}, "alice")
                assert public["data"] == [{"room": "visible"}]
                found = await mcp_client.request("search_tools", {"query": "maps"})
                assert found["tools"] and found["services"]["maps"]["available"]
                denied = await mcp_client.request("call_tool", {"name": "printers_list", "arguments": {}})
                assert "signing in" in denied["error"]
        assert clients and all(client.is_closed for client in clients)
        assert all(not list(client.cookies.jar) for client in clients)

    asyncio.run(run())
    assert sorted(call[2] for call in policy.calls if call[0] == "printers.list") == ["alice", "bob"]
    assert all(call[2] is None for call in policy.calls if call[0] == "maps.list")
    assert requests and all(b"cookie" not in headers and b"authorization" not in headers for headers in requests)
