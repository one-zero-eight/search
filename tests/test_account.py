"""The account helper (agent/account_tools.py): on the site it works with the asker's InNoHassle token, and each action it asks
for waits for the asker's decision (HumanInTheLoopMiddleware). Without a model or InNoHassle: a scripted model asks for the
action, the services are fakes that record what was done."""

from datetime import datetime, time, timedelta, timezone
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.types import Command
from pydantic import SecretStr

from catix import personal_calendar
from catix.agent import account_tools, calendar_tools, roles
from catix.agent.core import ACCOUNT_HELPER, AccountOnTheSiteMiddleware, build_agent
from catix.agent.tools import TOOLS, AgentContext
from catix.innohassle import client as innohassle
from catix.settings import settings
from tests.test_roles import ScriptedModel

SITE = AgentContext(innohassle_token=SecretStr("user-token"), innohassle_id="u1")
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
        ("remove_from_ai_calendar", {"calendar_event_id": 5}, False),
        ("remove_from_ai_calendar", {"calendar_event_id": 0}, True),
    ],
)
def test_arguments_that_cannot_be_right_are_told_without_asking(name, args, wrong):
    assert (account_tools._problem(name, args) is not None) is wrong


# --- the asker's whole calendar and their AI Calendar ---

HACKATHON = personal_calendar.PersonalEvent(5, "Хакатон", datetime.combine(DAY, time(10), settings.tz),
                                            datetime.combine(DAY, time(18), settings.tz), False, "108", "https://t.me/c/1/2")  # fmt: skip


@pytest.fixture
def ai_calendar(monkeypatch):
    """The AI Calendar of the account u1 without the database: one event; the (key, id) removed."""
    removed: list[tuple[str, int]] = []
    monkeypatch.setattr(personal_calendar, "account_key", lambda innohassle_id, telegram_id=None: f"ih:{innohassle_id}")
    monkeypatch.setattr(personal_calendar, "between",
                        lambda key, start, end, limit=40: [HACKATHON] if key == "ih:u1" and start <= HACKATHON.starts_at < end else [])  # fmt: skip
    monkeypatch.setattr(personal_calendar, "event_of", lambda key, event_id: HACKATHON if (key, event_id) == ("ih:u1", 5) else None)
    monkeypatch.setattr(personal_calendar, "delete_event", lambda key, event_id: removed.append((key, event_id)) or event_id == 5)

    def telegram_key(telegram_id):
        if telegram_id != 7:
            raise personal_calendar.NoAccount(personal_calendar.NOT_LINKED)
        return "ih:u1"

    monkeypatch.setattr(personal_calendar, "telegram_key", telegram_key)
    return removed


def _ics(title: str, start: datetime, end: datetime) -> str:
    utc = lambda t: t.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")  # noqa: E731
    return ("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//test//test//EN\r\nBEGIN:VEVENT\r\n"
            f"UID:{title}@test\r\nDTSTAMP:{utc(start)}\r\nDTSTART:{utc(start)}\r\nDTEND:{utc(end)}\r\nSUMMARY:{title}\r\n"
            "END:VEVENT\r\nEND:VCALENDAR\r\n")  # fmt: skip


@pytest.fixture
def calendars(monkeypatch):
    """The asker's supported InNoHassle calendars that day, no bookings. Moodle is retired."""
    at = lambda h: datetime.combine(DAY, time(h), settings.tz)  # noqa: E731
    texts = {"class": _ics("Compiler Construction (lec)", at(9), at(10)), "sport": _ics("Плавание", at(19), at(20)),
             "event": _ics("Spooky Movie Night", at(21), at(23))}  # fmt: skip

    def calendar(token, kind):
        assert kind in texts, "the retired Moodle calendar must never be requested"
        return texts[kind]

    monkeypatch.setattr(innohassle, "my_calendar_ics", calendar)
    monkeypatch.setattr(innohassle, "my_music_room_bookings", lambda token: [])
    monkeypatch.setattr(innohassle, "my_room_bookings", lambda token, start, end: [])
    return texts


def test_the_schedule_has_every_calendar_of_the_asker_and_says_what_it_could_not_read(calendars, ai_calendar):
    out = account_tools.get_my_schedule.func(SimpleNamespace(context=SITE), DAY, DAY)
    assert [(i["kind"], i["time"], i["title"]) for i in out["schedule"]] == [
        ("class", "09:00-10:00", "Compiler Construction (lec)"), ("sport", "19:00-20:00", "Плавание"),
        ("event", "21:00-23:00", "Spooky Movie Night"),
    ]  # fmt: skip
    assert out["ai_calendar"] == [{"calendar_event_id": 5, "date": HACKATHON.starts_at.strftime("%Y-%m-%d %a"), "title": "Хакатон",
                                   "all_day": False, "starts_at": HACKATHON.starts_at.isoformat(), "ends_at": HACKATHON.ends_at.isoformat(),
                                   "time": "10:00-18:00", "place": "108", "source": "https://t.me/c/1/2"}]  # fmt: skip
    assert "not_read" not in out, "the retired Moodle calendar must not leave a warning"


def test_a_sign_in_that_innohassle_refuses_is_the_error_of_the_schedule(calendars, monkeypatch):
    def refused(token, kind):
        raise innohassle.ServiceError(401, "Invalid token")

    monkeypatch.setattr(innohassle, "my_calendar_ics", refused)
    assert "sign in" in account_tools.get_my_schedule.func(SimpleNamespace(context=SITE), DAY, DAY)["error"]


def test_the_ai_calendar_is_read_on_the_site_and_in_the_telegram_bot(ai_calendar):
    read = lambda context: calendar_tools.get_my_ai_calendar.func(SimpleNamespace(context=context), DAY, DAY)  # noqa: E731
    assert [e["title"] for e in read(SITE)["events"]] == ["Хакатон"]
    assert [e["title"] for e in read(AgentContext(user_telegram_id=7))["events"]] == ["Хакатон"], "the account linked to the Telegram"
    assert personal_calendar.CONNECT_TELEGRAM in read(AgentContext(user_telegram_id=8))["error"], "not linked: how to link it"
    assert read(AgentContext())["error"] == calendar_tools.NO_CALENDAR  # the CLI
    assert read(AgentContext(user_telegram_id=-7))["error"] == calendar_tools.NO_CALENDAR, "the Max bot: -its id, no Telegram"


def test_an_event_is_removed_from_the_ai_calendar_once_the_user_approves(ai_calendar):
    asked = "убери хакатон из моего календаря"
    script = [
        _call(ACCOUNT_HELPER, {"question": asked}, "s1"),
        _call("remove_from_ai_calendar", {"calendar_event_id": 5}, "h1"),
        AIMessage(content="Хакатон убран из календаря."),
        AIMessage(content="Готово: хакатон убран."),
    ]
    agent = build_agent(ScriptedModel(responses=script), guardrail=False)
    config = {"configurable": {"thread_id": "remove"}}
    agent.invoke({"messages": [{"role": "user", "content": asked}]}, config, context=SITE)
    paused = agent.get_state(config).interrupts
    assert len(paused) == 1 and not ai_calendar, "nothing is removed before the user decides"
    description = paused[0].value["action_requests"][0]["description"]
    assert "«Хакатон»" in description and "10:00–18:00" in description and "AI-календаря" in description
    out = agent.invoke(Command(resume={paused[0].id: {"decisions": [{"type": "approve"}]}}), config, context=SITE)
    assert ai_calendar == [("ih:u1", 5)] and out["messages"][-1].text == "Готово: хакатон убран."


def test_a_calendar_that_does_not_answer_leaves_the_others(calendars, ai_calendar, monkeypatch):
    import httpx

    def slow_sport(token, kind):
        if kind == "sport":
            raise httpx.ReadTimeout("timed out")
        return calendars.get(kind, calendars["class"])

    monkeypatch.setattr(innohassle, "my_calendar_ics", slow_sport)
    out = account_tools.get_my_schedule.func(SimpleNamespace(context=SITE), DAY, DAY)
    assert "sport" not in {i["kind"] for i in out["schedule"]} and "class" in {i["kind"] for i in out["schedule"]}
    assert "sport: InNoHassle did not answer (ReadTimeout)" in out["not_read"] and out["ai_calendar"]
