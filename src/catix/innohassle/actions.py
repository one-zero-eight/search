"""Static response DTOs and bounded GET projection for explicit MCP functions.

No discovery, operation catalogue or request schemas: paths and typed arguments
belong to the function declarations in mcp_tools.py.
"""
import json

import httpx
from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

MAX_BYTES = 1_000_000
MAX_ITEMS = 40
MAX_RESULT_CHARS = 20_000


class ReadError(Exception):
    """Safe failure, never containing upstream diagnostics or credentials."""


class Projection(BaseModel):
    # Unknown upstream fields are discarded, including nested IPP/owner data.
    model_config = ConfigDict(extra="ignore", strict=True)


class Printer(Projection):
    display_name: str
    cups_name: str


class PrinterStatus(Projection):
    printer: Printer
    offline: bool
    paper_percentage: int | None
    toner_percentage: int | None


class Area(Projection):
    title: str | None
    ru_title: str | None
    description: str | None


class AreaHit(Projection):
    scene_id: str
    area: Area


class Scene(Projection):
    scene_id: str
    title: str
    ru_title: str | None


class Club(Projection):
    title: str
    short_description: str | None
    is_active: bool


class Booking(Projection):
    time_start: str
    time_end: str


class Location(Projection):
    display_name: str


class EventData(Projection):
    name: str | None
    starts_at: str
    duration_hours: float
    location: Location


class Event(Projection):
    id: str
    data: EventData


class ReadResult[T: Projection](BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_id: str
    data: list[T]
    total: int
    truncated: bool
    note: str


def read(path: str, response_model: type[Projection], parameters: dict, token: str | None,
         *, action_id: str, note: str) -> dict:
    """Internal HTTP helper: only guarded explicit functions supply these controls."""
    from catix.innohassle import client as backend

    headers = {"Authorization": f"Bearer {token}"} if token else {}
    parameters = {key: value for key, value in parameters.items() if value is not None}
    try:
        with backend._client.stream("GET", path, headers=headers, params=parameters,
                                    follow_redirects=False) as response:
            if response.status_code == 401:
                raise ReadError("InNoHassle did not accept the sign-in: sign in on the site again.")
            if response.status_code == 403:
                raise ReadError("This account does not have permission for that API action.")
            if response.status_code != 200:
                raise ReadError("InNoHassle API is unavailable or refused the request. Try again later.")
            raw = bytearray()
            for chunk in response.iter_bytes():
                raw.extend(chunk)
                if len(raw) > MAX_BYTES:
                    raise ReadError("InNoHassle returned an oversized response; it was not used.")
            data = json.loads(raw)
    except httpx.TimeoutException:
        # Let result_boundary preserve the upstream timeout as structured data.
        raise
    except (httpx.HTTPError, ValueError):
        raise ReadError("InNoHassle API is unavailable or returned unreadable JSON. Try again later.") from None
    try:
        # Validate the whole bounded response, not only its first displayed rows.
        parsed = TypeAdapter(list[response_model]).validate_python(data)
        visible = [row.model_dump(mode="json") for row in parsed[:MAX_ITEMS]]
        if len(json.dumps(visible, ensure_ascii=False)) > MAX_RESULT_CHARS:
            raise ValueError("Result too large")
    except (ValidationError, ValueError, TypeError):
        raise ReadError("InNoHassle returned an unexpected response; no reliable result is available.") from None
    return {"action_id": action_id, "data": visible, "total": len(parsed),
            "truncated": len(parsed) > MAX_ITEMS, "note": note}
