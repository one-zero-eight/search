"""When2Meet through real direct/generic MCP, signed auth and mocked HTTP only."""
import asyncio
import json
from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from catix.innohassle import client as backend
from catix.innohassle import token
from tests.mcp_native_helpers import connection

REF = 'Abcd_12-'
ID = 'a' * 24
SLOTS = ['2099-01-01T10:00:00+03:00', '2099-01-01T10:30:00+03:00']


def meeting(**changes):
    return {'id': ID, 'slug': REF, 'name': 'Study', 'description': None,
            'slots': SLOTS.copy(), 'timezone': 'Europe/Moscow', 'specific_time': True,
            'participants': [], 'created_at': '2098-12-01T10:00:00Z',
            'archive_after': '2099-01-01T11:00:00+03:00', 'is_archived': False,
            **changes}


@pytest.fixture
def signed(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(token._keys, 'get_signing_keys', lambda: [key.public_key()])
    return jwt.encode({'uid': 'signed-owner', 'exp': datetime.now(UTC) + timedelta(hours=1)},
                      key, algorithm='RS256')


async def invoke(client, generic, name, arguments):
    return await client.call_tool('call_tool' if generic else name,
        {'name': name, 'arguments': arguments} if generic else arguments, raise_on_error=False)


@pytest.fixture
def upstream(monkeypatch):
    requests = []
    state = {'reply': lambda request: httpx.Response(200, json=meeting())}
    def reply(request):
        requests.append(request)
        return state['reply'](request)
    with backend._http_client('https://synthetic.test', transport=httpx.MockTransport(reply)) as http:
        monkeypatch.setattr(backend, '_client', http)
        yield state, requests


@pytest.mark.parametrize('generic', [False, True], ids=['direct', 'generic'])
def test_get_meeting_projects_private_fields_and_actual_intersection(signed, upstream, generic):
    state, requests = upstream
    people = [{'user_id': 'signed-owner', 'name': 'Alice', 'email': 'private@example.test',
               'telegram': '@private', 'availability': SLOTS},
              {'user_id': 'other', 'name': 'Bob', 'availability': SLOTS[1:]}]
    state['reply'] = lambda request: httpx.Response(200, json=meeting(participants=people))
    async def run():
        async with connection(True, signed) as client:
            result = await invoke(client, generic, 'when2meet_get_meeting', {'meeting_ref': REF})
            assert not result.is_error
            data = result.data
            assert data['slots'] == SLOTS
            assert data['page'] == f'https://innohassle.ru/when2meet/{REF}'
            assert data['participants'][0] == {
                'user_id': 'signed-owner', 'name': 'Alice', 'availability': SLOTS,
                'availability_count': 2, 'availability_truncated': False, 'is_me': True}
            assert data['participants'][1]['is_me'] is False
            assert data['common_slots'] == SLOTS[1:]
            assert data['participants_count'] == 2
            assert 'private' not in str(data)
    asyncio.run(run())
    assert [(r.method, r.url.path) for r in requests] == [('GET', f'/when2meet/v0/meetings/{REF}')]
    assert requests[0].headers['authorization'] == f'Bearer {signed}'


@pytest.mark.parametrize('generic', [False, True])
@pytest.mark.parametrize('scope', ['all', 'owned', 'participating'])
def test_listing_merges_deduplicates_and_filters_without_detail_reads(signed, upstream, generic, scope):
    state, requests = upstream
    owned = [meeting(participants_count=0), meeting(id='b'*24, participants_count=3)]
    participating = [owned[1], meeting(id='c'*24, participants_count=1)]
    state['reply'] = lambda request: httpx.Response(200, json=(
        participating if request.url.path.endswith('/participating') else owned))
    async def run():
        async with connection(True, signed) as client:
            result = await invoke(client, generic, 'when2meet_get_my_meetings', {'status': 'archived', 'scope': scope})
            assert not result.is_error
            data = result.data
            assert data['status'] == 'archived' and data['scope'] == scope
            expected = [ID, 'b'*24, 'c'*24] if scope == 'all' else [row['id'] for row in (owned if scope == 'owned' else participating)]
            assert [row['id'] for row in data['meetings']] == expected
            assert all(row['page'] == f"https://innohassle.ru/when2meet/{row['slug']}" for row in data['meetings'])
            assert data['total'] == len(expected) and not data['truncated']
            assert all('slots' not in row and 'participants' not in row for row in data['meetings'])
    asyncio.run(run())
    expected_paths = ['/when2meet/v0/meetings/'] if scope == 'owned' else ['/when2meet/v0/meetings/participating']
    if scope == 'all':
        expected_paths = ['/when2meet/v0/meetings/', '/when2meet/v0/meetings/participating']
    assert [r.url.path for r in requests] == expected_paths
    assert all(r.method == 'GET' and dict(r.url.params) == {'status': 'archived'} for r in requests)


def test_detail_bounds_and_common_slots_include_hidden_participants(signed, upstream):
    state, _ = upstream
    slots = [(datetime(2099, 1, 1, tzinfo=UTC) + timedelta(minutes=30*i)).isoformat()
             for i in range(250)]
    people = [{'user_id': str(i), 'name': 'Person', 'availability': slots} for i in range(45)]
    people[-1]['availability'] = []
    state['reply'] = lambda request: httpx.Response(200, json=meeting(slots=slots, participants=people,
                                                                   description='x'*5000))
    async def run():
        async with connection(True, signed) as client:
            data = (await invoke(client, True, 'when2meet_get_meeting', {'meeting_ref': REF})).data
            assert len(data['slots']) == 200 and data['slots_count'] == 250 and data['slots_truncated']
            assert len(data['participants']) == 40 and data['participants_count'] == 45
            assert data['participants_truncated'] and data['truncated']
            assert data['common_slots'] == [] and data['common_slots_count'] == 0
            assert len(data['participants'][0]['availability']) == 200
            assert data['participants'][0]['availability_count'] == 250
            assert data['participants'][0]['availability_truncated']
            assert len(data['description']) == 2000 and data['description_truncated']
            people.clear()
            empty = (await invoke(client, True, 'when2meet_get_meeting', {'meeting_ref': REF})).data
            assert empty['participants'] == [] and empty['common_slots'] == []
    asyncio.run(run())


@pytest.mark.parametrize('generic', [False, True])
@pytest.mark.parametrize('options', [{}, {'timezone': 'Asia/Kolkata', 'specific_time': False, 'description': 'Choose a day'}])
def test_create_posts_exact_payload_then_reads_created_id(signed, upstream, generic, options):
    state, requests = upstream
    created = meeting(**options)
    def reply(request):
        if request.method == 'POST':
            assert request.url.path == '/when2meet/v0/meetings/'
            return httpx.Response(201, json=created)
        assert request.url.path == f'/when2meet/v0/meetings/{ID}'
        return httpx.Response(200, json=created)
    state['reply'] = reply
    async def run():
        async with connection(True, signed) as client:
            result = await invoke(client, generic, 'when2meet_create_meeting', {'name': 'Study', 'slots': SLOTS, **options})
            assert not result.is_error
            assert result.data['done'] is True
            assert result.data['meeting']['id'] == ID
            assert result.data['meeting']['slots'] == SLOTS
            assert result.data['meeting']['page'] == f'https://innohassle.ru/when2meet/{REF}'
    asyncio.run(run())
    assert [r.method for r in requests] == ['POST', 'GET']
    assert json.loads(requests[0].content) == {
        'name': 'Study', 'slots': SLOTS, 'timezone': 'Europe/Moscow', 'specific_time': True,
        'description': None, **options}
    assert all(r.headers['authorization'] == f'Bearer {signed}' for r in requests)


@pytest.mark.parametrize('generic', [False, True])
@pytest.mark.parametrize('changes', [
    {'name': ''}, {'name': '   '}, {'name': 'x'*201}, {'slots': []}, {'slots': SLOTS*1001},
    {'timezone': 'Not/AZone'}, {'timezone': ' Europe/Moscow '}, {'description': 'x'*2001},
    {'specific_time': 'true'}, {'specific_time': 1}, {'slots': [True]},
    {'slots': ['2099-01-01 10:00:00+03:00']}, {'slots': ['2099-01-01T10:00:00']},
    {'slots': ['2099-01-01T10:00:00+03:99']}, {'slots': ['2099-02-30T10:00:00Z']},
    {'uid': 'other'}, {'token': 'model-secret'}, {'url': 'https://elsewhere.test'},
])
def test_create_invalid_inputs_are_known_refusal_before_http(signed, upstream, generic, changes):
    _, requests = upstream
    async def run():
        async with connection(True, signed) as client:
            result = await invoke(client, generic, 'when2meet_create_meeting', {'name': 'Study', 'slots': SLOTS, **changes})
            assert not result.is_error
            assert result.data['done'] is False and result.data['code'] == 'invalid_arguments'
    asyncio.run(run())
    assert requests == []


@pytest.mark.parametrize('changes', [
    {'name': 'different'}, {'slots': SLOTS[:1]}, {'timezone': 'UTC'}, {'specific_time': False},
    {'description': 'different'}, {'id': 'b'*24}, {'slug': 'Other123'},
])
def test_create_readback_must_match_requested_fields_and_identity(signed, upstream, changes):
    state, requests = upstream
    state['reply'] = lambda request: httpx.Response(201 if request.method == 'POST' else 200,
        json=meeting() if request.method == 'POST' else meeting(**changes))
    async def run():
        async with connection(True, signed) as client:
            result = await invoke(client, True, 'when2meet_create_meeting', {'name': 'Study', 'slots': SLOTS})
            assert result.data['done'] is None and result.data['outcome'] == 'unknown'
            assert 'retry automatically' in result.data['error']
    asyncio.run(run())
    assert [r.method for r in requests] == ['POST', 'GET']


@pytest.mark.parametrize('generic', [False, True])
@pytest.mark.parametrize('availability', [SLOTS[1:], []])
def test_set_availability_reads_fresh_then_puts_and_verifies_signed_user(signed, upstream, generic, availability):
    state, requests = upstream
    current = meeting(participants=[{'user_id': 'other', 'name': 'Not me', 'availability': SLOTS},
                                    {'user_id': 'signed-owner', 'name': 'Me', 'availability': SLOTS}])
    def reply(request):
        if request.method == 'PUT':
            current['participants'][1]['availability'] = availability
            assert request.url.path == f'/when2meet/v0/meetings/{REF}/participants'
        else:
            assert request.url.path == f'/when2meet/v0/meetings/{REF}'
        return httpx.Response(200, json=current)
    state['reply'] = reply
    async def run():
        async with connection(True, signed) as client:
            result = await invoke(client, generic, 'when2meet_set_my_availability',
                                  {'meeting_ref': REF, 'availability': availability})
            assert not result.is_error
            assert result.data['done'] is True
            assert result.data['meeting']['id'] == ID
            assert result.data['meeting']['participants'][1]['availability'] == availability
    asyncio.run(run())
    assert [r.method for r in requests] == ['GET', 'PUT', 'GET']
    assert json.loads(requests[1].content) == {'availability': availability}


@pytest.mark.parametrize('generic', [False, True])
@pytest.mark.parametrize('problem', ['archived', 'outside_slots', 'check_404', 'check_503', 'check_invalid', 'wrong_target'])
def test_update_precheck_failure_is_known_without_put(signed, upstream, generic, problem):
    state, requests = upstream
    event = meeting(is_archived=problem == 'archived')
    if problem == 'check_invalid':
        event.pop('slots')
    if problem == 'wrong_target':
        event['slug'] = 'Other123'
    status = 404 if problem == 'check_404' else 503 if problem == 'check_503' else 200
    state['reply'] = lambda request: httpx.Response(status, json=event)
    async def run():
        async with connection(True, signed) as client:
            availability = ['2099-01-02T10:00:00+03:00'] if problem == 'outside_slots' else SLOTS
            result = await invoke(client, generic, 'when2meet_set_my_availability',
                                  {'meeting_ref': REF, 'availability': availability})
            assert not result.is_error
            assert result.data['done'] is False
            assert result.data['code'] == ('meeting_archived' if problem == 'archived' else
                'invalid_arguments' if problem == 'outside_slots' else 'meeting_unverified')
    asyncio.run(run())
    assert [r.method for r in requests] == ['GET']


@pytest.mark.parametrize('problem', ['wrong_user', 'missing_user', 'wrong_slots', 'wrong_id', 'missing_clear', 'hidden_slots'])
def test_update_requires_exact_authenticated_user_readback(signed, upstream, problem):
    state, requests = upstream
    availability = [] if problem in {'missing_clear', 'hidden_slots'} else SLOTS
    rows = [{'user_id': 'other' if problem == 'wrong_user' else 'signed-owner', 'availability': SLOTS}]
    if problem in {'missing_user', 'missing_clear'}:
        rows = []
    if problem == 'wrong_slots':
        rows[0]['availability'] = SLOTS[:1]
    if problem == 'hidden_slots':
        rows[0]['availability'] = ['2099-01-02T10:00:00+03:00']
    def reply(request):
        event = meeting() if len(requests) == 1 else meeting(participants=rows,
            id='b'*24 if problem == 'wrong_id' else ID)
        return httpx.Response(200, json=event)
    state['reply'] = reply
    async def run():
        async with connection(True, signed) as client:
            result = await invoke(client, True, 'when2meet_set_my_availability',
                                  {'meeting_ref': REF, 'availability': availability})
            assert result.data['done'] is None and result.data['outcome'] == 'unknown'
    asyncio.run(run())
    assert [r.method for r in requests] == ['GET', 'PUT', 'GET']


@pytest.mark.parametrize('operation', ['create', 'set'])
@pytest.mark.parametrize('failure', [400, 401, 403, 404, 409, 422, 429, 408, 500, 503,
                                   'timeout', 'redirect', 'malformed', 'readback_404', 'readback_timeout'])
def test_write_failures_distinguish_refusals_from_unknown_without_retry(signed, upstream, operation, failure, caplog):
    state, requests = upstream
    writes = []
    def reply(request):
        event = meeting(participants=[{'user_id': 'signed-owner', 'availability': SLOTS}])
        if request.method in {'POST', 'PUT'}:
            writes.append(request)
            if isinstance(failure, int):
                return httpx.Response(failure, json={'detail': 'private-upstream-diagnostic'})
            if failure == 'timeout':
                raise httpx.ReadTimeout('private-upstream-diagnostic')
            if failure == 'redirect':
                return httpx.Response(307, headers={'location': 'https://elsewhere.test'})
            if failure == 'malformed':
                return httpx.Response(200, text='not-json-private-upstream-diagnostic')
        elif writes:
            if failure == 'readback_404':
                return httpx.Response(404, json={'detail': 'private-upstream-diagnostic'})
            if failure == 'readback_timeout':
                raise httpx.ReadTimeout('private-upstream-diagnostic')
        return httpx.Response(201 if request.method == 'POST' else 200, json=event)
    state['reply'] = reply
    async def run():
        async with connection(True, signed) as client:
            name = 'when2meet_create_meeting' if operation == 'create' else 'when2meet_set_my_availability'
            arguments = {'name': 'Study', 'slots': SLOTS} if operation == 'create' else {'meeting_ref': REF, 'availability': SLOTS}
            result = await invoke(client, True, name, arguments)
            assert not result.is_error
            known = isinstance(failure, int) and failure < 500 and failure != 408
            assert result.data['done'] is (False if known else None)
            if not known:
                assert result.data['outcome'] == 'unknown'
                assert 'retry automatically' in result.data['error']
            assert 'private-upstream-diagnostic' not in str(result.data)
    asyncio.run(run())
    assert len(writes) == 1
    assert len(requests) == (1 if operation == 'create' else 2) + (1 if str(failure).startswith('readback_') else 0)
    assert 'private-upstream-diagnostic' not in caplog.text


def test_my_selection_remains_visible_when_participant_list_is_truncated(signed, upstream):
    state, _ = upstream
    people = [{'user_id': f'other-{i}', 'availability': SLOTS} for i in range(41)]
    people.append({'user_id': 'signed-owner', 'availability': SLOTS[1:]})
    state['reply'] = lambda request: httpx.Response(200, json=meeting(participants=people))
    async def run():
        async with connection(True, signed) as client:
            result = await invoke(client, True, 'when2meet_get_meeting', {'meeting_ref': REF})
            assert result.data['my_availability'] == SLOTS[1:]
            assert result.data['my_availability_count'] == 1
            assert result.data['my_availability_truncated'] is False
            assert result.data['my_participation'] is True
            people.pop()
            result = await invoke(client, True, 'when2meet_get_meeting', {'meeting_ref': REF})
            assert result.data['my_availability'] == [] and result.data['my_participation'] is False
    asyncio.run(run())


@pytest.mark.parametrize('bad', ['oversized', 'huge_uid', 'huge_timezone', 'object_id_mismatch'])
def test_detail_rejects_unbounded_or_wrong_target_response(signed, upstream, bad):
    state, _ = upstream
    event = meeting()
    if bad == 'oversized':
        event['unexpected'] = 'x'*2_000_001
    elif bad == 'huge_uid':
        event['participants'] = [{'user_id': 'x'*10000, 'availability': []}]
    elif bad == 'huge_timezone':
        event['timezone'] = 'x'*10000
    else:
        event.update(id='b'*24, slug=ID)
    state['reply'] = lambda request: httpx.Response(200, json=event)
    async def run():
        async with connection(True, signed) as client:
            result = await invoke(client, True, 'when2meet_get_meeting',
                                  {'meeting_ref': ID if bad == 'object_id_mismatch' else REF})
            assert result.is_error
    asyncio.run(run())


@pytest.mark.parametrize('operation', ['create', 'set'])
def test_oversized_write_reply_is_unknown_not_confirmed(signed, upstream, operation):
    state, requests = upstream
    def reply(request):
        event = meeting(participants=[{'user_id': 'signed-owner', 'availability': SLOTS}])
        if request.method in {'POST', 'PUT'}:
            event['unexpected'] = 'x'*2_000_001
        return httpx.Response(201 if request.method == 'POST' else 200, json=event)
    state['reply'] = reply
    async def run():
        async with connection(True, signed) as client:
            name = 'when2meet_create_meeting' if operation == 'create' else 'when2meet_set_my_availability'
            args = {'name': 'Study', 'slots': SLOTS} if operation == 'create' else {'meeting_ref': REF, 'availability': SLOTS}
            result = await invoke(client, True, name, args)
            assert result.data['done'] is None and result.data['outcome'] == 'unknown'
    asyncio.run(run())
    assert sum(r.method in {'POST', 'PUT'} for r in requests) == 1


def test_detail_keeps_selected_time_and_archival_metadata(signed, upstream):
    state, _ = upstream
    selected = {'start': SLOTS[0], 'end': SLOTS[1]}
    state['reply'] = lambda request: httpx.Response(200, json=meeting(
        selected_time=selected, archived_at=SLOTS[1], is_archived=True,
        time_range={'start': '10:00', 'end': '18:00'}, owner_id='signed-owner'))
    async def run():
        async with connection(True, signed) as client:
            result = await invoke(client, True, 'when2meet_get_meeting', {'meeting_ref': REF})
            assert result.data['selected_time'] == selected
            assert result.data['archived_at'] == SLOTS[1]
            assert result.data['time_range'] == {'start': '10:00', 'end': '18:00'}
            assert result.data['owner_id'] == 'signed-owner'
    asyncio.run(run())


@pytest.mark.parametrize('generic', [False, True])
def test_all_four_tools_require_real_verified_identity_even_for_invalid_inputs(signed, upstream, generic):
    state, requests = upstream
    forged = jwt.encode({'uid': 'signed-owner', 'exp': datetime.now(UTC) + timedelta(hours=1)},
        rsa.generate_private_key(public_exponent=65537, key_size=2048), algorithm='RS256')
    calls = [('when2meet_get_my_meetings', {}), ('when2meet_get_meeting', {'meeting_ref': REF}),
             ('when2meet_create_meeting', {'name': 'Study', 'slots': SLOTS}),
             ('when2meet_set_my_availability', {'meeting_ref': REF, 'availability': SLOTS})]
    def reply(request):
        event = meeting(participants_count=1, participants=[{'user_id': 'signed-owner', 'availability': SLOTS}])
        listed = request.method == 'GET' and request.url.path.endswith(('/', '/participating'))
        return httpx.Response(201 if request.method == 'POST' else 200, json=[event] if listed else event)
    state['reply'] = reply
    async def run():
        for credential in (None, forged):
            async with connection(True, credential) as client:
                for name, args in calls:
                    for arguments in (args, {**args, 'uid': 'model-user'}):
                        result = await invoke(client, generic, name, arguments)
                        assert result.is_error
                        assert requests == []
        async with connection(True, signed) as client:
            for name, args in calls:
                result = await invoke(client, generic, name, args)
                assert not result.is_error
                if 'done' in result.data:
                    assert result.data['done'] is True
    asyncio.run(run())
    assert sum(request.method in {'PUT', 'POST'} for request in requests) == 2
    assert all(request.headers['authorization'] == f'Bearer {signed}' for request in requests)


@pytest.mark.parametrize('generic', [False, True])
def test_literal_references_and_strict_update_inputs_reject_without_io(signed, upstream, generic):
    state, requests = upstream
    state['reply'] = lambda request: httpx.Response(200, json=meeting(
        participants=[{'user_id': 'signed-owner', 'availability': SLOTS}]))
    invalid_refs = ['', ' ', ' '+REF, REF+' ', '../'+REF, REF+'/child', REF+'?a=b', REF+'#anchor',
                    '%2f'+REF, '%252f'+REF, REF+'\\child', REF+'\n', 'https://host.test/'+REF, 'x'*129, False, 42]
    invalid_availability = [None, False, '2099-01-01', [1], [False], ['2099-01-01T10:00:00'],
                            ['2099-01-01 10:00:00+03:00'], ['2099-01-01T10:00:00+03:60'], SLOTS*1001]
    async def run():
        async with connection(True, signed) as client:
            for reference in invalid_refs:
                result = await invoke(client, generic, 'when2meet_get_meeting', {'meeting_ref': reference})
                assert result.is_error
                result = await invoke(client, generic, 'when2meet_set_my_availability',
                                      {'meeting_ref': reference, 'availability': SLOTS})
                assert result.data['done'] is False
            for values in invalid_availability:
                result = await invoke(client, generic, 'when2meet_set_my_availability',
                                      {'meeting_ref': REF, 'availability': values})
                assert result.data['done'] is False
            for name in ('when2meet_create_meeting', 'when2meet_set_my_availability'):
                result = await invoke(client, generic, name, {})
                assert result.data['done'] is False and result.data['code'] == 'invalid_arguments'
            assert requests == []
            result = await invoke(client, generic, 'when2meet_set_my_availability',
                                  {'meeting_ref': REF, 'availability': SLOTS})
            assert result.data['done'] is True
    asyncio.run(run())
    assert [r.method for r in requests] == ['GET', 'PUT', 'GET']


def test_listing_defaults_bounds_empty_and_failure_never_fabricates_empty(signed, upstream):
    state, requests = upstream
    rows = [meeting(id=f'{i:024x}', participants_count=0) for i in range(45)]
    state['reply'] = lambda request: httpx.Response(200, json=rows)
    async def run():
        async with connection(True, signed) as client:
            result = await invoke(client, True, 'when2meet_get_my_meetings', {})
            assert result.data['total'] == 45 and len(result.data['meetings']) == 40 and result.data['truncated']
            assert result.data['scope'] == 'all' and result.data['status'] == 'active'
            rows.clear()
            result = await invoke(client, True, 'when2meet_get_my_meetings', {})
            assert result.data['total'] == 0 and result.data['meetings'] == [] and not result.data['truncated']
            state['reply'] = lambda request: httpx.Response(503, json={'detail': 'private-failure'})
            result = await invoke(client, True, 'when2meet_get_my_meetings', {})
            assert result.is_error and 'private-failure' not in str(result)
            before = len(requests)
            for args in ({'scope': 'everyone'}, {'status': 'all'}, {'scope': False}):
                result = await invoke(client, True, 'when2meet_get_my_meetings', args)
                assert result.is_error and len(requests) == before
    asyncio.run(run())
    assert all(dict(request.url.params) == {'status': 'active'} for request in requests)


@pytest.mark.parametrize('generic', [False, True])
@pytest.mark.parametrize('operation', ['create', 'set'])
def test_fractional_nonhour_offsets_preserved_and_readback_instant_equivalence(signed, upstream, generic, operation):
    state, requests = upstream
    slot = '2099-01-01T10:12:34.123456+05:45'
    utc = datetime.fromisoformat(slot).astimezone(UTC).isoformat()
    event = meeting(slots=[utc], participants=[{'user_id': 'signed-owner', 'availability': [utc]}])
    state['reply'] = lambda request: httpx.Response(201 if request.method == 'POST' else 200, json=event)
    async def run():
        async with connection(True, signed) as client:
            name = 'when2meet_create_meeting' if operation == 'create' else 'when2meet_set_my_availability'
            args = {'name': 'Study', 'slots': [slot]} if operation == 'create' else {'meeting_ref': REF, 'availability': [slot]}
            result = await invoke(client, generic, name, args)
            assert result.data['done'] is True
    asyncio.run(run())
    body = json.loads(next(request.content for request in requests if request.method in {'POST', 'PUT'}))
    assert body['slots' if operation == 'create' else 'availability'] == [slot]


def test_native_meeting_read_reaches_personal_recommendation_as_actual_instants(signed, upstream, monkeypatch):
    from types import SimpleNamespace
    from pydantic import SecretStr
    from catix.agent import meeting_tools
    from catix.agent.schedule_tools import merge_schedule
    from catix.agent.tools import AgentContext
    from catix.innohassle import mcp_client

    state, requests = upstream
    state['reply'] = lambda request: httpx.Response(200, json=meeting(
        slots=['2099-01-01T07:00:00Z', '2099-01-01T07:30:00Z'],
        participants=[{'user_id': 'other', 'availability': SLOTS}],
    ))
    monkeypatch.setattr(mcp_client, '_connection', lambda token: connection(True, token))
    def agenda(runtime, first, last):
        assert first.isoformat() == last.isoformat() == '2099-01-01'
        period = [first.isoformat(), last.isoformat()]
        return merge_schedule(period, {'range': period, 'schedule': [
            {'title': 'Class', 'starts_at': '2099-01-01T10:15:00+03:00', 'ends_at': '2099-01-01T10:30:00+03:00'}],
            'bookings': []}, {'range': period, 'events': [], 'truncated': False})
    monkeypatch.setattr(meeting_tools, 'read_my_schedule', agenda)
    context = AgentContext(innohassle_id='signed-owner', innohassle_token=SecretStr(signed),
                           asked_at=datetime.fromisoformat('2098-12-31T12:00:00+03:00'))
    from langchain_core.tools import StructuredTool
    assert isinstance(meeting_tools.get_my_available_meeting_slots, StructuredTool)
    assert meeting_tools.get_my_available_meeting_slots.func is not None
    result = meeting_tools.get_my_available_meeting_slots.func(SimpleNamespace(context=context), REF)
    assert result['complete'] is True
    assert result['available'] == result['common_available'] == [
        {'starts_at': SLOTS[1], 'ends_at': '2099-01-01T11:00:00+03:00'}]
    assert result['excluded'][0]['conflicts'][0]['title'] == 'Class'
    assert [(request.method, request.url.path) for request in requests] == [('GET', f'/when2meet/v0/meetings/{REF}')]


def test_registered_schema_has_exact_tools_defaults_formats_and_no_identity_controls():
    from tests.mcp_native_helpers import registered_tools

    registered = {name: item for name, item in registered_tools().items()
                  if item is not None and name.startswith('when2meet_')}
    assert set(registered) == {'when2meet_get_my_meetings', 'when2meet_get_meeting',
                              'when2meet_create_meeting', 'when2meet_set_my_availability'}
    for name, item in registered.items():
        schema = item.parameters
        assert schema['additionalProperties'] is False
        assert not {'uid', 'token', 'headers', 'url'} & schema['properties'].keys()
        assert item.annotations is not None
        assert item.annotations.read_only_hint is ('_get_' in name)
        assert item.annotations.destructive_hint is ('_get_' not in name)
    schema = registered['when2meet_create_meeting'].parameters
    assert set(schema['required']) == {'name', 'slots'}
    assert schema['properties']['slots']['items']['format'] == 'date-time'
    assert schema['properties']['timezone']['default'] == 'Europe/Moscow'
    assert schema['properties']['specific_time']['default'] is True
    assert schema['properties']['description']['default'] is None
    update = registered['when2meet_set_my_availability'].parameters
    assert set(update['required']) == {'meeting_ref', 'availability'}
    assert update['properties']['availability']['items']['format'] == 'date-time'
    assert update['properties']['availability'].get('minItems', 0) == 0


def test_list_truncation_counts_meetings_and_labels_text_separately(signed, upstream):
    state, _ = upstream
    state['reply'] = lambda request: httpx.Response(200, json=[meeting(participants_count=0, description='x'*5000)])
    async def run():
        async with connection(True, signed) as client:
            result = await invoke(client, True, 'when2meet_get_my_meetings', {'scope': 'owned'})
            assert result.data['total'] == 1 and result.data['truncated'] is False
            assert result.data['meetings'][0]['description_truncated'] is True
            assert len(result.data['meetings'][0]['description']) == 2000
    asyncio.run(run())


@pytest.mark.parametrize('operation', ['create', 'set'])
def test_submicrosecond_input_is_not_silently_truncated_into_success(signed, upstream, operation):
    state, requests = upstream
    slot = '2099-01-01T10:00:00.0000001+03:00'
    state['reply'] = lambda request: httpx.Response(201 if request.method == 'POST' else 200, json=meeting(
        slots=SLOTS[:1], participants=[{'user_id': 'signed-owner', 'availability': SLOTS[:1]}]))
    async def run():
        async with connection(True, signed) as client:
            name = 'when2meet_create_meeting' if operation == 'create' else 'when2meet_set_my_availability'
            args = {'name': 'Study', 'slots': [slot]} if operation == 'create' else {'meeting_ref': REF, 'availability': [slot]}
            result = await invoke(client, True, name, args)
            assert result.data['done'] is False and result.data['code'] == 'invalid_arguments'
    asyncio.run(run())
    assert requests == []
