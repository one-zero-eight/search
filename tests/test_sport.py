"""The asker's sport (agent/sport_tools.py, innohassle/sport.py) with InNoHassle Sport faked: their hours and what is left, the
trainings they may go to, checking in only after they approve it, and the Sport token taken only from the site and only
when it is theirs (api/auth.py verify_asker)."""

import asyncio
from datetime import date, datetime, time, timedelta
from types import SimpleNamespace

import httpx
import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from pydantic import SecretStr

from catix.agent import account_tools, roles, sport_tools
from catix.agent.core import build_agent
from catix.agent.tools import AgentContext
from catix.api import auth
from catix.innohassle import client as innohassle
from catix.innohassle import sport as sport_api
from catix.settings import settings

SITE = AgentContext(innohassle_token=SecretStr("user-token"), innohassle_id="u1", sport_token=SecretStr("sport-token"))
NO_SPORT = AgentContext(innohassle_token=SecretStr("user-token"), innohassle_id="u1")
TODAY = datetime.now(settings.tz).date()
FRIDAY = TODAY + timedelta(days=2)


def _at(day: date, hour: int, minute: int = 0) -> str:
    return datetime.combine(day, time(hour, minute), settings.tz).isoformat()


def _training(training_id: int, sport: str, group: str, day: date, hour: int, *, taken: int = 3, capacity: int = 20, **more) -> dict:
    return {"id": training_id, "start": _at(day, hour), "end": _at(day, hour + 1, 30), "is_all_day": False,
            "training_location": {"id": 1, "name": "Sport Complex, Hall 1"}, "display_name": group, "sport_name": sport,
            "group_name": group, "training_custom_name": None, "is_accredited": True, "is_club": False, "is_paid": False,
            "sport_id": 1, "group_id": 1, "checkins_count": taken, "max_checkins": capacity, **more}  # fmt: skip


VOLLEYBALL = _training(11, "Volleyball", "Volleyball (Beginners)", FRIDAY, 18)
FULL = _training(12, "Volleyball", "Volleyball (Advanced)", FRIDAY, 20, taken=20)
SWIMMING = _training(13, "Swimming", "Swimming", TODAY + timedelta(days=1), 9)


@pytest.fixture
def sport(monkeypatch):
    """InNoHassle Sport of a student checked in to the swimming tomorrow; what was checked in (training_id, checkin)."""
    done: list[tuple[int, bool]] = []
    schedule = [{"training": SWIMMING, "checked_in": True, "can_check_in": False},
                {"training": VOLLEYBALL, "checked_in": False, "can_check_in": True},
                {"training": FULL, "checked_in": False, "can_check_in": False}]  # fmt: skip

    def mine(token, start, end):
        assert token == "sport-token"
        return [t for t in schedule if start <= datetime.fromisoformat(t["training"]["start"]) < end]

    def check_in(token, training_id, checkin):
        if training_id == 12:
            raise innohassle.ServiceError(400, "You cannot check in at this training")
        done.append((training_id, checkin))

    monkeypatch.setattr(sport_api, "me", lambda token: {"user_id": 42, "full_name": "Ivan", "student_info":
                        {"student_status": "Normal", "medical_group": "General", "is_college": False}})  # fmt: skip
    monkeypatch.setattr(sport_api, "hours", lambda token, student_id: {"semester_id": 5, "debt": 2, "self_sport_hours": 4,
                        "hours_from_groups": 10, "required_hours": 30} if student_id == 42 else {})  # fmt: skip
    monkeypatch.setattr(sport_api, "current_semester", lambda token: {"name": "F26", "end": (TODAY + timedelta(days=40)).isoformat()})
    monkeypatch.setattr(sport_api, "my_trainings", mine)
    monkeypatch.setattr(sport_api, "training", lambda token, training_id: {11: VOLLEYBALL, 12: FULL, 13: SWIMMING}[training_id])
    monkeypatch.setattr(sport_api, "check_in", check_in)
    return done


def test_the_askers_hours_and_what_is_left(sport):
    out = sport_tools.get_my_sport.func(SimpleNamespace(context=SITE))
    assert out["hours"] == {"done": 14, "from_trainings": 10, "self_sport": 4, "required": 30, "debt": 2, "left": 18}
    assert out["semester"] == {"name": "F26", "ends": (TODAY + timedelta(days=40)).isoformat(), "days_left": 40}
    assert out["medical_group"] == "General" and "debt" in out["note"]
    assert [t["training_id"] for t in out["checked_in"]] == [13], "only the trainings they are checked in to"


def test_the_trainings_they_may_go_to_with_places_and_check_in(sport):
    out = sport_tools.get_sport_trainings.func(SimpleNamespace(context=SITE), TODAY, FRIDAY, "volley")
    assert [(t["training_id"], t["places_left"], t["can_check_in"]) for t in out["trainings"]] == [(11, 17, True), (12, 0, False)]
    first = out["trainings"][0]
    assert first == {"training_id": 11, "date": FRIDAY.strftime("%Y-%m-%d %a"), "name": "Volleyball (Beginners)", "time": "18:00-19:30",
                     "place": "Sport Complex, Hall 1", "places_left": 17, "checked_in": False, "can_check_in": True}  # fmt: skip
    assert "no places left" in out["rules"]
    swimming = sport_tools.get_sport_trainings.func(SimpleNamespace(context=SITE), TODAY, FRIDAY, "swim")["trainings"]
    assert swimming[0]["checked_in"] is True and "can_check_in" not in swimming[0]
    none = sport_tools.get_sport_trainings.func(SimpleNamespace(context=SITE), TODAY, FRIDAY, "Tennis")
    assert none["trainings"] == [] and "Swimming" in none["note"] and "Volleyball" in none["note"]


def test_a_training_is_named_once():
    assert sport_tools.training_name(VOLLEYBALL) == "Volleyball (Beginners)"
    assert sport_tools.training_name(SWIMMING) == "Swimming"
    assert sport_tools.training_name(_training(1, "Yoga", "Group 2", TODAY, 9)) == "Yoga (Group 2)"


def test_without_the_sport_token_nothing_is_asked(sport):
    runtime = SimpleNamespace(context=NO_SPORT)
    assert sport_tools.get_my_sport.func(runtime) == {"error": sport_tools.NO_SPORT}
    assert sport_tools.get_sport_trainings.func(runtime)["error"] == sport_tools.NO_SPORT
    assert sport_tools.sport_checkin.func(11, runtime) == {"done": False, "error": sport_tools.NO_SPORT} and not sport


def test_checking_in_waits_for_the_askers_approval(sport):
    account, names = roles.ROLES["account"], {t.name for t in sport_tools.SPORT_TOOLS}
    assert "sport_checkin" in account.approval and names <= account.tools
    for role in roles.ROLES.values():
        if role.name != "account":
            assert not role.tools & names, f"the {role.name} helper has no sport token"
    runtime = SimpleNamespace(context=SITE)
    state = {"messages": [HumanMessage("запиши меня на волейбол в пятницу")]}
    described = account_tools.APPROVAL["sport_checkin"]["description"]({"args": {"training_id": 11}}, state, runtime)
    assert described.startswith("Записать вас на тренировку «Volleyball (Beginners)»") and "18:00–19:30, Sport Complex, Hall 1" in described
    cancel = account_tools.APPROVAL["sport_checkin"]["description"]({"args": {"training_id": 13, "cancel": True}}, state, runtime)
    assert cancel.startswith("Отменить вашу запись на тренировку «Swimming»")

    assert sport_tools.sport_checkin.func(11, runtime)["done"] is True and sport == [(11, True)]
    assert sport_tools.sport_checkin.func(13, runtime, cancel=True)["done"] is True and sport[-1] == (13, False)
    refused = sport_tools.sport_checkin.func(12, runtime)
    assert refused == {"done": False, "error": "InNoHassle Sport refused: You cannot check in at this training"}


@pytest.mark.parametrize(("args", "wrong"), [({"training_id": 11}, False), ({"training_id": 0}, True), ({"training_id": "volleyball"}, True)])
def test_a_check_in_that_cannot_be_right_is_not_put_to_the_asker(args, wrong):
    assert (account_tools._problem("sport_checkin", args) is not None) is wrong


def test_the_client_asks_the_sport_as_the_user(monkeypatch):
    asked: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        asked.append(request)
        if request.url.path.endswith("/checkin"):
            return httpx.Response(400, json={"detail": "You have already checked in at this training"})
        return httpx.Response(200, json=[])

    monkeypatch.setattr(sport_api, "_client", httpx.Client(base_url=str(settings.sport_api), transport=httpx.MockTransport(answer)))
    start = datetime.combine(TODAY, time.min, settings.tz)
    assert sport_api.my_trainings("sport-token", start, start + timedelta(days=1)) == []
    with pytest.raises(innohassle.ServiceError) as refused:
        sport_api.check_in("sport-token", 11, True)
    assert refused.value.status == 400 and "already checked in" in refused.value.detail
    schedule, checkin = asked
    assert str(schedule.url).startswith("https://sport.innopolis.university/api/v3/users/me/schedule?start=")
    assert schedule.url.params["start"] == start.isoformat() and schedule.headers["Authorization"] == "Bearer sport-token"
    assert checkin.method == "POST" and str(checkin.url) == "https://sport.innopolis.university/api/v3/trainings/11/checkin?checkin=true"


@pytest.mark.parametrize(("header", "kept"), [
    ("sport-mine", True),  # the same Innopolis email, whatever its case
    ("sport-other", False),  # another user's
    ("sport-bad", False),  # expired or not InNoHassle's
    (None, False),
])  # fmt: skip
def test_the_sport_token_is_taken_only_when_it_is_the_askers(monkeypatch, header, kept):
    emails = {"sport-mine": "A@innopolis.university", "sport-other": "b@innopolis.university"}
    monkeypatch.setattr(auth.innohassle_token, "sport_email", emails.get)
    user = auth.UserTokenData(innohassle_id="u1", email="a@innopolis.university", token=SecretStr("good"))
    asker = asyncio.run(auth.verify_asker(user, header))
    assert (asker.sport_token is not None and asker.sport_token.get_secret_value() == header) is kept
    assert "sport" not in asker.model_dump_json() and "sport-" not in repr(asker), "never shown, never kept"


class ScriptedModel(FakeMessagesListChatModel):
    """Answers with the given messages in turn, whichever agent asks (the supervisor and the helpers share one model)."""

    def bind_tools(self, tools, **kwargs):
        return self


def test_a_ref_in_the_account_helpers_report_is_invented_and_goes():
    # The account helper's tools give no sources: it wrote the training 13 as [m13], which may be a source of an earlier question.
    script = [AIMessage(content="", tool_calls=[{"name": "ask_account", "args": {"question": "сколько у меня часов спорта"}, "id": "c1", "type": "tool_call"}]),
              AIMessage(content="У вас 14 часов из 30 [m13]. Вы записаны на плавание [m1, m2] [m3]."),
              AIMessage(content="У вас 14 часов из 30.")]  # fmt: skip
    agent = build_agent(ScriptedModel(responses=script), guardrail=False)
    out = agent.invoke({"messages": [{"role": "user", "content": "сколько у меня часов спорта"}]}, {"configurable": {"thread_id": "s"}}, context=SITE)
    report = next(m for m in out["messages"] if isinstance(m, ToolMessage))
    assert report.name == "ask_account" and report.content == "У вас 14 часов из 30. Вы записаны на плавание."
    assert roles.ROLES["account"].cites is False and all(r.cites for r in roles.ROLES.values() if r.name != "account")
