"""leave_feedback waits for native approval, sends once with the asker's contact, and reports every outcome honestly."""

import json
from types import SimpleNamespace

import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command
from pydantic import SecretStr

from catix.agent import core, feedback_tools
from catix.agent.core import build_agent
from catix.agent.tools import AgentContext
from tests.test_calendar_approval import call
from tests.test_roles import ScriptedModel

SITE = AgentContext(innohassle_id="u1", innohassle_token=SecretStr("t"), innohassle_email="a.b@innopolis.university",
                    user_telegram_id=42)
ARGS = {"subject": "catix", "feedback": "Добавьте чат https://t.me/+AbCdEfGhIjKlMnOp"}
ASK = "Передай разработчикам: добавьте чат https://t.me/+AbCdEfGhIjKlMnOp"


@pytest.fixture
def sent(monkeypatch):
    posts = []

    def submit(data):
        posts.append(data)
        return httpx.Response(200)

    monkeypatch.setattr(feedback_tools, "_submit", submit)
    return posts


def run(context, thread):
    script = [call("leave_feedback", ARGS, "f1"), AIMessage(content="Готово.")]
    agent = build_agent(ScriptedModel(responses=script), guardrail=False)
    config = {"configurable": {"thread_id": thread}}
    out = agent.invoke({"messages": [HumanMessage(ASK)]}, config, context=context)
    return agent, config, out


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_feedback_waits_for_approval_and_sends_once(sent, decision):
    agent, config, _ = run(SITE, f"feedback-{decision}")
    interrupts = agent.get_state(config).interrupts
    assert len(interrupts) == 1 and sent == []
    assert interrupts[0].value["action_requests"][0]["args"] == ARGS, "the user sees exactly what is sent"
    out = agent.invoke(Command(resume={interrupts[0].id: {"decisions": [{"type": decision}]}}), config, context=SITE)
    if decision == "reject":
        assert sent == []
        return
    assert sent == [{"entry.1256372940": "catix", "entry.1356945135": ARGS["feedback"],
                     "entry.1696474646": "a.b@innopolis.university, Telegram id 42"}]
    report = next(m for m in out["messages"] if isinstance(m, ToolMessage) and m.name == "leave_feedback")
    assert json.loads(report.content)["done"] is True
    assert core.action_receipt(out["messages"])


def test_feedback_needs_a_site_user(sent):
    agent, config, out = run(AgentContext(), "feedback-anonymous")
    assert not agent.get_state(config).interrupts and sent == []
    report = next(m for m in out["messages"] if isinstance(m, ToolMessage) and m.name == "leave_feedback")
    assert json.loads(report.content)["done"] is False


@pytest.mark.parametrize("result, done, unknown", [
    (httpx.Response(200), True, False),
    (httpx.Response(400), False, False),
    (httpx.Response(500), None, True),
    (httpx.ReadTimeout("x"), None, True),
    (httpx.ConnectError("x"), False, False),
])
def test_feedback_outcomes(monkeypatch, result, done, unknown):
    def submit(data):
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(feedback_tools, "_submit", submit)
    got = feedback_tools.leave_feedback.func(subject="catix", feedback="x", runtime=SimpleNamespace(context=SITE))
    assert got["done"] is done
    assert (got.get("outcome") == "unknown") is unknown
