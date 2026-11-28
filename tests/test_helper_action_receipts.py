"""Mutation results survive a failed answer prose without becoming read evidence."""

import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command
from pydantic import SecretStr

from catix.agent import api_tools, core
from catix.agent.tools import AgentContext
from tests.mcp_native_helpers import input_schema
from tests.test_roles import ScriptedModel


ACTION = {"name": "account_cancel_booking", "arguments": {
    "service": "room", "booking_id": "synthetic-booking-5"}}
CONFIRMED = {"done": True, "booking_id": "m0"}
UNKNOWN = {"done": None, "outcome": "unknown", "error": "Do not retry automatically."}
BAD_MARKUP = '<tool_call><function=not_a_tool></function></tool_call>'


def call(name, args, ident):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": ident}])


@pytest.fixture
def mutation(monkeypatch):
    sent = []
    payload: dict[str, dict | list[dict]] = {"result": CONFIRMED}

    def request(method, args, token=None, **kwargs):
        if method == "search_tools":
            assert token is None and kwargs == {}
            return {"tools": [{"name": args["query"], "inputSchema": input_schema(args["query"])}]}
        assert token == "synthetic-user"
        assert method == "call_tool"
        if args["name"] == "account_get_booking":
            assert args["arguments"]["service"] == "room" and kwargs == {}
            return {"booking": {**args["arguments"], "title": "Study group", "room": "314",
                                "date": "2099-01-02", "time": "10:00-11:00"}}
        assert args["name"] == "account_cancel_booking"
        sent.append(args)
        result = payload["result"]
        return result.pop(0) if isinstance(result, list) else result

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    return sent, payload


def invoke_action(script, question="Отмени бронь.", model_class=ScriptedModel):
    agent = core.build_agent(model_class(responses=script), guardrail=False)
    config = {"configurable": {"thread_id": "receipt"}}
    context = AgentContext(innohassle_token=SecretStr("synthetic-user"))
    out = agent.invoke({"messages": [HumanMessage(question)]}, config, context=context)
    return agent, config, context, out



@pytest.mark.parametrize("bad_prose", [BAD_MARKUP, ".", core.TOOL_FAILURE_ANSWER])
@pytest.mark.parametrize("receipt", [CONFIRMED, UNKNOWN])
def test_failed_prose_preserves_executed_action(mutation, receipt, bad_prose):
    sent, payload = mutation
    payload["result"] = receipt
    agent, config, context, paused = invoke_action([
        call("call_api_tool", ACTION, "w1"),
        *[AIMessage(content=bad_prose) for _ in range(3)],
    ])
    assert sent == [] and not core.action_receipt(paused["messages"])
    interrupt = agent.get_state(config).interrupts[0]
    out = agent.invoke(Command(resume={interrupt.id: {"decisions": [{"type": "approve"}]}}),
                       config, context=context)
    assert sent == [ACTION]
    assert not agent.get_state(config).interrupts
    assert core.action_receipt(out["messages"]) is True
    answer = core.final_answer(out["messages"], {}).answer
    assert answer != core.TOOL_FAILURE_ANSWER
    assert "Не повторяйте" in answer
    assert ("могло выполниться" if receipt == UNKNOWN else "подтверждено сервисом") in answer
    assert "[m0]" not in answer and "[1]" not in answer


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("question", ["Отмени обе брони.", "Cancel both bookings."])
def test_mixed_receipts_preserve_unknown_and_second_consent(mutation, reverse, question):
    sent, payload = mutation
    payload["result"] = [UNKNOWN, CONFIRMED] if reverse else [CONFIRMED, UNKNOWN]
    second = {**ACTION, "arguments": {**ACTION["arguments"], "booking_id": "synthetic-booking-6"}}
    agent, config, context, _ = invoke_action([
        call("call_api_tool", ACTION, "w1"), call("call_api_tool", second, "w2"),
        AIMessage(content="."), AIMessage(content="Оба действия выполнены. Повторите их."),
    ], question=question)
    assert sent == []
    first = agent.get_state(config).interrupts[0]
    agent.invoke(Command(resume={first.id: {"decisions": [{"type": "approve"}]}}), config, context=context)
    assert sent == [ACTION]
    pending = agent.get_state(config).interrupts
    assert len(pending) == 1 and pending[0].id != first.id
    out = agent.invoke(Command(resume={pending[0].id: {"decisions": [{"type": "approve"}]}}), config, context=context)
    assert sent == [ACTION, second]
    assert not agent.get_state(config).interrupts
    assert {r["outcome"] for r in core._action_receipts(out["messages"])} == {"confirmed", "unknown"}
    answer = core.final_answer(out["messages"], {}).answer
    if question.startswith("Cancel"):
        assert "confirmed some actions" in answer and "unknown outcomes" in answer and "Do not repeat" in answer
    else:
        assert "части действий подтверждено" in answer and "других действий неизвестен" in answer and "Не повторяйте" in answer


@pytest.mark.parametrize("reject", [False, True])
def test_no_receipt_without_approval_or_after_rejection(mutation, reject):
    sent, _ = mutation
    agent, config, context, out = invoke_action([
        call("call_api_tool", ACTION, "w1"),
        *[AIMessage(content=core.TOOL_FAILURE_ANSWER) for _ in range(4)],
    ])
    assert sent == [] and not core.action_receipt(out["messages"])
    interrupt = agent.get_state(config).interrupts[0]
    if reject:
        out = agent.invoke(Command(resume={interrupt.id: {"decisions": [{"type": "reject"}]}}), config, context=context)
        assert not agent.get_state(config).interrupts
        assert not core.action_receipt(out["messages"])
    assert sent == []


@pytest.mark.parametrize("target,ident,status,receipt", [
    ("account_cancel_booking", "unmatched", "success", CONFIRMED),
    ("account_cancel_booking", "w1", "error", CONFIRMED),
    ("maps_scenes_scenes", "w1", "success", CONFIRMED),
    ("maps_scenes_scenes", "w1", "success", UNKNOWN),
    ("unregistered_mutation", "w1", "success", CONFIRMED),
    ("account_cancel_booking", "w1", "success", {"done": False}),
    ("account_cancel_booking", "w1", "success", {"done": True, "error": "unavailable"}),
])
def test_only_matched_mutation_results_are_receipts(target, ident, status, receipt):
    messages = [HumanMessage("Act"), call("call_api_tool", {**ACTION, "name": target}, "w1"),
                ToolMessage(content=json.dumps(receipt), name="call_api_tool", tool_call_id=ident, status=status),
                AIMessage(content="Completed.")]
    assert not core.action_receipt(messages)
    assert core.final_answer(messages, {}).answer == "Completed."


def test_receipts_of_an_earlier_question_do_not_count():
    done = [HumanMessage("Act"), call("call_api_tool", ACTION, "w1"),
            ToolMessage(content=json.dumps(CONFIRMED), name="call_api_tool", tool_call_id="w1"), AIMessage(content=".")]
    assert core.action_receipt(done)  # Positive control: valid in its own turn.
    assert "подтверждено" in core.final_answer(done, {}).answer or "confirmed" in core.final_answer(done, {}).answer
    later = [*done, HumanMessage("Any announcements?"), AIMessage(content="No.")]
    assert not core.action_receipt(later)
    assert core.final_answer(later, {}).answer == "No."
    mismatched = [done[0], call("call_api_tool", ACTION, "other"), *done[2:]]
    assert not core.action_receipt(mismatched)
