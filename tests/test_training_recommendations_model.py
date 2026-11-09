"""Small real-model checks for the reported date/recommendation failure; no live account I/O."""

from copy import deepcopy

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI

from catix.agent import calendar_tools, core, roles
from catix.innohassle import mcp_client
from catix.settings import settings
from tests.test_training_recommendations import CONTEXT, CLASSES, TRAININGS


@pytest.mark.model
@pytest.mark.parametrize("case", ["spaced_day_after_tomorrow", "conflicting_trainings", "partial_calendar", "sport_timeout"])
def test_real_model_recommends_only_checked_trainings_for_the_exact_day(monkeypatch, case):
    day = "2026-11-10" if case == "spaced_day_after_tomorrow" else "2026-11-09"
    question = ("предложи мне тренировки на после завтра" if case == "spaced_day_after_tomorrow"
                else "на что записатьс по спорту на завтра?" if case == "sport_timeout"
                else "Предложи тренировки на 9 ноября.")
    classes, trainings = deepcopy(CLASSES), deepcopy(TRAININGS)
    if case == "spaced_day_after_tomorrow":
        classes = [{"title": "Introduction to Programming (lab)", "starts_at": day + "T12:40:00+03:00", "ends_at": day + "T14:10:00+03:00"}]
        trainings = [
            {"training_id": 49183, "name": "Frisbee", "starts_at": day + "T12:30:00+03:00", "ends_at": day + "T14:30:00+03:00", "checked_in": False, "can_check_in": True},
            {"training_id": 47535, "name": "CrossFit", "starts_at": day + "T15:00:00+03:00", "ends_at": day + "T16:30:00+03:00", "checked_in": False, "can_check_in": True},
            {"training_id": 48015, "name": "Street Dance", "starts_at": day + "T17:00:00+03:00", "ends_at": day + "T19:30:00+03:00", "checked_in": False, "can_check_in": True},
        ]
    for training in trainings:
        training.setdefault("place", "Sport Complex")
    requests = []
    def request(method, payload, token=None, **credentials):
        assert method == "call_tool", "The host recommendation read needs no model catalogue lookup"
        requests.append(payload)
        assert token == "synthetic-ih" and payload["arguments"] == {"date_from": day, "date_to": day}
        if payload["name"] == "sport_get_sport_trainings":
            assert credentials == {"sport_token": "synthetic-sport"}
            if case == "sport_timeout":
                return {"code": "upstream_timeout", "error": "The upstream API request timed out; no reliable result was obtained."}
            return {"range": [day, day], "trainings": trainings}
        assert payload["name"] == "account_get_my_schedule", "Recommendation must never write"
        return {"range": [day, day], "schedule": classes, "bookings": [],
                **({"not_read": ["class: some selected calendars unavailable"]} if case == "partial_calendar" else {})}
    monkeypatch.setattr(mcp_client, "request_sync", request)
    monkeypatch.setattr(calendar_tools, "events_between", lambda *a: [])
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    monkeypatch.setattr(roles, "MAIN_TOOLS", frozenset({"get_my_available_trainings", "get_my_schedule", "get_my_ai_calendar", "search_api_tools", "call_api_tool"}))
    monkeypatch.setattr(settings, "agent_max_model_calls", 4)
    model = ChatOpenAI(base_url=str(settings.llm_route), api_key="not-needed", model=settings.llm_model,
                       max_tokens=1200, temperature=0, timeout=60, max_retries=0,
                       extra_body={"chat_template_kwargs": {"enable_thinking": False}})
    graph = core.build_agent(model, guardrail=False)
    config = {"configurable": {"thread_id": f"recommendation-model-{case}"}}
    result = graph.invoke({"messages": [HumanMessage(question)]}, config, context=CONTEXT)
    calls = [call for message in result["messages"] if isinstance(message, AIMessage) for call in message.tool_calls]
    answer = core.final_answer(result["messages"], {}).answer
    print({"case": case, "calls": calls, "answer": answer})
    assert len(calls) == 1 and calls[0]["name"] == "get_my_available_trainings"
    assert calls[0]["args"].get("day") == day and calls[0]["args"].get("sport") is None
    assert len(requests) == (1 if case == "sport_timeout" else 2) and not graph.get_state(config).interrupts
    if case == "spaced_day_after_tomorrow":
        assert "10 ноября" in answer and "CrossFit" in answer and "15:00" in answer
    elif case == "conflicting_trainings":
        assert "Basketball" in answer and "17:00" in answer
    elif case == "partial_calendar":
        import json
        payload = next(json.loads(m.content) for m in result["messages"] if isinstance(m, ToolMessage) and isinstance(m.content, str))
        assert payload["available"] == [] and payload["complete"] is False
        assert any(word in answer.lower() for word in ("не удалось", "недоступ", "непол", "не могу", "не могу гарантировать"))
        assert "подходящих тренировок нет" not in answer.lower(), "Unknown availability is not absence"
        assert "могу попробовать запис" not in answer.lower(), "Do not offer signup for unverified slots"
    else:
        assert answer.strip()
        assert any(word in answer.lower() for word in ("не удалось", "недоступ", "не ответил", "таймаут", "не могу"))
        assert all(training["name"] not in answer for training in trainings)
