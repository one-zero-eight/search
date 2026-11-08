"""Host-owned booking choices, derived from native recommendation evidence only."""
from copy import deepcopy
from datetime import UTC, date, datetime, time

from catix.agent.music_tools import AvailableMusicArgs, _at, _fit_windows, _windows
from catix.agent.room_tools import AvailableRoomsArgs, _rooms
from catix.agent.scheduling import ScheduleCheckError, _busy, _calendar_conflicts
from catix.api.schemas import SignupSelection
from catix.settings import settings


def room_candidates(data, artifact, arguments):
    """Recheck the original service/agenda evidence, not model-visible claims."""
    if not isinstance(data, dict) or not isinstance(artifact, dict):
        return []
    try:
        args = AvailableRoomsArgs.model_validate(arguments)
        source = args.model_dump(mode='json')
        if artifact.get('room_arguments') != source:
            return []
        rooms = _rooms(artifact['rooms'], args.day, args.time_from, args.time_to)
        interval = {key: datetime.combine(args.day, time.fromisoformat(clock), settings.tz).isoformat()
                    for key, clock in (('starts_at', args.time_from), ('ends_at', args.time_to))}
        period = {'date_from': source['day'], 'date_to': source['day']}
        conflicts, unknown = _calendar_conflicts(interval, _busy(artifact['agenda'], period))
        if (conflicts or unknown or data.get('interval') != interval
                or data.get('range') != [source['day'], source['day']]
                or data.get('timezone') != str(settings.tz) or data.get('available') != rooms['free']):
            return []
        return [({**room, **interval, 'location': room['room_id']},
                 {'arguments': {**source, 'room_id': room['room_id']}, 'room': deepcopy(room)})
                for room in rooms['free']]
    except (ScheduleCheckError, KeyError, TypeError, ValueError, AttributeError):
        return []


def music_candidates(data, artifact, arguments):
    if not isinstance(data, dict) or not isinstance(artifact, dict):
        return []
    try:
        args = AvailableMusicArgs.model_validate(arguments)
        source = args.model_dump(mode='json', exclude_none=True)
        if artifact.get('music_arguments') != source:
            return []
        windows = _windows(artifact['music'], args.day, args.duration_minutes)
        period = {'date_from': source['day'], 'date_to': source['day']}
        available, _, _ = _fit_windows(args.day, args.duration_minutes, windows, _busy(artifact['agenda'], period))
        if (data.get('available') != available or data.get('duration_minutes') != args.duration_minutes
                or data.get('range') != [source['day'], source['day']] or data.get('timezone') != str(settings.tz)):
            return []
        return [({**window, 'title': 'Music room', 'location': 'Music room', 'music_window': {
                    'starts_at': window['starts_at'], 'ends_at': window['ends_at'],
                    'latest_start_at': _at(args.day, window['latest_start']).isoformat(),
                    'max_duration_minutes': window['max_duration_minutes'], 'duration_minutes': args.duration_minutes}},
                 {'arguments': {'day': source['day']}}) for window in available]
    except (ScheduleCheckError, KeyError, TypeError, ValueError, AttributeError):
        return []


def select(offer, target, selection, *, now=None):
    """Validate consent under the answer row lock, before the durable claim."""
    selection = selection or SignupSelection()
    now = now or datetime.now(UTC)
    target = deepcopy(target)
    if offer.service == 'rooms':
        if (not selection.booking_title or not selection.booking_title.strip()
                or selection.model_fields_set - {'booking_title'}):
            raise ValueError('Enter a booking title; the room and interval cannot be changed.')
        offer = offer.model_copy(update={'booking_title': selection.booking_title})
        target['arguments']['title'] = selection.booking_title
    elif offer.service == 'music':
        if (selection.model_fields_set != {'time_from', 'time_to'}
                or selection.time_from is None or selection.time_to is None or offer.music_window is None):
            raise ValueError('Choose both start and end for the Music room booking.')
        window = offer.music_window
        day = date.fromisoformat(target['arguments']['day'])
        start, end = _at(day, selection.time_from), _at(day, selection.time_to)
        duration = (end - start).total_seconds() / 60
        if (not window.starts_at <= start < end <= window.ends_at or start > window.latest_start_at
                or duration > window.max_duration_minutes
                or window.duration_minutes is not None and duration != window.duration_minutes):
            raise ValueError('The selected interval must fit the offered window, duration and limits.')
        offer = offer.model_copy(update={'starts_at': start, 'ends_at': end})
        target['arguments'].update(time_from=selection.time_from, time_to=selection.time_to)
    elif selection.model_fields_set:
        raise ValueError('This offer does not accept booking selections.')
    if offer.service in {'rooms', 'music'} and (offer.expires_at <= now or offer.starts_at <= now):
        raise ValueError('The offer has expired or the selected interval is in the past. Request new options.')
    return offer, target
