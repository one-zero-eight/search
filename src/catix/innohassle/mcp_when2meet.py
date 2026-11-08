"""Four explicit When2Meet MCP tools; host consent is deliberately separate."""
from typing import Annotated, Literal

from fastmcp.dependencies import Depends
from fastmcp.tools import tool
from pydantic import AfterValidator, Field

from catix.innohassle import client as api
from catix.innohassle import when2meet
from catix.innohassle.mcp_declarations import (
    invalid_arguments,
    metadata,
    require_innohassle,
    result_boundary,
)


@tool(**metadata())
@result_boundary()
def when2meet_get_my_meetings(
    status: Literal['active', 'archived'] = 'active',
    scope: Literal['all', 'owned', 'participating'] = 'all',
    *, token: str = Depends(require_innohassle),
) -> dict:
    """List my When2Meet polls / Мои встречи, опросы для выбора времени.

    Sign-in required. Defaults to active owned and participating meetings, deduplicated by ID.
    Use archived for past meetings; report truncation. Details and common slots require
    when2meet_get_meeting. This is not the user's calendar or a room reservation list.
    """
    return when2meet.listing(token, status, scope)


@tool(**metadata())
@result_boundary()
def when2meet_get_meeting(
    meeting_ref: when2meet.MeetingRef,
    *, token: str = Depends(require_innohassle),
) -> dict:
    """Read a When2Meet meeting and participants' availability / Когда встретимся, общие слоты.

    Use its exact URL-safe slug or lowercase ObjectId, not a URL. Sign-in required.
    common_slots intersects actual participants, not people who have not responded; no
    participants means no common slots. is_me/my_availability use verified identity.
    Report truncation; never use a truncated selection as a complete replacement.
    No time selection, room booking or calendar changes.
    """
    return _details(when2meet.read(token, meeting_ref))


@tool(**metadata(write=True))
@result_boundary(write=True)
def when2meet_create_meeting(
    name: Annotated[str, Field(min_length=1, max_length=200, pattern=r'\S')],
    slots: Annotated[list[when2meet.Slot], Field(min_length=1, max_length=2000)],
    timezone: Annotated[str, Field(max_length=100), AfterValidator(when2meet.valid_timezone)] = 'Europe/Moscow',
    specific_time: bool = True,
    description: Annotated[str | None, Field(max_length=2000)] = None,
    *, token: str = Depends(require_innohassle),
) -> dict:
    """Create a When2Meet availability poll / Создать встречу, опрос времени.

    Requires an explicit name and timezone-aware RFC3339 slots; offsets are preserved.
    specific_time=true means time slots; false means date-choice display, still with explicit
    timestamps. Client hosts handle confirmation. Does not book a room or publish a calendar.
    Never retry unknown outcomes automatically.
    """
    payload = {'name': name, 'slots': [slot.isoformat() for slot in slots], 'timezone': timezone,
               'specific_time': specific_time, 'description': description}
    try:
        response = api._as_user('POST', when2meet.BASE, token, json=payload)
    except api.ServiceError as error:
        return _refused(error)
    created = when2meet.Meeting.model_validate(when2meet.decode(response))
    confirmed = when2meet.read(token, created.id)
    if (confirmed.slug != created.slug or confirmed.name != name or sorted(confirmed.slots) != sorted(slots)
            or confirmed.timezone != timezone or confirmed.specific_time != specific_time
            or confirmed.description != description):
        raise ValueError('Created meeting did not match the requested values on readback.')
    return {'done': True, 'meeting': _details(confirmed)}


@tool(**metadata(write=True))
@result_boundary(write=True)
def when2meet_set_my_availability(
    meeting_ref: when2meet.MeetingRef,
    availability: Annotated[list[when2meet.Slot], Field(max_length=2000)],
    *, token: str = Depends(require_innohassle),
) -> dict:
    """Replace my When2Meet availability / Указать моё свободное время для встречи.

    Explicit timezone-aware RFC3339 slots only; [] clears current selections. Replaces rather
    than appends: read the meeting first to preserve existing choices for add/remove requests.
    Checks fresh meeting slots and archive state, then verifies the signed-in user's selection.
    Upstream can retain hidden removed-slot selections; mismatched readback stays unknown.
    Client hosts handle confirmation. Never retry unknown outcomes automatically.
    """
    from catix.innohassle.mcp_server import _identity

    identity = _identity.get()
    if identity is None or not identity.uid:
        return {'done': False, 'code': 'identity_unverified', 'error': 'The signed-in user could not be verified.'}
    try:
        current = when2meet.read(token, meeting_ref)
    except Exception:  # noqa: BLE001 -- every failure here precedes the first write
        # Read-only phase: no mutation has started, so refusal is definite.
        return {'done': False, 'code': 'meeting_unverified',
                'error': 'The meeting could not be verified; availability was not changed.'}
    if current.is_archived:
        return {'done': False, 'code': 'meeting_archived',
                'error': 'This meeting is archived; availability was not changed.'}
    if not set(availability).issubset(current.slots):
        return invalid_arguments('Availability must contain only slots from the current meeting; nothing was changed.')
    try:
        response = api._as_user(
            'PUT', when2meet.path(meeting_ref) + '/participants', token,
            json={'availability': [slot.isoformat() for slot in availability]},
        )
    except api.ServiceError as error:
        return _refused(error)
    when2meet.Meeting.model_validate(when2meet.decode(response))
    confirmed = when2meet.read(token, meeting_ref)
    mine = [person for person in confirmed.participants if person.user_id == identity.uid]
    if (confirmed.id != current.id or confirmed.slug != current.slug or len(mine) != 1
            or set(mine[0].availability) != set(availability)):
        raise ValueError('The signed-in availability could not be confirmed on readback.')
    return {'done': True, 'meeting': _details(confirmed)}


def _details(event: when2meet.Meeting) -> dict:
    from catix.innohassle.mcp_server import _identity

    identity = _identity.get()
    if identity is None or not identity.uid:
        raise ValueError('The signed-in user could not be verified.')
    return when2meet.details(event, identity.uid)


def _refused(error: api.ServiceError) -> dict:
    # _as_user raises a different exception for 408/5xx. Never echo API detail.
    return {'done': False, 'code': 'service_refused', 'status': error.status,
            'error': 'When2Meet refused the request; nothing was changed.'}
