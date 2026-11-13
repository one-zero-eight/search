"""The production client only connects to an independently running HTTP server."""

import pytest
from pydantic import HttpUrl, ValidationError

from catix.settings import Settings


def test_default_mcp_endpoint_is_local_http(monkeypatch):
    monkeypatch.delenv("INNOHASSLE_MCP_URL", raising=False)
    configured = Settings(_env_file=None)
    assert configured.innohassle_mcp_url == HttpUrl("http://127.0.0.1:8010/mcp")


def test_mcp_endpoint_cannot_disable_http():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, innohassle_mcp_url=None)


@pytest.mark.parametrize("legacy_none", [False, True])
def test_unavailable_http_never_imports_or_constructs_an_adapter(monkeypatch, caplog, legacy_none):
    import builtins
    import httpx2
    from catix.innohassle import mcp_client, mcp_server

    constructed, imported, requests = [], [], []
    original_import = builtins.__import__
    original_http = mcp_client._http_client

    def import_guard(name, *args, **kwargs):
        if name == "catix.innohassle.mcp_server":
            imported.append(name)
            raise AssertionError("the production client must not import the server")
        return original_import(name, *args, **kwargs)

    def adapter_guard():
        constructed.append(True)
        raise AssertionError("the production client must not create a server")

    def unavailable(request):
        requests.append(request)
        raise httpx2.ConnectError("synthetic-token private diagnostic", request=request)

    monkeypatch.delenv("INNOHASSLE_MCP_URL", raising=False)
    endpoint = Settings(_env_file=None).innohassle_mcp_url
    monkeypatch.setattr(mcp_client.settings, "innohassle_mcp_url", None if legacy_none else endpoint)
    monkeypatch.setattr(mcp_server, "adapter", adapter_guard)
    monkeypatch.setattr(builtins, "__import__", import_guard)
    monkeypatch.setattr(mcp_client, "_http_client", lambda **kwargs: original_http(transport=httpx2.MockTransport(unavailable), **kwargs))
    result = mcp_client.request_sync("search_tools", {"query": "calendar"}, "synthetic-token")
    assert "error" in result
    assert not constructed and not imported
    if not legacy_none:
        assert requests and all(str(request.url) == str(endpoint) for request in requests)
    assert "synthetic-token" not in str(result) + caplog.text
    assert "private diagnostic" not in str(result) + caplog.text


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8010/mcp", "http://localhost:8010/mcp", "http://[::1]:8010/mcp",
    "http://mcp:8010/mcp", "https://adapter.example/mcp",
])
def test_allowed_http_endpoints_and_https(url):
    from catix.innohassle.mcp_client import validate_url

    validate_url(url)


@pytest.mark.parametrize("url", [
    "http://outside.example/mcp", "http://mcp/mcp", "http://mcp:8011/mcp", "http://mcp:8010/other",
    "http://mcp.example:8010/mcp", "http://mcp:8010/mcp/", "ftp://localhost/mcp",
    "http://@127.0.0.1:8010/mcp", "https://@adapter.example/mcp", "https://:@adapter.example/mcp",
    "https://user@adapter.example/mcp", "https://user:secret@adapter.example/mcp",
    "http://mcp:8010/mcp?token=secret", "http://mcp:8010/mcp#secret",
    "https://adapter.example/mcp?", "https://adapter.example/mcp#",
])
def test_url_credentials_and_nonapproved_http_endpoints_are_rejected(url):
    from catix.innohassle.mcp_client import validate_url

    with pytest.raises(ValueError):
        validate_url(url)


def test_confirmed_action_uses_normal_credentials_without_shared_store(monkeypatch):
    from types import SimpleNamespace
    from pydantic import SecretStr
    from catix.agent import api_tools
    from catix.agent.tools import AgentContext
    from catix.settings import settings

    monkeypatch.setattr(settings, "redis_url", None)
    sent = []
    monkeypatch.setattr(api_tools.mcp_client, "request_sync", lambda *a, **kw: sent.append((a, kw)) or {"done": True})
    runtime = SimpleNamespace(context=AgentContext(innohassle_token=SecretStr("synthetic-user")))
    arguments = {"service": "room", "booking_id": "test-booking"}
    assert api_tools.call_api_tool.func("account_cancel_booking", runtime, arguments) == {"done": True}
    assert sent == [(("call_tool", {"name": "account_cancel_booking", "arguments": arguments}, "synthetic-user"), {})]


@pytest.mark.parametrize("url", [
    "http://@127.0.0.1:8010/mcp", "https://@adapter.example/mcp", "https://:@adapter.example/mcp",
    "https://user:secret@adapter.example/mcp", "http://mcp:8010/mcp?", "http://mcp:8010/mcp#",
    "https://adapter.example/mcp?token=secret", "https://adapter.example/mcp#secret",
])
def test_settings_reject_url_context_before_httpurl_normalizes_it(url):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, innohassle_mcp_url=url)
