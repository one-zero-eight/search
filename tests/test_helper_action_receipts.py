"""Mutation results survive helper prose failures without becoming read evidence."""

import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command
from pydantic import SecretStr

from catix.agent import api_tools, core
from catix.agent.tools import AgentContext
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

    def request(method, args, token, **kwargs):
        assert token == "synthetic-user"
        if method == "preview_tool":
            return {"name": args["name"], "arguments": args["arguments"], "description": "Cancel synthetic booking"}
        assert method == "call_tool"
        sent.append(args)
        result = payload["result"]
        return result.pop(0) if isinstance(result, list) else result

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    return sent, payload


def invoke_action(script, question="Отмени бронь.", model_class=ScriptedModel):
    agent = core.build_agent(model_class(responses=script), guardrail=False)
    config = {"configurable": {"thread_id": "helper-receipt"}}
    context = AgentContext(innohassle_token=SecretStr("synthetic-user"))
    out = agent.invoke({"messages": [HumanMessage(question)]}, config, context=context)
    return agent, config, context, out


@pytest.mark.parametrize("helper", ["account", "docs", "chats"])
@pytest.mark.parametrize("bad_prose", [BAD_MARKUP, "."])
@pytest.mark.parametrize("root_answer", [core.TOOL_FAILURE_ANSWER, "Действие не выполнено. Повторите запрос."])
@pytest.mark.parametrize("receipt", [CONFIRMED, UNKNOWN])
def test_helper_failed_prose_preserves_executed_action(mutation, receipt, helper, bad_prose, root_answer):
    sent, payload = mutation
    payload["result"] = receipt
    agent, config, context, paused = invoke_action([
        call(f"ask_{helper}", {"question": "Отмени бронь."}, "h1"),
        call("call_api_tool", ACTION, "w1"),
        AIMessage(content=bad_prose), *([AIMessage(content=bad_prose)] if bad_prose == BAD_MARKUP else []),
        AIMessage(content=root_answer),
    ])
    assert sent == [] and not core.action_receipt(paused["messages"])
    interrupt = agent.get_state(config).interrupts[0]
    out = agent.invoke(Command(resume={interrupt.id: {"decisions": [{"type": "approve"}]}}),
                       config, context=context)
    assert sent == [ACTION]
    assert not agent.get_state(config).interrupts
    report = next(m for m in out["messages"] if isinstance(m, ToolMessage))
    assert json.loads(report.artifact["results"][0]) == receipt
    assert core.action_receipt(out["messages"]) is True
    answer = core.final_answer(out["messages"], {})
    assert answer != core.TOOL_FAILURE_ANSWER
    assert "Не повторяйте" in answer
    assert ("могло выполниться" if receipt == UNKNOWN else "подтверждено сервисом") in answer
    assert "[m0]" not in report.content and "[1]" not in answer
    assert core.read_evidence(out["messages"]) is False
    assert core.successful_read(out["messages"]) is False
    assert core.found_anything(out["messages"]) is not True
    assert report.artifact["found"] is not True and "read_found" not in report.artifact


class FailingReportModel(ScriptedModel):
    def _generate(self, *args, **kwargs):
        if self.responses[self.i].content == "raise-after-write":
            self.i += 1
            raise RuntimeError("Synthetic helper model failure after mutation")
        return super()._generate(*args, **kwargs)


@pytest.mark.parametrize("helper", ["account", "docs", "chats"])
@pytest.mark.parametrize("receipt", [CONFIRMED, UNKNOWN])
def test_helper_model_exception_retains_streamed_receipt(mutation, helper, receipt):
    sent, payload = mutation
    payload["result"] = receipt
    agent, config, context, _ = invoke_action([
        call(f"ask_{helper}", {"question": "Отмени бронь."}, "h1"),
        call("call_api_tool", ACTION, "w1"),
        AIMessage(content="raise-after-write"), AIMessage(content="Повторите запрос."),
    ], model_class=FailingReportModel)
    assert sent == []
    interrupt = agent.get_state(config).interrupts[0]
    out = agent.invoke(Command(resume={interrupt.id: {"decisions": [{"type": "approve"}]}}),
                       config, context=context)
    assert sent == [ACTION]
    assert core.action_receipt(out["messages"])
    report = next(m for m in out["messages"] if isinstance(m, ToolMessage))
    assert report.artifact["action_receipts"]
    answer = core.final_answer(out["messages"], {})
    assert "Не повторяйте" in answer
    assert ("могло выполниться" if receipt == UNKNOWN else "подтверждено сервисом") in answer


@pytest.mark.parametrize("helper", ["account", "docs", "chats"])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("question", ["Отмени обе брони.", "Cancel both bookings."])
def test_mixed_receipts_preserve_unknown_and_second_consent(mutation, helper, reverse, question):
    sent, payload = mutation
    payload["result"] = [UNKNOWN, CONFIRMED] if reverse else [CONFIRMED, UNKNOWN]
    second = {**ACTION, "arguments": {**ACTION["arguments"], "booking_id": "synthetic-booking-6"}}
    agent, config, context, _ = invoke_action([
        call(f"ask_{helper}", {"question": "Отмени обе брони."}, "h1"),
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
    report = next(m for m in out["messages"] if isinstance(m, ToolMessage))
    assert {r["outcome"] for r in report.artifact["action_receipts"]} == {"confirmed", "unknown"}
    answer = core.final_answer(out["messages"], {})
    if question.startswith("Cancel"):
        assert "confirmed some actions" in answer and "unknown outcomes" in answer and "Do not repeat" in answer
    else:
        assert "части действий подтверждено" in answer and "других действий неизвестен" in answer and "Не повторяйте" in answer
    assert report.content == answer
    assert core.found_anything(out["messages"]) is not True


@pytest.mark.parametrize("helper", ["account", "docs", "chats"])
@pytest.mark.parametrize("reject", [False, True])
def test_no_receipt_without_approval_or_after_rejection(mutation, helper, reject):
    sent, _ = mutation
    agent, config, context, out = invoke_action([
        call(f"ask_{helper}", {"question": "Отмени бронь."}, "h1"),
        call("call_api_tool", ACTION, "w1"),
        *[AIMessage(content=core.TOOL_FAILURE_ANSWER) for _ in range(4)],
    ])
    assert sent == [] and not core.action_receipt(out["messages"])
    interrupt = agent.get_state(config).interrupts[0]
    if reject:
        out = agent.invoke(Command(resume={interrupt.id: {"decisions": [{"type": "reject"}]}}), config, context=context)
        assert not agent.get_state(config).interrupts
        assert not core.action_receipt(out["messages"])
        assert all(not (m.artifact or {}).get("action_receipts") for m in out["messages"] if isinstance(m, ToolMessage))
    assert sent == []


def helper_result(monkeypatch, messages, *, error=None, role="account"):
    """Exercise the real helper boundary with precisely shaped stream messages."""
    from types import SimpleNamespace
    from langchain_core.tools import StructuredTool

    def stream(*args, **kwargs):
        yield {"messages": messages}
        if error is not None:
            raise error

    monkeypatch.setattr(core, "create_agent", lambda *a, **kw: SimpleNamespace(stream=stream))
    helper = core._helper_tool(core.roles.ROLES[role], ScriptedModel(responses=[]))
    assert isinstance(helper, StructuredTool) and helper.func is not None
    runtime = SimpleNamespace(state={"messages": [HumanMessage("Cancel booking.")]}, config={}, context=AgentContext(),
                              tool_call_id="h1", stream_writer=lambda *a: None)
    return helper.func("Отмени бронь.", runtime).update["messages"][0]


@pytest.mark.parametrize("role", ["account", "docs", "chats"])
@pytest.mark.parametrize("target,ident,status,receipt", [
    ("account_cancel_booking", "unmatched", "success", CONFIRMED),
    ("account_cancel_booking", "w1", "error", CONFIRMED),
    ("maps_scenes_scenes", "w1", "success", CONFIRMED),
    ("maps_scenes_scenes", "w1", "success", UNKNOWN),
    ("unregistered_mutation", "w1", "success", CONFIRMED),
    ("account_cancel_booking", "w1", "success", {"done": False}),
    ("account_cancel_booking", "w1", "success", {"done": True, "error": "unavailable"}),
])
def test_helper_only_propagates_matched_mutation_results(monkeypatch, role, target, ident, status, receipt):
    messages = [HumanMessage("Act"), call("call_api_tool", {**ACTION, "name": target}, "w1"),
                ToolMessage(content=json.dumps(receipt), name="call_api_tool", tool_call_id=ident, status=status),
                AIMessage(content=core.TOOL_FAILURE_ANSWER)]
    report = helper_result(monkeypatch, messages, role=role)
    assert "action_receipts" not in report.artifact
    assert report.content == core.TOOL_FAILURE_ANSWER
    root = [HumanMessage("Act"), call(f"ask_{role}", {"question": "Act"}, "h1"), report,
            AIMessage(content="Completed.")]
    assert not core.action_receipt(root)
    assert core.final_answer(root, {}) == core.TOOL_FAILURE_ANSWER


def test_old_or_unmatched_helper_artifacts_do_not_resurrect_receipts(monkeypatch):
    messages = [HumanMessage("Act"), call("call_api_tool", ACTION, "w1"),
                ToolMessage(content=json.dumps(CONFIRMED), name="call_api_tool", tool_call_id="w1"), AIMessage(content=".")]
    report = helper_result(monkeypatch, messages)
    root = [HumanMessage("Act"), call("ask_account", {"question": "Act"}, "h1"), report, AIMessage(content=".")]
    assert core.action_receipt(root)  # Positive control: this artifact is valid in its own turn.
    assert "confirmed" in core.final_answer(root, {})
    mismatched = [root[0], call("ask_account", {"question": "Act"}, "other"), report, root[-1]]
    assert not core.action_receipt(mismatched)
    wrong_name = [root[0], call("ask_docs", {"question": "Act"}, "h1"), report, root[-1]]
    assert not core.action_receipt(wrong_name)
    root += [HumanMessage("Any announcements?"), call("ask_account", {"question": "Announcements?"}, "h2"),
             ToolMessage(content=core.TOOL_FAILURE_ANSWER, name="ask_account", tool_call_id="h2"), AIMessage(content="All done.")]
    assert not core.action_receipt(root)
    assert core.final_answer(root, {}) == core.TOOL_FAILURE_ANSWER
    report = helper_result(monkeypatch, [*messages, HumanMessage("Another question"), AIMessage(content=core.TOOL_FAILURE_ANSWER)])
    assert "action_receipts" not in report.artifact


@pytest.mark.parametrize("bubble", [False, True])
def test_helper_preserves_graph_control_flow_after_a_receipt(monkeypatch, bubble):
    from langgraph.errors import GraphBubbleUp, GraphInterrupt

    error = GraphBubbleUp("control-flow") if bubble else GraphInterrupt(())
    messages = [HumanMessage("Act"), call("call_api_tool", ACTION, "w1"),
                ToolMessage(content=json.dumps(CONFIRMED), name="call_api_tool", tool_call_id="w1")]
    with pytest.raises(type(error)) as caught:
        helper_result(monkeypatch, messages, error=error)
    assert caught.value is error


def test_helper_exception_without_receipt_is_not_swallowed(monkeypatch):
    error = RuntimeError("Synthetic read failure")
    messages = [HumanMessage("Read"), call("call_api_tool", {"name": "maps_scenes_scenes", "arguments": {}}, "r1"),
                ToolMessage(content=json.dumps(CONFIRMED), name="call_api_tool", tool_call_id="r1")]
    with pytest.raises(RuntimeError) as caught:
        helper_result(monkeypatch, messages, error=error)
    assert caught.value is error


@pytest.mark.parametrize("receipt", [CONFIRMED, UNKNOWN])
def test_exhausted_helper_budget_returns_receipt_not_limit_text(monkeypatch, receipt):
    messages = [HumanMessage("Act"), call("call_api_tool", ACTION, "w1"),
                ToolMessage(content=json.dumps(receipt), name="call_api_tool", tool_call_id="w1"),
                AIMessage(content="Model call limits exceeded: run limit (8/8)")]
    report = helper_result(monkeypatch, messages)
    assert "Do not repeat" in report.content
    root = [HumanMessage("Cancel booking."), call("ask_account", {"question": "Act"}, "h1"), report,
            AIMessage(content="The action failed. Retry.")]
    assert core.final_answer(root, {}) == report.content
