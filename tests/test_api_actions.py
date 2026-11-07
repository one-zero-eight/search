"""Static printer read contract over real mock HTTP; never live accounts."""
from copy import deepcopy
from types import SimpleNamespace
import asyncio

import httpx
import pytest

from catix.innohassle import actions, mcp_domain, client as backend


def read(name, parameters, token):
    """Exercise the actual declared function and server guard, not an action registry."""
    from fastmcp import Client
    from fastmcp.exceptions import ToolError
    from catix.innohassle import mcp_server

    async def call():
        with mcp_server.credentials(token):
            async with mcp_server.adapter() as root, Client(root) as client:
                return (await client.call_tool(name, parameters)).data
    try:
        return asyncio.run(call())
    except (ToolError, ValueError) as error:
        raise actions.ReadError(str(error)) from None

NAME = 'printers_print_get_printers_status'
PATH = '/printers/v0/print/get_printers_status'
STATUS = [{'printer': {'display_name': 'Library', 'cups_name': 'library', 'ipp': '192.168.1.1:631'},
           'offline': False, 'paper_percentage': 0, 'toner_percentage': None}]


@pytest.fixture
def gateway(monkeypatch):
    from catix.innohassle import token
    monkeypatch.setattr(token, 'claims', lambda value: {'uid': 'synthetic-' + value})
    state = SimpleNamespace(body=deepcopy(STATUS), status=200, asked=[], error=None,
                            headers={}, content=None)
    def respond(request):
        state.asked.append(request)
        assert request.method == 'GET' and request.url.path == PATH
        assert not request.url.query and not request.content
        if state.error:
            raise state.error('secret diagnostic', request=request)
        if state.content is not None:
            return httpx.Response(state.status, content=state.content)
        return httpx.Response(state.status, json=state.body, headers=state.headers)
    with backend._http_client('https://api.innohassle.ru', transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr(backend, '_client', client)
        yield state


def test_typed_projection_preserves_null_and_zero_but_not_ipp(gateway):
    result = read(NAME, {}, 'user-secret')
    assert result['data'] == [{'printer': {'display_name': 'Library', 'cups_name': 'library'},
                               'offline': False, 'paper_percentage': 0, 'toner_percentage': None}]
    assert '192.168' not in str(result) and 'user-secret' not in str(result)
    assert [r.url.path for r in gateway.asked] == [PATH]
    assert gateway.asked[0].headers['authorization'] == 'Bearer user-secret'
    assert not hasattr(actions, 'ACTIONS') and not hasattr(actions, 'Action')


@pytest.mark.parametrize('parameters', [{'url': 'http://127.0.0.1'}, {'Authorization': 'Bearer other'},
                                        {'printer_cups_name': 'library'}, {'user_id': 'other'}, {'token': 'bad'}])
def test_unsupported_parameters_refused_before_network(gateway, parameters):
    with pytest.raises(actions.ReadError):
        read(NAME, parameters, 'user-secret')
    assert not gateway.asked


def test_policy_rejects_non_object_arguments_before_protocol(gateway):
    # FastMCP Client treats a falsey [] as omitted arguments. The host checks
    # the original JSON before entering that client; do not test the sanitization.
    with pytest.raises(ValueError):
        mcp_domain.validate(NAME, [])
    assert not gateway.asked


@pytest.mark.parametrize('name', ['printers_print_actual_print', 'accounts_tokens_impersonate', 'https://evil.example/',
                                 'printers/../accounts/users', 'GET /print/get_printers_status'])
def test_unknown_names_cannot_pass_the_single_catalogue(gateway, name):
    with pytest.raises(ValueError):
        mcp_domain.validate(name, {})
    assert not gateway.asked


@pytest.mark.parametrize('token', [None, ''])
def test_missing_token_cannot_use_service_credentials(gateway, monkeypatch, token):
    from pydantic import SecretStr
    from catix.settings import settings
    monkeypatch.setattr(settings, 'innohassle_service_token', SecretStr('service-secret'))
    with pytest.raises(actions.ReadError, match='sign in'):
        read(NAME, {}, token)
    assert not gateway.asked


def test_results_are_fresh_and_missing_supplies_are_not_zero(gateway):
    first = read(NAME, {}, 'first-user')
    gateway.body[0].update(offline=True, paper_percentage=None, toner_percentage=0)
    second = read(NAME, {}, 'second-user')
    assert first['data'][0]['offline'] is False and second['data'][0]['offline'] is True
    assert second['data'][0]['paper_percentage'] is None and second['data'][0]['toner_percentage'] == 0
    assert [r.headers['authorization'] for r in gateway.asked] == ['Bearer first-user', 'Bearer second-user']


@pytest.mark.parametrize('status', [301, 302, 307, 401, 403, 404, 429, 500])
def test_errors_are_not_empty_results_or_raw_private_details(gateway, status):
    gateway.status, gateway.body = status, {'detail': 'user-secret ipp://192.168.1.1 private diagnostics'}
    gateway.headers = {'Location': 'https://evil.example/collect'}
    with pytest.raises(actions.ReadError) as error:
        read(NAME, {}, 'user-secret')
    assert all(text not in str(error.value) for text in ('user-secret', '192.168', 'private diagnostics'))
    assert len(gateway.asked) == 1


@pytest.mark.parametrize('body', [{}, [None], [{'offline': 'false'}], [{**STATUS[0], 'offline': 'false'}],
                                 [{**STATUS[0], 'paper_percentage': False}],
                                 [{**STATUS[0], 'offline': {'secret': 'hidden'}}],
                                 [*STATUS * 40, {'unexpected': 'invalid tail'}]])
def test_malformed_results_are_not_facts_including_truncated_tail(gateway, body):
    gateway.body = body
    with pytest.raises(actions.ReadError, match='unexpected response'):
        read(NAME, {}, 'user-secret')


@pytest.mark.parametrize('status', [200, 302, 307, 401, 403, 500])
def test_cookies_and_bearers_are_isolated_across_users(gateway, status):
    gateway.status = status
    gateway.headers = {'Set-Cookie': 'session=private-user-a; Path=/; Secure', 'Location': PATH}
    if status == 200:
        read(NAME, {}, 'user-a')
    else:
        with pytest.raises(actions.ReadError):
            read(NAME, {}, 'user-a')
    gateway.status = 200
    gateway.headers['Set-Cookie'] = 'session=private-user-b; Path=/; Secure'
    read(NAME, {}, 'user-b')
    assert not list(backend._client.cookies.jar)
    assert 'authorization' not in backend._client.headers
    assert [r.headers['authorization'] for r in gateway.asked] == ['Bearer user-a', 'Bearer user-b']
    assert all('cookie' not in r.headers for r in gateway.asked)


@pytest.mark.parametrize('error', [httpx.ReadTimeout, httpx.ConnectError])
def test_transport_errors_are_safe_and_not_retried(gateway, error):
    gateway.error = error
    with pytest.raises(actions.ReadError) as failure:
        read(NAME, {}, 'user-secret')
    assert 'secret diagnostic' not in str(failure.value)
    assert len(gateway.asked) == 1


@pytest.mark.parametrize('content', [b'<html>login page</html>', b'[' + b' ' * 1_000_001 + b']'])
def test_unreadable_or_oversized_response_is_not_a_result(gateway, content):
    gateway.content = content
    with pytest.raises(actions.ReadError):
        read(NAME, {}, 'user-secret')


def test_empty_and_truncated_inventory_are_distinct(gateway):
    gateway.body = []
    empty = read(NAME, {}, 'user-secret')
    assert empty['data'] == [] and empty['total'] == 0 and not empty['truncated']
    gateway.body = STATUS * (actions.MAX_ITEMS + 1)
    many = read(NAME, {}, 'user-secret')
    assert len(many['data']) == actions.MAX_ITEMS and many['total'] == actions.MAX_ITEMS + 1 and many['truncated']
    gateway.body = deepcopy(STATUS)
    gateway.body[0]['printer']['display_name'] = 'x' * actions.MAX_RESULT_CHARS
    with pytest.raises(actions.ReadError, match='unexpected response'):
        read(NAME, {}, 'user-secret')
