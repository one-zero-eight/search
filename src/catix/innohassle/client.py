"""Thin client for the InNoHassle API gateway (https://api.innohassle.ru).

Clubs, events, maps, the timetable and the music room's bookings are public; the service token (scope `users`) is sent only
to the users endpoint. What is the user's own (their schedule, bookings, enrolments) is asked with the user's own token,
which only the site has (api/auth.py): those calls are never cached, and the token is never kept."""

import time
from datetime import date, datetime
from typing import Any

import httpx

from catix.settings import settings

_client = httpx.Client(
    base_url=str(settings.innohassle_api),
    timeout=30,
    follow_redirects=True,
)


_cache: dict[str, tuple[float, Any]] = {}
BOOKINGS_TTL = 30  # seconds: the music room's bookings are looked at right before one is made


def _get(path: str, *, params: dict | None = None, as_text: bool = False, ttl: int | None = None) -> Any:
    key = f"{path}?{sorted((params or {}).items())}"
    ttl = settings.innohassle_cache_ttl if ttl is None else ttl
    if (hit := _cache.get(key)) and time.monotonic() - hit[0] < ttl:
        return hit[1]
    resp = _client.get(path.lstrip("/"), params=params)
    resp.raise_for_status()
    data = resp.text if as_text else resp.json()
    _cache[key] = (time.monotonic(), data)
    return data


def clubs() -> list[dict]:
    return _get("/clubs/v0/clubs/")


def club_leaders() -> dict[str, dict | None]:
    """Mapping leader innohassle_id -> leader (name, email, telegram_alias) or None."""
    return _get("/clubs/v0/leaders/")


def events(start: datetime, end: datetime) -> list[dict]:
    """The published university events (InNoHassle Events) starting between `start` and `end`: name, start, duration,
    place, hosts and how to enrol; without their descriptions (`event`)."""
    return _get("/events/v1/events/", params={"from": start.isoformat(), "to": end.isoformat()})


def event(event_id: str) -> dict:
    """One published event with its descriptions in each language (`locales`) and links."""
    return _get(f"/events/v1/events/{event_id}")


def search_areas(query: str) -> list[dict]:
    return _get("/maps/v0/scenes/areas/search", params={"query": query})


def scenes() -> list[dict]:
    return _get("/maps/v0/scenes/")


def timetable() -> dict:
    """The official timetable of the current term (Schedule Assistant): the term and its blocks, the rooms, the
    instructors, the student groups and the courses with their weekly classes and the changes made to them."""
    return _get("/schedule-assistant/v0/timetable")


def music_room_bookings(day: date) -> list[dict]:
    """The bookings of the music room on a day (id, user_alias, time_start, time_end in local time)."""
    return _get("/music-room/v0/bookings/daily_bookings", params={"date": day.isoformat()}, ttl=BOOKINGS_TTL)


class ServiceTokenError(Exception):
    """The service token is missing or lacks the `users` scope."""


def _user_by_telegram_id(telegram_id: int) -> dict | None:
    """The InNoHassle account linked to a Telegram id; None if the person is not registered there. Needs a token with the
    `users` scope."""
    if not settings.innohassle_service_token:
        raise ServiceTokenError("INNOHASSLE_SERVICE_TOKEN is not set")
    resp = _client.get(
        f"accounts/v0/users/by-telegram-id/{telegram_id}",
        headers={"Authorization": f"Bearer {settings.innohassle_service_token.get_secret_value()}"},
        timeout=10,  # A calendar button waits for it, and Telegram drops an answer to a button after 15 seconds.
    )
    if resp.status_code == 404:
        return None
    if resp.status_code in (401, 403):
        raise ServiceTokenError(f"InNoHassle refused the service token: {resp.text[:120]}")
    resp.raise_for_status()
    return resp.json()


def study_group_by_telegram_id(telegram_id: int) -> str | None:
    """The study group (SSO `group`, e.g. B26-CSE-01) InNoHassle knows for a Telegram id; None if the person is not
    registered there or has no group (staff)."""
    user = _user_by_telegram_id(telegram_id)
    sso = (user or {}).get("innopolis_sso") or {}
    return sso.get("group") or None


def user_id_by_telegram_id(telegram_id: int) -> str | None:
    """The InNoHassle id (the `uid` of the account's tokens) linked to a Telegram id; None if the person is not registered."""
    user = _user_by_telegram_id(telegram_id)
    return str(user["id"]) if user else None


def event_groups() -> list[dict]:
    """All schedule groups (academic groups, electives, sport, ...) with aliases and names."""
    return _get("/schedule/v0/event-groups/")["event_groups"]


def group_schedule_ics(alias: str) -> str:
    # The endpoint requires a user_id but serves the same public calendar for any value.
    return _get(
        f"/schedule/v0/{alias}.ics",
        params={"user_id": 0, "export_type": "group"},
        as_text=True,
    )


# ---- as the user, with their token ----------------------------------------------------------------------------


class ServiceError(Exception):
    """An InNoHassle service refused a request made as the user; `detail` is what it said."""

    def __init__(self, status: int, detail: str) -> None:
        super().__init__(f"{status}: {detail}")
        self.status, self.detail = status, detail


def _detail(resp: httpx.Response) -> str:
    """What a service said of a refused request: FastAPI's `detail` (a text or a list of validation errors), or its text."""
    try:
        body = resp.json()
    except ValueError:
        return resp.text[:300] or resp.reason_phrase
    detail = body.get("detail", body) if isinstance(body, dict) else body
    if isinstance(detail, list):
        return "; ".join(str(d.get("msg", d)) if isinstance(d, dict) else str(d) for d in detail)[:300]
    return str(detail)[:300]


def _as_user(method: str, path: str, token: str, *, params: dict | None = None, json: dict | None = None) -> httpx.Response:
    resp = _client.request(method, path.lstrip("/"), params=params, json=json, headers={"Authorization": f"Bearer {token}"}, timeout=20)
    if resp.status_code >= 400:
        raise ServiceError(resp.status_code, _detail(resp))
    return resp


# The user's own calendars, as the site's calendar shows them. all.ics is only the event groups (the classes of their groups
# and the groups they added, not hidden): sport, Moodle and the events they enrolled in are calendars of their own. (The
# music room and the room bookings are read from their services, with the ids a cancellation takes.)
MY_CALENDARS = {
    "class": "/schedule/v0/users/me/all.ics",
    "sport": "/schedule/v0/users/me/sport.ics",
    "deadline": "/schedule/v0/users/me/moodle.ics",  # 404 when the user's Moodle is not linked to InNoHassle
    "event": "/events/v1/users/me/events.ics",
}


def my_calendar_ics(token: str, kind: str) -> str:
    """One of the user's calendars (MY_CALENDARS) as iCalendar text."""
    return _as_user("GET", MY_CALENDARS[kind], token).text


def my_music_room_bookings(token: str) -> list[dict]:
    return _as_user("GET", "/music-room/v0/bookings/my_bookings", token).json()


def music_room_hours_left(token: str, day: date) -> tuple[float, float]:
    """(hours of the music room the user may still book on that day, in that week)."""
    daily = _as_user("GET", "/music-room/v0/users/me/remaining_daily_hours", token, params={"date": day.isoformat()}).json()
    weekly = _as_user("GET", "/music-room/v0/users/me/remaining_weekly_hours", token, params={"date": day.isoformat()}).json()
    return float(daily), float(weekly)


def book_music_room(token: str, start: datetime, end: datetime) -> dict:
    """Book the music room for the user; the booking. The times go in local time without an offset, as the service wants."""
    body = {"time_start": start.replace(tzinfo=None).isoformat(), "time_end": end.replace(tzinfo=None).isoformat()}
    booking = _as_user("POST", "/music-room/v0/bookings/", token, json=body).json()
    if not isinstance(booking, dict):  # It says why it did not book with a text and 200: "overlapping", no hours left...
        raise ServiceError(200, str(booking)[:300])
    return booking


def cancel_music_room(token: str, booking_id: int) -> None:
    if _as_user("DELETE", f"/music-room/v0/bookings/{booking_id}", token).json() is not True:
        raise ServiceError(200, "the music room did not cancel the booking")


def bookable_rooms(token: str) -> list[dict]:
    """The rooms the room booking service has (id, title, capacity, access_level, restrict_daytime); the same for
    everybody, so it is cached once read."""
    if (hit := _cache.get("room-booking:rooms")) and time.monotonic() - hit[0] < settings.innohassle_cache_ttl:
        return hit[1]
    rooms = _as_user("GET", "/room-booking/v0/rooms/", token).json()
    _cache["room-booking:rooms"] = (time.monotonic(), rooms)
    return rooms


def room_bookings(token: str, start: datetime, end: datetime) -> list[dict]:
    """The bookings of all the rooms (of the students' access level) between `start` and `end`."""
    return _as_user("GET", "/room-booking/v0/bookings/", token, params={"start": start.isoformat(), "end": end.isoformat()}).json()


def my_room_bookings(token: str, start: datetime, end: datetime) -> list[dict]:
    return _as_user("GET", "/room-booking/v0/bookings/my", token, params={"start": start.isoformat(), "end": end.isoformat()}).json()


def can_book_room(token: str, room_id: str, start: datetime, end: datetime) -> tuple[bool, str]:
    """(may the user book the room then, why not)."""
    answer = _as_user(
        "GET", f"/room-booking/v0/room/{room_id}/can-book", token, params={"start": start.isoformat(), "end": end.isoformat()}
    ).json()
    return bool(answer.get("can_book")), str(answer.get("reason_why_cannot") or "")


def book_room(token: str, room_id: str, title: str, start: datetime, end: datetime) -> dict:
    body = {"room_id": room_id, "title": title, "start": start.isoformat(), "end": end.isoformat()}
    return _as_user("POST", "/room-booking/v0/bookings/", token, json=body).json()


def cancel_room(token: str, outlook_booking_id: str) -> None:
    _as_user("DELETE", f"/room-booking/v0/bookings/{outlook_booking_id}", token)


def enroll(token: str, event_id: str) -> dict:
    return _as_user("POST", f"/events/v1/events/{event_id}/enroll", token).json()


def unenroll(token: str, event_id: str) -> dict:
    return _as_user("POST", f"/events/v1/events/{event_id}/unenroll", token).json()
