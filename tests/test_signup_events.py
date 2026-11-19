"""Native Events projections expose typed enrollment; writes need exact own readback."""

import httpx
import pytest

from catix.innohassle import client as api
from tests.test_mcp_action_details import event, identity, invoke  # noqa: F401

pytestmark = pytest.mark.usefixtures('identity')


def published(**changes):
    return {**event(enrollment={'type': 'internal', 'capacity': 4}), 'enrolled_count': 1, 'enrolled': False, **changes}


def test_exact_and_list_events_expose_same_typed_snapshot(monkeypatch):
    monkeypatch.setattr(api, 'event', lambda *a, **kw: published())
    monkeypatch.setattr(api, 'events', lambda *a: [published()])
    exact = invoke('events_get_event', {'event_id': 'a' * 24})[0].data['event']
    listed = invoke('events_get_university_events', {'date_from': '2099-01-01', 'date_to': '2099-01-02'})[0].data['events'][0]
    assert exact.get('enrollment_info') == {'type': 'internal', 'capacity': 4, 'url': None, 'enrolled_count': 1}
    for key in ('id', 'title', 'starts_at', 'ends_at', 'location', 'enrollment_info'):
        assert listed[key] == exact[key]
    assert 'enrolled' not in exact and 'enrolled_emails' not in str(exact)


@pytest.mark.parametrize('mode', ['success', 'readback_lost', 'wrong_id', 'not_enrolled', 'already', 'full', 'external'])
def test_events_write_confirms_only_exact_authenticated_readback(monkeypatch, mode):
    requests = []
    state = {'written': False}
    def send(request):
        requests.append(request)
        assert request.headers.get('authorization') == 'Bearer synthetic-ih'
        assert request.url.path == '/events/v1/events/' + 'a' * 24 + ('/enroll' if request.method == 'POST' else '')
        if request.method == 'POST':
            state['written'] = True
        wrote = state['written']
        if request.method == 'GET' and wrote:
            state['written'] = False
        body = published(enrolled=wrote or mode == 'already')
        if mode == 'full':
            body['enrolled_count'] = 4
        if mode == 'external':
            body['data']['enrollment'] = {'type': 'external', 'url': 'https://organizer.test/signup'}
        if wrote and request.method == 'GET':
            if mode == 'readback_lost':
                raise httpx.ReadTimeout('sensitive upstream diagnostics')
            if mode == 'wrong_id':
                body['id'] = 'b' * 24
            if mode == 'not_enrolled':
                body['enrolled'] = False
        return httpx.Response(200, json=body, request=request)
    monkeypatch.setattr(api, '_client', httpx.Client(base_url='https://api.test/', transport=httpx.MockTransport(send)))
    # Invoke each protocol separately; both follow the same fresh-read/write/readback path.
    for result in invoke('events_enroll_in_event', {'event_id': 'a' * 24}):
        if mode in {'success', 'already'}:
            assert result.data['done'] is True and result.data.get('enrollment_verified') is True
            verified = result.data['event']
            assert verified['id'] == 'a' * 24 and verified['title'] == 'Meeting'
            assert verified['starts_at'] == '2099-01-01T23:30:00+03:00'
            assert verified['ends_at'] == '2099-01-02T01:30:00+03:00'
            assert verified['location'] == '301'
            assert 'participants' not in verified and 'enrolled' not in verified
        elif mode in {'full', 'external'}:
            assert result.data['done'] is False
        else:
            assert result.data['done'] is None and result.data['outcome'] == 'unknown'
    if mode in {'already', 'full', 'external'}:
        assert all(r.method == 'GET' for r in requests)
    else:
        assert sum(r.method == 'POST' for r in requests) <= 2
    assert 'sensitive' not in str(result)


@pytest.mark.parametrize('generic', [False, True])
@pytest.mark.parametrize('phase', ['authenticated_prewrite', 'readback'])
@pytest.mark.parametrize('changed', [None, 'interval', 'duration', 'name', 'location', 'equivalent'])
def test_native_event_click_compares_final_details(monkeypatch, generic, phase, changed):
    import asyncio
    import json

    from fastmcp import Client
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
    from pydantic import SecretStr

    from catix.agent.tools import AgentContext
    from catix.api import signup
    from catix.innohassle import mcp_server
    from tests.test_signup_offers import DAY, NOW

    requests = []
    writes = []
    def snapshot(*, authenticated=False):
        body = published(enrolled=bool(writes), enrolled_count=2 if writes else 1)
        body['data'].update(starts_at=DAY + 'T17:00:00+03:00', duration_hours=1.5)
        if authenticated and (phase == 'authenticated_prewrite' or writes):
            if changed == 'interval':
                body['data']['starts_at'] = DAY + 'T18:00:00+03:00'
            elif changed == 'duration':
                body['data']['duration_hours'] = 2
            elif changed == 'name':
                body['data']['locales']['en']['name'] = 'Other meeting'
            elif changed == 'location':
                body['data']['location']['display_name'] = 'Other room'
            elif changed == 'equivalent':
                body['data']['starts_at'] = DAY + 'T14:00:00Z'
        return body
    def send(request):
        requests.append(request.method)
        assert request.headers['authorization'] == 'Bearer synthetic-ih'
        if request.method == 'POST':
            writes.append(request)
        return httpx.Response(200, json=snapshot(authenticated=True), request=request)
    monkeypatch.setattr(api, 'event', lambda *a, **kw: snapshot())
    monkeypatch.setattr(api, '_client', httpx.Client(base_url='https://api.test/', transport=httpx.MockTransport(send)))
    async def run():
        root = await mcp_server.build_server()
        async def request(method, payload, token=None, **credentials):
            with mcp_server.credentials(token):
                async with Client(root) as client:
                    result = await client.call_tool(method if generic else payload['name'],
                                                    payload if generic else payload['arguments'])
                    return result.data
        monkeypatch.setattr(signup.mcp_client, 'request', request)
        payload = {'name': 'events_get_event', 'arguments': {'event_id': 'a' * 24}}
        data = await request('call_tool', payload)
        messages = [HumanMessage('Events?'), AIMessage('', tool_calls=[{'id': 'read', 'name': 'call_api_tool', 'args': payload}]),
                    ToolMessage(json.dumps(data), tool_call_id='read', name='call_api_tool')]
        offers, targets = signup.collect(messages, 'Meeting', now=NOW)
        offer, = offers
        assert not writes
        context = AgentContext(innohassle_id='owner', innohassle_token=SecretStr('synthetic-ih'))
        result = await signup.execute(offer, targets[offer.id], context, now=NOW)
        assert result.status == ('confirmed' if changed in {None, 'equivalent'} else 'unknown')
        assert result.starts_at == offer.starts_at and result.ends_at == offer.ends_at
    asyncio.run(run())
    assert requests == ['GET', 'POST', 'GET'] and len(writes) == 1


def test_list_detail_identity_mismatch_is_not_a_new_target(monkeypatch):
    monkeypatch.setattr(api, 'events', lambda *a: [published()])
    monkeypatch.setattr(api, 'event', lambda *a, **kw: published(id='b' * 24))
    for result in invoke('events_get_university_events', {'date_from': '2099-01-01'}):
        assert result.is_error or 'error' in result.data
        assert not (result.data or {}).get('events')
