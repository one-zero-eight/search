"""Small real-model probes; all account reads are synthetic and writes forbidden."""
import asyncio
import json
import re
from copy import deepcopy

import pytest
from fastmcp import Client
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI

from catix.agent import api_tools, core, roles
from catix.innohassle import mcp_server
from catix.settings import settings
from tests.test_music_recommendations import CONTEXT, DAY, services  # noqa: F401 -- shared fixture


@pytest.mark.model
@pytest.mark.parametrize("case", ["hour", "no_duration", "partial"])
def test_model_uses_personal_music_windows_without_booking(monkeypatch, services, case):
    question = "Когда завтра могу поиграть час в музкомнате без пересечений с моим расписанием?"
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
    answer = core.final_answer(result["messages"], {}).answer
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


@pytest.mark.model
@pytest.mark.parametrize("case", ["occupied", "free", "conflict", "partial", "legacy_morning_only"])
def test_model_preserves_exact_music_interval_without_unrelated_class_claims(monkeypatch, services, case):
    from tests.test_music_recommendations import exact_music, interval
    exact_music(services, reason="room_occupied" if case == "occupied" else None)
    services["agenda"]["schedule"] = [interval("09:00", "12:10", title="Unrelated morning class")]
    services["local"] = []
    if case == "conflict":
        services["local"] = [interval("15:30", "16:30", title="Afternoon meeting")]
    elif case == "partial":
        services["agenda"]["not_read"] = ["Selected calendar unavailable"]
    elif case == "legacy_morning_only":
        services["music"].pop("requested_interval")
        services["music"]["windows"] = [{"start": "10:00", "end": "11:00", "latest_start": "10:00", "max_duration_minutes": 60}]
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    monkeypatch.setattr(settings, "agent_max_model_calls", 4)
    model = ChatOpenAI(base_url=str(settings.llm_route), api_key="not-needed", model=settings.llm_model,
                       max_tokens=2000, temperature=0, timeout=60, max_retries=0,
                       extra_body={"chat_template_kwargs": {"enable_thinking": False}})
    graph = core.build_agent(model, guardrail=False)
    config = {"configurable": {"thread_id": f"music-exact-model-{case}"}}
    # The recorded conversation previously discussed university rooms. Their
    # availability must not be reused as evidence for the separate music room.
    history = [HumanMessage("Find a university classroom tomorrow from 15:00 to 16:00."),
        AIMessage("", tool_calls=[{"id": "prior-rooms", "name": "call_api_tool", "args": {
            "name": "rooms_get_free_rooms", "arguments": {"day": DAY, "time_from": "15:00", "time_to": "16:00"}}}]),
        ToolMessage(json.dumps({"date": DAY, "range": "15:00-16:00", "timezone": "Europe/Moscow",
            "free": [{"room_id": "321", "title": "University classroom 321"}], "booked": [], "unavailable": []}),
            name="call_api_tool", tool_call_id="prior-rooms"), AIMessage("University classroom 321 is available.")]
    result = graph.invoke({"messages": [*history, HumanMessage(
        "Find a music room available tomorrow from 15:00 to 16:00 that fits my personal schedule.")], "answer_alone": False}, config, context=CONTEXT)
    current = result["messages"][len(history) + 1:]
    calls = [call for message in current if isinstance(message, AIMessage) for call in message.tool_calls]
    answer = core.final_answer(result["messages"], {}).answer
    print({"case": case, "calls": calls, "answer": answer})
    assert calls and all(call["name"] == "get_my_available_music_windows" for call in calls)
    for call in calls:
        assert call["args"]["day"] == DAY
        assert {key: call["args"].get(key) for key in ("time_from", "time_to")} == {"time_from": "15:00", "time_to": "16:00"}
        assert call["args"].get("duration_minutes") in {None, 60}
    assert not graph.get_state(config).interrupts
    payload = next(json.loads(message.content) for message in current if isinstance(message, ToolMessage))
    assert len(services["requests"]) == (1 if case in {"occupied", "legacy_morning_only"} else 2)
    lower = answer.lower().replace("**", "")
    assert not any(text in lower for text in ("09:00", "12:10", "10:00", "11:00", "unrelated morning", "classroom 321"))
    if case == "free":
        assert payload["available"] and "15:00" in answer and "16:00" in answer
    elif case == "occupied":
        assert payload["available"] == [] and payload["excluded"][0]["reason"] == "room_occupied"
        assert any(text in lower for text in ("occupied", "booked", "not available", "unavailable", "занят", "недоступ"))
    elif case == "conflict":
        assert payload["available"] == [] and "15:30" in answer and "16:30" in answer
    else:
        assert payload.get("complete") is False and not payload.get("available")
        assert any(text in lower for text in ("could not", "couldn't", "unable", "unknown", "not verif", "incomplete",
                                               "не удалось", "неполн", "не провер", "не могу", "неизвест"))
        assert not re.search(r"(?:music room|room|музкомната)\s+(?:is\s+)?(?:occupied|booked|занята)", lower)


@pytest.mark.model
@pytest.mark.parametrize("prior_misroute", [False, True], ids=["fresh-session", "recorded-wrong-room-history"])
def test_model_music_service_session_preserves_exact_interval(monkeypatch, services, prior_misroute):
    from tests.test_music_recommendations import exact_music, interval

    original = "Find a music room available tomorrow from 15:00 to 16:00."
    correction = "Find a music room available tomorrow from 15:00 to 16:00. music room"
    exact_music(services)
    services["agenda"]["schedule"] = [interval("15:00", "16:00", title="Personal class must not filter service availability")]
    services["local"] = []
    discoveries = []

    # Real catalogue ranking/schemas, but every service read is synthetic. Neither
    # a mistaken classroom route nor any write can reach an upstream service.
    async def discover(payload):
        async with mcp_server.adapter() as root, Client(root) as client:
            return {"tools": (await client.call_tool("search_tools", payload)).data,
                    "services": (await client.call_tool("service_status", {})).data}

    def service_read(method, payload, token, credentials):
        assert method == "call_tool" and token == "synthetic-ih" and credentials == {}
        services["requests"].append(deepcopy(payload))
        if payload["name"] == "music_get_available_windows":
            arguments = payload["arguments"]
            assert {key: arguments.get(key) for key in ("day", "time_from", "time_to")} == {
                "day": DAY, "time_from": "15:00", "time_to": "16:00"}
            assert arguments.get("duration_minutes") in {None, 60}
            assert set(arguments) <= {"day", "time_from", "time_to", "duration_minutes"}
            return deepcopy(services["music"])
        raise AssertionError("Generic music availability must not read calendars, university rooms or mutations")

    def request(method, payload, token=None, **credentials):
        if method == "search_tools":
            assert token is None and not credentials
            discoveries.append(deepcopy(payload))
            return asyncio.run(discover(payload))
        return service_read(method, payload, token, credentials)

    async def arequest(method, payload, token=None, **credentials):
        if method == "search_tools":
            assert token is None and not credentials
            discoveries.append(deepcopy(payload))
            return await discover(payload)
        return service_read(method, payload, token, credentials)

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    monkeypatch.setattr(api_tools.mcp_client, "request", arequest)
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    model = ChatOpenAI(base_url=str(settings.llm_route), api_key="not-needed", model=settings.llm_model,
                       max_tokens=2000, temperature=0, timeout=60, max_retries=0,
                       extra_body={"chat_template_kwargs": {"enable_thinking": False}})
    graph = core.build_agent(model, guardrail=False)
    config = {"configurable": {"thread_id": f"music-service-session-{prior_misroute}"}}

    def assert_turn(result, occupied):
        # Summarization can replace earlier history between turns.
        last_question = max(i for i, message in enumerate(result["messages"]) if isinstance(message, HumanMessage))
        current = result["messages"][last_question + 1:]
        calls = [call for message in current if isinstance(message, AIMessage) for call in message.tool_calls]
        assert calls
        assert all(call["name"] in {"search_api_tools", "call_api_tool"} for call in calls)
        reads = [call for call in calls if call["name"] != "search_api_tools"]
        assert reads
        for call in reads:
            arguments = call["args"]
            if call["name"] == "call_api_tool":
                assert arguments["name"] == "music_get_available_windows"
                arguments = arguments["arguments"]
            assert arguments["day"] == DAY
            assert arguments["time_from"] == "15:00" and arguments["time_to"] == "16:00"
        assert not graph.get_state(config).interrupts
        assert [item["name"] for item in services["requests"]].count("music_get_available_windows") == 1
        assert all(item["name"] == "music_get_available_windows" for item in services["requests"])
        assert not any(message.name == "get_my_available_music_windows" for message in current if isinstance(message, ToolMessage))
        payloads = [json.loads(message.content) for message in current if isinstance(message, ToolMessage)
                    and message.name != "search_api_tools"]
        assert payloads and all("error" not in payload for payload in payloads)
        evidence = payloads[-1]
        if occupied:
            assert evidence.get("reason") == "room_occupied" or any(
                item.get("reason") == "room_occupied" for item in evidence.get("excluded", []))
        else:
            assert evidence.get("available") or evidence.get("windows")
        answer = core.final_answer(result["messages"], {}).answer
        print({"prior_misroute": prior_misroute, "occupied": occupied, "calls": calls, "answer": answer})
        lower = answer.lower().replace("**", "")
        assert "15:00" in answer and "16:00" in answer
        assert not any(text in lower for text in ("09:00", "12:10", "personal class", "morning class", "meeting room 3.", "classroom 321"))
        if occupied:
            assert len(services["requests"]) == 1, "Service refusal must stop before any calendar reads"
            assert any(text in lower for text in ("occupied", "booked", "not available", "unavailable", "занят", "недоступ"))
        else:
            assert any(text in lower for text in ("available", "free", "доступ", "свобод"))

    if prior_misroute:
        # Reproduce the original failure's service confusion, keeping its exact
        # English user turns. Old room evidence is deliberately not music evidence.
        history = [HumanMessage(original), AIMessage("", tool_calls=[{
            "id": "old-classroom", "name": "call_api_tool", "args": {"name": "rooms_get_free_rooms",
                "arguments": {"day": DAY, "time_from": "15:00", "time_to": "16:00"}}}]),
            ToolMessage(json.dumps({"date": DAY, "range": "15:00-16:00", "timezone": "Europe/Moscow",
                "free": [{"room_id": "3.2", "title": "Meeting Room 3.2"}], "booked": [], "unavailable": []}),
                name="call_api_tool", tool_call_id="old-classroom"),
            AIMessage("Meeting Room 3.2 is free and bookable for students. Would you like to book it?")]
    else:
        # answer_alone=False keeps the production first-call planner enabled.
        result = graph.invoke({"messages": [HumanMessage(original)], "answer_alone": False}, config, context=CONTEXT)
        assert_turn(result, occupied=False)
        history = []  # The successful first turn is already in the checkpointer.

    services["requests"].clear()
    exact_music(services, reason="room_occupied")
    result = graph.invoke({"messages": [*history, HumanMessage(correction)], "answer_alone": False}, config, context=CONTEXT)
    assert_turn(result, occupied=True)
