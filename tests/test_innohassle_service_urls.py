"""Service URL overrides use synthetic HTTP only; no local or production writes."""

import runpy
from datetime import datetime, timezone

import httpx
import pytest
from pydantic import HttpUrl, ValidationError

from catix.innohassle import actions, client as backend, token
from catix.settings import Settings


@pytest.fixture
def routed_api(monkeypatch):
    config = Settings(
        _env_file=None,
        innohassle_api="https://gateway.test/base",
        innohassle_events_api="http://127.0.0.1:9101/api/v1",
        innohassle_clubs_api="http://127.0.0.1:9102",
    )
    seen = []

    def reply(request):
        seen.append(request)
        return httpx.Response(200, json=[])

    with backend._http_client(str(config.innohassle_api), transport=httpx.MockTransport(reply)) as http:
        monkeypatch.setattr(backend, "settings", config)
        monkeypatch.setattr(backend, "_client", http)
        yield config, seen


def test_public_service_reads_replace_only_their_full_prefix(routed_api):
    _, seen = routed_api
    start = datetime(2099, 1, 1, tzinfo=timezone.utc)
    end = datetime(2099, 1, 2, tzinfo=timezone.utc)
    backend.events(start, end)
    backend.clubs()
    backend.club_leaders()
    backend.scenes()
    assert [str(r.url).split("?")[0] for r in seen] == [
        "http://127.0.0.1:9101/api/v1/events/",
        "http://127.0.0.1:9102/clubs/",
        "http://127.0.0.1:9102/leaders/",
        "https://gateway.test/base/maps/v0/scenes/",
    ]
    assert dict(seen[0].url.params) == {"from": start.isoformat(), "to": end.isoformat()}
    assert all("authorization" not in r.headers and "cookie" not in r.headers for r in seen)


@pytest.mark.parametrize("operation,path", [
    (lambda: backend.event("a" * 24, fresh=True), "/api/v1/events/" + "a" * 24),
    (lambda: backend._as_user("GET", "/events/v1/users/me", "test-user"), "/api/v1/users/me"),
    (lambda: backend._as_user("GET", backend.MY_CALENDARS["event"], "test-user"), "/api/v1/users/me/events.ics"),
    (lambda: backend.enroll("test-user", "a" * 24), "/api/v1/events/" + "a" * 24 + "/enroll"),
    (lambda: backend.unenroll("test-user", "a" * 24), "/api/v1/events/" + "a" * 24 + "/unenroll"),
    (lambda: actions.read("/events/v1/events/", actions.Event, {}, None, action_id="events", note=""), "/api/v1/events/"),
    (lambda: actions.read("/clubs/v0/clubs/", actions.Club, {}, None, action_id="clubs", note=""), "/clubs/"),
])
def test_fresh_private_mutation_and_streaming_reads_use_override(routed_api, operation, path):
    _, seen = routed_api
    operation()
    assert len(seen) == 1
    assert seen[0].url.host == "127.0.0.1"
    assert seen[0].url.port == (9102 if path == "/clubs/" else 9101)
    assert seen[0].url.path == path


@pytest.mark.parametrize("service", ["events", "clubs"])
def test_cache_is_separate_for_each_service_root(routed_api, service):
    config, seen = routed_api
    read = backend.clubs if service == "clubs" else lambda: backend.event("a" * 24)
    read()
    read()
    assert len(seen) == 1
    setattr(config, f"innohassle_{service}_api", HttpUrl("http://127.0.0.1:9103/other-root"))
    read()
    read()
    assert len(seen) == 2
    assert seen[-1].url.port == 9103
    setattr(config, f"innohassle_{service}_api", None)
    read()
    assert len(seen) == 3
    assert seen[-1].url.host == "gateway.test"


def test_cache_is_separate_for_each_default_gateway(routed_api, monkeypatch):
    _, seen = routed_api
    backend.scenes()
    with backend._http_client("https://another.test/base", transport=httpx.MockTransport(
        lambda r: seen.append(r) or httpx.Response(200, json=[]),
    )) as http:
        monkeypatch.setattr(backend, "_client", http)
        backend.scenes()
        backend.scenes()
    assert len(seen) == 2
    assert seen[-1].url.host == "another.test"


@pytest.mark.parametrize("field", ["innohassle_events_api", "innohassle_clubs_api"])
@pytest.mark.parametrize("value", [
    "http://user:secret@localhost:9101/v1", "http://@localhost:9101/v1",
    "http://localhost:9101/v1?", "http://localhost:9101/v1?q=test",
    "http://localhost:9101/v1#", "http://localhost:9101/v1#fragment",
    "ftp://localhost/v1", "/relative/v1",
])
def test_service_roots_reject_credentials_query_fragment_and_non_http(field, value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: value})


@pytest.mark.parametrize("field", ["innohassle_events_api", "innohassle_clubs_api"])
def test_empty_service_root_is_unset(field):
    assert getattr(Settings(_env_file=None, **{field: ""}), field) is None


def test_service_roots_load_from_environment(monkeypatch):
    monkeypatch.setenv("INNOHASSLE_EVENTS_API", "http://events:8000/v1/")
    monkeypatch.setenv("INNOHASSLE_CLUBS_API", "http://clubs:8000/")
    config = Settings(_env_file=None)
    assert str(config.innohassle_events_api) == "http://events:8000/v1/"
    assert str(config.innohassle_clubs_api) == "http://clubs:8000/"


@pytest.mark.parametrize("events_root", [None, "http://127.0.0.1:9101/v1", "http://127.0.0.1:9101/v1/"])
@pytest.mark.parametrize("clubs_root", [None, "http://127.0.0.1:9102", "http://127.0.0.1:9102/"])
def test_overrides_are_optional_independent_and_preserve_trailing_slashes(routed_api, events_root, clubs_root):
    config, seen = routed_api
    config.innohassle_events_api = HttpUrl(events_root) if events_root else None
    config.innohassle_clubs_api = HttpUrl(clubs_root) if clubs_root else None
    backend.event("a" * 24, fresh=True)
    backend.clubs()
    assert str(seen[0].url) == (
        "http://127.0.0.1:9101/v1/events/" if events_root else "https://gateway.test/base/events/v1/events/"
    ) + "a" * 24
    assert str(seen[1].url) == (
        "http://127.0.0.1:9102/clubs/" if clubs_root else "https://gateway.test/base/clubs/v0/clubs/"
    )


def test_accounts_jwks_and_other_services_keep_the_gateway(routed_api, monkeypatch):
    config, seen = routed_api
    monkeypatch.setattr("catix.settings.settings", config)
    loaded = runpy.run_path(token.__file__)
    assert loaded["JWKS_URL"] == "https://gateway.test/base/accounts/v0/.well-known/jwks.json"
    for path in ["/accounts/v0/users/me", "/schedule/v0/users/me", "/room-booking/v0/rooms/",
                 "/music-room/v0/users/me", "/events/v10/users/me", "/clubs/v01/clubs/"]:
        backend._as_user("GET", path, "synthetic-user")
        assert str(seen[-1].url) == "https://gateway.test/base" + path


def test_private_tokens_and_upstream_cookies_never_reach_public_calls(routed_api, monkeypatch):
    _, seen = routed_api

    def reply(request):
        seen.append(request)
        return httpx.Response(200, json=[], headers={"Set-Cookie": "session=private; Path=/"})

    with backend._http_client("https://gateway.test/base", transport=httpx.MockTransport(reply)) as http:
        monkeypatch.setattr(backend, "_client", http)
        backend._as_user("GET", "/events/v1/users/me", "first-user")
        backend._as_user("GET", "/events/v1/users/me", "second-user")
        backend.event("a" * 24, fresh=True)
        actions.read("/events/v1/events/", actions.Event, {}, None, action_id="events", note="")
        backend.clubs()
        backend.scenes()
    assert [r.headers.get("authorization") for r in seen] == [
        "Bearer first-user", "Bearer second-user", None, None, None, None,
    ]
    assert all("cookie" not in r.headers for r in seen)


@pytest.mark.parametrize("failure", ["timeout", "503", "307"])
@pytest.mark.parametrize("operation", [
    lambda: backend.clubs(),
    lambda: backend.event("a" * 24, fresh=True),
    lambda: actions.read("/events/v1/events/", actions.Event, {}, None, action_id="events", note=""),
    lambda: backend._as_user("POST", "/events/v1/drafts/", "test-user", json={"locales": ["en"]}),
])
def test_local_failure_never_retries_redirects_or_falls_back_to_gateway(routed_api, monkeypatch, failure, operation):
    _, seen = routed_api

    def reply(request):
        seen.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("synthetic timeout", request=request)
        return httpx.Response(int(failure), headers={"Location": "https://gateway.test/events/v1/drafts/"})

    with backend._http_client("https://gateway.test/base", transport=httpx.MockTransport(reply)) as http:
        monkeypatch.setattr(backend, "_client", http)
        with pytest.raises((httpx.HTTPError, actions.ReadError, backend.ServiceError)):
            operation()
    assert len(seen) == 1
    assert seen[0].url.host == "127.0.0.1"
