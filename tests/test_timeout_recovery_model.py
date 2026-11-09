"""Small live-model recovery probes after a real host read returns a synthetic timeout.

Seed the paired read to isolate recovery from tool selection. Raw API tools remain
available; no live account operations or mutations are permitted.
"""
import json
from datetime import date, datetime
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from catix.agent import core, meeting_tools, music_tools, roles, room_tools
from catix.agent.tools import AgentContext
from catix.innohassle import mcp_client
from catix.settings import settings


@pytest.mark.model
@pytest.mark.parametrize("case", ["rooms_upstream", "music_mcp", "meeting_upstream"])
def test_real_model_reports_failed_personal_check_without_raw_fallback(monkeypatch, case):
    if case == "rooms_upstream":
        tool = room_tools.get_my_available_rooms
        arguments = {"day": "2026-11-10", "time_from": "18:00", "time_to": "19:00"}
        question = "Подбери комнату на 10 ноября с 18:00 до 19:00, чтобы не было пересечений с моим расписанием."
        service, code = "rooms_get_free_rooms", "upstream_timeout"
    elif case == "music_mcp":
        tool = music_tools.get_my_available_music_windows
        arguments = {"day": "2026-11-10", "duration_minutes": 60}
        question = "Когда 10 ноября можно поиграть час в музкомнате без пересечений с моими занятиями?"
        service, code = "music_get_available_windows", "mcp_timeout"
    else:
        tool = meeting_tools.get_my_available_meeting_slots
        arguments = {"meeting_ref": "team-poll"}
        question = "Какие варианты встречи в When2Meet team-poll подходят мне по расписанию?"
        service, code = "when2meet_get_meeting", "upstream_timeout"
    calls = []

    def request(method, payload, *a, **kw):
        calls.append((method, payload))
        assert method == "call_tool" and payload["name"] == service
        return {"error": "private-diagnostic", "code": code}

    monkeypatch.setattr(mcp_client, "request_sync", request)
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    monkeypatch.setattr(roles, "MAIN_TOOLS", frozenset({tool.name, "get_my_schedule", "get_my_ai_calendar",
                                                       "search_api_tools", "call_api_tool"}))
    monkeypatch.setattr(settings, "agent_max_model_calls", 3)
    context = AgentContext(innohassle_id="synthetic-owner", innohassle_token=SecretStr("synthetic-ih"),
                           asked_at=datetime.fromisoformat("2026-11-09T12:00:00+03:00"))
    typed = {**arguments, **({"day": date.fromisoformat(arguments["day"])} if "day" in arguments else {})}
    output = tool.func(SimpleNamespace(context=context), **typed)
    content, artifact = output if isinstance(output, tuple) else (output, None)
    assert content["code"] == code
    model = ChatOpenAI(base_url=str(settings.llm_route), api_key="not-needed", model=settings.llm_model,
                       max_tokens=900, temperature=0, timeout=60, max_retries=0,
                       extra_body={"chat_template_kwargs": {"enable_thinking": False}})
    graph = core.build_agent(model, guardrail=False)
    config = {"configurable": {"thread_id": f"timeout-recovery-{case}"}}
    messages = [HumanMessage(question),
                AIMessage(content="", tool_calls=[{"name": tool.name, "args": arguments, "id": "checked"}]),
                ToolMessage(content=json.dumps(content), artifact=artifact, name=tool.name, tool_call_id="checked")]
    result = graph.invoke({"messages": messages}, config, context=context)
    tool_calls = [call for message in result["messages"] if isinstance(message, AIMessage) for call in message.tool_calls]
    answer = core.final_answer(result["messages"], {}).answer
    print({"case": case, "calls": tool_calls, "answer": answer})
    assert len(tool_calls) == 1 and tool_calls[0]["name"] == tool.name
    assert len(calls) == 1 and not graph.get_state(config).interrupts
    assert answer.strip() and "private-diagnostic" not in answer
    assert any(word in answer.lower() for word in ("не удалось", "не могу", "не ответил", "таймаут", "недоступ"))
    assert not any(phrase in answer.lower() for phrase in ("свободных комнат нет", "свободного времени нет",
                                                          "подходящих вариантов нет", "могу забронировать"))
