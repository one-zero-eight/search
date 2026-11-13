"""When2Meet personal availability checks intervals, never writes selections."""
from copy import deepcopy
from datetime import datetime
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from catix.agent import calendar_tools
from catix.agent.tools import AgentContext, TOOLS
from catix.innohassle import mcp_client, when2meet

NAME = "get_my_available_meeting_slots"
REF = "team-poll"
DAY = "2099-01-01"
CONTEXT = AgentContext(innohassle_id="owner", innohassle_token=SecretStr("synthetic-ih"),
                       asked_at=datetime.fromisoformat("2098-12-31T12:00:00+03:00"))


def stamp(clock):
    return f"{DAY}T{clock}:00+03:00"


def poll(**changes):
    return {"id": "a" * 24, "slug": REF, "name": "Team meeting", "timezone": "Europe/Moscow",
            "specific_time": True, "slots": [stamp(t) for t in ("10:00", "10:30", "11:00", "12:00")],
            "participants": [{"user_id": "other", "availability": [stamp(t) for t in ("10:30", "11:00")]}],
            "created_at": "2098-12-31T09:00:00Z", "archive_after": stamp("13:00"), "is_archived": False,
            **changes}


def tool():
    found = next((item for item in TOOLS if item.name == NAME), None)
    assert found is not None, "Personal meeting recommendations need a registered host tool"
    return found


@pytest.fixture

def services(monkeypatch):
    state = {"poll": poll(), "external": {"range": [DAY, DAY], "schedule": [
        {"title": "Class", "starts_at": stamp("10:15"), "ends_at": stamp("10:30")}], "bookings": []},
        "local": [], "requests": []}

    def request(method, payload, token=None, **credentials):
        state["requests"].append(deepcopy(payload))
        assert method == "call_tool" and token == "synthetic-ih" and credentials == {}
        if payload["name"] == "when2meet_get_meeting":
            assert payload["arguments"] == {"meeting_ref": REF}
            return when2meet.details(when2meet.Meeting.model_validate(state["poll"]), "owner")
        assert payload["name"] == "account_get_my_schedule", "Recommendations must never write"
        assert payload["arguments"] == {"date_from": DAY, "date_to": DAY}
        return deepcopy(state["external"])

    monkeypatch.setattr(mcp_client, "request_sync", request)
    monkeypatch.setattr(calendar_tools, "events_between", lambda *a: state["local"])
    return state


def recommend():
    return tool().func(SimpleNamespace(context=CONTEXT), REF)


def test_recommendation_separates_personal_common_and_conflicts(services):
    result = recommend()
    assert [row["starts_at"] for row in result["available"]] == [stamp(t) for t in ("10:30", "11:00", "12:00")]
    assert [row["starts_at"] for row in result["common_available"]] == [stamp("10:30"), stamp("11:00")]
    assert result["excluded"][0]["starts_at"] == stamp("10:00")
    assert result["excluded"][0]["ends_at"] == stamp("10:30")
    assert result["excluded"][0]["conflicts"][0]["starts_at"] == stamp("10:15")
    assert result["available"][-1]["ends_at"] == stamp("12:30"), "Sparse slots are still half-hour cells"
    assert result["unverified"] == [] and result["complete"] is True
    assert result["participants_count"] == 1 and result["my_participation"] is False
    assert result["total"] == 4 and result["slot_duration_minutes"] == 30
    assert result["timezone"] == "Europe/Moscow" and result["page"] == f"https://innohassle.ru/when2meet/{REF}"
    assert [call["name"] for call in services["requests"]] == ["when2meet_get_meeting", "account_get_my_schedule"]


@pytest.mark.parametrize("failure", ["upstream_timeout", "mcp_timeout", "partial"])
def test_calendar_timeout_reason_reaches_meeting_recommendations(services, failure):
    if failure == "partial":
        services["external"]["source_errors"] = {"event": "upstream_timeout"}
    else:
        services["external"] = {"error": "private diagnostic", "code": failure}
    result = recommend()
    expected = {"innohassle.event": "upstream_timeout"} if failure == "partial" else {"innohassle": failure}
    assert result["source_errors"] == expected
    assert result["complete"] is False and not result["available"] and result["unverified"]
    assert len(result["excluded"]) == (1 if failure == "partial" else 0)
    assert "private diagnostic" not in str(result)
    assert len(services["requests"]) == 2


@pytest.mark.parametrize("fault", ["partial", "failed", "truncated", "malformed_event"])
def test_incomplete_calendars_preserve_known_conflicts_but_never_prove_free_time(services, fault):
    if fault == "partial":
        services["external"]["not_read"] = ["class: missing feed"]
    elif fault == "failed":
        services["external"] = {"error": "unavailable"}
    elif fault == "truncated":
        services["external"]["truncated"] = True
    else:
        services["external"]["schedule"].append({"starts_at": stamp("09:00"), "ends_at": "invalid"})
    result = recommend()
    assert result["available"] == result["common_available"] == []
    assert result["complete"] is False and result["not_read"]
    assert len(result["excluded"]) == (0 if fault == "failed" else 1)
    assert len(result["unverified"]) == (4 if fault == "failed" else 3)


def test_unknown_end_is_not_a_source_failure_and_only_blocks_later_cells(services):
    services["external"]["schedule"] = []
    services["local"] = [{"title": "Personal meeting", "starts_at": stamp("11:00"), "ends_at": None}]
    result = recommend()
    assert [row["starts_at"] for row in result["available"]] == [stamp("10:00"), stamp("10:30")]
    assert len(result["unverified"]) == 2 and result["not_read"] == []
    assert result["unverified"][0]["unknown_duration_events"][0]["ends_at"] is None


@pytest.mark.parametrize("people, expected", [([], []),
    ([{"user_id": "other", "availability": []}], []),
    ([{"user_id": "owner", "availability": [stamp("11:00")]},
      {"user_id": "other", "availability": [stamp("10:30"), stamp("11:00")]}], [stamp("11:00")])])
def test_common_respects_all_respondents_including_my_saved_answer(services, people, expected):
    services["poll"]["participants"] = people
    result = recommend()
    assert [row["starts_at"] for row in result["common_available"]] == expected
    assert len(result["available"]) == 3, "Saved selections must not restrict newly calculated personal availability"


def test_all_day_ai_calendar_blocks_every_cell(services):
    services["local"] = [{"title": "Away", "starts_at": stamp("09:00"), "ends_at": None, "all_day": True}]
    result = recommend()
    assert not result["available"] and not result["unverified"]
    assert len(result["excluded"]) == 4


def test_utc_slots_and_common_slots_are_compared_as_instants(services):
    services["poll"]["slots"] = [f"{DAY}T07:00:00Z", f"{DAY}T07:30:00Z"]
    result = recommend()
    assert result["available"] == result["common_available"] == [
        {"starts_at": stamp("10:30"), "ends_at": stamp("11:00")}]


@pytest.mark.parametrize("fault", ["wrong_id", "wrong_slug", "naive", "missing_slots", "count", "common_count", "page", "error", "transport"])
def test_bad_or_failed_poll_never_reaches_calendar(monkeypatch, services, fault):
    data = when2meet.details(when2meet.Meeting.model_validate(services["poll"]), "owner")
    reference = REF
    if fault == "wrong_id":
        reference = "b" * 24
    elif fault == "wrong_slug":
        data["slug"] = "different"
    elif fault == "naive":
        data["slots"][0] = f"{DAY}T10:00:00"
    elif fault == "missing_slots":
        data.pop("slots")
    elif fault == "count":
        data["slots_count"] = 999
    elif fault == "common_count":
        data["common_slots_count"] = 999
    elif fault == "page":
        data["page"] = "https://example.test/wrong"
    elif fault == "error":
        data = {"error": "upstream unavailable"}
    def request(method, payload, *a, **kw):
        assert payload["name"] == "when2meet_get_meeting", "An invalid poll cannot define calendar dates"
        if fault == "transport":
            raise RuntimeError("not for user output")
        return data
    monkeypatch.setattr(mcp_client, "request_sync", request)
    result = tool().func(SimpleNamespace(context=CONTEXT), reference)
    assert result["code"] == "meeting_unverified" and "error" in result
    assert "not for user output" not in str(result)


def test_credentials_are_required_before_any_io(monkeypatch):
    monkeypatch.setattr(mcp_client, "request_sync", lambda *a, **kw: pytest.fail("No credentials"))
    assert "error" in tool().func(SimpleNamespace(context=AgentContext()), REF)


@pytest.mark.parametrize("arguments", [{}, {"meeting_ref": "https://innohassle.ru/when2meet/abc"},
    {"meeting_ref": "../abc"}, {"meeting_ref": REF, "owner": "other"}, {"meeting_ref": REF, "duration_minutes": 60}])
def test_schema_exposes_only_literal_meeting_reference(arguments):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        tool().args_schema.model_validate(arguments)


@pytest.mark.parametrize("mode", ["empty", "archived", "past", "too_wide"])
def test_unactionable_polls_do_not_fetch_calendar(services, mode):
    if mode == "empty":
        services["poll"]["slots"] = []
    elif mode == "archived":
        services["poll"]["is_archived"] = True
    elif mode == "past":
        services["poll"]["slots"] = ["2098-12-30T10:00:00+03:00"]
    else:
        services["poll"]["slots"].append("2099-12-01T10:00:00+03:00")
    result = recommend()
    assert not result["available"] and not result["common_available"]
    assert len(services["requests"]) == 1
    assert bool(result["unverified"]) is (mode == "too_wide")
    assert bool(result["excluded"]) is (mode in {"past", "archived"})
    assert result["complete"] is (mode != "too_wide")


def test_off_grid_cell_is_unverified_not_rounded(services):
    services["poll"]["slots"].append(stamp("12:15"))
    result = recommend()
    assert result["unverified"] == [{"starts_at": stamp("12:15"), "ends_at": stamp("12:45"), "reason": "unsupported_slot"}]
    assert result["complete"] is False


def test_specific_time_false_is_still_a_timed_daily_range(services):
    services["poll"]["specific_time"] = False
    result = recommend()
    assert len(result["available"]) == 3 and result["complete"] is True


def test_projection_limits_do_not_turn_partial_slots_into_an_exhaustive_answer(monkeypatch, services):
    monkeypatch.setattr(when2meet, "MAX_SHOWN_SLOTS", 2)
    result = recommend()
    assert result["total"] == 2 and result["slots_count"] == 4
    assert result["truncated"] is True and result["complete"] is False and result["poll_complete"] is False
    assert result["not_read"] and len(result["available"]) == 1


def test_common_is_computed_before_participant_projection_limit(services):
    services["poll"]["participants"] = [{"user_id": str(i), "availability": services["poll"]["slots"]} for i in range(45)]
    services["poll"]["participants"][-1]["availability"] = [stamp("11:00")]
    result = recommend()
    assert result["participants_count"] == 45
    assert [row["starts_at"] for row in result["common_available"]] == [stamp("11:00")]
    assert result["poll_complete"] is True, "Participant names/details are not required to trust server-computed common slots"


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("role", ["root", "docs", "chats"])
def test_actual_graph_exposes_read_without_approval_or_writes(monkeypatch, services, asynchronous, role):
    import asyncio
    import json
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
    from catix.agent import core, roles
    from catix.common.status import STATUS
    from tests.test_roles import ScriptedModel

    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    assert NAME in roles.MAIN_TOOLS and all(NAME in item.tools for item in roles.ROLES.values())
    assert NAME in STATUS and NAME in roles.MCP_RULES
    script = []
    if role != "root":
        script.append(AIMessage(content="", tool_calls=[{"name": "ask_" + role, "args": {"question": "Проверь опрос team-poll по моему календарю"}, "id": "helper"}]))
    script.extend([
        AIMessage(content="", tool_calls=[{"name": NAME, "args": {"meeting_ref": REF}, "id": "meeting"}]),
        AIMessage(content="В опросе Team meeting вам подходят 10:30–11:00, 11:00–11:30 и 12:00–12:30. Первые два варианта отметили все ответившие."),
    ])
    if role != "root":
        script.append(AIMessage(content="Вам подходят 10:30–11:00, 11:00–11:30 и 12:00–12:30."))
    graph = core.build_agent(ScriptedModel(responses=script), guardrail=False)
    config = {"configurable": {"thread_id": f"meeting-{role}-{asynchronous}"}}
    inputs = {"messages": [HumanMessage("Какие варианты в When2Meet team-poll подходят мне по расписанию?")]}
    out = asyncio.run(graph.ainvoke(inputs, config, context=CONTEXT)) if asynchronous else graph.invoke(inputs, config, context=CONTEXT)
    assert not graph.get_state(config).interrupts
    assert len(services["requests"]) == 2
    if role == "root":
        message = next(m for m in out["messages"] if isinstance(m, ToolMessage))
        assert isinstance(message.content, str)
        assert message.status == "success" and json.loads(message.content)["common_available"]
        assert core.successful_read(out["messages"]) and core.read_evidence(out["messages"])
    else:
        helper = next(m for m in out["messages"] if isinstance(m, ToolMessage) and m.name == "ask_" + role)
        assert helper.status == "success" and "10:30" in helper.content


@pytest.mark.parametrize("fault", [None, "empty", "partial", "count", "common", "duration", "complete", "other_shape"])
def test_evidence_accepts_real_results_and_rejects_malformed_envelopes(services, fault):
    from catix.agent import core
    if fault == "empty":
        services["poll"]["slots"] = []
    elif fault == "partial":
        services["external"]["not_read"] = ["class: missing"]
    result = recommend()
    if fault == "count":
        result["total"] = 999
    elif fault == "common":
        result["common_available"].append({"starts_at": stamp("16:00"), "ends_at": stamp("16:30")})
    elif fault == "duration":
        result["slot_duration_minutes"] = 60
    elif fault == "complete":
        result["truncated"] = True
    elif fault == "other_shape":
        result = services["external"]
    assert (core._read_parts(NAME, result) is not None) is (fault in {None, "empty", "partial"})


def test_read_evidence_is_paired_to_exact_requested_poll(services):
    import json
    from langchain_core.messages import AIMessage, ToolMessage
    from catix.agent import core
    result = recommend()
    messages = [AIMessage(content="", tool_calls=[{"name": NAME, "args": {"meeting_ref": "different"}, "id": "read"}]),
                ToolMessage(content=json.dumps(result), name=NAME, tool_call_id="read")]
    assert not core.successful_read(messages)


def test_local_midnight_uses_moscow_date_and_does_not_read_next_day(services):
    services["poll"]["slots"] = ["2098-12-31T21:00:00Z", "2099-01-01T20:30:00Z"]
    services["poll"]["participants"] = []
    services["external"]["schedule"] = [{"title": "Late class", "starts_at": "2098-12-31T20:45:00Z",
                                         "ends_at": "2098-12-31T21:15:00Z"}]
    result = recommend()
    assert result["range"] == [DAY, DAY]
    assert result["excluded"][0]["starts_at"] == stamp("00:00")
    assert result["available"] == [{"starts_at": stamp("23:30"), "ends_at": "2099-01-02T00:00:00+03:00"}]
    assert services["requests"][-1]["arguments"] == {"date_from": DAY, "date_to": DAY}


@pytest.mark.model
@pytest.mark.parametrize("incomplete", [False, True])
def test_live_model_routes_to_meeting_read_without_writes(monkeypatch, services, incomplete):
    import json
    import re
    import httpx
    from langchain_core.messages import AIMessage, HumanMessage
    from langchain_openai import ChatOpenAI
    from catix.agent import core
    from catix.settings import settings

    if incomplete:
        services["external"]["not_read"] = ["class: unavailable"]
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    monkeypatch.setattr(settings, "agent_max_model_calls", 3)
    offered = []
    def inspect_request(request):
        body = json.loads(request.content)
        names = [item["function"]["name"] for item in body.get("tools", [])]
        offered.append(names)
        print({"offered_tools": names, "tool_choice": body.get("tool_choice")})
    model = ChatOpenAI(base_url=str(settings.llm_route), api_key=SecretStr("not-needed"), model=settings.llm_model,
                       max_completion_tokens=900, temperature=0, timeout=60, max_retries=0,
                       http_client=httpx.Client(event_hooks={"request": [inspect_request]}),
                       extra_body={"chat_template_kwargs": {"enable_thinking": False}})
    graph = core.build_agent(model, guardrail=False)
    config = {"configurable": {"thread_id": f"meeting-model-{incomplete}"}}
    out = graph.invoke({"messages": [HumanMessage("Какие варианты встречи в When2Meet team-poll подходят мне по расписанию и какие из них отметили все ответившие? Ничего не отмечай.")]}, config, context=CONTEXT)
    calls = [call for message in out["messages"] if isinstance(message, AIMessage) for call in message.tool_calls]
    answer = core.final_answer(out["messages"], {}).answer
    print({"calls": calls, "answer": answer})
    assert offered and NAME in offered[0], "The live model must actually be offered the new native tool"
    assert len(calls) == 1 and calls[0]["name"] == NAME and calls[0]["args"] == {"meeting_ref": REF}
    assert len(services["requests"]) == 2 and not graph.get_state(config).interrupts
    if incomplete:
        assert any(word in answer.lower() for word in ("непол", "недоступ", "не удалось", "не могу", "провер"))
        assert not re.search(r"(?:свободны|подходят)[:\s*]*10:30", answer, re.IGNORECASE)
    else:
        assert all(clock in answer for clock in ("10:30", "11:00", "12:00"))
        assert any(word in answer.lower() for word in ("ответивш", "участник"))
        assert "10:15" in answer and not re.search(r"11:30\s*[–—-]\s*12:00", answer)
