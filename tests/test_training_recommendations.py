"""Read-only Sport recommendations use the same interval checks as signup."""

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
                       sport_token=SecretStr("synthetic-sport"),
                       asked_at=datetime.fromisoformat("2026-11-08T07:20:55+03:00"))


def interval(start, end, **fields):
    return {"starts_at": f"{DAY}T{start}:00+03:00", "ends_at": f"{DAY}T{end}:00+03:00", **fields}


CLASSES = [interval("12:40", "14:10", title="Logic and Discrete Math (lab)"),
           interval("14:20", "15:50", title="English for Scientific Purposes")]
TRAININGS = [
    interval("13:30", "15:00", training_id=49039, name="Functional Training", place="[SC] 3rd floor", checked_in=False, can_check_in=True),
    interval("15:00", "16:30", training_id=47775, name="Functional Training", place="[SC] 3rd floor", checked_in=False, can_check_in=True),
    interval("17:00", "18:30", training_id=46975, name="Basketball", place="[SC] Big Hall", checked_in=False, can_check_in=True),
    interval("19:00", "20:30", training_id=48671, name="Karate", checked_in=False, can_check_in=False),
]


def tool():
    found = next((item for item in TOOLS if item.name == "get_my_available_trainings"), None)
    assert found is not None, "Recommendations need calendar-checked candidates, not raw Sport eligibility"
    return found


@pytest.fixture
def services(monkeypatch):
    state = {"trainings": {"range": [DAY, DAY], "trainings": deepcopy(TRAININGS)},
             "agenda": {"range": [DAY, DAY], "schedule": deepcopy(CLASSES), "bookings": []},
             "local": [], "requests": []}
    def request(method, payload, token=None, **credentials):
        state["requests"].append((method, deepcopy(payload), token, credentials))
        assert method == "call_tool" and token == "synthetic-ih"
        assert payload["arguments"] == PERIOD
        if payload["name"] == "sport_get_sport_trainings":
            assert credentials == {"sport_token": "synthetic-sport"}
            return state["trainings"]
        assert payload["name"] == "account_get_my_schedule", "Read-only tool must never sign up"
        assert credentials == {}
        return state["agenda"]
    monkeypatch.setattr(mcp_client, "request_sync", request)
    monkeypatch.setattr(calendar_tools, "events_between", lambda *a: state["local"])
    return state


def test_trace_functional_training_overlaps_are_excluded_before_recommendation(services):
    result, artifact = tool().func(SimpleNamespace(context=CONTEXT), date(2026, 11, 9))
    assert [t["training_id"] for t in result["available"]] == [46975]
    excluded = {t["training_id"]: t for t in result["excluded"]}
    assert excluded[49039]["reason"] == "schedule_conflict"
    assert [e["title"] for e in excluded[49039]["conflicts"]] == [e["title"] for e in CLASSES]
    assert excluded[47775]["reason"] == "schedule_conflict"
    assert excluded[48671]["reason"] == "training_unavailable"
    assert result["unverified"] == [] and result["complete"] is True
    assert result["range"] == [DAY, DAY] and result["total"] == 4
    assert [r[1]["name"] for r in services["requests"]] == ["sport_get_sport_trainings", "account_get_my_schedule"]
    assert artifact["agenda"]["complete"] is True
    assert artifact["trainings"]["range"] == [DAY, DAY]


def test_unknown_event_end_only_affects_later_nonconflicting_trainings(services):
    unknown = {**interval("09:00", "10:30", title="test1 по дискре", all_day=False), "ends_at": None}
    services["local"] = [unknown]
    early = {**TRAININGS[2], **interval("07:00", "09:00"), "training_id": 1}
    services["trainings"]["trainings"].insert(0, early)
    result, _ = tool().func(SimpleNamespace(context=CONTEXT), date.fromisoformat(DAY))
    assert [t["training_id"] for t in result["available"]] == [1]
    assert [t["training_id"] for t in result["excluded"]] == [49039, 47775, 48671]
    later, = result["unverified"]
    assert later["training_id"] == 46975 and later["reason"] == "schedule_unverified"
    assert later["uncertainty"] == "unknown_event_end"
    assert later["unknown_duration_events"][0]["title"] == "test1 по дискре"
    assert later["unknown_duration_events"][0]["ends_at"] is None
    assert result["complete"] is False and result["not_read"] == []


@pytest.mark.parametrize("mode", ["partial_calendar", "local_conflict", "unknown_duration", "closed", "truncated", "empty"])
def test_recommendations_never_confuse_unknown_or_ineligible_with_free(services, mode):
    services["trainings"]["trainings"] = [deepcopy(TRAININGS[2])]
    if mode == "partial_calendar":
        services["agenda"]["not_read"] = ["class: failed"]
    elif mode == "local_conflict":
        services["local"] = [interval("17:30", "18:00", title="Personal meeting")]
    elif mode == "unknown_duration":
        services["trainings"]["trainings"][0]["ends_at"] = None
    elif mode == "closed":
        services["trainings"]["trainings"][0]["can_check_in"] = False
    elif mode == "truncated":
        services["trainings"]["more"] = 4
    else:
        services["trainings"]["trainings"] = []
    result, _ = tool().func(SimpleNamespace(context=CONTEXT), date(2026, 11, 9))
    assert len(result["available"]) == (1 if mode == "truncated" else 0)
    if mode in {"partial_calendar", "unknown_duration"}:
        assert result["unverified"] and result["complete"] is False
    elif mode in {"local_conflict", "closed"}:
        assert result["excluded"] and result["complete"] is True
    elif mode == "truncated":
        assert result["complete"] is False and result["truncated"] is True and result["not_read"]
    else:
        assert result["complete"] is True and result["total"] == 0


@pytest.mark.parametrize("signup", [False, True])
def test_real_graph_recommendation_is_read_only_and_reusable_for_approval(monkeypatch, services, signup):
    import json
    from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
    from catix.agent import core

    from catix.common.status import STATUS
    from tests.test_roles import ScriptedModel
    from tests.test_sport_calendar_guard import SCHEMA

    original = mcp_client.request_sync
    def request(method, payload, token=None, **credentials):
        if method == "search_tools":
            assert token is None and credentials == {}
            return {"tools": [{"name": "sport_sport_checkin", "inputSchema": SCHEMA}]}
        return original(method, payload, token, **credentials)
    monkeypatch.setattr(mcp_client, "request_sync", request)
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    script: list[BaseMessage] = [AIMessage(content="", tool_calls=[{"name": "get_my_available_trainings", "args": {"day": DAY}, "id": "recommend"}])]
    if signup:
        script.append(AIMessage(content="", tool_calls=[{"name": "call_api_tool", "id": "signup", "args": {
            "name": "sport_sport_checkin", "arguments": {"training_id": 46975}}}]))
    script.append(AIMessage(content="Basketball 17:00–18:30."))
    graph = core.build_agent(ScriptedModel(responses=script), guardrail=False)
    config = {"configurable": {"thread_id": f"recommend-{signup}"}}
    out = graph.invoke({"messages": [HumanMessage("Подбери тренировку и запиши." if signup else "Предложи тренировки на завтра.")]},
                       config, context=CONTEXT)
    result = next(m for m in out["messages"] if isinstance(m, ToolMessage))
    assert result.status == "success"
    assert isinstance(result.content, str)
    assert json.loads(result.content)["available"][0]["training_id"] == 46975
    assert core.successful_read(out["messages"]) and core.read_evidence(out["messages"])
    assert "get_my_available_trainings" in STATUS
    paused = graph.get_state(config).interrupts
    assert bool(paused) is signup
    if signup:
        assert "Basketball" in paused[0].value["action_requests"][0]["description"]
        assert graph.get_state(config).values["api_prepared"][0]["schedule_check"]["training"]["training_id"] == 46975
    assert len(services["requests"]) == 2, "Reuse the snapshot; no redundant calendar/detail reads or writes before consent"


@pytest.mark.parametrize("context", [AgentContext(), AgentContext(innohassle_token=SecretStr("synthetic-ih")),
                                     AgentContext(sport_token=SecretStr("synthetic-sport"))])
def test_missing_credentials_never_read_any_service(monkeypatch, context):
    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: pytest.fail("No credentials"))
    result, artifact = tool().func(SimpleNamespace(context=context), date(2026, 11, 9))
    assert "error" in result and artifact is None


@pytest.mark.parametrize("arguments", [{}, {"day": DAY, "date_to": "2026-11-15"}, {"day": DAY, "owner": "other"},
                                       {"day": DAY, "sport_token": "forged"}])
def test_recommendation_schema_requires_one_day_and_forbids_identity(arguments):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        tool().args_schema.model_validate(arguments)


@pytest.mark.parametrize("fault", ["failed", "unpaired", "previous_turn", "wrong_tool", "missing_artifact"])
def test_old_or_unmatched_recommendation_does_not_supply_signup_evidence(monkeypatch, services, fault):
    import json
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
    from catix.agent.api_preflight import ApiPreflightMiddleware, ApiPreflightState
    from langgraph.runtime import Runtime
    from tests.test_sport_calendar_guard import SCHEMA

    result, artifact = tool().func(SimpleNamespace(context=CONTEXT), date(2026, 11, 9))
    pair = [AIMessage(content="", tool_calls=[{"name": "get_my_available_trainings", "args": {"day": DAY}, "id": "read"}]),
            ToolMessage(content=json.dumps(result), name="get_my_available_trainings", tool_call_id="read", artifact=artifact)]
    if fault == "failed":
        pair[1].status = "error"
    elif fault == "unpaired":
        pair[1].tool_call_id = "different"
    elif fault == "previous_turn":
        pair.append(HumanMessage("Запиши теперь."))
    elif fault == "wrong_tool":
        pair[0].tool_calls[0].update(name="call_api_tool", args={"name": "get_my_available_trainings", "arguments": {"day": DAY}})
        pair[1].name = "call_api_tool"
    else:
        pair[1].artifact = None
    state: ApiPreflightState = {"messages": [HumanMessage("Подбери и запиши."), *pair,
        AIMessage(content="", tool_calls=[{"name": "search_api_tools", "args": {"query": "sport_sport_checkin"}, "id": "schema"}]),
        ToolMessage(content=json.dumps({"tools": [{"name": "sport_sport_checkin", "inputSchema": SCHEMA}]}), name="search_api_tools", tool_call_id="schema"),
        AIMessage(content="", tool_calls=[{"name": "call_api_tool", "args": {"name": "sport_sport_checkin", "arguments": {"training_id": 46975}}, "id": "write"}])]}
    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: pytest.fail("No usable training evidence"))
    prepared = ApiPreflightMiddleware().after_model(state, Runtime(context=CONTEXT))
    assert prepared.get("jump_to") == "model" and prepared["api_prepared"] == []


@pytest.mark.parametrize("malformed", ["count", "available", "range", "reason", "complete"])
def test_malformed_recommendations_are_not_read_evidence(services, malformed):
    from catix.agent import core

    result, _ = tool().func(SimpleNamespace(context=CONTEXT), date(2026, 11, 9))
    if malformed == "count":
        result["total"] = 99
    elif malformed == "available":
        result["available"][0]["can_check_in"] = False
    elif malformed == "range":
        result["range"][1] = "2026-11-15"
    elif malformed == "reason":
        result["excluded"][0].pop("reason")
    else:
        result.update(complete=True, truncated=True)
    assert core._read_parts("get_my_available_trainings", result) is None


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_recommendation_snapshot_preserves_consent_and_fresh_execution_checks(monkeypatch, services, asynchronous, decision):
    import asyncio
    from langchain_core.messages import AIMessage, HumanMessage
    from langgraph.types import Command
    from catix.agent import core
    from tests.test_roles import ScriptedModel
    from tests.test_sport_calendar_guard import SCHEMA

    writes = []
    original = mcp_client.request_sync
    def request(method, payload, token=None, **credentials):
        if method == "search_tools":
            return {"tools": [{"name": "sport_sport_checkin", "inputSchema": SCHEMA}]}
        if payload["name"] == "sport_sport_checkin":
            assert token == "synthetic-ih" and credentials == {"sport_token": "synthetic-sport"}
            writes.append(payload["arguments"])
            return {"done": True, "training_id": 46975, "signed_up": True}
        return original(method, payload, token, **credentials)
    async def arequest(*a, **kw):
        return request(*a, **kw)
    monkeypatch.setattr(mcp_client, "request_sync", request)
    monkeypatch.setattr(mcp_client, "request", arequest)
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    graph = core.build_agent(ScriptedModel(responses=[
        AIMessage(content="", tool_calls=[{"name": "get_my_available_trainings", "args": {"day": DAY}, "id": "read"}]),
        AIMessage(content="", tool_calls=[{"name": "call_api_tool", "args": {"name": "sport_sport_checkin", "arguments": {"training_id": 46975}}, "id": "signup"}]),
        AIMessage(content="Обработано."),
    ]), guardrail=False)
    config = {"configurable": {"thread_id": "recommendation-consent"}}
    def invoke(value):
        return asyncio.run(graph.ainvoke(value, config, context=CONTEXT)) if asynchronous else graph.invoke(value, config, context=CONTEXT)
    invoke({"messages": [HumanMessage("Подбери и запиши на подходящую тренировку.")]})
    pending = graph.get_state(config).interrupts
    assert len(pending) == 1 and writes == [] and len(services["requests"]) == 2
    invoke(Command(resume={pending[0].id: {"decisions": [{"type": decision}]}}))
    assert writes == ([{"training_id": 46975}] if decision == "approve" else [])
    assert len(services["requests"]) == (4 if decision == "approve" else 2)
