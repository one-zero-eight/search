"""Explicit MCP sport integrations. Business rules execute here, not in the agent."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from catix.innohassle.client import ServiceError
from datetime import date, datetime, time, timedelta
from typing import Annotated

from fastmcp.dependencies import Depends
from fastmcp.tools import tool
from pydantic import Field

from catix.innohassle.mcp_declarations import metadata, require_sport, result_boundary
from catix.settings import settings

SPORT_PAGE = "https://innohassle.ru/sport"


MAX_TRAININGS = 40


DEFAULT_DAYS = 7


NOT_STUDENT = "The asker has no sport hours: InNoHassle Sport does not know them as a student."


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
    start, end = (_local(t["start"]), _local(t["end"]))
    item: dict = {"training_id": t["id"], "date": start.strftime("%Y-%m-%d %a"), "name": training_name(t),
                  "starts_at": start.isoformat(), "ends_at": end.isoformat()}
    if not t.get("is_all_day"):
        item["time"] = f"{start:%H:%M}-{end:%H:%M}"
    else:
        item["all_day"] = True
    if place := (t.get("training_location") or {}).get("name"):
        item["place"] = place
    if (capacity := t.get("max_checkins")) is not None:
        item["places_left"] = max(0, capacity - (t.get("checkins_count") or 0))
    if t.get("is_accredited") is False:
        item["accredited"] = False
    if t.get("is_paid"):
        item["paid"] = True
    return item


def _matches(t: dict, wanted: str) -> bool:
    wanted = wanted.casefold().strip()
    names = (t.get("sport_name"), t.get("display_name"), t.get("group_name"), t.get("training_custom_name"))
    return any((wanted in (n or "").casefold() for n in names))


def _day_start(day: date) -> datetime:
    return datetime.combine(day, time.min, settings.tz)


@tool(**metadata())
@result_boundary()
def sport_get_training(
    training_id: Annotated[int, Field(gt=0)],
    *, token: str = Depends(require_sport),
) -> dict:
    """Read one exact Sport training: name, date, interval and place by training_id.

    Requires separate Sport sign-in. Does not establish personal signup eligibility.
    """
    from catix.innohassle import sport as sport_api

    training = sport_api.training(token, training_id)
    if (not isinstance(training, dict) or type(training.get("id")) is not int
            or training["id"] != training_id or type(training.get("is_all_day")) is not bool):
        raise ValueError("Unreadable training details.")
    names = [training.get(key) for key in ("training_custom_name", "sport_name", "display_name", "group_name")]
    if (any(name is not None and not isinstance(name, str) for name in names)
            or not any(isinstance(name, str) and name.strip() for name in names)):
        raise ValueError("Unreadable training name.")
    location = training.get("training_location")
    if location is not None and (not isinstance(location, dict)
            or not isinstance(location.get("name"), str) or not location["name"].strip()):
        raise ValueError("Unreadable training location.")
    start, end = _local(training["start"]), _local(training["end"])
    if end <= start:
        raise ValueError("Unreadable training interval.")
    return {"training": {**training_item(training), "timezone": str(settings.tz),
                         **({"all_day": True} if training["is_all_day"] else {}),
                         "starts_at": start.isoformat(), "ends_at": end.isoformat()}}


@tool(**metadata())
@result_boundary()
def sport_get_my_sport(*, token: str = Depends(require_sport)) -> dict:
    """Personal Sport summary: hours earned/required, debt, medical group and trainings.

    Requires InNoHassle sign-in and the separate Sport credential.
    """
    from catix.innohassle import sport as sport_api
    from catix.innohassle.client import ServiceError

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
    trainings, self_sport = (summary.get("hours_from_groups") or 0, summary.get("self_sport_hours") or 0)
    required, debt = (summary.get("required_hours") or 0, summary.get("debt") or 0)
    done = trainings + self_sport
    info = user["student_info"]
    hours = {
        "done": done,
        "from_trainings": trainings,
        "self_sport": self_sport,
        "required": required,
        "debt": debt,
        "left": max(0, required + debt - done),
    }
    result: dict = {
        "hours": hours,
        "medical_group": info.get("medical_group"),
        "student_status": info.get("student_status"),
        "checked_in": [training_item(t["training"]) for t in coming[:MAX_TRAININGS]],
        "page": SPORT_PAGE,
    }
    if end := semester.get("end"):
        result["semester"] = {
            "name": semester.get("name"),
            "ends": end,
            "days_left": max(0, (date.fromisoformat(end[:10]) - now.date()).days),
        }
    if debt:
        result["note"] = (
            "The debt is hours left over from earlier semesters: they are needed on top of this semester's."
        )
    return result


@tool(**metadata())
@result_boundary()
def sport_get_sport_trainings(
    date_from: date | None = None, date_to: date | None = None,
    sport: Annotated[str | None, Field(max_length=60)] = None,
    *, token: str = Depends(require_sport),
) -> dict:
    """Sport trainings in a date range, optionally filtered by sport, with signup availability.

    Requires InNoHassle sign-in and the separate Sport credential.
    """
    from catix.innohassle import sport as sport_api
    from catix.innohassle.client import ServiceError

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
            f" Sports with trainings then: {', '.join(names)}." if sport and names else ""
        )
    elif any((not t["checked_in"] and (not t["can_check_in"]) for t in trainings)):
        result["rules"] = (
            "can_check_in false: no places left, more than a week before the start, already over, or the asker has 4 hours that day (2 of one sport) already."
        )
    return result


@tool(**metadata())
@result_boundary()
def sport_get_sports(
    sport: Annotated[str | None, Field(max_length=60)] = None,
    *, token: str = Depends(require_sport),
) -> dict:
    """List available sports or details for a sport. Requires separate Sport sign-in."""
    from catix.innohassle import sport as sport_api
    from catix.innohassle.client import ServiceError

    try:
        found = sport_api.sports(token)
    except ServiceError as e:
        return {"error": _why(e)}
    if not sport:
        return {"sports": sorted((s["name"] for s in found)), "page": SPORT_PAGE}
    chosen = [s for s in found if sport.casefold().strip() in s["name"].casefold()]
    if not chosen:
        return {"error": f"No sport named '{sport}'.", "sports": sorted((s["name"] for s in found))}
    return {
        "sports": [
            {
                "sport_id": s["id"],
                "name": s["name"],
                "description": " ".join((s.get("description") or "").split())[:600] or None,
                "groups": [
                    {
                        "name": g.get("display_name"),
                        "capacity": g.get("capacity"),
                        "trainers": [
                            {"name": tr.get("full_name"), "email": tr.get("email")} for tr in g.get("trainers") or []
                        ],
                        "medical_groups": g.get("allowed_medical_groups"),
                        "accredited": g.get("is_accredited"),
                        **({"club": True} if g.get("is_club") else {}),
                        **({"paid": True} if g.get("is_paid") else {}),
                    }
                    for g in s.get("groups") or []
                ],
            }
            for s in chosen[:5]
        ],
        "page": SPORT_PAGE,
    }


@tool(**metadata(write=True))
@result_boundary(write=True)
def sport_sport_checkin(
    training_id: Annotated[int, Field(gt=0)], cancel: bool = False,
    *, token: str = Depends(require_sport),
) -> dict:
    """Sign up for a Sport training, or cancel the signup.
    Записаться на спортивную тренировку или отменить запись.

    Requires verified InNoHassle and Sport sign-in; client hosts handle confirmation.
    Never retry an unknown outcome automatically.
    """
    from catix.innohassle import sport as sport_api
    from catix.innohassle.client import ServiceError

    try:
        sport_api.check_in(token, training_id, not cancel)
    except ServiceError as e:
        return {"done": False, "error": _why(e)}
    if cancel:
        return {
            "done": True,
            "training_id": training_id,
            "signed_up": False,
            "note": "Done: the asker is no longer signed up for this training (запись на тренировку отменена). Tell them.",
        }
    return {
        "done": True,
        "training_id": training_id,
        "signed_up": True,
        "note": "Done: the asker is signed up for this training (записан на тренировку). Tell them; it is on the sport page and in their InNoHassle calendar.",
    }
