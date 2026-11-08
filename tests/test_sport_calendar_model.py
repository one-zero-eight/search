"""Two bounded real-model probes; all service/calendar data is synthetic, stop at HITL."""

from copy import deepcopy
from dataclasses import replace
from datetime import datetime

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from catix.agent import api_tools, calendar_tools, core, roles
from catix.settings import settings
from tests.mcp_native_helpers import registered_tools
from tests.test_sport_calendar_guard import BASKETBALL, CLASS, CONTEXT, DAY, FRISBEE, PERIOD, history, prepare


@pytest.mark.model
@pytest.mark.parametrize("seeded_bad_choice", [False, True])
def test_real_model_selects_nonoverlapping_training_without_any_write(monkeypatch, seeded_bad_choice):
    declarations = registered_tools()
    names = ["sport_get_sport_trainings", "account_get_my_schedule", "sport_sport_checkin", "sport_get_my_sport"]
    metadata = {"tools": [{"name": name, "description": declarations[name].description,
                            "inputSchema": declarations[name].parameters} for name in names]}
    calls = []

    def request(method, payload, token=None, **credentials):
        if method == "search_tools":
            assert token is None and not credentials
            return deepcopy(metadata)
        name = payload["name"]
        calls.append((name, deepcopy(payload["arguments"])))
        assert name != "sport_sport_checkin", "The real model probe must stop at approval"
        assert token == "synthetic-ih"
        if name == "sport_get_sport_trainings":
            assert payload["arguments"]["date_from"] == DAY and payload["arguments"]["date_to"] == DAY
            wanted = payload["arguments"].get("sport")
            found = [t for t in (FRISBEE, BASKETBALL) if not wanted or wanted.casefold() in t["name"].casefold()]
            return {"range": [DAY, DAY], "trainings": found,
                    **({"note": "No such sport on this day. Available sports: Frisbee, Basketball."} if not found else {})}
        if name == "account_get_my_schedule":
            assert payload["arguments"] == PERIOD
            return {"range": [DAY, DAY], "schedule": [CLASS], "bookings": []}
        if name == "sport_get_training":
            return {"training": next(t for t in (FRISBEE, BASKETBALL) if t["training_id"] == payload["arguments"]["training_id"])}
        if name == "sport_get_my_sport":
            return {"hours": {"done": 16, "required": 30, "left": 14}, "checked_in": []}
        pytest.fail(f"Unexpected synthetic service read: {name}")

    async def arequest(*args, **kwargs):
        return request(*args, **kwargs)

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    monkeypatch.setattr(api_tools.mcp_client, "request", arequest)
    monkeypatch.setattr(calendar_tools, "events_between", lambda *args: [])
    monkeypatch.setattr(core.store, "visible_chats", lambda *args: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    monkeypatch.setattr(roles, "MAIN_TOOLS", frozenset({"search_api_tools", "call_api_tool", "get_my_schedule", "get_my_ai_calendar", "get_my_available_trainings"}))
    monkeypatch.setattr(settings, "agent_max_model_calls", 8)
    model = ChatOpenAI(base_url=str(settings.llm_route), api_key="not-needed", model=settings.llm_model,
                       max_tokens=1200, temperature=0, timeout=60, max_retries=0,
                       extra_body={"chat_template_kwargs": {"enable_thinking": False}})
    agent = core.build_agent(model, guardrail=False)
    config = {"configurable": {"thread_id": f"synthetic-sport-guard-{seeded_bad_choice}"}}
    if seeded_bad_choice:
        inputs = history()
        refused = prepare(inputs)
        inputs["messages"].extend(refused["messages"])
    else:
        inputs = {"messages": [HumanMessage("Запиши меня на завтрашнюю тренировку, чтобы она не пересекалась с моими занятиями.")]}
    context = replace(CONTEXT, asked_at=datetime.fromisoformat("2026-11-08T06:11:00+03:00"))
    result = agent.invoke(inputs, config, context=context)
    pending = agent.get_state(config).interrupts
    answer = next((m.content for m in reversed(result["messages"]) if isinstance(m, AIMessage) and m.content), "")
    print({"seeded_bad_choice": seeded_bad_choice, "reads": calls, "answer": answer,
           "approval": pending[0].value if pending else None})
    if not pending:
        print([(m.type, m.content, getattr(m, "tool_calls", None)) for m in result["messages"]])
    assert pending, "Expected a concrete non-overlapping proposal for approval"
    requests = pending[0].value["action_requests"]
    assert len(requests) == 1
    assert requests[0]["args"] == {"name": "sport_sport_checkin", "arguments": {"training_id": 46975}}
    assert "17:00" in requests[0]["description"] and "18:30" in requests[0]["description"]
