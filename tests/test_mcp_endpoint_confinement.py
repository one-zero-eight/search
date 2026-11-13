"""Authenticated identifiers stay within the approved endpoint; all upstream I/O is synthetic."""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone


import httpx
import httpx2
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.utilities.asgi_transport import StreamingASGITransport, run_asgi_lifespan

from catix.innohassle import client as backend, mcp_server, token



@pytest.fixture
def upstream(monkeypatch):
    requests = []

    def reply(request):
        requests.append(request)
        if request.method == "GET":
            if request.url.path == "/room-booking/v0/bookings/":
                return httpx.Response(200, json=[])
            if request.url.path.endswith(("/rooms/", "/bookings/my", "/my_bookings")):
                return httpx.Response(200, json=[])
            if request.url.path.startswith("/room-booking/v0/bookings/"):
                return httpx.Response(200, json={
                    "outlook_booking_id": request.url.path.removeprefix("/room-booking/v0/bookings/"),
                    "related_to_me": True, "room_id": "314", "title": "Study group",
                    "start": "2099-01-01T10:00:00+03:00", "end": "2099-01-01T11:00:00+03:00",
                })
            return httpx.Response(200, json={"can_book": True})
        if request.method == "POST":
            return httpx.Response(200, json={"outlook_booking_id": "outlook-id"})
        return httpx.Response(200, json=True)

    with backend._http_client("https://backend.test", transport=httpx.MockTransport(reply)) as http:
        monkeypatch.setattr(backend, "_client", http)
        yield requests


@pytest.fixture
def signed_user(monkeypatch):
    """Verify a locally signed JWT with a synthetic key, not a production account."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(token._keys, "get_signing_keys", lambda: [key.public_key()])
    return jwt.encode({"uid": "synthetic-owner", "exp": datetime.now(timezone.utc) + timedelta(hours=1)}, key, algorithm="RS256")


@asynccontextmanager
async def wire(monkeypatch, signed_user):
    async with mcp_server.adapter() as root:
        app = root.http_app(stateless_http=True)
        async with run_asgi_lifespan(app):
            def factory(headers: dict[str, str] | None = None, timeout: httpx2.Timeout | None = None,
                        auth: httpx2.Auth | None = None, **kwargs) -> httpx2.AsyncClient:
                return httpx2.AsyncClient(transport=StreamingASGITransport(app), headers=headers, timeout=timeout, auth=auth, **kwargs)

            async def call(name, arguments, *, generic=False):
                # A normal independent MCP client: credentials, no cAtIx approval ticket.
                transport = StreamableHttpTransport("http://testserver/mcp", headers={
                    "X-Innohassle-Token": signed_user,
                }, httpx_client_factory=factory)
                async with Client(transport) as mcp:
                    return await mcp.call_tool("call_tool" if generic else name,
                        {"name": name, "arguments": arguments} if generic else arguments, raise_on_error=False)
            yield call


def test_authenticated_http_cancellation_cannot_escape_to_music_room(monkeypatch, signed_user, upstream):
    async def run():
        async with wire(monkeypatch, signed_user) as call:
            result = await call("account_cancel_booking", {
                "service": "room", "booking_id": "../../../music-room/v0/bookings/42",
            })
            assert upstream == [], [(request.method, str(request.url)) for request in upstream]
            assert not result.is_error and result.data['done'] is False
            assert result.data['code'] == 'invalid_arguments'
            allowed = await call("account_cancel_booking", {"service": "room", "booking_id": "outlook-id"})
            assert allowed.data["done"] is True
            assert len(upstream) == 1
            assert upstream[0].method == "DELETE"
            assert upstream[0].url.raw_path == b"/room-booking/v0/bookings/outlook-id"
            assert upstream[0].headers["authorization"] == f"Bearer {signed_user}"
    asyncio.run(run())


UNSAFE_IDS = [
    "", ".", "..", "../42", "a/../42", "../../../music-room/v0/bookings/42",
    "a\\..\\42", "a?cancel_all=true", "a#other", "a;other", "https://other.test/id",
    "%2e%2e%2f42", "%2E%2E/42", ".%2e/42", "%252e%252e%252f42", "%25252e%25252e%25252f42",
    "a%2f42", "a%5c42", "a%3fother", "a%23other", "a%253fother", "a%2523other",
    "a\x00b", "a\r\nb", "a\tb", "a\x7fb", "a%00b", "a%250db", " id", "id ",
]


@pytest.mark.parametrize("identifier", UNSAFE_IDS)
def test_direct_room_cancellation_rejects_url_syntax_without_request(upstream, identifier):
    with pytest.raises(ValueError):
        backend.cancel_room("synthetic-user", identifier)
    assert upstream == []


@pytest.mark.parametrize("identifier", ["../42", "42?other", "42#other", "%2e%2e", "a\\42", True])
def test_direct_music_cancellation_cannot_interpolate_non_integer(upstream, identifier):
    with pytest.raises(ValueError):
        backend.cancel_music_room("synthetic-user", identifier)
    assert upstream == []


@pytest.mark.parametrize("identifier,segment", [
    ("outlook-id", b"outlook-id"),
    ("AA+/BB==", b"AA%2B%2FBB%3D%3D"),
    ("AA+/BB", b"AA%2B%2FBB"),
    ("AA/_BB==", b"AA%2F_BB%3D%3D"),
])
def test_direct_outlook_cancellation_quotes_exact_opaque_id(upstream, identifier, segment):
    backend.cancel_room("synthetic-user", identifier)
    assert len(upstream) == 1
    assert upstream[0].method == "DELETE"
    assert upstream[0].url.raw_path == b"/room-booking/v0/bookings/" + segment
    assert upstream[0].url.query == b"" and upstream[0].url.fragment == ""


def room_arguments(identifier):
    return {"room_id": identifier, "title": "Meeting", "day": "2099-01-01", "time_from": "10:00", "time_to": "11:00"}


@pytest.mark.parametrize("identifier", UNSAFE_IDS + ["a/b", "AA+/BB=="])
@pytest.mark.parametrize("operation", ["can_book_room", "book_room"])
def test_direct_room_operations_reject_unsafe_ids_without_request(upstream, identifier, operation):
    start = datetime(2099, 1, 1, 10, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    with pytest.raises(ValueError):
        if operation == "can_book_room":
            backend.can_book_room("synthetic-user", identifier, start, end)
        else:
            backend.book_room("synthetic-user", identifier, "Meeting", start, end)
    assert upstream == []


@pytest.mark.parametrize("identifier", ["../../../music-room/v0/bookings/42", "%252e%252e%252f42", "a?other", "a#other", "a\\b", "a\nb"])
@pytest.mark.parametrize("name", ["account_cancel_booking", "rooms_book_room"])
@pytest.mark.parametrize("helper", [None, "ask_docs", "ask_chats"])
def test_invalid_identifier_is_refused_before_upstream(monkeypatch, upstream, signed_user, mcp_http_protocol, name, identifier, helper):
    from langchain_core.messages import ToolMessage
    from langgraph.types import Command
    from pydantic import SecretStr
    from catix.agent import core
    from catix.agent.tools import AgentContext
    from tests.test_mcp_approval import _graph_action

    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    arguments = {"service": "room", "booking_id": identifier} if name == "account_cancel_booking" else room_arguments(identifier)
    context = AgentContext(innohassle_token=SecretStr(signed_user), innohassle_id="synthetic-owner")
    agent, config, out = _graph_action({"name": name, "arguments": arguments}, context=context, helper=helper)
    paused = agent.get_state(config).interrupts
    if name == "account_cancel_booking":
        # Cancellation now needs an exact detail read before consent; its ID validation fails without I/O.
        assert not paused and upstream == []
        assert not core.action_receipt(out["messages"])
        results = [m for m in out["messages"] if isinstance(m, ToolMessage)]
        payloads = results[0].artifact["results"] if helper else [m.content for m in results]
        assert any("confirmation" in str(value) for value in payloads)
        return
    assert len(paused) == 1 and upstream == []
    assert paused[0].value['action_requests'][0]['args']['arguments'] == arguments
    out = agent.invoke(Command(resume={paused[0].id: {'decisions': [{'type': 'approve'}]}}), config, context=context)
    assert not agent.get_state(config).interrupts and upstream == []
    assert not core.action_receipt(out['messages'])
    results = [m for m in out["messages"] if isinstance(m, ToolMessage)]
    payloads = results[0].artifact["results"] if helper else [m.content for m in results]
    refused = []
    for value in payloads:
        assert isinstance(value, str)
        result = json.loads(value)
        if 'identifier' in result.get('error', '').lower():
            refused.append(result)
    assert refused and all(result['done'] is False and result['code'] == 'invalid_arguments' for result in refused)


def test_http_room_preflight_stays_on_approved_endpoint(monkeypatch, signed_user, upstream):
    async def run():
        async with wire(monkeypatch, signed_user) as call:
            invalid = await call("rooms_book_room", room_arguments("../../../accounts/v0/tokens/generate-my-sport-token?"))
            assert upstream == [], [(request.method, str(request.url)) for request in upstream]
            assert not invalid.is_error and invalid.data['done'] is False
            assert invalid.data['code'] == 'invalid_arguments'
            allowed = await call("rooms_book_room", room_arguments("r+1@example.test"))
            assert allowed.data["done"] is True
            assert [(request.method, request.url.raw_path.split(b"?")[0]) for request in upstream] == [
                ("GET", b"/room-booking/v0/room/r%2B1%40example.test/can-book"),
                ("GET", b"/room-booking/v0/bookings/"),
                ("POST", b"/room-booking/v0/bookings/"),
            ]
            assert set(upstream[0].url.params) == {"start", "end"}
            assert dict(upstream[1].url.params) == {**dict(upstream[0].url.params), "room_id": "r+1@example.test"}
            body = json.loads(upstream[2].content)
            assert {key: body[key] for key in ("start", "end", "room_id")} == dict(upstream[1].url.params)
            assert all(request.headers['authorization'] == f'Bearer {signed_user}' for request in upstream)
    asyncio.run(run())


@pytest.mark.parametrize("identifier", UNSAFE_IDS)
@pytest.mark.parametrize("name", ["account_cancel_booking", "rooms_book_room"])
def test_invalid_identifier_is_rejected_by_server_argument_validation(name, identifier):
    from inspect import unwrap
    from typing import get_type_hints
    from pydantic import TypeAdapter
    from catix.innohassle.mcp_account import account_cancel_booking, rooms_book_room

    function, field = (account_cancel_booking, "booking_id") if name == "account_cancel_booking" else (rooms_book_room, "room_id")
    annotation = get_type_hints(unwrap(function), include_extras=True)[field]
    with pytest.raises(ValueError):
        TypeAdapter(annotation).validate_python(identifier)


@pytest.mark.parametrize("generic", [False, True])
def test_authenticated_http_rejects_encoded_and_literal_path_syntax(monkeypatch, signed_user, upstream, generic):
    async def run():
        async with wire(monkeypatch, signed_user) as call:
            for identifier in UNSAFE_IDS:
                for name, arguments in [
                    ("account_cancel_booking", {"service": "room", "booking_id": identifier}),
                    ("rooms_book_room", room_arguments(identifier)),
                ]:
                    result = await call(name, arguments, generic=generic)
                    assert upstream == [], (name, identifier, upstream)
                    assert not result.is_error and result.data['done'] is False
                    assert result.data['code'] == 'invalid_arguments'
            for identifier, segment in [("AA+/BB==", b"AA%2B%2FBB%3D%3D"), ("AA+/BB", b"AA%2B%2FBB")]:
                arguments = {"service": "room", "booking_id": identifier}
                result = await call("account_cancel_booking", arguments, generic=generic)
                assert result.data["done"] is True and result.data["cancelled"] == arguments
                assert upstream[-1].url.raw_path == b"/room-booking/v0/bookings/" + segment
            music = await call("account_cancel_booking", {"service": "music_room", "booking_id": "42"}, generic=generic)
            assert music.data["done"] is True
            assert upstream[-1].url.raw_path == b"/music-room/v0/bookings/42"
            assert len(upstream) == 3 and all(request.method == "DELETE" for request in upstream)
    asyncio.run(run())


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_graph_preserves_opaque_id_and_requires_consent(monkeypatch, signed_user, upstream, decision, mcp_http_protocol):
    from langgraph.types import Command
    from pydantic import SecretStr
    from catix.agent.tools import AgentContext
    from tests.test_mcp_approval import _graph_action

    context = AgentContext(innohassle_token=SecretStr(signed_user), innohassle_id="synthetic-owner")
    arguments = {"service": "room", "booking_id": "AA+/BB=="}
    agent, config, _ = _graph_action({"name": "account_cancel_booking", "arguments": arguments}, context=context)
    paused = agent.get_state(config).interrupts
    assert len(paused) == 1
    assert paused[0].value["action_requests"][0]["args"]["arguments"] == arguments
    assert "AA+/BB==" in paused[0].value["action_requests"][0]["description"]
    assert "Study group" in paused[0].value["action_requests"][0]["description"]
    assert [(request.method, request.url.raw_path) for request in upstream] == [
        ("GET", b"/room-booking/v0/bookings/AA%2B%2FBB%3D%3D")]
    agent.invoke(Command(resume={paused[0].id: {"decisions": [{"type": decision}]}}), config, context=context)
    writes = [request for request in upstream if request.method != "GET"]
    if decision == "approve":
        assert len(writes) == 1
        assert writes[0].url.raw_path == b"/room-booking/v0/bookings/AA%2B%2FBB%3D%3D"
    else:
        assert writes == []
    assert sum(request.method == "GET" for request in upstream) == 1, "Resume must not refetch the proposal"
