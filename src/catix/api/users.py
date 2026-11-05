"""The user's personal calendar: the events they added with "➕ В мой календарь" under an answer of the site or of the
Telegram bot (personal_calendar.py), kept under their InNoHassle account.

    GET  /users/my-calendar.ics                    the calendar for InNoHassle and calendar apps
    POST /users/my-calendar/events/{proposal_id}   the button under an answer of /ask/ (its `calendar_events`)

The address is the same for everyone; nobody's calendar opens without their token. Events added in the Telegram bot are
there when Telegram is linked to the account.
"""

import asyncio

from fastapi import APIRouter, HTTPException, Response

from catix import personal_calendar
from catix.api.auth import AccountDep
from catix.api.schemas import AddedCalendarEvent

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
