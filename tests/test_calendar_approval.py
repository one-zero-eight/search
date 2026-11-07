"""Local calendar uses native supervisor approval and API resume, never a helper or MCP."""

import json
from datetime import datetime, time, timedelta
from types import SimpleNamespace

import psycopg
import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command
from pydantic import SecretStr

from catix import personal_calendar
from catix.agent import roles
from catix.agent.core import build_agent
from catix.agent.tools import AgentContext, TOOLS
from catix.settings import settings
from tests.test_calendar_actions import calendar_db  # noqa: F401 - shared disposable PostgreSQL fixture
from tests.test_roles import ScriptedModel

DAY = (datetime.now(settings.tz) + timedelta(days=2)).date()
SITE = AgentContext(innohassle_id="u1", innohassle_token=SecretStr("calendar-user-token"))
ARGS = {"title": "Встреча", "day": DAY.isoformat(), "start_time": "15:00", "end_time": "16:00", "all_day": False, "room": "108"}


@pytest.fixture
def calendar(monkeypatch):
    old = personal_calendar.PersonalEvent(5, "Встреча", datetime.combine(DAY, time(10), settings.tz),
                                          datetime.combine(DAY, time(11), settings.tz), False, "101")
    state = SimpleNamespace(events={("ih:u1", 5): old}, writes=[])
    monkeypatch.setattr(personal_calendar, "account_key", lambda uid, telegram_id=None: f"ih:{uid}")
    monkeypatch.setattr(personal_calendar, "event_of", lambda key, ident: state.events.get((key, ident)))

    def save(key, ident=6, **fields):
        event = personal_calendar.PersonalEvent(ident, **fields)
        state.writes.append((key, ident, fields))
        state.events[key, ident] = event
        return event

    monkeypatch.setattr(personal_calendar, "add_event", save)
    monkeypatch.setattr(personal_calendar, "update_event", save)

    def delete(key, ident):
        state.writes.append((key, ident, "delete"))
        return state.events.pop((key, ident), None) is not None

    monkeypatch.setattr(personal_calendar, "delete_event", delete)
    return state


def call(name, args, ident):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": ident, "type": "tool_call"}])


def run_action(name, args):
    question = "Добавь встречу в мой календарь" if name == "add_to_ai_calendar" else "Перенеси встречу на 15:00"
    script = [call(name, args, "h1"), AIMessage(content="Запрос обработан.")]
    agent = build_agent(ScriptedModel(responses=script), guardrail=False)
    config = {"configurable": {"thread_id": f"calendar-{name}"}}
    out = agent.invoke({"messages": [HumanMessage(question)]}, config, context=SITE)
    return agent, config, out


def test_calendar_actions_are_exposed_only_on_root_and_always_reviewed():
    from catix.agent.calendar_approval import LOCAL_CALENDAR_APPROVAL

    names = {"add_to_ai_calendar", "update_ai_calendar", "remove_from_ai_calendar"}
    assert names <= {t.name for t in TOOLS}
    assert {"search_api_tools", "call_api_tool"} <= roles.MAIN_TOOLS
    assert all(not hasattr(role, "approval") for role in roles.ROLES.values())
    assert names == set(LOCAL_CALENDAR_APPROVAL)
    assert names | {"get_my_ai_calendar"} <= roles.MAIN_TOOLS
    assert not any((names | {"get_my_ai_calendar"}) & role.tools for role in roles.ROLES.values())


@pytest.mark.parametrize("unknown", [False, True])
def test_local_action_result_survives_unrelated_helper_failure(calendar, monkeypatch, unknown):
    from catix.agent import core

    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    if unknown:
        save = personal_calendar.add_event

        def committed_but_reply_lost(*args, **kwargs):
            save(*args, **kwargs)
            raise RuntimeError("synthetic lost response")

        monkeypatch.setattr(personal_calendar, "add_event", committed_but_reply_lost)
    answer = ("Сохранение встречи не подтверждено; повторять нельзя. Объявления проверить не удалось." if unknown
              else "Встреча сохранена. Объявления проверить не удалось.")
    script = [call("add_to_ai_calendar", ARGS, "w1"),
              call("ask_chats", {"question": "Есть объявления?"}, "h1"),
              AIMessage(content=core.TOOL_FAILURE_ANSWER), AIMessage(content=answer)]
    agent = build_agent(ScriptedModel(responses=script), guardrail=False)
    config = {"configurable": {"thread_id": "mixed-local-action"}}
    agent.invoke({"messages": [HumanMessage("Добавь встречу и проверь объявления.")]}, config, context=SITE)
    paused = agent.get_state(config).interrupts[0]
    assert calendar.writes == []
    out = agent.invoke(Command(resume={paused.id: {"decisions": [{"type": "approve"}]}}), config, context=SITE)
    assert len(calendar.writes) == 1
    assert core.final_answer(out["messages"], {}) == answer
    assert core.action_receipt(out["messages"])
    assert not core.read_evidence(out["messages"]) and not core.successful_read(out["messages"])


@pytest.mark.parametrize("name", ["add_to_ai_calendar", "update_ai_calendar"])
@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_calendar_write_waits_for_consent_and_rejection_changes_nothing(calendar, name, decision):
    args = {**ARGS, **({"calendar_event_id": 5} if name == "update_ai_calendar" else {})}
    agent, config, _ = run_action(name, args)
    interrupts = agent.get_state(config).interrupts
    assert len(interrupts) == 1 and calendar.writes == []
    request = interrupts[0].value["action_requests"][0]
    assert request["name"] == name
    assert "Встреча" in request["description"] and "15:00" in request["description"] and "108" in request["description"]
    assert interrupts[0].value["review_configs"][0]["allowed_decisions"] == ["approve", "reject"]
    out = agent.invoke(Command(resume={interrupts[0].id: {"decisions": [{"type": decision}]}}), config, context=SITE)
    assert not agent.get_state(config).interrupts
    if decision == "approve":
        assert len(calendar.writes) == 1 and calendar.writes[0][0] == "ih:u1"
        assert calendar.writes[0][2]["starts_at"] == datetime.combine(DAY, time(15), settings.tz)
        report = next(m for m in out["messages"] if isinstance(m, ToolMessage) and m.name == name)
        assert json.loads(report.content)["done"] is True
    else:
        assert calendar.writes == [] and calendar.events["ih:u1", 5].starts_at.hour == 10
    assert "calendar-user-token" not in str(out)
    assert not any(m.name in {"ask_account", "call_api_tool"} for m in out["messages"] if isinstance(m, ToolMessage))


@pytest.mark.parametrize("name", ["add_to_ai_calendar", "update_ai_calendar"])
@pytest.mark.parametrize("decision", ["approve", "reject"])
@pytest.mark.parametrize("spoof", [{"context": {"innohassle_id": "forged"}}, None, "forged"])
def test_model_runtime_cannot_bypass_calendar_consent(calendar, name, decision, spoof):
    args = {**ARGS, "runtime": spoof, **({"calendar_event_id": 5} if name == "update_ai_calendar" else {})}
    agent, config, _ = run_action(name, args)
    assert calendar.writes == [], "Model runtime suppressed approval and allowed a write"
    interrupts = agent.get_state(config).interrupts
    assert len(interrupts) == 1
    description = interrupts[0].value["action_requests"][0]["description"]
    assert all(detail in description for detail in ("Встреча", "15:00", "16:00", "108"))
    assert str(DAY.year) in description
    assert "forged" not in description
    agent.invoke(Command(resume={interrupts[0].id: {"decisions": [{"type": decision}]}}), config, context=SITE)
    assert not agent.get_state(config).interrupts
    if decision == "approve":
        assert len(calendar.writes) == 1
        key, ident, fields = calendar.writes[0]
        assert key == "ih:u1" and ident == (5 if name == "update_ai_calendar" else 6)
        assert fields == {"title": "Встреча", "starts_at": datetime.combine(DAY, time(15), settings.tz),
                          "ends_at": datetime.combine(DAY, time(16), settings.tz), "all_day": False, "room": "108"}
    else:
        assert calendar.writes == []
        assert calendar.events["ih:u1", 5].starts_at.hour == 10


@pytest.mark.parametrize("name", ["add_to_ai_calendar", "update_ai_calendar"])
@pytest.mark.parametrize("wrong", [{"start_time": None}, {"end_time": "14:00"}, {"title": " "},
                                  {"user_key": "ih:forged"}, {"recurrence": "weekly"}])
def test_spoofed_runtime_does_not_hide_invalid_business_arguments(calendar, name, wrong):
    args = {**ARGS, "runtime": {"context": {"innohassle_id": "forged"}}, **wrong,
            **({"calendar_event_id": 5} if name == "update_ai_calendar" else {})}
    agent, config, _ = run_action(name, args)
    assert not agent.get_state(config).interrupts
    assert calendar.writes == []


@pytest.mark.parametrize("wrong", [{"start_time": None}, {"end_time": "14:00"}, {"title": " "},
                                    {"all_day": True, "start_time": "15:00"}])
def test_invalid_calendar_actions_do_not_prompt_or_write(calendar, wrong):
    agent, config, _ = run_action("add_to_ai_calendar", {**ARGS, **wrong})
    assert not agent.get_state(config).interrupts
    assert calendar.writes == []


@pytest.mark.parametrize("wrong", [{"calendar_event_id": 0}, {"user_key": "ih:forged"}, {"recurrence": "weekly"}])
def test_invalid_removal_does_not_prompt_or_write(calendar, wrong):
    agent, config, _ = run_action("remove_from_ai_calendar", {"calendar_event_id": 5, "runtime": "forged", **wrong})
    assert not agent.get_state(config).interrupts
    assert calendar.writes == []


@pytest.mark.parametrize("name, backend", [("add_to_ai_calendar", "add_event"), ("update_ai_calendar", "update_event"),
                                        ("remove_from_ai_calendar", "delete_event")])
@pytest.mark.parametrize("after_write", [False, True])
@pytest.mark.parametrize("error_type", [psycopg.OperationalError, RuntimeError])
def test_calendar_storage_failure_is_safe_and_outcome_unknown(calendar, monkeypatch, caplog, name, backend, after_write, error_type):
    original = getattr(personal_calendar, backend)
    calls = []
    secret = "postgresql://calendar_admin:secret-password@private-db/calendar"

    def fail(*args, **kwargs):
        calls.append((args, kwargs))
        if after_write:
            original(*args, **kwargs)
        raise error_type(secret)

    monkeypatch.setattr(personal_calendar, backend, fail)
    args = {} if name == "remove_from_ai_calendar" else dict(ARGS)
    if name != "add_to_ai_calendar":
        args["calendar_event_id"] = 5
    agent, config, _ = run_action(name, args)
    paused = agent.get_state(config).interrupts[0]
    assert calls == [] and calendar.writes == []
    out = agent.invoke(Command(resume={paused.id: {"decisions": [{"type": "approve"}]}}), config, context=SITE)
    report = next(m for m in out["messages"] if isinstance(m, ToolMessage) and m.name == name)
    assert all(value not in str(out) + caplog.text for value in (secret, "calendar_admin", "secret-password", "private-db"))
    result = json.loads(report.content)
    assert result["done"] is None and result["outcome"] == "unknown"
    assert "may have" in result["error"] and "Do not retry automatically" in result["error"]
    assert "nothing" not in result["error"].lower()
    assert len(calls) == 1 and len(calendar.writes) == int(after_write)


@pytest.mark.parametrize("name", ["update_ai_calendar", "remove_from_ai_calendar"])
@pytest.mark.parametrize("error_type", [psycopg.OperationalError, RuntimeError])
def test_approval_read_failure_still_requires_consent_without_diagnostics(calendar, monkeypatch, caplog, name, error_type):
    def unavailable(*args):
        raise error_type("connection refused: host=private-db user=calendar_admin password=secret-password")

    monkeypatch.setattr(personal_calendar, "event_of", unavailable)
    args = {"calendar_event_id": 5, **(ARGS if name == "update_ai_calendar" else {})}
    agent, config, out = run_action(name, args)
    interrupts = agent.get_state(config).interrupts
    assert len(interrupts) == 1 and calendar.writes == []
    description = interrupts[0].value["action_requests"][0]["description"]
    assert "#5" in description
    assert "не удалось прочитать" in description
    if name == "update_ai_calendar":
        assert all(detail in description for detail in ("Встреча", "15:00", "16:00", "108"))
    assert all(value not in str(out) + str(interrupts) + caplog.text
               for value in ("private-db", "calendar_admin", "secret-password"))
    agent.invoke(Command(resume={interrupts[0].id: {"decisions": [{"type": "reject"}]}}), config, context=SITE)
    assert calendar.writes == []


@pytest.mark.parametrize("name", ["add_to_ai_calendar", "update_ai_calendar", "remove_from_ai_calendar"])
@pytest.mark.parametrize("all_day", [False, True])
@pytest.mark.parametrize("question", ["Добавь встречу", "Add an event"])
def test_calendar_approval_distinguishes_years(calendar, name, all_day, question):
    descriptions = []
    for year in (2027, 2038):
        args = {**ARGS, "day": f"{year}-11-20", "all_day": all_day}
        if all_day:
            args.update(start_time=None, end_time=None)
        if name != "add_to_ai_calendar":
            args["calendar_event_id"] = 5
        if name == "remove_from_ai_calendar":
            args = {"calendar_event_id": 5}
            calendar.events["ih:u1", 5] = personal_calendar.PersonalEvent(
                5, "Встреча", datetime(year, 11, 20, 15, tzinfo=settings.tz), None, all_day, "108"
            )
        from catix.agent.calendar_approval import LOCAL_CALENDAR_APPROVAL

        describe = LOCAL_CALENDAR_APPROVAL[name]["description"]
        description = describe({"name": name, "args": args}, {"messages": [HumanMessage(question)]}, SimpleNamespace(context=SITE))
        assert str(year) in description
        if not all_day:
            assert "15:00" in description
        descriptions.append(description)
    assert descriptions[0] != descriptions[1]
    assert calendar.writes == []


def test_approved_calendar_event_is_persisted_and_exported_in_the_real_feed(calendar_db):
    agent, config, _ = run_action("add_to_ai_calendar", ARGS)
    paused = agent.get_state(config).interrupts[0]
    assert calendar_db.execute("SELECT count(*) AS n FROM personal_events").fetchone()["n"] == 0
    agent.invoke(Command(resume={paused.id: {"decisions": [{"type": "approve"}]}}), config, context=SITE)
    assert calendar_db.execute("SELECT count(*) AS n FROM personal_events").fetchone()["n"] == 1
    feed = personal_calendar.ics("ih:u1")
    assert "SUMMARY:Встреча" in feed and "LOCATION:108" in feed
    assert "SUMMARY:Встреча" not in personal_calendar.ics("ih:other")
    saved = personal_calendar.between("ih:u1", datetime.combine(DAY, time.min, settings.tz),
                                       datetime.combine(DAY + timedelta(days=1), time.min, settings.tz))[0]
    assert saved.starts_at == datetime.combine(DAY, time(15), settings.tz)
    # The next turn's explicit update changes this same row, not a second calendar event.
    agent, config, _ = run_action("update_ai_calendar", {**ARGS, "calendar_event_id": saved.id, "start_time": "15:30"})
    paused = agent.get_state(config).interrupts[0]
    assert personal_calendar.event_of("ih:u1", saved.id) == saved
    agent.invoke(Command(resume={paused.id: {"decisions": [{"type": "approve"}]}}), config, context=SITE)
    changed = personal_calendar.event_of("ih:u1", saved.id)
    assert changed is not None and changed.starts_at == datetime.combine(DAY, time(15, 30), settings.tz)
    assert calendar_db.execute("SELECT count(*) AS n FROM personal_events").fetchone()["n"] == 1


def test_calendar_write_binding_requires_site_identity_but_read_is_always_local():
    from catix.agent.core import LocalCalendarAccessMiddleware

    def offered(context):
        request = SimpleNamespace(runtime=SimpleNamespace(context=context), tools=TOOLS,
                                  override=lambda **kw: SimpleNamespace(**kw))
        return {t.name for t in LocalCalendarAccessMiddleware._without(request).tools}

    writes = {"add_to_ai_calendar", "update_ai_calendar", "remove_from_ai_calendar"}
    for context in (None, AgentContext(), AgentContext(user_telegram_id=42),
                    AgentContext(innohassle_id="u1"), AgentContext(innohassle_token=SecretStr("token"))):
        assert "get_my_ai_calendar" in offered(context)
        assert {"search_api_tools", "call_api_tool"} <= offered(context)
        assert not writes & offered(context)
    assert writes | {"get_my_ai_calendar"} <= offered(SITE)


@pytest.mark.parametrize("name", ["add_to_ai_calendar", "update_ai_calendar", "remove_from_ai_calendar"])
def test_bot_guessing_hidden_write_cannot_prompt_or_mutate(calendar, monkeypatch, name):
    def forbidden(*args, **kwargs):
        pytest.fail("Bot mutations must not resolve ownership via service auth")

    monkeypatch.setattr(personal_calendar, "telegram_key", forbidden)
    args = {} if name == "remove_from_ai_calendar" else dict(ARGS)
    if name != "add_to_ai_calendar":
        args["calendar_event_id"] = 5
    agent = build_agent(ScriptedModel(responses=[call(name, args, "bot"), AIMessage(content="Доступно на сайте.")]), guardrail=False)
    config = {"configurable": {"thread_id": "bot-write"}}
    out = agent.invoke({"messages": [HumanMessage("Добавь встречу")]}, config, context=AgentContext(user_telegram_id=42))
    assert not agent.get_state(config).interrupts and calendar.writes == []
    result = next(m for m in out["messages"] if isinstance(m, ToolMessage))
    assert json.loads(str(result.content))["done"] is False


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_remove_is_a_root_approval_and_removes_only_owned_record(calendar, decision):
    agent, config, _ = run_action("remove_from_ai_calendar", {"calendar_event_id": 5, "runtime": {"context": {"innohassle_id": "other"}}})
    paused = agent.get_state(config).interrupts[0]
    request = paused.value["action_requests"][0]
    assert request["name"] == "remove_from_ai_calendar" and "Встреча" in request["description"]
    assert calendar.writes == []
    agent.invoke(Command(resume={paused.id: {"decisions": [{"type": decision}]}}), config, context=SITE)
    assert calendar.writes == ([("ih:u1", 5, "delete")] if decision == "approve" else [])


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_real_api_decision_resumes_root_calendar_once(calendar, monkeypatch, decision):
    import asyncio
    from catix.api import ask
    from tests.test_api import FakeChats

    fake = FakeChats()
    monkeypatch.setattr(ask, "chats", fake)
    monkeypatch.setattr(ask.titles, "name", lambda question: "Calendar")
    monkeypatch.setattr(ask.groups, "scoped_chat_ids", lambda *a: set())
    monkeypatch.setattr(ask.groups, "effective_group", lambda *a: ask.groups.ALL)
    agent = build_agent(ScriptedModel(responses=[call("add_to_ai_calendar", ARGS, "api-local"), AIMessage(content="Запрос обработан.")]), guardrail=False)
    monkeypatch.setattr(ask, "agent", lambda: agent)
    user = ask.UserTokenData(innohassle_id="u1", email="a@innopolis.university", token=SecretStr("calendar-user-token"))
    chat_id = fake.start("u1", "Добавь встречу")
    async def scenario():
        waiting = await ask.run("Добавь встречу", chat_id, user)
        assert waiting.approval.actions[0].name == "add_to_ai_calendar"
        assert calendar.writes == []
        with pytest.raises(ask.NothingToDecide):
            await ask.run("Добавь встречу", chat_id, user, decision=ask.AskDecision(decision=decision, approval_id="wrong"))
        answer = await ask.run("Добавь встречу", chat_id, user, decision=ask.AskDecision(decision=decision, approval_id=waiting.approval.id))
        assert answer.approval is None and fake.waiting(chat_id) is None
        with pytest.raises(ask.NothingToDecide):
            await ask.run("Добавь встречу", chat_id, user, decision=ask.AskDecision(decision=decision))
    asyncio.run(scenario())
    assert len(calendar.writes) == (1 if decision == "approve" else 0)


def test_root_approval_uses_current_question_language_and_shows_cleared_fields(calendar):
    from catix.agent.calendar_approval import LOCAL_CALENDAR_APPROVAL

    request = {"name": "update_ai_calendar", "args": {"calendar_event_id": 5, "title": "New title",
               "day": DAY.isoformat(), "start_time": "15:00"}}
    description = LOCAL_CALENDAR_APPROVAL["update_ai_calendar"]["description"](
        request, {"messages": [HumanMessage("Привет"), AIMessage(content="Здравствуйте"), HumanMessage("Update my meeting")]},
        SimpleNamespace(context=SITE))
    assert "Update event" in description and "Встреча" in description and "#5" in description
    assert "no end time" in description and "no place specified" in description
    assert all(value in description for value in (str(DAY.year), "15:00", "New title"))


@pytest.mark.parametrize("site", [True, False])
def test_personal_agenda_parallel_external_and_local_root_reads(calendar, monkeypatch, site):
    from catix.agent import api_tools, calendar_tools
    from threading import Barrier

    barrier, external, local = Barrier(2), [], []
    def request(name, arguments, *args, **kwargs):
        external.append((name, arguments))
        barrier.wait(timeout=5)
        return {"schedule": [{"title": "Physics", "date": DAY.isoformat()}], "bookings": []}
    def events(key, start, end):
        local.append((key, start, end))
        barrier.wait(timeout=5)
        return [{"title": "Personal event"}]
    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    monkeypatch.setattr(personal_calendar, "telegram_key", lambda uid: "ih:u1" if uid == 42 else None)
    monkeypatch.setattr(calendar_tools, "events_between", events)
    period = {"date_from": DAY.isoformat(), "date_to": DAY.isoformat()}
    name = "account_get_my_schedule" if site else "schedule_get_schedule"
    message = AIMessage(content="", tool_calls=[
        {"name": "call_api_tool", "args": {"name": name, "arguments": period}, "id": "external"},
        {"name": "get_my_ai_calendar", "args": period, "id": "local"},
    ])
    agent = build_agent(ScriptedModel(responses=[message, AIMessage(content="Physics; Personal event.")]), guardrail=False)
    config = {"configurable": {"thread_id": "agenda"}}
    context = SITE if site else AgentContext(user_telegram_id=42, study_group="B26-CSE-01")
    out = agent.invoke({"messages": [HumanMessage("Что у меня завтра?")]}, config, context=context)
    assert not agent.get_state(config).interrupts
    assert local == [("ih:u1", DAY, DAY)]
    assert external, [(m.name, m.content) for m in out["messages"] if isinstance(m, ToolMessage)]
    assert external == [("call_tool", {"name": name, "arguments": period if site else {**period, "group": "B26-CSE-01"}})]
    results = [m for m in out["messages"] if isinstance(m, ToolMessage)]
    assert {m.name for m in results} == {"call_api_tool", "get_my_ai_calendar"}
    assert all("error" not in json.loads(str(m.content)) for m in results)
