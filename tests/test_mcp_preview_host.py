"""External API approval details are read over MCP, never through agent HTTP code."""
import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from langchain_core.messages import HumanMessage
from pydantic import SecretStr

from catix.agent import api_tools
from catix.innohassle import mcp_client


def test_approval_description_comes_from_mcp_without_issuing_a_capability(monkeypatch):
    calls = []
    arguments = {"day": "2099-01-01", "time_from": "10:00", "time_to": "11:00"}
    runtime = SimpleNamespace(context=SimpleNamespace(innohassle_token=SecretStr("synthetic-user")))

    def request(name, payload, token, **credentials):
        calls.append((name, payload, token, credentials))
        return {"name": "music_book_music_room", "arguments": arguments, "description": "Описание от MCP."}

    monkeypatch.setattr(mcp_client, "request_sync", request)
    result = api_tools._describe_mutation(
        {"name": "call_api_tool", "args": {"name": "music_book_music_room", "arguments": arguments}},
        {"messages": [HumanMessage("Забронируй музыкальную комнату.")]}, runtime,
    )
    assert result == "Описание от MCP."
    assert calls == [("preview_tool", {
        "name": "music_book_music_room", "arguments": arguments, "language": "ru",
    }, "synthetic-user", {})]


@pytest.mark.parametrize("bad_preview", [
    {"error": "synthetic-user upstream diagnostics"},
    {"name": "other_tool", "arguments": {}, "description": "WRONG PREVIEW"},
    {"name": "music_book_music_room", "arguments": {"day": "2099-01-02"}, "description": "WRONG PREVIEW"},
    {"name": "music_book_music_room", "arguments": {}, "description": ""},
])
def test_failed_or_mismatched_preview_keeps_exact_confirmation_without_leaking_errors(monkeypatch, bad_preview):
    arguments = {"day": "2099-01-01", "time_from": "10:00", "time_to": "11:00"}
    call = {"name": "call_api_tool", "args": {"name": "music_book_music_room", "arguments": arguments}}
    runtime = SimpleNamespace(context=SimpleNamespace(innohassle_token=SecretStr("synthetic-user")))
    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: bad_preview)
    assert api_tools._needs_approval(SimpleNamespace(tool_call=call))
    result = api_tools._describe_mutation(call, {"messages": [HumanMessage("Book the music room.")]}, runtime)
    assert "music_book_music_room" in result and "2099-01-01" in result
    assert "10:00" in result and "11:00" in result
    assert "synthetic-user" not in result and "WRONG PREVIEW" not in result
    assert api_tools._needs_approval(SimpleNamespace(tool_call=call))


def test_sport_preview_uses_separate_credentials_without_an_approval_capability(monkeypatch):
    calls = []
    runtime = SimpleNamespace(context=SimpleNamespace(
        innohassle_token=SecretStr("synthetic-user"), sport_token=SecretStr("synthetic-sport"),
    ))

    def request(name, payload, token, **credentials):
        calls.append((name, payload, token, credentials))
        return {"name": payload["name"], "arguments": payload["arguments"], "description": "Reviewed training."}

    monkeypatch.setattr(mcp_client, "request_sync", request)
    result = api_tools._describe_mutation(
        {"name": "call_api_tool", "args": {"name": "sport_sport_checkin", "arguments": {"training_id": 7}}},
        {"messages": [HumanMessage("Register me for the training.")]}, runtime,
    )
    assert result == "Reviewed training."
    assert calls == [("preview_tool", {
        "name": "sport_sport_checkin", "arguments": {"training_id": 7}, "language": "en",
    }, "synthetic-user", {"sport_token": "synthetic-sport"})]


@pytest.mark.parametrize("inside_event_loop", [False, True])
def test_mcp_preview_transport_works_in_sync_and_async_hitl_callbacks(monkeypatch, inside_event_loop):
    calls = []
    payload = {"name": "music_book_music_room", "arguments": {}, "language": "en"}
    result = {"name": payload["name"], "arguments": {}, "description": "Remote preview."}

    class Client:
        async def call_tool(self, method, arguments, **kwargs):
            calls.append((method, arguments))
            return SimpleNamespace(is_error=False, data=result)

    @asynccontextmanager
    async def connection(token, **kwargs):
        assert token == "synthetic-user" and not kwargs
        yield Client()

    monkeypatch.setattr(mcp_client, "_connection", connection)

    def call():
        return mcp_client.request_sync("preview_tool", payload, "synthetic-user")

    async def in_loop():
        return call()

    actual = asyncio.run(in_loop()) if inside_event_loop else call()
    assert actual == result
    assert calls == [("preview_tool", payload)]


@pytest.mark.parametrize("auth,token", [("innohassle", None), ("sport", SecretStr("synthetic-user"))])
def test_missing_required_credentials_never_send_a_preview(monkeypatch, auth, token):
    sent = []
    parsed = api_tools.CallApiToolArgs(name="sport_sport_checkin", arguments={"training_id": 7})
    monkeypatch.setattr(api_tools, "_reviewed_args", lambda call: parsed)
    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: sent.append((a, kw)) or {})
    runtime = SimpleNamespace(context=SimpleNamespace(innohassle_token=token))
    description = api_tools._describe_mutation({}, {"messages": [HumanMessage("Check in.")]}, runtime)
    assert "sport_sport_checkin" in description and "7" in description
    assert sent == []


def test_preview_can_fill_defaults_but_cannot_change_explicit_values(monkeypatch):
    runtime = SimpleNamespace(context=SimpleNamespace(innohassle_token=SecretStr("ih"), sport_token=SecretStr("sport")))
    call = {"args": {"name": "sport_sport_checkin", "arguments": {"training_id": 7}}}
    preview = {"name": "sport_sport_checkin", "arguments": {"training_id": 7, "cancel": False}, "description": "Check in to training 7."}
    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: preview)
    assert api_tools._describe_mutation(call, {}, runtime) == preview["description"]
    call["args"]["arguments"]["cancel"] = True
    description = api_tools._describe_mutation(call, {}, runtime)
    assert description != preview["description"] and '"cancel": true' in description
