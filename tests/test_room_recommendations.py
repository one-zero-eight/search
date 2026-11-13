"""Read-only room recommendations combine service permissions and the full agenda."""
from copy import deepcopy
from datetime import date, datetime
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from catix.agent import calendar_tools
from catix.agent.tools import AgentContext, TOOLS
from catix.innohassle import mcp_client

DAY = "2026-11-10"
ARGUMENTS = {"day": DAY, "time_from": "18:00", "time_to": "19:00"}
CONTEXT = AgentContext(innohassle_id="synthetic-owner", innohassle_token=SecretStr("synthetic-ih"),
                       asked_at=datetime.fromisoformat("2026-11-09T12:00:00+03:00"))


def interval(start="18:00", end="19:00", **fields):
    return {"starts_at": f"{DAY}T{start}:00+03:00", "ends_at": f"{DAY}T{end}:00+03:00", **fields}


def tool():
    found = next((item for item in TOOLS if item.name == "get_my_available_rooms"), None)
    assert found is not None, "Room recommendations must include the personal agenda"
    return found


def recommend(context=CONTEXT):
    return tool().func(SimpleNamespace(context=context), date.fromisoformat(DAY), "18:00", "19:00")


@pytest.fixture
def services(monkeypatch):
    state = {"rooms": {"date": "2026-11-10 Tue", "range": "18:00-19:00", "timezone": "Europe/Moscow",
                       "checked_at": "2026-11-09T12:00:00+03:00",
                       "free": [{"room_id": "r", "title": "Room", "capacity": 12}], "booked": ["busy"],
                       "unavailable": [{"room_id": "staff", "reason": "Staff only"}]},
             "agenda": {"range": [DAY, DAY], "schedule": [], "bookings": []}, "local": [], "requests": []}
    def request(method, payload, token=None, **credentials):
        state["requests"].append(deepcopy(payload))
        assert method == "call_tool" and token == "synthetic-ih" and credentials == {}
        if payload["name"] == "rooms_get_free_rooms":
            assert payload["arguments"] == ARGUMENTS
            return deepcopy(state["rooms"])
        assert payload == {"name": "account_get_my_schedule", "arguments": {"date_from": DAY, "date_to": DAY}}
        return deepcopy(state["agenda"])
    monkeypatch.setattr(mcp_client, "request_sync", request)
    monkeypatch.setattr(calendar_tools, "events_between", lambda *a: deepcopy(state["local"]))
    return state


def test_rooms_combine_service_availability_with_one_unified_agenda_read(services):
    result, artifact = recommend()
    assert result["available"] == services["rooms"]["free"]
    assert result["excluded"] == [{"room_id": "busy", "reason": "room_occupied"},
                                  {"room_id": "staff", "reason": "service_unavailable", "detail": "Staff only"}]
    assert result["interval"] == interval() and result["range"] == [DAY, DAY]
    assert result["unverified"] == [] and result["conflicts"] == []
    assert result["complete"] is True and result["truncated"] is False and result["not_read"] == []
    assert result["total"] == 3 and result["timezone"] == "Europe/Moscow"
    assert result["service_checked_at"] == services["rooms"]["checked_at"]
    assert [r["name"] for r in services["requests"]] == ["rooms_get_free_rooms", "account_get_my_schedule"]
    assert artifact["rooms"] == services["rooms"] and artifact["agenda"]["complete"] is True
    assert artifact["room_arguments"] == ARGUMENTS


@pytest.mark.parametrize("source", ["external", "local", "booking", "all_day", "utc", "boundary", "unknown", "later_unknown", "known_and_unknown"])
def test_calendar_conflicts_and_unknown_ends_are_distinct(services, source):
    event = interval("18:30", "19:30", title="Meeting")
    if source == "external":
        services["agenda"]["schedule"] = [event]
    elif source == "booking":
        services["agenda"]["bookings"] = [{**event, "service": "music_room", "booking_id": "own-booking"}]
    elif source == "all_day":
        services["local"] = [{**interval("12:00", "13:00", title="Day off"), "ends_at": None, "all_day": True}]
    elif source == "utc":
        services["local"] = [{"starts_at": DAY + "T15:30:00Z", "ends_at": DAY + "T16:30:00Z", "title": "UTC meeting"}]
    elif source == "boundary":
        services["local"] = [interval("17:00", "18:00"), interval("19:00", "20:00")]
    elif source in {"unknown", "later_unknown", "known_and_unknown"}:
        services["local"] = [{**interval("19:00" if source == "later_unknown" else "18:30", "20:00", title="Unknown end"),
                              "ends_at": None}]
        if source == "known_and_unknown":
            services["local"].append(event)
    else:
        services["local"] = [event]
    result, _ = recommend()
    assert result["total"] == 3 and result["not_read"] == []
    if source in {"boundary", "later_unknown"}:
        assert result["available"] and not result["conflicts"] and not result["unverified"]
        assert result["complete"] is True
    elif source == "unknown":
        assert not result["available"] and not result["conflicts"]
        assert result["unverified"] == [{**services["rooms"]["free"][0], "reason": "schedule_unverified"}]
        assert result["uncertainty"] == "unknown_event_end"
        assert result["unknown_duration_events"][0]["ends_at"] is None
        assert result["complete"] is False
    else:
        assert not result["available"] and not result["unverified"]
        assert result["excluded"][-1] == {**services["rooms"]["free"][0], "reason": "schedule_conflict"}
        assert len(result["conflicts"]) == 1 and result["complete"] is True
        assert all("conflicts" not in row for row in result["excluded"]), "Shared conflicts must not be repeated per room"


@pytest.mark.parametrize("failure", ["upstream_timeout", "mcp_timeout", "partial"])
def test_calendar_timeout_reason_reaches_room_recommendations(services, failure):
    if failure == "partial":
        services["agenda"]["source_errors"] = {"music_room": "upstream_timeout"}
    else:
        services["agenda"] = {"error": "private diagnostic", "code": failure}
    result, artifact = recommend()
    expected = {"innohassle.music_room": "upstream_timeout"} if failure == "partial" else {"innohassle": failure}
    assert result["source_errors"] == expected
    assert artifact["agenda"]["source_errors"] == expected
    assert result["complete"] is False and not result["available"] and result["unverified"]
    assert {r["reason"] for r in result["excluded"]} == {"room_occupied", "service_unavailable"}
    assert "private diagnostic" not in str(result)
    assert len(services["requests"]) == 2


@pytest.mark.parametrize("fault", ["partial", "truncated", "missing_owner", "local_failure", "invalid_interval"])
def test_incomplete_calendars_preserve_service_exclusions_but_never_claim_free(services, monkeypatch, fault):
    context = CONTEXT
    if fault == "partial":
        services["agenda"]["not_read"] = ["class: unavailable"]
    elif fault == "truncated":
        services["agenda"]["truncated"] = True
    elif fault == "missing_owner":
        context = AgentContext(innohassle_token=SecretStr("synthetic-ih"))
    elif fault == "invalid_interval":
        services["local"] = [interval("18:30", "18:00")]
    else:
        def fail(*a):
            raise RuntimeError("private-storage-diagnostic")
        monkeypatch.setattr(calendar_tools, "events_between", fail)
    result, artifact = recommend(context)
    assert not result["available"] and result["unverified"]
    assert result["complete"] is False and result["not_read"]
    assert {r["reason"] for r in result["excluded"]} == {"room_occupied", "service_unavailable"}
    assert "private-storage-diagnostic" not in str(result)
    assert artifact["rooms"] == services["rooms"]


@pytest.mark.parametrize("field,value", [
    ("date", "2026-11-11 Wed"), ("range", "18:00-20:00"), ("timezone", "UTC"),
    ("checked_at", "2026-11-09T12:00:00"), ("checked_at", None), ("checked_at", "2026-11-10T20:00:00+03:00"),
    ("free", None), ("free", [{"room_id": ""}]), ("free", [{"room_id": "r", "capacity": True}]),
    ("free", [{"room_id": "r", "title": []}]), ("free", [{"room_id": "r"}, {"room_id": "r"}]),
    ("booked", "busy"), ("booked", ["r"]), ("unavailable", [{"room_id": "staff", "reason": ""}]),
    ("truncated", True), ("more", 1), ("total", 99), ("error", "private-upstream-diagnostic"),
])
def test_malformed_or_mismatched_service_data_never_means_available(services, field, value):
    services["rooms"][field] = value
    result, artifact = recommend()
    assert "error" in result and not result.get("available") and artifact is None
    assert "private-upstream-diagnostic" not in str(result)
    assert len(services["requests"]) == 1, "Do not read the agenda after invalid room availability"


def test_service_failure_is_unknown_not_an_empty_room_list(monkeypatch):
    def fail(*a, **kw):
        raise RuntimeError("private-upstream-diagnostic")
    monkeypatch.setattr(mcp_client, "request_sync", fail)
    result, artifact = recommend()
    assert "error" in result and "available" not in result and artifact is None
    assert "private-upstream-diagnostic" not in str(result)


def test_without_signin_never_reads(monkeypatch):
    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: pytest.fail("No credentials"))
    result, artifact = recommend(AgentContext())
    assert "error" in result and artifact is None


@pytest.mark.parametrize("changes", [{"day": None}, {"time_to": None}, {"time_to": "17:00"}, {"time_to": "18:00"},
                                     {"time_from": "18:00:00"}, {"time_from": "18:00+03:00"}, {"time_from": True},
                                     {"time_to": "24:00"}, {"time_from": "18:00\n"}, {"owner": "other"},
                                     {"runtime": {}}, {"token": "forged"}])
def test_schema_requires_exact_ordered_clocks_and_no_identity(changes):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        tool().args_schema.model_validate({**ARGUMENTS, **changes})


@pytest.mark.parametrize("missing", ["day", "time_from", "time_to"])
def test_schema_does_not_default_day_or_duration(missing):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        tool().args_schema.model_validate({key: value for key, value in ARGUMENTS.items() if key != missing})


def test_empty_service_inventory_is_a_valid_empty_read(services):
    services["rooms"].update(free=[], booked=[], unavailable=[])
    result, artifact = recommend()
    assert result["total"] == 0 and result["complete"] is True and artifact["rooms"]
    assert not result["available"] and not result["excluded"] and not result["unverified"]


@pytest.mark.parametrize("helper", [None, "docs", "chats"])
@pytest.mark.parametrize("asynchronous", [False, True])
def test_native_host_graph_exposes_read_and_evidence_without_approval(services, monkeypatch, helper, asynchronous):
    import asyncio
    import json
    from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
    from catix.agent import core, roles
    from tests.test_roles import ScriptedModel
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    name = "get_my_available_rooms"
    assert name in roles.MAIN_TOOLS and all(name in role.tools for role in roles.ROLES.values())
    assert name in roles.MCP_RULES
    script: list[BaseMessage] = [AIMessage(content="", tool_calls=[{"name": name, "args": ARGUMENTS, "id": "read"}]),
              AIMessage(content="Room доступна с 18:00 до 19:00.")]
    if helper:
        script.insert(0, AIMessage(content="", tool_calls=[{"name": f"ask_{helper}", "args": {"question": "Подбери комнату завтра с 18 до 19"}, "id": "helper"}]))
        script.append(AIMessage(content="Room доступна с 18:00 до 19:00."))
    graph = core.build_agent(ScriptedModel(responses=script), guardrail=False)
    config = {"configurable": {"thread_id": f"rooms-{helper}-{asynchronous}"}}
    inputs = {"messages": [HumanMessage("Подбери комнату завтра с 18 до 19")]}
    out = asyncio.run(graph.ainvoke(inputs, config, context=CONTEXT)) if asynchronous else graph.invoke(inputs, config, context=CONTEXT)
    message = next(m for m in out["messages"] if isinstance(m, ToolMessage))
    assert message.status == "success"
    if helper:
        assert message.artifact["read_found"] is True and message.artifact["tools"] == [name]
    else:
        assert isinstance(message.content, str)
        assert json.loads(message.content)["available"]
        assert core.successful_read(out["messages"]) and core.read_evidence(out["messages"])
    assert not graph.get_state(config).interrupts and len(services["requests"]) == 2


@pytest.mark.parametrize("fault", [None, "empty", "count", "room_id", "reason", "complete", "interval", "range", "other_family"])
def test_room_evidence_validates_its_own_wire_shape(services, fault):
    from catix.agent import core
    if fault == "empty":
        services["rooms"].update(free=[], booked=[], unavailable=[])
    result, _ = recommend()
    if fault == "count":
        result["total"] += 1
    elif fault == "room_id":
        result["available"][0].pop("room_id")
    elif fault == "reason":
        result["excluded"][0].pop("reason")
    elif fault == "complete":
        result["truncated"] = True
    elif fault == "interval":
        result["interval"]["ends_at"] = None
    elif fault == "range":
        result["range"][1] = "2026-11-11"
    elif fault == "other_family":
        result = {key: result[key] for key in ("range", "available", "excluded", "unverified", "total", "complete", "truncated", "not_read")}
    assert (core._read_parts("get_my_available_rooms", result) is not None) is (fault in {None, "empty"})


@pytest.mark.parametrize("fault", [None, "unpaired", "wrong_tool", "failed", "old", "wrong_interval"])
def test_only_matched_current_turn_room_results_are_evidence(services, fault):
    import json
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
    from catix.agent import core
    result, artifact = recommend()
    name = "get_my_available_rooms"
    call = AIMessage(content="", tool_calls=[{"name": name, "args": dict(ARGUMENTS), "id": "r"}])
    response = ToolMessage(content=json.dumps(result), name=name, tool_call_id="r", artifact=artifact)
    messages = [HumanMessage("Комнату завтра с 18 до 19"), call, response]
    if fault == "unpaired":
        response.tool_call_id = "other"
    elif fault == "wrong_tool":
        call.tool_calls[0].update(name="call_api_tool", args={"name": name, "arguments": ARGUMENTS})
        response.name = "call_api_tool"
    elif fault == "failed":
        response.status = "error"
    elif fault == "old":
        messages.append(HumanMessage("А в другой день?"))
    elif fault == "wrong_interval":
        call.tool_calls[0]["args"]["time_to"] = "20:00"
    assert core.successful_read(messages) is (fault is None)


@pytest.mark.parametrize("helper", [False, True])
def test_room_status_is_emitted_before_the_read_result(monkeypatch, helper):
    from tests.test_my_schedule import test_agenda_progress_is_shown_before_any_tool_result
    test_agenda_progress_is_shown_before_any_tool_result(monkeypatch, helper, "get_my_available_rooms")


@pytest.mark.parametrize("fault", [None, "failed", "missing_artifact", "mismatched_arguments", "later_failure", "mutation"])
def test_room_agenda_snapshot_reuse_and_invalidation(services, fault):
    import json
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
    from catix.agent.scheduling import _reads
    result, artifact = recommend()
    name = "get_my_available_rooms"
    call = AIMessage(content="", tool_calls=[{"name": name, "args": ARGUMENTS, "id": "r"}])
    response = ToolMessage(content=json.dumps(result), name=name, tool_call_id="r", artifact=deepcopy(artifact))
    messages = [HumanMessage("Комната"), call, response]
    if fault == "failed":
        response.status = "error"
    elif fault == "missing_artifact":
        response.artifact = None
    elif fault == "mismatched_arguments":
        response.artifact["room_arguments"]["time_to"] = "20:00"
    elif fault in {"later_failure", "mutation"}:
        target = name if fault == "later_failure" else "add_to_ai_calendar"
        messages.extend([AIMessage(content="", tool_calls=[{"name": target, "args": ARGUMENTS, "id": "later"}]),
                         ToolMessage(content='{"error": "unavailable"}', name=target, tool_call_id="later")])
    assert _reads(messages).get("get_my_schedule") == (artifact["agenda"] if fault is None else None)


@pytest.mark.parametrize("failed", [False, True])
def test_new_room_calendar_read_supersedes_previous_sport_offer(services, failed):
    import json
    from langchain_core.messages import AIMessage, ToolMessage
    from catix.api.signup import collect
    from tests.test_signup_offers import NOW, recommendation
    messages = recommendation()
    assert collect(messages, "Basketball", now=NOW)[0], "Control must establish an actual offer first"
    result, artifact = recommend()
    messages.extend([AIMessage(content="", tool_calls=[{"name": "get_my_available_rooms", "args": ARGUMENTS, "id": "rooms"}]),
                     ToolMessage(content=json.dumps({"error": "unavailable"} if failed else result),
                                 name="get_my_available_rooms", tool_call_id="rooms", artifact=None if failed else artifact)])
    assert collect(messages, "Basketball", now=NOW) == ([], {})
