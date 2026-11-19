"""Real graph -> API -> saved waiting response retains context without model prose."""

import json

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from catix.agent import api_tools, core
from catix.api import ask
from tests.test_api import client, kept  # noqa: F401 - synthetic HTTP auth and isolated in-memory chats
from tests.test_approval_context import EVENT
from tests.mcp_native_helpers import input_schema


@pytest.mark.parametrize("streamed", [False, True])
def test_blank_model_approval_details_survive_api_and_reopening(client, kept, monkeypatch, streamed):
    class Model(FakeMessagesListChatModel):
        def bind_tools(self, tools, **kwargs):
            return self

    sent = []

    def request(method, payload, token=None, **credentials):
        sent.append((method, payload))
        assert token is None and not credentials, "Schema and published event details are public"
        if method == "search_tools":
            return {"tools": [{"name": "events_enroll_in_event", "inputSchema": input_schema("events_enroll_in_event")}]}
        assert method == "call_tool" and payload == {"name": "events_get_event", "arguments": {"event_id": EVENT["id"]}}
        return {"event": EVENT}

    async def arequest(*args, **kwargs):
        return request(*args, **kwargs)

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    monkeypatch.setattr(api_tools.mcp_client, "request", arequest)
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    monkeypatch.setattr(ask.groups, "website_chat_ids", lambda *a: set())
    monkeypatch.setattr(ask.groups, "website_groups", lambda *a: [])
    agent = core.build_agent(Model(responses=[AIMessage(content="", tool_calls=[{
        "name": "call_api_tool", "id": "join", "args": {"name": "events_enroll_in_event", "arguments": {"event_id": EVENT["id"]}},
    }])]), guardrail=False)
    monkeypatch.setattr(ask, "agent", lambda: agent)
    response = client.post("/ask/stream" if streamed else "/ask/", json={"query": "Запиши на мероприятие."},
                           headers={"Authorization": "Bearer good"})
    assert response.status_code == 200
    if streamed:
        block = next(block for block in response.text.split("\n\n") if block.startswith("event: done\n"))
        body = json.loads(block.split("data: ", 1)[1])
    else:
        body = response.json()
    description = body["approval"]["actions"][0]["description"]
    assert all(value in description for value in ("Robotics workshop", "2026-11-09", "17:00", "19:00", "Room 314"))
    assert description not in body["answer"]
    assert "Robotics workshop" not in body["answer"]
    history = client.get(f"/ask/chats/{body['chat_id']}", headers={"Authorization": "Bearer good"}).json()
    assert history["waiting"]["approval"] == body["approval"]
    assert history["waiting"]["answer"] == body["answer"]
    assert not kept.answers
    assert len(sent) == 2, "Only schema discovery and exact detail read, never a write"
