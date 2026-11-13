"""Regression for trace cb8a4983407edc4f8e5e79c754e2d44e using synthetic services."""
from copy import deepcopy
from datetime import date, datetime
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from catix.agent import calendar_tools
from catix.agent.music_tools import get_my_available_music_windows
from catix.agent.tools import AgentContext
from catix.innohassle import mcp_client

DAY = "2026-11-09"
CONTEXT = AgentContext(innohassle_id="synthetic", innohassle_token=SecretStr("synthetic-token"),
                       asked_at=datetime.fromisoformat("2026-11-08T09:12:11+03:00"))


def interval(start, end, title):
    return {"starts_at": DAY + "T" + start + ":00+03:00", "ends_at": DAY + "T" + end + ":00+03:00", "title": title}


@pytest.fixture
def trace_services(monkeypatch):
    windows = [{"start": start, "end": end, "latest_start": latest, "max_duration_minutes": duration}
               for start, end, latest, duration in [("07:00", "09:00", "08:30", 120), ("10:00", "10:30", "10:00", 30),
                                                    ("12:30", "13:00", "12:30", 30), ("20:30", "21:00", "20:30", 30)]]
    music = {"date": DAY, "timezone": "Europe/Moscow", "checked_at": "2026-11-08T09:12:13+03:00",
             "availability": "calculated", "duration_minutes": None, "windows": windows, "reason": None,
             "remaining_daily_minutes": 120, "remaining_weekly_minutes": 240,
             "rules": {"opens_at": "07:00", "closes_at": "22:30", "step_minutes": 30,
                       "latest_booking_start": "2026-11-15T09:12:13+03:00"}}
    agenda = {"range": [DAY, DAY], "bookings": [], "schedule": [
        interval("09:00", "10:30", "Logic and Discrete Math (lec)"), interval("10:40", "12:10", "Logic and Discrete Math (tut)"),
        interval("12:40", "14:10", "Logic and Discrete Math (lab)"), interval("14:20", "15:50", "English"),
    ]}
    local = [{"calendar_event_id": 274, "starts_at": DAY + "T09:00:00+03:00", "ends_at": None,
              "all_day": False, "title": "тест1 по дискре"}]
    calls = []
    def request(method, payload, token=None, **credentials):
        assert method == "call_tool" and token == "synthetic-token" and credentials == {}
        calls.append(deepcopy(payload))
        if payload["name"] == "music_get_available_windows":
            assert payload["arguments"] == {"day": DAY}
            return deepcopy(music)
        assert payload == {"name": "account_get_my_schedule", "arguments": {"date_from": DAY, "date_to": DAY}}
        return deepcopy(agenda)
    monkeypatch.setattr(mcp_client, "request_sync", request)
    monkeypatch.setattr(calendar_tools, "events_between", lambda *a: deepcopy(local))
    return calls


def test_exact_trace_keeps_early_window_and_names_unknown_event(trace_services):
    from langchain_core.tools import StructuredTool
    assert isinstance(get_my_available_music_windows, StructuredTool) and get_my_available_music_windows.func is not None
    result, artifact = get_my_available_music_windows.func(SimpleNamespace(context=CONTEXT), date.fromisoformat(DAY))
    assert [(w["start"], w["end"]) for w in result["available"]] == [("07:00", "09:00")]
    assert [(w["start"], w["end"]) for w in result["unverified"]] == [("20:30", "21:00")]
    assert {c["title"] for w in result["excluded"] for c in w.get("conflicts", [])} == {
        "Logic and Discrete Math (lec)", "Logic and Discrete Math (lab)",
    }
    assert result["unverified"][0]["unknown_duration_events"][0]["title"] == "тест1 по дискре"
    assert artifact["agenda"]["complete"] is True
    assert result["complete"] is False and len(trace_services) == 2


@pytest.mark.model
def test_real_model_explains_exact_trace_without_calling_it_an_empty_day(monkeypatch, trace_services):
    import re
    from langchain_core.messages import AIMessage, HumanMessage
    from langchain_openai import ChatOpenAI
    from catix.agent import core, roles
    from catix.settings import settings

    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    monkeypatch.setattr(roles, "MAIN_TOOLS", frozenset({"get_my_available_music_windows", "get_my_schedule", "get_my_ai_calendar", "search_api_tools", "call_api_tool"}))
    monkeypatch.setattr(settings, "agent_max_model_calls", 3)
    model = ChatOpenAI(base_url=str(settings.llm_route), api_key=SecretStr("not-needed"), model=settings.llm_model,
                       max_completion_tokens=900, temperature=0, timeout=60, max_retries=0,
                       extra_body={"chat_template_kwargs": {"enable_thinking": False}})
    graph = core.build_agent(model, guardrail=False)
    config = {"configurable": {"thread_id": "unknown-end-trace-model"}}
    out = graph.invoke({"messages": [HumanMessage("какая есть свободная музыкальная комната на завтра")]}, config, context=CONTEXT)
    calls = [call for m in out["messages"] if isinstance(m, AIMessage) for call in m.tool_calls]
    answer = core.final_answer(out["messages"], {}).answer
    print({"calls": calls, "answer": answer})
    assert len(calls) == 1 and calls[0]["name"] == "get_my_available_music_windows"
    assert calls[0]["args"] == {"day": DAY} and len(trace_services) == 2
    assert "07:00" in answer and "09:00" in answer and "тест1" in answer.lower()
    assert any(word in answer.lower() for word in ("оконч", "заканч", "длитель"))
    assert "?" in answer
    assert not re.search(r"10:30\s*[–—-]\s*12:40|14:10\s*[–—-]\s*20:30", answer), "Never invent free windows as the complement of conflict events"
    assert not any(phrase in answer.lower().replace("**", "") for phrase in ("свободных окон не найдено", "нет свободных окон", "не удалось прочитать"))
    assert not graph.get_state(config).interrupts
