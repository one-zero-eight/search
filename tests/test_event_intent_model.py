"""Real-model routing with synthetic attachment/agenda data, stopping at host approval.

No vision inference here: the regression concerns what the supervisor does AFTER
reading a poster. MCP discovery/schema validation are real; no business calls or
local storage operations are allowed. These are small development probes, not a benchmark.
"""
import json
import uuid
from datetime import datetime

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import SecretStr

from catix import attachments
from catix.agent import api_tools, attachment_tools, core, schedule_tools
from catix.agent.tools import AgentContext
from catix.db import pg
from catix.settings import settings

pytestmark = pytest.mark.model

FILE_ID = "11111111-1111-4111-8111-111111111111"
POSTER = ("Стартап Толк №20. Встреча предпринимателей и студентов: обсуждение роста бизнеса и нетворкинг. "
          "12 ноября 2026 года, 18:00–21:00 (Москва). Технопарк им. Лобачевского, коворкинг, Иннополис.")


@pytest.fixture
def routing(monkeypatch, mcp_http_protocol):
    monkeypatch.setattr(core.store, "visible_chats", lambda *args: [])
    monkeypatch.setattr(settings, "agent_plan_thinking", False)
    monkeypatch.setattr(settings, "agent_max_model_calls", 6)
    reads, business = [], []
    request_sync, request_async = api_tools.mcp_client.request_sync, api_tools.mcp_client.request

    def request(name, arguments, *args, **kwargs):
        if name == "search_tools":
            return request_sync(name, arguments, *args, **kwargs)
        business.append((name, arguments))
        pytest.fail("Routing probes must stop before business API calls")

    async def arequest(name, arguments, *args, **kwargs):
        if name == "search_tools":
            return await request_async(name, arguments, *args, **kwargs)
        business.append((name, arguments))
        pytest.fail("Routing probes must stop before business API calls")

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    monkeypatch.setattr(api_tools.mcp_client, "request", arequest)
    monkeypatch.setattr(pg, "connection", lambda *args, **kwargs: pytest.fail("No database in routing probes"))

    def image(owner, chat, attachment_id, page):
        assert (owner, chat, attachment_id, page) == ("synthetic-owner", "synthetic-chat", FILE_ID, 1)
        reads.append(attachment_id)
        return b"synthetic pixels; inspection is stubbed"

    monkeypatch.setattr(attachments, "image_page", image)
    monkeypatch.setattr(attachment_tools, "_inspect_image", lambda *args: (POSTER, False))

    def agenda(runtime, date_from=None, date_to=None):
        return {"range": [str(date_from), str(date_to or date_from)], "timezone": "Europe/Moscow",
                "events": [], "total": 0, "complete": True, "truncated": False, "not_read": [],
                "sources": {"ai_calendar": {"status": "complete", "truncated": False},
                            "innohassle": {"status": "complete", "truncated": False}}}

    monkeypatch.setattr(schedule_tools, "read_my_schedule", agenda)
    helper_tool = core._helper_tool

    def helper(role, model):
        # Preserve the production tool declaration; avoid real retrieval if routing regresses.
        return helper_tool(role, model).model_copy(update={"func": lambda **kwargs: POSTER})

    monkeypatch.setattr(core, "_helper_tool", helper)

    def run(question, with_image=True):
        info = {"id": FILE_ID, "filename": "image.png", "media_type": "image/png", "size_bytes": 100, "pages": 1}
        context = AgentContext(innohassle_id="synthetic-owner", innohassle_token=SecretStr("synthetic-not-real"),
                               attachment_chat_id="synthetic-chat", attachments=(info,) if with_image else (),
                               current_attachment_ids=(FILE_ID,) if with_image else (),
                               asked_at=datetime(2026, 11, 9, 0, 7, tzinfo=settings.tz))
        graph = core.build_agent(guardrail=False)
        config = {"configurable": {"thread_id": "event-intent-" + uuid.uuid4().hex}}
        result = graph.invoke({"messages": [HumanMessage(question)]}, config, context=context)
        calls = [call for message in result["messages"] if isinstance(message, AIMessage) for call in message.tool_calls]
        actions = [action for interrupt in graph.get_state(config).interrupts
                   for action in interrupt.value["action_requests"]]
        answer = result["messages"][-1].text
        print(json.dumps({"question": question, "calls": calls, "actions": actions, "answer": answer}, ensure_ascii=False))
        assert business == []
        if with_image:
            assert reads == [FILE_ID]
            assert calls[0]["name"] == "view_attachment"
        return calls, actions, answer

    return run


@pytest.mark.parametrize("question", ["создай ивент на основе изображения", "Создай ивент"])
def test_poster_creation_reaches_events_draft_approval(routing, question):
    calls, actions, answer = routing(question)
    assert len(actions) == 1, answer
    assert actions[0]["name"] == "call_api_tool"
    assert actions[0]["args"]["name"] == "events_create_draft"
    args = actions[0]["args"]["arguments"]
    assert "Стартап Толк" in args["name"] and args["description"].strip()
    assert args["starts_at"] == "2026-11-12T18:00:00+03:00"
    assert args["duration_hours"] == 3
    assert "Лобачевского" in args["location"]
    assert not args.get("club_id") and not args.get("registration_url")
    assert any(call["name"] == "search_api_tools" for call in calls)
    assert not {"add_to_ai_calendar", "ask_docs", "ask_chats"} & {call["name"] for call in calls}


def test_explicit_personal_calendar_request_does_not_create_events_draft(routing):
    calls, actions, answer = routing("Добавь мероприятие с изображения в мой календарь")
    assert len(actions) == 1, answer
    assert actions[0]["name"] == "add_to_ai_calendar"
    args = actions[0]["args"]
    assert args["day"] == "2026-11-12" and args["start_time"] == "18:00" and args["end_time"] == "21:00"
    assert not any(call["name"] == "call_api_tool" for call in calls)


def test_ambiguous_event_destination_is_clarified_without_mutation(routing):
    calls, actions, answer = routing("Создай событие «Встреча» 12 ноября 2026 с 18:00 до 19:00 в аудитории 512", with_image=False)
    assert actions == [], actions
    assert not any(call["name"] in {"call_api_tool", "add_to_ai_calendar"} for call in calls)
    lowered = answer.lower()
    assert "?" in answer and "календар" in lowered and ("черновик" in lowered or "draft" in lowered or "events" in lowered), answer
