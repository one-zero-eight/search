"""Attachment metadata follows a question through SSE, history and approval."""

import json

import pytest

from catix.api import ask
from tests.test_api import AUTH, answering, client, kept  # noqa: F401 - shared isolated API fixtures
from tests.test_attachment_privacy import traced_files  # noqa: F401 - isolated real tracer


def events(response):
    return [(block.splitlines()[0].removeprefix("event: "), json.loads(block.splitlines()[1].removeprefix("data: ")))
            for block in response.text.strip().split("\n\n")]


def test_stream_identifies_chat_before_generation_fails(client, monkeypatch, kept):
    async def failure(*args, **kwargs):
        raise RuntimeError("synthetic model failure")

    monkeypatch.setattr(ask, "_run", failure)
    response = client.post("/ask/stream", json={"query": "Прочитай файл"}, headers=AUTH)
    stream = events(response)
    assert stream[0][0] == "chat"
    assert kept.owner(stream[0][1]["chat_id"]) == "u1"
    assert stream[-1][0] == "error"


@pytest.mark.parametrize("path", ["/ask/", "/ask/stream"])
def test_attachment_ids_are_validated_before_generation(client, monkeypatch, kept, path):
    monkeypatch.setattr(ask, "_run", answering())
    response = client.post(path, json={"query": "Прочитай файл", "attachment_ids": ["a", "b", "c", "d"]}, headers=AUTH)
    assert response.status_code == 422
    assert not kept.answers


@pytest.mark.parametrize("path", ["/ask/", "/ask/stream"])
def test_attachment_manifest_follows_question_into_history(client, monkeypatch, kept, traced_files, path):
    store = getattr(ask, "attachments", None)
    assert store is not None, "ask must bind owned uploads and return metadata"
    item = store.AttachmentInfo(id="11111111-1111-4111-8111-111111111111", filename="plan.txt",
                                media_type="text/plain", size_bytes=20, pages=1)
    calls = []

    def bind(owner, chat_id, ids):
        assert owner == "u1" and kept.owner(chat_id) == owner and ids == [item.id]
        calls.append("bind")
        return [item]

    from catix.agent import tracing
    feedback_calls = []
    monkeypatch.setattr(tracing, "score_feedback", lambda *args: feedback_calls.append(args))

    async def answer(query, chat_id, user, events=None, decision=None, **kwargs):
        assert tracing.is_private()
        assert tracing.enabled()
        assert kwargs["attachment_manifest"] == (item.model_dump(),)
        assert kwargs["current_attachment_ids"] == (item.id,)
        calls.append("agent")
        text = "В файле указан дедлайн."
        with tracing.question(kept.thread_of(chat_id), user.innohassle_id, query) as traced:
            traced.answer(text)
        return text, [], [], traced.id, "cp-file"

    monkeypatch.setattr(store, "bind", bind)
    monkeypatch.setattr(store, "list_for_chat", lambda owner, chat_id: [item])
    monkeypatch.setattr(ask, "_run", answer)
    response = client.post(path, json={"query": "Какой дедлайн?", "attachment_ids": [item.id]}, headers=AUTH)
    assert response.status_code == 200
    body = response.json() if path == "/ask/" else next(data for name, data in events(response) if name == "done")
    assert body["attachments"] == [item.model_dump()]
    assert body["ask_query_id"]
    assert calls == ["bind", "agent"]
    history = client.get(f"/ask/chats/{body['chat_id']}", headers=AUTH).json()
    assert history["answers"][0]["attachments"] == body["attachments"]
    response = client.post(f"/ask/{body['ask_query_id']}/feedback?feedback=dislike", json={"comment": "Wrong deadline"}, headers=AUTH)
    assert response.status_code == 200
    span = next(span for span in traced_files.get_finished_spans() if span.name == "question")
    assert span.attributes["input.value"] == "Какой дедлайн?"
    assert span.attributes["output.value"] == body["answer"]
    assert feedback_calls == [(f"{span.context.span_id:016x}", "api:u1", False, "Wrong deadline")]
    history = client.get(f"/ask/chats/{body['chat_id']}", headers=AUTH).json()
    assert history["answers"][0]["feedback"] == "dislike"
    assert history["answers"][0]["feedback_comment"] == "Wrong deadline"


def test_upload_contract_is_registered_in_the_application(client):
    from catix.api.app import app
    schema = app.openapi()
    assert "/ask/attachments" in schema["paths"]
    upload = schema["paths"]["/ask/attachments"]["post"]
    assert upload["requestBody"]["content"]["application/octet-stream"]["schema"]["format"] == "binary"
    assert client.post("/ask/attachments", content=b"test",
                       headers={"Content-Type": "application/octet-stream", "X-Attachment-Filename": "test.txt"}).status_code == 401


@pytest.mark.parametrize("path", ["/ask/", "/ask/stream"])
def test_private_model_errors_are_not_logged_or_returned(client, monkeypatch, caplog, path):
    item = ask.attachments.AttachmentInfo(id="a" * 32, filename="private.txt", media_type="text/plain", size_bytes=10, pages=1)
    monkeypatch.setattr(ask.attachments, "list_for_chat", lambda *args: [item])

    async def failure(*args, **kwargs):
        raise RuntimeError("PRIVATE_DOCUMENT_SENTINEL")

    monkeypatch.setattr(ask, "_run", failure)
    response = client.post(path, json={"query": "Прочитай документ"}, headers=AUTH)
    assert "PRIVATE_DOCUMENT_SENTINEL" not in response.text
    assert "PRIVATE_DOCUMENT_SENTINEL" not in caplog.text
    assert "ML service error" in response.text


def test_approval_resume_retains_files_and_followups_remain_private(client, monkeypatch, kept):
    from catix.agent import tracing
    monkeypatch.setattr(tracing, "_provider", object())
    feedback_calls = []
    monkeypatch.setattr(tracing, "score_feedback", lambda *args: feedback_calls.append(args))
    from catix.api.schemas import AskAction, AskApproval

    item = ask.attachments.AttachmentInfo(id="a" * 32, filename="event.png", media_type="image/png", size_bytes=100, pages=1)
    monkeypatch.setattr(ask.attachments, "bind", lambda *args: [item])
    monkeypatch.setattr(ask.attachments, "list_for_chat", lambda *args: [item])
    seen = []

    async def answer(query, chat_id, user, events=None, decision=None, **kwargs):
        assert tracing.is_private()
        seen.append(kwargs["current_attachment_ids"])
        if len(seen) == 1:
            return ask.Waiting("В файле указана встреча.", [], None, "cp-wait",
                               AskApproval(id="cp-wait", actions=[AskAction(name="add_to_ai_calendar", description="Добавить встречу")]),
                               [{"id": "interrupt", "actions": 1}])
        return "Ответ", [], [], "phoenix-span-followup", "cp-done"

    monkeypatch.setattr(ask, "_run", answer)
    stream = events(client.post("/ask/stream", json={"query": "Добавь встречу с картинки", "attachment_ids": [item.id]}, headers=AUTH))
    body = next(data for name, data in stream if name == "done")
    chat_id = body["chat_id"]
    assert body["attachments"] == [item.model_dump()]
    history = client.get(f"/ask/chats/{chat_id}", headers=AUTH).json()
    assert history["waiting"]["attachments"] == body["attachments"]
    decision = client.post(f"/ask/{chat_id}/decision", json={"decision": "reject", "approval_id": "cp-wait"}, headers=AUTH)
    assert decision.status_code == 200 and decision.json()["attachments"] == body["attachments"]
    followup = client.post("/ask/", json={"query": "Что ещё видно?", "chat_id": chat_id}, headers=AUTH)
    assert followup.status_code == 200 and followup.json()["attachments"] == []
    assert followup.json()["ask_query_id"]
    feedback = client.post(f"/ask/{followup.json()['ask_query_id']}/feedback?feedback=like", json={"comment": "Useful summary"}, headers=AUTH)
    assert feedback.status_code == 200
    assert feedback_calls == [("phoenix-span-followup", "api:u1", True, "Useful summary")]
    history = client.get(f"/ask/chats/{chat_id}", headers=AUTH).json()
    assert history["answers"][-1]["feedback"] == "like"
    assert history["answers"][-1]["feedback_comment"] == "Useful summary"
    assert seen == [(item.id,), (item.id,), ()]


@pytest.mark.parametrize("path", ["/ask/", "/ask/stream"])
def test_unowned_file_is_rejected_before_the_agent(client, monkeypatch, kept, path):
    def denied(*args):
        raise ask.attachments.AttachmentError(404, "Attachment not found")

    monkeypatch.setattr(ask.attachments, "bind", denied)
    monkeypatch.setattr(ask, "_run", lambda *args, **kwargs: pytest.fail("unowned file reached the model"))
    response = client.post(path, json={"query": "Прочитай", "attachment_ids": ["a" * 32]}, headers=AUTH)
    assert response.status_code == 404 and not kept.answers
