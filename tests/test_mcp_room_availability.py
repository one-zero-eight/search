"""Personal room checks over real MCP and synthetic upstream HTTP."""
import asyncio
import json
from datetime import datetime

import httpx
import pytest

from catix.innohassle import client as backend, mcp_account, mcp_server
from catix.settings import settings
from tests.mcp_native_helpers import connection

DAY = "2026-11-10"
NOW = datetime(2026, 11, 9, 12, tzinfo=settings.tz)
INTERVAL = {"day": DAY, "time_from": "10:00", "time_to": "11:00"}
BOOK = {**INTERVAL, "room_id": "r", "title": "Study"}
# Required body fields from https://api.innohassle.ru/room-booking/v0/openapi.json,
# CreateBookingRequest. participant_emails is nullable, but has no default.
ROOM_BOOKING_REQUIRED_FIELDS = {"room_id", "title", "start", "end", "participant_emails"}


@pytest.fixture
def room_api(monkeypatch):
    state = {"requests": [], "writes": [], "rooms": [{"id": "r", "title": "Room"}],
             "bookings": [], "permission": {"can_book": True, "reason_why_cannot": ""}}
    monkeypatch.setattr(mcp_account, "_now", lambda: NOW)
    monkeypatch.setattr(mcp_server.token_verifier, "claims", lambda token: {"uid": "owner"} if token == "ih" else None)

    def respond(request):
        state["requests"].append(request)
        assert request.headers["authorization"] == "Bearer ih"
        assert "cookie" not in request.headers
        path = request.url.path
        if state.get("fail_path") == path:
            if state.get("timeout"):
                raise httpx.ReadTimeout("private-upstream-detail", request=request)
            return httpx.Response(state.get("status", 503), json={"detail": "private-upstream-detail"})
        if request.method == "POST":
            assert path == "/room-booking/v0/bookings/"
            body = json.loads(request.content)
            missing = ROOM_BOOKING_REQUIRED_FIELDS - body.keys()
            if missing:
                return httpx.Response(422, json={"detail": [
                    {"type": "missing", "loc": ["body", field], "msg": "Field required"}
                    for field in sorted(missing)
                ]})
            state["writes"].append(body)
            if state.get("post_timeout"):
                raise httpx.ReadTimeout("private-upstream-detail", request=request)
            return httpx.Response(200, json={"outlook_booking_id": "created-id"})
        assert request.method == "GET"
        if path == "/room-booking/v0/rooms/":
            return httpx.Response(200, json=state["rooms"])
        if path == "/room-booking/v0/bookings/":
            return httpx.Response(200, json=state["bookings"])
        if path.startswith("/room-booking/v0/room/") and path.endswith("/can-book"):
            room_id = path.split("/")[-2]
            assert room_id in {r["id"] for r in state["rooms"]}
            return httpx.Response(200, json=state.get("permissions", {}).get(room_id, state["permission"]))
        pytest.fail(f"Unexpected path: {path}")

    with backend._http_client("https://synthetic.test", transport=httpx.MockTransport(respond)) as http:
        monkeypatch.setattr(backend, "_client", http)
        yield state


def invoke(name="rooms_get_free_rooms", arguments=None, *, generic=False, remote=False, token="ih"):
    async def run():
        async with connection(remote, token) as client:
            return await client.call_tool(
                "call_tool" if generic else name,
                {"name": name, "arguments": arguments or INTERVAL} if generic else arguments or INTERVAL,
                raise_on_error=False,
            )
    return asyncio.run(run())


@pytest.mark.parametrize("generic", [False, True])
@pytest.mark.parametrize("remote", [False, True])
def test_free_room_requires_personal_permission_for_exact_interval(room_api, generic, remote):
    room_api["permission"] = {"can_book": False, "reason_why_cannot": "Students cannot book at this time"}
    result = invoke(generic=generic, remote=remote)
    assert not result.is_error
    assert result.data["free"] == []
    assert result.data["unavailable"] == [{"room_id": "r", "reason": "Students cannot book at this time"}]
    assert result.data["booked"] == []
    checks = [r for r in room_api["requests"] if r.url.path.endswith("/can-book")]
    assert len(checks) == 1
    assert dict(checks[0].url.params) == {"start": DAY + "T10:00:00+03:00", "end": DAY + "T11:00:00+03:00"}
    room_api["permission"]["can_book"] = True
    allowed = invoke(generic=generic, remote=remote).data
    assert allowed["free"] == [{"room_id": "r", "title": "Room"}]
    assert allowed["unavailable"] == []
    assert allowed["checked_at"] == NOW.isoformat()
    assert allowed["timezone"] == str(settings.tz)
    assert room_api["writes"] == []


@pytest.mark.parametrize("generic", [False, True])
@pytest.mark.parametrize("permission", [{"can_book": "false"}, {"can_book": 1}, {"can_book": None}, {}, []])
def test_malformed_permission_cannot_authorize_read_or_write(room_api, generic, permission):
    room_api["permission"] = permission
    read = invoke(generic=generic)
    assert read.is_error or "error" in read.data
    assert "free" not in (read.data or {})
    write = invoke("rooms_book_room", BOOK, generic=generic)
    assert write.data["done"] is False
    assert write.data["code"] == "availability_unverified"
    assert room_api["writes"] == []


@pytest.mark.parametrize("generic", [False, True])
@pytest.mark.parametrize("remote", [False, True])
def test_write_rechecks_occupancy_even_when_permission_is_true(room_api, generic, remote):
    assert invoke().data["free"]
    room_api["bookings"] = [{"room_id": "r", "start": DAY + "T07:30:00Z", "end": DAY + "T08:30:00Z"}]
    denied = invoke("rooms_book_room", BOOK, generic=generic, remote=remote).data
    assert denied["done"] is False
    assert denied["code"] == "room_occupied"
    assert room_api["writes"] == []
    checks = [r for r in room_api["requests"] if r.url.path.endswith("/bookings/")]
    assert checks[-1].url.params["room_id"] == "r"
    room_api["bookings"] = [{"room_id": "r", "start": DAY + "T09:00:00+03:00", "end": DAY + "T10:00:00+03:00"}]
    allowed = invoke("rooms_book_room", BOOK, generic=generic, remote=remote).data
    assert allowed["done"] is True
    assert len(room_api["writes"]) == 1


@pytest.mark.parametrize("bookings", [{}, None, [None], [{}], [
    {"room_id": "r", "start": DAY + "T10:30:00", "end": DAY + "T09:00:00"}], [
    {"room_id": "r", "start": DAY + "T10:30:00", "end": DAY + "T10:30:00"}], [
    {"room_id": "r", "start": "bad-date", "end": DAY + "T11:00:00"}]])
def test_malformed_occupancy_never_means_free_or_allows_write(room_api, bookings):
    room_api["bookings"] = bookings
    read = invoke()
    assert read.is_error or "error" in read.data
    assert "free" not in (read.data or {})
    write = invoke("rooms_book_room", BOOK).data
    assert write["done"] is False and write["code"] == "availability_unverified"
    assert room_api["writes"] == []


def test_inventory_is_refreshed_and_checks_include_staff_rooms(room_api, monkeypatch):
    from catix.common import cache

    monkeypatch.setattr(cache, "cached", lambda key, ttl, load: [])
    assert invoke().data["free"]
    for request in room_api["requests"]:
        if request.url.path.endswith(("/rooms/", "/bookings/")):
            assert request.url.params["include_red"] == "true"
    room_api["rooms"] = []
    assert invoke().data["free"] == []
    assert len([r for r in room_api["requests"] if r.url.path.endswith("/rooms/")]) == 2


@pytest.mark.parametrize("rooms", [{}, None, [None], [{}]])
def test_malformed_inventory_is_not_an_empty_success(room_api, rooms):
    room_api["rooms"] = rooms
    result = invoke()
    assert result.is_error or "error" in result.data
    assert "free" not in (result.data or {})


@pytest.mark.parametrize("name", ["rooms_get_free_rooms", "rooms_book_room"])
def test_past_or_reversed_intervals_do_not_reach_upstream(room_api, name):
    base = BOOK if name == "rooms_book_room" else INTERVAL
    for change in [{"day": "2026-11-08"}, {"time_to": "10:00"}, {"time_to": "09:00"}]:
        result = invoke(name, {**base, **change})
        assert "error" in result.data
        assert room_api["requests"] == []


def test_interval_that_starts_during_checks_cannot_be_booked(room_api, monkeypatch):
    times = iter([NOW, datetime(2026, 11, 10, 10, 1, tzinfo=settings.tz)])
    monkeypatch.setattr(mcp_account, "_now", lambda: next(times))
    result = invoke("rooms_book_room", BOOK).data
    assert result["done"] is False
    assert "already past" in result["error"]
    assert room_api["writes"] == []


@pytest.mark.parametrize("path", ["/room-booking/v0/room/r/can-book", "/room-booking/v0/bookings/"])
@pytest.mark.parametrize("timeout", [False, True])
def test_failed_checks_are_not_availability_or_unknown_mutations(room_api, caplog, path, timeout):
    room_api.update(fail_path=path, timeout=timeout)
    read = invoke()
    assert read.is_error or "error" in read.data
    assert "free" not in (read.data or {})
    write = invoke("rooms_book_room", BOOK).data
    assert write["done"] is False and write["code"] == "availability_unverified"
    assert "private-upstream-detail" not in str(read) + str(write) + caplog.text
    assert room_api["writes"] == []


@pytest.mark.parametrize("generic", [False, True])
@pytest.mark.parametrize("token", [None, "forged"])
def test_checks_require_verified_user_before_any_upstream_io(room_api, token, generic):
    for name, args in [("rooms_get_free_rooms", INTERVAL), ("rooms_book_room", BOOK)]:
        denied = invoke(name, args, token=token, generic=generic, remote=True)
        assert denied.is_error and room_api["requests"] == []
    assert invoke("rooms_book_room", BOOK, generic=generic, remote=True).data["done"] is True


@pytest.mark.parametrize("generic", [False, True])
def test_lost_write_response_remains_unknown_and_is_never_repeated(room_api, generic):
    room_api["post_timeout"] = True
    result = invoke("rooms_book_room", BOOK, generic=generic).data
    assert result["done"] is None and result["outcome"] == "unknown"
    assert len(room_api["writes"]) == 1


@pytest.mark.parametrize("change", ["permission", "occupied", "none", "reject"])
def test_host_approval_rechecks_and_never_bypasses_availability(room_api, monkeypatch, mcp_http_protocol, change):
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
    from langgraph.types import Command
    from pydantic import SecretStr
    from catix.agent import core
    from catix.agent.tools import AgentContext
    from tests.test_roles import ScriptedModel

    monkeypatch.setattr(core.store, "visible_chats", lambda *args: [])
    assert invoke().data["free"]
    room_api["requests"].clear()
    model = ScriptedModel(responses=[
        AIMessage(content="", tool_calls=[{"name": "call_api_tool", "args": {
            "name": "rooms_book_room", "arguments": BOOK}, "id": "book", "type": "tool_call"}]),
        AIMessage(content="Результат бронирования получен."),
    ])
    agent = core.build_agent(model, guardrail=False)
    config = {"configurable": {"thread_id": "room-check-" + change}}
    context = AgentContext(innohassle_token=SecretStr("ih"), innohassle_id="owner")
    agent.invoke({"messages": [HumanMessage("Забронируй комнату r на 10 ноября с 10 до 11, название Study.")]},
                 config, context=context)
    paused = agent.get_state(config).interrupts
    assert len(paused) == 1 and room_api["requests"] == []
    if change == "permission":
        room_api["permission"] = {"can_book": False, "reason_why_cannot": "Access revoked"}
    if change == "occupied":
        room_api["bookings"] = [{"room_id": "r", "start": DAY + "T10:00:00", "end": DAY + "T11:00:00"}]
    out = agent.invoke(Command(resume={paused[0].id: {"decisions": [{"type": "reject" if change == "reject" else "approve"}]}}),
                       config, context=context)
    if change == "reject":
        assert room_api["requests"] == []
    else:
        payload = json.loads(next(m.content for m in out["messages"] if isinstance(m, ToolMessage) and m.tool_call_id == "book"))
        assert payload["done"] is (change == "none")
    assert len(room_api["writes"]) == (1 if change == "none" else 0)


def test_personal_refusals_are_read_evidence_not_empty_inventory(room_api):
    from catix.agent import core

    room_api["permission"] = {"can_book": False, "reason_why_cannot": "Only staff can book this room"}
    data = invoke().data
    assert core._read_parts("rooms_get_free_rooms", data) == ([], [], data["unavailable"])
    assert core._read_parts("rooms_get_free_rooms", {**data, "unavailable": "invalid"}) is None


def test_every_unoccupied_room_has_its_own_permission_check(room_api):
    room_api["rooms"] = [{"id": "r"}, {"id": "allowed"}, {"id": "busy"}]
    room_api["bookings"] = [{"room_id": "busy", "start": DAY + "T10:00:00", "end": DAY + "T11:00:00"}]
    room_api["permissions"] = {"r": {"can_book": False, "reason_why_cannot": "No access"}}
    data = invoke().data
    assert data["free"] == [{"room_id": "allowed"}]
    assert data["booked"] == ["busy"]
    assert data["unavailable"] == [{"room_id": "r", "reason": "No access"}]
    checks = [r.url.path for r in room_api["requests"] if r.url.path.endswith("/can-book")]
    assert checks == ["/room-booking/v0/room/r/can-book", "/room-booking/v0/room/allowed/can-book"]


@pytest.mark.parametrize("generic", [False, True])
@pytest.mark.parametrize("remote", [False, True])
def test_trace_booking_sends_required_empty_participants_without_extra_user_input(room_api, generic, remote):
    room_api["rooms"] = [{"id": "3.1"}]
    arguments = {"room_id": "3.1", "day": "2026-11-11", "time_from": "11:00", "time_to": "12:00", "title": "Тест"}
    result = invoke("rooms_book_room", arguments, generic=generic, remote=remote)
    assert not result.is_error and result.data["done"] is True, result
    assert room_api["writes"] == [{
        "room_id": "3.1", "title": "Тест", "start": "2026-11-11T11:00:00+03:00",
        "end": "2026-11-11T12:00:00+03:00", "participant_emails": [],
    }]
    assert [r.method for r in room_api["requests"]] == ["GET", "GET", "POST"]
