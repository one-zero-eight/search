"""Real supervisor/planner probes with synthetic vision, credentials and upstreams.

Keep production tools and their injected ToolRuntime: only image inspection,
attachment storage and service boundaries are synthetic. Calendar runs stop at
native approval; this module never resumes or approves a mutation.
"""

from copy import deepcopy
from datetime import datetime
import json
import uuid

import pytest
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from pydantic import SecretStr

from catix import attachments, personal_calendar
from catix.agent import api_tools, attachment_tools, core
from catix.db import pg
from catix.settings import settings
from catix.agent.tools import AgentContext

pytestmark = pytest.mark.model

FILE_ID = "11111111-1111-4111-8111-111111111111"
OWNER = "task-intent-synthetic-owner"
CHAT = "task-intent-synthetic-chat"
PIXELS = b"synthetic image bytes; only the vision boundary is mocked"
INCOMPLETE_POSTER = (
    "Программирование дронов. Практический интенсив. 14–15 ноября. "
    "Иннополис, аудитория 512. Год, время начала и окончания на афише не указаны."
)
COMPLETE_POSTER = (
    "Программирование дронов. Практический интенсив. "
    "14 ноября 2026 года, с 10:00 до 16:00, московское время. "
    "Иннополис, аудитория 512."
)
EVENT_READS = {"events_get_university_events", "events_events_list_events"}


class _ToolBoundary(BaseCallbackHandler):
    """Fail before an unintended tool can contact retrieval or account backends."""

    raise_error = True

    def __init__(self, allowed):
        self.allowed = allowed
        self.started = []

    def on_tool_start(self, serialized, input_str, **kwargs):
        name = serialized["name"]
        self.started.append(name)
        if name not in self.allowed:
            pytest.fail(f"Unexpected tool execution in isolated intent probe: {name}")


@pytest.fixture
def intent_token():
    return SecretStr("task-intent-synthetic-not-a-production-token")


@pytest.fixture
def intent_probe(monkeypatch, mcp_http_protocol, intent_token):
    monkeypatch.setattr(core.store, "visible_chats", lambda *args: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    # guardrail=False avoids the external classifier, not the production planner.
    monkeypatch.setattr(settings, "agent_max_model_calls", 6)
    monkeypatch.setattr(personal_calendar, "account_key", lambda uid, telegram_id=None: f"ih:{uid}")

    writes, reads, inspections, business, discoveries = [], [], [], [], []

    def no_database(*args, **kwargs):
        pytest.fail("No database access is permitted in task-intent probes")

    def no_write(*args, **kwargs):
        writes.append((args, kwargs))
        pytest.fail("Native approval must interrupt before any calendar write")

    monkeypatch.setattr(pg, "connection", no_database)
    for name in ("add_event", "update_event", "delete_event"):
        monkeypatch.setattr(personal_calendar, name, no_write)

    def image_page(owner, chat, attachment_id, page):
        assert (owner, chat, attachment_id, page) == (OWNER, CHAT, FILE_ID, 1)
        reads.append(attachment_id)
        return PIXELS

    poster = None

    def inspect_image(png, question):
        assert png == PIXELS and question.strip()
        assert poster is not None
        inspections.append(question)
        return poster, False

    monkeypatch.setattr(attachments, "image_page", image_page)
    monkeypatch.setattr(attachment_tools, "_inspect_image", inspect_image)
    request_sync = api_tools.mcp_client.request_sync
    request_async = api_tools.mcp_client.request
    timeout_events = False

    def service_timeout(method, payload, token, credentials):
        business.append(deepcopy(payload))
        assert timeout_events, "No business service is needed for a poster or a clarification"
        assert method == "call_tool" and payload["name"] in EVENT_READS
        assert token is None and credentials == {}, "University event listings are public, not personal agenda reads"
        return {"code": "mcp_timeout", "error": "The MCP adapter request timed out; no reliable result was obtained."}

    def request(method, payload, token=None, **credentials):
        if method == "search_tools":
            assert timeout_events and token is None and credentials == {}
            discoveries.append(deepcopy(payload))
            return request_sync(method, payload)
        return service_timeout(method, payload, token, credentials)

    async def arequest(method, payload, token=None, **credentials):
        if method == "search_tools":
            assert timeout_events and token is None and credentials == {}
            discoveries.append(deepcopy(payload))
            return await request_async(method, payload)
        return service_timeout(method, payload, token, credentials)

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    monkeypatch.setattr(api_tools.mcp_client, "request", arequest)

    def run(question, *, image=None, event_timeout=False):
        nonlocal poster, timeout_events
        poster, timeout_events = image, event_timeout
        info = {"id": FILE_ID, "filename": "poster.png", "media_type": "image/png", "size_bytes": 100, "pages": 1}
        context = AgentContext(
            innohassle_id=OWNER, innohassle_token=intent_token,
            attachment_chat_id=CHAT,
            attachments=(info,) if image is not None else (),
            current_attachment_ids=(FILE_ID,) if image is not None else (),
            asked_at=datetime.fromisoformat("2026-11-09T12:00:00+03:00"),
        )
        allowed = {"search_api_tools", "call_api_tool"} if event_timeout else (
            {"view_attachment", "add_to_ai_calendar"} if image is not None else set()
        )
        boundary = _ToolBoundary(allowed)
        graph = core.build_agent(guardrail=False)
        config = {"configurable": {"thread_id": "task-intent-" + uuid.uuid4().hex}, "callbacks": [boundary]}
        result = graph.invoke(
            {"messages": [HumanMessage(question)], "answer_alone": False}, config, context=context,
        )
        calls = [call for message in result["messages"] if isinstance(message, AIMessage) for call in message.tool_calls]
        pending = graph.get_state(config).interrupts
        actions = [action for interrupt in pending for action in interrupt.value["action_requests"]]
        answer = core.final_answer(result["messages"], result.get("sources") or {}).answer
        print(json.dumps({"question": question, "calls": calls, "actions": actions, "answer": answer}, ensure_ascii=False))
        assert writes == []
        if image is not None:
            assert reads == [FILE_ID] and len(inspections) == 1
            assert calls and calls[0]["name"] == "view_attachment"
            visual = [json.loads(message.text) for message in result["messages"]
                      if isinstance(message, ToolMessage) and message.name == "view_attachment"]
            assert len(visual) == 1 and visual[0].get("visual") is True
            assert visual[0]["text"] == image
        else:
            assert reads == inspections == []
        if not event_timeout:
            assert business == discoveries == []
        return calls, actions, answer, boundary.started, business, discoveries

    return run


def test_incomplete_poster_is_read_then_missing_calendar_fields_are_clarified(intent_probe):
    calls, actions, answer, started, _, _ = intent_probe("добавь в ai календарь", image=INCOMPLETE_POSTER)
    assert [call["name"] for call in calls] == ["view_attachment"], calls
    assert started == ["view_attachment"] and actions == []
    lowered = answer.lower()
    assert answer.strip() and "год" in lowered, answer
    assert any(word in lowered for word in ("врем", "час", "начал")), answer
    assert "?" in answer or any(word in lowered for word in ("уточн", "укаж", "сообщ")), answer


def test_complete_poster_proposes_local_calendar_action_and_stops_at_native_approval(intent_probe):
    calls, actions, _, started, _, _ = intent_probe("добавь в ai календарь", image=COMPLETE_POSTER)
    assert [call["name"] for call in calls] == ["view_attachment", "add_to_ai_calendar"], calls
    assert started == ["view_attachment"], "The calendar tool must not execute before approval"
    assert len(actions) == 1 and actions[0]["name"] == "add_to_ai_calendar", actions
    args = actions[0]["args"]
    assert args["day"] == "2026-11-14"
    assert args["start_time"] == "10:00" and args["end_time"] == "16:00"
    assert args.get("all_day", False) is False
    assert args.get("proposed_duration_minutes") is None
    assert "дрон" in args["title"].lower() and "512" in (args.get("room") or "")
    assert calls[-1]["args"] == args


def test_ambiguous_signup_tomorrow_asks_domain_without_lookup(intent_probe):
    calls, actions, answer, started, _, _ = intent_probe("на что можно записаться на завтра")
    assert calls == actions == started == []
    lowered = answer.lower()
    assert "спорт" in lowered or "трениров" in lowered, answer
    assert any(word in lowered for word in ("мероприят", "событи", "ивент", "events")), answer
    assert "?" in answer or "уточн" in lowered, answer
    assert len(answer) < 500, answer


def test_explicit_event_signup_timeout_preserves_tomorrow_and_public_scope(intent_probe):
    calls, actions, answer, _, business, discoveries = intent_probe(
        "На какие мероприятия университета можно записаться завтра?", event_timeout=True,
    )
    assert actions == [] and discoveries and business
    assert calls and all(call["name"] in {"search_api_tools", "call_api_tool"} for call in calls), calls
    reads = [call["args"] for call in calls if call["name"] == "call_api_tool"]
    assert reads == business, "Every attempted read must go through the synthetic public service"
    for payload in business:
        assert payload["name"] in EVENT_READS, payload
        args = payload["arguments"]
        if payload["name"] == "events_get_university_events":
            assert args.get("date_from") == args.get("date_to") == "2026-11-10", payload
        else:
            assert args.get("from") and args.get("to"), payload
            start = datetime.fromisoformat(args["from"]).astimezone(settings.tz)
            end = datetime.fromisoformat(args["to"]).astimezone(settings.tz)
            assert start == datetime.fromisoformat("2026-11-10T00:00:00+03:00"), payload
            assert datetime.fromisoformat("2026-11-10T23:59:00+03:00") <= end <= datetime.fromisoformat("2026-11-11T00:00:00+03:00"), payload
    lowered = answer.lower()
    assert answer.strip() and any(word in lowered for word in (
        "не удалось", "не могу", "не смог", "не ответ", "таймаут", "недоступ", "ошиб", "сбой", "истек",
    )), answer
    assert not any(phrase in lowered for phrase in ("мероприятий нет", "нет мероприятий", "некуда записаться")), answer
