"""When2Meet host routing, read evidence and exact consent boundaries."""

import asyncio
import json
from copy import deepcopy

import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command
from pydantic import SecretStr

from catix.agent import api_tools, core, roles
from catix.agent.tools import AgentContext
from catix.innohassle import client, token
from tests.test_roles import ScriptedModel


SLOT = "2099-01-02T10:00:00+03:00"
MEETING = {"id": "a" * 24, "slug": "team-42", "name": "Planning", "slots": [SLOT],
           "participants": [], "common_slots": [], "is_archived": False}
LIST = {"meetings": [MEETING], "total": 1, "truncated": False, "status": "active", "scope": "all"}


def messages(target, data):
    return [HumanMessage("Когда встречаемся?"), AIMessage(content="", tool_calls=[{
        "name": "call_api_tool", "args": {"name": target, "arguments": {}}, "id": "read",
    }]), ToolMessage(content=json.dumps(data), name="call_api_tool", tool_call_id="read")]


@pytest.mark.parametrize("target,data,found", [
    ("when2meet_get_my_meetings", LIST, True),
    ("when2meet_get_my_meetings", {**LIST, "meetings": [], "total": 0}, False),
    ("when2meet_get_meeting", MEETING, True),
])
def test_when2meet_reads_support_answers_without_retrieval_citations(target, data, found):
    result = messages(target, data)
    assert core.successful_read(result)
    assert core.read_evidence(result) is found
    assert not core.action_receipt(result)


@pytest.mark.parametrize("target,data", [
    ("when2meet_get_my_meetings", {**LIST, "total": 0}),
    ("when2meet_get_my_meetings", {**LIST, "truncated": True}),
    ("when2meet_get_my_meetings", {**LIST, "meetings": ["metadata"]}),
    ("when2meet_get_my_meetings", {**LIST, "error": "unavailable"}),
    ("when2meet_get_meeting", {"name": "Planning", "slots": []}),
    ("when2meet_get_meeting", {**MEETING, "participants": None}),
    ("when2meet_get_meeting", {**MEETING, "common_slots": "unknown"}),
    ("when2meet_get_meeting", {**MEETING, "error": "unavailable"}),
    ("when2meet_get_meeting", LIST),
    ("when2meet_get_my_meetings", MEETING),
    ("when2meet_create_meeting", MEETING),
])
def test_malformed_unrelated_or_failed_reads_are_not_evidence(target, data):
    result = messages(target, data)
    assert not core.successful_read(result)
    assert not core.read_evidence(result)


def test_when2meet_guidance_is_shared_and_credential_aware():
    for prompt in (roles.SUPERVISOR, roles.prompt("docs"), roles.prompt("chats")):
        assert "when2meet_get_my_meetings" in prompt
        assert "when2meet_get_meeting" in prompt
        assert "when2meet_create_meeting" in prompt
        assert "when2meet_set_my_availability" in prompt
        assert "replaces" in prompt
        assert "RFC 3339" in prompt
    assert "When2Meet" in api_tools.search_api_tools.description
    assert "When2Meet" in roles.abilities([], signed_in=True)
    assert "When2Meet" in roles.ON_THE_SITE


@pytest.fixture
def upstream(monkeypatch):
    state = {**deepcopy(MEETING), "timezone": "Europe/Moscow", "specific_time": True,
             "description": None, "owner_id": "test-user", "created_at": "2098-01-01T00:00:00Z",
             "archive_after": "2099-01-03T00:00:00Z", "archived_at": None,
             "selected_time": None, "booked_room": None, "time_range": None}
    requests = []

    def handle(request):
        assert request.headers["Authorization"] == "Bearer synthetic-user"
        requests.append((request.method, request.url.path, json.loads(request.content) if request.content else None))
        path = request.url.path
        if request.method == "POST" and path == "/when2meet/v0/meetings/":
            state.update(json.loads(request.content))
            return httpx.Response(201, json=state)
        if request.method == "PUT" and path.endswith("/participants"):
            state["participants"] = [{"user_id": "test-user", "name": "Tester",
                                      "availability": json.loads(request.content)["availability"]}]
            return httpx.Response(200, json=state)
        if request.method == "GET" and path.rsplit("/", 1)[-1] in {state["id"], state["slug"]}:
            return httpx.Response(200, json=state)
        pytest.fail(f"Unexpected upstream operation: {request.method} {path}")

    with httpx.Client(base_url="https://synthetic.invalid", transport=httpx.MockTransport(handle)) as http:
        monkeypatch.setattr(client, "_client", http)
        monkeypatch.setattr(token, "claims", lambda value: {"uid": "test-user"} if value == "synthetic-user" else None)
        monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
        monkeypatch.setattr(core, "tool_call_token", lambda: None)
        yield state, requests


MUTATIONS = [
    ("when2meet_create_meeting", {"name": "Planning", "slots": [SLOT]}),
    ("when2meet_set_my_availability", {"meeting_ref": "team-42", "availability": [SLOT]}),
    ("when2meet_set_my_availability", {"meeting_ref": "team-42", "availability": []}),
]


def action_script(target, arguments, helper=None):
    script = []
    if helper:
        script.append(AIMessage(content="", tool_calls=[{
            "name": helper, "args": {"question": "Измени опрос When2Meet."}, "id": "helper",
        }]))
    script.append(AIMessage(content="", tool_calls=[{
        "name": "call_api_tool", "args": {"name": target, "arguments": arguments}, "id": "write",
    }]))
    return [*script, *[AIMessage(content="Обработано.") for _ in range(4)]]


@pytest.mark.parametrize("target,arguments", MUTATIONS)
@pytest.mark.parametrize("helper", [None, "ask_docs", "ask_chats"])
@pytest.mark.parametrize("decision", ["approve", "reject"])
@pytest.mark.parametrize("asynchronous", [False, True])
def test_when2meet_real_protocol_waits_for_consent_and_reads_back(
    upstream, mcp_http_protocol, target, arguments, helper, decision, asynchronous,
):
    state, requests = upstream
    agent = core.build_agent(ScriptedModel(responses=action_script(target, arguments, helper)), guardrail=False)
    config = {"configurable": {"thread_id": "when2meet-consent"}}
    context = AgentContext(innohassle_token=SecretStr("synthetic-user"))

    def invoke(value):
        return (asyncio.run(agent.ainvoke(value, config, context=context)) if asynchronous
                else agent.invoke(value, config, context=context))

    invoke({"messages": [HumanMessage("Измени опрос When2Meet.")]})
    paused = agent.get_state(config).interrupts
    assert len(paused) == 1
    assert requests == [], "Confirmation cannot read upstream details or mutate"
    action = paused[0].value["action_requests"][0]
    assert action["args"] == {"name": target, "arguments": arguments}
    assert "When2Meet" in action["description"]
    if target == "when2meet_create_meeting":
        assert all(value in action["description"] for value in ("Planning", SLOT, "Europe/Moscow"))
    else:
        assert "team-42" in action["description"]
        assert ("Заменить все" if arguments["availability"] else "Очистить все") in action["description"]
    out = invoke(Command(resume={paused[0].id: {"decisions": [{"type": decision}]}}))
    assert not agent.get_state(config).interrupts
    if decision == "reject":
        assert requests == []
        assert not core.action_receipt(out["messages"])
    else:
        assert [method for method, *_ in requests] == (
            ["POST", "GET"] if target == "when2meet_create_meeting" else ["GET", "PUT", "GET"])
        assert requests[-1][1].rsplit("/", 1)[-1] in {state["id"], state["slug"]}
        assert core.action_receipt(out["messages"])
        assert core._action_receipts(out["messages"])[0]["outcome"] == "confirmed"


def test_when2meet_archive_after_approval_prevents_write(upstream, mcp_http_protocol):
    state, requests = upstream
    target, arguments = MUTATIONS[1]
    agent = core.build_agent(ScriptedModel(responses=action_script(target, arguments)), guardrail=False)
    config = {"configurable": {"thread_id": "when2meet-archive"}}
    context = AgentContext(innohassle_token=SecretStr("synthetic-user"))
    agent.invoke({"messages": [HumanMessage("Отметь время When2Meet.")]}, config, context=context)
    paused = agent.get_state(config).interrupts
    assert len(paused) == 1 and requests == []
    state["is_archived"] = True
    out = agent.invoke(Command(resume={paused[0].id: {"decisions": [{"type": "approve"}]}}), config, context=context)
    assert [method for method, *_ in requests] == ["GET"]
    result = next(json.loads(m.content) for m in out["messages"]
                  if isinstance(m, ToolMessage) and isinstance(m.content, str))
    assert result["done"] is False
    assert not core.action_receipt(out["messages"])
