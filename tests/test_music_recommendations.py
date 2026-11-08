"""Personal music windows: service limits intersect the complete unified agenda."""
from copy import deepcopy
from datetime import date, datetime
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from catix.agent import calendar_tools
from catix.agent.tools import AgentContext, TOOLS
from catix.innohassle import mcp_client

DAY = "2026-11-10"
CONTEXT = AgentContext(innohassle_id="synthetic-owner", innohassle_token=SecretStr("synthetic-ih"),
                       asked_at=datetime.fromisoformat("2026-11-09T12:10:00+03:00"))


def interval(start, end, **fields):
    return {"starts_at": f"{DAY}T{start}:00+03:00", "ends_at": f"{DAY}T{end}:00+03:00", **fields}


def tool():
    found = next((item for item in TOOLS if item.name == "get_my_available_music_windows"), None)
    assert found is not None, "Music recommendations must check the personal agenda, not just room occupancy"
    return found


@pytest.fixture
def services(monkeypatch):
    state = {
        "music": {"date": DAY, "timezone": "Europe/Moscow", "checked_at": "2026-11-09T12:10:00+03:00",
                  "availability": "calculated", "duration_minutes": 60,
                  "rules": {"opens_at": "07:00", "closes_at": "22:30", "step_minutes": 30,
                            "latest_booking_start": "2026-11-16T12:10:00+03:00", "source": "https://example.test/rules"},
                  "remaining_daily_minutes": 120, "remaining_weekly_minutes": 60, "reason": None,
                  "windows": [{"start": "10:30", "end": "18:00", "latest_start": "17:00", "max_duration_minutes": 60}]},
        "agenda": {"range": [DAY, DAY], "schedule": [interval("12:40", "14:10", title="Class")], "bookings": []},
        "local": [interval("16:00", "16:30", title="Personal meeting")], "requests": [],
    }
    def request(method, payload, token=None, **credentials):
        state["requests"].append(deepcopy(payload))
        assert method == "call_tool" and token == "synthetic-ih" and credentials == {}
        if payload["name"] == "music_get_available_windows":
            assert payload["arguments"] == {"day": DAY, **({"duration_minutes": state["music"]["duration_minutes"]}
                                                        if state["music"]["duration_minutes"] is not None else {})}
            return deepcopy(state["music"])
        assert payload == {"name": "account_get_my_schedule", "arguments": {"date_from": DAY, "date_to": DAY}}
        return deepcopy(state["agenda"])
    monkeypatch.setattr(mcp_client, "request_sync", request)
    monkeypatch.setattr(calendar_tools, "events_between", lambda *a: deepcopy(state["local"]))
    return state


def test_windows_subtract_both_calendars_regrid_and_preserve_quota(services):
    result, artifact = tool().func(SimpleNamespace(context=CONTEXT), date.fromisoformat(DAY), 60)
    assert [(w["start"], w["end"], w["latest_start"], w["max_duration_minutes"]) for w in result["available"]] == [
        ("10:30", "12:30", "11:30", 60), ("14:30", "16:00", "15:00", 60), ("16:30", "18:00", "17:00", 60),
    ]
    assert all(w["starts_at"].startswith(DAY) and w["ends_at"].startswith(DAY) for w in result["available"])
    assert {c["title"] for w in result["excluded"] for c in w.get("conflicts", [])} == {"Class", "Personal meeting"}
    assert all("starts_at" not in w and "start" not in w for w in result["excluded"] if w["reason"] == "schedule_conflict"), \
        "Report actual conflicts, not rounded grid blocks the model can mistake for class times"
    assert result["complete"] is True and result["unverified"] == [] and result["not_read"] == []
    assert result["total"] == sum(len(result[key]) for key in ("available", "excluded", "unverified"))
    assert result["remaining_weekly_minutes"] == 60 and result["duration_minutes"] == 60
    assert [r["name"] for r in services["requests"]] == ["music_get_available_windows", "account_get_my_schedule"]
    assert artifact["agenda"]["complete"] is True and artifact["music"] == services["music"]
    assert artifact["music_arguments"] == {"day": DAY, "duration_minutes": 60}


def test_trace_unknown_end_keeps_early_window_and_exact_known_conflicts(services, monkeypatch):
    monkeypatch.setattr("tests.test_music_recommendations.DAY", "2026-11-09")
    services["music"].update(date=DAY, checked_at="2026-11-08T12:10:00+03:00", duration_minutes=None,
                             remaining_weekly_minutes=120, windows=[
        {"start": start, "end": end, "latest_start": latest, "max_duration_minutes": maximum}
        for start, end, latest, maximum in [("07:00", "09:00", "08:30", 120),
                                           ("10:00", "10:30", "10:00", 30),
                                           ("12:30", "13:00", "12:30", 30),
                                           ("20:30", "21:00", "20:30", 30)]])
    services["agenda"].update(range=[DAY, DAY], schedule=[
        interval(start, end, title=f"Class {start}") for start, end in [
            ("09:00", "10:30"), ("10:40", "12:10"), ("12:40", "14:10"), ("14:20", "15:50")]])
    services["local"] = [{**interval("09:00", "10:30", title="test1 по дискре", all_day=False), "ends_at": None}]
    result, artifact = tool().func(SimpleNamespace(context=CONTEXT), date.fromisoformat(DAY))
    assert [(w["start"], w["end"]) for w in result["available"]] == [("07:00", "09:00")]
    assert [w["conflicts"][0]["starts_at"] for w in result["excluded"]] == [
        DAY + "T09:00:00+03:00", DAY + "T12:40:00+03:00"]
    assert all("start" not in w and "starts_at" not in w for w in result["excluded"])
    later, = result["unverified"]
    assert (later["start"], later["end"]) == ("20:30", "21:00")
    assert later["reason"] == "schedule_unverified" and later["uncertainty"] == "unknown_event_end"
    assert later["unknown_duration_events"][0]["title"] == "test1 по дискре"
    assert later["unknown_duration_events"][0]["ends_at"] is None
    assert result["complete"] is False and result["not_read"] == []
    assert result["total"] == 4 and artifact["agenda"]["complete"] is True


@pytest.mark.parametrize("duration", [None, 60])
def test_unknown_end_splits_one_window_without_losing_grid_or_limits(services, duration):
    services["music"]["duration_minutes"] = duration
    services["music"]["windows"][0]["latest_start"] = "16:30"
    services["local"] = [{**interval("16:10", "16:30", title="Unknown meeting", all_day=False), "ends_at": None}]
    result, _ = tool().func(SimpleNamespace(context=CONTEXT), date.fromisoformat(DAY), duration)
    assert [(w["start"], w["end"], w["latest_start"], w["max_duration_minutes"]) for w in result["available"]] == [
        ("10:30", "12:30", "11:30" if duration else "12:00", 60),
        ("14:30", "16:00", "15:00" if duration else "15:30", 60)]
    later, = result["unverified"]
    assert (later["start"], later["end"], later["latest_start"], later["max_duration_minutes"]) == (
        "15:30" if duration else "16:00", "17:30" if duration else "17:00", "16:30", 60)
    assert later["unknown_duration_events"][0]["starts_at"] == DAY + "T16:10:00+03:00"
    assert result["not_read"] == [] and result["complete"] is False


def test_requested_duration_crossing_unknown_start_remains_unverified(services):
    services["music"].update(duration_minutes=120, remaining_weekly_minutes=120, windows=[
        {"start": "07:00", "end": "10:00", "latest_start": "08:00", "max_duration_minutes": 120}])
    services["agenda"]["schedule"] = []
    services["local"] = [{**interval("09:00", "10:00", title="Unknown meeting", all_day=False), "ends_at": None}]
    result, _ = tool().func(SimpleNamespace(context=CONTEXT), date.fromisoformat(DAY), 120)
    assert [(w["start"], w["end"], w["latest_start"]) for w in result["available"]] == [("07:00", "09:00", "07:00")]
    later, = result["unverified"]
    assert (later["start"], later["end"], later["latest_start"]) == ("07:30", "10:00", "08:00")
    assert result["complete"] is False and result["not_read"] == []


@pytest.mark.parametrize("failure", ["upstream_timeout", "mcp_timeout", "partial"])
def test_calendar_timeout_reason_reaches_music_recommendations(services, failure):
    if failure == "partial":
        services["agenda"]["source_errors"] = {"rooms": "upstream_timeout"}
    else:
        services["agenda"] = {"error": "private diagnostic", "code": failure}
    result, artifact = tool().func(SimpleNamespace(context=CONTEXT), date.fromisoformat(DAY), 60)
    expected = {"innohassle.rooms": "upstream_timeout"} if failure == "partial" else {"innohassle": failure}
    assert result["source_errors"] == expected
    assert artifact["agenda"]["source_errors"] == expected
    assert result["complete"] is False and not result["available"] and result["unverified"]
    assert "private diagnostic" not in str(result)
    assert len(services["requests"]) == 2


@pytest.mark.parametrize("fault", ["partial", "truncated", "missing_owner", "local_failure"])
def test_incomplete_agenda_never_yields_free_windows(services, monkeypatch, fault):
    context = CONTEXT
    if fault == "partial":
        services["agenda"]["not_read"] = ["class: unavailable"]
    elif fault == "truncated":
        services["agenda"]["truncated"] = True
    elif fault == "missing_owner":
        context = AgentContext(innohassle_token=SecretStr("synthetic-ih"))
    else:
        def fail(*a):
            raise RuntimeError("private-storage-diagnostic")
        monkeypatch.setattr(calendar_tools, "events_between", fail)
    result, artifact = tool().func(SimpleNamespace(context=context), date.fromisoformat(DAY), 60)
    assert result["available"] == [] and result["unverified"]
    assert result["complete"] is False and result["not_read"]
    assert "private-storage-diagnostic" not in str(result)
    assert artifact["agenda"] and artifact["music"] == services["music"]


@pytest.mark.parametrize("fault", ["wrong_day", "wrong_duration", "wrong_timezone", "error", "truncated", "quota",
                                  "negative_quota", "grid", "latest", "oversized", "overlap", "null", "missing_reason"])
def test_invalid_service_response_is_unknown_not_free(services, fault):
    music = services["music"]
    if fault == "wrong_day":
        music["date"] = "2026-11-11"
    elif fault == "wrong_duration":
        # The request is deliberately correct; the return value is mismatched below.
        original = mcp_client.request_sync
        def request(*a, **kw):
            data = original(*a, **kw)
            if a[1]["name"] == "music_get_available_windows":
                data["duration_minutes"] = 30
            return data
        from unittest.mock import patch
        with patch.object(mcp_client, "request_sync", request):
            result, artifact = tool().func(SimpleNamespace(context=CONTEXT), date.fromisoformat(DAY), 60)
        assert "error" in result and artifact is None
        return
    elif fault == "wrong_timezone":
        music["timezone"] = "UTC"
    elif fault == "error":
        music["error"] = "private-upstream-diagnostic"
    elif fault == "truncated":
        music["truncated"] = True
    elif fault == "quota":
        music["remaining_weekly_minutes"] = True
    elif fault == "negative_quota":
        music["remaining_daily_minutes"] = -30
    elif fault == "grid":
        music["windows"][0]["start"] = "10:35"
    elif fault == "latest":
        music["windows"][0]["latest_start"] = "18:00"
    elif fault == "oversized":
        music["windows"][0]["max_duration_minutes"] = 120
    elif fault == "overlap":
        music["windows"] *= 2
    elif fault == "null":
        music["windows"] = None
    else:
        music["windows"] = []
        music["reason"] = None
    result, artifact = tool().func(SimpleNamespace(context=CONTEXT), date.fromisoformat(DAY), 60)
    assert "error" in result and not result.get("available") and artifact is None
    assert "private-upstream-diagnostic" not in str(result)


@pytest.mark.parametrize("case", ["boundary", "utc", "all_day", "short_gap", "horizon", "no_duration", "quota_empty"])
def test_window_boundaries_duration_and_service_limits(services, case):
    services["local"] = []
    services["agenda"]["schedule"] = []
    duration = 60
    if case == "boundary":
        services["local"] = [interval("09:00", "10:30"), interval("18:00", "19:00")]
    elif case == "utc":
        services["local"] = [{"starts_at": DAY + "T07:30:00Z", "ends_at": DAY + "T08:00:00Z"}]
    elif case == "all_day":
        services["local"] = [{"starts_at": DAY + "T12:00:00+03:00", "ends_at": None, "all_day": True}]
    elif case == "short_gap":
        services["local"] = [interval("11:00", "18:00")]
    elif case == "horizon":
        services["music"]["rules"]["latest_booking_start"] = DAY + "T12:10:00+03:00"
        services["music"]["windows"][0]["latest_start"] = "12:00"
        services["local"] = [interval("11:30", "12:10")]
    elif case == "no_duration":
        duration = None
        services["music"]["duration_minutes"] = None
        services["music"]["windows"][0]["latest_start"] = "17:30"
    else:
        services["music"].update(windows=[], reason="insufficient_quota", remaining_weekly_minutes=0)
    result, _ = tool().func(SimpleNamespace(context=CONTEXT), date.fromisoformat(DAY), duration)
    assert result["complete"] is True and result["unverified"] == []
    if case in {"all_day", "short_gap", "quota_empty"}:
        assert result["available"] == []
    else:
        assert len(result["available"]) == 1
        window = result["available"][0]
        assert window["start"] == ("11:00" if case == "utc" else "10:30")
        assert window["latest_start"] == {"horizon": "10:30", "no_duration": "17:30"}.get(case, "17:00")
        assert window["max_duration_minutes"] == 60
    if case == "quota_empty":
        assert result["reason"] == "insufficient_quota" and result["total"] == 0
    if case == "no_duration":
        assert result["duration_minutes"] is None and "duration_minutes" not in services["requests"][0]["arguments"]


@pytest.mark.parametrize("arguments", [{}, {"day": DAY, "owner": "forged"}, {"day": DAY, "runtime": {}},
                                       {"day": DAY, "duration_minutes": True}, {"day": DAY, "duration_minutes": "60"},
                                       {"day": DAY, "duration_minutes": 45}, {"day": DAY, "date_to": "2026-11-11"}])
def test_music_schema_requires_one_day_and_no_invented_identity(arguments):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        tool().args_schema.model_validate(arguments)


def test_music_without_signin_never_reads(monkeypatch):
    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: pytest.fail("No credentials"))
    result, artifact = tool().func(SimpleNamespace(context=AgentContext()), date.fromisoformat(DAY))
    assert "error" in result and artifact is None


def test_music_host_graph_exposes_read_evidence_and_status(monkeypatch, services):
    import json
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
    from catix.agent import core, roles
    from catix.common.status import STATUS
    from tests.test_roles import ScriptedModel

    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    name = "get_my_available_music_windows"
    assert name in roles.MAIN_TOOLS and all(name in role.tools for role in roles.ROLES.values())
    assert name in STATUS and name in roles.MCP_RULES
    graph = core.build_agent(ScriptedModel(responses=[
        AIMessage(content="", tool_calls=[{"name": name, "args": {"day": DAY, "duration_minutes": 60}, "id": "read"}]),
        AIMessage(content="Можно поиграть с 10:30 до 11:30."),
    ]), guardrail=False)
    config = {"configurable": {"thread_id": "music-recommendation"}}
    out = graph.invoke({"messages": [HumanMessage("Когда завтра могу поиграть час в музкомнате?")]}, config, context=CONTEXT)
    message = next(m for m in out["messages"] if isinstance(m, ToolMessage))
    assert message.status == "success" and isinstance(message.content, str)
    assert json.loads(message.content)["available"]
    assert core.successful_read(out["messages"]) and core.read_evidence(out["messages"])
    assert not graph.get_state(config).interrupts
    assert len(services["requests"]) == 2


@pytest.mark.parametrize("fault", [None, "count", "available", "range", "reason", "complete", "other_shape", "empty"])
def test_music_evidence_shape_is_scoped_counted_and_supports_empty(services, fault):
    from catix.agent import core
    if fault == "empty":
        services["music"].update(windows=[], reason="insufficient_quota", remaining_weekly_minutes=0)
    result, _ = tool().func(SimpleNamespace(context=CONTEXT), date.fromisoformat(DAY), 60)
    if fault == "count":
        result["total"] = 999
    elif fault == "available":
        result["available"][0].pop("starts_at")
    elif fault == "range":
        result["range"][1] = "2026-11-11"
    elif fault == "reason":
        result["excluded"][0].pop("reason")
    elif fault == "complete":
        result["truncated"] = True
    elif fault == "other_shape":
        result = services["music"]
    parts = core._read_parts("get_my_available_music_windows", result)
    assert (parts is not None) is (fault in {None, "empty"})
    if fault != "empty":
        assert core._read_parts("get_my_available_trainings", result) is None
    training_shape = {key: result[key] for key in ("range", "available", "excluded", "unverified", "total", "complete", "truncated", "not_read")
                      if key in result}
    assert core._read_parts("get_my_available_music_windows", training_shape) is None


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("decision,changed", [("approve", False), ("reject", False), ("approve", True)])
def test_real_recommendation_snapshot_reaches_consent_and_fresh_booking_check(monkeypatch, services, asynchronous, decision, changed):
    import asyncio
    from langchain_core.messages import AIMessage, HumanMessage
    from langgraph.types import Command
    from catix.agent import core
    from tests.test_music_calendar_guard import SCHEMA
    from tests.test_roles import ScriptedModel

    writes = []
    original = mcp_client.request_sync
    arguments = {"day": DAY, "time_from": "10:30", "time_to": "11:30"}
    def request(method, payload, token=None, **credentials):
        if method == "search_tools":
            assert token is None and credentials == {}
            return {"tools": [{"name": "music_book_music_room", "inputSchema": SCHEMA}]}
        if payload["name"] == "music_book_music_room":
            assert token == "synthetic-ih" and credentials == {} and payload["arguments"] == arguments
            writes.append(payload)
            return {"done": True, "booked": {"service": "music_room", "booking_id": "synthetic-booking"}}
        return original(method, payload, token, **credentials)
    async def arequest(*a, **kw):
        return request(*a, **kw)
    monkeypatch.setattr(mcp_client, "request_sync", request)
    monkeypatch.setattr(mcp_client, "request", arequest)
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    graph = core.build_agent(ScriptedModel(responses=[
        AIMessage(content="", tool_calls=[{"name": "get_my_available_music_windows", "args": {"day": DAY, "duration_minutes": 60}, "id": "read"}]),
        AIMessage(content="", tool_calls=[{"name": "call_api_tool", "args": {"name": "music_book_music_room", "arguments": arguments}, "id": "write"}]),
        AIMessage(content="Обработано."),
    ]), guardrail=False)
    config = {"configurable": {"thread_id": "music-recommendation-consent"}}
    def invoke(value):
        return asyncio.run(graph.ainvoke(value, config, context=CONTEXT)) if asynchronous else graph.invoke(value, config, context=CONTEXT)
    invoke({"messages": [HumanMessage("Проверь завтра музкомнату и забронируй с 10:30 до 11:30, если свободно.")]})
    pending = graph.get_state(config)
    assert len(pending.interrupts) == 1 and writes == []
    assert len(services["requests"]) == 2, "Native recommendation artifact must prevent redundant calendar reads"
    assert pending.values["api_prepared"][0]["schedule_check"]["booking"] == interval("10:30", "11:30")
    if changed:
        services["local"].append(interval("11:00", "12:00", title="New meeting"))
    invoke(Command(resume={pending.interrupts[0].id: {"decisions": [{"type": decision}]}}))
    assert len(writes) == (1 if decision == "approve" and not changed else 0)
    assert len(services["requests"]) == (3 if decision == "approve" else 2)
