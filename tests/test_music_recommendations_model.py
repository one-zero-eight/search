"""Small real-model probes; all account reads are synthetic and writes forbidden."""
import json
import re

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI

from catix.agent import core, roles
from catix.settings import settings
from tests.test_music_recommendations import CONTEXT, DAY, services  # noqa: F401 -- shared fixture


@pytest.mark.model
@pytest.mark.parametrize("case", ["hour", "no_duration", "partial"])
def test_model_uses_personal_music_windows_without_booking(monkeypatch, services, case):
    question = "Когда завтра могу поиграть час в музкомнате?"
    if case == "no_duration":
        question = "Подбери мне свободные окна в музкомнате на завтра с учётом моего расписания."
        services["music"]["duration_minutes"] = None
        services["music"]["windows"][0]["latest_start"] = "17:30"
    elif case == "partial":
        services["agenda"]["not_read"] = ["class: selected calendar unavailable"]
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    monkeypatch.setattr(roles, "MAIN_TOOLS", frozenset({"get_my_available_music_windows", "get_my_available_trainings",
                                                     "get_my_schedule", "get_my_ai_calendar", "search_api_tools", "call_api_tool"}))
    monkeypatch.setattr(settings, "agent_max_model_calls", 4)
    model = ChatOpenAI(base_url=str(settings.llm_route), api_key="not-needed", model=settings.llm_model,
                       max_tokens=1000, temperature=0, timeout=60, max_retries=0,
                       extra_body={"chat_template_kwargs": {"enable_thinking": False}})
    graph = core.build_agent(model, guardrail=False)
    config = {"configurable": {"thread_id": f"music-model-{case}"}}
    result = graph.invoke({"messages": [HumanMessage(question)]}, config, context=CONTEXT)
    calls = [call for message in result["messages"] if isinstance(message, AIMessage) for call in message.tool_calls]
    answer = core.final_answer(result["messages"], {})
    print({"case": case, "calls": calls, "answer": answer})
    assert len(calls) == 1 and calls[0]["name"] == "get_my_available_music_windows"
    assert calls[0]["args"] == {"day": DAY, **({"duration_minutes": 60} if case != "no_duration" else {})}
    assert len(services["requests"]) == 2 and not graph.get_state(config).interrupts
    if case == "partial":
        payload = next(json.loads(m.content) for m in result["messages"] if isinstance(m, ToolMessage) and isinstance(m.content, str))
        assert payload["available"] == [] and payload["complete"] is False
        assert any(word in answer.lower() for word in ("не удалось", "недоступ", "непол", "не могу", "не провер"))
        assert not any(phrase in answer.lower() for phrase in ("нет доступных окон", "свободных окон нет", "нет свободных окон"))
    else:
        assert "10:30" in answer and ("12:30" in answer or "11:30" in answer)
        # Reporting a rounded block as overlapping a class is valid; calling it
        # the actual class interval (the observed regression) is not.
        assert not re.search(r"12:30\s*(?:до|[–—-])\s*14:30\s*(?:у вас\s+|[:–—-]\s*)?заняти",
                             answer.lower().replace("**", ""))


@pytest.mark.model
@pytest.mark.parametrize("text", ["Когда завтра могу поиграть час в музкомнате?", "Подбери мне свободное время в музкомнате."])
def test_music_scheduling_reaches_agent_through_real_screen(text):
    from catix.agent.guardrail import _screen_chain
    result = _screen_chain().invoke({"text": text, "history": "[]"})
    print({"text": text, "category": result.category})
    assert result.category == "ok"
