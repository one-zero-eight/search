"""Organizer draft workflows; no implicit submission or publication."""
from typing import Literal

from fastmcp.dependencies import Depends
from fastmcp.tools import tool
from pydantic import TypeAdapter

from catix.innohassle import client, event_drafts as drafts
from catix.innohassle.mcp_declarations import invalid_arguments, metadata, require_innohassle, result_boundary


@tool(**metadata(write=True))
@result_boundary(write=True)
def events_create_draft(
    name: drafts.Name,
    description: drafts.Description,
    locale: Literal['ru', 'en'] = 'ru',
    starts_at: drafts.EventDateTime | None = None,
    location: drafts.Location | None = None,
    duration_hours: drafts.Duration | None = None,
    registration_url: drafts.RegistrationURL | None = None,
    club_id: drafts.ClubId | None = None,
    *, token: str = Depends(require_innohassle),
) -> dict:
    """Create an organizer's event draft / Создать черновик мероприятия клуба.

    Name and description are prepared text in the chosen ru/en language. Optional timezone-aware
    RFC3339 start, location, duration in hours, external registration URL and owned club ID.
    Missing optional facts stay unset; do not invent them. Only club leaders or event managers.
    Checks fresh Events permissions, then saves and reads back. Host confirmation required.
    Multiple API writes are not atomic: never retry an unknown outcome. Does not submit to moderators.
    """
    try:
        profile = drafts.Profile.model_validate(client._as_user('GET', '/events/v1/users/me', token).json())
    except Exception:
        return drafts.refused()
    if not {'club-leader', 'event-manager'}.intersection(profile.roles):
        return drafts.refused('permission_denied')
    if club_id is not None and not any(club.club_id == club_id for club in profile.clubs):
        return drafts.refused('club_not_owned')
    fields = {'starts_at': starts_at.isoformat() if starts_at else None, 'location': location,
              'duration_hours': duration_hours,
              'enrollment': {'type': 'external', 'url': registration_url, 'capacity': None}
              if registration_url is not None else None}
    draft_id = None
    try:
        response = client._as_user('POST', drafts.BASE, token, json={**fields, 'locales': [locale]})
    except client.ServiceError:
        return drafts.refused('upstream_refused')
    except Exception:
        return drafts.unknown(None)
    try:
        data = response.json()
        draft_id = TypeAdapter(drafts.DraftId).validate_python(data['id'], strict=True)
        created = drafts.Draft.model_validate(data)
        if not created.can_edit:
            return drafts.unknown(draft_id)
        text = {'name': name, 'description': drafts.description_document(description)}
        client._as_user('PUT', drafts.path(draft_id) + f'/locales/{locale}', token, json=text)
        if club_id is not None:
            client._as_user('POST', drafts.path(draft_id) + '/hosts/clubs', token, json={'club_id': club_id})
        confirmed = drafts.read(token, draft_id)
        drafts.verify(confirmed, fields, locale, text, club_id)
        return drafts.receipt(confirmed)
    except Exception:
        return drafts.unknown(draft_id)


@tool(**metadata(write=True))
@result_boundary(write=True)
def events_update_draft(
    draft_id: drafts.DraftId,
    locale: Literal['ru', 'en'] = 'ru',
    name: drafts.Name | None = None,
    description: drafts.Description | None = None,
    starts_at: drafts.EventDateTime | None = None,
    location: drafts.Location | None = None,
    duration_hours: drafts.Duration | None = None,
    registration_url: drafts.RegistrationURL | None = None,
    club_id: drafts.ClubId | None = None,
    *, token: str = Depends(require_innohassle),
) -> dict:
    """Edit an event draft / Изменить черновик мероприятия клуба, название, описание, время, место.

    Exact draft ID required. Omitted/null fields remain unchanged; empty description clears it.
    Updates only the chosen ru/en locale, preserving its other text and other languages.
    registration_url replaces enrollment with external registration; club_id adds an owned club
    without removing existing organizers. Checks fresh can_edit and club ownership after consent.
    Reads back saved values. Not atomic; never retry unknown outcomes. No submission or publication.
    """
    fields = {key: value for key, value in {
        'starts_at': starts_at.isoformat() if starts_at else None,
        'location': location, 'duration_hours': duration_hours,
        'enrollment': {'type': 'external', 'url': registration_url, 'capacity': None}
        if registration_url is not None else None,
    }.items() if value is not None}
    if not fields and name is None and description is None and club_id is None:
        return invalid_arguments('Specify at least one draft field to change; nothing was done.')
    try:
        current = drafts.read(token, draft_id)
        if not current.can_edit:
            return drafts.refused('permission_denied')
        if club_id is not None:
            profile = drafts.Profile.model_validate(client._as_user('GET', '/events/v1/users/me', token).json())
            if not any(club.club_id == club_id for club in profile.clubs):
                return drafts.refused('club_not_owned')
    except Exception:
        return drafts.refused()
    text = None
    if name is not None or description is not None:
        text = current.data.locales.get(locale, drafts.Locale()).model_dump()
        if name is not None:
            text['name'] = name
        if description is not None:
            text['description'] = drafts.description_document(description)
    written = False
    try:
        if fields:
            client._as_user('PATCH', drafts.path(draft_id), token, json=fields)
            written = True
        if text is not None:
            client._as_user('PUT', drafts.path(draft_id) + f'/locales/{locale}', token, json=text)
            written = True
        if club_id is not None and not any(h.type == 'club' and h.club_id == club_id for h in current.data.hosts):
            client._as_user('POST', drafts.path(draft_id) + '/hosts/clubs', token, json={'club_id': club_id})
            written = True
    except client.ServiceError:
        return drafts.unknown(draft_id) if written else drafts.refused('upstream_refused')
    except Exception:
        return drafts.unknown(draft_id)
    try:
        confirmed = drafts.read(token, draft_id)
        drafts.verify(confirmed, fields, locale, text, club_id)
        return drafts.receipt(confirmed)
    except Exception:
        return drafts.unknown(draft_id)
