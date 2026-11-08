"""Thin client for the InNoHassle API gateway (https://api.innohassle.ru).

Clubs, events, maps, the timetable and the music room's bookings are public; the service token (scope `users`) is sent only
to the users endpoint. What is the user's own (their schedule, bookings, enrolments) is asked with the user's own token,
which only the site has (api/auth.py): those calls are never cached, and the token is never kept. What is the same for
everybody is kept in the shared cache (common/cache.py) for settings.innohassle_cache_ttl."""

import math
from datetime import date, datetime
from http.cookiejar import CookieJar, DefaultCookiePolicy
from typing import Any
from urllib.parse import quote, urlencode

import httpx

from catix.common import cache
from catix.innohassle.identifiers import validate_outlook_id, validate_room_id
from catix.settings import settings


def _http_client(base_url: str, *, timeout: float = 20, **kwargs) -> httpx.Client:
    """Shared connections, never shared user sessions or redirected credentials."""
    return httpx.Client(base_url=base_url, timeout=httpx.Timeout(timeout, connect=5), follow_redirects=False,
                        cookies=CookieJar(policy=DefaultCookiePolicy(allowed_domains=[])), **kwargs)


_client = _http_client(str(settings.innohassle_api), timeout=30)


BOOKINGS_TTL = 30  # seconds: public timetable only; availability and writes bypass it


def _get(path: str, *, params: dict | None = None, as_text: bool = False, ttl: int | None = None) -> Any:
    def load() -> Any:
        resp = _client.get(path.lstrip("/"), params=params)
        resp.raise_for_status()
        return resp.text if as_text else resp.json()

    key = f"innohassle:{path}?{urlencode(sorted((params or {}).items()))}"
    return cache.cached(key, settings.innohassle_cache_ttl if ttl is None else ttl, load)


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


def music_room_bookings(day: date, *, fresh: bool = False) -> list[dict]:
    """Public occupied intervals; bypass shared cache for availability and writes."""
    path, parameters = "/music-room/v0/bookings/daily_bookings", {"date": day.isoformat()}
    if fresh:
        return _check_response(_client.get(path.lstrip("/"), params=parameters)).json()
    return _get(path, params=parameters, ttl=BOOKINGS_TTL)


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


def _check_response(resp: httpx.Response) -> httpx.Response:
    if 300 <= resp.status_code < 400:
        raise httpx.HTTPStatusError("API redirects are refused.", request=resp.request, response=resp)
    if resp.request.method not in {"GET", "HEAD", "OPTIONS"} and (resp.status_code == 408 or resp.status_code >= 500):
        # These are not definite domain refusals: the mutation may have committed.
        # Escape legacy ServiceError handlers; MCP reports an unknown outcome without retrying.
        raise httpx.HTTPStatusError("The API mutation outcome is unknown.", request=resp.request, response=resp)
    if resp.status_code >= 400:
        raise ServiceError(resp.status_code, _detail(resp))
    return resp


def _as_user(method: str, path: str, token: str, *, params: dict | None = None, json: dict | None = None) -> httpx.Response:
    resp = _client.request(method, path.lstrip("/"), params=params, json=json, headers={"Authorization": f"Bearer {token}"},
                           timeout=httpx.Timeout(20, connect=5))
    return _check_response(resp)


# The user's own calendars, as the site's calendar shows them. all.ics is only the event groups (the classes of their groups
# and the groups they added, not hidden): sport and the events they enrolled in are calendars of their own. (The
# music room and the room bookings are read from their services, with the ids a cancellation takes.)
MY_CALENDARS = {
    "class": "/schedule/v0/users/me/all.ics",
    "sport": "/schedule/v0/users/me/sport.ics",
    "event": "/events/v1/users/me/events.ics",
}


def my_calendar_ics(token: str, kind: str) -> str:
    """One of the user's calendars (MY_CALENDARS) as iCalendar text."""
    return _as_user("GET", MY_CALENDARS[kind], token).text


def my_music_room_bookings(token: str) -> list[dict]:
    return _as_user("GET", "/music-room/v0/bookings/my_bookings", token).json()


def my_music_room_profile(token: str) -> dict:
    """Verify registration/access in Music Room without retaining profile data."""
    return _as_user("GET", "/music-room/v0/users/me", token).json()


def music_room_hours_left(token: str, day: date) -> tuple[float, float]:
    """(hours of the music room the user may still book on that day, in that week)."""
    daily = _as_user("GET", "/music-room/v0/users/me/remaining_daily_hours", token, params={"date": day.isoformat()}).json()
    weekly = _as_user("GET", "/music-room/v0/users/me/remaining_weekly_hours", token, params={"date": day.isoformat()}).json()
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in (daily, weekly)):
        raise ValueError("Invalid Music Room quota response.")
    return float(daily), float(weekly)


def book_music_room(token: str, start: datetime, end: datetime) -> dict:
    """Book the music room for the user; the booking. The times go in local time without an offset, as the service wants."""
    body = {"time_start": start.replace(tzinfo=None).isoformat(), "time_end": end.replace(tzinfo=None).isoformat()}
    booking = _as_user("POST", "/music-room/v0/bookings/", token, json=body).json()
    if not isinstance(booking, dict):  # It says why it did not book with a text and 200: "overlapping", no hours left...
        raise ServiceError(200, str(booking)[:300])
    return booking


def cancel_music_room(token: str, booking_id: int) -> None:
    if type(booking_id) is not int:
        raise ValueError("Invalid music room booking identifier.")
    if _as_user("DELETE", f"/music-room/v0/bookings/{booking_id}", token).json() is not True:
        raise ServiceError(200, "the music room did not cancel the booking")


def bookable_rooms(token: str) -> list[dict]:
    """Fresh room inventory including staff rooms; each still requires a personal permission check."""
    rooms = _as_user("GET", "/room-booking/v0/rooms/", token, params={"include_red": True}).json()
    if not isinstance(rooms, list):
        raise ValueError("Invalid room inventory response.")
    for room in rooms:
        if not isinstance(room, dict) or not isinstance(room.get("id"), str):
            raise ValueError("Invalid room inventory entry.")
        validate_room_id(room["id"])
    return rooms


def room_bookings(token: str, start: datetime, end: datetime, *, room_id: str | None = None) -> list[dict]:
    """Read occupancy again, optionally for one exact room (including restricted rooms)."""
    params = {"start": start.isoformat(), "end": end.isoformat()}
    if room_id is not None:
        params["room_id"] = validate_room_id(room_id)
    else:
        params["include_red"] = "true"
    return _as_user("GET", "/room-booking/v0/bookings/", token, params=params).json()


def my_room_bookings(token: str, start: datetime, end: datetime) -> list[dict]:
    return _as_user("GET", "/room-booking/v0/bookings/my", token, params={"start": start.isoformat(), "end": end.isoformat()}).json()


def can_book_room(token: str, room_id: str, start: datetime, end: datetime) -> tuple[bool, str]:
    """Personal access/time permission and refusal reason, NOT an occupancy check."""
    segment = quote(validate_room_id(room_id), safe="")
    answer = _as_user(
        "GET", f"/room-booking/v0/room/{segment}/can-book", token, params={"start": start.isoformat(), "end": end.isoformat()}
    ).json()
    if not isinstance(answer, dict) or type(answer.get("can_book")) is not bool:
        raise ValueError("Invalid room permission response.")
    reason = answer.get("reason_why_cannot", "")
    if not isinstance(reason, str):
        raise ValueError("Invalid room permission reason.")
    return answer["can_book"], reason


def book_room(token: str, room_id: str, title: str, start: datetime, end: datetime) -> dict:
    validate_room_id(room_id)
    body = {"room_id": room_id, "title": title, "start": start.isoformat(), "end": end.isoformat()}
    return _as_user("POST", "/room-booking/v0/bookings/", token, json=body).json()


def cancel_room(token: str, outlook_booking_id: str) -> None:
    segment = quote(validate_outlook_id(outlook_booking_id), safe="")
    _as_user("DELETE", f"/room-booking/v0/bookings/{segment}", token)


def enroll(token: str, event_id: str) -> dict:
    return _as_user("POST", f"/events/v1/events/{event_id}/enroll", token).json()


def unenroll(token: str, event_id: str) -> dict:
    return _as_user("POST", f"/events/v1/events/{event_id}/unenroll", token).json()
