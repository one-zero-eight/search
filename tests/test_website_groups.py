"""Website group verification uses the caller, never a Telegram/service identity."""

from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from pydantic import SecretStr

from catix import groups
from catix.api.app import app
from catix.api.auth import UserTokenData, verify_user
from catix.api import ask, source_requests
from catix.innohassle import client as upstream
from catix.settings import settings
from tests.test_api import client, kept  # noqa: F401 - isolated auth/chat fixtures
from tests.test_source_requests import db, source_database  # noqa: F401 - disposable SQL only


def test_source_groups_use_website_token_without_telegram_or_service_key(monkeypatch):
    monkeypatch.setattr(settings, "innohassle_service_token", None)
    monkeypatch.setattr(settings, "innohassle_groups", False)
    monkeypatch.setattr(source_requests.source_requests, "list_owned", lambda owner: [])
    calls = []

    def respond(request):
        calls.append(request)
        assert request.url.path == "/schedule-assistant/v0/me/student-groups"
        assert request.headers["Authorization"] == "Bearer website-user"
        return httpx.Response(200, json=["B26-CSE-01", "B26-CSE-02"])

    def no_telegram(*args):
        pytest.fail("Website must not resolve access via Telegram")

    monkeypatch.setattr(groups, "auto_group", no_telegram)
    with httpx.Client(transport=httpx.MockTransport(respond), base_url="https://upstream.test/") as client:
        monkeypatch.setattr(upstream, "_client", client)
        app.dependency_overrides[verify_user] = lambda: UserTokenData(
            innohassle_id="user", email="user@example.org", token=SecretStr("website-user"),
        )
        try:
            response = TestClient(app).get("/sources/requests")
        finally:
            app.dependency_overrides.pop(verify_user, None)
    assert response.status_code == 200
    assert response.json() == {"requests": [], "verified_groups": ["B26-CSE-01", "B26-CSE-02"]}
    assert len(calls) == 1


@pytest.mark.parametrize("streamed", [False, True])
@pytest.mark.parametrize("memberships, allowed, study_group", [
    (["B26", "B27"], {1, 2, 3, 4}, None),
    (["B26"], {1, 2, 4}, "B26"),
    ([], {1}, None),
    (403, {1}, None),
    (503, {1}, None),
    (302, {1}, None),
    ("timeout", {1}, None),
    ({"groups": ["B26"]}, {1}, None),
    (["B26", "all"], {1}, None),
    (["B26", 123], {1}, None),
])
def test_ask_uses_all_verified_groups_without_telegram(
    db, client, kept, monkeypatch, streamed, memberships, allowed, study_group,
):
    from catix.innohassle import token

    with db() as conn:
        conn.execute("""INSERT INTO chats (chat_id, title, group_code, requires_verified_group) VALUES
            (1, 'Public', 'all', false), (2, 'First', 'B26', true), (3, 'Second', 'B27', true),
            (4, 'Legacy first', 'B26', false), (5, 'Other', 'B99', true),
            (6, 'Not public', 'all', true), (7, 'Legacy other', 'B99', false)""")
    groups.set_user_group("tg:0", "B99")
    groups.set_user_group("ih:u1", "B99")
    monkeypatch.setattr(settings, "innohassle_service_token", None)
    monkeypatch.setattr(settings, "innohassle_groups", False)
    monkeypatch.setattr(token, "claims", lambda t: {"uid": "u1", "email": "a@innopolis.university"})
    monkeypatch.setattr(groups, "auto_group", lambda *args: pytest.fail("No Telegram lookup on website"))
    seen = []
    calls = []

    def respond(request):
        calls.append(request)
        assert request.url.path == "/schedule-assistant/v0/me/student-groups"
        assert request.headers["Authorization"] == "Bearer good"
        if memberships == "timeout":
            raise httpx.ReadTimeout("private response", request=request)
        if isinstance(memberships, int):
            return httpx.Response(memberships, text="private response", headers={"Location": "/do-not-follow"})
        return httpx.Response(200, json=memberships)

    class Agent:
        def __init__(self):
            self.checkpointer = self

        async def adelete_thread(self, thread):
            pass

        async def aget_state(self, config):
            return SimpleNamespace(values={}, config={"configurable": {"checkpoint_id": "cp"}})

        async def ainvoke(self, inputs, config, *, context):
            seen.append(context)
            return {"messages": [AIMessage("answer")], "sources": {}}

    agent = Agent()
    monkeypatch.setattr(ask, "agent", lambda: agent)
    monkeypatch.setattr(ask, "questions", ask.QuestionQueue(1))

    async def stream(inputs, config, context, events):
        return await agent.ainvoke(inputs, config, context=context)

    async def no_offers(*args):
        return []

    monkeypatch.setattr(ask, "stream_agent", stream)
    monkeypatch.setattr(ask, "calendar_offers", no_offers)
    with httpx.Client(transport=httpx.MockTransport(respond), base_url="https://upstream.test/") as transport:
        monkeypatch.setattr(upstream, "_client", transport)
        response = client.post("/ask/stream" if streamed else "/ask/", json={"query": "hello"},
                               headers={"Authorization": "Bearer good"})
    assert response.status_code == 200
    if streamed:
        assert "event: done" in response.text and "event: error" not in response.text
    assert len(seen) == 1
    assert seen[0].allowed_chat_ids == frozenset(allowed)
    assert seen[0].study_group == study_group
    assert len(calls) == 1


def test_verification_is_fresh_per_user_and_never_falls_back_or_logs_secrets(monkeypatch, caplog):
    responses = iter([
        httpx.Response(200, json=["B26", "B26", "b27"]),
        httpx.Response(200, json=["B28"]),
        httpx.Response(200, json=[]),
        httpx.Response(503, text="private-diagnostic"),
        httpx.Response(200, content="not JSON"),
    ])
    sent = []

    def respond(request):
        sent.append(request.headers["Authorization"])
        return next(responses)

    monkeypatch.setattr(groups, "auto_group", lambda *args: pytest.fail("No Telegram fallback"))
    with httpx.Client(transport=httpx.MockTransport(respond), base_url="https://upstream.test/") as transport:
        monkeypatch.setattr(upstream, "_client", transport)
        assert groups.website_groups("user-a") == ["B26", "B27"]
        assert groups.website_groups("user-b") == ["B28"]
        assert groups.website_groups("user-a") == []
        assert groups.website_groups("user-b") == []
        assert groups.website_groups("user-a") == []
        assert groups.website_groups(None) == []
    assert sent == ["Bearer user-a", "Bearer user-b", "Bearer user-a", "Bearer user-b", "Bearer user-a"]
    assert not any(value in caplog.text for value in ("private-diagnostic", "user-a", "user-b"))
