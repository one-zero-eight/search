"""Direct bookings use verified host evidence and explicit, persisted choices."""
from datetime import UTC, datetime
from copy import deepcopy
import asyncio
import json
from datetime import date
from types import SimpleNamespace

import httpx
import pytest
from pydantic import SecretStr, ValidationError
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from catix.api import schemas
from tests.test_signup_offers import AGENDA, DAY, NOW


@pytest.fixture
def native_bookings(monkeypatch):
    """Actual native MCP tools and HTTP backends; no production service writes."""
    from fastmcp import Client
    from catix.agent import room_tools, music_tools, schedule_tools
    from catix.agent.tools import AgentContext
    from catix.innohassle import client as backend, mcp_account, mcp_client, mcp_server
    state = {'requests': [], 'writes': [], 'agenda': deepcopy(AGENDA), 'allowed': True,
             'occupied': False, 'daily': 2, 'weekly': 2, 'status': 'free', 'changed': None}
    context = AgentContext(innohassle_id='owner', innohassle_token=SecretStr('ih'))
    monkeypatch.setattr(mcp_account, '_now', lambda: NOW)
    monkeypatch.setattr(mcp_server.token_verifier, 'claims', lambda token: {'uid': 'owner'} if token == 'ih' else None)
    def respond(request):
        state['requests'].append(request)
        path = request.url.path
        public = path.endswith('/daily_bookings')
        assert request.headers.get('authorization') == (None if public else 'Bearer ih')
        if request.method == 'POST':
            if state.get('before_write'):
                state['before_write'](request)
            state['writes'].append(request)
            if state.get('lost_write'):
                raise httpx.ReadTimeout('secret', request=request)
            return httpx.Response(200, json={'outlook_booking_id': 'opaque==', 'id': 99})
        assert request.method == 'GET'
        if path.endswith('/rooms/'):
            return httpx.Response(200, json=[{'id': 'r', 'title': 'Study room', 'capacity': 12}])
        if path.endswith('/can-book'):
            return httpx.Response(200, json={'can_book': state['allowed'], 'reason_why_cannot': ''})
        if path == '/room-booking/v0/bookings/':
            return httpx.Response(200, json=[{'room_id': 'r', 'start': DAY + 'T18:00:00+03:00',
                'end': DAY + 'T19:00:00+03:00'}] if state['occupied'] else [])
        if path.endswith('/users/me'):
            return httpx.Response(200, json={'status': state['status']})
        if path.endswith('/remaining_daily_hours'):
            return httpx.Response(200, json=state['daily'])
        if path.endswith('/remaining_weekly_hours'):
            return httpx.Response(200, json=state['weekly'])
        if public:
            return httpx.Response(200, json=[{'time_start': DAY + 'T18:00:00',
                'time_end': DAY + 'T19:00:00'}] if state['occupied'] else [])
        if state.get('lost_readback'):
            raise httpx.ReadTimeout('private', request=request)
        assert state['writes'], path
        body = json.loads(state['writes'][-1].content)
        if path.startswith('/room-booking/v0/bookings/'):
            booking = {'outlook_booking_id': 'opaque==', 'related_to_me': True, **body}
        else:
            assert path.endswith('/my_bookings'), path
            booking = {'id': 99, **body}
        change = state['changed']
        if change == 'interval':
            booking['end' if 'room_id' in booking else 'time_end'] = DAY + 'T20:00:00+03:00'
        elif change == 'title':
            booking['title'] = 'Other subject'
        elif change == 'room':
            booking['room_id'] = 'other'
        elif change == 'owner':
            booking['related_to_me'] = False
        elif change == 'id':
            booking.update(outlook_booking_id='other', id=100)
        elif change == 'equivalent':
            start_key, end_key = ('start', 'end') if 'room_id' in body else ('time_start', 'time_end')
            booking.update({start_key: DAY + 'T15:00:00Z', end_key: DAY + 'T16:00:00Z'})
        elif change == 'missing_end':
            booking.pop('end' if 'room_id' in body else 'time_end')
        return httpx.Response(200, json=booking if 'room_id' in body else [booking])
    async def request(method, payload, token=None, **credentials):
        root = await mcp_server.build_server()
        with mcp_server.credentials(token, sport_token=credentials.get('sport_token')):
            async with Client(root) as client:
                return (await client.call_tool(method, payload)).data
    monkeypatch.setattr(mcp_client, 'request', request)
    monkeypatch.setattr(mcp_client, 'request_sync', lambda *a, **kw: asyncio.run(request(*a, **kw)))
    monkeypatch.setattr(room_tools, 'read_my_schedule', lambda *a: deepcopy(state['agenda']))
    monkeypatch.setattr(music_tools, 'read_my_schedule', lambda *a: deepcopy(state['agenda']))
    async def agenda(*a):
        state.setdefault('calendar_reads', []).append(a)
        return deepcopy(state['agenda'])
    monkeypatch.setattr(schedule_tools, 'aread_my_schedule', agenda)
    def recommend(service, duration=None):
        tool = room_tools.get_my_available_rooms if service == 'rooms' else music_tools.get_my_available_music_windows
        arguments = {'day': DAY, **({'time_from': '18:00', 'time_to': '19:00'} if service == 'rooms'
                                  else {'duration_minutes': duration} if duration is not None else {})}
        result, artifact = tool.func(SimpleNamespace(context=context), **{**arguments, 'day': date.fromisoformat(DAY)})
        assert result.get('available'), result
        messages = [HumanMessage('Find an available room'), AIMessage('', tool_calls=[{
            'id': 'read', 'name': tool.name, 'args': arguments}]),
            ToolMessage(json.dumps(result), name=tool.name, tool_call_id='read', artifact=artifact),
            AIMessage('Choose below.')]
        return messages
    with backend._http_client('https://synthetic.test', transport=httpx.MockTransport(respond)) as http:
        monkeypatch.setattr(backend, '_client', http)
        yield state, context, recommend


def test_booking_selection_and_window_public_contract():
    assert hasattr(schemas, 'SignupSelection'), 'Clicks need strict service-specific selections'
    selection = schemas.SignupSelection(booking_title='Study group')
    assert selection.booking_title == 'Study group'
    for payload in ({'room_id': 'forged'}, {'time_from': '09:00:00'}, {'time_to': '9:00'},
                    {'booking_title': 12}, {'booking_title': 'x' * 101}, {'booking_title': '  '}):
        with pytest.raises(ValidationError):
            schemas.SignupSelection(**payload)
    window = schemas.MusicBookingWindow(starts_at=datetime(2099, 1, 2, 7, tzinfo=UTC),
        ends_at=datetime(2099, 1, 2, 15, tzinfo=UTC), latest_start_at=datetime(2099, 1, 2, 14, 30, tzinfo=UTC),
        max_duration_minutes=60, duration_minutes=None)
    assert window.step_minutes == 30
    for service in ('rooms', 'music'):
        offer = schemas.SignupOffer(id='opaque', service=service, title='Room', starts_at=window.starts_at,
                                   ends_at=window.ends_at, expires_at=window.latest_start_at,
                                   music_window=window if service == 'music' else None)
        assert offer.booking_title is None
        assert offer.model_dump(mode='json')['service'] == service


def test_native_rooms_recommendation_becomes_offer_without_prose_matching(native_bookings):
    from catix.api import signup
    state, _, recommend = native_bookings
    offers, targets = signup.collect(recommend('rooms'), 'Choose below.', now=NOW)
    offer, = offers
    assert offer.service == 'rooms' and offer.title == 'Study room'
    assert offer.booking_title is None and offer.music_window is None
    assert offer.starts_at == datetime.fromisoformat(DAY + 'T18:00:00+03:00')
    assert offer.ends_at == datetime.fromisoformat(DAY + 'T19:00:00+03:00')
    assert targets[offer.id]['arguments'] == {'room_id': 'r', 'day': DAY, 'time_from': '18:00', 'time_to': '19:00'}
    assert not state['writes']


@pytest.mark.parametrize('duration', [None, 60])
def test_native_music_windows_remain_choices_not_default_bookings(native_bookings, duration):
    from catix.api import signup
    state, _, recommend = native_bookings
    messages = recommend('music', duration)
    now = datetime.fromisoformat(DAY + 'T08:00:00+03:00')
    offers, targets = signup.collect(messages, 'Choose below.', now=now)
    offer, = offers
    assert offer.service == 'music' and offer.title == 'Music room'
    assert offer.starts_at.hour == 7 and offer.ends_at.hour == 22
    window = offer.music_window
    assert window.starts_at == offer.starts_at and window.ends_at == offer.ends_at
    assert window.max_duration_minutes == 120 and window.duration_minutes == duration
    assert window.latest_start_at.hour == (21 if duration else 22)
    assert offer.expires_at == window.latest_start_at and offer.expires_at > now
    assert targets[offer.id]['arguments'] == {'day': DAY}
    assert not state['writes']


@pytest.mark.parametrize('service', ['rooms', 'music', 'sport'])
@pytest.mark.parametrize('later', ['get_my_schedule', 'get_my_available_rooms', 'get_my_available_music_windows',
                                  'get_my_available_trainings', 'rooms_get_free_rooms', 'music_get_available_windows',
                                  'rooms_book_room', 'helper_write'])
def test_later_paired_failures_and_mutations_invalidate_booking_recommendations(native_bookings, service, later):
    from catix.api import signup
    from tests.test_signup_offers import recommendation
    _, _, recommend = native_bookings
    messages = recommendation() if service == 'sport' else recommend(service)
    assert signup.collect(messages, '', now=NOW)[0]
    name = later if later.startswith('get_my_') else 'ask_docs' if later == 'helper_write' else 'call_api_tool'
    args = {} if name != 'call_api_tool' else {'name': later, 'arguments': {}}
    messages.extend([AIMessage('', tool_calls=[{'id': 'later', 'name': name, 'args': args}]),
                     ToolMessage('{"error":"failed"}', name=name, tool_call_id='later',
                         artifact={'action_receipts': [{'outcome': 'unknown'}]} if later == 'helper_write' else None)])
    assert signup.collect(messages, '', now=NOW) == ([], {})


@pytest.mark.parametrize('service', ['rooms', 'music'])
@pytest.mark.parametrize('changed', [None, 'equivalent'])
def test_native_booking_click_rechecks_calendar_service_and_exact_owned_readback(native_bookings, service, changed):
    from catix.api import booking_offers, signup
    state, context, recommend = native_bookings
    offers, targets = signup.collect(recommend(service), '', now=NOW)
    offer, = offers
    selection = schemas.SignupSelection(booking_title='Study group') if service == 'rooms' else schemas.SignupSelection(
        time_from='18:00', time_to='19:00')
    chosen, target = booking_offers.select(offer, targets[offer.id], selection)
    state['changed'] = changed
    state['requests'].clear()
    result = asyncio.run(signup.execute(chosen, target, context, now=NOW))
    assert result.status == 'confirmed', result
    assert result.starts_at == chosen.starts_at and result.ends_at == chosen.ends_at
    assert result.booking_title == chosen.booking_title
    assert len(state['writes']) == 1 and len(state['calendar_reads']) == 1
    paths = [r.url.path for r in state['requests']]
    if service == 'rooms':
        assert any(p.endswith('/can-book') for p in paths)
        assert paths[-1] == '/room-booking/v0/bookings/opaque=='
        body = json.loads(state['writes'][0].content)
        assert body['title'] == 'Study group' and body['room_id'] == 'r'
    else:
        assert paths[-1] == '/music-room/v0/bookings/my_bookings'
        assert all(any(p.endswith(s) for p in paths) for s in ('/users/me', '/remaining_daily_hours',
                                                              '/remaining_weekly_hours', '/daily_bookings'))
        assert json.loads(state['writes'][0].content) == {'time_start': DAY + 'T18:00:00', 'time_end': DAY + 'T19:00:00'}


@pytest.mark.parametrize('service', ['rooms', 'music'])
def test_expiry_and_past_choices_refuse_before_claim_but_later_music_stays_open(native_bookings, service):
    from catix.api import booking_offers, signup
    _, _, recommend = native_bookings
    now = datetime.fromisoformat(DAY + 'T17:00:00+03:00')
    offers, targets = signup.collect(recommend(service), '', now=now)
    offer, = offers
    choice = schemas.SignupSelection(booking_title='Study') if service == 'rooms' else schemas.SignupSelection(
        time_from='18:00', time_to='19:00')
    with pytest.raises(ValueError, match='expired|past'):
        booking_offers.select(offer, targets[offer.id], choice, now=datetime.fromisoformat(DAY + 'T18:00:00+03:00'))
    with pytest.raises(ValueError, match='expired|past'):
        booking_offers.select(offer.model_copy(update={'expires_at': now}), targets[offer.id], choice, now=now)
    if service == 'music':
        chosen, target = booking_offers.select(offer, targets[offer.id], choice, now=now)
        assert chosen.starts_at.hour == 18 and target['arguments']['time_from'] == '18:00'
        assert chosen.expires_at == offer.expires_at


@pytest.mark.parametrize('service', ['rooms', 'music'])
@pytest.mark.parametrize('fault', ['old', 'unpaired', 'failed', 'raw_service', 'artifact_args', 'call_args',
                                 'available_interval', 'source_interval', 'conflict', 'partial', 'unknown_end', 'excluded'])
def test_booking_evidence_is_recomputed_not_trusted_from_visible_results(native_bookings, service, fault):
    from catix.api import signup
    _, _, recommend = native_bookings
    messages = recommend(service)
    assert signup.collect(messages, '', now=NOW)[0]
    message = messages[2]
    data = json.loads(message.content)
    if fault == 'old':
        messages.append(HumanMessage('New turn'))
    elif fault == 'unpaired':
        message.tool_call_id = 'forged'
    elif fault == 'failed':
        message.status = 'error'
    elif fault == 'raw_service':
        call = messages[1].tool_calls[0]
        call['args'] = {'name': 'rooms_get_free_rooms' if service == 'rooms' else 'music_get_available_windows', 'arguments': call['args']}
        call['name'] = message.name = 'call_api_tool'
    elif fault == 'artifact_args':
        message.artifact['room_arguments' if service == 'rooms' else 'music_arguments']['day'] = '2099-01-03'
    elif fault == 'call_args':
        messages[1].tool_calls[0]['args']['day'] = '2099-01-03'
    elif fault == 'available_interval':
        (data['interval'] if service == 'rooms' else data['available'][0])['ends_at'] = DAY + 'T21:00:00+03:00'
    elif fault == 'source_interval':
        source = message.artifact[service if service == 'rooms' else 'music']
        if service == 'rooms':
            source['range'] = '18:00-21:00'
        else:
            source['windows'][0]['max_duration_minutes'] = 30
    elif fault in {'conflict', 'unknown_end'}:
        message.artifact['agenda'].update(total=1, events=[{'title': 'Class', 'starts_at': DAY + 'T18:00:00+03:00',
            'ends_at': None if fault == 'unknown_end' else DAY + 'T19:00:00+03:00'}])
    elif fault == 'partial':
        message.artifact['agenda']['complete'] = False
    elif fault == 'excluded':
        data['excluded'] = data['available']
        data['available'] = []
    message.content = json.dumps(data)
    assert signup.collect(messages, 'Book invented rooms at any time', now=NOW) == ([], {})
