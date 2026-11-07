"""The asker's sport (InNoHassle Sport, innohassle/sport.py), for the account helper on the site: their hours of the semester
and what is left to do, the trainings they may go to with free places and whether they are checked in, the sports and their
trainers; and checking them in to a training or cancelling it, which waits for their approval like the account helper's
other actions (account_tools.APPROVAL).

The sport is asked with the asker's own Sport token, which the site sends with a question (api/auth.py verify_asker): the
bots have none, nor does a site user who has no Innopolis account. Check-in rules are the sport's own (a week before the
start at most, while places are free, up to 4 hours a day and 2 of one sport); a refusal says why.
"""

from datetime import date, datetime, time, timedelta

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from catix.innohassle import sport as sport_api
from catix.innohassle.client import ServiceError
from catix.settings import settings

SPORT_PAGE = "https://innohassle.ru/sport"
MAX_TRAININGS = 40
DEFAULT_DAYS = 7  # a check-in opens a week before the training
NO_SPORT = (
    "The asker's sport is not reachable: the site did not pass their InNoHassle Sport access (it comes with signing in with an "
    f"Innopolis account). Ask them to open {SPORT_PAGE} once, or to sign in again; their hours and trainings are there too."
)
NOT_STUDENT = "The asker has no sport hours: InNoHassle Sport does not know them as a student."


def sport_token(runtime) -> str | None:
    token = getattr(getattr(runtime, "context", None), "sport_token", None)
    return token.get_secret_value() if token else None


def _local(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(settings.tz) if parsed.tzinfo else parsed.replace(tzinfo=settings.tz)


def _why(e: ServiceError) -> str:
    if e.status == 401:
        return f"InNoHassle Sport did not accept the asker's sign-in: ask them to open {SPORT_PAGE} or sign in again."
    if e.status == 403:
        return f"InNoHassle Sport does not let the asker do this: {e.detail}"
    return f"InNoHassle Sport refused: {e.detail}"


def training_name(t: dict) -> str:
    """A training as its card names it: the sport, with its group when it has another name."""
    name = t.get("training_custom_name") or t.get("sport_name") or t.get("display_name") or f"#{t.get('id')}"
    group = t.get("group_name") or t.get("display_name")
    if not group or group in name:
        return name
    return group if name in group else f"{name} ({group})"


def training_item(t: dict) -> dict:
    """A training as the model sees it, with the id sport_checkin takes."""
    start, end = _local(t["start"]), _local(t["end"])
    item: dict = {"training_id": t["id"], "date": start.strftime("%Y-%m-%d %a"), "name": training_name(t)}
    if not t.get("is_all_day"):
        item["time"] = f"{start:%H:%M}-{end:%H:%M}"
    if place := (t.get("training_location") or {}).get("name"):
        item["place"] = place
    if (capacity := t.get("max_checkins")) is not None:
        item["places_left"] = max(0, capacity - (t.get("checkins_count") or 0))
    if t.get("is_accredited") is False:
        item["accredited"] = False  # (its hours do not count towards the semester's)
    if t.get("is_paid"):
        item["paid"] = True
    return item


def _matches(t: dict, wanted: str) -> bool:
    wanted = wanted.casefold().strip()
    names = (t.get("sport_name"), t.get("display_name"), t.get("group_name"), t.get("training_custom_name"))
    return any(wanted in (n or "").casefold() for n in names)


def _day_start(day: date) -> datetime:
    return datetime.combine(day, time.min, settings.tz)


# ---- what the asker has --------------------------------------------------------------------------------------------------


@tool
def get_my_sport(runtime: ToolRuntime) -> dict:
    """The asker's sport this semester: the hours they have (from trainings and self-sport), the hours required and their debt
    from earlier semesters, what is left and the days to the semester's end, their medical group, and the trainings they are
    checked in to in the next two weeks."""
    if not (token := sport_token(runtime)):
        return {"error": NO_SPORT}
    try:
        user = sport_api.me(token)
        if not user.get("student_info"):
            return {"error": NOT_STUDENT, "page": SPORT_PAGE}
        summary = sport_api.hours(token, user["user_id"])
        semester = sport_api.current_semester(token)
        now = datetime.now(settings.tz)
        coming = [t for t in sport_api.my_trainings(token, now, now + timedelta(days=14)) if t.get("checked_in")]
    except ServiceError as e:
        return {"error": _why(e)}
    trainings, self_sport = summary.get("hours_from_groups") or 0, summary.get("self_sport_hours") or 0
    required, debt = summary.get("required_hours") or 0, summary.get("debt") or 0
    done = trainings + self_sport
    info = user["student_info"]
    hours = {"done": done, "from_trainings": trainings, "self_sport": self_sport, "required": required, "debt": debt,
             "left": max(0, required + debt - done)}  # fmt: skip
    result: dict = {
        "hours": hours,
        "medical_group": info.get("medical_group"),
        "student_status": info.get("student_status"),
        "checked_in": [training_item(t["training"]) for t in coming[:MAX_TRAININGS]],
        "page": SPORT_PAGE,
    }
    if end := semester.get("end"):
        result["semester"] = {"name": semester.get("name"), "ends": end, "days_left": max(0, (date.fromisoformat(end[:10]) - now.date()).days)}
    if debt:
        result["note"] = "The debt is hours left over from earlier semesters: they are needed on top of this semester's."
    return result


class GetSportTrainingsArgs(BaseModel):
    date_from: date | None = Field(None, description="YYYY-MM-DD, default today.")
    date_to: date | None = Field(None, description=f"YYYY-MM-DD inclusive, default date_from + {DEFAULT_DAYS - 1} days.")
    sport: str | None = Field(None, max_length=60, description="Only this sport, by a part of its name as in get_sports (such as 'Volleyball').")


@tool(args_schema=GetSportTrainingsArgs)
def get_sport_trainings(runtime: ToolRuntime, date_from: date | None = None, date_to: date | None = None, sport: str | None = None) -> dict:
    """The trainings the asker may go to in a period (by their medical group and level), each with the places left, whether
    they are checked in and whether they can check in now, and the `training_id` sport_checkin takes."""
    if not (token := sport_token(runtime)):
        return {"error": NO_SPORT}
    start = date_from or datetime.now(settings.tz).date()
    end = date_to or start + timedelta(days=DEFAULT_DAYS - 1)
    if end < start:
        return {"error": "date_to must not be before date_from."}
    try:
        found = sport_api.my_trainings(token, _day_start(start), _day_start(end + timedelta(days=1)))
    except ServiceError as e:
        return {"error": _why(e)}
    chosen = [t for t in found if not sport or _matches(t["training"], sport)]
    trainings = []
    for t in chosen[:MAX_TRAININGS]:
        item = training_item(t["training"])
        item["checked_in"] = bool(t.get("checked_in"))
        if not item["checked_in"]:
            item["can_check_in"] = bool(t.get("can_check_in"))
        trainings.append(item)
    result: dict = {"range": [start.isoformat(), end.isoformat()], "trainings": trainings, "page": SPORT_PAGE}
    if len(chosen) > MAX_TRAININGS:
        result["more"] = len(chosen) - MAX_TRAININGS
        result["note"] = "Not all are shown: ask for one sport or a shorter period."
    if not chosen:
        names = sorted({t["training"].get("sport_name") or t["training"].get("display_name") for t in found} - {None})
        result["note"] = (f"No training of '{sport}' in this period." if sport else "No training in this period.") + (
            f" Sports with trainings then: {', '.join(names)}." if sport and names else "")  # fmt: skip
    elif any(not t["checked_in"] and not t["can_check_in"] for t in trainings):
        result["rules"] = ("can_check_in false: no places left, more than a week before the start, already over, or the asker "
                           "has 4 hours that day (2 of one sport) already.")  # fmt: skip
    return result


class GetSportsArgs(BaseModel):
    sport: str | None = Field(None, max_length=60, description="One sport, by a part of its name: its groups, trainers, rules.")


@tool(args_schema=GetSportsArgs)
def get_sports(runtime: ToolRuntime, sport: str | None = None) -> dict:
    """The sports of the university's sport: without `sport` their names; with it, the sport's description and its groups
    with their trainers (name, email), capacity and the medical groups allowed."""
    if not (token := sport_token(runtime)):
        return {"error": NO_SPORT}
    try:
        found = sport_api.sports(token)
    except ServiceError as e:
        return {"error": _why(e)}
    if not sport:
        return {"sports": sorted(s["name"] for s in found), "page": SPORT_PAGE}
    chosen = [s for s in found if sport.casefold().strip() in s["name"].casefold()]
    if not chosen:
        return {"error": f"No sport named '{sport}'.", "sports": sorted(s["name"] for s in found)}
    return {"sports": [{
        "sport_id": s["id"], "name": s["name"], "description": " ".join((s.get("description") or "").split())[:600] or None,
        "groups": [{"name": g.get("display_name"), "capacity": g.get("capacity"),
                    "trainers": [{"name": tr.get("full_name"), "email": tr.get("email")} for tr in g.get("trainers") or []],
                    "medical_groups": g.get("allowed_medical_groups"), "accredited": g.get("is_accredited"),
                    **({"club": True} if g.get("is_club") else {}), **({"paid": True} if g.get("is_paid") else {})}
                   for g in s.get("groups") or []],
    } for s in chosen[:5]], "page": SPORT_PAGE}  # fmt: skip


# ---- what is done for the asker ------------------------------------------------------------------------------------------


class SportCheckinArgs(BaseModel):
    training_id: int = Field(gt=0, description="The `training_id` from get_sport_trainings or get_my_sport.")
    cancel: bool = Field(False, description="true: cancel the asker's check-in to this training.")


@tool(args_schema=SportCheckinArgs)
def sport_checkin(training_id: int, runtime: ToolRuntime, cancel: bool = False) -> dict:
    """Check the asker in to a sport training (or, with cancel, cancel their check-in). The asker approves or declines it
    before it is done: call it as soon as they asked, with a training from get_sport_trainings; never ask them yourself."""
    if not (token := sport_token(runtime)):
        return {"done": False, "error": NO_SPORT}
    try:
        sport_api.check_in(token, training_id, not cancel)
    except ServiceError as e:
        return {"done": False, "error": _why(e)}
    # (Said as "signed up": the model put "check-in" into Russian as "проверка".)
    if cancel:
        return {"done": True, "training_id": training_id, "signed_up": False,
                "note": "Done: the asker is no longer signed up for this training (запись на тренировку отменена). Tell them."}  # fmt: skip
    return {"done": True, "training_id": training_id, "signed_up": True,
            "note": "Done: the asker is signed up for this training (записан на тренировку). Tell them; it is on the sport page "
                    "and in their InNoHassle calendar."}  # fmt: skip


SPORT_TOOLS = [get_my_sport, get_sport_trainings, get_sports, sport_checkin]
