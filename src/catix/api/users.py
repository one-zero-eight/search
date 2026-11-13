"""The user's personal calendar: the events they added with "➕ В мой календарь" under an answer of the site or of the
Telegram bot (personal_calendar.py), kept under their InNoHassle account.

    GET  /users/my-calendar.ics                    the calendar for InNoHassle and calendar apps
    POST /users/my-calendar/events/{proposal_id}   the button under an answer of /ask/ (its `calendar_events`)

The private feed requires the account token. External subscriptions use a separately issued, revocable read-only key
at /users/calendar-export.ics, without source-message provenance. Events added in the Telegram bot are there when
Telegram is linked to the account.
"""

import asyncio

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from catix import calendar_export, personal_calendar
from catix.api.auth import AccountDep
from catix.api.schemas import AddedCalendarEvent


class CalendarExportKeyStatus(BaseModel):
    access_key: str | None


class CalendarExportKeyCreated(BaseModel):
    access_key: str


router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/my-calendar.ics",
    response_class=Response,
    responses={
        200: {"description": "The user's events as iCalendar", "content": {"text/calendar": {}}},
        401: {"description": "No token or a bad one"},
    },
)
def my_calendar(account: AccountDep) -> Response:
    """The events the user added to their calendar under the answers of the site and of the Telegram bot (all of them,
    past ones too)."""
    key = personal_calendar.account_key(account.innohassle_id, account.telegram_id)
    return Response(personal_calendar.ics(key), media_type="text/calendar; charset=utf-8")


@router.post(
    "/my-calendar/events/{proposal_id}",
    responses={
        200: {"description": "The event is in the user's calendar"},
        401: {"description": "No token or a bad one"},
        404: {"description": "The offer expired (it lives 48 hours) or there is no such offer"},
    },
)
async def add_calendar_event(account: AccountDep, proposal_id: str) -> AddedCalendarEvent:
    """Add an event offered under an answer of /ask/ (`calendar_events`, its `id`) to the user's calendar. The same event
    twice is one."""
    key = await asyncio.to_thread(personal_calendar.account_key, account.innohassle_id, account.telegram_id)
    title = await asyncio.to_thread(personal_calendar.add_proposal, key, proposal_id)
    if title is None:
        raise HTTPException(404, "The offer expired or there is no such offer")
    return AddedCalendarEvent(proposal_id=proposal_id, title=title)


@router.get(
    "/my-calendar/export-key",
    response_model=CalendarExportKeyStatus,
    responses={401: {"description": "No token or a bad one"}},
)
def calendar_export_key_status(account: AccountDep) -> Response:
    access_key = calendar_export.get_key(f"ih:{account.innohassle_id}")
    return JSONResponse({"access_key": access_key}, headers={"Cache-Control": "no-store"})


@router.post(
    "/my-calendar/export-key",
    response_model=CalendarExportKeyCreated,
    responses={401: {"description": "No token or a bad one"}},
)
def create_calendar_export_key(account: AccountDep) -> Response:
    access_key = calendar_export.create_key(f"ih:{account.innohassle_id}")
    return JSONResponse({"access_key": access_key}, headers={"Cache-Control": "no-store"})


@router.delete("/my-calendar/export-key", status_code=204, responses={401: {"description": "No token or a bad one"}})
def revoke_calendar_export_key(account: AccountDep) -> Response:
    calendar_export.revoke_key(f"ih:{account.innohassle_id}")
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.get(
    "/calendar-export.ics",
    response_class=Response,
    responses={
        200: {"description": "AI Calendar events without source-message provenance", "content": {"text/calendar": {}}},
        404: {"description": "Missing, invalid or revoked subscription key"},
    },
)
def public_calendar_export(access_key: str | None = None) -> Response:
    headers = {
        "Cache-Control": "no-store",
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
    }
    owner = calendar_export.owner_for_key(access_key) if access_key is not None and calendar_export.valid_key_shape(access_key) else None
    if owner is None:
        return Response("Calendar not found", status_code=404, media_type="text/plain", headers=headers)
    body = personal_calendar.ics(owner, include_sources=False)
    return Response(body, media_type="text/calendar; charset=utf-8", headers=headers)
