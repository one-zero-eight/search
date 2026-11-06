"""The account helper (agent/account_tools.py): on the site it works with the asker's InNoHassle token, and each action it asks
for waits for the asker's decision (HumanInTheLoopMiddleware). Without a model or InNoHassle: a scripted model asks for the
action, the services are fakes that record what was done."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.types import Command
from pydantic import SecretStr

from catix.agent import account_tools, roles
from catix.agent.core import ACCOUNT_HELPER, AccountOnTheSiteMiddleware, build_agent
from catix.agent.tools import TOOLS, AgentContext
from catix.innohassle import client as innohassle
from catix.settings import settings
from tests.test_roles import ScriptedModel

SITE = AgentContext(innohassle_token=SecretStr("user-token"))
DAY = (datetime.now(settings.tz) + timedelta(days=2)).date()


def _call(name: str, args: dict, call_id: str) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}])


@pytest.fixture
def music_room(monkeypatch):
    """The music room's service: nothing booked that day, 4 hours left; the bookings made."""
    made: list[tuple[str, datetime, datetime]] = []
    monkeypatch.setattr(innohassle, "music_room_bookings", lambda day: [])
    monkeypatch.setattr(innohassle, "music_room_hours_left", lambda token, day: (4.0, 10.0))

    def book(token, start, end):
        made.append((token, start, end))
        return {"id": 77, "time_start": start.isoformat(), "time_end": end.isoformat()}

    monkeypatch.setattr(innohassle, "book_music_room", book)
    return made


def _booking_run(*after_decision: AIMessage, slot=("18:00", "19:00")):
    script = [
        _call(ACCOUNT_HELPER, {"question": "забронируй музкомнату послезавтра с 18 до 19"}, "s1"),  # the supervisor
        _call("book_music_room", {"day": DAY.isoformat(), "time_from": slot[0], "time_to": slot[1]}, "h1"),  # the helper
        *after_decision,
    ]
    agent = build_agent(ScriptedModel(responses=script), guardrail=False)
    config = {"configurable": {"thread_id": "account"}}
    agent.invoke({"messages": [{"role": "user", "content": "забронируй музкомнату послезавтра с 18 до 19"}]}, config, context=SITE)
    return agent, config


def test_an_action_waits_for_the_users_approval_and_is_done_once_approved(music_room):
    agent, config = _booking_run(AIMessage(content="Музкомната забронирована."), AIMessage(content="Готово: музкомната ваша."))
    paused = agent.get_state(config).interrupts
    assert len(paused) == 1 and not music_room, "nothing is booked before the user decides"
    request = paused[0].value["action_requests"][0]
    assert request["name"] == "book_music_room"
    assert "музыкальную комнату" in request["description"] and "18:00–19:00" in request["description"]
    assert paused[0].value["review_configs"][0]["allowed_decisions"] == ["approve", "reject"]

    out = agent.invoke(Command(resume={paused[0].id: {"decisions": [{"type": "approve"}]}}), config, context=SITE)
    assert [(token, f"{start:%H:%M}", f"{end:%H:%M}") for token, start, end in music_room] == [("user-token", "18:00", "19:00")]
    assert out["messages"][-1].text == "Готово: музкомната ваша."
    assert not agent.get_state(config).interrupts


def test_a_rejected_action_is_not_done_and_the_helper_is_told_so(music_room):
    agent, config = _booking_run(AIMessage(content="Бронь отменена вами."), AIMessage(content="Хорошо, не бронирую."))
    paused = agent.get_state(config).interrupts
    out = agent.invoke(
        Command(resume={paused[0].id: {"decisions": [{"type": "reject", "message": account_tools.DECLINED}]}}), config, context=SITE
    )
    assert not music_room
    report = next(m for m in out["messages"] if isinstance(m, ToolMessage) and m.name == ACCOUNT_HELPER)
    told = [r for r in report.artifact["results"] if "declined" in r]
    assert told, "the helper gets the user's refusal as the result of the call"


def test_an_impossible_action_is_not_put_to_the_user_and_does_nothing(music_room):
    yesterday = (datetime.now(settings.tz) - timedelta(days=1)).date()
    script = [
        _call(ACCOUNT_HELPER, {"question": "забронируй музкомнату вчера"}, "s1"),
        _call("book_music_room", {"day": yesterday.isoformat(), "time_from": "18:00", "time_to": "19:00"}, "h1"),
        AIMessage(content="Это время уже прошло."),
        AIMessage(content="Это время уже прошло: назовите другое."),
    ]
    agent = build_agent(ScriptedModel(responses=script), guardrail=False)
    config = {"configurable": {"thread_id": "past"}}
    out = agent.invoke({"messages": [{"role": "user", "content": "забронируй музкомнату вчера"}]}, config, context=SITE)
    assert not agent.get_state(config).interrupts and not music_room
    report = next(m for m in out["messages"] if isinstance(m, ToolMessage) and m.name == ACCOUNT_HELPER)
    assert any("already past" in r for r in report.artifact["results"])


def test_the_account_helper_is_offered_only_with_the_users_token():
    tools = [SimpleNamespace(name="ask_docs"), SimpleNamespace(name=ACCOUNT_HELPER)]

    def request(context):
        return SimpleNamespace(runtime=SimpleNamespace(context=context), tools=tools,
                               override=lambda **kw: SimpleNamespace(tools=kw["tools"]))  # fmt: skip

    offered = lambda context: [t.name for t in AccountOnTheSiteMiddleware._without(request(context)).tools]  # noqa: E731
    assert offered(AgentContext()) == ["ask_docs"]  # the bots, the CLI
    assert offered(None) == ["ask_docs"]
    assert offered(SITE) == ["ask_docs", ACCOUNT_HELPER]


def test_the_account_tools_without_a_token_say_that_it_is_done_on_the_site():
    runtime = SimpleNamespace(context=AgentContext())
    assert "only on the site" in account_tools.get_my_schedule.func(runtime)["error"]
    result = account_tools.book_music_room.func(DAY, datetime.min.time(), datetime.max.time(), runtime)
    assert "only on the site" in result["error"]


def test_the_token_is_never_shown():
    assert "user-token" not in repr(SITE) and "user-token" not in str(SITE)


def test_every_action_of_a_helper_waits_for_a_decision():
    known = {t.name for t in TOOLS}
    account = roles.ROLES["account"]
    assert account.approval == set(account_tools.APPROVAL) and account.approval <= account.tools <= known
    for role in roles.ROLES.values():
        if role.name != "account":
            assert not role.tools & set(account_tools.APPROVAL), f"the {role.name} helper may not act for the user"


@pytest.mark.parametrize(
    ("name", "args", "wrong"),
    [
        ("book_music_room", {"day": DAY.isoformat(), "time_from": "19:00", "time_to": "18:00"}, True),
        ("book_music_room", {"day": DAY.isoformat(), "time_from": "18:00", "time_to": "19:00"}, False),
        ("book_music_room", {"day": DAY.isoformat(), "time_from": "25:00", "time_to": "19:00"}, True),
        ("enroll_in_event", {"event_id": "6ae86975e82e1733c875ed01"}, False),
        ("enroll_in_event", {"event_id": "Spooky Movie Night"}, True),
        ("cancel_booking", {"service": "music_room", "booking_id": "77"}, False),
        ("cancel_booking", {"service": "music_room", "booking_id": "tomorrow"}, True),
        ("cancel_booking", {"service": "room", "booking_id": "AAMkAD="}, False),
    ],
)
def test_arguments_that_cannot_be_right_are_told_without_asking(name, args, wrong):
    assert (account_tools._problem(name, args) is not None) is wrong
