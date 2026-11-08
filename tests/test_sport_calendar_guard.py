"""Replay the overlapping Sport choice from trace 55c00961401c192a27e90457659ceef1.

Only synthetic MCP responses and local calendar data; never a real signup.
"""

import asyncio
import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.runtime import Runtime
from pydantic import SecretStr

from catix.agent import api_tools
from catix.agent.api_preflight import ApiPreflightMiddleware
from catix.agent.tools import AgentContext

DAY = "2026-11-09"
PERIOD = {"date_from": DAY, "date_to": DAY}
SCHEMA = {"type": "object", "additionalProperties": False,
          "properties": {"training_id": {"type": "integer", "minimum": 1},
                         "cancel": {"type": "boolean", "default": False}}, "required": ["training_id"]}
CONTEXT = AgentContext(innohassle_id="synthetic-owner", innohassle_token=SecretStr("synthetic-ih"),
                       sport_token=SecretStr("synthetic-sport"))
RUNTIME = Runtime(context=CONTEXT)


def interval(start, end, **fields):
    return {"starts_at": f"{DAY}T{start}:00+03:00", "ends_at": f"{DAY}T{end}:00+03:00", **fields}


FRISBEE = interval("08:00", "10:00", training_id=48591, name="Frisbee", date=DAY + " Mon",
                   time="08:00-10:00", place="[SC] Big Hall", checked_in=False, can_check_in=True)
BASKETBALL = interval("17:00", "18:30", training_id=46975, name="Basketball", date=DAY + " Mon",
                      time="17:00-18:30", place="[SC] Big Hall", checked_in=False, can_check_in=True)
CLASS = interval("09:00", "10:30", title="Logic and Discrete Math (lec)", kind="class")


def read_messages(name, data, ident, arguments=None):
    local = name in {"get_my_ai_calendar", "get_my_schedule"}
    return [AIMessage(content="", tool_calls=[{
        "name": name if local else "call_api_tool", "id": ident,
        "args": (arguments or PERIOD) if local else {"name": name, "arguments": arguments or PERIOD},
    }]), ToolMessage(content=json.dumps(data), name=name if local else "call_api_tool", tool_call_id=ident)]


def action(training_id=48591, cancel=None, ident="write"):
    args = {"training_id": training_id}
    if cancel is not None:
        args["cancel"] = cancel
    return {"name": "call_api_tool", "id": ident,
            "args": {"name": "sport_sport_checkin", "arguments": args}}


def agenda_data(classes=None, events=None):
    from catix.agent.schedule_tools import merge_schedule

    return merge_schedule([DAY, DAY], {"range": [DAY, DAY], "schedule": [CLASS] if classes is None else classes, "bookings": []},
                          {"range": [DAY, DAY], "events": events or []})


def history(classes=None, events=None, training_id=48591):
    return {"messages": [HumanMessage("Запиши завтра на тренировку без пересечений с занятиями."),
        AIMessage(content="", tool_calls=[{"name": "search_api_tools", "id": "schema", "args": {"query": "sport"}}]),
        ToolMessage(content=json.dumps({"tools": [{"name": "sport_sport_checkin", "inputSchema": SCHEMA}]}),
                    name="search_api_tools", tool_call_id="schema"),
        *read_messages("get_my_schedule", agenda_data(classes, events), "agenda"),
        *read_messages("sport_get_sport_trainings", {"range": [DAY, DAY], "trainings": [FRISBEE, BASKETBALL]}, "sport"),
        AIMessage(content="", tool_calls=[action(training_id)])]}


def prepare(state, asynchronous=False):
    middleware = ApiPreflightMiddleware()
    return (asyncio.run(middleware.aafter_model(state, RUNTIME)) if asynchronous
            else middleware.after_model(state, RUNTIME))


@pytest.mark.parametrize("asynchronous", [False, True])
def test_trace_frisbee_overlap_cannot_reach_ordinary_approval(monkeypatch, asynchronous):
    monkeypatch.setattr(api_tools.mcp_client, "request_sync", lambda *a, **kw: pytest.fail("All reads are present"))
    state = history()
    original = deepcopy(state)
    result = prepare(state, asynchronous)
    assert result.get("jump_to") == "model", "08:00–10:00 overlaps the 09:00 class: do not offer approval"
    assert result["api_prepared"] == []
    feedback = json.loads(result["messages"][0].content)
    assert feedback["code"] == "schedule_conflict"
    assert feedback["done"] is False
    assert feedback["conflicts"][0]["title"] == CLASS["title"]
    assert [t["training_id"] for t in feedback["alternatives"]] == [46975]
    assert state == original


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("change,expected_writes", [("none", 1), ("new_class", 0), ("new_local", 0),
                                                    ("moved", 0), ("unavailable", 0), ("failed", 0)])
def test_approved_training_is_rechecked_before_the_only_write(monkeypatch, asynchronous, change, expected_writes):
    from catix.agent import calendar_tools, core
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.types import Command
    from tests.test_mcp_preflight_graph import ObservedModel

    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    log = []
    training = deepcopy(BASKETBALL)
    external = {"range": [DAY, DAY], "schedule": [CLASS], "bookings": []}
    local = []

    def request(method, payload, token=None, **credentials):
        name = payload.get("name")
        log.append(name)
        assert method == "call_tool" and token == "synthetic-ih"
        if name == "sport_get_sport_trainings":
            assert credentials == {"sport_token": "synthetic-sport"}
            assert payload["arguments"] == PERIOD
            return {"range": [DAY, DAY], "trainings": [training]}
        if name == "account_get_my_schedule":
            assert credentials == {} and payload["arguments"] == PERIOD
            if change == "failed":
                raise RuntimeError("synthetic private diagnostic")
            return external
        assert name == "sport_sport_checkin"
        assert payload["arguments"] == {"training_id": 46975}
        return {"done": True, "training_id": 46975, "signed_up": True}

    async def arequest(*a, **kw):
        return request(*a, **kw)

    def local_events(key, start, end):
        log.append("get_my_ai_calendar")
        assert str(start) == DAY and str(end) == DAY
        return local

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    monkeypatch.setattr(api_tools.mcp_client, "request", arequest)
    monkeypatch.setattr(calendar_tools, "events_between", local_events)
    saver = InMemorySaver()
    model = ObservedModel(responses=[AIMessage(content="", tool_calls=[action(46975)]), AIMessage(content="Проверено.")])
    agent = core.build_agent(model, guardrail=False, checkpointer=saver)
    config = {"configurable": {"thread_id": "sport-recheck"}}
    inputs = history(training_id=46975)
    inputs["messages"].pop()  # The model, not a fabricated history entry, requests this write.

    def invoke(value):
        return asyncio.run(agent.ainvoke(value, config, context=CONTEXT)) if asynchronous else agent.invoke(value, config, context=CONTEXT)

    invoke(inputs)
    paused = agent.get_state(config)
    assert len(paused.interrupts) == 1 and log == []
    description = paused.interrupts[0].value["action_requests"][0]["description"]
    assert all(text in description for text in ("Basketball", DAY, "17:00", "18:30"))
    if change == "new_class":
        external["schedule"].append(interval("17:30", "19:00", title="New class"))
    elif change == "new_local":
        local.append(interval("17:30", "19:00", title="New appointment"))
    elif change == "moved":
        training.update(interval("18:00", "19:30"))
    elif change == "unavailable":
        training["can_check_in"] = False
    # Rebuild over the checkpoint: no transient instance state can authorize the write.
    agent = core.build_agent(model, guardrail=False, checkpointer=saver)
    out = invoke(Command(resume={paused.interrupts[0].id: {"decisions": [{"type": "approve"}]}}))
    assert log.count("sport_sport_checkin") == expected_writes
    if expected_writes:
        assert log == ["sport_get_sport_trainings", "account_get_my_schedule", "get_my_ai_calendar", "sport_sport_checkin"]
    else:
        result = next(json.loads(m.content) for m in out["messages"] if isinstance(m, ToolMessage)
                      and isinstance(m.content, str) and m.tool_call_id == "write")
        assert result["done"] is False and "synthetic private diagnostic" not in str(result)


@pytest.mark.parametrize("event,code", [
    (interval("06:00", "08:00", title="Ends at training start"), None),
    (interval("10:00", "11:00", title="Starts at training end"), None),
    (interval("07:00", "11:00", title="Contains training"), "schedule_conflict"),
    (interval("08:30", "09:00", title="Inside training"), "schedule_conflict"),
    ({"starts_at": DAY + "T06:00:00Z", "ends_at": DAY + "T07:00:00Z"}, "schedule_conflict"),
    ({"starts_at": DAY + "T09:00:00", "ends_at": DAY + "T10:00:00"}, "schedule_unverified"),
    ({"starts_at": DAY + "T09:00:00+03:00", "ends_at": None}, "schedule_unverified"),
    ({"starts_at": DAY + "T12:00:00+03:00", "ends_at": None, "all_day": True}, "schedule_conflict"),
])
def test_interval_boundaries_offsets_and_unknown_durations(event, code):
    result = prepare(history(classes=[], events=[event]))
    if code:
        assert result.get("jump_to") == "model"
        assert json.loads(result["messages"][0].content)["code"] == code
    else:
        assert "jump_to" not in result


@pytest.mark.parametrize("fault", ["missing_external", "missing_local", "partial", "truncated", "malformed",
                                  "old_turn", "unpaired", "wrong_source", "failed_latest", "wrong_period",
                                  "no_training_end", "duplicate_training"])
def test_missing_or_untrusted_data_never_means_free(fault, monkeypatch):
    from catix.agent import schedule_tools

    monkeypatch.setattr(schedule_tools, "read_my_schedule", lambda *a: {"error": "Fresh read unavailable"})
    state = history(classes=[])
    message = state["messages"][4]
    agenda = json.loads(message.content)
    if fault == "missing_external":
        del agenda["sources"]["innohassle"]
    elif fault == "missing_local":
        del agenda["sources"]["ai_calendar"]
    elif fault == "partial":
        agenda.update(complete=False, not_read=["innohassle: class failed"])
    elif fault == "truncated":
        agenda.update(complete=False, truncated=True)
    elif fault == "old_turn":
        state["messages"].insert(-1, HumanMessage("Теперь запиши."))
    elif fault == "unpaired":
        message.tool_call_id = "not-agenda"
    elif fault == "wrong_source":
        state["messages"][3].tool_calls[0]["name"] = "get_my_ai_calendar"
        message.name = "get_my_ai_calendar"
    elif fault == "failed_latest":
        state["messages"][-1:-1] = read_messages("get_my_schedule", {"error": "Unavailable"}, "latest")
    elif fault == "wrong_period":
        agenda["range"] = ["2026-11-10", "2026-11-10"]
    elif fault == "no_training_end":
        state["messages"][6].content = json.dumps({"range": [DAY, DAY], "trainings": [{**FRISBEE, "ends_at": None}]})
    elif fault == "duplicate_training":
        state["messages"][6].content = json.dumps({"range": [DAY, DAY], "trainings": [FRISBEE, FRISBEE]})
    message.content = "not JSON" if fault == "malformed" else json.dumps(agenda)
    result = prepare(state)
    assert result.get("jump_to") == "model" and result["api_prepared"] == []
    assert json.loads(result["messages"][0].content)["code"] == "schedule_unverified"


@pytest.mark.parametrize("asynchronous", [False, True])
def test_unprepared_signup_cannot_bypass_guard_and_cancel_is_not_blocked(monkeypatch, asynchronous):
    sent = []
    monkeypatch.setattr(api_tools.mcp_client, "request_sync", lambda *a, **kw: sent.append(a) or {"done": True})

    async def request(*a, **kw):
        return api_tools.mcp_client.request_sync(*a, **kw)

    monkeypatch.setattr(api_tools.mcp_client, "request", request)
    runtime = SimpleNamespace(context=CONTEXT)
    def call(arguments):
        return (asyncio.run(api_tools.call_api_tool.coroutine("sport_sport_checkin", runtime, arguments)) if asynchronous
                else api_tools.call_api_tool.func("sport_sport_checkin", runtime, arguments))
    result = call({"training_id": 46975})
    assert result["done"] is False and result["code"] == "schedule_unverified" and not sent
    assert call({"training_id": 46975, "cancel": True}) == {"done": True}
    assert len(sent) == 1


def test_planning_rules_distinguish_signup_eligibility_from_personal_availability():
    from catix.agent import roles

    assert "can_check_in is NOT personal availability" in roles.MCP_RULES
    assert "Before planning" in roles.MCP_RULES
    assert "schedule_conflict" in roles.MCP_RULES


@pytest.mark.parametrize("asynchronous", [False, True])
def test_host_reads_combined_agenda_when_the_model_omitted_it(monkeypatch, asynchronous):
    from catix.agent import calendar_tools

    read = []
    def events(key, start, end):
        read.append((key, str(start), str(end)))
        return [interval("08:30", "09:00", title="Personal meeting")]
    monkeypatch.setattr(calendar_tools, "events_between", events)
    monkeypatch.setattr(api_tools.mcp_client, "request_sync", lambda *a, **kw: {"range": [DAY, DAY], "schedule": [], "bookings": []})
    state = history(classes=[])
    state["messages"][3:5] = []
    result = prepare(state, asynchronous)
    assert read and read[0][1:] == (DAY, DAY)
    assert json.loads(result["messages"][0].content)["code"] == "schedule_conflict"


def test_two_overlapping_signups_cannot_pass_in_one_batch():
    state = history(classes=[])
    second = {**FRISBEE, "training_id": 99, "name": "Other training"}
    state["messages"][6].content = json.dumps({"range": [DAY, DAY], "trainings": [FRISBEE, second]})
    state["messages"][-1].tool_calls.append(action(99, ident="second-write"))
    result = prepare(state)
    assert result.get("jump_to") == "model" and result["api_prepared"] == []
    assert len(result["messages"]) == 2
    assert all(json.loads(m.content)["code"] == "schedule_conflict" for m in result["messages"])


def test_legacy_capped_local_calendar_does_not_prove_availability():
    result = prepare(history(classes=[], events=[interval("11:00", "12:00")] * 40))
    assert result.get("jump_to") == "model"
    assert json.loads(result["messages"][0].content)["code"] == "schedule_unverified"
