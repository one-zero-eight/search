"""Deterministic agent graphs for direct, read-only MCP access, and what the answer may cite of it."""

import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from catix.agent import api_tools, core
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



def test_agent_discovers_and_reads_directly(public_read):
    out = run([
        call("search_api_tools", {"query": "room 301"}, "s1"),
        call("call_api_tool", {"name": "maps_find_room", "arguments": {"query": "301"}}, "s2"),
        AIMessage(content="Аудитория 301 на третьем этаже."),
    ])
    results = [m for m in out["messages"] if isinstance(m, ToolMessage)]
    assert [name for name, _ in public_read] == ["search_tools", "call_tool"]
    assert [m.name for m in results] == ["search_api_tools", "call_api_tool"]
    assert json.loads(results[-1].content)["areas"][0]["title"] == "301"
    assert core.final_answer(out["messages"], {}).answer == "Аудитория 301 на третьем этаже."


def test_prompt_keeps_trusted_group_without_course_glossary(monkeypatch):
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
    core.agent_prompt().wrap_model_call(request, seen.append)
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


@pytest.mark.parametrize("kind", ["schedule", "bot_calendar"])
def test_empty_calendar_read_in_full_graph(mcp_http_protocol, monkeypatch, kind):
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
        answer = "Пар нет."
        empty_key = "classes"
    else:
        monkeypatch.setattr(calendar_tools.personal_calendar, "telegram_key", lambda uid: "account:bot")
        monkeypatch.setattr(calendar_tools, "events_between", lambda key, start, end: [])
        direct = call("get_my_ai_calendar", {"date_from": day, "date_to": day}, "r1")
        answer = "В личном календаре событий нет."
        empty_key = "events"
    out = run([direct, AIMessage(content=answer)], context=context)
    results = [m for m in out["messages"] if isinstance(m, ToolMessage)]
    payload = json.loads(results[0].content)
    assert payload[empty_key] == [] and payload["range"] == [day, day]
    assert core.final_answer(out["messages"], {}).answer == answer


@pytest.mark.parametrize("empty", [False, True])
def test_web_ai_calendar_is_read_without_mcp(monkeypatch, empty):
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
    answer = "В личном календаре событий нет." if empty else "В личном календаре: Personal meeting."
    out = run([
        call("get_my_ai_calendar", {"date_from": "2026-11-08", "date_to": "2026-11-08"}, "r1"),
        AIMessage(content=answer),
    ], context=AgentContext(innohassle_id="u1", innohassle_token=SecretStr("synthetic-user")))
    payload = json.loads(next(m.content for m in out["messages"] if isinstance(m, ToolMessage) and m.name == "get_my_ai_calendar"))
    assert payload["events"] == events and payload["range"] == ["2026-11-08", "2026-11-08"]
    assert owners and set(owners) == {"u1"}
    assert len(reads) == 1 and reads[0][0] == "ih:u1"
    assert core.final_answer(out["messages"], {}).answer == answer


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


def test_mixed_mcp_and_search_results_are_cited_from_the_search(public_read, monkeypatch):
    from langchain.tools import ToolRuntime
    from langchain_core.tools import tool
    from langgraph.types import Command

    @tool("search")
    def lookup(queries: list[str], runtime: ToolRuntime[AgentContext]) -> Command:
        """Read synthetic announcements for this graph regression."""
        return Command(update={
            "messages": [ToolMessage(content='{"total": 1, "chat": {"total": 1, "messages": [{"ref": "m0", "text": "Тест завтра"}]}}',
                                     name="search", tool_call_id=runtime.tool_call_id, artifact={"relevant": ["m0"]})],
            "sources": {"m0": {"wiki": True, "title": "Synthetic announcement", "link": None, "trust": "official"}},
        })

    monkeypatch.setattr(core, "TOOLS", [lookup if t.name == "search" else t for t in core.TOOLS])
    out = run([
        call("call_api_tool", {"name": "maps_find_room", "arguments": {"query": "301"}}, "r1"),
        call("search", {"queries": ["тест"]}, "s1"),
        AIMessage(content="Аудитория 301 на третьем этаже. Тест завтра [m0]."),
    ])
    assert out["messages"][-1].text == "Аудитория 301 на третьем этаже. Тест завтра [m0]."
    assert core.final_answer(out["messages"], out["sources"]).sources[0].title == "Synthetic announcement"


def test_mcp_ref_fields_do_not_trigger_retrieval_citation_retry():
    from types import SimpleNamespace

    message = ToolMessage(content='{"rooms": [{"ref": "m0", "name": "301"}]}', name="call_api_tool", tool_call_id="r1")
    request = SimpleNamespace(messages=[HumanMessage("Где аудитория?"), message])
    assert core.CiteMiddleware._uncited(request, AIMessage(content="Аудитория 301.")) is None


SEARCH_RESULT = '{"total": 1, "docs": {"total": 1, "pieces": [{"ref": "m1", "text": "Правила"}]}}'


def test_an_uncited_answer_after_a_search_with_refs_is_asked_once_more():
    from types import SimpleNamespace

    request = SimpleNamespace(messages=[HumanMessage("Какие правила?"), call("search", {"queries": ["правила"]}, "s1"),
                                        ToolMessage(content=SEARCH_RESULT, name="search", tool_call_id="s1")])
    answer = AIMessage(content="Правила такие.")
    assert core.CiteMiddleware._uncited(request, answer) is answer
    assert core.CiteMiddleware._uncited(request, AIMessage(content="Правила такие [m1].")) is None
    # a search of an earlier question does not count
    earlier = SimpleNamespace(messages=[*request.messages, AIMessage(content="Правила [m1]."), HumanMessage("Привет")])
    assert core.CiteMiddleware._uncited(earlier, answer) is None


def test_a_ref_is_honoured_only_when_this_turns_retrieval_results_gave_it():
    registry = {"m1": {"wiki": True, "title": "Rules", "link": None, "trust": "official"},
                "m2": {"wiki": True, "title": "Old page", "link": None, "trust": "official"}}
    messages = [HumanMessage("Какие правила?"), call("search", {"queries": ["правила"]}, "s1"),
                ToolMessage(content=SEARCH_RESULT, name="search", tool_call_id="s1"),
                AIMessage(content="Правила такие [m1], а ещё [m2].")]
    cited = core.final_answer(messages, registry)
    assert [s.title for s in cited.sources] == ["Rules"]
    assert "Old page" not in cited.answer
    # the same ref in the result of a tool that is not retrieval gives no source
    api = [messages[0], ToolMessage(content=SEARCH_RESULT, name="call_api_tool", tool_call_id="s1"), messages[-1]]
    assert core.final_answer(api, registry).sources == []


def test_native_map_read_through_http(mcp_http_protocol, monkeypatch):
    from catix.innohassle import client

    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(client, "scenes", lambda: [{"scene_id": "floor3", "title": "Third floor"}])
    queries = []

    def areas(query):
        queries.append(query)
        return [{"scene_id": "floor3", "area": {"svg_polygon_id": "room301", "title": "301",
                 "ru_title": "301", "description": "Lecture room", "people": [], "room_booking_id": None}}]

    monkeypatch.setattr(client, "search_areas", areas)
    script = [
        call("search_api_tools", {"query": "room campus map"}, "s1"),
        call("call_api_tool", {"name": "maps_find_room", "arguments": {"query": "301"}}, "r1"),
        AIMessage(content="Аудитория 301 на третьем этаже."),
        AIMessage(content="Аудитория 301 на третьем этаже."),
    ]
    out = run(script, question="Где аудитория 301?")
    assert queries == ["301"]
    results = [m for m in out["messages"] if isinstance(m, ToolMessage)]
    payload = json.loads(results[-1].content)
    assert payload["areas"][0]["where"] == "Third floor"
    assert core.final_answer(out["messages"], {}).answer == "Аудитория 301 на третьем этаже."


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
        # API IDs which resemble retrieval refs cannot revive an unrelated source.
        messages = [HumanMessage("Что известно?"), call("call_api_tool", {"name": target, "arguments": args}, "r1"),
                    ToolMessage(content=json.dumps(payload), name="call_api_tool", tool_call_id="r1"),
                    AIMessage(content="Данные получены [m0].")]
        assert "Old unrelated page" not in core.final_answer(messages, {
            "m0": {"wiki": True, "title": "Old unrelated page", "link": None, "trust": "official"}}).answer
