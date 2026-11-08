"""Real PostgreSQL claim races. Opt in only with a disposable signup_test DB."""
import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg
import pytest
from psycopg.rows import dict_row

from catix.api import chats, signup
from catix.api.schemas import AskResponses
from catix.db import pg
from tests.test_signup_offers import (
    AGENDA,
    DAY,
    EVENT,
    NOW,
    TRAINING,
    event_read,
    native_sport_recommendation,  # noqa: F401 - shared native protocol fixture
    recommendation,
)


@pytest.fixture
def stored(monkeypatch):
    url = os.environ.get('SIGNUP_TEST_DATABASE_URL')
    if not url:
        pytest.skip('needs disposable SIGNUP_TEST_DATABASE_URL')
    assert psycopg.conninfo.conninfo_to_dict(url)['dbname'] == 'signup_test'
    monkeypatch.setattr(pg, 'connection', lambda: psycopg.connect(url, row_factory=dict_row))
    owner = 'signup-test:' + uuid4().hex
    chat_id = chats.start(owner, 'Basketball')
    offers, targets = signup.collect(recommendation(), 'Basketball', now=NOW)
    response = AskResponses(query='q', answer='Basketball', chat_id=chat_id, search_responses=[], messages=[], signup_offers=offers)
    response._signup_targets = targets
    chats.save_answer(response, None, 'checkpoint')
    yield chat_id, owner, offers[0], targets
    chats.delete(chat_id, owner)


@pytest.mark.parametrize('changed', [None, 'interval'])
def test_native_all_day_offer_interval_survives_click_history_and_receipt(stored, native_sport_recommendation, changed):
    from catix.api import ask
    from catix.api.auth import UserTokenData

    chat_id, owner, _, _ = stored
    messages, context, writes = native_sport_recommendation(all_day=True, changed=changed)
    offers, targets = signup.collect(messages, 'Basketball', now=NOW)
    offer, = offers
    response = AskResponses(query='all-day', answer='Basketball', chat_id=chat_id,
                            search_responses=[], messages=[], signup_offers=offers)
    response._signup_targets = targets
    chats.save_answer(response, None, 'checkpoint')
    reopened = chats.history(chat_id, owner).answers[-1].signup_offers[0]
    assert reopened.all_day is True and reopened.ends_at == offer.ends_at
    user = UserTokenData(innohassle_id=owner, email='a@innopolis.university', token=context.innohassle_token,
                         sport_token=context.sport_token)
    result = asyncio.run(ask.signup_offer(user, chat_id, offer.id))
    assert result.status == ('unknown' if changed else 'confirmed')
    assert asyncio.run(ask.signup_offer(user, chat_id, offer.id)) == result
    assert len(writes) == 1, 'An uncertain changed readback must never regain execution rights'
    reopened = chats.history(chat_id, owner).answers[-1].signup_offers[0]
    assert reopened == result
    receipt, = chats.signup_receipts(chat_id, owner)
    assert receipt['all_day'] is True
    assert receipt['starts_at'] == offer.model_dump(mode='json')['starts_at']
    assert receipt['ends_at'] == offer.model_dump(mode='json')['ends_at']
    assert receipt['status'] == result.status


def test_atomic_claim_has_one_winner_and_survives_restart(stored):
    chat_id, owner, offer, _targets = stored
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: chats.claim_signup(chat_id, owner, offer.id), range(8)))
    assert sum(result[1] is not None for result in results) == 1
    assert all(result[0].status == 'unknown' for result in results)
    again, target = chats.claim_signup(chat_id, owner, offer.id)
    assert again.status == 'unknown' and target is None
    assert chats.claim_signup(chat_id, 'attacker', offer.id) is None
    assert chats.claim_signup(chat_id, owner, 'forged') is None
    reopened = chats.history(chat_id, owner).answers[0]
    assert reopened.signup_offers[0].status == 'unknown'
    assert '_signup_targets' not in reopened.model_dump_json()
    completed = signup.outcome(again, 'confirmed', signup.CONFIRMED)
    assert chats.finish_signup(chat_id, owner, completed).status == 'confirmed'
    assert chats.claim_signup(chat_id, owner, offer.id)[1] is None
    assert chats.history(chat_id, owner).answers[0].signup_offers[0].status == 'confirmed'
    receipt, = chats.signup_receipts(chat_id, owner)
    assert receipt['status'] == 'confirmed' and receipt['title'] == 'Basketball'


@pytest.mark.parametrize('streamed', [False, True])
@pytest.mark.parametrize('service', ['sport', 'events'])
def test_http_read_offer_click_history_next_turn_without_click_model(stored, monkeypatch, streamed, service):
    import json
    from types import SimpleNamespace

    from fastapi.testclient import TestClient

    from catix.agent import schedule_tools
    from catix.api import ask
    from catix.api.app import app
    from catix.innohassle import token

    chat_id, owner, _, _ = stored
    inputs, writes = [], []
    class Graph:
        async def aget_state(self, config):
            return SimpleNamespace(values={'sources': {}}, config={'configurable': {'checkpoint_id': 'cp-next'}}, interrupts=[])
        async def ainvoke(self, data, config, **kw):
            inputs.append(data)
            return {'messages': recommendation() if service == 'sport' else event_read(), 'sources': {}}
        async def astream(self, data, config, **kw):
            yield 'values', await self.ainvoke(data, config)
    monkeypatch.setattr(ask, 'agent', Graph)
    monkeypatch.setattr(ask.groups, 'scoped_chat_ids', lambda *a: set())
    monkeypatch.setattr(ask.groups, 'effective_group', lambda *a: ask.groups.ALL)
    async def no_calendar(*a):
        return []
    monkeypatch.setattr(ask, 'calendar_offers', no_calendar)
    monkeypatch.setattr(ask.titles, 'name', lambda *a: 'Sport')
    monkeypatch.setattr(token, 'claims', lambda t: {'uid': owner if t == 'fresh-ih' else 'attacker', 'email': 'a@innopolis.university'})
    monkeypatch.setattr(token, 'sport_email', lambda t: 'a@innopolis.university')
    async def request(method, payload, token=None, **credentials):
        if service == 'events':
            if payload['name'] == 'events_get_event':
                assert token is None and not credentials
                return {'event': EVENT}
            assert token == 'fresh-ih' and not credentials
            assert payload['name'] == 'events_enroll_in_event'
            writes.append(payload)
            return {'done': True, 'event_id': EVENT['id'], 'enrolled': True, 'enrollment_verified': True, 'event': EVENT}
        assert token == 'fresh-ih' and credentials == {'sport_token': 'fresh-sport'}
        if payload['name'] == 'sport_get_sport_trainings':
            return {'range': [DAY, DAY], 'trainings': [{**TRAINING, 'checked_in': bool(writes)}]}
        assert payload['name'] == 'sport_sport_checkin'
        writes.append(payload)
        return {'done': True, 'training_id': 7, 'signed_up': True}
    async def agenda(*a):
        return AGENDA
    monkeypatch.setattr(signup.mcp_client, 'request', request)
    monkeypatch.setattr(schedule_tools, 'aread_my_schedule', agenda)
    client = TestClient(app)
    auth = {'Authorization': 'Bearer fresh-ih', 'X-Sport-Token': 'fresh-sport'}
    response = client.post('/ask/stream' if streamed else '/ask/', headers=auth,
                           json={'query': 'Предложи тренировки', 'chat_id': chat_id})
    assert response.status_code == 200, response.text
    body = json.loads(next(b.split('data: ', 1)[1] for b in response.text.split('\n\n') if b.startswith('event: done\n'))) if streamed else response.json()
    assert len(body.get('signup_offers', [])) == 1, body
    offer = body['signup_offers'][0]
    path = f'/ask/{chat_id}/signup/{offer["id"]}'
    assert client.post(path, headers={'Authorization': 'Bearer other'}).status_code == 404
    assert client.post(f'/ask/{chat_id}/signup/forged', headers=auth).status_code == 404
    assert client.post(path).status_code == 401
    first = client.post(path, headers=auth)
    assert first.status_code == 200 and first.json()['status'] == 'confirmed', first.text
    assert client.post(path, headers=auth).json() == first.json()
    assert len(writes) == 1 and len(inputs) == 1, 'No second model call on click'
    history = client.get(f'/ask/chats/{chat_id}', headers=auth).json()
    assert history['answers'][-1]['signup_offers'][0]['status'] == 'confirmed'
    assert 'training_id' not in json.dumps(history)
    client.post('/ask/', headers=auth, json={'query': 'Куда я записан?', 'chat_id': chat_id})
    receipt_text = '\n'.join(m.content for m in inputs[-1]['messages'] if getattr(m, 'type', None) == 'ai')
    assert 'confirmed' in receipt_text and ('Basketball' if service == 'sport' else 'Robotics') in receipt_text


@pytest.mark.parametrize('failure', [None, 'lost_write', 'lost_receipt'])
def test_concurrent_clicks_and_lost_outcomes_never_repeat_write(stored, monkeypatch, failure):
    from pydantic import SecretStr

    from catix.agent import schedule_tools
    from catix.api import ask
    from catix.api.auth import UserTokenData
    chat_id, owner, offer, _ = stored
    writes = []
    async def request(method, payload, token=None, **credentials):
        if payload['name'] == 'sport_get_sport_trainings':
            return {'range': [DAY, DAY], 'trainings': [{**TRAINING, 'checked_in': bool(writes)}]}
        # The database claim is committed and visible from an independent connection BEFORE this write.
        assert chats.history(chat_id, owner).answers[0].signup_offers[0].status == 'unknown'
        writes.append(payload)
        await asyncio.sleep(0.01)
        if failure == 'lost_write':
            raise TimeoutError('secret')
        return {'done': True, 'training_id': 7, 'signed_up': True}
    async def agenda(*a):
        return AGENDA
    monkeypatch.setattr(signup.mcp_client, 'request', request)
    monkeypatch.setattr(schedule_tools, 'aread_my_schedule', agenda)
    if failure == 'lost_receipt':
        def lost(*a):
            raise ConnectionError('storage lost')
        monkeypatch.setattr(chats, 'finish_signup', lost)
    user = UserTokenData(innohassle_id=owner, email='a@innopolis.university', token=SecretStr('ih'), sport_token=SecretStr('sport'))
    async def race():
        return await asyncio.gather(*(ask.signup_offer(user, chat_id, offer.id) for _ in range(8)))
    results = asyncio.run(race())
    expected = 'unknown' if failure else 'confirmed'
    assert len(writes) == 1 and all(result.status == expected for result in results)
    assert asyncio.run(ask.signup_offer(user, chat_id, offer.id)).status == expected
    assert chats.history(chat_id, owner).answers[0].signup_offers[0].status == expected
    assert chats.signup_receipts(chat_id, owner)[0]['status'] == expected


def test_real_graph_native_recommendation_to_click_with_replaced_credentials(stored, monkeypatch):
    from fastapi.testclient import TestClient
    from langchain_core.messages import AIMessage

    from catix.agent import calendar_tools, core
    from catix.api import ask
    from catix.api.app import app
    from catix.innohassle import token
    from tests.test_roles import ScriptedModel
    chat_id, owner, _, _ = stored
    with pg.connection() as conn:
        conn.execute('UPDATE api_chats SET checkpoint = NULL WHERE chat_id = %s', (chat_id,))
    monkeypatch.setattr(core.store, 'visible_chats', lambda *a: [])
    monkeypatch.setattr(core, 'tool_call_token', lambda: None)
    monkeypatch.setattr(ask.groups, 'scoped_chat_ids', lambda *a: set())
    monkeypatch.setattr(ask.groups, 'effective_group', lambda *a: ask.groups.ALL)
    monkeypatch.setattr(ask.titles, 'name', lambda *a: 'Sport')
    monkeypatch.setattr(calendar_tools, 'events_between', lambda *a: [])
    async def no_calendar(*a):
        return []
    monkeypatch.setattr(ask, 'calendar_offers', no_calendar)
    monkeypatch.setattr(token, 'claims', lambda t: {'uid': owner, 'email': 'a@innopolis.university'})
    monkeypatch.setattr(token, 'sport_email', lambda t: 'a@innopolis.university')
    calls, writes = [], []
    def request(method, payload, token=None, **credentials):
        calls.append((payload['name'], token, credentials))
        if payload['name'] == 'sport_get_sport_trainings':
            assert payload['arguments'] == {'date_from': DAY, 'date_to': DAY, 'sport': 'Basketball'}
            return {'range': [DAY, DAY], 'trainings': [{**TRAINING, 'checked_in': bool(writes)}]}
        if payload['name'] == 'account_get_my_schedule':
            return {'range': [DAY, DAY], 'schedule': [], 'bookings': []}
        assert payload['name'] == 'sport_sport_checkin'
        writes.append(payload)
        return {'done': True, 'training_id': 7, 'signed_up': True}
    async def arequest(*a, **kw):
        return request(*a, **kw)
    monkeypatch.setattr(signup.mcp_client, 'request_sync', request)
    monkeypatch.setattr(signup.mcp_client, 'request', arequest)
    model = ScriptedModel(responses=[AIMessage('', tool_calls=[{'id': 'native-read', 'name': 'get_my_available_trainings',
                                    'args': {'day': DAY, 'sport': 'Basketball'}}]), AIMessage('Basketball в Hall в 17:00–18:30.')])
    graph = core.build_agent(model, guardrail=False)
    monkeypatch.setattr(ask, 'agent', lambda: graph)
    client = TestClient(app)
    before = {'Authorization': 'Bearer original-ih', 'X-Sport-Token': 'original-sport'}
    response = client.post('/ask/', headers=before, json={'query': 'Подбери тренировку на 2099-01-02', 'chat_id': chat_id})
    assert response.status_code == 200, response.text
    offer, = response.json()['signup_offers']
    assert not writes
    after = {'Authorization': 'Bearer replaced-ih', 'X-Sport-Token': 'replaced-sport'}
    index = len(calls)
    clicked = client.post(f'/ask/{chat_id}/signup/{offer["id"]}', headers=after)
    assert clicked.json()['status'] == 'confirmed', clicked.text
    assert len(writes) == 1
    assert all(ih == 'replaced-ih' for _, ih, _ in calls[index:])
    assert all(creds == {'sport_token': 'replaced-sport'} for name, _, creds in calls[index:] if name.startswith('sport_'))
