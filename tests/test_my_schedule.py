"""One host read assembles the personal agenda; all services/storage are synthetic."""

from copy import deepcopy
from datetime import date, datetime
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from catix.agent import calendar_tools
from catix.agent.tools import AgentContext, TOOLS
from catix.innohassle import mcp_client

DAY = "2026-11-09"
PERIOD = {"date_from": DAY, "date_to": DAY}
CONTEXT = AgentContext(innohassle_id="synthetic-owner", innohassle_token=SecretStr("synthetic-ih"),
                       asked_at=datetime.fromisoformat(DAY + "T06:00:00+03:00"))
CLASS = {"title": "Selected English", "kind": "class", "calendar": "english-selected", "calendar_uid": "class-uid",
         "starts_at": DAY + "T09:00:00+03:00", "ends_at": DAY + "T10:30:00+03:00"}
BOOKING = {"title": "Study room", "service": "room", "booking_id": "AA+/BB==", "room": "314",
           "starts_at": DAY + "T12:00:00+03:00", "ends_at": DAY + "T13:00:00+03:00"}
LOCAL = {"title": "My meeting", "calendar_event_id": 17, "all_day": False,
         "starts_at": DAY + "T08:00:00Z", "ends_at": DAY + "T08:30:00Z", "source": "https://example.test/message"}


def tool():
    found = next((item for item in TOOLS if item.name == "get_my_schedule"), None)
    assert found is not None, "The main agent needs one personal schedule tool including AI Calendar"
    return found


def test_one_read_combines_both_sources_and_preserves_ids(monkeypatch):
    sent, local_reads = [], []
    external = {"range": [DAY, DAY], "schedule": [CLASS], "bookings": [BOOKING]}
    original = deepcopy(external)

    def request(method, payload, token=None, **credentials):
        sent.append((method, payload, token, credentials))
        return external

    def events(key, start, end):
        local_reads.append((key, start, end))
        return [LOCAL]

    monkeypatch.setattr(mcp_client, "request_sync", request)
    monkeypatch.setattr(calendar_tools, "events_between", events)
    result = tool().func(SimpleNamespace(context=CONTEXT), date(2026, 11, 9), date(2026, 11, 9))
    assert sent == [("call_tool", {"name": "account_get_my_schedule", "arguments": PERIOD}, "synthetic-ih", {})]
    assert local_reads == [("ih:synthetic-owner", date(2026, 11, 9), date(2026, 11, 9))]
    assert result["range"] == [DAY, DAY] and result["complete"] is True
    assert result["total"] == 3 and result["truncated"] is False
    assert [e["title"] for e in result["events"]] == ["Selected English", "My meeting", "Study room"]
    assert [e["source"] for e in result["events"]] == ["innohassle", "ai_calendar", "innohassle"]
    assert result["events"][0]["calendar_uid"] == "class-uid"
    assert result["events"][1]["calendar_event_id"] == 17
    assert result["events"][1]["starts_at"] == DAY + "T11:00:00+03:00"
    assert result["events"][1]["source_url"] == LOCAL["source"]
    assert result["events"][2]["booking_id"] == "AA+/BB=="
    assert result["sources"]["innohassle"]["status"] == "complete"
    assert result["sources"]["ai_calendar"]["status"] == "complete"
    assert external == original


@pytest.mark.parametrize("broken", ["external_exception", "external_error", "local_exception", "external_partial", "external_truncated",
                                   "local_truncated", "wrong_period", "malformed_bookings"])
def test_unavailable_or_partial_source_does_not_hide_the_other(monkeypatch, broken):
    external = {"range": [DAY, DAY], "schedule": [CLASS], "bookings": []}
    if broken == "external_error":
        external = {"error": "sensitive upstream diagnostic"}
    elif broken == "external_partial":
        external["not_read"] = ["class: selected English feed unavailable"]
    elif broken == "external_truncated":
        external["note"] = "Only the first 40 are shown; narrow the dates."
    elif broken == "wrong_period":
        external["range"] = ["2026-11-10", "2026-11-10"]
    elif broken == "malformed_bookings":
        external["bookings"] = None

    def request(*a, **kw):
        if broken == "external_exception":
            raise RuntimeError("sensitive upstream diagnostic")
        return external

    def local(*a, **kw):
        if broken == "local_exception":
            raise RuntimeError("sensitive database diagnostic")
        return [LOCAL] * (41 if broken == "local_truncated" else 1)

    monkeypatch.setattr(mcp_client, "request_sync", request)
    monkeypatch.setattr(calendar_tools, "events_between", local)
    result = tool().func(SimpleNamespace(context=CONTEXT), date(2026, 11, 9), date(2026, 11, 9))
    assert result["complete"] is False and result["not_read"]
    assert "sensitive" not in str(result)
    good_source = "innohassle" if broken.startswith("local") else "ai_calendar"
    assert any(event["source"] == good_source for event in result["events"])
    assert result["sources"][good_source]["status"] == "complete"
    if broken.endswith("truncated"):
        assert result["truncated"] is True
    if broken == "malformed_bookings":
        assert any(event["title"] == CLASS["title"] for event in result["events"])


def test_default_dates_anchor_to_question_and_match_for_both_sources(monkeypatch):
    sent, local_reads = [], []
    def request(method, payload, token=None, **kw):
        sent.append(payload)
        return {"range": list(payload["arguments"].values()), "schedule": [], "bookings": []}
    monkeypatch.setattr(mcp_client, "request_sync", request)
    monkeypatch.setattr(calendar_tools, "events_between", lambda key, start, end: local_reads.append((str(start), str(end))) or [])
    result = tool().func(SimpleNamespace(context=CONTEXT))
    assert result["range"] == [DAY, "2026-11-15"] and result["complete"] is True
    assert sent[0]["arguments"] == {"date_from": DAY, "date_to": "2026-11-15"}
    assert local_reads == [(DAY, "2026-11-15")]


def test_unauthenticated_read_keeps_local_events_without_private_rpc(monkeypatch):
    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: pytest.fail("No private read without user credentials"))
    monkeypatch.setattr(calendar_tools, "events_between", lambda *a: [LOCAL])
    context = AgentContext(innohassle_id="synthetic-owner", asked_at=CONTEXT.asked_at)
    result = tool().func(SimpleNamespace(context=context))
    assert result["complete"] is False and len(result["events"]) == 1
    assert result["sources"]["innohassle"]["status"] == "unavailable"
    assert "sign" in str(result["not_read"]).lower()


def test_signed_in_external_failure_never_substitutes_group_timetable(monkeypatch):
    sent = []
    monkeypatch.setattr(mcp_client, "request_sync", lambda method, payload, *a, **kw: sent.append(payload) or {"error": "Unavailable"})
    monkeypatch.setattr(calendar_tools, "events_between", lambda *a: [LOCAL])
    context = AgentContext(innohassle_id="synthetic-owner", innohassle_token=CONTEXT.innohassle_token,
                           study_group="B26-CSE-01", asked_at=CONTEXT.asked_at)
    result = tool().func(SimpleNamespace(context=context))
    assert [r["name"] for r in sent] == ["account_get_my_schedule"]
    assert result["complete"] is False and result["events"][0]["source"] == "ai_calendar"


def test_bot_uses_trusted_group_as_labelled_partial_fallback(monkeypatch):
    sent = []
    def request(method, payload, token=None, **credentials):
        sent.append((payload, token, credentials))
        return {"range": [DAY, DAY], "schedule": "B26-CSE-01", "classes": [CLASS], "total": 1}
    monkeypatch.setattr(mcp_client, "request_sync", request)
    monkeypatch.setattr(calendar_tools.personal_calendar, "telegram_key", lambda ident: "ih:linked-owner" if ident == 17 else None)
    monkeypatch.setattr(calendar_tools, "events_between", lambda key, *a: [LOCAL] if key == "ih:linked-owner" else [])
    context = AgentContext(user_telegram_id=17, study_group="B26-CSE-01", asked_at=CONTEXT.asked_at)
    result = tool().func(SimpleNamespace(context=context), date(2026, 11, 9), date(2026, 11, 9))
    assert sent == [({"name": "schedule_get_schedule", "arguments": {**PERIOD, "group": "B26-CSE-01"}}, None, {})]
    assert result["complete"] is False and result["total"] == 2
    assert result["sources"]["group_timetable"]["status"] == "partial"
    assert {e["source"] for e in result["events"]} == {"group_timetable", "ai_calendar"}
    assert "English" in str(result["not_read"])


def test_all_failed_is_not_a_successful_empty_agenda(monkeypatch):
    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: {"error": "Unavailable"})
    monkeypatch.setattr(calendar_tools, "read_calendar", lambda *a: {"error": "Unavailable"})
    result = tool().func(SimpleNamespace(context=CONTEXT))
    assert result["complete"] is False and result["events"] == []
    assert all(s["status"] == "unavailable" for s in result["sources"].values())


@pytest.mark.parametrize("field", ["day", "owner", "innohassle_token", "group"])
def test_model_cannot_inject_identity_or_silent_date_alias(field):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        tool().args_schema.model_validate({field: "forged"})


def test_root_uses_one_tool_and_keeps_combined_read_as_evidence(monkeypatch):
    import json
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
    from catix.agent import core
    from catix.common.status import STATUS
    from tests.test_roles import ScriptedModel

    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: {"range": [DAY, DAY], "schedule": [CLASS], "bookings": []})
    monkeypatch.setattr(calendar_tools, "events_between", lambda *a: [LOCAL])
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    agent = core.build_agent(ScriptedModel(responses=[
        AIMessage(content="", tool_calls=[{"name": "get_my_schedule", "args": PERIOD, "id": "agenda"}]),
        AIMessage(content="У вас английский и личная встреча."),
    ]), guardrail=False)
    config = {"configurable": {"thread_id": "combined-agenda"}}
    result = agent.invoke({"messages": [HumanMessage("Что у меня завтра?")]}, config, context=CONTEXT)
    messages = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert len(messages) == 1 and messages[0].name == "get_my_schedule"
    assert isinstance(messages[0].content, str)
    assert json.loads(messages[0].content)["total"] == 2
    assert core.read_evidence(result["messages"]) and core.successful_read(result["messages"])
    assert not agent.get_state(config).interrupts
    assert "get_my_schedule" in STATUS


@pytest.mark.parametrize("kind,recognized", [("complete_empty", True), ("partial_empty", True),
                                           ("all_failed", False), ("bad_count", False), ("wrong_source", False), ("unhashable_source", False)])
def test_merged_agenda_evidence_distinguishes_partial_empty_from_unread(monkeypatch, kind, recognized):
    from catix.agent import core

    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: {"range": [DAY, DAY], "schedule": [], "bookings": []})
    monkeypatch.setattr(calendar_tools, "events_between", lambda *a: [])
    result = tool().func(SimpleNamespace(context=CONTEXT), date(2026, 11, 9), date(2026, 11, 9))
    if kind in {"partial_empty", "all_failed"}:
        result["complete"] = False
        result["not_read"] = ["innohassle: unavailable"]
        result["sources"]["innohassle"]["status"] = "unavailable"
    if kind == "all_failed":
        result["sources"]["ai_calendar"]["status"] = "unavailable"
    elif kind == "bad_count":
        result["total"] = 1
    elif kind == "wrong_source":
        result["events"] = [{**CLASS, "source": "invented"}]
        result["total"] = 1
    elif kind == "unhashable_source":
        result["events"] = [{**CLASS, "source": {"bad": "source"}}]
        result["total"] = 1
    assert (core._read_parts("get_my_schedule", result) is not None) is recognized


def test_sport_preflight_uses_the_same_combined_agenda(monkeypatch):
    import json
    from langchain_core.messages import AIMessage, ToolMessage
    from tests.test_sport_calendar_guard import history, prepare

    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: {"range": [DAY, DAY], "schedule": [CLASS], "bookings": []})
    monkeypatch.setattr(calendar_tools, "events_between", lambda *a: [LOCAL])
    agenda = tool().func(SimpleNamespace(context=CONTEXT), date(2026, 11, 9), date(2026, 11, 9))
    state = history()
    state["messages"][3:5] = [AIMessage(content="", tool_calls=[{"name": "get_my_schedule", "args": PERIOD, "id": "combined"}]),
                              ToolMessage(content=json.dumps(agenda), name="get_my_schedule", tool_call_id="combined")]
    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: pytest.fail("The combined read is already available"))
    result = prepare(state)
    assert result.get("jump_to") == "model"
    feedback = json.loads(result["messages"][0].content)
    assert feedback["code"] == "schedule_conflict"
    assert feedback["conflicts"][0]["source"] == "innohassle"


def test_forged_mcp_name_cannot_replace_the_host_agenda(monkeypatch):
    from catix.agent import schedule_tools
    from tests.test_sport_calendar_guard import history, prepare

    monkeypatch.setattr(schedule_tools, "read_my_schedule", lambda *a: {"error": "unavailable"})
    state = history(classes=[])
    state["messages"][3].tool_calls[0].update(name="call_api_tool", args={"name": "get_my_schedule", "arguments": PERIOD})
    state["messages"][4].name = "call_api_tool"
    assert prepare(state).get("jump_to") == "model"


@pytest.mark.parametrize("row", [{}, {**CLASS, "title": []}, {**CLASS, "starts_at": "not a timestamp"}])
def test_bad_event_does_not_abort_unaffected_source_or_prove_completeness(monkeypatch, row):
    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: {"range": [DAY, DAY], "schedule": [row], "bookings": []})
    monkeypatch.setattr(calendar_tools, "events_between", lambda *a: [LOCAL])
    result = tool().func(SimpleNamespace(context=CONTEXT), date(2026, 11, 9), date(2026, 11, 9))
    assert result["complete"] is False and result["not_read"]
    assert result["events"][0]["calendar_event_id"] == 17


@pytest.mark.parametrize("helper", [False, True])
@pytest.mark.parametrize("tool_name", ["get_my_schedule", "get_my_available_trainings"])
def test_agenda_progress_is_shown_before_any_tool_result(monkeypatch, helper, tool_name):
    import asyncio
    from langchain_core.messages import AIMessageChunk
    from catix.api import ask
    from catix.common.status import STATUS
    from tests.test_stream import Recorder, SUPERVISOR

    chunk = AIMessageChunk(content="", id="model", tool_call_chunks=[
        {"name": tool_name, "args": "", "id": "agenda", "index": 0}])
    event = ("custom", {"tool": tool_name}) if helper else ("messages", (chunk, SUPERVISOR))
    queue = asyncio.Queue()
    class Stream:
        async def astream(self, *a, **kw):
            yield event
            # The consumer must publish progress before the tool yields its result.
            sent = [queue.get_nowait() for _ in range(queue.qsize())]
            assert ("status", {"text": STATUS[tool_name]}) in sent
            yield "values", {"messages": []}
    monkeypatch.setattr(ask, "agent", lambda: Stream())
    asyncio.run(ask.stream_agent({}, {}, CONTEXT, queue))
    recorder = Recorder()
    asyncio.run(recorder.feed_custom(event[1]) if helper else recorder.feed(chunk, SUPERVISOR))
    assert recorder.sent == [STATUS[tool_name]]


@pytest.mark.parametrize("helper", ["docs", "chats"])
def test_helpers_share_the_same_host_agenda_without_local_write_tools(monkeypatch, helper):
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
    from catix.agent import core, roles
    from tests.test_roles import ScriptedModel

    requests = []
    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: requests.append(a) or {"range": [DAY, DAY], "schedule": [CLASS], "bookings": []})
    monkeypatch.setattr(calendar_tools, "events_between", lambda *a: [LOCAL])
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    model = ScriptedModel(responses=[
        AIMessage(content="", tool_calls=[{"name": f"ask_{helper}", "args": {"question": "Что у меня завтра?"}, "id": "helper"}]),
        AIMessage(content="", tool_calls=[{"name": "get_my_schedule", "args": PERIOD, "id": "agenda"}]),
        AIMessage(content="Английский и личная встреча."), AIMessage(content="Английский и личная встреча."),
    ])
    result = core.build_agent(model, guardrail=False).invoke({"messages": [HumanMessage("Что у меня завтра?")]},
                {"configurable": {"thread_id": f"shared-agenda-{helper}"}}, context=CONTEXT)
    report = next(m for m in result["messages"] if isinstance(m, ToolMessage))
    assert report.name == f"ask_{helper}" and report.artifact["read_found"] is True
    assert report.artifact["tools"] == ["get_my_schedule"] and len(requests) == 1
    assert "add_to_ai_calendar" not in roles.ROLES[helper].tools
