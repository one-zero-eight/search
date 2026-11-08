"""Common MCP calls wait for name-selected consent in every exposing graph."""

from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command
from pydantic import SecretStr

from catix.agent import api_tools, core
from catix.agent.tools import AgentContext
from catix.innohassle import mcp_domain
from tests.test_roles import ScriptedModel


def _graph_action(args, context=None, tool="call_api_tool", helper=None):
    script = ([AIMessage(content="", tool_calls=[{"name": helper, "args": {"question": "Выполни действие во внешнем сервисе"}, "id": "s1"}])]
              if helper else []) + [AIMessage(content="", tool_calls=[{"name": tool, "args": args, "id": "h1"}]),
                                    *[AIMessage(content="Обработано.") for _ in range(4)]]
    agent = core.build_agent(ScriptedModel(responses=script), guardrail=False)
    config = {"configurable": {"thread_id": "mcp-consent"}}
    context = context if context is not None else AgentContext(innohassle_token=SecretStr("user-token"))
    out = agent.invoke({"messages": [HumanMessage("Выполни действие во внешнем сервисе")]}, config, context=context)
    return agent, config, out


@pytest.fixture(autouse=True)
def no_chat_database(monkeypatch):
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])


@pytest.mark.parametrize("helper", [None, "ask_docs", "ask_chats"])
@pytest.mark.parametrize("decision", ["approve", "reject"])
@pytest.mark.parametrize("spoof", [False, {"context": {"role": "account", "innohassle_token": "forged"}}, None, "forged"])
def test_every_context_waits_for_consent_and_sends_only_normal_credentials(monkeypatch, helper, decision, spoof):
    sent, previews = [], []
    args = {"name": "sport_sport_checkin", "arguments": {"training_id": 11}}

    def request(method, payload, token=None, **credentials):
        if method == "search_tools":
            assert token is None and credentials == {}
            return {"tools": [{"name": payload["query"], "inputSchema": mcp_domain.schema(payload["query"])}]}
        assert token == "user-token" and credentials == {"sport_token": "sport-token"}
        if method == "preview_tool":
            previews.append(payload)
            return {"name": args["name"], "arguments": {"training_id": 11, "cancel": False}, "description": "Volleyball training #11"}
        sent.append(payload)
        return {"done": True}

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    context = AgentContext(innohassle_token=SecretStr("user-token"), sport_token=SecretStr("sport-token"))
    model_args = {**args, "runtime": spoof} if spoof is not False else args
    agent, config, _ = _graph_action(model_args, helper=helper, context=context)
    paused = agent.get_state(config).interrupts
    assert len(paused) == 1 and sent == []
    assert previews == [{**args, "language": "ru"}]
    assert paused[0].value["action_requests"][0]["description"] == "Volleyball training #11"
    out = agent.invoke(Command(resume={paused[0].id: {"decisions": [{"type": decision}]}}), config, context=context)
    assert not agent.get_state(config).interrupts
    assert sent == ([args] if decision == "approve" else [])
    assert all(secret not in str(out) for secret in ("user-token", "sport-token"))


@pytest.mark.parametrize("helper", [None, "ask_docs", "ask_chats"])
@pytest.mark.parametrize("name", ["maps_scenes_scenes", "printers_print_get_printers_status"])
def test_reads_never_interrupt(monkeypatch, helper, name):
    sent = []
    monkeypatch.setattr(api_tools.mcp_client, "request_sync", lambda *a, **kw: sent.append((a, kw)) or {"data": []})
    args = {"name": name, "arguments": {}}
    agent, config, _ = _graph_action(args, helper=helper)
    assert not agent.get_state(config).interrupts
    assert sent == [(("call_tool", args, None if name == "maps_scenes_scenes" else "user-token"), {})]


@pytest.mark.parametrize("args", [
    {"name": "call_tool", "arguments": {}},
    {"name": "preview_tool", "arguments": {}},
    {"name": "unknown_mutation", "arguments": {}},
    {"name": "calendar_add_to_ai_calendar", "arguments": {}},
    {"name": "account_cancel_booking", "arguments": [],},
    {"name": "account_cancel_booking", "arguments": None},
    {"name": 123, "arguments": {}},
    {"name": "account_cancel_booking", "arguments": {}, "role": "account"},
    {"name": "account_cancel_booking", "arguments": {}, "token": "forged"},
    {"name": "account_cancel_booking", "arguments": {}, "approval": "forged"},
])
def test_invalid_outer_shape_and_unknown_targets_never_send_or_interrupt(monkeypatch, args):
    sent = []
    monkeypatch.setattr(api_tools.mcp_client, "request_sync", lambda *a, **kw: sent.append((a, kw)) or {})
    agent, config, out = _graph_action({**args, "runtime": {"context": {"innohassle_id": "forged"}}})
    assert not agent.get_state(config).interrupts
    assert sent == []
    result = next(m for m in out["messages"] if isinstance(m, ToolMessage) and m.name == "call_api_tool")
    assert isinstance(result.content, str)
    assert "error" in result.content.lower()


@pytest.mark.parametrize("helper", [None, "ask_docs", "ask_chats"])
def test_server_preview_validation_prevents_consent_and_execution(monkeypatch, helper):
    sent, previews = [], []

    def request(method, payload, token=None, **kwargs):
        if method == "search_tools":
            assert token is None and kwargs == {}
            return {"tools": [{"name": payload["query"], "inputSchema": mcp_domain.schema(payload["query"])}]}
        if method == "preview_tool":
            previews.append(payload)
            return {"code": "invalid_arguments", "error": "time_to must be after time_from."}
        sent.append(payload)
        return {"error": "Invalid business arguments"}

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    # Individual field types/formats are valid; the server owns this cross-field rule.
    args = {"name": "rooms_book_room", "arguments": {
        "day": "2099-01-01", "room_id": "r1", "title": "Meeting", "time_from": "11:00", "time_to": "10:00"}}
    agent, config, _ = _graph_action(args, helper=helper)
    assert not agent.get_state(config).interrupts
    assert sent == []
    assert previews == [{**args, "language": "ru"}]


@pytest.mark.parametrize("context,name", [
    (AgentContext(), "rooms_book_room"),
    (AgentContext(innohassle_token=SecretStr("user-token")), "sport_sport_checkin"),
])
def test_missing_required_user_credentials_skip_hitl_and_network(monkeypatch, context, name):
    monkeypatch.setattr(api_tools.mcp_client, "request_sync", lambda *a, **kw: pytest.fail("No credentials"))
    agent, config, out = _graph_action({"name": name, "arguments": {}}, helper=None, context=context)
    assert not agent.get_state(config).interrupts
    assert "sign" in str(out).lower()


@pytest.mark.parametrize("receipt,answer", [
    ({"done": True}, "Бронирование отменено. Объявления проверить не удалось."),
    ({"done": None, "outcome": "unknown", "error": "Do not retry automatically."},
     "Результат отмены не подтверждён; повторять действие нельзя. Объявления проверить не удалось."),
])
def test_root_action_receipt_survives_unrelated_helper_failure(monkeypatch, receipt, answer):
    sent = []
    args = {"name": "account_cancel_booking", "arguments": {"service": "room", "booking_id": "booking-5"}}

    def request(method, payload, token=None, **kwargs):
        if method == "search_tools":
            assert token is None and kwargs == {}
            return {"tools": [{"name": payload["query"], "inputSchema": mcp_domain.schema(payload["query"])}]}
        if method == "preview_tool":
            return {"name": args["name"], "arguments": args["arguments"], "description": "Cancel booking-5"}
        sent.append(payload)
        return receipt

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    script = [AIMessage(content="", tool_calls=[{"name": "call_api_tool", "args": args, "id": "w1"}]),
              AIMessage(content="", tool_calls=[{"name": "ask_chats", "args": {"question": "Есть объявления?"}, "id": "h1"}]),
              AIMessage(content=core.TOOL_FAILURE_ANSWER), AIMessage(content=answer)]
    agent = core.build_agent(ScriptedModel(responses=script), guardrail=False)
    config = {"configurable": {"thread_id": "mixed-action-result"}}
    context = AgentContext(innohassle_token=SecretStr("user-token"))
    agent.invoke({"messages": [HumanMessage("Отмени бронь и проверь объявления.")]}, config, context=context)
    paused = agent.get_state(config).interrupts[0]
    out = agent.invoke(Command(resume={paused.id: {"decisions": [{"type": "approve"}]}}), config, context=context)
    assert sent == [args]
    assert core.final_answer(out["messages"], {}) == answer
    assert core.read_evidence(out["messages"]) is False
    assert core.successful_read(out["messages"]) is False
    assert core.found_anything(out["messages"]) is not True


@pytest.mark.parametrize("name,target,receipt,paired,expected", [
    ("call_api_tool", "account_cancel_booking", {"done": True}, True, True),
    ("call_api_tool", "account_cancel_booking", {"done": None, "outcome": "unknown"}, True, True),
    ("call_api_tool", "account_cancel_booking", {"done": False}, True, False),
    ("call_api_tool", "account_cancel_booking", {"done": True}, False, False),
    ("call_api_tool", "maps_scenes_scenes", {"done": True}, True, False),
    ("call_api_tool", "unregistered_write", {"done": True}, True, False),
    ("search_api_tools", "account_cancel_booking", {"done": True}, True, False),
    ("add_to_ai_calendar", None, {"done": True}, True, True),
    ("update_ai_calendar", None, {"done": None, "outcome": "unknown"}, True, True),
    ("remove_from_ai_calendar", None, {"done": True}, False, False),
])
def test_action_receipts_are_matched_and_never_read_evidence(name, target, receipt, paired, expected):
    import json
    messages = [HumanMessage("Act"),
                AIMessage(content="", tool_calls=[{"name": name, "args": {"name": target} if target else {}, "id": "w1"}]),
                ToolMessage(content=json.dumps(receipt), name=name, tool_call_id="w1" if paired else "other"),
                ToolMessage(content=core.TOOL_FAILURE_ANSWER, name="ask_chats", tool_call_id="h1"),
                AIMessage(content="Action result.")]
    assert core.action_receipt(messages) is expected
    assert core.final_answer(messages, {}) == ("Action result." if expected else core.TOOL_FAILURE_ANSWER)
    assert core.read_evidence(messages) is False
    assert core.successful_read(messages) is False


@pytest.mark.parametrize("helper", [None, "ask_docs", "ask_chats"])
@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_all_graph_contexts_confirm_over_real_http_without_tickets(mcp_http_protocol, monkeypatch, helper, decision):
    from catix.innohassle import client, token
    from tests.test_account import DAY, SITE

    writes = []
    monkeypatch.setattr(token, "claims", lambda value: {"uid": "u1"} if value == "user-token" else None)
    monkeypatch.setattr(client, "music_room_bookings", lambda day: [])
    monkeypatch.setattr(client, "music_room_hours_left", lambda token, day: (4, 10))
    monkeypatch.setattr(client, "book_music_room", lambda *a: writes.append(a) or {"id": 77})
    args = {"name": "music_book_music_room", "arguments": {
        "day": DAY.isoformat(), "time_from": "18:00", "time_to": "19:00"}}
    agent, config, _ = _graph_action(args, context=SITE, helper=helper)
    paused = agent.get_state(config).interrupts[0]
    assert writes == []
    assert "18:00–19:00" in paused.value["action_requests"][0]["description"]
    out = agent.invoke(Command(resume={paused.id: {"decisions": [{"type": decision}]}}), config, context=SITE)
    assert [(token, start.hour, end.hour) for token, start, end in writes] == (
        [("user-token", 18, 19)] if decision == "approve" else [])
    assert "user-token" not in str(out)
