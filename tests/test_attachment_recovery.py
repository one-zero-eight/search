"""A lost first SSE event must not strand bound uploads or make them impossible to retry."""

import json

import pytest

from fastapi.testclient import TestClient
from pydantic import SecretStr

from catix import attachments
from catix.api import ask
from catix.api.app import app
from catix.api.auth import UserTokenData, verify_asker, verify_user
from tests.test_attachments import disposable_db  # noqa: F401 - real isolated SQL


@pytest.fixture(autouse=True)
def no_calendar_model(monkeypatch):
    monkeypatch.setattr(ask.calendar_events, "extract", lambda *args, **kwargs: [])


@pytest.mark.parametrize("path", ["/ask/", "/ask/stream"])
def test_retry_without_received_chat_id_recovers_its_owned_bound_files(disposable_db, monkeypatch, path):
    owner, original_chat, _, connect = disposable_db
    info = attachments.create(owner, "retry.txt", b"An uploaded note.")
    # The first HTTP request committed this binding, but the connection was lost before its first SSE event.
    attachments.bind(owner, original_chat, [info.id])
    user = UserTokenData(innohassle_id=owner, email="synthetic@innopolis.university", token=SecretStr("synthetic"), sport_token=None)
    monkeypatch.setattr(ask.titles, "name", lambda *args: "Recovered")
    async def answer(query, chat_id, user, events=None, decision=None, **kwargs):
        return "Read successfully", [], [], None, "cp-recovered"
    monkeypatch.setattr(ask, "_run", answer)
    app.dependency_overrides[verify_user] = lambda: user
    app.dependency_overrides[verify_asker] = lambda: user
    try:
        response = TestClient(app).post(path, json={"query": "Прочитай файл", "attachment_ids": [info.id]})
        assert response.status_code == 200, response.text
        assert response_chat(response) == original_chat
        with connect() as conn:
            assert conn.execute("SELECT chat_id FROM api_attachments WHERE id = %s", (info.id,)).fetchone()["chat_id"] == original_chat
            assert conn.execute("SELECT count(*) AS n FROM api_chats WHERE innohassle_id = %s", (owner,)).fetchone()["n"] == 2
    finally:
        app.dependency_overrides.pop(verify_user, None)
        app.dependency_overrides.pop(verify_asker, None)


def response_chat(response):
    assert response.status_code == 200, response.text
    if response.headers["content-type"].startswith("text/event-stream"):
        first = response.text.split("\n\n", 1)[0]
        assert first.startswith("event: chat\n")
        assert "event: done" in response.text
        return json.loads(first.split("data: ", 1)[1])["chat_id"]
    return response.json()["chat_id"]


@pytest.fixture
def recovery_client(disposable_db, monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    owner, _, _, _ = disposable_db
    user = UserTokenData(innohassle_id=owner, email="synthetic@innopolis.university", token=SecretStr("synthetic"), sport_token=None)
    monkeypatch.setattr(ask.titles, "name", lambda *args: "Recovered")
    async def answer(query, chat_id, user, events=None, decision=None, **kwargs):
        assert decision is None  # Recovery is not an approval resume.
        return "Read successfully", [], [], None, "cp-recovered"
    monkeypatch.setattr(ask, "_run", answer)
    monkeypatch.setattr(ask, "_agent", SimpleNamespace(checkpointer=SimpleNamespace(adelete_thread=AsyncMock())))
    app.dependency_overrides[verify_user] = lambda: user
    app.dependency_overrides[verify_asker] = lambda: user
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(verify_user, None)
        app.dependency_overrides.pop(verify_asker, None)


@pytest.mark.parametrize("path", ["/ask/", "/ask/stream"])
def test_binding_committed_between_lookup_and_bind_is_recovered(disposable_db, recovery_client, monkeypatch, path):
    owner, original_chat, _, connect = disposable_db
    info = attachments.create(owner, "race.txt", b"An uploaded note.")
    start = ask.chats.start
    def racing_start(owner, query):
        # Another first request binds after this request's lookup, before its bind.
        attachments.bind(owner, original_chat, [info.id])
        return start(owner, query)
    monkeypatch.setattr(ask.chats, "start", racing_start)
    response = recovery_client.post(path, json={"query": "Read", "attachment_ids": [info.id]})
    assert response_chat(response) == original_chat
    with connect() as conn:
        assert conn.execute("SELECT chat_id FROM api_attachments WHERE id = %s", (info.id,)).fetchone()["chat_id"] == original_chat


@pytest.mark.parametrize("path", ["/ask/", "/ask/stream"])
@pytest.mark.parametrize("case,status", [
    ("unknown", 404), ("unowned_file", 404), ("unowned_chat", 404), ("mixed_chats", 409),
    ("expired", 404), ("explicit_other", 409), ("duplicate", 422), ("malformed", 404),
])
def test_recovery_rejects_invalid_sets_without_rebinding(disposable_db, recovery_client, monkeypatch, path, case, status):
    owner, original_chat, other_chat, connect = disposable_db
    first = attachments.create(owner, "first.txt", b"First note.")
    second = attachments.create(owner, "second.txt", b"Second note.")
    attachments.bind(owner, original_chat, [first.id])
    ids = [first.id, second.id]
    body = {"query": "Read", "attachment_ids": ids}
    with connect() as conn:
        if case == "unknown":
            ids[1] = "f" * 32
        elif case == "unowned_file":
            conn.execute("UPDATE api_attachments SET owner = %s WHERE id = %s", (owner + ":other", second.id))
        elif case == "unowned_chat":
            conn.execute("UPDATE api_chats SET innohassle_id = %s WHERE chat_id = %s", (owner + ":other", original_chat))
        elif case == "mixed_chats":
            attachments.bind(owner, other_chat, [second.id])
        elif case == "expired":
            conn.execute("UPDATE api_attachments SET created_at = now() - interval '25 hours' WHERE id = %s", (second.id,))
        elif case == "explicit_other":
            body["chat_id"] = other_chat
        elif case == "duplicate":
            ids[1] = first.id
        elif case == "malformed":
            ids[1] = "A" * 32
    def bindings():
        with connect() as conn:
            return conn.execute("SELECT id, chat_id FROM api_attachments WHERE id = ANY(%s) ORDER BY id", ([first.id, second.id],)).fetchall()
    before = bindings()
    monkeypatch.setattr(ask, "_run", lambda *args, **kwargs: pytest.fail("invalid files reached the agent"))
    try:
        response = recovery_client.post(path, json=body)
        assert response.status_code == status, response.text
        assert bindings() == before
    finally:
        # Keep the shared fixture's unique-owner cleanup complete, including denial controls.
        with connect() as conn:
            conn.execute("UPDATE api_attachments SET owner = %s WHERE id = %s", (owner, second.id))
            conn.execute("UPDATE api_chats SET innohassle_id = %s WHERE chat_id = %s", (owner, original_chat))


@pytest.mark.parametrize("path", ["/ask/", "/ask/stream"])
def test_recovery_accepts_live_pending_files_alongside_old_bound_files(disposable_db, recovery_client, path):
    owner, original_chat, _, connect = disposable_db
    first = attachments.create(owner, "first.txt", b"First note.")
    second = attachments.create(owner, "second.txt", b"Second note.")
    attachments.bind(owner, original_chat, [first.id])
    with connect() as conn:
        conn.execute("UPDATE api_attachments SET created_at = now() - interval '25 hours' WHERE id = %s", (first.id,))
    response = recovery_client.post(path, json={"query": "Read", "attachment_ids": [second.id, first.id]})
    assert response_chat(response) == original_chat
    assert {item.id for item in attachments.list_for_chat(owner, original_chat)} == {first.id, second.id}


@pytest.mark.parametrize("case,status", [("unowned", 404), ("mixed", 409), ("expired", 404)])
def test_conflict_recovery_revalidates_all_ids(disposable_db, recovery_client, monkeypatch, case, status):
    owner, original_chat, other_chat, connect = disposable_db
    first = attachments.create(owner, "first.txt", b"First note.")
    second = attachments.create(owner, "second.txt", b"Second note.")
    bind = attachments.bind
    start = ask.chats.start
    def racing_start(owner, query):
        bind(owner, original_chat, [first.id])
        return start(owner, query)
    def racing_bind(owner, chat_id, ids):
        try:
            return bind(owner, chat_id, ids)
        except attachments.AttachmentError as exc:
            assert exc.status_code == 409
            # Change the second ID after the conflict, before the recovery lookup.
            with connect() as conn:
                if case == "unowned":
                    conn.execute("UPDATE api_attachments SET owner = %s WHERE id = %s", (owner + ":other", second.id))
                elif case == "mixed":
                    bind(owner, other_chat, [second.id])
                else:
                    conn.execute("UPDATE api_attachments SET created_at = now() - interval '25 hours' WHERE id = %s", (second.id,))
            raise
    monkeypatch.setattr(ask.chats, "start", racing_start)
    monkeypatch.setattr(attachments, "bind", racing_bind)
    monkeypatch.setattr(ask, "_run", lambda *args, **kwargs: pytest.fail("invalid conflict reached the agent"))
    try:
        response = recovery_client.post("/ask/stream", json={"query": "Read", "attachment_ids": [first.id, second.id]})
        assert response.status_code == status, response.text
        with connect() as conn:
            assert conn.execute("SELECT chat_id FROM api_attachments WHERE id = %s", (first.id,)).fetchone()["chat_id"] == original_chat
            assert conn.execute("SELECT chat_id FROM api_attachments WHERE id = %s", (second.id,)).fetchone()["chat_id"] == (other_chat if case == "mixed" else None)
    finally:
        with connect() as conn:
            conn.execute("UPDATE api_attachments SET owner = %s WHERE id = %s", (owner, second.id))


@pytest.mark.parametrize("path", ["/ask/", "/ask/stream"])
@pytest.mark.parametrize("failure", [RuntimeError, ask.AskCancelled])
def test_failed_first_request_can_retry_without_chat_id(disposable_db, recovery_client, monkeypatch, path, failure):
    owner, _, _, connect = disposable_db
    info = attachments.create(owner, "first-request.txt", b"An uploaded note.")
    body = {"query": "Read", "attachment_ids": [info.id]}
    answer = ask._run
    async def fail(*args, **kwargs):
        raise failure("synthetic failure")
    monkeypatch.setattr(ask, "_run", fail)
    first = recovery_client.post(path, json=body)
    if path.endswith("stream"):
        assert "event: cancelled" in first.text if failure is ask.AskCancelled else "event: error" in first.text
    else:
        assert first.status_code == (409 if failure is ask.AskCancelled else 502)
    with connect() as conn:
        original_chat = conn.execute("SELECT chat_id FROM api_attachments WHERE id = %s", (info.id,)).fetchone()["chat_id"]
        assert original_chat is not None
        assert conn.execute("SELECT count(*) AS n FROM api_answers WHERE chat_id = %s", (original_chat,)).fetchone()["n"] == 0
    assert original_chat in {chat["chat_id"] for chat in recovery_client.get("/ask/chats").json()}
    monkeypatch.setattr(ask, "_run", answer)
    assert response_chat(recovery_client.post(path, json=body)) == original_chat


def test_unanswered_file_chat_is_listed_and_owned_delete_cascades(disposable_db, recovery_client):
    owner, original_chat, empty_chat, connect = disposable_db
    info = attachments.create(owner, "unanswered.txt", b"Never answered.")
    attachments.bind(owner, original_chat, [info.id])
    listed = recovery_client.get("/ask/chats")
    assert listed.status_code == 200
    assert {chat["chat_id"] for chat in listed.json()} == {original_chat}
    assert ask.chats.of_user(owner + ":other") == []
    assert not ask.chats.delete(original_chat, owner + ":other")
    assert attachments.get_content(owner, info.id)[0] == info
    response = recovery_client.delete(f"/ask/chats/{original_chat}")
    assert response.status_code == 200
    with connect() as conn:
        assert conn.execute("SELECT id FROM api_attachments WHERE id = %s", (info.id,)).fetchone() is None
        assert conn.execute("SELECT chat_id FROM api_chats WHERE chat_id = %s", (original_chat,)).fetchone() is None
        assert conn.execute("SELECT chat_id FROM api_chats WHERE chat_id = %s", (empty_chat,)).fetchone() is not None
    assert recovery_client.get("/ask/chats").json() == []
