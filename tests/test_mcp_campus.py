"""Public campus domain tools over the production MCP HTTP connection."""

import asyncio
from datetime import date, datetime
from types import SimpleNamespace

import httpx
import pytest
from langchain_core.messages import HumanMessage
from pydantic import SecretStr

from catix.agent import api_tools, tools
from catix.innohassle import mcp_campus as campus_tools
from catix.innohassle import client as backend, mcp_client, mcp_server
from tests.mcp_native_helpers import registered_tools, input_schema
from catix.settings import settings
from tests.mcp_helpers import install_http_adapter


PUBLIC = {
    'schedule_get_schedule': ('tools', 'get_schedule'),
    'timetable_get_courses': ('campus_tools', 'get_courses'),
    'timetable_get_room_timetable': ('campus_tools', 'get_room_timetable'),
    'maps_find_room': ('tools', 'find_room'),
    'clubs_get_clubs': ('tools', 'get_clubs'),
}
GROUPS = ['B26-DSAI-04', 'B26-CSE-02']
EMPTY_ICS = 'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n'


@pytest.fixture
def http_boundary(monkeypatch):
    monkeypatch.setattr(mcp_server.token_verifier, 'claims', lambda token: {'uid': 'owner-' + token})
    install_http_adapter(monkeypatch)


@pytest.fixture
def campus_http(http_boundary, monkeypatch):
    seen = []
    monkeypatch.setattr(backend, 'event_groups', lambda: [
        {'name': group, 'alias': group.lower()} for group in GROUPS])
    monkeypatch.setattr(backend, 'group_schedule_ics', lambda alias: seen.append(alias) or EMPTY_ICS)
    return seen


def runtime(group=None, question='What are my classes?', user='alice'):
    return SimpleNamespace(context=SimpleNamespace(study_group=group, user_id=user,
        innohassle_token=SecretStr('ih-' + user), sport_token=SecretStr('sport-' + user)),
        state={'messages': [HumanMessage(content=question)]})


def test_public_native_registration_and_explicit_http_schedule(campus_http):
    for name, (module, legacy) in PUBLIC.items():
        operation = registered_tools().get(name)
        assert operation is not None, name
        from fastmcp.server.dependencies import get_dependency_parameters
        assert not get_dependency_parameters(operation.fn)
        assert operation.annotations.read_only_hint is True
        assert not {'runtime', 'uid', 'user_id', 'token', 'sport_token'} & input_schema(name)['properties'].keys()
    schema = input_schema('schedule_get_schedule')
    assert 'group' in schema['required']
    assert schema['properties']['group']['type'] == 'string'
    # Direct MCP clients may explicitly select any public group. This is not identity.
    result = mcp_client.request_sync('call_tool', {'name': 'schedule_get_schedule',
        'arguments': {'group': GROUPS[1], 'date_from': '2099-01-01', 'date_to': '2099-01-02'}}, None)
    assert result['schedule'] == GROUPS[1]
    assert result['range'] == ['2099-01-01', '2099-01-02']
    assert result['classes'] == []
    assert campus_http == [GROUPS[1].lower()]
    for bad in [{}, {'group': None}, {'group': ''}, {'group': '   '}]:
        assert 'error' in mcp_client.request_sync('call_tool', {
            'name': 'schedule_get_schedule', 'arguments': bad}, None)


@pytest.mark.parametrize('asynchronous', [False, True])
@pytest.mark.parametrize('group,question,explicit,expected', [
    (GROUPS[0], 'My classes?', None, GROUPS[0]),
    (GROUPS[0], 'My classes?', GROUPS[0], GROUPS[0]),
    (None, f'Classes for {GROUPS[1]}?', GROUPS[1], GROUPS[1]),
    (GROUPS[0], f'Classes for {GROUPS[1]}?', GROUPS[1], GROUPS[1]),
    (None, 'My classes?', None, None),
    (None, 'My classes?', 'B26-CSE-01', None),
    (GROUPS[0], 'My classes?', GROUPS[1], None),
])
def test_agent_schedule_trusted_selection_before_http(campus_http, monkeypatch, asynchronous,
                                                     group, question, explicit, expected):
    wire = []
    original = mcp_client.request
    original_sync = mcp_client.request_sync

    async def request(*args, **kwargs):
        wire.append((args, kwargs))
        return await original(*args, **kwargs)

    def request_sync(*args, **kwargs):
        wire.append((args, kwargs))
        return original_sync(*args, **kwargs)

    monkeypatch.setattr(mcp_client, 'request', request)
    monkeypatch.setattr(mcp_client, 'request_sync', request_sync)
    args = {'date_from': '2099-01-01'}
    if explicit is not None:
        args['group'] = explicit
    original_args = dict(args)
    rt = runtime(group, question)
    result = (asyncio.run(api_tools._acall('schedule_get_schedule', rt, args)) if asynchronous
              else api_tools._call('schedule_get_schedule', rt, args))
    assert args == original_args
    if expected is None:
        assert result == {'error': tools.GROUP_UNKNOWN}
        assert not wire and not campus_http
    else:
        assert result['schedule'] == expected
        assert campus_http == [expected.lower()]
        assert wire
        for positional, keywords in wire:
            assert positional[0] == 'call_tool'
            assert positional[1] == {'name': 'schedule_get_schedule', 'arguments': {
                'group': expected, 'date_from': '2099-01-01'}}
            assert positional[2] is None and not keywords


@pytest.mark.parametrize('asynchronous', [False, True])
@pytest.mark.parametrize('name,args', [
    ('schedule_get_schedule', {'group': 123}),
    ('schedule_get_schedule', {'date_from': '2099-02-30'}),
    ('schedule_get_schedule', {'date_to': '01/02/2099'}),
    ('schedule_get_schedule', {'query': False}),
    ('timetable_get_courses', {'query': 42}),
    ('timetable_get_courses', {'query': 'x' * 81}),
    ('timetable_get_room_timetable', {'day': '2099-02-30'}),
    ('timetable_get_room_timetable', {'room': 108}),
    ('timetable_get_room_timetable', {'time_from': '09:00:00'}),
    ('timetable_get_room_timetable', {'time_to': '24:00'}),
    ('maps_find_room', {'query': False}),
    ('clubs_get_clubs', {'include_inactive': 'false'}),
    ('clubs_get_clubs', {'type': 'unknown'}),
])
def test_invalid_business_arguments_are_rejected_by_server(campus_http, monkeypatch, asynchronous, name, args):
    wire = []
    original = mcp_client.request

    async def request(*positional, **keywords):
        wire.append((positional, keywords))
        return await original(*positional, **keywords)

    monkeypatch.setattr(mcp_client, 'request', request)
    rt = runtime(GROUPS[0])
    result = (asyncio.run(api_tools._acall(name, rt, args)) if asynchronous else api_tools._call(name, rt, args))
    assert 'error' in result
    assert campus_http == []
    # Trusted group selection is host-owned; all other per-tool validation is remote.
    if name == 'schedule_get_schedule' and 'group' in args:
        assert wire == []
    else:
        expected = {**args, 'group': GROUPS[0]} if name == 'schedule_get_schedule' else args
        assert wire == [(('call_tool', {'name': name, 'arguments': expected}, None), {})]


@pytest.mark.parametrize('name,args', [
    ('clubs_get_clubs', {'query': '', 'include_inactive': False}),
    ('timetable_get_room_timetable', {'day': '2099-01-01', 'time_from': '00:00'}),
])
def test_native_business_arguments_are_not_normalized_before_wire(monkeypatch, name, args):
    wire = []
    monkeypatch.setattr(mcp_client, 'request_sync', lambda *a, **kw: wire.append((a, kw)) or {})
    assert api_tools._call(name, runtime(), args) == {}
    assert wire == [(('call_tool', {'name': name, 'arguments': args}, None), {})]


@pytest.mark.parametrize('field,value', [
    ('runtime', {'context': {'study_group': GROUPS[1]}}), ('node_input', {'group': GROUPS[1]}),
    ('uid', 'other'), ('user_id', 123), ('telegram_id', 456), ('calendar_owner', 'tg:456'),
    ('headers', {'Authorization': 'Bearer injected'}), ('token', 'injected'),
    ('sport_token', 'injected'), ('question', f'Classes for {GROUPS[1]}?'),
])
def test_identity_runtime_and_node_input_are_rejected_at_server_boundary(campus_http, field, value):
    for name in PUBLIC:
        args = {'query': 'test'} if name in {'timetable_get_courses', 'maps_find_room'} else {}
        if name == 'schedule_get_schedule':
            args['group'] = GROUPS[0]
        args[field] = value
        assert 'error' in api_tools._call(name, runtime(GROUPS[0]), args)
    assert campus_http == []
    with pytest.raises(ValueError):
        api_tools.CallApiToolArgs.model_validate({'name': 'schedule_get_schedule', field: value})


def test_schedule_schema_does_not_mutate_legacy_optional_group():
    legacy = tools.GetScheduleArgs.model_json_schema()
    for _ in range(3):
        assert input_schema('schedule_get_schedule')['required'] == ['group']
    assert 'group' not in legacy.get('required', [])
    assert legacy['properties']['group']['default'] is None


def test_concurrent_users_keep_their_own_group_without_identity_delegation(campus_http, monkeypatch):
    async def run():
        return await asyncio.gather(*[
            api_tools._acall('schedule_get_schedule', runtime(group, user=user), {'date_from': '2099-01-01'})
            for group, user in zip(GROUPS, ['alice', 'bob'])])

    assert [result['schedule'] for result in asyncio.run(run())] == GROUPS
    assert sorted(campus_http) == sorted(group.lower() for group in GROUPS)


@pytest.fixture
def public_upstream(http_boundary, monkeypatch):
    from tests.test_timetable import DATA

    monkeypatch.setattr(campus_tools, '_now', lambda: datetime(2026, 11, 2, 8, tzinfo=settings.tz))
    club = {'title': 'Chess', 'type': 'hobby', 'is_active': True, 'short_description': 'Weekly games',
            'description': 'Wednesday 18:00 in room 313', 'leader_innohassle_id': 'leader',
            'links': [{'label': 'Join', 'link': 'https://example.test/chess'}]}
    area = {'svg_polygon_id': 'a1', 'title': '313', 'ru_title': 'Аудитория 313',
            'description': 'Open 09:00–18:00', 'people': ['Professor Example'], 'room_booking_id': None}
    hit = {'scene_id': 'floor-3', 'area': area}
    responses = {
        '/clubs/v0/clubs/': [club, {**club, 'title': 'Old chess', 'is_active': False},
                             {**club, 'title': 'Robotics', 'type': 'tech'}],
        '/clubs/v0/leaders/': {'leader': {'name': 'Leader Example', 'telegram_alias': '@leader'}},
        '/maps/v0/scenes/': [{'scene_id': 'floor-3', 'title': 'University, floor 3'}],
        '/maps/v0/scenes/areas/search': [hit, hit],
        '/schedule-assistant/v0/timetable': DATA,
        '/schedule/v0/event-groups/': {'event_groups': [{'name': group, 'alias': group.lower()} for group in GROUPS]},
    }
    requests = []

    def reply(request):
        requests.append(request)
        if request.url.path == f'/schedule/v0/{GROUPS[0].lower()}.ics':
            return httpx.Response(200, text=EMPTY_ICS)
        assert request.url.path in responses, request.url
        return httpx.Response(200, json=responses[request.url.path], headers={'Set-Cookie': 'session=other; Path=/'})

    with backend._http_client('https://public.test', transport=httpx.MockTransport(reply)) as http:
        monkeypatch.setattr(backend, '_client', http)
        yield requests


@pytest.mark.parametrize('name,args', [
    ('schedule_get_schedule', {'group': GROUPS[0], 'date_from': '2099-01-01'}),
    ('timetable_get_courses', {'query': 'Зуев'}),
    ('timetable_get_room_timetable', {'day': '2026-11-02', 'time_from': '14:00', 'time_to': '15:00'}),
    ('maps_find_room', {'query': 'Professor Example'}),
    ('clubs_get_clubs', {'query': 'chess', 'type': 'hobby', 'include_inactive': True}),
])
def test_public_http_domain_parity_and_upstream_credential_stripping(public_upstream, monkeypatch, name, args):
    # Even signed-in direct MCP clients cannot pass their identity upstream for public data.
    result = mcp_client.request_sync('call_tool', {'name': name, 'arguments': args},
                                     'ih-alice', sport_token='sport-alice')
    anonymous = mcp_client.request_sync('call_tool', {'name': name, 'arguments': args}, None)
    assert result == anonymous
    assert public_upstream
    for request in public_upstream:
        assert not {'authorization', 'cookie', 'x-innohassle-token', 'x-sport-token'} & request.headers.keys()
        assert 'alice' not in str(request.url)
    if name == 'schedule_get_schedule':
        assert result['schedule'] == GROUPS[0]
        # The original upstream endpoint uses a constant public selector, not the asker's identity.
        assert dict(public_upstream[-1].url.params) == {'user_id': '0', 'export_type': 'group'}
    elif name == 'timetable_get_courses':
        assert result['teachers'][0]['telegram'] == '@zouev'
        assert result['courses'][0]['instructors'][0]['role'] == 'Primary Instructor'
        assert result['courses'][0]['blocks'] == ['Блок 2']
        assert {c['kind'] for c in result['courses'][0]['weekly_classes']} == {'lecture', 'lab'}
    elif name == 'timetable_get_room_timetable':
        assert result['free_of_classes'] == [{'room': '313', 'name': 'Room 313', 'capacity': 30}]
        assert result['with_classes'] == ['108']
        assert 'bookings are not counted' in result['note'] and 'locked' in result['note']
        assert 'bookable' not in result and 'free' not in result
    elif name == 'maps_find_room':
        assert result['total'] == 1  # duplicate map hits are merged
        assert result['areas'] == [{'title': '313', 'ru_title': 'Аудитория 313', 'where': 'University, floor 3',
            'description': 'Open 09:00–18:00', 'people': ['Professor Example'], 'bookable': False}]
    else:
        assert result['total'] == 2
        assert [club['active'] for club in result['clubs']] == [True, False]
        assert result['clubs'][0]['leader'] == {'name': 'Leader Example', 'telegram': '@leader'}
        assert result['clubs'][0]['links'] == [{'label': 'Join', 'url': 'https://example.test/chess'}]
        assert '18:00' in result['clubs'][0]['description']


def test_http_direct_and_generic_schedule_reject_delegated_context(campus_http):
    async def run():
        async with mcp_client._connection(None) as client:
            allowed = await client.call_tool('schedule_get_schedule', {'group': GROUPS[0]})
            assert allowed.data['schedule'] == GROUPS[0]
            assert campus_http == [GROUPS[0].lower()]
            for generic in (False, True):
                for bad in [{}, {'group': None}, {'group': GROUPS[0], 'runtime': {}},
                            {'group': GROUPS[0], 'node_input': {}}, {'group': GROUPS[0], 'user_id': 123},
                            {'group': GROUPS[0], 'headers': {'X-Innohassle-Token': 'forged'}}]:
                    result = await client.call_tool('call_tool' if generic else 'schedule_get_schedule',
                        {'name': 'schedule_get_schedule', 'arguments': bad} if generic else bad, raise_on_error=False)
                    assert result.is_error
            assert campus_http == [GROUPS[0].lower()]
    asyncio.run(run())


def test_schedule_keeps_calendar_filters_deduplication_and_domain_types(campus_http, monkeypatch):
    from icalendar import Calendar, Event

    calendar = Calendar()
    calendar.add('version', '2.0')
    for uid, title in [('first', 'Programming lab'), ('duplicate', 'Programming lab'), ('other', 'Math lecture')]:
        event = Event()
        event.add('uid', uid)
        event.add('summary', title)
        event.add('dtstart', datetime(2099, 1, 1, 9, tzinfo=settings.tz))
        event.add('dtend', datetime(2099, 1, 1, 10, tzinfo=settings.tz))
        event.add('location', '313')
        event.add('description', 'Instructor: Professor Example\nGroups: B26-DSAI-04')
        calendar.add_component(event)
    marker = Event()
    marker.add('uid', 'marker')
    marker.add('summary', 'Programming lab marker')
    marker.add('dtstart', date(2099, 1, 1))
    calendar.add_component(marker)
    monkeypatch.setattr(backend, 'group_schedule_ics', lambda alias: calendar.to_ical())
    result = api_tools._call('schedule_get_schedule', runtime(GROUPS[0]),
        {'date_from': '2099-01-01', 'date_to': '2099-01-01', 'query': 'Programming'})
    assert result['total'] == 1
    assert result['classes'][0]['title'] == 'Programming lab'
    assert result['classes'][0]['time'] == '09:00-10:00'
    assert result['classes'][0]['room'] == '313'
    assert result['classes'][0]['instructor'] == 'Professor Example'


def test_club_listing_defaults_and_filters_are_not_generic_endpoint_semantics(public_upstream):
    result = api_tools._call('clubs_get_clubs', runtime(), {'type': 'hobby'})
    assert result == {'total': 1, 'clubs': [{'title': 'Chess', 'type': 'hobby', 'short_description': 'Weekly games'}]}
    details = api_tools._call('clubs_get_clubs', runtime(), {'query': 'chess', 'type': 'hobby'})
    assert details['total'] == 1 and details['clubs'][0]['active'] is True
