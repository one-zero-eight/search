"""Draft workflows through real MCP with signed users and synthetic upstream HTTP."""
import asyncio
import copy
import json
from datetime import datetime, timedelta, timezone

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from catix.innohassle import client as backend, token
from tests.mcp_native_helpers import connection

ID = 'a' * 24
START = '2099-01-01T18:00:00+03:00'
CREATE = {'name': 'Club evening', 'description': 'Board games', 'locale': 'en',
          'starts_at': START, 'location': 'Room 301', 'duration_hours': 2,
          'registration_url': 'https://example.test/register', 'club_id': '42'}


@pytest.fixture
def signed(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(token._keys, 'get_signing_keys', lambda: [key.public_key()])
    return jwt.encode({'uid': 'draft-owner', 'exp': datetime.now(timezone.utc) + timedelta(hours=1)},
                      key, algorithm='RS256')


@pytest.fixture
def upstream(monkeypatch):
    draft = {'id': ID, 'can_edit': True, 'can_submit': False, 'has_public': False,
             'cannot_submit_reasons': ['Image is missing'], 'status': None,
             'data': {'starts_at': None, 'location': None, 'duration_hours': None,
                      'enrollment': None, 'locales': {}, 'hosts': [], 'links': []}}
    state = {'draft': draft, 'profile': {'roles': ['club-leader'],
             'clubs': [{'club_id': '42', 'title': 'Games'}]}, 'hook': None}
    requests = []

    def reply(request):
        requests.append(request)
        if state['hook']:
            override = state['hook'](request)
            if override is not None:
                return override
        path, method = request.url.path, request.method
        if path == '/events/v1/users/me' and method == 'GET':
            return httpx.Response(200, json=state['profile'])
        data = json.loads(request.content) if request.content else {}
        if method in {'POST', 'PATCH'} and path in {'/events/v1/drafts/', f'/events/v1/drafts/{ID}'}:
            for key, value in data.items():
                if key == 'locales':
                    draft['data']['locales'].update({locale: {'name': None, 'description': None} for locale in value})
                elif key == 'location':
                    draft['data'][key] = {'display_name': value, 'url': ''} if value else None
                else:
                    draft['data'][key] = value
        elif method == 'PUT' and '/locales/' in path:
            draft['data']['locales'][path.rsplit('/', 1)[1]] = data
        elif method == 'POST' and path.endswith('/hosts/clubs'):
            draft['data']['hosts'].append({'id': 'host-1', 'type': 'club', 'club_id': data['club_id']})
        elif method != 'GET' or path != f'/events/v1/drafts/{ID}':
            pytest.fail(f'Unexpected request: {method} {path}')
        return httpx.Response(200, json=copy.deepcopy(draft))

    with backend._http_client('https://synthetic.test', transport=httpx.MockTransport(reply)) as http:
        monkeypatch.setattr(backend, '_client', http)
        yield state, requests


def invoke(signed, name, arguments, generic=True):
    async def run():
        async with connection(True, signed) as client:
            return await client.call_tool('call_tool' if generic else name,
                {'name': name, 'arguments': arguments} if generic else arguments, raise_on_error=False)
    return asyncio.run(run())


@pytest.mark.parametrize('generic', [False, True])
def test_create_draft_checks_rights_writes_locale_host_and_reads_back(signed, upstream, generic):
    _, requests = upstream
    result = invoke(signed, 'events_create_draft', CREATE, generic)
    assert not result.is_error
    assert result.data['done'] is True
    assert result.data['draft']['id'] == ID
    locale = result.data['draft']['data']['locales']['en']
    assert locale['name'] == 'Club evening'
    assert json.loads(locale['description']) == {
        'type': 'doc', 'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': 'Board games'}]}]}
    assert result.data['submitted'] is False
    assert [(r.method, r.url.path) for r in requests] == [
        ('GET', '/events/v1/users/me'), ('POST', '/events/v1/drafts/'),
        ('PUT', f'/events/v1/drafts/{ID}/locales/en'), ('POST', f'/events/v1/drafts/{ID}/hosts/clubs'),
        ('GET', f'/events/v1/drafts/{ID}')]
    assert json.loads(requests[1].content) == {
        'starts_at': START, 'location': 'Room 301', 'duration_hours': 2, 'locales': ['en'],
        'enrollment': {'type': 'external', 'url': CREATE['registration_url'], 'capacity': None}}
    assert json.loads(requests[3].content) == {'club_id': '42'}
    assert all(r.headers['Authorization'] == f'Bearer {signed}' for r in requests)


@pytest.mark.parametrize('generic', [False, True])
def test_update_partial_locale_preserves_other_text_and_languages(signed, upstream, generic):
    state, requests = upstream
    state['draft']['data']['locales'] = {
        'en': {'name': 'Original', 'description': 'Keep description'},
        'ru': {'name': 'Название', 'description': 'Описание'}}
    result = invoke(signed, 'events_update_draft', {
        'draft_id': ID, 'locale': 'en', 'name': 'Changed', 'location': 'Room 302'}, generic)
    assert not result.is_error
    assert result.data['done'] is True and result.data['submitted'] is False
    assert result.data['draft']['data']['locales'] == {
        'en': {'name': 'Changed', 'description': 'Keep description'},
        'ru': {'name': 'Название', 'description': 'Описание'}}
    assert [(r.method, r.url.path) for r in requests] == [
        ('GET', f'/events/v1/drafts/{ID}'), ('PATCH', f'/events/v1/drafts/{ID}'),
        ('PUT', f'/events/v1/drafts/{ID}/locales/en'), ('GET', f'/events/v1/drafts/{ID}')]
    assert json.loads(requests[1].content) == {'location': 'Room 302'}
    assert json.loads(requests[2].content) == {'name': 'Changed', 'description': 'Keep description'}


@pytest.mark.parametrize('generic', [False, True])
@pytest.mark.parametrize('profile', [
    {'roles': [], 'clubs': []}, {'roles': ['moderator'], 'clubs': []},
    {'roles': ['club-leader'], 'clubs': []}, {'roles': 'club-leader', 'clubs': []},
])
def test_create_requires_verified_organizer_and_owned_club(signed, upstream, generic, profile):
    state, requests = upstream
    state['profile'] = profile
    result = invoke(signed, 'events_create_draft', CREATE, generic)
    assert result.data['done'] is False
    assert [r.method for r in requests] == ['GET']


@pytest.mark.parametrize('generic', [False, True])
@pytest.mark.parametrize('problem', ['no_edit', 'wrong_id', 'malformed', '403', '503'])
def test_update_permission_failure_never_writes(signed, upstream, generic, problem):
    state, requests = upstream
    if problem == 'no_edit':
        state['draft']['can_edit'] = False
    elif problem == 'wrong_id':
        state['draft']['id'] = 'b' * 24
    elif problem == 'malformed':
        state['draft']['can_edit'] = 'true'
    else:
        state['hook'] = lambda r: httpx.Response(int(problem), json={'detail': 'unavailable'})
    result = invoke(signed, 'events_update_draft', {'draft_id': ID, 'description': 'New'}, generic)
    assert result.data['done'] is False
    assert [r.method for r in requests] == ['GET']


@pytest.mark.parametrize('generic', [False, True])
@pytest.mark.parametrize('changes', [
    {'name': ''}, {'name': ' '}, {'name': 'x' * 301}, {'description': 'x' * 12001},
    {'starts_at': '2099-01-01T18:00:00'}, {'starts_at': '2099-01-01 18:00:00+03:00'},
    {'starts_at': '2099-01-01T18:00:00+03:99'}, {'starts_at': '2099-02-30T18:00:00Z'},
    {'starts_at': True}, {'duration_hours': 0}, {'duration_hours': -1}, {'duration_hours': True},
    {'locale': '../en'}, {'locale': 'de'}, {'location': ' '},
    {'registration_url': 'javascript:alert(1)'}, {'registration_url': 'https://user:secret@example.test'},
    {'registration_url': 'https://@example.test'}, {'registration_url': 'https://'},
    {'registration_url': 'https://example.test/ bad'}, {'club_id': '../42'},
    {'token': 'invented'}, {'uid': 'other'}, {'url': 'https://evil.test'},
])
def test_invalid_create_inputs_refused_before_http(signed, upstream, generic, changes):
    _, requests = upstream
    result = invoke(signed, 'events_create_draft', {**CREATE, **changes}, generic)
    assert not result.is_error
    assert result.data['done'] is False and result.data['code'] == 'invalid_arguments'
    assert requests == []


@pytest.mark.parametrize('generic', [False, True])
@pytest.mark.parametrize('draft_id', ['../draft', 'A' * 24, 'a' * 23, 'a' * 24 + '?x', '%252e%252e'])
def test_invalid_draft_id_never_reaches_http(signed, upstream, generic, draft_id):
    _, requests = upstream
    result = invoke(signed, 'events_update_draft', {'draft_id': draft_id, 'name': 'New'}, generic)
    assert result.data['done'] is False and result.data['code'] == 'invalid_arguments'
    assert requests == []


@pytest.mark.parametrize('generic', [False, True])
@pytest.mark.parametrize('credential', [None, 'forged'])
@pytest.mark.parametrize('name,arguments', [
    ('events_create_draft', CREATE), ('events_update_draft', {'draft_id': ID, 'name': 'New'}),
    ('events_create_draft', {'name': ''}), ('events_update_draft', {'draft_id': '../bad'}),
])
def test_missing_or_forged_identity_blocks_valid_and_invalid_input(upstream, generic, credential, name, arguments):
    _, requests = upstream
    result = invoke(credential, name, arguments, generic)
    assert result.is_error
    assert requests == []


@pytest.mark.parametrize('stage,status', [('POST', 403), ('POST', 408), ('POST', 503), ('PUT', 403), ('PUT', 503)])
def test_create_refusal_vs_partial_unknown_never_retries(signed, upstream, stage, status):
    state, requests = upstream
    state['hook'] = lambda r: httpx.Response(status, json={'detail': 'private diagnostics'}) if r.method == stage else None
    result = invoke(signed, 'events_create_draft', CREATE)
    if stage == 'POST' and status == 403:
        assert result.data['done'] is False
    else:
        assert result.data['done'] is None and result.data['outcome'] == 'unknown'
        assert result.data['draft_id'] == (ID if stage == 'PUT' else None)
        assert 'Do not retry automatically' in result.data['error']
    assert 'private diagnostics' not in str(result.data)
    assert sum(r.method == stage for r in requests) == 1


def test_create_retains_known_id_when_post_response_is_incomplete(signed, upstream):
    state, requests = upstream
    state['hook'] = lambda r: httpx.Response(200, json={'id': ID}) if r.method == 'POST' else None
    result = invoke(signed, 'events_create_draft', CREATE)
    assert result.data['done'] is None and result.data['draft_id'] == ID
    assert [r.method for r in requests] == ['GET', 'POST']


@pytest.mark.parametrize('changes', [
    {'id': 'b' * 24}, {'data': {}},
    {'data': {'locales': {'en': {'name': 'Wrong', 'description': 'Wrong'}}}},
])
def test_create_readback_mismatch_is_unknown(signed, upstream, changes):
    state, requests = upstream
    state['hook'] = lambda r: httpx.Response(200, json={**state['draft'], **changes}) if r.method == 'GET' and '/drafts/' in r.url.path else None
    result = invoke(signed, 'events_create_draft', CREATE)
    assert result.data['done'] is None and result.data['draft_id'] == ID
    assert requests[-1].method == 'GET'


def test_update_empty_change_is_refused_and_empty_description_clears(signed, upstream):
    state, requests = upstream
    result = invoke(signed, 'events_update_draft', {'draft_id': ID})
    assert result.data['done'] is False and requests == []
    state['draft']['data']['locales']['ru'] = {'name': 'Keep', 'description': 'Remove'}
    result = invoke(signed, 'events_update_draft', {'draft_id': ID, 'description': ''})
    assert result.data['done'] is True
    assert state['draft']['data']['locales']['ru'] == {'name': 'Keep', 'description': None}


@pytest.mark.parametrize('stage,status', [('PATCH', 403), ('PATCH', 503), ('PUT', 403), ('PUT', 503)])
def test_update_failure_after_first_write_is_not_a_definite_refusal(signed, upstream, stage, status):
    state, requests = upstream
    state['hook'] = lambda r: httpx.Response(status, json={'detail': 'private'}) if r.method == stage else None
    result = invoke(signed, 'events_update_draft', {'draft_id': ID, 'name': 'New', 'location': '301'})
    assert result.data['done'] is (False if stage == 'PATCH' and status == 403 else None)
    if result.data['done'] is None:
        assert result.data['draft_id'] == ID
    assert sum(r.method == stage for r in requests) == 1


def test_update_adds_owned_host_once_without_removing_existing_hosts(signed, upstream):
    state, requests = upstream
    state['draft']['data']['hosts'] = [{'id': 'other', 'type': 'external', 'name': 'Other'}]
    for _ in range(2):
        result = invoke(signed, 'events_update_draft', {'draft_id': ID, 'club_id': '42'})
        assert result.data['done'] is True
    assert sum(r.method == 'POST' for r in requests) == 1
    assert len(state['draft']['data']['hosts']) == 2


def test_description_is_site_compatible_tiptap_with_literal_text(signed, upstream):
    _, requests = upstream
    text = '<script>not HTML</script>\n\nSecond paragraph'
    result = invoke(signed, 'events_create_draft', {'name': 'Draft', 'description': text})
    assert result.data['done'] is True
    payload = json.loads(next(r.content for r in requests if r.method == 'PUT'))
    assert json.loads(payload['description']) == {'type': 'doc', 'content': [
        {'type': 'paragraph', 'content': [{'type': 'text', 'text': '<script>not HTML</script>'}]},
        {'type': 'paragraph'},
        {'type': 'paragraph', 'content': [{'type': 'text', 'text': 'Second paragraph'}]},
    ]}


@pytest.mark.parametrize('query,target', [
    ('создать черновик мероприятия клуба', 'events_create_draft'),
    ('подготовь мероприятие клуба название описание время место ссылка регистрации', 'events_create_draft'),
    ('изменить черновик мероприятия', 'events_update_draft'),
    ('create event draft', 'events_create_draft'),
    ('events_update_draft', 'events_update_draft'),
])
def test_five_draft_discovery_requests_are_anonymous_and_include_schema(upstream, query, target):
    _, requests = upstream
    async def run():
        async with connection(True) as client:
            matches = (await client.call_tool('search_tools', {'query': query})).data
            match = next(item for item in matches if item['name'] == target)
            props = match['inputSchema']['properties']
            assert {'name', 'description', 'locale', 'starts_at', 'location', 'registration_url', 'club_id'} <= props.keys()
            assert not {'token', 'uid', 'user_id'} & props.keys()
    asyncio.run(run())
    assert requests == []


@pytest.mark.parametrize('field,value', [
    ('starts_at', '2099-01-01T19:00:00+03:00'), ('location', {'display_name': 'Wrong', 'url': ''}),
    ('duration_hours', 1), ('enrollment', {'type': 'internal', 'url': None, 'capacity': None}),
    ('locales', {'en': {'name': 'Wrong', 'description': None}}), ('hosts', []),
])
def test_valid_readback_must_match_every_requested_value(signed, upstream, field, value):
    state, _ = upstream
    def hook(request):
        if request.method == 'GET' and '/drafts/' in request.url.path:
            changed = copy.deepcopy(state['draft'])
            changed['data'][field] = value
            return httpx.Response(200, json=changed)
    state['hook'] = hook
    result = invoke(signed, 'events_create_draft', CREATE)
    assert result.data['done'] is None and result.data['draft_id'] == ID


@pytest.mark.parametrize('method', ['POST', 'PUT', 'GET'])
def test_transport_failure_never_retries_or_claims_nothing_changed(signed, upstream, method):
    state, requests = upstream
    def hook(request):
        if request.method == method and '/drafts/' in request.url.path:
            raise httpx.ReadTimeout('private diagnostic', request=request)
    state['hook'] = hook
    result = invoke(signed, 'events_create_draft', CREATE)
    assert result.data['done'] is None and result.data['outcome'] == 'unknown'
    assert result.data['draft_id'] == (None if method == 'POST' else ID)
    assert 'private diagnostic' not in str(result.data)
    assert sum(r.method == method and '/drafts/' in r.url.path for r in requests) == 1


def test_aware_fractional_time_and_registration_url_are_preserved(signed, upstream):
    _, requests = upstream
    start = '2099-01-01T18:00:00.123456+05:30'
    url = 'https://example.test/register?club=42&source=catix#form'
    result = invoke(signed, 'events_create_draft', {**CREATE, 'starts_at': start, 'registration_url': url})
    assert result.data['done'] is True
    assert json.loads(requests[1].content)['starts_at'] == start
    assert json.loads(requests[1].content)['enrollment']['url'] == url


def test_name_only_update_preserves_existing_rich_description_verbatim(signed, upstream):
    state, requests = upstream
    rich = '{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"Bold","marks":[{"type":"bold"}]}]}]}'
    state['draft']['data']['locales']['en'] = {'name': 'Old', 'description': rich}
    result = invoke(signed, 'events_update_draft', {'draft_id': ID, 'locale': 'en', 'name': 'New'})
    assert result.data['done'] is True
    assert json.loads(next(r.content for r in requests if r.method == 'PUT'))['description'] == rich
