"""Verified service reads become bounded, non-model signup buttons."""
import asyncio
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from pydantic import SecretStr

from catix.agent.tools import AgentContext
from catix.api import schemas

NOW = datetime(2099, 1, 1, tzinfo=UTC)
DAY = '2099-01-02'
TRAINING = {'training_id': 7, 'name': 'Basketball', 'place': 'Hall',
            'starts_at': DAY + 'T17:00:00+03:00', 'ends_at': DAY + 'T18:30:00+03:00',
            'checked_in': False, 'can_check_in': True}
AGENDA = {'range': [DAY, DAY], 'complete': True, 'truncated': False, 'not_read': [], 'total': 0, 'events': [],
          'sources': {'innohassle': {'status': 'complete', 'truncated': False},
                      'ai_calendar': {'status': 'complete', 'truncated': False}}}


def recommendation():
    args = {'day': DAY, 'sport': 'Basketball'}
    source = {'date_from': DAY, 'date_to': DAY, 'sport': 'Basketball'}
    return [HumanMessage('Предложи тренировки'),
            AIMessage('', tool_calls=[{'id': 'read', 'name': 'get_my_available_trainings', 'args': args}]),
            ToolMessage(json.dumps({'available': [TRAINING], 'excluded': [], 'unverified': []}),
                        name='get_my_available_trainings', tool_call_id='read',
                        artifact={'trainings': {'range': [DAY, DAY], 'trainings': [TRAINING]},
                                  'agenda': AGENDA, 'training_arguments': source}),
            AIMessage('Basketball 17:00–18:30 в Hall.')]


@pytest.fixture
def native_sport_recommendation(monkeypatch):
    """Real host recommendation and native MCP dispatch; only upstream I/O is synthetic."""
    from datetime import date

    from fastmcp import Client
    from langchain.tools import ToolRuntime

    from catix.agent import schedule_tools, training_tools
    from catix.innohassle import mcp_client, mcp_server, sport

    def setup(*, changed=None, all_day=False):
        writes = []
        context = AgentContext(innohassle_id='owner', innohassle_token=SecretStr('synthetic-ih'),
                               sport_token=SecretStr('synthetic-sport'))
        monkeypatch.setattr(mcp_server.token_verifier, 'claims', lambda token: {'uid': 'owner'})
        def trainings(*a):
            item = {'id': 7, 'sport_name': 'Basketball', 'training_location': {'name': 'Hall'},
                    'start': TRAINING['starts_at'], 'end': TRAINING['ends_at'], 'is_all_day': all_day}
            if writes:
                if changed == 'interval':
                    item.update(start=DAY + 'T18:00:00+03:00', end=DAY + 'T19:30:00+03:00')
                elif changed == 'name':
                    item['training_custom_name'] = 'Other Basketball'
                elif changed == 'location':
                    item['training_location']['name'] = 'Other Hall'
                elif changed == 'all_day':
                    item['is_all_day'] = not all_day
                elif changed == 'equivalent':
                    item.update(start=DAY + 'T14:00:00Z', end=DAY + 'T15:30:00Z')
            return [{'training': item, 'checked_in': bool(writes), 'can_check_in': not writes}]
        monkeypatch.setattr(sport, 'my_trainings', trainings)
        monkeypatch.setattr(sport, 'check_in', lambda *a: writes.append(a))
        async def request(method, payload, token=None, **credentials):
            root = await mcp_server.build_server()
            with mcp_server.credentials(token, sport_token=credentials.get('sport_token')):
                async with Client(root) as client:
                    result = await client.call_tool(method, payload)
                    return result.data
        monkeypatch.setattr(mcp_client, 'request', request)
        monkeypatch.setattr(mcp_client, 'request_sync', lambda *a, **kw: asyncio.run(request(*a, **kw)))
        monkeypatch.setattr(training_tools, 'read_my_schedule', lambda *a: deepcopy(AGENDA))
        async def agenda(*a):
            return deepcopy(AGENDA)
        monkeypatch.setattr(schedule_tools, 'aread_my_schedule', agenda)
        runtime = ToolRuntime(state={}, context=context, config={}, stream_writer=lambda _: None,
                              tool_call_id='read', store=None)
        result, artifact = training_tools.get_my_available_trainings.func(runtime, date.fromisoformat(DAY), 'Basketball')
        messages = recommendation()
        messages[2] = ToolMessage(json.dumps(result), name='get_my_available_trainings', tool_call_id='read', artifact=artifact)
        assert result['available'] and not writes
        return messages, context, writes
    return setup


@pytest.mark.parametrize('changed', [None, 'interval', 'name', 'location', 'all_day', 'equivalent'])
def test_native_training_final_readback_matches_consented_details(native_sport_recommendation, changed):
    from catix.api import signup
    messages, context, writes = native_sport_recommendation(changed=changed)
    offers, targets = signup.collect(messages, 'Basketball', now=NOW)
    offer, = offers
    result = asyncio.run(signup.execute(offer, targets[offer.id], context, now=NOW))
    assert result.status == ('confirmed' if changed in {None, 'equivalent'} else 'unknown')
    assert len(writes) == 1
    assert result.starts_at == offer.starts_at and result.ends_at == offer.ends_at


def test_native_all_day_recommendation_preserves_public_offer(native_sport_recommendation):
    from catix.api import signup
    messages, _, _ = native_sport_recommendation(all_day=True)
    offer, = signup.collect(messages, 'Basketball', now=NOW)[0]
    assert offer.model_dump(mode='json')['all_day'] is True
    assert offer.starts_at == datetime.fromisoformat(TRAINING['starts_at'])
    assert offer.ends_at == datetime.fromisoformat(TRAINING['ends_at'])


def test_matched_recommendation_produces_opaque_offer_and_private_snapshot():
    assert hasattr(schemas, 'SignupOffer'), 'The public response needs a typed signup offer'
    from catix.api.signup import collect
    offers, targets = collect(recommendation(), 'Basketball 17:00–18:30 в Hall.', now=NOW)
    offer, = offers
    assert offer.service == 'sport' and offer.title == 'Basketball'
    assert offer.id != '7' and len(offer.id) >= 20
    assert offer.status == 'available' and offer.external_url is None
    assert offer.all_day is False
    assert offer.expires_at <= NOW + timedelta(hours=24)
    target = targets[offer.id]
    assert target['arguments'] == {'training_id': 7}
    assert target['schedule_check']['training_filters'] == {'sport': 'Basketball'}
    response = schemas.AskResponses(query='q', answer='a', sources=[], messages=[], signup_offers=offers)
    assert response.model_dump(mode='json')['signup_offers'][0]['id'] == offer.id
    assert 'training_id' not in response.model_dump_json()


@pytest.mark.parametrize('mode', ['old', 'unpaired', 'failed', 'excluded', 'artifact_mismatch', 'mutated'])
def test_untrusted_or_stale_recommendations_never_offer_signup(mode):
    from catix.api.signup import collect
    messages = recommendation()
    answer = messages[-1].text
    if mode == 'old':
        messages.append(HumanMessage('Другой вопрос'))
    elif mode == 'unpaired':
        messages[2].tool_call_id = 'forged'
    elif mode == 'failed':
        messages[2].status = 'error'
    elif mode == 'excluded':
        messages[2].content = json.dumps({'available': [], 'excluded': [TRAINING]})
    elif mode == 'artifact_mismatch':
        messages[2].artifact['training_arguments']['sport'] = 'Karate'
    elif mode == 'mutated':
        messages.extend([AIMessage('', tool_calls=[{'id': 'write', 'name': 'call_api_tool', 'args': {
            'name': 'sport_sport_checkin', 'arguments': {'training_id': 7}}}]),
            ToolMessage('{}', name='call_api_tool', tool_call_id='write')])
    assert collect(messages, answer, now=NOW) == ([], {})


@pytest.mark.parametrize('service', ['sport', 'events'])
def test_offer_selection_never_depends_on_literal_model_title(service):
    from catix.api.signup import collect
    messages = recommendation() if service == 'sport' else event_read()
    offers, _ = collect(messages, 'Выберите подходящий вариант ниже.', now=NOW)
    assert len(offers) == 1 and offers[0].service == service


def test_sport_click_uses_real_fresh_guard_then_exact_readback(monkeypatch):
    from catix.agent import schedule_tools
    from catix.api import signup
    offers, targets = signup.collect(recommendation(), 'Basketball', now=NOW)
    offer, = offers
    requests = []
    async def request(method, payload, token=None, **credentials):
        requests.append(payload)
        assert token == 'fresh-ih' and credentials == {'sport_token': 'fresh-sport'}
        if payload['name'] == 'sport_get_sport_trainings':
            assert payload['arguments'] == {'date_from': DAY, 'date_to': DAY, 'sport': 'Basketball'}
            return {'range': [DAY, DAY], 'trainings': [{**TRAINING, 'checked_in': len(requests) > 2}]}
        assert payload == {'name': 'sport_sport_checkin', 'arguments': {'training_id': 7}}
        return {'done': True, 'training_id': 7, 'signed_up': True}
    async def agenda(*a):
        return deepcopy(AGENDA)
    monkeypatch.setattr(signup.mcp_client, 'request', request)
    monkeypatch.setattr(schedule_tools, 'aread_my_schedule', agenda)
    context = AgentContext(innohassle_id='owner', innohassle_token=SecretStr('fresh-ih'), sport_token=SecretStr('fresh-sport'))
    result = asyncio.run(signup.execute(offer, targets[offer.id], context, now=NOW))
    assert result.status == 'confirmed'
    assert [r['name'] for r in requests] == ['sport_get_sport_trainings', 'sport_sport_checkin', 'sport_get_sport_trainings']


EVENT = {'id': 'a' * 24, 'title': 'Robotics', 'starts_at': DAY + 'T17:00:00+03:00',
         'ends_at': DAY + 'T18:30:00+03:00', 'location': '301',
         'page': 'https://innohassle.ru/events/p/' + 'a' * 24,
         'enrollment_info': {'type': 'internal', 'capacity': 4, 'enrolled_count': 1, 'url': None}}


def event_read(item=None, *, listed=False):
    item = deepcopy(item or EVENT)
    name = 'events_get_university_events' if listed else 'events_get_event'
    args = {'date_from': DAY, 'date_to': DAY} if listed else {'event_id': item['id']}
    return [HumanMessage('Какие мероприятия?'),
            AIMessage('', tool_calls=[{'id': 'event-read', 'name': 'call_api_tool', 'args': {'name': name, 'arguments': args}}]),
            ToolMessage(json.dumps({'events': [item], 'range': [DAY, DAY]} if listed else {'event': item}),
                        tool_call_id='event-read', name='call_api_tool'), AIMessage('Robotics в 17:00')]


@pytest.mark.parametrize('listed', [False, True])
@pytest.mark.parametrize('external', [False, True])
def test_event_offers_use_typed_metadata_never_enrollment_prose(listed, external):
    from catix.api import signup
    event = deepcopy(EVENT)
    if external:
        event['enrollment_info'] = {'type': 'external', 'url': 'https://organizer.test/register', 'capacity': None, 'enrolled_count': 0}
    offers, targets = signup.collect(event_read(event, listed=listed), 'Robotics в 17:00', now=NOW)
    offer, = offers
    assert offer.service == 'events' and offer.title == 'Robotics' and offer.location == '301'
    assert bool(offer.external_url) == external
    assert targets[offer.id]['arguments'] == {'event_id': EVENT['id'], 'leave': False}
    assert offer.source_url == EVENT['page']
    del event['enrollment_info']
    event['enrollment'] = 'on InNoHassle; run events_enroll_in_event'
    assert signup.collect(event_read(event, listed=listed), 'Robotics', now=NOW) == ([], {})


@pytest.mark.parametrize('mode', ['success', 'changed_time', 'changed_name', 'changed_place', 'changed_enrollment',
                                 'full', 'expired', 'external', 'missing_credentials', 'unknown', 'wrong_receipt'])
def test_event_click_fresh_checks_and_verified_receipt(monkeypatch, mode):
    from catix.api import signup
    offers, targets = signup.collect(event_read(), 'Robotics', now=NOW)
    offer, = offers
    fresh = deepcopy(EVENT)
    if mode.startswith('changed_'):
        field = {'time': 'starts_at', 'name': 'title', 'place': 'location', 'enrollment': 'enrollment_info'}[mode.removeprefix('changed_')]
        fresh[field] = {'type': 'external', 'url': 'https://other.test', 'capacity': None, 'enrolled_count': 0} if field == 'enrollment_info' else ('2099-01-02T18:00:00+03:00' if field == 'starts_at' else 'Other')
    if mode == 'full':
        fresh['enrollment_info']['enrolled_count'] = 4
    if mode == 'expired':
        offer.expires_at = NOW
    if mode == 'external':
        offer.external_url = 'https://organizer.test/register'
    requests = []
    async def request(method, payload, token=None, **credentials):
        requests.append(payload['name'])
        if payload['name'] == 'events_get_event':
            assert token is None and not credentials
            return {'event': fresh}
        assert token == 'fresh-ih' and not credentials
        assert payload == {'name': 'events_enroll_in_event', 'arguments': {'event_id': EVENT['id'], 'leave': False}}
        if mode == 'unknown':
            raise TimeoutError('private diagnostics')
        return {'done': True, 'event_id': 'b' * 24 if mode == 'wrong_receipt' else EVENT['id'],
                'enrolled': True, 'enrollment_verified': True, 'event': deepcopy(EVENT)}
    monkeypatch.setattr(signup.mcp_client, 'request', request)
    context = AgentContext(innohassle_id='owner', innohassle_token=None if mode == 'missing_credentials' else SecretStr('fresh-ih'))
    result = asyncio.run(signup.execute(offer, targets[offer.id], context, now=NOW))
    expected = 'confirmed' if mode == 'success' else 'unknown' if mode in {'unknown', 'wrong_receipt'} else 'refused'
    assert result.status == expected
    assert requests.count('events_enroll_in_event') == int(mode in {'success', 'unknown', 'wrong_receipt'})
    assert 'private' not in (result.message or '')
    if mode == 'full':
        assert 'мест' in result.message
    elif mode.startswith('changed_'):
        assert 'изменил' in result.message


@pytest.mark.parametrize('mode', ['equivalent', 'all_day', 'changed_all_day', 'missing_details', 'naive', 'end_missing', 'full'])
def test_event_final_wire_details_fail_closed_without_losing_canonical_equivalence(monkeypatch, mode):
    from catix.api import signup
    original = deepcopy(EVENT)
    if mode == 'all_day':
        original['all_day'] = True
    offers, targets = signup.collect(event_read(original), 'Robotics', now=NOW)
    offer, = offers
    final = deepcopy(original)
    fresh = deepcopy(original)
    if mode == 'equivalent':
        fresh.update(starts_at=DAY + 'T14:00:00Z', ends_at=DAY + 'T15:30:00Z')
        final.update(fresh)
    elif mode == 'changed_all_day':
        final['all_day'] = True
    elif mode == 'missing_details':
        final = None
    elif mode == 'naive':
        final['starts_at'] = DAY + 'T17:00:00'
    elif mode == 'end_missing':
        final.pop('ends_at')
    elif mode == 'full':
        final['enrollment_info']['enrolled_count'] = final['enrollment_info']['capacity']
    writes = []
    async def request(method, payload, token=None, **credentials):
        if payload['name'] == 'events_get_event':
            return {'event': fresh}
        writes.append(payload)
        return {'done': True, 'event_id': EVENT['id'], 'enrolled': True, 'enrollment_verified': True, 'event': final}
    monkeypatch.setattr(signup.mcp_client, 'request', request)
    result = asyncio.run(signup.execute(offer, targets[offer.id], AgentContext(innohassle_token=SecretStr('ih')), now=NOW))
    assert result.status == ('confirmed' if mode in {'equivalent', 'all_day', 'full'} else 'unknown')
    assert len(writes) == 1


@pytest.mark.parametrize('mode', ['success', 'conflict', 'partial', 'moved', 'renamed', 'full', 'missing_credentials',
                                 'expired', 'lost_write', 'readback_lost', 'wrong_receipt', 'wrong_readback'])
def test_sport_refusal_and_unknown_paths_never_retarget(monkeypatch, mode):
    from catix.agent import schedule_tools
    from catix.api import signup
    offers, targets = signup.collect(recommendation(), 'Basketball', now=NOW)
    offer, = offers
    fresh, agenda = deepcopy(TRAINING), deepcopy(AGENDA)
    if mode == 'conflict':
        agenda.update(events=[{**TRAINING, 'title': 'Class'}], total=1)
    if mode == 'partial':
        agenda['complete'] = False
    if mode == 'moved':
        fresh['starts_at'] = DAY + 'T17:30:00+03:00'
    if mode == 'renamed':
        fresh['name'] = 'Other'
    if mode == 'full':
        fresh['can_check_in'] = False
    if mode == 'expired':
        offer.expires_at = NOW
    writes = []
    async def request(method, payload, token=None, **credentials):
        if payload['name'] == 'sport_get_sport_trainings':
            assert payload['arguments']['sport'] == 'Basketball'
            if writes and mode == 'readback_lost':
                raise TimeoutError('secret')
            return {'range': [DAY, DAY], 'trainings': [{**fresh, 'checked_in': bool(writes),
                       'training_id': 8 if writes and mode == 'wrong_readback' else 7}]}
        writes.append(payload)
        if mode == 'lost_write':
            raise TimeoutError('secret')
        return {'done': True, 'training_id': 8 if mode == 'wrong_receipt' else 7, 'signed_up': True}
    async def fresh_agenda(*a):
        return agenda
    monkeypatch.setattr(signup.mcp_client, 'request', request)
    monkeypatch.setattr(schedule_tools, 'aread_my_schedule', fresh_agenda)
    context = AgentContext(innohassle_id='owner', innohassle_token=SecretStr('ih'),
                           sport_token=None if mode == 'missing_credentials' else SecretStr('sport'))
    result = asyncio.run(signup.execute(offer, targets[offer.id], context, now=NOW))
    unknown = mode in {'lost_write', 'readback_lost', 'wrong_receipt', 'wrong_readback'}
    assert result.status == ('unknown' if unknown else 'confirmed' if mode == 'success' else 'refused')
    assert len(writes) == int(unknown or mode == 'success')
    if mode == 'conflict':
        assert 'пересекается' in result.message
    elif mode == 'partial':
        assert 'проверить расписание' in result.message
    elif mode in {'moved', 'renamed'}:
        assert 'изменил' in result.message
    elif mode == 'full':
        assert 'недоступна' in result.message


@pytest.mark.parametrize('mode', ['unsafe_url', 'foreign_id', 'naive_time', 'full', 'malformed', 'failure_after', 'mutated'])
def test_event_bad_evidence_cannot_offer_action(mode):
    from catix.api import signup
    item = deepcopy(EVENT)
    if mode == 'unsafe_url':
        item['enrollment_info'].update(type='external', url='javascript:alert(1)')
    if mode == 'naive_time':
        item['starts_at'] = DAY + 'T17:00:00'
    if mode == 'full':
        item['enrollment_info']['enrolled_count'] = 4
    if mode == 'malformed':
        item['names'] = 'not a language map'
    messages = event_read(item)
    if mode == 'foreign_id':
        messages[1].tool_calls[0]['args']['arguments']['event_id'] = 'b' * 24
    if mode == 'failure_after':
        messages.extend([messages[1], ToolMessage('{"error":"failed"}', name='call_api_tool', tool_call_id='event-read')])
    if mode == 'mutated':
        messages.extend([AIMessage('', tool_calls=[{'name': 'call_api_tool', 'id': 'write', 'args': {
            'name': 'events_enroll_in_event', 'arguments': {'event_id': EVENT['id']}}}]),
            ToolMessage('{"done":null}', name='call_api_tool', tool_call_id='write')])
    assert signup.collect(messages, 'Robotics', now=NOW) == ([], {})


@pytest.mark.parametrize('mode', ['later_failed_agenda', 'malformed_available', 'malformed_place', 'invalid_readback'])
def test_malformed_or_invalidated_training_evidence_fails_closed(monkeypatch, mode):
    from catix.api import signup
    messages = recommendation()
    if mode == 'later_failed_agenda':
        messages.extend([AIMessage('', tool_calls=[{'id': 'agenda', 'name': 'get_my_schedule', 'args': {}}]),
                         ToolMessage('{"error":"failed"}', name='get_my_schedule', tool_call_id='agenda')])
    elif mode == 'malformed_available':
        messages[2].content = '{"available": null}'
    elif mode == 'malformed_place':
        item = {**TRAINING, 'place': {'untrusted': 'object'}}
        messages[2].content = json.dumps({'available': [item]})
        messages[2].artifact = {**messages[2].artifact, 'trainings': {'range': [DAY, DAY], 'trainings': [item]}}
    else:
        # A fake transport error envelope must not establish enrollment even if it carries a training list.
        from catix.agent import schedule_tools
        offers, targets = signup.collect(messages, 'Basketball', now=NOW)
        offer, = offers
        writes = []
        async def request(method, payload, token=None, **kw):
            if payload['name'] == 'sport_get_sport_trainings':
                return {'range': [DAY, DAY], 'trainings': [{**TRAINING, 'checked_in': bool(writes)}],
                        **({'error': 'read failed'} if writes else {})}
            writes.append(payload)
            return {'done': True, 'training_id': 7, 'signed_up': True}
        async def agenda(*a):
            return AGENDA
        monkeypatch.setattr(signup.mcp_client, 'request', request)
        monkeypatch.setattr(schedule_tools, 'aread_my_schedule', agenda)
        context = AgentContext(innohassle_token=SecretStr('ih'), sport_token=SecretStr('sport'))
        assert asyncio.run(signup.execute(offer, targets[offer.id], context, now=NOW)).status == 'unknown'
        return
    assert signup.collect(messages, 'Basketball', now=NOW) == ([], {})


@pytest.mark.parametrize('mode', ['bad_tool_name', 'bad_enrollment_type', 'out_of_range'])
def test_invalid_service_metadata_never_breaks_the_chat_answer(mode):
    from catix.api import signup
    messages = event_read(listed=True)
    if mode == 'bad_tool_name':
        messages[1].tool_calls[0]['args']['name'] = []
        messages[2].status = 'error'
    elif mode == 'bad_enrollment_type':
        data = json.loads(messages[2].content)
        data['events'][0]['enrollment_info']['type'] = []
        messages[2].content = json.dumps(data)
    else:
        data = json.loads(messages[2].content)
        data['events'][0]['starts_at'] = '2099-01-03T17:00:00+03:00'
        data['events'][0]['ends_at'] = '2099-01-03T18:30:00+03:00'
        messages[2].content = json.dumps(data)
    assert signup.collect(messages, 'Robotics', now=NOW) == ([], {})
