"""Existing account HTTP backends must keep the MCP's credential isolation."""

import httpx
import pytest

from catix.innohassle import client, sport


def test_shared_domain_http_client_never_replays_cookies():
    assert hasattr(client, "_http_client"), "Domain clients need a restrictive shared HTTP factory"
    seen = []

    def reply(request):
        seen.append(dict(request.headers))
        return httpx.Response(200, json={}, headers={"Set-Cookie": "session=another-user; Path=/"})

    with client._http_client("https://backend.test", transport=httpx.MockTransport(reply)) as http:
        http.get("/private", headers={"Authorization": "Bearer synthetic-alice"})
        http.get("/private", headers={"Authorization": "Bearer synthetic-bob"})
        http.get("/public")
        assert not list(http.cookies.jar)
    assert all("cookie" not in headers for headers in seen)
    assert seen[0]["authorization"] != seen[1]["authorization"] and "authorization" not in seen[2]


@pytest.mark.parametrize("backend", [client, sport])
def test_domain_mutations_never_follow_redirects_or_claim_ambiguous_success(backend, monkeypatch):
    assert hasattr(client, "_http_client")
    asked = []

    def reply(request):
        asked.append(request.url.path)
        return httpx.Response(307, headers={"Location": "/credential-collector"})

    with client._http_client("https://backend.test", transport=httpx.MockTransport(reply)) as http:
        monkeypatch.setattr(backend, "_client", http)
        call = client._as_user if backend is client else sport._call
        with pytest.raises(httpx.HTTPError):
            call("POST", "/book", "synthetic-alice")
    assert asked == ["/book"]


@pytest.mark.parametrize("backend", [client, sport])
@pytest.mark.parametrize("status", [408, 500, 502, 503])
def test_uncertain_write_response_escapes_business_refusal_handlers(backend, status, monkeypatch):
    with client._http_client("https://backend.test", transport=httpx.MockTransport(
        lambda request: httpx.Response(status, json={"detail": "synthetic internal diagnostic"})
    )) as http:
        monkeypatch.setattr(backend, "_client", http)
        call = client._as_user if backend is client else sport._call
        with pytest.raises(httpx.HTTPError) as error:
            call("POST", "/book", "synthetic-alice")
        assert "synthetic internal diagnostic" not in str(error.value)


@pytest.mark.parametrize("status", [401, 403, 409, 422])
def test_definite_business_refusals_keep_their_semantics(status, monkeypatch):
    with client._http_client("https://backend.test", transport=httpx.MockTransport(
        lambda request: httpx.Response(status, json={"detail": "no permission or slot"})
    )) as http:
        monkeypatch.setattr(client, "_client", http)
        with pytest.raises(client.ServiceError) as error:
            client._as_user("POST", "/book", "synthetic-alice")
        assert error.value.status == status


def test_malformed_cancellation_response_is_unknown_not_a_validation_refusal(monkeypatch):
    from tests.mcp_native_helpers import call
    from catix.innohassle import mcp_server
    monkeypatch.setattr(mcp_server.token_verifier, "claims", lambda token: {"uid": "u1"})

    sent = []

    def reply(request):
        sent.append(request)
        return httpx.Response(200, text="truncated non-JSON response after cancellation")

    with client._http_client("https://backend.test", transport=httpx.MockTransport(reply)) as http:
        monkeypatch.setattr(client, "_client", http)
        result = call("account_cancel_booking", {"service": "music_room", "booking_id": "42"},
                                   token="synthetic-user", sport_token=None, uid="u1")
    assert len(sent) == 1 and sent[0].method == "DELETE"
    assert result.get("done") is None and result.get("outcome") == "unknown"
    assert "retry automatically" in result["error"]
