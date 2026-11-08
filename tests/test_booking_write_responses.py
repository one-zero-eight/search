"""Malformed post-write replies are uncertainty, never a definite refusal."""
import asyncio
import json
from datetime import datetime

import httpx
import pytest

from catix.api import booking_offers, signup
from catix.api.schemas import SignupSelection
from catix.innohassle import client as backend
from tests.test_booking_offers import native_bookings  # noqa: F401
from tests.test_signup_offers import DAY, NOW


@pytest.mark.parametrize('service', ['rooms', 'music'])
@pytest.mark.parametrize('body', [[], None, True, 42, {}, {'id': None, 'outlook_booking_id': ''}])
def test_malformed_booking_post_remains_unknown_through_native_card(native_bookings, monkeypatch, service, body):
    state, context, recommend = native_bookings
    offers, targets = signup.collect(recommend(service), '', now=NOW)
    offer, = offers
    choice = (SignupSelection(booking_title='Study') if service == 'rooms'
              else SignupSelection(time_from='18:00', time_to='19:00'))
    chosen, target = booking_offers.select(offer, targets[offer.id], choice, now=NOW)
    original = backend._client._transport

    def respond(request):
        response = original.handle_request(request)
        return httpx.Response(200, content=json.dumps(body)) if request.method == 'POST' else response

    monkeypatch.setattr(backend._client, '_transport', httpx.MockTransport(respond))
    result = asyncio.run(signup.execute(chosen, target, context, now=NOW))
    assert len(state['writes']) == 1
    assert result.status == 'unknown'


def test_music_string_refusal_remains_distinct_from_malformed_response(monkeypatch):
    def respond(request):
        return httpx.Response(200, json='overlapping')

    with backend._http_client('https://synthetic.test', transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr(backend, '_client', client)
        with pytest.raises(backend.ServiceError) as raised:
            backend.book_music_room('synthetic', datetime.fromisoformat(DAY + 'T18:00:00+03:00'),
                                    datetime.fromisoformat(DAY + 'T19:00:00+03:00'))
        assert raised.value.status == 200


@pytest.mark.parametrize('body', [[], None, 'false', 0, 1, {}])
def test_malformed_music_cancellation_reply_is_not_definite_refusal(monkeypatch, body):
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, content=json.dumps(body))

    with backend._http_client('https://synthetic.test', transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr(backend, '_client', client)
        with pytest.raises(ValueError, match='response'):
            backend.cancel_music_room('synthetic', 99)
    assert len(requests) == 1 and requests[0].method == 'DELETE'


@pytest.mark.parametrize('body', [True, False])
def test_music_cancellation_boolean_contract(monkeypatch, body):
    with backend._http_client('https://synthetic.test', transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=body))) as client:
        monkeypatch.setattr(backend, '_client', client)
        if body:
            assert backend.cancel_music_room('synthetic', 99) is None
        else:
            with pytest.raises(backend.ServiceError):
                backend.cancel_music_room('synthetic', 99)


@pytest.mark.parametrize('body,expected', [([], None), (None, None), (False, False), (True, True)])
def test_native_cancellation_preserves_uncertainty_and_boolean_controls(monkeypatch, body, expected):
    from catix.innohassle import mcp_server
    from tests.mcp_native_helpers import call

    requests = []
    monkeypatch.setattr(mcp_server.token_verifier, 'claims', lambda token: {'uid': 'owner'})

    def respond(request):
        requests.append(request)
        return httpx.Response(200, content=json.dumps(body))

    with backend._http_client('https://synthetic.test', transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr(backend, '_client', client)
        result = call('account_cancel_booking', {'service': 'music_room', 'booking_id': '99'}, token='synthetic')
    assert result['done'] is expected
    if expected is None:
        assert result['outcome'] == 'unknown'
    assert len(requests) == 1 and requests[0].method == 'DELETE'
