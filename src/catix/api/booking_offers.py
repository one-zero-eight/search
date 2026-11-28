"""Host-owned booking choices, derived from paired, validated service evidence."""
import re
from copy import deepcopy
from datetime import UTC, date, datetime, time, timedelta

from pydantic import BaseModel, ConfigDict, Field, model_validator

from catix.api.schemas import SignupSelection
from catix.settings import settings


class AvailableRoomsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    day: date = Field(description="One explicit local date, YYYY-MM-DD. Ask if unknown.")
    time_from: str = Field(pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$", description="Requested start, HH:MM, Moscow time.")
    time_to: str = Field(pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$",
                         description="Requested end on the same day, HH:MM. Never invent a duration; ask if unknown.")

    @model_validator(mode="after")
    def ordered(self):
        if self.time_from >= self.time_to:
            raise ValueError("time_to must be after time_from on the same day.")
        return self


def _rooms(data, day, time_from, time_to):
    """Validate the existing MCP wire response, not server implementation models."""
    if (not isinstance(data, dict) or "error" in data or data.get("truncated") or data.get("more")
            or data.get("date") != day.strftime("%Y-%m-%d %a") or data.get("range") != f"{time_from}-{time_to}"
            or data.get("timezone") != str(settings.tz)
            or not all(isinstance(data.get(key), list) for key in ("free", "booked", "unavailable"))):
        raise ValueError("Room availability is unverified.")
    checked = datetime.fromisoformat(data["checked_at"])
    if checked.utcoffset() is None or checked >= datetime.combine(day, time.fromisoformat(time_from), settings.tz):
        raise ValueError("Room availability check time is invalid.")
    ids = list(data["booked"])
    for room in [*data["free"], *data["unavailable"]]:
        if not isinstance(room, dict):
            raise ValueError("Invalid room entry.")
        ids.append(room.get("room_id"))
    if (any(not isinstance(value, str) or not value.strip() or len(value) > 80 for value in ids)
            or len(ids) != len(set(ids))
            or "total" in data and (type(data["total"]) is not int or data["total"] != len(ids))):
        raise ValueError("Invalid or duplicate room identifiers/count.")
    for room in data["free"]:
        if (any(key in room and not isinstance(room[key], str) for key in ("title", "who", "night_only"))
                or "capacity" in room and (type(room["capacity"]) is not int or room["capacity"] < 0)):
            raise ValueError("Invalid room details.")
    if any(not isinstance(room.get("reason"), str) or not room["reason"].strip() for room in data["unavailable"]):
        raise ValueError("Missing room refusal reason.")
    return data


class AvailableMusicArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    day: date = Field(description="One requested local date, YYYY-MM-DD. Ask if unknown.")
    duration_minutes: int | None = Field(None, strict=True, ge=30, le=1440, multiple_of=30,
                                         description="Only the user's requested duration; omit to show windows without choosing it.")
    time_from: str | None = Field(None, pattern=r"^(?:[01][0-9]|2[0-3]):(?:00|30)$",
                                  description="Exact requested start, HH:MM. Always pass both times when the user specifies an interval.")
    time_to: str | None = Field(None, pattern=r"^(?:[01][0-9]|2[0-3]):(?:00|30)$",
                                description="Exact requested end on the same day, HH:MM; never replace exact times with duration alone.")

    @model_validator(mode="after")
    def exact_interval(self):
        if (self.time_from is None) != (self.time_to is None):
            raise ValueError("Pass both time_from and time_to, or omit both.")
        if self.time_from is not None:
            if self.time_from >= self.time_to:
                raise ValueError("time_to must be after time_from on the same day.")
            duration = int((_at(self.day, self.time_to) - _at(self.day, self.time_from)).total_seconds() // 60)
            if self.duration_minutes is not None and self.duration_minutes != duration:
                raise ValueError("duration_minutes must match the exact requested interval.")
            self.duration_minutes = duration
        return self


def _at(day, clock):
    if not isinstance(clock, str) or not re.fullmatch(r"(?:[01][0-9]|2[0-3]):(?:00|30)", clock):
        raise ValueError("Music windows must use the half-hour HH:MM grid.")
    return datetime.combine(day, time.fromisoformat(clock), settings.tz)


def _span(start, end):
    return {"start": start.strftime("%H:%M"), "end": end.strftime("%H:%M"),
            "starts_at": start.isoformat(), "ends_at": end.isoformat()}


def _windows(music, day, duration_minutes, time_from=None, time_to=None):
    """Validate the client wire contract before using service data as availability."""
    if time_from is not None or time_to is not None:
        args = AvailableMusicArgs(day=day, duration_minutes=duration_minutes, time_from=time_from, time_to=time_to)
        duration_minutes = args.duration_minutes
    if (not isinstance(music, dict) or "error" in music or music.get("truncated") or music.get("more")
            or music.get("date") != day.isoformat() or music.get("timezone") != str(settings.tz)
            or music.get("availability") != "calculated" or music.get("duration_minutes") != duration_minutes
            or not isinstance(music.get("windows"), list)):
        raise ValueError("Music availability is unverified.")
    checked = datetime.fromisoformat(music["checked_at"])
    rules = music["rules"]
    horizon = datetime.fromisoformat(rules["latest_booking_start"])
    if (checked.utcoffset() is None or horizon.utcoffset() is None or horizon < checked
            or type(rules.get("step_minutes")) is not int or rules["step_minutes"] != 30):
        raise ValueError("Music availability rules are unverified.")
    opening, closing = _at(day, rules["opens_at"]), _at(day, rules["closes_at"])
    if closing <= opening:
        raise ValueError("Music opening interval is invalid.")
    requested = music.get("requested_interval")
    if time_from is not None or time_to is not None:
        expected = {key: value for key, value in _span(_at(day, args.time_from), _at(day, args.time_to)).items()
                    if key in {"starts_at", "ends_at"}}
        if requested != expected:
            raise ValueError("Music availability does not match the requested interval.")
    elif requested is not None:
        raise ValueError("Unexpected exact Music Room response to a day-wide request.")
    windows = music["windows"]
    if not windows:
        if music.get("reason") not in {"outside_booking_horizon", "access_denied", "insufficient_quota", "no_matching_window",
                                       "outside_opening_hours", "past", "room_occupied"}:
            raise ValueError("Missing Music Room refusal reason.")
        if requested is not None and music.get("reason") == "room_occupied":
            occupied = music.get("occupied_intervals")
            if not isinstance(occupied, list) or not occupied:
                raise ValueError("Missing exact Music Room occupancy evidence.")
            previous = _at(day, time_from)
            for item in occupied:
                if not isinstance(item, dict) or set(item) != {"starts_at", "ends_at"}:
                    raise ValueError("Invalid Music Room occupancy evidence.")
                start, end = (datetime.fromisoformat(item[key]) for key in ("starts_at", "ends_at"))
                if start.utcoffset() is None or end.utcoffset() is None or not previous <= start < end <= _at(day, time_to):
                    raise ValueError("Music Room occupancy is outside the requested interval.")
                previous = end
        return windows
    quotas = [music[key] for key in ("remaining_daily_minutes", "remaining_weekly_minutes")]
    if music.get("reason") is not None or any(type(value) is not int or value < 0 for value in quotas):
        raise ValueError("Music quotas are unverified.")
    minimum = duration_minutes or 30
    previous_end = opening
    for window in windows:
        start, end, latest = (_at(day, window[key]) for key in ("start", "end", "latest_start"))
        maximum = window["max_duration_minutes"]
        if (not previous_end <= start < end <= closing or not checked < start <= latest <= horizon
                or latest + timedelta(minutes=minimum) > end
                or type(maximum) is not int or maximum % 30 or not minimum <= maximum <= min(quotas)
                or maximum > (end - start).total_seconds() / 60):
            raise ValueError("Music window bounds or limits are invalid.")
        previous_end = end
    if requested is not None and windows != [{"start": time_from, "end": time_to, "latest_start": time_from,
                                               "max_duration_minutes": duration_minutes}]:
        raise ValueError("Music availability window differs from the exact requested interval.")
    return windows


def _service_day(data, arguments, *, rooms=False):
    """Use the service's resolved date, never the host's current date or prose."""
    if not isinstance(data, dict) or not isinstance(arguments, dict):
        raise ValueError('Missing paired service evidence.')
    value = data['date']
    day = date.fromisoformat(value.split(' ')[0] if rooms else value)
    if arguments.get('day') is not None:
        if date.fromisoformat(arguments['day']) != day:
            raise ValueError('Service date differs from the requested day.')
    else:
        checked = datetime.fromisoformat(data['checked_at'])
        if checked.utcoffset() is None or checked.astimezone(settings.tz).date() != day:
            raise ValueError('The default service day is unverified.')
    return day


def raw_room_candidates(data, arguments):
    """Only the service's free list authorizes an exact-interval room choice."""
    try:
        day = _service_day(data, arguments, rooms=True)
        args = AvailableRoomsArgs.model_validate({**arguments, 'day': day})
        source = args.model_dump(mode='json')
        rooms = _rooms(data, day, args.time_from, args.time_to)
        interval = {key: datetime.combine(day, time.fromisoformat(clock), settings.tz).isoformat()
                    for key, clock in (('starts_at', args.time_from), ('ends_at', args.time_to))}
        return [({**room, **interval, 'title': room.get('title', '').strip() or room['room_id'],
                  'location': room['room_id']},
                 {'arguments': {**source, 'room_id': room['room_id']}, 'room': deepcopy(room)})
                for room in rooms['free']]
    except (KeyError, TypeError, ValueError, AttributeError):
        return []


def raw_music_candidates(data, arguments):
    """Keep service windows and bounds without claiming personal agenda fit."""
    try:
        day = _service_day(data, arguments)
        args = AvailableMusicArgs.model_validate({**arguments, 'day': day})
        windows = _windows(data, day, args.duration_minutes, args.time_from, args.time_to)
        return [({'title': 'Music room', 'location': 'Music room',
                  'starts_at': _at(day, window['start']).isoformat(),
                  'ends_at': _at(day, window['end']).isoformat(),
                  'music_window': {'starts_at': _at(day, window['start']).isoformat(),
                                   'ends_at': _at(day, window['end']).isoformat(),
                                   'latest_start_at': _at(day, window['latest_start']).isoformat(),
                                   'max_duration_minutes': window['max_duration_minutes'],
                                   'duration_minutes': args.duration_minutes}},
                 {'arguments': args.model_dump(mode='json', exclude_none=True, exclude={'duration_minutes'})}) for window in windows]
    except (KeyError, TypeError, ValueError, AttributeError):
        return []

def raw_training_candidates(data, arguments):
    """Sport's own eligibility authorizes a signup choice; the personal calendar is not consulted."""
    try:
        if not isinstance(data, dict) or 'error' in data or not isinstance(arguments, dict):
            return []
        first, last = data['range']
        date.fromisoformat(first), date.fromisoformat(last)
        if any(arguments.get(key) is not None and arguments[key] != value
               for key, value in (('date_from', first), ('date_to', last))) or not isinstance(data.get('trainings'), list):
            return []
        period = {'date_from': first, 'date_to': last}
        filters = {'sport': arguments['sport']} if isinstance(arguments.get('sport'), str) else {}
        return [(deepcopy(item), {'arguments': {'training_id': item['training_id']}, 'training': deepcopy(item),
                                  'period': period, 'training_filters': filters})
                for item in data['trainings'] if isinstance(item, dict) and type(item.get('training_id')) is int
                and item['training_id'] > 0 and item.get('checked_in') is False and item.get('can_check_in') is True]
    except (KeyError, TypeError, ValueError):
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
