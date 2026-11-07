"""Client of InNoHassle Sport (settings.sport_api, the API of sport.innopolis.university), asked as the user with their Sport
token, which only the site has (api/auth.py verify_asker): every endpoint wants it, the list of sports too. Nothing of the
user's is cached; the sports and the current semester, the same for everyone, are kept for a while (common/cache.py)."""

from datetime import datetime
from typing import Any

import httpx

from catix.common import cache
from catix.innohassle.client import ServiceError, _check_response, _http_client
from catix.settings import settings

_client = _http_client(str(settings.sport_api))
SHARED_TTL = 3600  # seconds


def _call(method: str, path: str, token: str, *, params: dict | None = None) -> httpx.Response:
    resp = _client.request(method, path.lstrip("/"), params=params, headers={"Authorization": f"Bearer {token}"})
    return _check_response(resp)


def _shared_get(path: str, token: str) -> Any:
    """What is the same for every user (a valid token reads it), cached for SHARED_TTL."""
    return cache.cached(f"sport:{path}", SHARED_TTL, lambda: _call("GET", path, token).json())


def me(token: str) -> dict:
    """The user: user_id (their student id too), full_name, student_info (medical_group, student_status) or None."""
    return _call("GET", "/users/me", token).json()


def hours(token: str, student_id: int) -> dict:
    """The student's hours of the current semester: hours_from_groups, self_sport_hours, required_hours, debt."""
    return _call("GET", f"/students/{student_id}/hours-summary", token).json()


def current_semester(token: str) -> dict:
    """The current semester: name, start, end (YYYY-MM-DD), required_hours."""
    return _shared_get("/semesters/current", token)


def sports(token: str) -> list[dict]:
    """The sports with their groups: trainers, capacity, the medical groups allowed, accredited/club/paid."""
    return _shared_get("/sports", token)


def my_trainings(token: str, start: datetime, end: datetime) -> list[dict]:
    """The trainings the student may go to between `start` and `end` (by their medical group and level), each with
    `checked_in` and `can_check_in`."""
    return _call("GET", "/users/me/schedule", token, params={"start": start.isoformat(), "end": end.isoformat()}).json()


def training(token: str, training_id: int) -> dict:
    return _call("GET", f"/trainings/{training_id}", token).json()


def check_in(token: str, training_id: int, checkin: bool) -> None:
    """Check the student in to a training (checkin) or cancel their check-in. Raises ServiceError with why it is refused."""
    _call("POST", f"/trainings/{training_id}/checkin", token, params={"checkin": checkin})
