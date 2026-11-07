"""Static read services retain their paths, aliases, and response privacy."""
from copy import deepcopy

import httpx
import pytest

from catix.innohassle import actions, mcp_domain, client as backend
from tests.test_api_actions import read

BODIES = {
    '/maps/v0/scenes/areas/search': [{'scene_id': 'floor3', 'area': {'title': '301', 'ru_title': '301',
        'description': None, 'people': ['private']}}],
    '/maps/v0/scenes/': [{'scene_id': 'floor3', 'title': 'Floor 3', 'ru_title': None, 'private': 'hidden'}],
    '/events/v1/events/': [{'id': 'e1', 'creator_id': 'private', 'data': {'name': 'Lecture',
        'starts_at': '2026-11-08T15:00:00+03:00', 'duration_hours': 1.5, 'location': {'display_name': '108'}}}],
    '/clubs/v0/clubs/': [{'title': 'Hobby', 'short_description': None, 'is_active': False, 'leaders': ['private']}],
    '/music-room/v0/bookings/daily_bookings': [{'time_start': '2026-11-08T12:00:00',
        'time_end': '2026-11-08T13:00:00', 'user_alias': 'private'}],
}


@pytest.fixture
def service_api(monkeypatch):
    from catix.innohassle import token
    monkeypatch.setattr(token, 'claims', lambda value: {'uid': 'synthetic-' + value})
    seen, bodies = [], deepcopy(BODIES)
    def handle(request):
        seen.append(request)
        assert request.method == 'GET'
        assert 'authorization' not in request.headers and 'cookie' not in request.headers
        return httpx.Response(200, json=bodies[request.url.path])
    with backend._http_client('https://api.innohassle.ru', transport=httpx.MockTransport(handle)) as client:
        monkeypatch.setattr(backend, '_client', client)
        yield seen, bodies


@pytest.mark.parametrize('name,args,path', [
    ('maps_scenes_search_areas', {'query': '301'}, '/maps/v0/scenes/areas/search'),
    ('maps_scenes_scenes', {}, '/maps/v0/scenes/'),
    ('clubs_get_clubs_list_clubs__get', {}, '/clubs/v0/clubs/'),
    ('music_bookings_daily_bookings', {'date': '2026-11-08'}, '/music-room/v0/bookings/daily_bookings'),
    ('events_events_list_events', {}, '/events/v1/events/'),
])
def test_public_reads_never_receive_credentials_and_only_project_reviewed_fields(service_api, name, args, path):
    result = read(name, args, 'must-not-forward')
    assert result['total'] == 1 and result['truncated'] is False
    assert 'private' not in str(result) and 'must-not-forward' not in str(result)
    assert [r.url.path for r in service_api[0]] == [path]
    assert mcp_domain.policy(name)['auth'] == 'public'


def test_events_use_v1_and_original_query_aliases(service_api):
    params = {'from': '2026-11-08T00:00:00+03:00', 'to': '2026-11-09T00:00:00+03:00', 'club': 0}
    result = read('events_events_list_events', params, None)
    seen, _ = service_api
    assert [r.url.path for r in seen] == ['/events/v1/events/']
    assert dict(seen[-1].url.params) == {**params, 'club': '0'}
    assert result['data'][0]['data']['name'] == 'Lecture'


def test_music_does_not_claim_availability_beyond_occupied_intervals(service_api):
    note = read('music_bookings_daily_bookings', {'date': '2026-11-08'}, None)['note']
    assert 'opening hours' in note and 'Do not infer free slots' in note


@pytest.mark.parametrize('name,params', [
    ('events_events_list_events', {'from': 'tomorrow'}),
    ('events_events_list_events', {'from': '2026-11-08'}),
    ('events_events_list_events', {'club': True}),
    ('events_events_list_events', {'from_': '2026-11-08T00:00:00+03:00'}),
    ('music_bookings_daily_bookings', {'date': '2026-02-30'}),
    ('maps_scenes_search_areas', {'query': ''}),
    ('maps_scenes_search_areas', {'query': '301', 'url': 'https://evil.test'}),
])
def test_invalid_request_rejected_without_network(service_api, name, params):
    with pytest.raises(actions.ReadError):
        read(name, params, None)
    assert service_api[0] == []


def test_optional_null_query_values_omitted_not_sent_as_empty_strings(service_api):
    read('events_events_list_events', {'from': None, 'to': None, 'club': None}, None)
    assert not service_api[0][-1].url.query


def test_query_text_remains_a_safe_encoded_parameter(service_api):
    query = 'Принтер & room?url=https://evil.test/#secret'
    read('maps_scenes_search_areas', {'query': query}, None)
    request = service_api[0][-1]
    assert request.url.path == '/maps/v0/scenes/areas/search'
    assert dict(request.url.params) == {'query': query}
    assert request.url.host == 'api.innohassle.ru'
