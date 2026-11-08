"""Bounded real-model routing probes with synthetic sources and no writes."""

from dataclasses import replace
from datetime import datetime

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from catix.agent import calendar_tools, core, roles
from catix.innohassle import mcp_client
from catix.settings import settings
from tests.test_my_schedule import CLASS, LOCAL, CONTEXT, DAY


@pytest.mark.model
@pytest.mark.parametrize("local_only", [False, True])
def test_real_model_uses_one_agenda_read_and_local_only_when_explicit(monkeypatch, local_only):
    requests = []
    def request(method, payload, token=None, **credentials):
        requests.append(payload)
        assert method == "call_tool" and payload["name"] == "account_get_my_schedule"
        assert token == "synthetic-ih" and not credentials
        assert payload["arguments"] == {"date_from": DAY, "date_to": DAY}
        return {"range": [DAY, DAY], "schedule": [{**CLASS, "title": "Дискретная математика"}], "bookings": []}
    monkeypatch.setattr(mcp_client, "request_sync", request)
    monkeypatch.setattr(calendar_tools, "events_between", lambda *a: [{**LOCAL, "title": "Созвон с командой"}])
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    monkeypatch.setattr(roles, "MAIN_TOOLS", frozenset({"get_my_schedule", "get_my_ai_calendar", "search_api_tools", "call_api_tool"}))
    monkeypatch.setattr(settings, "agent_max_model_calls", 4)
    model = ChatOpenAI(base_url=str(settings.llm_route), api_key="not-needed", model=settings.llm_model,
                       max_tokens=1000, temperature=0, timeout=60, max_retries=0,
                       extra_body={"chat_template_kwargs": {"enable_thinking": False}})
    graph = core.build_agent(model, guardrail=False)
    question = "Что у меня завтра только в AI Calendar?" if local_only else "Какое у меня завтра расписание?"
    context = replace(CONTEXT, asked_at=datetime.fromisoformat("2026-11-08T06:00:00+03:00"))
    result = graph.invoke({"messages": [HumanMessage(question)]},
                          {"configurable": {"thread_id": f"combined-agenda-model-{local_only}"}}, context=context)
    calls = [call for m in result["messages"] if isinstance(m, AIMessage) for call in m.tool_calls]
    answer = core.final_answer(result["messages"], {})
    print({"local_only": local_only, "calls": calls, "answer": answer})
    assert [call["name"] for call in calls] == ["get_my_ai_calendar" if local_only else "get_my_schedule"]
    assert "Созвон" in answer
    assert ("Дискретная математика" in answer) is not local_only
    assert len(requests) == (0 if local_only else 1)
