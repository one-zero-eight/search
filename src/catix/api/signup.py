"""Signup buttons contain only paired service facts; clicks never invoke a model.

Private snapshots live beside the answer, not in the public response or credentials.
A durable claim becomes unknown BEFORE service I/O and can never be retried.
"""
import json
import re
import secrets
from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from urllib.parse import urlsplit

from langchain.tools import ToolRuntime
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from catix.agent import schedule_tools
from catix.agent.api_tools import _acall, _credentials
from catix.agent.scheduling import ScheduleCheckError, _busy, _calendar_conflicts, prepare_training
from catix.api import booking_offers
from catix.api.schemas import MusicBookingWindow, SignupOffer
from catix.innohassle import mcp_client
from catix.innohassle.mcp_access import CONFIRMATION_TOOLS
from catix.settings import settings


def safe_url(value):
    if not isinstance(value, str) or any(ord(c) < 33 for c in value) or '\\' in value:
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username is not None or parsed.password is not None:
            return None
        _ = parsed.port  # Access validates a malformed/out-of-range port.
    except ValueError:
        return None
    return value


def _data(message):
    try:
        value = json.loads(message.content) if message.status == 'success' else None
        return value if isinstance(value, dict) and 'error' not in value else None
    except (ValueError, TypeError):
        return None


def _same_details(current, expected, *, fields):
    """Compare consented wire facts, not eligibility or timestamp spelling."""
    if not isinstance(current, dict) or not isinstance(expected, dict):
        return False
    if any(current.get(key) != expected.get(key) for key in fields):
        return False
    for item in (current, expected):
        if type(item.get('all_day', False)) is not bool:
            return False
    if current.get('all_day', False) != expected.get('all_day', False):
        return False
    try:
        for key in ('starts_at', 'ends_at'):
            actual, consented = current.get(key), expected.get(key)
            if key == 'ends_at' and actual is None and consented is None:
                continue
            if not isinstance(actual, str) or not isinstance(consented, str):
                return False
            actual, consented = datetime.fromisoformat(actual), datetime.fromisoformat(consented)
            if actual.utcoffset() is None or consented.utcoffset() is None or actual != consented:
                return False
    except (TypeError, ValueError):
        return False
    return True


def _event_snapshot(item):
    if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not re.fullmatch(r'[0-9a-f]{24}', item['id']):
        return None
    enrollment = item.get('enrollment_info')
    if (not isinstance(enrollment, dict) or not isinstance(enrollment.get('type'), str)
            or enrollment['type'] not in {'internal', 'external'}
            or type(enrollment.get('enrolled_count')) is not int or enrollment['enrolled_count'] < 0
            or enrollment.get('capacity') is not None and (type(enrollment['capacity']) is not int or enrollment['capacity'] < 0)):
        return None
    if enrollment['type'] == 'external':
        if not safe_url(enrollment.get('url')):
            return None
    elif enrollment.get('capacity') is not None and enrollment['enrolled_count'] >= enrollment['capacity']:
        return None
    return {**{key: deepcopy(item.get(key)) for key in ('id', 'title', 'names', 'starts_at', 'ends_at', 'location')},
            'all_day': item.get('all_day', False),
            'enrollment': {key: enrollment.get(key) for key in ('type', 'url', 'capacity')}}


def collect(messages, answer, *, now=None):
    """Only the latest current-turn read per service survives failures and writes.

    Prose never selects targets or supplies IDs, dates or arguments.
    """
    now = now or datetime.now(UTC)
    calls, candidates = {}, {}
    for index, message in enumerate(messages):
        if isinstance(message, HumanMessage):
            calls, candidates = {}, {}
        elif isinstance(message, AIMessage):
            calls.update((call['id'], call) for call in message.tool_calls)
        elif isinstance(message, ToolMessage):
            call = calls.pop(message.tool_call_id, None)
            if not call or message.name != call['name']:
                continue
            name = call['args'].get('name') if call['name'] == 'call_api_tool' else call['name']
            if not isinstance(name, str):
                continue
            if name in CONFIRMATION_TOOLS or name in {'add_to_ai_calendar', 'update_ai_calendar', 'remove_from_ai_calendar'}:
                candidates.clear()
                continue
            if message.name in {'ask_docs', 'ask_chats'}:
                if isinstance(message.artifact, dict) and message.artifact.get('action_receipts'):
                    candidates.clear()
                continue
            if name in {'get_my_schedule', 'get_my_available_trainings', 'get_my_available_rooms',
                        'get_my_available_music_windows', 'rooms_get_free_rooms', 'music_get_available_windows',
                        'account_get_my_schedule', 'sport_get_my_sport', 'sport_get_sport_trainings', 'sport_get_training'}:
                # A newer source read, even a failed one, supersedes personal fit.
                for service in ('sport', 'rooms', 'music'):
                    candidates.pop(service, None)
            if message.name == 'get_my_available_rooms':
                candidates['rooms'] = booking_offers.room_candidates(_data(message), message.artifact, call['args'])
            elif message.name == 'get_my_available_music_windows':
                candidates['music'] = booking_offers.music_candidates(_data(message), message.artifact, call['args'])
            elif call['name'] == 'call_api_tool' and name == 'rooms_get_free_rooms':
                candidates['rooms'] = booking_offers.raw_room_candidates(_data(message), call['args'].get('arguments'))
            elif call['name'] == 'call_api_tool' and name == 'music_get_available_windows':
                candidates['music'] = booking_offers.raw_music_candidates(_data(message), call['args'].get('arguments'))
            elif message.name == 'get_my_available_trainings':
                candidates['sport'] = []
                data = _data(message)
                artifact = message.artifact
                args = call['args']
                source = {'date_from': args.get('day'), 'date_to': args.get('day'),
                          **({'sport': args['sport']} if args.get('sport') is not None else {})}
                if (not data or not isinstance(data.get('available'), list) or not isinstance(artifact, dict)
                        or artifact.get('training_arguments') != source):
                    continue
                for item in data['available']:
                    if not isinstance(item, dict) or type(item.get('training_id')) is not int:
                        continue
                    arguments = {'training_id': item['training_id']}
                    try:
                        checked = prepare_training(arguments, messages[:index + 1])
                    except (ScheduleCheckError, KeyError, TypeError, ValueError):
                        continue
                    if item != checked['training']:
                        continue
                    candidates['sport'].append((item, {'arguments': arguments, 'schedule_check': checked}))
            elif call['name'] == 'call_api_tool' and name == 'events_events_list_events':
                candidates['events'] = []
            elif call['name'] == 'call_api_tool' and name in {'events_get_event', 'events_get_university_events'}:
                candidates['events'] = []
                data = _data(message)
                if not data:
                    continue
                arguments = call['args'].get('arguments') or {}
                period = data.get('range')
                if name == 'events_get_event':
                    item = data.get('event')
                    items = [item] if isinstance(item, dict) and item.get('id') == arguments.get('event_id') else []
                else:
                    if (not isinstance(period, list) or len(period) != 2 or any(
                            arguments.get(key) is not None and arguments[key] != period[i]
                            for i, key in enumerate(('date_from', 'date_to')))):
                        continue
                    items = data.get('events', [])
                if not isinstance(items, list):
                    continue
                for item in items:
                    snapshot = _event_snapshot(item)
                    if snapshot and name == 'events_get_university_events':
                        try:
                            start = datetime.fromisoformat(item['starts_at'])
                            if (start.utcoffset() is None or not date.fromisoformat(period[0])
                                    <= start.astimezone(settings.tz).date() <= date.fromisoformat(period[1])):
                                continue
                        except (ValueError, KeyError, TypeError):
                            continue
                    if snapshot:
                        candidates['events'].append((item, {'arguments': {'event_id': item['id'], 'leave': False}, 'event': snapshot}))
    offers, targets = [], {}
    for service, items in candidates.items():
        for item, target in items:
            title = item.get('name') if service == 'sport' else item.get('title')
            aliases = item.get('names') or {}
            if not isinstance(aliases, dict) or any(not isinstance(name, str) for name in aliases.values()):
                continue
            if not isinstance(title, str) or not title.strip():
                continue
            try:
                start = datetime.fromisoformat(item['starts_at'])
                end = datetime.fromisoformat(item['ends_at']) if item.get('ends_at') else None
                window = MusicBookingWindow(**item['music_window']) if service == 'music' else None
                deadline = window.latest_start_at if window else start
                if start.utcoffset() is None or deadline <= now or end is not None and (end.utcoffset() is None or end <= start):
                    continue
            except (ValueError, TypeError, KeyError):
                continue
            location = item.get('place') if service == 'sport' else item.get('location')
            if location is not None and not isinstance(location, str):
                continue
            offer = SignupOffer(id=secrets.token_urlsafe(24), service=service, title=title, starts_at=start,
                                music_window=window, personal_schedule_checked=item.get('personal_schedule_checked') is True,
                                ends_at=end, all_day=item.get('all_day') is True, location=location,
                                source_url='https://innohassle.ru/sport' if service == 'sport' else safe_url(item.get('page')),
                                external_url=safe_url(item.get('enrollment_info', {}).get('url'))
                                    if item.get('enrollment_info', {}).get('type') == 'external' else None,
                                expires_at=min(deadline, now + timedelta(hours=24)))
            offers.append(offer)
            targets[offer.id] = target
    return offers[:12], {offer.id: targets[offer.id] for offer in offers[:12]}


UNKNOWN = 'Результат записи неизвестен. Проверьте запись в сервисе; повторно запрос не отправляется.'
REFUSED = 'Запись не выполнена: условия изменились или проверка недоступна. Запросите новые варианты.'
CONFIRMED = 'Запись подтверждена в сервисе.'


def outcome(offer, status, message):
    return offer.model_copy(update={'status': status, 'message': message})


async def _enroll_event(offer, target, context):
    if not context.innohassle_token:
        return outcome(offer, 'refused', 'Войдите в InNoHassle, затем запросите новые варианты.')
    arguments = target['arguments']
    try:
        data = await mcp_client.request('call_tool', {'name': 'events_get_event', 'arguments': {'event_id': arguments['event_id']}})
        item = data.get('event') if isinstance(data, dict) and 'error' not in data else None
        enrollment = item.get('enrollment_info') if isinstance(item, dict) else None
        if (isinstance(item, dict) and isinstance(enrollment, dict) and item.get('id') == arguments['event_id']
                and enrollment.get('type') == 'internal' and type(enrollment.get('capacity')) is int
                and type(enrollment.get('enrolled_count')) is int
                and enrollment['enrolled_count'] >= enrollment['capacity'] >= 0):
            return outcome(offer, 'refused', 'Свободных мест больше нет. Запись не выполнена.')
        current = _event_snapshot(item)
        if not current:
            return outcome(offer, 'refused', REFUSED)
        if (not _same_details(current, target['event'], fields=('id', 'title', 'names', 'location', 'enrollment'))
                or current['enrollment']['type'] != 'internal'):
            return outcome(offer, 'refused', 'Время, место или условия события изменились. Запросите новые варианты; запись не выполнена.')
    except Exception:  # noqa: BLE001 - read-only failures are definite refusals
        return outcome(offer, 'refused', REFUSED)
    try:
        result = await mcp_client.request('call_tool', {'name': 'events_enroll_in_event', 'arguments': arguments},
                                          context.innohassle_token.get_secret_value())
        if isinstance(result, dict):
            if result.get('done') is False:
                return outcome(offer, 'refused', REFUSED)
            if (result.get('done') is True and result.get('event_id') == arguments['event_id']
                    and result.get('enrolled') is True and result.get('enrollment_verified') is True
                    and _same_details(result.get('event'), target['event'], fields=('id', 'title', 'names', 'location'))):
                return outcome(offer, 'confirmed', CONFIRMED)
    except Exception:  # noqa: BLE001 - post-write errors must retain unknown
        return outcome(offer, 'unknown', UNKNOWN)
    return outcome(offer, 'unknown', UNKNOWN)


async def _book(offer, target, context):
    """Direct-offer calendar guard; native MCP retains authoritative service checks."""
    if not context.innohassle_id or not context.innohassle_token:
        return outcome(offer, 'refused', 'Войдите в InNoHassle, затем запросите новые варианты.')
    token = context.innohassle_token.get_secret_value()
    arguments = target['arguments']
    runtime = ToolRuntime(state={}, context=context, config={}, stream_writer=lambda _: None,
                          tool_call_id=offer.id, store=None)
    service = 'room' if offer.service == 'rooms' else 'music_room'
    name = 'rooms_book_room' if offer.service == 'rooms' else 'music_book_music_room'
    try:
        day = date.fromisoformat(arguments['day'])
        if offer.service == 'rooms':
            source = {key: arguments[key] for key in ('day', 'time_from', 'time_to')}
            current = await mcp_client.request('call_tool', {'name': 'rooms_get_free_rooms', 'arguments': source}, token)
            rooms = booking_offers._rooms(current, day, source['time_from'], source['time_to'])
            if target['room'] not in rooms['free']:
                return outcome(offer, 'refused', REFUSED)
        agenda = await schedule_tools.aread_my_schedule(runtime, day, day)
        interval = {'starts_at': offer.starts_at.isoformat(), 'ends_at': offer.ends_at.isoformat()}
        conflicts, unknown = _calendar_conflicts(interval, _busy(agenda, {'date_from': day.isoformat(), 'date_to': day.isoformat()}))
        if conflicts or unknown:
            return outcome(offer, 'refused', 'Не удалось подтвердить отсутствие пересечений с календарём. Бронирование не выполнено.')
    except Exception:  # noqa: BLE001 - all checks above are read-only
        return outcome(offer, 'refused', REFUSED)
    try:
        result = await mcp_client.request('call_tool', {'name': name, 'arguments': arguments}, token)
        if isinstance(result, dict) and result.get('done') is False:
            return outcome(offer, 'refused', REFUSED)
        booked = result.get('booked') if isinstance(result, dict) and result.get('done') is True else None
        if (not isinstance(booked, dict) or booked.get('service') != service
                or not isinstance(booked.get('booking_id'), str) or not booked['booking_id']):
            return outcome(offer, 'unknown', UNKNOWN)
        data = await mcp_client.request('call_tool', {'name': 'account_get_booking', 'arguments': {
            'service': service, 'booking_id': booked['booking_id']}}, token)
        expected = {**interval, 'service': service, 'booking_id': booked['booking_id'],
                    'title': offer.booking_title if offer.service == 'rooms' else 'Music room',
                    'place': arguments['room_id'] if offer.service == 'rooms' else 'Music room'}
        if offer.service == 'rooms':
            expected['room'] = arguments['room_id']
        if (isinstance(data, dict) and 'error' not in data
                and _same_details(data.get('booking'), expected, fields=tuple(key for key in expected if key not in interval))):
            return outcome(offer, 'confirmed', CONFIRMED)
    except Exception:  # noqa: BLE001 - POST or readback may have been lost; never retry
        return outcome(offer, 'unknown', UNKNOWN)
    return outcome(offer, 'unknown', UNKNOWN)


async def execute(offer, target, context, *, now=None):
    """Execute a durably claimed click with CURRENT credentials and host policy.

    ToolRuntime is the actual host runtime type. Its prepared snapshot represents
    this explicit HTTP consent, not an invented model tool call or HITL resume.
    """
    now = now or datetime.now(UTC)
    if offer.expires_at <= now or offer.starts_at <= now:
        return outcome(offer, 'refused', 'Предложение устарело. Запросите новые варианты.')
    if offer.external_url:
        return outcome(offer, 'refused', 'Регистрация проходит на сайте организатора; запись здесь не выполняется.')
    if offer.service == 'events':
        return await _enroll_event(offer, target, context)
    if offer.service in {'rooms', 'music'}:
        return await _book(offer, target, context)
    name = 'sport_sport_checkin'
    arguments = target['arguments']
    prepared = {'call_id': offer.id, 'target': name, 'arguments': arguments, 'schedule_check': target['schedule_check']}
    runtime = ToolRuntime(state={'api_prepared': [prepared]}, context=context, config={}, stream_writer=lambda _: None,
                          tool_call_id=offer.id, store=None)
    try:
        token, credentials = _credentials('sport', runtime)
    except ValueError:
        return outcome(offer, 'refused', 'Войдите в InNoHassle и Sport, затем запросите новые варианты.')
    try:
        result = await _acall(name, runtime, arguments)
        if isinstance(result, dict) and result.get('done') is False:
            # Only authored codes choose UI text; never forward upstream diagnostics.
            code = result.get('code')
            if not isinstance(code, str):
                code = ''
            reason = {
                'schedule_conflict': 'Тренировка пересекается с событием в вашем календаре. Запись не выполнена.',
                'schedule_unverified': 'Не удалось полностью проверить расписание. Запись не выполнена.',
                'training_changed': 'Время, название или место тренировки изменились. Запросите новые варианты; запись не выполнена.',
                'training_unavailable': 'Запись на тренировку недоступна или вы уже записаны. Новая запись не выполнена.',
            }.get(code, REFUSED)
            if result.get('code') == 'schedule_unverified' and result.get('uncertainty') == 'unknown_event_end':
                reason = 'В календаре есть событие без времени окончания: нельзя проверить пересечение. Уточните его длительность; запись не выполнена.'
            return outcome(offer, 'refused', reason)
        if (not isinstance(result, dict) or result.get('done') is not True
                or type(result.get('training_id')) is not int or result['training_id'] != arguments['training_id']
                or result.get('signed_up') is not True):
            return outcome(offer, 'unknown', UNKNOWN)
        checked = target['schedule_check']
        data = await mcp_client.request('call_tool', {'name': 'sport_get_sport_trainings',
            'arguments': {**checked['period'], **checked.get('training_filters', {})}}, token, **credentials)
        if (not isinstance(data, dict) or 'error' in data or not isinstance(data.get('trainings'), list)
                or data.get('range') != [checked['period']['date_from'], checked['period']['date_to']]):
            return outcome(offer, 'unknown', UNKNOWN)
        matches = [item for item in data['trainings'] if isinstance(item, dict) and type(item.get('training_id')) is int
                   and item['training_id'] == arguments['training_id']]
        if (len(matches) == 1 and matches[0].get('checked_in') is True
                and _same_details(matches[0], checked['training'], fields=('name', 'place'))):
            return outcome(offer, 'confirmed', CONFIRMED)
    except Exception:  # noqa: BLE001 - post-write errors must retain unknown
        # No upstream text, tokens or ambiguous error classification reaches chat.
        return outcome(offer, 'unknown', UNKNOWN)
    return outcome(offer, 'unknown', UNKNOWN)
