"""Uncached When2Meet transport and bounded, privacy-minimal response projections.

Contract inspected at one-zero-eight/monorepo cebefd0658786a0820369e93398a5c573bdeca7f.
Current slugs use secrets.token_urlsafe(6); lookup imposes no slug length constraint.
Accept bounded URL-safe slugs and lowercase ObjectIds without repairing either.
Upstream normalizes timestamps to whole seconds and can retain availability for
removed (hidden) slots. Never reproduce that normalization silently: exact readback
checks may therefore leave a write unconfirmed. No retry is safe automatically.
No generic URLs, credentials, room actions or calendar publishing are exposed here.
"""
import re
from datetime import datetime
from typing import Annotated
from urllib.parse import quote
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from pydantic import (
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    TypeAdapter,
)

from catix.innohassle import client

BASE = '/when2meet/v0/meetings/'
# The website's meeting route uses the validated public slug, not the database ID.
PAGE = 'https://innohassle.ru/when2meet/{slug}'
# Adapter safety/output limits, not advertised upstream service limits.
MAX_ITEMS = 40
MAX_SHOWN_SLOTS = 200
MAX_TEXT = 2000
MAX_RESPONSE_BYTES = 2_000_000
REF_PATTERN = r'^[A-Za-z0-9_-]{1,128}$'
MeetingRef = Annotated[str, Field(pattern=REF_PATTERN)]


def _rfc3339(value):
    if isinstance(value, str):
        if not re.fullmatch(
            r'[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt](?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]'
            r'(?:\.[0-9]+)?(?:[Zz]|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])', value,
        ):
            raise ValueError('Date-time must use RFC 3339 format with a timezone.')
        fraction = re.search(r'\.([0-9]+)', value)
        if fraction and len(fraction[1]) > 6:
            raise ValueError('Date-time supports at most six fractional-second digits; precision must not be truncated.')
        try:
            return datetime.fromisoformat(value.upper())
        except ValueError:
            raise ValueError('Date-time must use a valid RFC 3339 timestamp.') from None
    return value


Slot = Annotated[
    AwareDatetime,
    BeforeValidator(_rfc3339),
    Field(json_schema_extra={'pattern': r'^[^.]+(?:\.[0-9]{1,6}(?:[Zz]|[+-][0-9]{2}:[0-9]{2}))?$'}),
]


def valid_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ValueError, ZoneInfoNotFoundError):
        raise ValueError('timezone must be a valid IANA timezone name.') from None
    return value


class Projection(BaseModel):
    model_config = ConfigDict(strict=True, extra='ignore')


class Participant(Projection):
    user_id: Annotated[str, Field(min_length=1, max_length=128)]
    name: str | None = None
    availability: list[Slot]


class SelectedTime(Projection):
    start: Slot
    end: Slot


class TimeRange(Projection):
    start: Annotated[str, Field(max_length=32)]
    end: Annotated[str, Field(max_length=32)]


class Summary(Projection):
    id: Annotated[str, Field(pattern=r'^[0-9a-f]{24}$')]
    slug: MeetingRef
    name: str
    description: str | None = None
    created_at: Slot
    archive_after: Slot
    is_archived: bool
    participants_count: Annotated[int, Field(ge=0)]
    selected_time: SelectedTime | None = None
    archived_at: Slot | None = None


class Meeting(Projection):
    id: Annotated[str, Field(pattern=r'^[0-9a-f]{24}$')]
    slug: MeetingRef
    name: str
    description: str | None = None
    slots: list[Slot]
    timezone: Annotated[str, Field(max_length=100)] = 'UTC'
    specific_time: bool = False
    participants: list[Participant]
    created_at: Slot
    archive_after: Slot
    is_archived: bool
    selected_time: SelectedTime | None = None
    time_range: TimeRange | None = None
    archived_at: Slot | None = None
    owner_id: Annotated[str | None, Field(max_length=128)] = None


def decode(response: httpx.Response):
    # _as_user buffers HTTP responses; bound parsing/projection here as well.
    if len(response.content) > MAX_RESPONSE_BYTES:
        raise ValueError('When2Meet response exceeds the supported size.')
    return response.json()


def path(meeting_ref: str) -> str:
    if not re.fullmatch(REF_PATTERN, meeting_ref):
        raise ValueError('Invalid When2Meet reference.')
    return BASE + quote(meeting_ref, safe='')


def listing(token: str, status: str, scope: str) -> dict:
    paths = ([BASE] if scope == 'owned' else [BASE + 'participating'] if scope == 'participating'
             else [BASE, BASE + 'participating'])
    unique: dict[str, Summary] = {}
    for endpoint in paths:
        rows = TypeAdapter(list[Summary]).validate_python(
            decode(client._as_user('GET', endpoint, token, params={'status': status})))
        for row in rows:
            unique.setdefault(row.id, row)
    meetings = []
    truncated = len(unique) > MAX_ITEMS
    for row in list(unique.values())[:MAX_ITEMS]:
        data = row.model_dump(mode='json')
        data['page'] = PAGE.format(slug=row.slug)
        for field in ('name', 'description'):
            _bound_text(data, field)
        meetings.append(data)
    return {'meetings': meetings, 'total': len(unique), 'truncated': truncated, 'status': status, 'scope': scope}


def read(token: str, meeting_ref: str) -> Meeting:
    event = Meeting.model_validate(decode(client._as_user('GET', path(meeting_ref), token)))
    expected = event.id if re.fullmatch(r'[0-9a-f]{24}', meeting_ref) else event.slug
    if meeting_ref != expected:
        raise ValueError('When2Meet returned a different meeting.')
    return event


def details(event: Meeting, uid: str) -> dict:
    data = event.model_dump(mode='json')
    data['page'] = PAGE.format(slug=event.slug)
    data['truncated'] = False
    mine = next((person for person in event.participants if person.user_id == uid), None)
    data['my_participation'] = mine is not None
    data['my_availability'] = [slot.isoformat() for slot in mine.availability] if mine else []
    _bound_list(data, 'my_availability', MAX_SHOWN_SLOTS)
    data['truncated'] |= data['my_availability_truncated']
    for field in ('name', 'description'):
        _bound_text(data, field)
    data['participants'] = data['participants'][:MAX_ITEMS]
    for participant in data['participants']:
        participant['is_me'] = participant['user_id'] == uid
        _bound_text(participant, 'name')
        _bound_list(participant, 'availability', MAX_SHOWN_SLOTS)
        data['truncated'] |= participant.get('name_truncated', False) or participant['availability_truncated']
    common = set(event.slots) if event.participants else set()
    for participant in event.participants:
        common.intersection_update(participant.availability)
    data['common_slots'] = list(dict.fromkeys(slot.isoformat() for slot in event.slots if slot in common))
    data['participants_count'] = len(event.participants)
    data['participants_truncated'] = len(event.participants) > MAX_ITEMS
    _bound_list(data, 'slots', MAX_SHOWN_SLOTS)
    _bound_list(data, 'common_slots', MAX_SHOWN_SLOTS)
    data['truncated'] |= data['participants_truncated'] or data['slots_truncated'] or data['common_slots_truncated']
    return data


def _bound_text(data: dict, field: str) -> None:
    value = data.get(field)
    if value is not None and len(value) > MAX_TEXT:
        data[field] = value[:MAX_TEXT]
        data[field + '_truncated'] = True
        data['truncated'] = True


def _bound_list(data: dict, field: str, limit: int) -> None:
    values = data[field]
    data[field + '_count'] = len(values)
    data[field + '_truncated'] = len(values) > limit
    data[field] = values[:limit]
