"""Name-only host policy: common tools, trusted credentials and no server imports."""

import asyncio
import builtins
from types import SimpleNamespace

import pytest
from pydantic import SecretStr, ValidationError

from catix.agent import api_tools, core, roles
from catix.agent.tools import AgentContext


def test_one_common_call_instance_for_every_helper():
    tool = api_tools.call_api_tool
    assert not hasattr(api_tools, "call_api_tool_for")
    assert not hasattr(api_tools, "_approved_request")
    assert set(tool.tool_call_schema.model_fields) == {"name", "arguments"}
    assert tool.tool_call_schema.model_json_schema()["additionalProperties"] is False
    for role in roles.ROLES.values():
        assert next(t for t in core.helper_tools(role) if t.name == "call_api_tool") is tool


@pytest.mark.parametrize("field", ["role", "token", "sport_token", "approval", "owner"])
def test_outer_context_fields_are_forbidden(field):
    with pytest.raises(ValidationError):
        api_tools.CallApiToolArgs.model_validate({"name": "sport_sport_checkin", "arguments": {}, field: "forged"})


@pytest.mark.parametrize("name", ["call_tool", "preview_tool", "search_tools", "service_status", "call_api_tool",
                                  "search_api_tools", "act_api_tool", "unregistered_write", "calendar_add_to_ai_calendar"])
def test_nested_unknown_and_removed_targets_fail_closed(monkeypatch, name):
    sent = []
    monkeypatch.setattr(api_tools.mcp_client, "request_sync", lambda *a, **kw: sent.append((a, kw)))
    runtime = SimpleNamespace(context=AgentContext(innohassle_token=SecretStr("user-a")))
    assert "error" in api_tools.call_api_tool.func(name, runtime, {})
    assert not api_tools._needs_approval(SimpleNamespace(tool_call={"args": {"name": name, "arguments": {}}}))
    assert sent == []


@pytest.mark.parametrize("asynchronous", [False, True])
def test_per_user_credentials_and_raw_arguments_without_server_imports(monkeypatch, asynchronous):
    sent = []
    original = builtins.__import__

    def guarded(name, globals=None, locals=None, fromlist=(), level=0):
        forbidden = {"mcp_domain", "mcp_tools", "mcp_security", "mcp_server", "mcp_declarations"}
        if name.rsplit(".", 1)[-1] in forbidden or (name == "catix.innohassle" and forbidden.intersection(fromlist)):
            pytest.fail(f"Host imported server implementation: {name} {fromlist}")
        return original(name, globals, locals, fromlist, level)

    def request(*args, **kwargs):
        sent.append((args, kwargs))
        return {"done": True}

    async def arequest(*args, **kwargs):
        return request(*args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    monkeypatch.setattr(api_tools.mcp_client, "request", arequest)
    tool = api_tools.call_api_tool
    for user in ("a", "b"):
        runtime = SimpleNamespace(context=AgentContext(innohassle_token=SecretStr(f"user-{user}"),
                                                       sport_token=SecretStr(f"sport-{user}")))
        for name, args in [("maps_scenes_scenes", {}), ("printers_print_get_printers_status", {}),
                           ("sport_sport_checkin", {"training_id": 11})]:
            result = (asyncio.run(tool.coroutine(name, runtime, args)) if asynchronous else tool.func(name, runtime, args))
            assert result == {"done": True}
    assert [(args[2], kwargs) for args, kwargs in sent] == [
        (None, {}), ("user-a", {}), ("user-a", {"sport_token": "sport-a"}),
        (None, {}), ("user-b", {}), ("user-b", {"sport_token": "sport-b"}),
    ]
    assert sent[2][0][1]["arguments"] == {"training_id": 11}  # No host defaults/canonicalizer.


@pytest.mark.parametrize("name,context", [
    ("account_get_my_schedule", AgentContext()),
    ("rooms_book_room", AgentContext()),
    ("sport_get_sports", AgentContext(innohassle_token=SecretStr("ih"))),
    ("sport_sport_checkin", AgentContext(sport_token=SecretStr("sport"))),
])
def test_missing_credentials_fail_before_transport(monkeypatch, name, context):
    monkeypatch.setattr(api_tools.mcp_client, "request_sync", lambda *a, **kw: pytest.fail("No credentials"))
    assert "error" in api_tools.call_api_tool.func(name, SimpleNamespace(context=context), {})


def test_confirmation_is_selected_by_exact_name_even_for_invalid_business_arguments():
    for name in ("rooms_book_room", "music_book_music_room", "account_cancel_booking",
                 "events_enroll_in_event", "sport_sport_checkin"):
        assert api_tools._needs_approval(SimpleNamespace(tool_call={"args": {"name": name, "arguments": {}}}))
    assert not api_tools._needs_approval(SimpleNamespace(tool_call={"args": {"name": "maps_scenes_scenes", "arguments": {}}}))


def test_client_catalogue_is_complete_and_pure():
    from catix.innohassle.mcp_access import CREDENTIAL_MODES, CONFIRMATION_TOOLS
    assert len(CREDENTIAL_MODES) == 24
    assert set(CREDENTIAL_MODES.values()) == {"public", "innohassle", "sport"}
    assert CONFIRMATION_TOOLS == {"rooms_book_room", "music_book_music_room", "account_cancel_booking",
                                  "events_enroll_in_event", "sport_sport_checkin"}
    assert CONFIRMATION_TOOLS <= CREDENTIAL_MODES.keys()
