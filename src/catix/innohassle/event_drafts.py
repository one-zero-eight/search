"""Events draft contracts and uncached user-scoped reads.

Contract: Events v1 OpenAPI and one-zero-eight/monorepo
cebefd0658786a0820369e93398a5c573bdeca7f, src/events/modules/drafts/routes.py.
No submission, publication, invitations or administrative writes.
"""
import json
import re
from datetime import datetime
from typing import Annotated, Literal
from urllib.parse import quote, urlsplit

from pydantic import AfterValidator, AwareDatetime, BaseModel, BeforeValidator, ConfigDict, Field, HttpUrl, TypeAdapter

from catix.innohassle import client

BASE = '/events/v1/drafts/'
DraftId = Annotated[str, Field(pattern=r'^[0-9a-f]{24}$')]
Name = Annotated[str, Field(min_length=1, max_length=300, pattern=r'\S')]
Description = Annotated[str, Field(max_length=12000)]
Location = Annotated[str, Field(min_length=1, max_length=500, pattern=r'\S')]
ClubId = Annotated[str, Field(min_length=1, max_length=100, pattern=r'^[A-Za-z0-9_-]+$')]
Duration = Annotated[float, Field(gt=0, allow_inf_nan=False)]


def rfc3339(value):
    if isinstance(value, str):
        if not re.fullmatch(
            r'[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt](?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]'
            r'(?:\.[0-9]+)?(?:[Zz]|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])', value,
        ):
            raise ValueError('Date-time must use RFC 3339 format with a timezone.')
        try:
            return datetime.fromisoformat(value.upper())
        except ValueError:
            raise ValueError('Date-time must use a valid RFC 3339 timestamp.') from None
    return value


EventDateTime = Annotated[AwareDatetime, BeforeValidator(rfc3339)]


def registration_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        if parsed.username is not None or parsed.password is not None:
            raise ValueError
        TypeAdapter(HttpUrl).validate_python(value)
    except ValueError:
        raise ValueError('Registration URL must be HTTP(S) without user credentials.') from None
    return value  # Preserve exactly what the user approved, including query parameters.


RegistrationURL = Annotated[str, Field(max_length=2048, pattern=r'^https?://\S+$'), AfterValidator(registration_url)]


def description_document(text: str) -> str | None:
    # Website 34dc0d59972778eb99de6b0f4b0c10f67599fdb5, events/utils/description.ts:
    # parseDescriptionContent calls JSON.parse; a plain API string breaks the viewer.
    if not text:
        return None
    paragraphs = [{'type': 'paragraph', **({'content': [{'type': 'text', 'text': line}]} if line else {})}
                  for line in text.split('\n')]
    return json.dumps({'type': 'doc', 'content': paragraphs}, ensure_ascii=False, separators=(',', ':'))


class Projection(BaseModel):
    model_config = ConfigDict(strict=True, extra='ignore')


class OwnedClub(Projection):
    club_id: str
    title: str


class Profile(Projection):
    roles: list[str]
    clubs: list[OwnedClub]


class Locale(Projection):
    name: str | None = None
    description: str | None = None


class ResolvedLocation(Projection):
    display_name: str
    url: str


class Enrollment(Projection):
    type: Literal['external', 'internal']
    url: str | None = None
    capacity: int | None = None


class Host(Projection):
    id: str
    type: Literal['club', 'external']
    club_id: str | None = None
    name: str | None = None


class DraftData(Projection):
    starts_at: EventDateTime | None
    location: ResolvedLocation | None
    duration_hours: float | None
    enrollment: Enrollment | None
    locales: dict[str, Locale]
    hosts: list[Host]


class Draft(Projection):
    id: DraftId
    can_edit: bool
    can_submit: bool
    has_public: bool
    cannot_submit_reasons: list[str]
    status: Literal['published', 'unpublished', 'pending', 'declined'] | None
    data: DraftData


def path(draft_id: str) -> str:
    if not re.fullmatch(r'[0-9a-f]{24}', draft_id):
        raise ValueError('Invalid draft ID.')
    return BASE + quote(draft_id, safe='')


def read(token: str, draft_id: str) -> Draft:
    draft = Draft.model_validate(client._as_user('GET', path(draft_id), token).json())
    if draft.id != draft_id:
        raise ValueError('Draft readback identity mismatch.')
    return draft


def unknown(draft_id: str | None) -> dict:
    return {'done': None, 'outcome': 'unknown', 'draft_id': draft_id,
            'error': 'Draft changes could not be fully confirmed; some changes may have been saved. '
                     'Read the draft before continuing. Do not retry automatically.'}


def refused(code: str = 'permission_unverified') -> dict:
    return {'done': False, 'code': code,
            'error': 'Draft permission could not be verified or access was refused; nothing was changed.'}


def verify(draft: Draft, fields: dict, locale: str, text: dict | None, club_id: str | None) -> None:
    for key, expected in fields.items():
        actual = getattr(draft.data, key)
        if key == 'starts_at' and expected is not None:
            expected = rfc3339(expected)
        elif key == 'location':
            actual = actual.display_name if actual else None
        elif key == 'enrollment':
            actual = actual.model_dump() if actual else None
        if actual != expected:
            raise ValueError('Draft readback does not match requested fields.')
    if text is not None:
        current = draft.data.locales.get(locale)
        if current is None or current.model_dump() != text:
            raise ValueError('Draft locale readback mismatch.')
    if club_id is not None and not any(h.type == 'club' and h.club_id == club_id for h in draft.data.hosts):
        raise ValueError('Draft club host readback mismatch.')


def receipt(draft: Draft) -> dict:
    return {'done': True, 'draft': draft.model_dump(mode='json'), 'submitted': False,
            'note': 'Draft saved and read back. This action did not submit or publish it. '
                    'Existing publication/submission state is shown separately in the draft.'}
