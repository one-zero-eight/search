"""Raw MCP arguments cannot become valid mutations through SDK coercion."""

import asyncio
from contextlib import asynccontextmanager
from datetime import date, datetime, time

import pytest
from fastmcp import Client

from catix.innohassle import client as backend
from catix.innohassle import mcp_domain, mcp_server
from tests.mcp_native_helpers import connection as native_connection
from catix.settings import settings


NAME = "rooms_book_room"
ARGS = {"room_id": "r", "title": "Synthetic meeting", "day": "2099-01-01", "time_from": "10:30", "time_to": "11:30"}


@pytest.fixture
def room_storage(monkeypatch):
    """Keep MCP, domain logic and HTTP client real; stub only the remote HTTP service."""
    import json
    import httpx

    monkeypatch.setattr(mcp_server.token_verifier, "claims", lambda token: {"uid": "synthetic-owner"})
    class RecordedWrites(list):
        def __init__(self):
            super().__init__()
            self.requests = []
    writes = RecordedWrites()
    def reply(request):
        writes.requests.append(request)
        assert request.headers['authorization'] == 'Bearer synthetic-token'
        if request.method == 'GET':
            assert request.url.path == '/room-booking/v0/room/r/can-book'
            return httpx.Response(200, json={'can_book': True})
        assert request.method == 'POST' and request.url.path == '/room-booking/v0/bookings/'
        body = json.loads(request.content)
        writes.append(('synthetic-token', body['room_id'], body['title'],
                       datetime.fromisoformat(body['start']), datetime.fromisoformat(body['end'])))
        return httpx.Response(200, json={'outlook_booking_id': 'booked-id'})
    with backend._http_client('https://synthetic.test', transport=httpx.MockTransport(reply)) as http:
        monkeypatch.setattr(backend, '_client', http)
        yield writes


async def call(client, name, arguments, generic):
    return await client.call_tool(
        "call_tool" if generic else name,
        {"name": name, "arguments": arguments} if generic else arguments,
        raise_on_error=False,
    )


@asynccontextmanager
async def connection(remote=False):
    async with native_connection(remote, "synthetic-token") as client:
        yield client


@pytest.mark.parametrize("remote", [False, True], ids=["inprocess", "http"])
@pytest.mark.parametrize("generic", [False, True], ids=["direct", "generic"])
@pytest.mark.parametrize("altered", [
    "10:30:59+05:00", "10:30:59", "10:30+05:00", "10:30:00.123456",
    "10:30:00", "10:30:00.000000", "10:30Z",
])
def test_invalid_raw_time_does_not_write(room_storage, generic, altered, remote):
    normalized = mcp_domain.validate(NAME, ARGS)
    invalid = {**ARGS, "time_from": altered}
    with pytest.raises(ValueError):
        mcp_domain.validate(NAME, invalid)

    async def run():
        async with connection(remote) as client:
            denied = await call(client, NAME, invalid, generic)
            assert denied.is_error, denied.data
            assert room_storage == [] and not room_storage.requests
            # A subsequent valid request must reach HTTP exactly once.
            allowed = await call(client, NAME, ARGS, generic)
            assert not allowed.is_error, allowed
            assert allowed.data["done"] is True

    asyncio.run(run())
    assert room_storage == [("synthetic-token", "r", ARGS["title"],
        datetime(2099, 1, 1, 10, 30, tzinfo=settings.tz), datetime(2099, 1, 1, 11, 30, tzinfo=settings.tz))]


@pytest.mark.parametrize("value", [
    time(10, 30, 59), time(10, 30, 0, 123456), time.fromisoformat("10:30+05:00"),
])
def test_typed_time_conversion_preserves_disallowed_components(value):
    encoded = mcp_domain._json({"time_from": value})
    assert encoded == {"time_from": value.isoformat()}
    with pytest.raises(ValueError):
        mcp_domain.validate(NAME, {**ARGS, **encoded})


def test_temporal_normalization_and_defaults_remain_unchanged():
    assert mcp_domain._json({"day": date(2099, 1, 1), "time_from": time(10, 30)}) == {
        "day": "2099-01-01", "time_from": "10:30",
    }
    stamp = datetime.fromisoformat("2099-01-01T10:30:59.123456+05:00")
    assert mcp_domain._json([stamp]) == ["2099-01-01T10:30:59.123456+05:00"]
    assert mcp_domain.validate(NAME, ARGS) == ARGS
    assert mcp_domain.validate("sport_sport_checkin", {"training_id": 7}) == {"training_id": 7, "cancel": False}
    assert mcp_domain.validate("events_events_list_events", {}) == {"from": None, "to": None, "club": None}
    assert mcp_domain.validate("events_events_list_events", {"from": stamp.isoformat(), "club": 0}) == {
        "from": stamp.isoformat(), "to": None, "club": 0,
    }


@pytest.mark.parametrize("generic", [False, True], ids=["direct", "generic"])
def test_raw_domain_failures_and_boolean_zero_do_not_reach_backend(room_storage, generic):
    invalid = [
        {**ARGS, "time_from": 0}, {**ARGS, "time_from": False},
        {**ARGS, "time_to": "10:30"}, {**ARGS, "time_to": "10:00"},
        {**ARGS, "day": "2000-01-01"}, {**ARGS, "room_id": "../other"},
    ]

    async def run():
        async with connection() as client:
            for arguments in invalid:
                with pytest.raises(ValueError):
                    mcp_domain.validate(NAME, arguments)
                assert (await call(client, NAME, arguments, generic)).is_error
                assert room_storage == [] and not room_storage.requests
            assert (await call(client, NAME, ARGS, generic)).data["done"] is True

    asyncio.run(run())
    assert len(room_storage) == 1


def test_generic_proxy_rejects_nested_interfaces_and_malformed_raw_payloads(room_storage):
    payloads = [
        {"name": "call_tool", "arguments": {"name": NAME, "arguments": ARGS}},
        {"name": "search_tools", "arguments": {"query": "calendar"}},
        {"name": "service_status"}, {"name": "call_api_tool"}, {"name": "unknown"},
        {"name": [NAME], "arguments": ARGS}, {"arguments": ARGS},
        {"name": "maps_scenes_scenes", "arguments": False},
        {"name": "maps_scenes_scenes", "arguments": 0},
        {"name": NAME, "arguments": ARGS, "approval": "arbitrary"},
    ]

    async def run():
        async with connection() as client:
            for payload in payloads:
                assert (await client.call_tool("call_tool", payload, raise_on_error=False)).is_error
                assert room_storage == [] and not room_storage.requests
            assert (await call(client, NAME, ARGS, True)).data["done"] is True

    asyncio.run(run())
    assert len(room_storage) == 1


@pytest.mark.parametrize("generic", [False, True], ids=["direct", "generic"])
@pytest.mark.parametrize("times", [
    {"time_from": "00:00", "time_to": "23:59"},
    {"time_from": "23:58", "time_to": "23:59"},
])
def test_valid_room_time_contract(room_storage, generic, times):
    arguments = {**ARGS, **times}
    normalized = mcp_domain.validate(NAME, arguments)

    async def run():
        async with connection() as client:
            result = await call(client, NAME, arguments, generic)
            assert not result.is_error, result
            assert result.data["done"] is True

    asyncio.run(run())
    start, end = time.fromisoformat(times["time_from"]), time.fromisoformat(times["time_to"])
    assert room_storage == [("synthetic-token", "r", ARGS["title"],
        datetime.combine(date(2099, 1, 1), start, settings.tz), datetime.combine(date(2099, 1, 1), end, settings.tz))]


@pytest.mark.parametrize("generic", [False, True], ids=["direct", "generic"])
def test_datetime_alias_defaults_and_integer_zero_reach_read_unchanged(monkeypatch, generic):
    import httpx
    from catix.innohassle import client as backend

    requests = []
    def reply(request):
        requests.append(request)
        return httpx.Response(200, json=[])

    stamp = "2099-01-01T10:30:59.123456+05:00"

    async def run():
        with backend._http_client("https://backend.test", transport=httpx.MockTransport(reply)) as http:
            monkeypatch.setattr(backend, "_client", http)
            async with mcp_server.adapter() as root:
                async with Client(root) as client:
                    for arguments in ({}, {"from": stamp, "club": 0}):
                        result = await call(client, "events_events_list_events", arguments, generic)
                        assert not result.is_error, result
                        assert result.data["data"] == []
                    assert (await call(client, "events_events_list_events", {"club": False}, generic)).is_error

    asyncio.run(run())
    assert [dict(request.url.params) for request in requests] == [{}, {"from": stamp, "club": "0"}]


@pytest.mark.parametrize('remote', [False, True], ids=['inprocess', 'http'])
@pytest.mark.parametrize('generic', [False, True], ids=['direct', 'generic'])
@pytest.mark.parametrize('cancel', [0, 1, 'false', 'true', None])
def test_boolean_coercion_cannot_turn_invalid_input_into_a_write(monkeypatch, remote, generic, cancel):
    import httpx
    from catix.innohassle import sport
    from tests.test_mcp_preview_server import connection as sport_connection

    monkeypatch.setattr(mcp_server.token_verifier, 'claims', lambda token: {'uid': 'owner'})
    requests = []
    def reply(request):
        requests.append(request)
        assert request.headers['authorization'] == 'Bearer sport'
        return httpx.Response(200, json={})
    name, args = 'sport_sport_checkin', {'training_id': 7, 'cancel': False}
    async def run():
        with backend._http_client('https://synthetic.test', transport=httpx.MockTransport(reply)) as http:
            monkeypatch.setattr(sport, '_client', http)
            async with sport_connection(remote) as client:
                invalid = {**args, 'cancel': cancel}
                with pytest.raises(ValueError):
                    mcp_domain.validate(name, invalid)
                assert (await call(client, name, invalid, generic)).is_error
                assert not requests
                assert (await call(client, name, args, generic)).data['signed_up'] is True
    asyncio.run(run())
    assert len(requests) == 1
    assert requests[0].url.path == '/trainings/7/checkin'
    assert dict(requests[0].url.params) == {'checkin': 'true'}
