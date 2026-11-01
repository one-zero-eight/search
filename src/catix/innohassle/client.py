"""Thin client for the InNoHassle API gateway (https://api.innohassle.ru).

Clubs, events, maps and group timetables are public; the only token is the service one (scope `users`), sent only to
the users endpoint."""

import time
from typing import Any

import httpx

from catix.settings import settings

_client = httpx.Client(
    base_url=str(settings.innohassle_api),
    timeout=30,
    follow_redirects=True,
)


_cache: dict[str, tuple[float, Any]] = {}


def _get(path: str, *, params: dict | None = None, as_text: bool = False) -> Any:
    key = f"{path}?{sorted((params or {}).items())}"
    if (hit := _cache.get(key)) and time.monotonic() - hit[
        0
    ] < settings.innohassle_cache_ttl:
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


def events_ics() -> str:
    return _get("/schedule/v0/events.ics", as_text=True)


def search_areas(query: str) -> list[dict]:
    return _get("/maps/v0/scenes/areas/search", params={"query": query})


def scenes() -> list[dict]:
    return _get("/maps/v0/scenes/")


class ServiceTokenError(Exception):
    """The service token is missing or lacks the `users` scope."""


def study_group_by_telegram_id(telegram_id: int) -> str | None:
    """The study group (SSO `group`, e.g. B26-CSE-01) InNoHassle knows for a Telegram id; None if the person is not
    registered there or has no group (staff). Needs a token with the `users` scope."""
    if not settings.innohassle_service_token:
        raise ServiceTokenError("INNOHASSLE_SERVICE_TOKEN is not set")
    resp = _client.get(
        f"accounts/v0/users/by-telegram-id/{telegram_id}",
        headers={"Authorization": f"Bearer {settings.innohassle_service_token.get_secret_value()}"},
    )
    if resp.status_code == 404:
        return None
    if resp.status_code in (401, 403):
        raise ServiceTokenError(f"InNoHassle refused the service token: {resp.text[:120]}")
    resp.raise_for_status()
    sso = resp.json().get("innopolis_sso") or {}
    return sso.get("group") or None


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
