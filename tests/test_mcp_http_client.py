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
                    mcp_client.request("call_tool", {"name": "printers_print_get_printers_status", "arguments": {}}, identity)
                    for identity in ("alice", "bob")
                ))
                assert all(response["data"][0]["paper_percentage"] == 0 for response in responses)
                public = await mcp_client.request("call_tool", {"name": "maps_scenes_search_areas", "arguments": {"query": "301"}}, "alice")
                assert public["data"][0]["scene_id"] == "floor3"
                found = await mcp_client.request("search_tools", {"query": "maps"})
                assert found["tools"] and found["services"]["maps"]["registered"]
                denied = await mcp_client.request("call_tool", {"name": "printers_print_get_printers_status", "arguments": {}})
                assert "signing in" in denied["error"]
        assert clients and all(client.is_closed for client in clients)
        assert all(not list(client.cookies.jar) for client in clients)

    asyncio.run(run())
    assert sorted(call[2] for call in policy.calls if call[0] == "printers_print_get_printers_status") == ["alice", "bob"]
    assert all(call[2] is None for call in policy.calls if call[0] == "maps_scenes_search_areas")
    assert requests and all(b"cookie" not in headers and b"authorization" not in headers for headers in requests)


def test_http_client_sends_only_service_credentials_out_of_band(monkeypatch):
    from catix.innohassle import mcp_domain, sport
    from tests.test_sport import VOLLEYBALL

    requests, writes = [], []
    original = mcp_client._http_client

    monkeypatch.setattr(settings, "innohassle_mcp_url", "http://127.0.0.1/mcp")
    monkeypatch.setattr(token, "claims", lambda value: {"uid": "u1"} if value == "user-token" else None)
    monkeypatch.setattr(sport, "training", lambda access, ident: VOLLEYBALL)
    monkeypatch.setattr(sport, "check_in", lambda *args: writes.append(args))

    args = mcp_domain.validate("sport_sport_checkin", {"training_id": 11})

    class RecordRequests:
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            if scope["type"] == "http":
                requests.append(dict(scope["headers"]))
            await self.app(scope, receive, send)

    async def run():
        async with mcp_server.adapter() as root:
            app = root.http_app(stateless_http=True)
            app.add_middleware(RecordRequests)
            monkeypatch.setattr(mcp_client, "_http_client", lambda **kwargs: original(transport=StreamingASGITransport(app), **kwargs))
            async with run_asgi_lifespan(app):
                result = await mcp_client.request("call_tool", {"name": "sport_sport_checkin", "arguments": args},
                                                  "user-token", sport_token="sport-token")
                assert result["done"] is True and writes == [("sport-token", 11, True)]
                assert all(secret not in str(result) for secret in ("user-token", "sport-token"))
                repeated = await mcp_client.request("call_tool", {"name": "sport_sport_checkin", "arguments": args},
                                                  "user-token", sport_token="sport-token")
                assert repeated["done"] is True and writes == [("sport-token", 11, True)] * 2
                await mcp_client.request("search_tools", {"query": "calendar"}, "user-token")

    asyncio.run(run())
    assert any(headers.get(b"x-sport-token") == b"sport-token" for headers in requests)
    assert all(b"x-catix-approval" not in headers for headers in requests)
    assert b"x-sport-token" not in requests[-1]
    assert all(b"cookie" not in headers and b"authorization" not in headers for headers in requests)
