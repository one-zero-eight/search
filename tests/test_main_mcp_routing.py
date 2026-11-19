"""Deterministic supervisor/helper graphs for direct, read-only MCP access."""

import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from catix.agent import api_tools, core, roles
from catix.agent.tools import AgentContext
from tests.mcp_native_helpers import call as native_call
from tests.test_roles import ScriptedModel


def call(name, args, ident):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": ident}])


def run(script, context=None, question="Где аудитория?"):
    model = ScriptedModel(responses=script)
    agent = core.build_agent(model, guardrail=False)
    output = agent.invoke({"messages": [HumanMessage(question)]},
                          {"configurable": {"thread_id": "direct-mcp"}},
                          context=context or AgentContext())
    return output


@pytest.fixture
def public_read(monkeypatch):
    sent = []

    def request(name, arguments, *args, **kwargs):
        sent.append((name, arguments))
        if name == "search_tools":
            return {"tools": [{"name": "maps_find_room", "inputSchema": {"type": "object"}}]}
        return {"areas": [{"title": "301", "where": "third floor"}], "total": 1}

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    return sent


def test_supervisor_discovers_and_reads_without_a_campus_helper(public_read):
    out = run([
        call("search_api_tools", {"query": "room 301"}, "s1"),
        call("call_api_tool", {"name": "maps_find_room", "arguments": {"query": "301"}}, "s2"),
        AIMessage(content="Аудитория 301 на третьем этаже."),
    ])
    results = [m for m in out["messages"] if isinstance(m, ToolMessage)]
    assert [name for name, _ in public_read] == ["search_tools", "call_tool"]
    assert [m.name for m in results] == ["search_api_tools", "call_api_tool"]
    assert json.loads(results[-1].content)["areas"][0]["title"] == "301"
    assert "campus" not in roles.ROLES
    assert core.final_answer(out["messages"], {}).answer == "Аудитория 301 на третьем этаже."


@pytest.mark.parametrize("helper", ["docs", "chats"])
def test_remaining_helpers_read_mcp_without_forcing_a_citation_or_fallback(public_read, helper):
    out = run([
        call(f"ask_{helper}", {"question": "Где аудитория?"}, "h1"),
        call("search_api_tools", {"query": "room 301"}, "s1"),
        call("call_api_tool", {"name": "maps_find_room", "arguments": {"query": "301"}}, "s2"),
        AIMessage(content="Аудитория 301 на третьем этаже."),
        AIMessage(content="Аудитория 301 на третьем этаже."),
    ])
    reports = [m for m in out["messages"] if isinstance(m, ToolMessage)]
    assert [m.name for m in reports] == [f"ask_{helper}"]
    assert [name for name, _ in public_read] == ["search_tools", "call_tool"]
    assert reports[0].artifact["found"] is True
    assert reports[0].artifact["read_found"] is True
    assert "[m" not in out["messages"][-1].text


@pytest.mark.parametrize("payload", [
    {"error": "unavailable", "rooms": [{"name": "301"}]},
    {"rooms": [], "total": 0},
    {"tools": [{"name": "maps_find_room"}]},
    {"note": "No matches"},
    {"total": 12, "truncated": True},
])
def test_mcp_metadata_errors_and_empty_results_are_not_found_evidence(payload):
    message = ToolMessage(content=json.dumps(payload), name="call_api_tool", tool_call_id="r1")
    assert core.found_anything([message]) is not True




@pytest.mark.parametrize("role", [None, "docs", "chats"])
def test_prompts_keep_trusted_group_without_course_glossary(monkeypatch, role):
    from langchain.agents.middleware import ModelRequest
    from langgraph.runtime import Runtime

    monkeypatch.setattr(core.courses, "courses", lambda: (
        core.courses.Course("ITP", "Introduction to Programming", ("итп",)),
        core.courses.Course("CA", "Computer Architecture", ("компарх", "компарч")),
    ))
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    seen = []
    request = ModelRequest(model=ScriptedModel(responses=[AIMessage(content="ok")]),
                           messages=[HumanMessage("Мои пары завтра")], tools=[],
                           state={"messages": []}, runtime=Runtime(context=AgentContext(study_group="B26-CSE-01")))
    core.prompt_for(role).wrap_model_call(request, seen.append)
    text = seen[0].system_message.text
    assert "study group is B26-CSE-01" in text
    assert "never ask for it" in text
    assert "Courses (use these names" not in text
    assert "ITP = Introduction to Programming" not in text
    assert "CA = Computer Architecture" not in text

    # Only the subject mentioned in the question is decoded, outside the system prompt.
    question = request.override(messages=[HumanMessage("Когда мидтерм по компарчу?")])
    hinted = core.QuestionNoteMiddleware(hint=True)._with_hint(question)
    assert "CA = Computer Architecture" in hinted.messages[0].content
    assert "ITP = Introduction to Programming" not in hinted.messages[0].content
    assert question.messages[0].content == "Когда мидтерм по компарчу?"
    assert {"компарх", "компарч"} <= set(core.store._words("компарч").split())


def test_api_identifiers_cannot_resurrect_old_citations():
    messages = [HumanMessage("Где аудитория?"),
                ToolMessage(content='{"rooms": [{"id": "m0", "name": "301"}]}',
                            name="call_api_tool", tool_call_id="r1"),
                AIMessage(content="Аудитория 301 [m0].")]
    old = {"m0": {"wiki": True, "title": "Old unrelated page", "link": None, "trust": "official"}}
    answer = core.final_answer(messages, old).answer
    assert "Old unrelated page" not in answer and "[1]" not in answer


def test_failed_helpers_do_not_discard_a_successful_direct_read():
    messages = [HumanMessage("Где аудитория и есть ли объявления?"),
                call("call_api_tool", {"name": "maps_find_room", "arguments": {"query": "301"}}, "r1"),
                ToolMessage(content='{"total": 1, "areas": [{"title": "301"}]}', name="call_api_tool", tool_call_id="r1"),
                ToolMessage(content=core.TOOL_FAILURE_ANSWER, name="ask_chats", tool_call_id="h1"),
                AIMessage(content="Аудитория 301. Объявления проверить не удалось.")]
    assert core.final_answer(messages, {}).answer == messages[-1].text
    messages[2] = ToolMessage(content='{"error": "unavailable"}', name="call_api_tool", tool_call_id="r1")
    assert core.final_answer(messages, {}).answer == core.TOOL_FAILURE_ANSWER


@pytest.mark.parametrize("kind", ["schedule", "bot_calendar"])
def test_empty_calendar_read_survives_failed_helper_in_full_graph(mcp_http_protocol, monkeypatch, kind):
    from catix.agent import calendar_tools
    from catix.innohassle import client

    day, group = "2026-11-08", "B26-CSE-01"
    context = AgentContext(study_group=group, user_telegram_id=123)
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    if kind == "schedule":
        monkeypatch.setattr(client, "event_groups", lambda: [{"name": group, "alias": group}])
        monkeypatch.setattr(client, "group_schedule_ics",
                            lambda alias: "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n")
        direct = call("call_api_tool", {"name": "schedule_get_schedule",
                      "arguments": {"group": group, "date_from": day, "date_to": day}}, "r1")
        answer = "Пар нет. Объявления проверить не удалось."
        empty_key = "classes"
    else:
        monkeypatch.setattr(calendar_tools.personal_calendar, "telegram_key", lambda uid: "account:bot")
        monkeypatch.setattr(calendar_tools, "events_between", lambda key, start, end: [])
        direct = call("get_my_ai_calendar", {"date_from": day, "date_to": day}, "r1")
        answer = "В личном календаре событий нет. Объявления проверить не удалось."
        empty_key = "events"
    out = run([direct, call("ask_chats", {"question": "Есть ли объявления?"}, "h1"),
               AIMessage(content=core.TOOL_FAILURE_ANSWER), AIMessage(content=answer)], context=context)
    results = [m for m in out["messages"] if isinstance(m, ToolMessage)]
    payload = json.loads(results[0].content)
    assert payload[empty_key] == [] and payload["range"] == [day, day]
    assert results[1].content == core.TOOL_FAILURE_ANSWER
    assert core.successful_read(out["messages"]) is True
    assert core.read_evidence(out["messages"]) is False  # Empty reads still leave retrieval fallback available.
    assert core.final_answer(out["messages"], {}).answer == answer


@pytest.mark.parametrize("tool_name,changes,status", [
    ("call_api_tool", {"error": "unavailable"}, "success"),
    ("call_api_tool", {}, "error"),
    ("call_api_tool", {"schedule": ""}, "success"),
    ("call_api_tool", {"total": 1}, "success"),
    ("call_api_tool", {"total": False}, "success"),
    ("call_api_tool", {"classes": None}, "success"),
    ("call_api_tool", {"range": []}, "success"),
    ("call_api_tool", {"range": ["2026-02-30", "2026-02-30"]}, "success"),
    ("call_api_tool", {"range": ["2026-11-09", "2026-11-08"]}, "success"),
    ("search_api_tools", {}, "success"),
    ("get_my_ai_calendar", {"error": "not linked"}, "success"),
    ("get_my_ai_calendar", {}, "error"),
    ("get_my_ai_calendar", {"range": None}, "success"),
    ("get_my_ai_calendar", {"events": None}, "success"),
])
def test_failed_or_malformed_empty_reads_do_not_hide_helper_failure(tool_name, changes, status):
    payload = {"range": ["2026-11-08", "2026-11-08"]}
    payload.update({"events": []} if tool_name == "get_my_ai_calendar" else
                   {"schedule": "B26-CSE-01", "total": 0, "classes": []})
    payload.update(changes)
    messages = [HumanMessage("Есть ли пары и объявления?"),
                call(tool_name, {"name": "schedule_get_schedule", "arguments": {}} if tool_name == "call_api_tool" else {}, "r1"),
                ToolMessage(content=json.dumps(payload), name=tool_name, tool_call_id="r1", status=status),
                ToolMessage(content=core.TOOL_FAILURE_ANSWER, name="ask_chats", tool_call_id="h1"),
                AIMessage(content="Пар нет. Объявления проверить не удалось.")]
    assert core.final_answer(messages, {}).answer == core.TOOL_FAILURE_ANSWER


@pytest.mark.parametrize("payload", [
    {"tools": [{"name": "schedule_get_schedule"}], "services": {"schedule": "available"}},
    {"classes": [], "total": 0},
    {"events": [], "total": 0},
    {"note": "No results"},
    {"error": "unavailable", "classes": [{"title": "Programming"}]},
])
def test_metadata_or_error_reads_do_not_hide_helper_failure(payload):
    messages = [HumanMessage("Есть ли пары и объявления?"),
                call("call_api_tool", {"name": "schedule_get_schedule", "arguments": {}}, "r1"),
                ToolMessage(content=json.dumps(payload), name="call_api_tool", tool_call_id="r1"),
                ToolMessage(content=core.TOOL_FAILURE_ANSWER, name="ask_chats", tool_call_id="h1"),
                AIMessage(content="Пар нет. Объявления проверить не удалось.")]
    assert core.final_answer(messages, {}).answer == core.TOOL_FAILURE_ANSWER


@pytest.mark.parametrize("target,call_id", [
    ("get_my_ai_calendar", "r1"),
    ("get_my_ai_calendar", "unmatched"),
    ("calendar_get_my_ai_calendar", "r1"),
    ("events_get_university_events", "r1"),
    ("calendar_get_my_ai_calendar", "unmatched"),
])
def test_empty_calendar_preserves_partial_answer_only_for_exact_local_read(target, call_id):
    answer = "В личном календаре событий нет. Объявления проверить не удалось."
    local = target == "get_my_ai_calendar"
    tool_name = target if local else "call_api_tool"
    messages = [HumanMessage("Что у меня завтра и есть ли объявления?"),
                call(tool_name, {} if local else {"name": target, "arguments": {}}, call_id),
                ToolMessage(content=json.dumps({"events": [], "range": ["2026-11-08", "2026-11-08"]}),
                            name=tool_name, tool_call_id="r1"),
                ToolMessage(content=core.TOOL_FAILURE_ANSWER, name="ask_chats", tool_call_id="h1"),
                AIMessage(content=answer)]
    assert core.read_evidence(messages) is False
    valid = local and call_id == "r1"
    assert core.successful_read(messages) is valid
    assert core.final_answer(messages, {}).answer == (answer if valid else core.TOOL_FAILURE_ANSWER)


@pytest.mark.parametrize("empty", [False, True])
def test_web_ai_calendar_survives_failed_helper_without_mcp(monkeypatch, empty):
    from pydantic import SecretStr
    from catix.agent import calendar_tools
    from catix.innohassle import mcp_server

    owners, reads = [], []
    events = [] if empty else [{"title": "Personal meeting"}]
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])

    monkeypatch.setattr(calendar_tools.personal_calendar, "account_key", lambda uid, *a: owners.append(uid) or "ih:u1")
    monkeypatch.setattr(calendar_tools, "events_between", lambda *a: reads.append(a) or events)
    def no_mcp(*args, **kwargs):
        pytest.fail("Local calendar reads must not consult or call MCP")

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", no_mcp)
    monkeypatch.setattr(mcp_server, "build_server", no_mcp)
    fact = "В личном календаре событий нет." if empty else "В личном календаре: Personal meeting."
    answer = fact + " Объявления проверить не удалось."
    out = run([
        call("get_my_ai_calendar", {"date_from": "2026-11-08", "date_to": "2026-11-08"}, "r1"),
        call("ask_chats", {"question": "Есть ли объявления?"}, "h1"),
        AIMessage(content=core.TOOL_FAILURE_ANSWER), AIMessage(content=answer),
    ], context=AgentContext(innohassle_id="u1", innohassle_token=SecretStr("synthetic-user")))
    payload = json.loads(next(m.content for m in out["messages"] if isinstance(m, ToolMessage) and m.name == "get_my_ai_calendar"))
    assert payload["events"] == events and payload["range"] == ["2026-11-08", "2026-11-08"]
    assert owners and set(owners) == {"u1"}
    assert len(reads) == 1 and reads[0][0] == "ih:u1"
    assert core.successful_read(out["messages"]) is True
    assert core.read_evidence(out["messages"]) is not empty
    assert core.final_answer(out["messages"], {}).answer == answer


def test_malformed_local_calendar_never_consults_mcp_declarations(monkeypatch):
    from catix.innohassle import mcp_server

    def no_mcp():
        pytest.fail("Local calendar evidence must not depend on MCP declarations")

    monkeypatch.setattr(mcp_server, "build_server", no_mcp)
    messages = [HumanMessage("Что у меня завтра?"), call("get_my_ai_calendar", {}, "r1"),
                ToolMessage(content='{"events": [], "range": []}', name="get_my_ai_calendar", tool_call_id="r1")]
    assert core.successful_read(messages) is False
    assert core.read_evidence(messages) is False


def test_previous_turn_empty_read_does_not_hide_current_helper_failure():
    messages = [HumanMessage("Какие пары?"),
                ToolMessage(content=json.dumps({"schedule": "B26-CSE-01", "total": 0, "classes": [],
                                               "range": ["2026-11-08", "2026-11-08"]}),
                            name="call_api_tool", tool_call_id="r1"),
                AIMessage(content="Пар нет."), HumanMessage("Какие объявления?"),
                ToolMessage(content=core.TOOL_FAILURE_ANSWER, name="ask_chats", tool_call_id="h1"),
                AIMessage(content="Ничего нового.")]
    assert core.final_answer(messages, {}).answer == core.TOOL_FAILURE_ANSWER


@pytest.mark.parametrize("helper", ["docs", "chats"])
def test_api_only_helper_drops_invented_refs(public_read, helper):
    out = run([
        call(f"ask_{helper}", {"question": "Где аудитория?"}, "h1"),
        call("call_api_tool", {"name": "maps_find_room", "arguments": {"query": "301"}}, "r1"),
        AIMessage(content="Аудитория 301 [m0]."),
        AIMessage(content="Аудитория 301."),
    ])
    report = next(m for m in out["messages"] if isinstance(m, ToolMessage))
    assert "[m0]" not in report.content
    assert out["messages"][-1].text == "Аудитория 301."


def test_bot_reads_known_group_and_linked_calendar_on_the_supervisor(public_read, monkeypatch):
    from catix.agent import calendar_tools

    identities, reads = [], []
    monkeypatch.setattr(calendar_tools.personal_calendar, "telegram_key", lambda uid: identities.append(uid) or "account:bot")
    monkeypatch.setattr(calendar_tools, "events_between", lambda key, start, end: reads.append((key, start, end)) or [{"title": "Study meeting"}])
    day = "2026-11-08"
    parallel = AIMessage(content="", tool_calls=[
        {"name": "call_api_tool", "args": {"name": "schedule_get_schedule", "arguments": {"date_from": day, "date_to": day}}, "id": "r1"},
        {"name": "get_my_ai_calendar", "args": {"date_from": day, "date_to": day,
                                                 "runtime": {"context": {"user_telegram_id": 999}}}, "id": "r2"},
    ])
    out = run([parallel, AIMessage(content="Личные события: Study meeting.")],
              context=AgentContext(study_group="B26-CSE-01", user_telegram_id=123), question="Что у меня завтра?")
    assert identities == [123] and reads[0][0] == "account:bot"
    schedule = next(args for name, args in public_read if name == "call_tool")
    assert schedule == {"name": "schedule_get_schedule", "arguments": {"group": "B26-CSE-01", "date_from": day, "date_to": day}}
    results = [m for m in out["messages"] if isinstance(m, ToolMessage)]
    assert {m.name for m in results} == {"call_api_tool", "get_my_ai_calendar"}
    assert "Study meeting" in next(m.content for m in results if m.name == "get_my_ai_calendar")


@pytest.mark.parametrize("markup", [False, True])
def test_retired_campus_tool_is_refused_by_the_real_graph(public_read, markup):
    attempted = (AIMessage(content='<tool_call><function=ask_campus><parameter=question>Где аудитория?</parameter></function></tool_call>')
                 if markup else call("ask_campus", {"question": "Где аудитория?"}, "old1"))
    out = run([attempted, AIMessage(content="Не удалось проверить аудиторию.")])
    assert public_read == []
    assert out["messages"][-1].text == "Не удалось проверить аудиторию."
    if not markup:
        result = next(m for m in out["messages"] if isinstance(m, ToolMessage))
        assert result.status == "error" and "not a valid tool" in result.content


def test_main_read_markup_is_repaired_against_its_actual_tools(public_read):
    out = run([
        AIMessage(content='<tool_call><function=call_api_tool><parameter=name>maps_find_room</parameter>'
                          '<parameter=arguments>{"query":"301"}</parameter></function></tool_call>'),
        AIMessage(content="Аудитория 301."),
    ])
    assert len(public_read) == 1
    assert out["messages"][-1].text == "Аудитория 301."


@pytest.mark.parametrize("fallback", [False, True])
def test_mixed_mcp_and_chat_report_are_synthesized_not_short_circuited(public_read, monkeypatch, fallback):
    from langchain.tools import ToolRuntime
    from langchain_core.tools import tool
    from langgraph.types import Command

    @tool("search_chats")
    def lookup(queries: list[str], runtime: ToolRuntime[AgentContext]) -> Command:
        """Read synthetic announcements for this graph regression."""
        return Command(update={
            "messages": [ToolMessage(content='{"results": [{"ref": "m0", "text": "Тест завтра"}]}',
                                     name="search_chats", tool_call_id=runtime.tool_call_id, artifact={"relevant": ["m0"]})],
            "sources": {"m0": {"wiki": True, "title": "Synthetic announcement", "link": None, "trust": "official"}},
        })

    monkeypatch.setattr(core, "TOOLS", [lookup if t.name == "search_chats" else t for t in core.TOOLS])
    monkeypatch.setattr(core.settings, "agent_pass_report", True)
    helper_calls = ([call("ask_docs", {"question": "Какие тесты завтра?"}, "d1"),
                     AIMessage(content="Ничего не найдено.")] if fallback else
                    [call("ask_chats", {"question": "Какие тесты завтра?"}, "h1")])
    out = run([
        call("call_api_tool", {"name": "maps_find_room", "arguments": {"query": "301"}}, "r1"),
        *helper_calls,
        call("search_chats", {"queries": ["тест"]}, "s1"),
        AIMessage(content="Тест завтра [m0]."),
        AIMessage(content="Аудитория 301 на третьем этаже. Тест завтра [m0]."),
    ])
    assert out["messages"][-1].text == "Аудитория 301 на третьем этаже. Тест завтра [m0]."
    assert core.final_answer(out["messages"], out["sources"]).sources[0].title == "Synthetic announcement"


@pytest.mark.parametrize("direct_name,args,payload", [
    ("call_api_tool", {"name": "maps_find_room", "arguments": {"query": "301"}}, {"rooms": [{"name": "301"}]}),
    ("search_api_tools", {"query": "room 301"}, {"tools": [{"name": "maps_find_room"}]}),
])
@pytest.mark.parametrize("direct_last", [False, True])
def test_direct_mcp_does_not_block_docs_fallback_or_replace_its_question(direct_name, args, payload, direct_last):
    from tests.test_agent_flow import Req

    direct = [call(direct_name, args, "r1"),
              ToolMessage(content=json.dumps(payload), name=direct_name, tool_call_id="r1")]
    docs = [call("ask_docs", {"question": "Какие правила?"}, "d1"),
            ToolMessage(content="Ничего не найдено.", name="ask_docs", tool_call_id="d1", artifact={"found": False})]
    request = Req(0)
    request.messages = [HumanMessage("Где аудитория и какие правила?"), *(docs + direct if direct_last else direct + docs)]
    request.state["messages"] = request.messages
    fallback = core.FallbackMiddleware._next(request)
    assert fallback is not None
    assert fallback.tool_calls[0]["name"] == "ask_chats"
    assert fallback.tool_calls[0]["args"] == {"question": "Какие правила?"}
    assert fallback.tool_calls[0]["id"].startswith(core.FALLBACK_ID)


def test_fallback_pass_report_does_not_drop_earlier_direct_read(monkeypatch):
    from types import SimpleNamespace
    from tests.test_agent_flow import Req

    monkeypatch.setattr(core.settings, "agent_pass_report", True)
    request = Req(0)
    request.runtime = SimpleNamespace(context=AgentContext())
    request.messages = [HumanMessage("Где аудитория и какие события?"),
                        call("call_api_tool", {"name": "maps_find_room", "arguments": {"query": "301"}}, "r1"),
                        ToolMessage(content='{"rooms": [{"name": "301"}]}', name="call_api_tool", tool_call_id="r1"),
                        call("ask_docs", {"question": "Какие события?"}, "d1"),
                        ToolMessage(content="Ничего.", name="ask_docs", tool_call_id="d1"),
                        call("ask_chats", {"question": "Какие события?"}, core.FALLBACK_ID + "h1"),
                        ToolMessage(content="Тест завтра [m0].", name="ask_chats", tool_call_id=core.FALLBACK_ID + "h1")]
    assert core.PassReportMiddleware._report(request) is None


def test_mcp_ref_fields_do_not_trigger_retrieval_citation_retry():
    from types import SimpleNamespace

    message = ToolMessage(content='{"rooms": [{"ref": "m0", "name": "301"}]}', name="call_api_tool", tool_call_id="r1")
    request = SimpleNamespace(messages=[HumanMessage("Где аудитория?"), message])
    assert core.CiteMiddleware._uncited(request, AIMessage(content="Аудитория 301.")) is None


def test_uncited_api_identifier_in_a_helper_report_is_not_a_source():
    messages = [HumanMessage("Где аудитория?"),
                ToolMessage(content="Аудитория 301, ID m0.", name="ask_docs", tool_call_id="h1"),
                AIMessage(content="Аудитория 301 [m0].")]
    registry = {"m0": {"wiki": True, "title": "Old unrelated page", "link": None, "trust": "official"}}
    assert "Old unrelated page" not in core.final_answer(messages, registry).answer


def test_discovered_read_is_not_cut_off_after_two_sourced_helper_rounds():
    from tests.test_agent_flow import Req

    request = Req(0)
    request.messages = [HumanMessage("Аудитория, правила и объявления?"),
                        call("search_api_tools", {"query": "room 301"}, "s1"),
                        ToolMessage(content='{"tools": [{"name": "maps_find_room"}]}', name="search_api_tools", tool_call_id="s1"),
                        call("ask_docs", {"question": "Правила?"}, "d1"),
                        ToolMessage(content="Правила [m0].", name="ask_docs", tool_call_id="d1"),
                        call("ask_chats", {"question": "Объявления?"}, "h1"),
                        ToolMessage(content="Тест завтра [m1].", name="ask_chats", tool_call_id="h1")]
    guard = core.RunGuardMiddleware({"ask_docs", "ask_chats"} | roles.MAIN_TOOLS)
    assert guard._final(request).tool_choice is None


@pytest.mark.parametrize("helper", [None, "docs", "chats"])
def test_native_map_read_through_http_in_main_and_helpers(mcp_http_protocol, monkeypatch, helper):
    from catix.innohassle import client

    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(client, "scenes", lambda: [{"scene_id": "floor3", "title": "Third floor"}])
    queries = []

    def areas(query):
        queries.append(query)
        return [{"scene_id": "floor3", "area": {"svg_polygon_id": "room301", "title": "301",
                 "ru_title": "301", "description": "Lecture room", "people": [], "room_booking_id": None}}]

    monkeypatch.setattr(client, "search_areas", areas)
    script = ([call(f"ask_{helper}", {"question": "Где аудитория 301?"}, "h1")] if helper else []) + [
        call("search_api_tools", {"query": "room campus map"}, "s1"),
        call("call_api_tool", {"name": "maps_find_room", "arguments": {"query": "301"}}, "r1"),
        AIMessage(content="Аудитория 301 на третьем этаже."),
        AIMessage(content="Аудитория 301 на третьем этаже."),
    ]
    out = run(script, question="Где аудитория 301?")
    assert queries == ["301"]
    results = [m for m in out["messages"] if isinstance(m, ToolMessage)]
    if helper:
        assert [m.name for m in results] == [f"ask_{helper}"]
        assert results[0].artifact["read_found"] is True
        payload = json.loads(results[0].artifact["results"][-1])
    else:
        payload = json.loads(results[-1].content)
    assert payload["areas"][0]["where"] == "Third floor"
    assert core.final_answer(out["messages"], {}).answer == "Аудитория 301 на третьем этаже."


def test_discovery_is_not_evidence_even_if_it_describes_a_result():
    message = ToolMessage(content=json.dumps({"rooms": [{"name": "301"}]}),
                          name="search_api_tools", tool_call_id="r1")
    assert core.found_anything([message]) is not True


def test_room_read_evidence_never_imports_server_policy(monkeypatch):
    import builtins
    original = builtins.__import__

    def guarded(name, globals=None, locals=None, fromlist=(), level=0):
        forbidden = {"mcp_domain", "mcp_tools", "mcp_security", "mcp_server", "mcp_declarations"}
        if name.rsplit(".", 1)[-1] in forbidden or (name == "catix.innohassle" and forbidden.intersection(fromlist)):
            pytest.fail("Host evidence must not import server implementations")
        return original(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded)
    messages = mixed_read_messages("rooms_get_free_rooms", {
        "free": [], "booked": ["313"], "date": "2099-01-01 Thu", "range": "10:00-11:00"})
    assert core.read_evidence(messages) is True
    assert core.successful_read(messages) is True
    assert core.final_answer(messages, {}).answer == messages[-1].text
    raw = {"action_id": "maps.scenes_scenes", "data": [{"scene_id": "m0", "title": "Third floor", "ru_title": None}],
           "total": 1, "truncated": False, "note": "Map scenes only"}
    assert core.read_evidence(mixed_read_messages("maps_scenes_scenes", raw))


@pytest.mark.parametrize("availability", ["free", "booked", "empty"])
def test_real_room_availability_survives_failed_helper(mcp_http_protocol, monkeypatch, availability):
    from catix.innohassle import client, token
    from pydantic import SecretStr

    day = "2099-01-01"
    rooms = [{"id": "313", "title": "Room313", "capacity": 10, "access_level": "yellow"}]
    bookings = [{"room_id": "313", "start": f"{day}T10:00:00+03:00", "end": f"{day}T11:00:00+03:00"}]
    monkeypatch.setattr(client, "bookable_rooms", lambda token: [] if availability == "empty" else rooms)
    monkeypatch.setattr(client, "room_bookings", lambda *a: bookings if availability == "booked" else [])
    permissions = []
    monkeypatch.setattr(client, "can_book_room", lambda *a: permissions.append(a) or (True, None))
    monkeypatch.setattr(token, "claims", lambda value: {"uid": "u1"})
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])


    fact = {"free": "Room313 свободна.", "booked": "Room313 занята.", "empty": "Список доступных комнат пуст."}[availability]
    answer = fact + " Объявления проверить не удалось."
    out = run([
        call("call_api_tool", {"name": "rooms_get_free_rooms", "arguments": {
            "day": day, "time_from": "10:00", "time_to": "11:00"}}, "r1"),
        call("ask_chats", {"question": "Есть ли объявления?"}, "h1"),
        AIMessage(content=core.TOOL_FAILURE_ANSWER), AIMessage(content=answer),
    ], context=AgentContext(innohassle_id="u1", innohassle_token=SecretStr("synthetic-user")))
    payload = json.loads(next(m.content for m in out["messages"] if isinstance(m, ToolMessage)))
    assert payload["free"] == ([{"room_id": "313", "title": "Room313", "capacity": 10, "who": "students"}]
                               if availability == "free" else [])
    assert payload["booked"] == (["313"] if availability == "booked" else [])
    assert [args[:2] for args in permissions] == ([('synthetic-user', '313')] if availability == 'free' else [])
    assert core.final_answer(out["messages"], {}).answer == answer
    assert core.successful_read(out["messages"]) is True
    assert core.read_evidence(out["messages"]) is (availability != "empty")


def mixed_read_messages(target, payload, *, call_id="r1", status="success"):
    return [HumanMessage("Что известно и есть ли объявления?"),
            call("call_api_tool", {"name": target, "arguments": {}}, call_id),
            ToolMessage(content=json.dumps(payload), name="call_api_tool", tool_call_id="r1", status=status),
            ToolMessage(content=core.TOOL_FAILURE_ANSWER, name="ask_chats", tool_call_id="h1"),
            AIMessage(content="Данные получены. Объявления проверить не удалось.")]


@pytest.mark.parametrize("target,kind", [
    ("sport_get_my_sport", "zero_hours"),
    ("sport_get_my_sport", "checked_in"),
    ("sport_get_sport_trainings", "empty"),
    ("sport_get_sport_trainings", "training"),
    ("account_get_my_schedule", "schedule"),
    ("account_get_my_schedule", "bookings"),
    ("account_get_my_schedule", "empty"),
    ("account_get_my_schedule", "partial"),
    ("account_get_my_schedule", "schedule_only_empty"),
])
def test_personal_read_contracts_preserve_partial_answers(monkeypatch, target, kind):
    from catix.innohassle import client, sport, token

    day = "2099-01-01"
    training = {"id": 31, "sport_name": "Swimming", "start": f"{day}T10:00:00+03:00",
                "end": f"{day}T11:00:00+03:00"}
    monkeypatch.setattr(sport, "me", lambda *a: {"user_id": 42, "student_info": {"medical_group": "General"}})
    monkeypatch.setattr(sport, "hours", lambda *a: {"required_hours": 30})
    monkeypatch.setattr(sport, "current_semester", lambda *a: {})
    monkeypatch.setattr(sport, "my_trainings", lambda *a: [
        {"training": training, "checked_in": True}] if kind in {"checked_in", "training"} else [])
    empty_ics = "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n"
    class_ics = empty_ics.replace("END:VCALENDAR", "BEGIN:VEVENT\r\nUID:test\r\nDTSTART:20990101T070000Z\r\n"
                                 "DTEND:20990101T080000Z\r\nSUMMARY:Programming\r\nEND:VEVENT\r\nEND:VCALENDAR")

    def calendar(token, calendar_kind):
        if kind == "partial":
            raise client.ServiceError(503, "unavailable")
        return class_ics if kind == "schedule" and calendar_kind == "class" else empty_ics

    monkeypatch.setattr(client, "my_calendar_ics", calendar)
    monkeypatch.setattr(client, "my_calendar_groups", lambda token: (1, ["core"]))
    monkeypatch.setattr(client, "event_groups", lambda **kw: [{"alias": "core", "tags": []}])
    monkeypatch.setattr(client, "my_group_calendar_ics", lambda token, user_id, alias: calendar(token, "class"))
    def music_bookings(*args):
        if kind == "schedule_only_empty":
            raise client.ServiceError(503, "unavailable")
        return [{"id": "42", "time_start": f"{day}T10:00:00+03:00",
                 "time_end": f"{day}T11:00:00+03:00"}] if kind == "bookings" else []

    def room_bookings(*args):
        if kind == "schedule_only_empty":
            raise client.ServiceError(503, "unavailable")
        return []

    monkeypatch.setattr(client, "my_music_room_bookings", music_bookings)
    monkeypatch.setattr(client, "my_room_bookings", room_bookings)
    monkeypatch.setattr(token, "claims", lambda value: {"uid": "u1"})
    args = {} if target == "sport_get_my_sport" else {"date_from": day, "date_to": day}
    payload = native_call(target, args, token="synthetic-user", sport_token="synthetic-sport", uid="u1")
    assert "error" not in payload
    if kind == "schedule":
        assert payload["schedule"][0]["title"] == "Programming" and payload["bookings"] == []
    if kind == "bookings":
        assert payload["bookings"][0]["booking_id"] == "42" and payload["schedule"] == []
    if kind == "zero_hours":
        assert payload["hours"]["done"] == 0 and payload["checked_in"] == []
    messages = mixed_read_messages(target, payload)
    assert core.final_answer(messages, {}).answer == messages[-1].text
    assert core.successful_read(messages) is True
    assert core.read_evidence(messages) is (kind not in {"empty", "partial", "schedule_only_empty"})


@pytest.mark.parametrize("injected_calendar", [False, True])
def test_all_external_schedule_components_failed_is_not_a_success(monkeypatch, injected_calendar):
    from catix.innohassle import client, token

    def unavailable(*args):
        raise client.ServiceError(503, "unavailable")

    monkeypatch.setattr(token, "claims", lambda value: {"uid": "u1"})
    for method in ("my_calendar_groups", "my_calendar_ics", "my_music_room_bookings", "my_room_bookings"):
        monkeypatch.setattr(client, method, unavailable)
    payload = native_call("account_get_my_schedule", {"date_from": "2099-01-01", "date_to": "2099-01-01"},
                          token="synthetic-user", uid="u1")
    assert payload["schedule"] == payload["bookings"] == []
    assert "ai_calendar" not in payload
    assert {problem.partition(":")[0] for problem in payload["not_read"]} == {
        "class", *client.MY_CALENDARS, "music room", "rooms"}
    if injected_calendar:
        payload["ai_calendar"] = [{"title": "Not part of this external read"}]
    messages = mixed_read_messages("account_get_my_schedule", payload)
    assert core.successful_read(messages) is False
    assert core.read_evidence(messages) is False
    assert core.final_answer(messages, {}).answer == core.TOOL_FAILURE_ANSWER


@pytest.mark.parametrize("target,payload,call_id,status", [
    ("rooms_book_room", {"done": True, "booked": {"room": "313"}, "data": [{"room": "313"}]}, "r1", "success"),
    ("unknown_read", {"areas": [{"title": "313"}]}, "r1", "success"),
    ("maps_find_room", {"areas": [{"title": "313"}], "total": 1}, "unmatched", "success"),
    ("maps_find_room", {"free": [{"room_id": "313"}], "booked": [], "date": "2099-01-01 Thu", "range": "10:00-11:00"}, "r1", "success"),
    ("rooms_get_free_rooms", {"areas": [{"title": "313"}], "total": 1}, "r1", "success"),
    ("sport_get_my_sport", {"tools": [{"name": "sport_get_my_sport"}]}, "r1", "success"),
    ("sport_get_my_sport", {"hours": {"done": 0, "required": 30, "left": 30}, "checked_in": [], "error": "unavailable"}, "r1", "success"),
    ("sport_get_my_sport", {"hours": {"done": 0, "required": 30, "left": 30}, "checked_in": []}, "r1", "error"),
    ("account_get_my_schedule", {"schedule": [], "bookings": [], "range": ["2099-01-01", "2099-01-01"],
                                "not_read": ["class: unavailable", "sport: unavailable", "event: unavailable",
                                             "music room: unavailable", "rooms: unavailable"]}, "r1", "success"),
])
def test_only_matching_successful_read_results_are_evidence(target, payload, call_id, status):
    messages = mixed_read_messages(target, payload, call_id=call_id, status=status)
    assert core.read_evidence(messages) is False
    assert core.successful_read(messages) is False
    # A matched successful write is not read evidence, but its action result must
    # survive an unrelated helper failure now that the supervisor can act too.
    assert core.final_answer(messages, {}).answer == (messages[-1].text if target == "rooms_book_room" else core.TOOL_FAILURE_ANSWER)


def test_previous_turn_nonempty_read_does_not_support_current_failure():
    messages = mixed_read_messages("maps_find_room", {"total": 1, "areas": [{"title": "313"}]})
    assert core.successful_read(messages) is True  # The same read is valid in its own turn.
    messages += [HumanMessage("Какие объявления?"),
                 ToolMessage(content=core.TOOL_FAILURE_ANSWER, name="ask_chats", tool_call_id="h2"),
                 AIMessage(content="Ничего нового.")]
    assert core.read_evidence(messages) is False
    assert core.successful_read(messages) is False
    assert core.final_answer(messages, {}).answer == core.TOOL_FAILURE_ANSWER


@pytest.mark.parametrize("target,args", [
    ("timetable_get_courses", {"query": "missing"}),
    ("timetable_get_room_timetable", {"room": "313", "day": "2099-01-01"}),
    ("timetable_get_room_timetable", {"day": "2099-01-01", "time_from": "10:00", "time_to": "11:00"}),
    ("maps_find_room", {"query": "missing"}),
    ("clubs_get_clubs", {}),
    ("events_get_university_events", {"date_from": "2099-01-01", "date_to": "2099-01-01"}),
    ("music_get_music_room_schedule", {"date_from": "2099-01-01", "date_to": "2099-01-01"}),
    ("sport_get_sports", {}),
])
def test_other_native_read_empty_contracts(monkeypatch, target, args):
    from catix.innohassle import client, sport, timetable, token

    monkeypatch.setattr(client, "timetable", lambda: {"term": {}, "courses": [], "rooms": [], "instructors": []})
    monkeypatch.setattr(timetable, "sessions_on", lambda *a: [])
    for name in ("scenes", "search_areas", "club_leaders", "clubs", "events", "music_room_bookings"):
        monkeypatch.setattr(client, name, lambda *a: [])
    monkeypatch.setattr(sport, "sports", lambda *a: [])
    monkeypatch.setattr(token, "claims", lambda value: {"uid": "u1"})
    payload = native_call(target, args, token="synthetic-user", sport_token="synthetic-sport", uid="u1")
    assert "error" not in payload
    messages = mixed_read_messages(target, payload)
    assert core.final_answer(messages, {}).answer == messages[-1].text
    assert core.successful_read(messages) is True
    # Music returns one real dated observation ("nothing booked"), not an empty search.
    assert core.read_evidence(messages) is (target == "music_get_music_room_schedule")


@pytest.mark.parametrize("empty", [False, True])
def test_native_read_envelopes_from_declared_functions(monkeypatch, empty):
    import httpx
    from catix.innohassle import client, token
    from tests.mcp_native_helpers import registered_tools

    samples = {
        "printers_print_get_printers_status": {"printer": {"display_name": "313", "cups_name": "m0"},
                                               "offline": False, "paper_percentage": None, "toner_percentage": 0},
        "maps_scenes_search_areas": {"scene_id": "m0", "area": {"title": "313", "ru_title": None, "description": None}},
        "maps_scenes_scenes": {"scene_id": "m0", "title": "Third floor", "ru_title": None},
        "clubs_get_clubs_list_clubs__get": {"title": "Chess", "short_description": None, "is_active": True},
        "music_bookings_daily_bookings": {"time_start": "2099-01-01T10:00:00", "time_end": "2099-01-01T11:00:00"},
        "events_events_list_events": {"id": "m0", "data": {"name": "Workshop", "starts_at": "2099-01-01T10:00:00",
                                                            "duration_hours": 1.0, "location": {"display_name": "313"}}},
    }
    declared = registered_tools()
    assert set(samples) == {name for name, tool in declared.items() if tool.annotations.read_only_hint
                           and "data" in (tool.output_schema or {}).get("required", [])}
    assert all("catix" not in (tool.meta or {}) for tool in declared.values())
    monkeypatch.setattr(token, "claims", lambda value: {"uid": "u1"})
    for target, sample in samples.items():
        with httpx.Client(base_url="https://synthetic.invalid", transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=[] if empty else [sample])
        )) as http:
            monkeypatch.setattr(client, "_client", http)
            args = {"query": "313"} if target == "maps_scenes_search_areas" else (
                {"date": "2099-01-01"} if target == "music_bookings_daily_bookings" else {})
            payload = native_call(target, args, token="synthetic-user", uid="u1")
        assert payload["data"] == ([] if empty else [sample])
        messages = mixed_read_messages(target, payload)
        assert core.successful_read(messages) is True, target
        assert core.read_evidence(messages) is not empty, target
        assert core.final_answer(messages, {}).answer == messages[-1].text
        # API IDs which resemble retrieval refs cannot revive an unrelated source.
        messages[-1] = AIMessage(content="Данные получены [m0].")
        assert "Old unrelated page" not in core.final_answer(messages, {
            "m0": {"wiki": True, "title": "Old unrelated page", "link": None, "trust": "official"}}).answer


@pytest.mark.parametrize("target,wrapper", [
    ("maps_find_room", None),
    ("rooms_get_free_rooms", None),
    ("sport_get_my_sport", None),
    ("unknown_read", None),
    ("rooms_book_room", None),
    ("calendar_get_my_ai_calendar", None),
    ("maps_scenes_scenes", "meta"),
    ("maps_scenes_scenes", "result"),
])
def test_raw_envelope_cannot_impersonate_another_read_or_nested_metadata(target, wrapper):
    payload = {"action_id": "maps.scenes_scenes", "data": [{"scene_id": "m0", "title": "Third floor", "ru_title": None}],
               "total": 1, "truncated": False, "note": "Map scenes only"}
    assert core.read_evidence(mixed_read_messages("maps_scenes_scenes", payload)) is True
    messages = mixed_read_messages(target, {wrapper: payload} if wrapper else payload)
    assert core.read_evidence(messages) is False
    assert core.successful_read(messages) is False
    assert core.final_answer(messages, {}).answer == core.TOOL_FAILURE_ANSWER


@pytest.mark.parametrize("changes", [
    {"data": [{"title": "Missing required scene_id"}]},
    {"data": None}, {"total": True}, {"total": 0}, {"truncated": "false"}, {"action_id": None},
])
def test_raw_envelope_must_validate_the_declared_output_contract(changes):
    payload = {"action_id": "maps.scenes_scenes", "data": [{"scene_id": "m0", "title": "Third floor", "ru_title": None}],
               "total": 1, "truncated": False, "note": "Map scenes only"}
    assert core.successful_read(mixed_read_messages("maps_scenes_scenes", payload)) is True
    payload.update(changes)
    messages = mixed_read_messages("maps_scenes_scenes", payload)
    assert core.read_evidence(messages) is False
    assert core.successful_read(messages) is False
    assert core.final_answer(messages, {}).answer == core.TOOL_FAILURE_ANSWER


@pytest.mark.parametrize("changes", [
    {"free": None}, {"booked": None}, {"date": None}, {"range": None},
    {"error": "unavailable"},
])
def test_room_read_contract_rejects_malformed_and_failed_payloads(changes):
    payload = {"free": [], "booked": [], "date": "2099-01-01 Thu", "range": "10:00-11:00"}
    assert core.successful_read(mixed_read_messages("rooms_get_free_rooms", payload)) is True
    payload.update(changes)
    messages = mixed_read_messages("rooms_get_free_rooms", payload)
    assert core.read_evidence(messages) is False
    assert core.successful_read(messages) is False
    assert core.final_answer(messages, {}).answer == core.TOOL_FAILURE_ANSWER


def test_room_timetable_with_only_occupied_rooms_is_nonempty_evidence(monkeypatch):
    from datetime import time
    from types import SimpleNamespace
    from catix.innohassle import client, timetable

    monkeypatch.setattr(client, "timetable", lambda: {"rooms": [{"id": "313"}]})
    monkeypatch.setattr(timetable, "sessions_on", lambda *a: [
        SimpleNamespace(room="313", start=time(10), end=time(11))])
    payload = native_call("timetable_get_room_timetable", {
        "day": "2099-01-01", "time_from": "10:00", "time_to": "11:00"}, token=None, sport_token=None, uid=None)
    assert payload["free_of_classes"] == [] and payload["with_classes"] == ["313"]
    messages = mixed_read_messages("timetable_get_room_timetable", payload)
    assert core.read_evidence(messages) is True
    assert core.final_answer(messages, {}).answer == messages[-1].text


@pytest.mark.parametrize("target,payload", [
    ("sport_get_my_sport", {"hours": {}, "checked_in": []}),
    ("sport_get_my_sport", {"hours": {"done": False, "required": 30, "left": 30}, "checked_in": []}),
    ("sport_get_sport_trainings", {"trainings": [], "range": []}),
    ("sport_get_sport_trainings", {"trainings": None, "range": ["2099-01-01", "2099-01-01"]}),
    ("account_get_my_schedule", {"schedule": "B26-CSE-01", "bookings": [], "range": ["2099-01-01", "2099-01-01"]}),
    ("account_get_my_schedule", {"schedule": [], "bookings": None, "range": ["2099-01-01", "2099-01-01"]}),
])
def test_personal_reads_require_their_own_result_collections(target, payload):
    messages = mixed_read_messages(target, payload)
    assert core.read_evidence(messages) is False
    assert core.successful_read(messages) is False
    assert core.final_answer(messages, {}).answer == core.TOOL_FAILURE_ANSWER
