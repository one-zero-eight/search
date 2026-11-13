"""Small real-model probes for explicit calendar duration proposals; no live writes."""
from datetime import datetime

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from catix import personal_calendar
from catix.agent import calendar_tools, core, roles
from catix.agent.tools import AgentContext
from catix.innohassle import mcp_client
from catix.settings import settings


@pytest.mark.model
@pytest.mark.parametrize("known_end", [False, True])
def test_model_leaves_unknown_end_to_explicit_host_proposal(monkeypatch, known_end):
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    monkeypatch.setattr(roles, "MAIN_TOOLS", frozenset({"get_my_schedule", "get_my_ai_calendar", "add_to_ai_calendar"}))
    monkeypatch.setattr(settings, "agent_max_model_calls", 4)
    monkeypatch.setattr(personal_calendar, "account_key", lambda *a: "ih:synthetic")
    monkeypatch.setattr(personal_calendar, "add_event", lambda *a, **kw: pytest.fail("Stop at approval; no write"))
    monkeypatch.setattr(calendar_tools, "events_between", lambda *a: [])
    def request(method, payload, token=None, **credentials):
        assert method == "call_tool" and payload["name"] == "account_get_my_schedule"
        assert token == "synthetic-token" and credentials == {}
        first, last = payload["arguments"]["date_from"], payload["arguments"]["date_to"]
        return {"range": [first, last], "schedule": [], "bookings": []}
    monkeypatch.setattr(mcp_client, "request_sync", request)
    question = ("Добавь в мой AI-календарь тест1 по дискре 9 ноября 2026 года с 09:00 до 10:30." if known_end
                else "Добавь в мой AI-календарь тест1 по дискре 9 ноября 2026 года в 09:00. Время окончания не указано.")
    model = ChatOpenAI(base_url=str(settings.llm_route), api_key=SecretStr("not-needed"), model=settings.llm_model,
                       max_completion_tokens=700, temperature=0, timeout=60, max_retries=0,
                       extra_body={"chat_template_kwargs": {"enable_thinking": False}})
    graph = core.build_agent(model, guardrail=False)
    config = {"configurable": {"thread_id": f"calendar-duration-{known_end}"}}
    context = AgentContext(innohassle_id="synthetic", innohassle_token=SecretStr("synthetic-token"),
                           asked_at=datetime.fromisoformat("2026-11-08T09:00:00+03:00"))
    out = graph.invoke({"messages": [HumanMessage(question)]}, config, context=context)
    calls = [call for m in out["messages"] if isinstance(m, AIMessage) for call in m.tool_calls if call["name"] == "add_to_ai_calendar"]
    pending = graph.get_state(config).interrupts
    print({"known_end": known_end, "calls": calls, "approval": pending[0].value if pending else None})
    assert len(calls) == 1 and len(pending) == 1
    assert calls[0]["args"].get("end_time") == ("10:30" if known_end else None)
    assert calls[0]["args"].get("proposed_duration_minutes") == (None if known_end else 90)
    description = pending[0].value["action_requests"][0]["description"]
    assert "09:00" in description and "10:30" in description
    assert ("предложенная" in description) is (not known_end)
