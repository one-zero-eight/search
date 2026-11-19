"""Site calendar selection, including English suppressed only in core-courses."""
import asyncio
from datetime import datetime, timedelta

import httpx
import pytest
from icalendar import Calendar, Event

from catix.innohassle import client as backend, mcp_server
from catix.settings import settings
from tests.mcp_native_helpers import call, connection

DAY = '2026-11-09'
ARGS = {'date_from': DAY, 'date_to': DAY}
TOKEN = 'synthetic-selected-calendar-user'


def ics(*rows):
    calendar = Calendar()
    for index, (title, clock, place) in enumerate(rows):
        event = Event()
        start = datetime.fromisoformat(f'{DAY}T{clock}').replace(tzinfo=settings.tz)
        event.add('uid', f'{title}-{index}')
        event.add('summary', title)
        event.add('location', place)
        event.add('dtstart', start)
        event.add('dtend', start + timedelta(minutes=90))
        calendar.add_component(event)
    return calendar.to_ical()


CORE = [
    ('English for Academic Purposes I', '14:20', '102/103/104/111/301/304/305/306'),
    ('English for Academic Purposes I', '16:00', '102/103/111/305/306'),
    ('Calculus', '10:00', '301'),
]
ENGLISH = [('English for Scientific Purposes (class)', '14:20', '304')]
COURSE = [('English-language robotics', '12:00', '303')]


@pytest.fixture
def selected(monkeypatch):
    monkeypatch.setattr(mcp_server.token_verifier, 'claims', lambda value: {'uid': 'owner'} if value == TOKEN else None)
    state = {
        'user': {'id': 73, 'favorite_event_groups': ['english-e7', 'robotics', 'core'], 'hidden_event_groups': ['hidden-course']},
        'predefined': {'event_groups': ['core', 'hidden-course']},
        'groups': [
            {'alias': 'core', 'name': 'B26-CSE-01', 'tags': [{'type': 'core-courses'}]},
            {'alias': 'english-e7', 'name': 'Selected English', 'tags': []},
            {'alias': 'robotics', 'name': 'Robotics', 'tags': []},
            {'alias': 'hidden-course', 'name': 'Hidden', 'tags': []},
        ],
        'feeds': {'core': ics(*CORE), 'english-e7': ics(*ENGLISH), 'robotics': ics(*COURSE)},
        'fail': {}, 'requests': [],
    }

    def respond(request):
        state['requests'].append(request)
        path = request.url.path
        assert request.method == 'GET'
        if path in state['fail']:
            return httpx.Response(state['fail'][path], json={'detail': 'synthetic unavailable'})
        if path == '/schedule/v0/event-groups/':
            assert 'authorization' not in request.headers
            return httpx.Response(200, json=state.get('catalogue_payload', {'event_groups': state['groups']}))
        assert request.headers['authorization'] == f'Bearer {TOKEN}'
        if path in state.get('responses', {}):
            return state['responses'][path]
        if path == '/schedule/v0/users/me':
            return httpx.Response(200, json=state['user'])
        if path == '/schedule/v0/users/me/predefined':
            return httpx.Response(200, json=state['predefined'])
        if path == '/schedule/v0/users/me/all.ics':
            # The former merged feed really contains all three English entries.
            return httpx.Response(200, content=ics(*CORE, *ENGLISH, *COURSE))
        if path in {'/schedule/v0/users/me/sport.ics', '/events/v1/users/me/events.ics'}:
            return httpx.Response(200, content=ics(('Swimming', '18:00', 'Pool')) if 'sport' in path else ics())
        if path in {'/music-room/v0/bookings/my_bookings', '/room-booking/v0/bookings/my'}:
            return httpx.Response(200, json=[])
        if path.startswith('/schedule/v0/') and path.endswith('.ics'):
            alias = path.removeprefix('/schedule/v0/').removesuffix('.ics')
            assert request.url.params['user_id'] == '73'
            assert request.url.params['export_type'] == 'web'
            return httpx.Response(200, content=state['feeds'][alias])
        raise AssertionError(f'Unexpected path: {path}')

    with backend._http_client('https://selected.test', transport=httpx.MockTransport(respond)) as http:
        monkeypatch.setattr(backend, '_client', http)
        yield state


def read():
    return call('account_get_my_schedule', ARGS, token=TOKEN)


def test_only_selected_english_survives_in_personal_schedule(selected):
    result = read()
    english = [item for item in result['schedule'] if item['title'].startswith('English for ')]
    assert [item['title'] for item in english] == ['English for Scientific Purposes (class)']
    assert english[0]['place'] == '304' and english[0]['time'] == '14:20-15:50'
    assert english[0]['calendar'] == 'english-e7'
    assert {'Calculus', 'English-language robotics', 'Swimming'} <= {i['title'] for i in result['schedule']}
    paths = [r.url.path for r in selected['requests']]
    assert '/schedule/v0/users/me/all.ics' not in paths
    assert '/schedule/v0/hidden-course.ics' not in paths
    assert paths.count('/schedule/v0/core.ics') == 1
    assert 'not_read' not in result


@pytest.mark.parametrize('hide', [True, False])
def test_no_visible_assistant_english_keeps_core_english(selected, hide):
    if hide:
        selected['user']['hidden_event_groups'].append('english-e7')
    else:
        selected['user']['favorite_event_groups'].remove('english-e7')
    result = read()
    assert sum(i['title'] == 'English for Academic Purposes I' for i in result['schedule']) == 2
    assert not any(i['title'] == ENGLISH[0][0] for i in result['schedule'])
    assert not any(r.url.path.endswith('/english-e7.ics') for r in selected['requests'])


def test_predefined_english_is_selected_and_hidden_predefined_is_excluded(selected):
    selected['user']['favorite_event_groups'] = []
    selected['predefined']['event_groups'] += ['english-e7']
    result = read()
    assert {i['title'] for i in result['schedule']} == {'Calculus', ENGLISH[0][0], 'Swimming'}


@pytest.mark.parametrize('status', [403, 404, 503])
def test_failed_selected_english_does_not_restore_other_streams(selected, status):
    selected['fail']['/schedule/v0/english-e7.ics'] = status
    result = read()
    assert not any(i['title'].startswith('English for ') for i in result['schedule'])
    assert {'Calculus', 'Swimming'} <= {i['title'] for i in result['schedule']}
    assert any(s.startswith('class:') and 'english-e7' in s for s in result['not_read'])


def test_missing_selected_catalogue_entry_is_reported_not_replaced(selected):
    selected['groups'] = [g for g in selected['groups'] if g['alias'] != 'english-e7']
    result = read()
    assert not any(i['title'].startswith('English for ') for i in result['schedule'])
    assert any('english-e7' in s for s in result['not_read'])


@pytest.mark.parametrize('path', ['/schedule/v0/users/me', '/schedule/v0/users/me/predefined', '/schedule/v0/event-groups/'])
def test_failed_selection_is_partial_without_merged_fallback(selected, path):
    selected['fail'][path] = 503
    result = read()
    assert {i['title'] for i in result['schedule']} == {'Swimming'}
    assert any(s.startswith('class:') for s in result['not_read'])
    assert not any(r.url.path.endswith('/all.ics') for r in selected['requests'])


def test_empty_selection_does_not_infer_profile_group(selected):
    selected['user']['favorite_event_groups'] = []
    selected['predefined']['event_groups'] = []
    result = read()
    assert {i['title'] for i in result['schedule']} == {'Swimming'}
    assert 'not_read' not in result


def test_selection_is_fresh_on_next_read(selected):
    read()
    selected['user']['hidden_event_groups'].append('english-e7')
    selected['requests'].clear()
    result = read()
    assert sum(i['title'] == 'English for Academic Purposes I' for i in result['schedule']) == 2
    assert not any(i['title'] == ENGLISH[0][0] for i in result['schedule'])


@pytest.mark.parametrize('alias', ['../users/me', '%2e%2e', 'a?token=x', 'a#x', 'a/b', 'a\\b'])
def test_invalid_calendar_alias_never_becomes_a_request_path(selected, alias):
    selected['user']['favorite_event_groups'] = [alias]
    selected['predefined']['event_groups'] = []
    selected['groups'].append({'alias': alias, 'tags': []})
    result = read()
    assert any(s.startswith('class:') for s in result['not_read'])
    assert {i['title'] for i in result['schedule']} == {'Swimming'}
    assert all(not r.url.path.endswith('.ics') or '/users/me/' in r.url.path for r in selected['requests'])


def test_cyrillic_calendar_alias_is_preserved(selected):
    alias = 'fall26-ru-bs2-акм'
    selected['user']['favorite_event_groups'] = [alias]
    selected['predefined']['event_groups'] = []
    selected['groups'].append({'alias': alias, 'tags': []})
    selected['feeds'][alias] = ics(('Applied mathematics', '12:00', '301'))
    result = read()
    assert any(i.get('calendar') == alias for i in result['schedule'])


@pytest.mark.parametrize('tags', [{}, False, 0, ''])
def test_malformed_tags_are_not_treated_as_non_core_calendar(selected, tags):
    selected['groups'][0]['tags'] = tags
    result = read()
    assert not any(i['title'] == 'English for Academic Purposes I' for i in result['schedule'])
    assert any('core' in problem for problem in result['not_read'])


@pytest.mark.parametrize('payload', [{}, [], {'event_groups': None}, {'event_groups': 'core'}])
def test_malformed_catalogue_does_not_discard_other_personal_sources(selected, payload):
    selected['catalogue_payload'] = payload
    result = read()
    assert {i['title'] for i in result['schedule']} == {'Swimming'}
    assert any(s.startswith('class:') for s in result['not_read'])


@pytest.mark.parametrize('field,value', [('favorite_event_groups', None), ('hidden_event_groups', 'core'),
                                        ('favorite_event_groups', [None]), ('id', True)])
def test_malformed_selection_is_not_an_empty_or_public_schedule(selected, field, value):
    selected['user'][field] = value
    result = read()
    assert {i['title'] for i in result['schedule']} == {'Swimming'}
    assert any(s.startswith('class:') for s in result['not_read'])


def test_broken_english_ics_is_partial_without_wrong_english_fallback(selected):
    selected['feeds']['english-e7'] = 'not a calendar'
    result = read()
    assert not any(i['title'].startswith('English for ') for i in result['schedule'])
    assert any('english-e7' in s for s in result['not_read'])


@pytest.mark.parametrize('title', [' FOREIGN LANGUAGE ', 'Иностранный язык', 'eNgLiSh practice'])
def test_site_english_title_variants_are_removed_only_from_core(selected, title):
    selected['feeds']['core'] = ics((title, '10:00', '301'))
    selected['feeds']['robotics'] = ics((title, '12:00', '303'))
    result = read()
    matching = [i for i in result['schedule'] if i['title'] == title]
    assert len(matching) == 1 and matching[0]['calendar'] == 'robotics'


@pytest.mark.parametrize('remote', [False, True])
@pytest.mark.parametrize('token', [None, 'forged-token'])
def test_no_valid_identity_means_no_upstream_requests(selected, remote, token):
    async def run():
        async with connection(remote=remote, token=token) as mcp:
            return await mcp.call_tool('account_get_my_schedule', ARGS, raise_on_error=False)
    assert asyncio.run(run()).is_error
    assert selected['requests'] == []


@pytest.mark.parametrize('remote', [False, True], ids=['local', 'http'])
@pytest.mark.parametrize('generic', [False, True], ids=['direct', 'generic'])
@pytest.mark.parametrize('alias', ['core', 'robotics'])
@pytest.mark.parametrize('summary', [None, ''], ids=['missing-summary', 'empty-summary'])
def test_untitled_selected_event_preserves_personal_schedule(selected, remote, generic, alias, summary):
    calendar = Calendar.from_ical(selected['feeds'][alias])
    event = Event()
    begin = datetime.fromisoformat(f'{DAY}T08:00').replace(tzinfo=settings.tz)
    event.add('uid', 'untitled-selected-event')
    event.add('dtstamp', begin)
    event.add('dtstart', begin)
    event.add('dtend', begin + timedelta(minutes=90))
    event.add('location', 'Untitled classroom')
    if summary is not None:
        event.add('summary', summary)
    calendar.subcomponents.insert(0, event)
    selected['feeds'][alias] = calendar.to_ical()
    selected['responses'] = {
        '/events/v1/users/me/events.ics': httpx.Response(200, content=ics(('Enrolled event', '19:00', 'Hall'))),
        '/music-room/v0/bookings/my_bookings': httpx.Response(200, json=[{
            'id': 42, 'time_start': begin.isoformat(), 'time_end': (begin + timedelta(hours=1)).isoformat(),
        }]),
        '/room-booking/v0/bookings/my': httpx.Response(200, json=[{
            'outlook_booking_id': 'AA+/BB==', 'room_id': 'r', 'title': 'Study',
            'start': begin.isoformat(), 'end': (begin + timedelta(hours=1)).isoformat(),
        }]),
    }

    async def run():
        async with connection(remote=remote, token=TOKEN) as mcp:
            name = 'call_tool' if generic else 'account_get_my_schedule'
            arguments = {'name': 'account_get_my_schedule', 'arguments': ARGS} if generic else ARGS
            return (await mcp.call_tool(name, arguments)).data

    result = asyncio.run(run())
    untitled = [item for item in result['schedule'] if item.get('place') == 'Untitled classroom']
    assert len(untitled) == 1
    assert untitled[0]['calendar'] == alias
    assert untitled[0]['kind'] == 'class'
    assert untitled[0]['date'] == f'{DAY} Mon' and untitled[0]['time'] == '08:00-09:30'
    assert 'title' not in untitled[0]
    assert {item.get('title') for item in result['schedule']} == {
        None, 'Calculus', ENGLISH[0][0], COURSE[0][0], 'Swimming', 'Enrolled event',
    }
    assert {item['kind'] for item in result['schedule']} == {'class', 'sport', 'event'}
    assert {item['booking_id'] for item in result['bookings']} == {'42', 'AA+/BB=='}
    assert 'not_read' not in result


@pytest.mark.parametrize('remote', [False, True])
def test_generic_mcp_dispatch_uses_the_same_selected_calendars(selected, remote):
    async def run():
        async with connection(remote=remote, token=TOKEN) as mcp:
            return (await mcp.call_tool('call_tool', {'name': 'account_get_my_schedule', 'arguments': ARGS})).data
    result = asyncio.run(run())
    assert [i['title'] for i in result['schedule'] if i['title'].startswith('English for ')] == [ENGLISH[0][0]]
