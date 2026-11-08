"""Common MCP calls wait for name-selected consent in every exposing graph."""

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.types import Command
from pydantic import SecretStr

from catix.agent import api_tools, core
from catix.agent.tools import AgentContext
from tests.mcp_native_helpers import input_schema
from tests.test_roles import ScriptedModel


def _graph_action(args, context=None, tool="call_api_tool", helper=None, reads=None):
    script: list[BaseMessage] = []
    if helper:
        script.append(AIMessage(content="", tool_calls=[{
            "name": helper, "args": {"question": "Выполни действие во внешнем сервисе"}, "id": "s1",
        }]))
    if reads:
        script.append(AIMessage(content="", tool_calls=reads))
    script.extend([AIMessage(content="", tool_calls=[{"name": tool, "args": args, "id": "h1"}]),
                   *[AIMessage(content="Обработано.") for _ in range(4)]])
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
    from catix.agent import calendar_tools
    from tests.test_sport_calendar_guard import BASKETBALL, DAY, PERIOD

    monkeypatch.setattr(calendar_tools, "events_between", lambda *a: [])
    sent = []
    args = {"name": "sport_sport_checkin", "arguments": {"training_id": 11}}

    def request(method, payload, token=None, **credentials):
        if method == "search_tools":
            assert token is None and credentials == {}
            return {"tools": [{"name": payload["query"], "inputSchema": input_schema(payload["query"])}]}
        assert token == "user-token"
        assert method == "call_tool"
        if payload["name"] == "account_get_my_schedule":
            assert credentials == {} and payload["arguments"] == PERIOD
            return {"range": [DAY, DAY], "schedule": [], "bookings": []}
        assert credentials == {"sport_token": "sport-token"}
        if payload["name"] == "sport_get_sport_trainings":
            assert payload["arguments"] == PERIOD
            return {"range": [DAY, DAY], "trainings": [{**BASKETBALL, "training_id": 11}]}
        sent.append(payload)
        return {"done": True}

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    context = AgentContext(innohassle_id="u1", innohassle_token=SecretStr("user-token"), sport_token=SecretStr("sport-token"))
    model_args = {**args, "runtime": spoof} if spoof is not False else args
    reads = [{"name": "call_api_tool", "args": {"name": name, "arguments": PERIOD}, "id": name}
             for name in ("sport_get_sport_trainings", "account_get_my_schedule")]
    agent, config, _ = _graph_action(model_args, helper=helper, context=context, reads=reads)
    paused = agent.get_state(config).interrupts
    assert len(paused) == 1 and sent == []
    description = paused[0].value["action_requests"][0]["description"]
    assert description.startswith("Записать вас на тренировку #11.")
    assert "Basketball" in description and "17:00" in description
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
@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_server_business_validation_remains_at_execution(mcp_http_protocol, monkeypatch, helper, decision):
    from catix.innohassle import client, token

    sent = []
    original = api_tools.mcp_client.request
    monkeypatch.setattr(token, "claims", lambda value: {"uid": "u1"} if value == "user-token" else None)
    monkeypatch.setattr(client, "can_book_room", lambda *a: pytest.fail("Invalid span must fail before upstream I/O"))
    monkeypatch.setattr(client, "book_room", lambda *a: pytest.fail("Invalid span must never write"))

    async def request(method, payload, access=None, **kwargs):
        sent.append(method)
        return await original(method, payload, access, **kwargs)

    monkeypatch.setattr(api_tools.mcp_client, "request", request)
    # Individual field types/formats are valid; the server owns this cross-field rule.
    args = {"name": "rooms_book_room", "arguments": {
        "day": "2099-01-01", "room_id": "r1", "title": "Meeting", "time_from": "11:00", "time_to": "10:00"}}
    agent, config, _ = _graph_action(args, helper=helper)
    paused = agent.get_state(config).interrupts[0]
    assert "11:00–10:00" in paused.value["action_requests"][0]["description"]
    assert sent == ["search_tools"]
    context = AgentContext(innohassle_token=SecretStr("user-token"))
    out = agent.invoke(Command(resume={paused.id: {"decisions": [{"type": decision}]}}), config, context=context)
    assert not agent.get_state(config).interrupts
    assert sent == ["search_tools"] + (["call_tool"] if decision == "approve" else [])
    if decision == "approve":
        assert "time_to must be after time_from" in str(out)
    assert not core.action_receipt(out["messages"])


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
            return {"tools": [{"name": payload["query"], "inputSchema": input_schema(payload["query"])}]}
        assert method == "call_tool"
        if payload["name"] == "account_get_booking":
            assert token == "user-token" and kwargs == {}
            assert payload["arguments"] == args["arguments"]
            return {"booking": {**args["arguments"], "title": "Study group", "room": "314",
                                "date": "2099-01-02", "time": "10:00-11:00"}}
        sent.append(payload)
        return receipt

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    script: list[BaseMessage] = [AIMessage(content="", tool_calls=[{"name": "call_api_tool", "args": args, "id": "w1"}]),
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
    from catix.agent import calendar_tools
    from catix.innohassle import client, mcp_account, token
    from tests.test_account import DAY, SITE

    def calendar(user_token, start, end):
        assert user_token == "user-token" and start == end == DAY
        return [], {}

    def bookings(user_token, start, end):
        assert user_token == "user-token" and start == end == DAY
        return [], []

    monkeypatch.setattr(mcp_account, "_calendar", calendar)
    monkeypatch.setattr(mcp_account, "_bookings", bookings)
    monkeypatch.setattr(calendar_tools, "events_between", lambda key, start, end: [])
    writes = []
    monkeypatch.setattr(token, "claims", lambda value: {"uid": "u1"} if value == "user-token" else None)
    monkeypatch.setattr(client, "my_music_room_profile", lambda token: {"status": "free"})
    monkeypatch.setattr(client, "music_room_bookings", lambda day, **kwargs: [])
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
