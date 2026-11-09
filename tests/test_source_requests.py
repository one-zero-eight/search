"""Source request contracts against an explicitly disposable, full-schema ParadeDB."""
import importlib.util
import os
from pathlib import Path

import psycopg
import pytest
from psycopg.rows import dict_row

from catix.db import pg

LINK = "https://t.me/+AbCdEfGhIjKlMnOp"


@pytest.mark.parametrize("audience", ["B26", "all"])
def test_form_admin_and_userbot_share_exact_durable_request(db, monkeypatch, audience):
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from fastapi.testclient import TestClient
    from telethon.tl import types
    from telethon.tl.functions.messages import ImportChatInviteRequest
    from catix import groups
    from catix.api.app import app
    from catix.api.auth import UserTokenData, verify_user
    from catix.tgbot import source_requests as moderation
    from catix.tguserbot import source_requests as worker

    client = TestClient(app)
    monkeypatch.setattr(moderation.changes, "admins", lambda: [7])
    monkeypatch.setattr(groups, "auto_group", lambda telegram_id: "B26" if telegram_id == 123 else None)
    monkeypatch.setattr(groups, "website_groups", lambda _: ["B26"])
    app.dependency_overrides[verify_user] = lambda: UserTokenData(innohassle_id="owner", email="o@example.org", telegram_id=123)
    try:
        created = client.post("/sources/requests", json={"invite_link": LINK, "group_code": audience, "consent": True})
        assert created.status_code == 201
        request_id = created.json()["id"]
        callback = SimpleNamespace(
            data=f"sr:approve:{request_id}", from_user=SimpleNamespace(id=7), answer=AsyncMock(),
            message=SimpleNamespace(chat=SimpleNamespace(type="private"), edit_text=AsyncMock()),
        )
        asyncio.run(moderation.request_callback(callback))
        assert "одобрена" in callback.message.edit_text.call_args.args[0].lower()
        assert client.get("/sources/requests").json()["requests"][0]["status"] == "approved"
        joined = False
        chat = types.Chat(123, "Confirmed source", types.ChatPhotoEmpty(), 1, None, 1)
        async def telegram(request, **kwargs):
            nonlocal joined
            if isinstance(request, ImportChatInviteRequest):
                joined = True
                return SimpleNamespace(chats=[chat])
            return types.ChatInviteAlready(chat) if joined else types.ChatInvite("Source", types.PhotoEmpty(1), 1, 0)
        assert asyncio.run(worker.process_one(telegram))
        view = client.get("/sources/requests").json()["requests"][0]
        assert view["id"] == request_id and view["status"] == "connected"
        assert view["title"] == "Confirmed source" and "invite_link" not in view
        assert groups.scoped_chat_ids("tg:123", 123) == {-123}
        groups.set_user_group("tg:456", "B26")
        assert groups.scoped_chat_ids("tg:456", 456) == ({-123} if audience == "all" else set())
        assert groups.website_chat_ids([]) == ({-123} if audience == "all" else set())
    finally:
        app.dependency_overrides.pop(verify_user, None)


@pytest.fixture(scope="module")
def source_database():
    dsn = os.environ.get("SOURCE_REQUESTS_TEST_DSN")
    if not dsn:
        pytest.skip("set SOURCE_REQUESTS_TEST_DSN to disposable ParadeDB")
    with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as conn:
        assert conn.execute("SELECT current_database() AS name").fetchone()["name"] == "catix_source_requests_test"
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.execute("CREATE EXTENSION IF NOT EXISTS pg_search")
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = 'ctx_reader'").fetchone():
            conn.execute("CREATE ROLE ctx_reader")
        schema = Path(__file__).resolve().parents[1].joinpath("db/schema.sql").read_text().replace("__TZ__", "UTC")
        conn.execute(schema)
        conn.execute(schema)
    return dsn


@pytest.fixture
def db(source_database, monkeypatch):
    def connect():
        return psycopg.connect(source_database, row_factory=dict_row)
    monkeypatch.setattr(pg, "connection", connect)
    with connect() as conn:
        conn.execute("TRUNCATE chats, userbot_listen, userbot_dialogs, user_groups, personal_events, calendar_proposals CASCADE")
        if conn.execute("SELECT to_regclass('source_requests') AS name").fetchone()["name"]:
            conn.execute("TRUNCATE source_requests")
        conn.execute("TRUNCATE source_request_join_intents")
        if conn.execute("SELECT to_regclass('source_request_lease') AS name").fetchone()["name"]:
            conn.execute("UPDATE source_request_lease SET token = NULL, lease_until = NULL, available_at = now()")
    yield connect


def test_submit_is_durable_private_and_deduplicated(db):
    assert importlib.util.find_spec("catix.source_requests"), "durable source request store is missing"
    from catix import source_requests as requests
    row = requests.submit("owner-a", "owner@example.org", LINK, " b26-cse-01 ", "Please add", consent=True)
    assert row["status"] == "pending"
    assert row["group_code"] == "B26-CSE-01"
    assert len(row["id"]) == 32
    assert row["consented_at"] is not None
    assert requests.submit("owner-a", "owner@example.org", LINK.replace("/+", "/joinchat/"), "B26-CSE-01", "", consent=True)["id"] == row["id"]
    assert requests.list_owned("owner-a") == [row]
    assert requests.list_owned("other") == []
    with db() as conn:
        assert conn.execute("SELECT count(*) AS n FROM chats").fetchone()["n"] == 0
        assert conn.execute("SELECT count(*) AS n FROM userbot_listen").fetchone()["n"] == 0


def test_all_audience_stays_pending_until_approved_and_activates_public_scope(db, monkeypatch):
    from fastapi.testclient import TestClient
    from catix import groups, source_requests as requests
    from catix.api.app import app
    from catix.api.auth import UserTokenData, verify_user

    monkeypatch.setattr(groups, "website_groups", lambda _: pytest.fail("Public proposals do not require study-group membership"))
    app.dependency_overrides[verify_user] = lambda: UserTokenData(innohassle_id="owner", email="o@example.org")
    try:
        response = TestClient(app).post("/sources/requests", json={"invite_link": LINK, "group_code": "all", "consent": True})
    finally:
        app.dependency_overrides.pop(verify_user, None)
    assert response.status_code == 201, response.text
    row = response.json()
    assert row["status"] == "pending" and row["group_code"] == "all"
    assert requests.claim() is None
    assert groups.website_chat_ids([]) == set()
    assert requests.approve(row["id"], 7, "all")
    assert requests.activate(requests.claim(), -123, "Public source", None, False)
    with db() as conn:
        chat = conn.execute("SELECT * FROM chats WHERE chat_id = -123").fetchone()
        assert chat["group_code"] == "all" and chat["requires_verified_group"] is False
    assert groups.website_chat_ids([]) == {-123}
    monkeypatch.setattr(groups, "auto_group", lambda _: None)
    assert groups.scoped_chat_ids("tg:999", 999) == {-123}


@pytest.mark.parametrize("memberships, requested, status", [
    (["B26", "B27"], "b27", 201),
    (["B26"], "B27", 403),
    ([], "B26", 403),
    ([], "all", 201),
    (["B26"], "bad group!", 422),
])
def test_submission_requires_fresh_own_group_unless_all(db, monkeypatch, memberships, requested, status):
    from fastapi.testclient import TestClient
    from pydantic import SecretStr
    from catix import groups, source_requests as requests
    from catix.api.app import app
    from catix.api.auth import UserTokenData, verify_user

    tokens = []
    monkeypatch.setattr(groups, "website_groups", lambda token: tokens.append(token) or memberships)
    groups.set_user_group("web:owner", "B27")  # A manual claim must never count as verification.
    app.dependency_overrides[verify_user] = lambda: UserTokenData(
        innohassle_id="owner", email="o@example.org", token=SecretStr("test-user-token"),
    )
    try:
        response = TestClient(app).post("/sources/requests", json={"invite_link": LINK, "group_code": requested, "consent": True})
    finally:
        app.dependency_overrides.pop(verify_user, None)
    assert response.status_code == status, response.text
    assert tokens == ([] if requested in ("all", "bad group!") else ["test-user-token"])
    assert len(requests.list_owned("owner")) == (1 if status == 201 else 0)


def test_audience_migration_preserves_existing_private_sources_and_accepts_all(db):
    from catix import groups, source_requests as requests

    private = requests.submit("owner", "o@example.org", LINK, "B26", consent=True)
    assert requests.approve(private["id"], 7, "B26")
    assert requests.activate(requests.claim(), -123, "Private source", None, False)
    with db() as conn:
        conn.execute("ALTER TABLE source_requests DROP CONSTRAINT IF EXISTS source_requests_group_code_check")
        conn.execute("ALTER TABLE source_requests ADD CONSTRAINT source_requests_group_code_check CHECK (group_code <> 'all')")
        schema = Path(__file__).resolve().parents[1].joinpath("db/schema.sql").read_text().replace("__TZ__", "UTC")
        conn.execute(schema)
        conn.execute(schema)
        chat = conn.execute("SELECT * FROM chats WHERE chat_id = -123").fetchone()
        assert chat["group_code"] == "B26" and chat["requires_verified_group"] is True
    assert requests.submit("other", "o@example.org", LINK, "all", consent=True)["status"] == "pending"
    assert groups.website_chat_ids([]) == set()
    assert groups.website_chat_ids(["B26"]) == {-123}


def test_persistent_rate_limit_serializes_concurrent_submissions(db):
    from concurrent.futures import ThreadPoolExecutor
    from catix import source_requests as requests
    assert hasattr(requests, "RateLimited"), "persistent submission rate limit is missing"
    def attempt(number):
        try:
            return requests.submit("owner", "owner@example.org", LINK + str(number), "B26", consent=True)
        except requests.RateLimited:
            return None
    with ThreadPoolExecutor(8) as pool:
        results = list(pool.map(attempt, range(12)))
    assert len([r for r in results if r]) == 5
    first = next(r for r in results if r)
    assert requests.submit("owner", "owner@example.org", first["invite_link"], "B26", consent=True)["id"] == first["id"]
    with db() as conn:
        conn.execute("UPDATE source_requests SET created_at = now() - interval '25 hours'")
    assert attempt(99) is not None


def test_moderation_is_pending_only_cas_with_admin_selected_group(db):
    from concurrent.futures import ThreadPoolExecutor
    from catix import source_requests as requests
    request = requests.submit("owner", "o@example.org", LINK, "B26", consent=True)
    assert hasattr(requests, "pending_requests"), "moderation API is missing"
    assert requests.pending_requests(offset=0, limit=8) == [request]
    assert requests.pending_requests(offset=1, limit=8) == []
    assert requests.get_request(request["id"]) == request
    assert requests.get_request("f" * 32) is None
    with pytest.raises(ValueError):
        requests.approve(request["id"], 111, "all")
    with ThreadPoolExecutor(6) as pool:
        outcomes = list(pool.map(lambda admin: requests.approve(request["id"], admin, "b27"), range(6)))
    assert sum(outcomes) == 1
    approved = requests.get_request(request["id"])
    assert approved["status"] == "approved" and approved["group_code"] == "B27"
    assert approved["decided_by"] in range(6) and approved["decided_at"]
    assert not requests.reject(request["id"], 111, "No")
    other = requests.submit("other", "other@example.org", LINK, "B26", consent=True)
    assert requests.reject(other["id"], 111, "Not authorized")
    assert requests.get_request(other["id"])["message"] == "Not authorized"
    assert not requests.approve(other["id"], 111, "B26")
    assert requests.pending_requests() == []


def test_http_contract_owner_only_and_verified_group(db, monkeypatch):
    from fastapi.testclient import TestClient
    from catix.api.app import app
    from catix.api.auth import UserTokenData, verify_user
    from catix import groups
    client = TestClient(app)
    assert client.get("/sources/requests").status_code == 401
    assert client.post("/sources/requests", json={}).status_code == 401
    monkeypatch.setattr(groups, "website_groups", lambda token: ["B26"] if token == "owner-token" else [])
    user = UserTokenData(innohassle_id="owner", email="o@example.org", telegram_id=123)
    from pydantic import SecretStr
    user.token = SecretStr("owner-token")
    app.dependency_overrides[verify_user] = lambda: user
    try:
        body = {"invite_link": LINK, "group_code": "B26", "consent": True}
        response = client.post("/sources/requests", json=body)
        assert response.status_code == 201, response.text
        view = response.json()
        assert set(view) == {"id", "group_code", "comment", "status", "message", "title", "created_at"}
        assert view["group_code"] == "B26" and view["comment"] == ""
        assert client.get("/sources/requests").json() == {"requests": [view], "verified_groups": ["B26"]}
        for consent in (False, 1, "true", None):
            assert client.post("/sources/requests", json={**body, "consent": consent}).status_code == 422
        for link in ("http://t.me/+AbCdEfGhIjKlMnOp", LINK + "?x=1", LINK + "/", "https://t.me/ab", "https://t.me.evil/+AbCdEfGhIjKlMnOp", LINK + "\nextra"):
            assert client.post("/sources/requests", json={**body, "invite_link": link}).status_code == 422
        assert client.post("/sources/requests", json={**body, "group_code": "bad group!"}).status_code == 422
        for number in range(4):
            assert client.post("/sources/requests", json={**body, "invite_link": LINK + str(number)}).status_code == 201
        assert client.post("/sources/requests", json={**body, "invite_link": LINK + "999"}).status_code == 429
        user = UserTokenData(innohassle_id="other", email="other@example.org")
        groups.set_user_group("web:other", "B26")
        assert client.get("/sources/requests").json() == {"requests": [], "verified_groups": []}
    finally:
        app.dependency_overrides.pop(verify_user, None)


def approved_request(owner="owner", link=LINK):
    from catix import source_requests as requests
    request = requests.submit(owner, "o@example.org", link, "B26", consent=True)
    assert requests.approve(request["id"], 100, "B26")
    return request


def test_claim_fencing_crash_recovery_and_atomic_activation(db, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from catix import source_requests as requests, userbot_config
    pending = requests.submit("pending", "p@example.org", LINK, "B26", consent=True)
    assert hasattr(requests, "claim"), "durable worker claims are missing"
    assert requests.claim() is None
    approved_request()
    with ThreadPoolExecutor(6) as pool:
        jobs = [job for job in pool.map(lambda _: requests.claim(), range(6)) if job]
    assert len(jobs) == 1
    old = jobs[0]
    assert requests.begin_join(old)
    with db() as conn:
        conn.execute("UPDATE source_requests SET lease_until = now() - interval '1 second'")
        conn.execute("UPDATE source_request_lease SET lease_until = now() - interval '1 second'")
    new = requests.claim()
    assert new["token"] != old["token"] and new["join_started_at"]
    assert not requests.begin_join(new), "a possibly committed join must only be reconciled"
    assert not requests.activate(old, -100123, "Source", None, False)
    assert requests.claim() is None
    invalidations = []
    monkeypatch.setattr(userbot_config, "_forget", lambda: invalidations.append(True))
    assert requests.activate(new, -100123, "Source", None, False)
    assert invalidations == [True]
    with db() as conn:
        chat = conn.execute("SELECT * FROM chats WHERE chat_id = -100123").fetchone()
        assert chat["group_code"] == "B26" and chat["requires_verified_group"] is True
        assert conn.execute("SELECT reader FROM userbot_listen WHERE chat_id = -100123").fetchone()["reader"] == "userbot"
    assert -100123 in userbot_config.userbot_reads()
    assert requests.get_request(new["id"])["status"] == "connected"
    assert requests.get_request(pending["id"])["status"] == "pending"
    assert requests.backfill_pending() == {-100123}
    requests.backfill_done(-100123)
    assert requests.backfill_pending() == set()


@pytest.mark.parametrize("existing", ["chat", "listener", "resolved"])
def test_existing_chat_never_reassigned_or_broadened(db, existing):
    from catix import source_requests as requests
    if existing == "resolved":
        approved_request("first", LINK + "a")
        assert requests.activate(requests.claim(), -100123, "Original", None, True)
    else:
        with db() as conn:
            if existing == "chat":
                conn.execute("INSERT INTO chats (chat_id, title, group_code) VALUES (-100123, 'Original', 'B99')")
            conn.execute("INSERT INTO userbot_listen (chat_id, topic_ids, reader) VALUES (-100123, '{7}', 'search')")
    with db() as conn:
        before = conn.execute("SELECT * FROM chats").fetchall(), conn.execute("SELECT * FROM userbot_listen").fetchall()
    approved_request("second", LINK + "b")
    job = requests.claim()
    assert requests.activate(job, -100123, "Replacement", "new", False) is False
    with db() as conn:
        assert (conn.execute("SELECT * FROM chats").fetchall(), conn.execute("SELECT * FROM userbot_listen").fetchall()) == before
    result = requests.get_request(job["id"])
    assert result["status"] == "failed" and "manual" in result["message"].lower()


def test_worker_only_joins_approved_then_verifies_membership(db):
    import asyncio
    from types import SimpleNamespace
    from telethon.tl import types
    from telethon.tl.functions.messages import CheckChatInviteRequest, ImportChatInviteRequest
    from catix import source_requests as requests
    assert importlib.util.find_spec("catix.tguserbot.source_requests"), "Telegram source worker is missing"
    from catix.tguserbot import source_requests as worker
    chat = types.Chat(123, "New source", types.ChatPhotoEmpty(), 1, None, 1)
    calls = []
    async def client(request, **kwargs):
        assert kwargs.get("flood_sleep_threshold") == 0
        calls.append(type(request))
        if isinstance(request, ImportChatInviteRequest):
            assert requests.list_owned("owner")[0]["join_started_at"] is not None
            return SimpleNamespace(chats=[chat])
        assert isinstance(request, CheckChatInviteRequest)
        if ImportChatInviteRequest in calls:
            return types.ChatInviteAlready(chat)
        return types.ChatInvite("New source", types.PhotoEmpty(1), 1, 0)
    pending = requests.submit("owner", "o@example.org", LINK, "B26", consent=True)
    assert asyncio.run(worker.process_one(client)) is False
    assert calls == []
    requests.approve(pending["id"], 1, "B26")
    assert asyncio.run(worker.process_one(client)) is True
    assert calls == [CheckChatInviteRequest, ImportChatInviteRequest, CheckChatInviteRequest]
    assert requests.get_request(pending["id"])["status"] == "connected"


@pytest.mark.parametrize("delete_first", [False, True])
def test_cross_owner_uncertain_join_only_reconciles_same_invite(db, delete_first):
    import asyncio
    from telethon.tl import types
    from telethon.tl.functions.messages import CheckChatInviteRequest, ImportChatInviteRequest
    from catix import source_requests as requests
    from catix.tguserbot import source_requests as worker

    first = approved_request("first")
    second = requests.submit("second", "s@example.org", LINK.replace("/+", "/joinchat/"), "B27", consent=True)
    assert requests.approve(second["id"], 100, "B27")
    assert first["id"] != second["id"]
    assert requests.list_owned("first")[0]["id"] == first["id"]
    assert requests.list_owned("second")[0]["id"] == second["id"]
    calls = []
    member = False
    chat = types.Chat(123, "Shared source", types.ChatPhotoEmpty(), 1, None, 1)

    async def client(request, **kwargs):
        calls.append(type(request))
        if isinstance(request, ImportChatInviteRequest):
            raise TimeoutError("Uncertain Telegram write")
        assert isinstance(request, CheckChatInviteRequest)
        return types.ChatInviteAlready(chat) if member else types.ChatInvite("Source", types.PhotoEmpty(1), 1, 0)

    assert asyncio.run(worker.process_one(client))
    first_result = requests.get_request(first["id"])
    assert first_result and first_result["status"] == "waiting_join" and first_result["join_started_at"]
    if delete_first:
        with db() as conn:
            conn.execute("DELETE FROM source_requests WHERE id = %s", (first["id"],))
    assert asyncio.run(worker.process_one(client))
    assert calls == [CheckChatInviteRequest, ImportChatInviteRequest, CheckChatInviteRequest]
    second_result = requests.get_request(second["id"])
    assert second_result and second_result["status"] == "waiting_join"
    assert second_result["join_started_at"] == first_result["join_started_at"]
    with db() as conn:
        assert conn.execute("SELECT count(*) AS n FROM chats").fetchone()["n"] == 0
        conn.execute("UPDATE source_requests SET available_at = now() WHERE id = %s", (second["id"],))
    member = True
    assert asyncio.run(worker.process_one(client))
    second_result = requests.get_request(second["id"])
    assert second_result and second_result["status"] == "connected"
    with db() as conn:
        before = conn.execute("SELECT * FROM chats").fetchall(), conn.execute("SELECT * FROM userbot_listen").fetchall()
        assert before[0][0]["group_code"] == "B27" and before[0][0]["requires_verified_group"]
        if not delete_first:
            conn.execute("UPDATE source_requests SET available_at = now() WHERE id = %s", (first["id"],))
    if not delete_first:
        assert asyncio.run(worker.process_one(client))
        first_result = requests.get_request(first["id"])
        assert first_result and first_result["status"] == "failed"
        with db() as conn:
            assert (conn.execute("SELECT * FROM chats").fetchall(), conn.execute("SELECT * FROM userbot_listen").fetchall()) == before
    assert calls.count(ImportChatInviteRequest) == 1


def test_migration_retains_existing_join_intent_across_owners(db):
    import asyncio
    from telethon.tl import types
    from telethon.tl.functions.messages import CheckChatInviteRequest
    from catix import source_requests as requests
    from catix.tguserbot import source_requests as worker

    first = approved_request("first")
    second = approved_request("second")
    schema = Path(__file__).resolve().parents[1].joinpath("db/schema.sql").read_text().replace("__TZ__", "UTC")
    with db() as conn:
        conn.execute("DROP TABLE source_request_join_intents")
        started = conn.execute(
            """UPDATE source_requests SET join_started_at = now(), status = 'waiting_join',
               available_at = now() + interval '1 day' WHERE id = %s RETURNING join_started_at""", (first["id"],),
        ).fetchone()["join_started_at"]
        conn.execute(schema)
        conn.execute(schema)
        conn.execute("DELETE FROM source_requests WHERE id = %s", (first["id"],))
    calls = []

    async def client(request, **kwargs):
        calls.append(type(request))
        return types.ChatInvite("Source", types.PhotoEmpty(1), 1, 0)

    assert asyncio.run(worker.process_one(client))
    assert calls == [CheckChatInviteRequest]
    result = requests.get_request(second["id"])
    assert result and result["status"] == "waiting_join" and result["join_started_at"] == started


def test_cross_owner_flood_refusal_allows_later_import_but_not_uncertain_retry(db):
    import asyncio
    from telethon import errors
    from telethon.tl import types
    from telethon.tl.functions.messages import CheckChatInviteRequest, ImportChatInviteRequest
    from catix import source_requests as requests
    from catix.tguserbot import source_requests as worker

    first = approved_request("first")
    second = approved_request("second", LINK.replace("/+", "/joinchat/"))
    calls = []
    check_flood = False

    async def client(request, **kwargs):
        calls.append(type(request))
        if isinstance(request, ImportChatInviteRequest):
            if calls.count(ImportChatInviteRequest) == 1:
                raise errors.FloodWaitError(request, capture=180)
            raise TimeoutError("Uncertain Telegram write")
        if check_flood:
            raise errors.FloodWaitError(request, capture=180)
        return types.ChatInvite("Source", types.PhotoEmpty(1), 1, 0)

    assert asyncio.run(worker.process_one(client))
    first_result = requests.get_request(first["id"])
    assert first_result and first_result["join_started_at"] is None
    assert asyncio.run(worker.process_one(client)) is False
    with db() as conn:
        conn.execute("UPDATE source_request_lease SET available_at = now()")
    assert asyncio.run(worker.process_one(client))
    assert calls == [CheckChatInviteRequest, ImportChatInviteRequest, CheckChatInviteRequest, ImportChatInviteRequest]
    second_result = requests.get_request(second["id"])
    assert second_result and second_result["status"] == "waiting_join"
    with db() as conn:
        conn.execute("UPDATE source_requests SET available_at = now() WHERE id = %s", (first["id"],))
    check_flood = True
    assert asyncio.run(worker.process_one(client))
    check_flood = False
    with db() as conn:
        conn.execute("UPDATE source_request_lease SET available_at = now()")
        conn.execute("UPDATE source_requests SET available_at = now() WHERE id = %s", (first["id"],))
    assert asyncio.run(worker.process_one(client))
    assert calls.count(ImportChatInviteRequest) == 2, "a Check FloodWait must not erase another owner's uncertain import"
    first_result = requests.get_request(first["id"])
    assert first_result and first_result["join_started_at"] == second_result["join_started_at"]


@pytest.mark.parametrize("problem", ["pending", "uncertain", "invalid", "flood"])
def test_worker_failure_paths_are_durable_and_never_blindly_rejoin(db, problem, caplog):
    import asyncio
    from telethon import errors
    from telethon.tl import types
    from telethon.tl.functions.messages import CheckChatInviteRequest, ImportChatInviteRequest
    from catix import source_requests as requests
    from catix.tguserbot import source_requests as worker
    approved = approved_request()
    calls = []
    async def client(request, **kwargs):
        calls.append(type(request))
        if isinstance(request, ImportChatInviteRequest):
            if problem == "pending":
                raise errors.InviteRequestSentError(request)
            if problem == "uncertain":
                raise OSError(LINK)
            if problem == "invalid":
                raise errors.InviteHashExpiredError(request)
            raise errors.FloodWaitError(request, capture=180)
        return types.ChatInvite("Source", types.PhotoEmpty(1), 1, 0, request_needed=True)
    asyncio.run(worker.process_one(client))
    row = requests.get_request(approved["id"])
    assert row["status"] == {"pending": "waiting_join", "uncertain": "waiting_join", "invalid": "failed", "flood": "approved"}[problem]
    assert LINK not in caplog.text and "AbCdEfGhIjKlMnOp" not in str(row["message"])
    assert requests.claim() is None
    if problem in ("pending", "uncertain"):
        with db() as conn:
            conn.execute("UPDATE source_requests SET available_at = now()")
        asyncio.run(worker.process_one(client))
        assert calls.count(ImportChatInviteRequest) == 1
        assert calls.count(CheckChatInviteRequest) == 2
        with db() as conn:
            assert conn.execute("SELECT count(*) AS n FROM chats").fetchone()["n"] == 0
    if problem == "flood":
        assert row["join_started_at"] is None
        approved_request("second", LINK + "x")
        assert requests.claim() is None, "FloodWait must pause all source joins, not just one request"


@pytest.mark.parametrize("error_name", ["ChannelsTooMuchError", "UsersTooMuchError", "UserBannedInChannelError"])
def test_definite_join_refusals_show_failure_instead_of_waiting_forever(db, error_name):
    import asyncio
    from telethon import errors
    from telethon.tl import types
    from telethon.tl.functions.messages import ImportChatInviteRequest
    from catix import source_requests as requests
    from catix.tguserbot import source_requests as worker

    approved = approved_request()
    async def client(request, **kwargs):
        if isinstance(request, ImportChatInviteRequest):
            raise getattr(errors, error_name)(request)
        return types.ChatInvite("Source", types.PhotoEmpty(1), 1, 0)
    asyncio.run(worker.process_one(client))
    row = requests.get_request(approved["id"])
    assert row["status"] == "failed"
    assert "administrator" in row["message"].lower()
    assert requests.claim() is None


def test_protected_scope_requires_verified_matching_non_all_group(db, monkeypatch):
    from catix import groups
    with db() as conn:
        conn.execute("""INSERT INTO chats (chat_id, title, group_code, requires_verified_group) VALUES
            (1, 'Public', 'all', false), (2, 'Legacy', 'B26', false),
            (3, 'Protected', 'B26', true), (4, 'Other', 'B27', true), (5, 'Protected public', 'all', true)""")
    groups.set_user_group("tg:7", "B26")
    monkeypatch.setattr(groups, "auto_group", lambda tg: None)
    assert groups.scoped_chat_ids("tg:7", 7) == {1, 2}
    monkeypatch.setattr(groups, "auto_group", lambda tg: "B26")
    assert groups.scoped_chat_ids("tg:7", 7) == {1, 2, 3}
    monkeypatch.setattr(groups, "auto_group", lambda tg: "B27")
    assert groups.scoped_chat_ids("tg:7", 7) == {1, 4}
    monkeypatch.setattr(groups, "auto_group", lambda tg: "all")
    assert groups.scoped_chat_ids("tg:7", 7) == {1}


def make_change(db, protected=True):
    from catix.worker import changes
    with db() as conn:
        conn.execute("INSERT INTO chats (chat_id, title, group_code, requires_verified_group) VALUES (7, 'Source', 'B26', %s)", (protected,))
        message = conn.execute("INSERT INTO messages (chat_id, msg_id, date, text) VALUES (7, 1, now(), 'Private schedule') RETURNING id").fetchone()["id"]
        conn.execute("""INSERT INTO schedule_changes (message_id, kind, subject, starts_at, all_day, summary)
            VALUES (%s, 'announcement', 'Private event', now() + interval '1 day', true, 'Private event')""", (message,))
    return changes.unnotified()[0]


def test_notifications_do_not_leak_protected_source_to_manual_group(db, monkeypatch):
    from catix import groups, bot_users
    from catix.worker import changes
    change = make_change(db)
    groups.set_user_group("tg:1", "B26")
    monkeypatch.setattr(bot_users, "reachable", lambda: [1, 2, 3])
    monkeypatch.setattr(groups, "auto_group", lambda tg: {2: "B26", 3: "B27"}.get(tg))
    assert changes.recipients(change) == [2]
    with db() as conn:
        conn.execute("UPDATE chats SET group_code = 'all'")
    assert changes.recipients(changes.unnotified()[0]) == []
    with db() as conn:
        conn.execute("UPDATE chats SET group_code = 'B26', requires_verified_group = false")
    assert changes.recipients(changes.unnotified()[0]) == [1, 2]


def test_guessed_change_id_cannot_copy_private_text_to_calendar(db, monkeypatch):
    from catix import groups
    from catix.worker import changes
    change = make_change(db)
    monkeypatch.setattr(groups, "auto_group", lambda tg: "B26" if tg == 123 else None)
    groups.set_user_group("ino:owner", "B26")
    assert changes.add_to_calendar("ino:owner", change.id) is None
    with db() as conn:
        assert conn.execute("SELECT count(*) AS n FROM personal_events WHERE user_key = 'ino:owner'").fetchone()["n"] == 0
    assert changes.add_to_calendar("ino:owner", change.id, telegram_id=123)
    with db() as conn:
        assert conn.execute("SELECT source_note FROM personal_events WHERE user_key = 'ino:owner'").fetchone()["source_note"]


def test_calendar_callback_passes_authenticated_telegram_id(monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from catix.tgbot import bot
    seen = []
    monkeypatch.setattr(bot.personal_calendar, "telegram_key", lambda tg: "ino:owner")
    monkeypatch.setattr(bot.changes, "add_to_calendar", lambda key, id, **kwargs: seen.append((key, id, kwargs)))
    query = SimpleNamespace(data="chg:ok:123", from_user=SimpleNamespace(id=456), answer=AsyncMock(), message=None)
    asyncio.run(bot.decide_change(query))
    assert seen == [("ino:owner", 123, {"telegram_id": 456})]


def test_connected_source_backfills_on_startup_and_preserves_access(db, monkeypatch):
    import asyncio
    from datetime import datetime, timezone
    from telethon.tl import types
    from catix import source_requests as requests
    from catix.tguserbot import userbot
    approved_request()
    assert requests.activate(requests.claim(), -123, "Source", None, False)
    chat = types.Chat(123, "Source", types.ChatPhotoEmpty(), 1, None, 1)
    class Client:
        async def get_entity(self, id):
            return chat
        async def iter_messages(self, entity, **kwargs):
            yield types.Message(id=1, peer_id=types.PeerChat(123), date=datetime.now(timezone.utc), message="The important examination starts tomorrow at noon in room 301.")
    monkeypatch.setattr(userbot, "POLL_SECONDS", .01)
    async def scenario():
        task = asyncio.create_task(userbot._follow_choice(Client(), {}))
        try:
            for _ in range(20):
                await asyncio.sleep(.01)
                if not requests.backfill_pending():
                    break
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    asyncio.run(scenario())
    with db() as conn:
        assert conn.execute("SELECT count(*) AS n FROM messages WHERE chat_id = -123").fetchone()["n"] == 1
        chat_row = conn.execute("SELECT * FROM chats WHERE chat_id = -123").fetchone()
        assert chat_row["group_code"] == "B26" and chat_row["requires_verified_group"]
        assert conn.execute("SELECT count(*) AS n FROM embedding_queue").fetchone()["n"] == 1
    assert requests.backfill_pending() == set()


def test_worker_lifecycle_cancels_before_client_disconnect(monkeypatch):
    import asyncio
    from unittest.mock import AsyncMock
    from catix.tguserbot import userbot, source_requests as worker
    events = []
    options = {}
    async def parked(*args, **kwargs):
        await asyncio.Event().wait()
    async def process(client):
        events.append("started")
        try:
            await asyncio.Event().wait()
        finally:
            events.append("cancelled")
    monkeypatch.setattr(worker, "process_one", process)
    for name in ("_publish_dialogs", "_seed"):
        monkeypatch.setattr(userbot, name, AsyncMock())
    for name in ("_follow_choice", "_serve_search", "_heartbeat"):
        monkeypatch.setattr(userbot, name, parked)
    monkeypatch.setattr(userbot.images, "run", parked)
    class Client:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            events.append("disconnected")
        async def start(self):
            pass
        def add_event_handler(self, *args):
            pass
        async def run_until_disconnected(self):
            await asyncio.sleep(.01)
    monkeypatch.setattr(userbot, "_client", lambda **kwargs: (options.update(kwargs), Client())[1])
    asyncio.run(userbot._listen_once())
    assert events == ["started", "cancelled", "disconnected"]
    assert options["request_retries"] == 0, "Telethon must not silently repeat an uncertain join write"


def test_terminal_duplicate_returns_conflict_not_false_submission_success(db, monkeypatch):
    from fastapi.testclient import TestClient
    from catix import groups, source_requests as requests
    from catix.api.app import app
    from catix.api.auth import UserTokenData, verify_user
    monkeypatch.setattr(groups, "website_groups", lambda _: ["B26"])
    request = requests.submit("owner", "o@example.org", LINK, "B26", consent=True)
    requests.reject(request["id"], 1, "Not authorized")
    app.dependency_overrides[verify_user] = lambda: UserTokenData(innohassle_id="owner", email="o@example.org")
    try:
        body = {"invite_link": LINK, "group_code": "B26", "consent": True}
        client = TestClient(app)
        response = client.post("/sources/requests", json=body)
        assert response.status_code == 409
        assert "existing" in response.json()["detail"].lower()
        assert client.post("/sources/requests", json={**body, "invite_link": LINK + "new"}).status_code == 201
    finally:
        app.dependency_overrides.pop(verify_user, None)


def test_protected_chat_migration_fails_closed_instead_of_resetting_policy(db):
    from catix.db import store
    with db() as conn:
        conn.execute("INSERT INTO chats (chat_id, title, group_code, requires_verified_group) VALUES (-123, 'Private', 'B26', true)")
        conn.execute("INSERT INTO messages (chat_id, msg_id, date, text) VALUES (-123, 1, now(), 'Private history')")
    with pytest.raises(ValueError, match="manual"):
        store.migrate_chat(-123, -100123)
    with db() as conn:
        assert conn.execute("SELECT chat_id FROM messages").fetchone()["chat_id"] == -123
        assert not conn.execute("SELECT 1 FROM chats WHERE chat_id = -100123").fetchone()


def test_refused_migration_does_not_redirect_future_private_messages(db, monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from catix.tgbot import bot
    with db() as conn:
        conn.execute("INSERT INTO chats (chat_id, title, group_code, requires_verified_group) VALUES (-123, 'Private', 'B26', true)")
    monkeypatch.setattr(bot, "MIGRATED", {})
    monkeypatch.setattr(bot.writer, "wait_idle", AsyncMock())
    message = SimpleNamespace(chat=SimpleNamespace(id=-123), migrate_to_chat_id=-100123)
    with pytest.raises(ValueError, match="manual"):
        asyncio.run(bot.chat_migrated(message))
    assert bot.MIGRATED == {}


def test_deleted_claim_does_not_release_account_lease_or_stale_token(db):
    from catix import source_requests as requests
    first = approved_request()
    old = requests.claim()
    second = approved_request("second", LINK + "b")
    with db() as conn:
        conn.execute("DELETE FROM source_requests WHERE id = %s", (first["id"],))
    assert requests.claim() is None
    assert not requests.defer(old, "stale")
    with db() as conn:
        conn.execute("UPDATE source_request_lease SET lease_until = now() - interval '1 second'")
    new = requests.claim()
    assert new["id"] == second["id"]
    assert not requests.defer(old, "stale", flood=True)
    assert not requests.activate(old, -123, "stale", None, False)
    assert requests.claim() is None
    assert requests.activate(new, -123, "Current", None, False)


def test_cancelled_join_reconciles_after_restart_without_second_import(db):
    import asyncio
    from telethon.tl import types
    from telethon.tl.functions.messages import ImportChatInviteRequest
    from catix import source_requests as requests
    from catix.tguserbot import source_requests as worker
    first = approved_request()
    joins = []
    joined = False
    async def client(request, **kwargs):
        nonlocal joined
        if isinstance(request, ImportChatInviteRequest):
            joins.append(request)
            joined = True
            raise asyncio.CancelledError
        if joined:
            return types.ChatInviteAlready(types.Chat(123, "Source", types.ChatPhotoEmpty(), 1, None, 1))
        return types.ChatInvite("Source", types.PhotoEmpty(1), 1, 0)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(worker.process_one(client))
    row = requests.get_request(first["id"])
    assert row["join_started_at"] and row["status"] == "joining"
    with db() as conn:
        conn.execute("UPDATE source_request_lease SET lease_until = now() - interval '1 second'")
        conn.execute("UPDATE source_requests SET lease_until = now() - interval '1 second'")
    asyncio.run(worker.process_one(client))
    assert len(joins) == 1
    assert requests.get_request(first["id"])["status"] == "connected"


def test_backfill_cancellation_leaves_durable_work_for_restart(db, monkeypatch):
    import asyncio
    from telethon.tl import types
    from catix import source_requests as requests
    from catix.tguserbot import userbot
    approved_request()
    requests.activate(requests.claim(), -123, "Source", None, False)
    stopped = []
    async def scenario():
        started = asyncio.Event()
        async def sync(*args, **kwargs):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                stopped.append(True)
        monkeypatch.setattr(userbot, "_sync_chat", sync)
        class Client:
            async def get_entity(self, id):
                return types.Chat(123, "Source", types.ChatPhotoEmpty(), 1, None, 1)
        task = asyncio.create_task(userbot._follow_choice(Client(), {}))
        await asyncio.wait_for(started.wait(), 1)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        assert stopped == [True]
    asyncio.run(scenario())
    assert requests.backfill_pending() == {-123}


def test_topic_change_during_source_backfill_is_not_lost(db, monkeypatch):
    import asyncio
    from telethon.tl import types
    from catix import source_requests as requests, userbot_config
    from catix.tguserbot import userbot
    approved_request()
    requests.activate(requests.claim(), -123, "Source", None, False)
    choice = [1]
    seen = []
    monkeypatch.setattr(userbot, "POLL_SECONDS", .001)
    monkeypatch.setattr(userbot_config, "userbot_reads", lambda: {-123: choice.copy()})
    monkeypatch.setattr(userbot_config, "storage_fingerprints", lambda: {-123: tuple(choice)})
    async def scenario():
        started, release = asyncio.Event(), asyncio.Event()
        async def sync(client, entity, topics, **kwargs):
            seen.append(topics)
            if len(seen) == 1:
                started.set()
                await release.wait()
            return "Done"
        monkeypatch.setattr(userbot, "_sync_chat", sync)
        class Client:
            async def get_entity(self, id):
                return types.Chat(123, "Source", types.ChatPhotoEmpty(), 1, None, 1)
        task = asyncio.create_task(userbot._follow_choice(Client(), {}))
        try:
            await asyncio.wait_for(started.wait(), 1)
            choice[:] = [2]
            await asyncio.sleep(.03)
            release.set()
            for _ in range(20):
                await asyncio.sleep(.01)
                if len(seen) == 2:
                    break
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    asyncio.run(scenario())
    assert seen == [[1], [2]]


@pytest.mark.parametrize(("raw", "canonical"), [
    ("https://t.me/UniversityInnopolis", "https://t.me/universityinnopolis"),
    ("t.me/UniversityInnopolis", "https://t.me/universityinnopolis"),
    ("https://t.me/+AbCdEfGhIjKlMnOp", "https://t.me/+AbCdEfGhIjKlMnOp"),
    ("t.me/+AbCdEfGhIjKlMnOp", "https://t.me/+AbCdEfGhIjKlMnOp"),
    ("https://t.me/joinchat/AbCdEfGhIjKlMnOp", "https://t.me/+AbCdEfGhIjKlMnOp"),
    ("t.me/joinchat/AbCdEfGhIjKlMnOp", "https://t.me/+AbCdEfGhIjKlMnOp"),
    ("  t.me/UniversityInnopolis  ", "https://t.me/universityinnopolis"),
    ("max.ru/UniversityInnopolis", "https://max.ru/UniversityInnopolis"),
    (" https://max.ru/join/AbCd_123-xyz ", "https://max.ru/join/AbCd_123-xyz"),
])
def test_public_and_private_links_normalize_to_canonical_https(raw, canonical):
    from catix import source_requests as requests
    assert requests.normalize_link(raw) == canonical


@pytest.mark.parametrize("raw", [
    "http://t.me/universityinnopolis", "https://t.me/user?x=1", "https://t.me/user#x",
    "https://name@t.me/user", "https://evil.example/user", "https://t.me/user/123",
    "https://t.me/joinchat", "https://t.me/Share",
    "https://t.me/1abcde", "https://t.me/ab", "https://t.me/user.",
    "https://t.me/%75ser",
    "http://max.ru/channel", "https://max.ru/join", "https://max.ru/join/",
    "https://max.ru/channel?x=1", "https://max.ru/channel#x", "https://max.ru/channel/123",
    "https://max.ru@evil.test/channel", "https://max.ru.evil.test/channel",
    "https://max.ru/%63hannel", "https://max.ru/канал", "https://max.ru:443/channel",
    "https://max.ru/" + "a" * 129,
])
def test_source_link_normalizer_rejects_noncanonical_or_reserved_links(raw):
    from catix import source_requests as requests
    with pytest.raises(ValueError):
        requests.normalize_link(raw)


@pytest.mark.parametrize("username", [
    "joinchat", "share", "proxy", "socks", "login", "confirmphone", "setlanguage",
    "addstickers", "addemoji", "addtheme", "bg", "invoice", "giftcode", "addlist",
    "boost", "contact",
])
def test_reserved_telegram_actions_are_not_public_usernames(username):
    from catix import source_requests as requests
    with pytest.raises(ValueError):
        requests.normalize_link(f"https://t.me/{username.title()}")


def test_public_api_store_moderation_and_worker_activation(db, monkeypatch):
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from fastapi.testclient import TestClient
    from telethon.tl import types
    from telethon.tl.functions.channels import JoinChannelRequest

    from catix import groups, source_requests as requests
    from catix.api.app import app
    from catix.api.auth import UserTokenData, verify_user
    from catix.tgbot import source_requests as moderation
    from catix.tguserbot import source_requests as worker

    monkeypatch.setattr(groups, "website_groups", lambda _: pytest.fail("all audience needs no study-group verification"))
    monkeypatch.setattr(moderation.changes, "admins", lambda: [7])
    app.dependency_overrides[verify_user] = lambda: UserTokenData(innohassle_id="public-owner", email="owner@example.org")
    try:
        client = TestClient(app)
        submitted = client.post("/sources/requests", json={"invite_link": "t.me/UniversityInnopolis", "group_code": "all", "consent": True})
        assert submitted.status_code == 201, submitted.text
        assert submitted.json()["status"] == "pending"
        assert requests.get_request(submitted.json()["id"])["invite_link"] == "https://t.me/universityinnopolis"
        assert requests.claim() is None
        callback = SimpleNamespace(
            data=f"sr:approve:{submitted.json()['id']}", from_user=SimpleNamespace(id=7), answer=AsyncMock(),
            message=SimpleNamespace(chat=SimpleNamespace(type="private"), edit_text=AsyncMock()),
        )
        asyncio.run(moderation.request_callback(callback))
        assert requests.get_request(submitted.json()["id"])["status"] == "approved"

        channel = types.Channel(456, "University Innopolis", types.ChatPhotoEmpty(), None, megagroup=True, access_hash=12345, username="universityinnopolis")
        calls = []
        joined = False
        class Telegram:
            async def get_entity(self, username):
                assert username == "universityinnopolis"
                return channel
            async def __call__(self, request, **kwargs):
                nonlocal joined
                calls.append(type(request))
                if isinstance(request, JoinChannelRequest):
                    assert requests.get_request(submitted.json()["id"])["join_started_at"] is not None
                    joined = True
                    return SimpleNamespace(chats=[channel], users=[])
                if type(request).__name__ == "GetParticipantRequest":
                    if not joined:
                        from telethon.errors import UserNotParticipantError
                        raise UserNotParticipantError(request)
                    return SimpleNamespace(participant=types.ChannelParticipantSelf(1, 2, None))
                raise AssertionError(f"unexpected RPC: {request!r}")
        telegram = Telegram()
        assert asyncio.run(worker.process_one(telegram))
        stored = requests.get_request(submitted.json()["id"])
        assert stored["status"] == "connected" and stored["chat_id"] == -1000000000456, stored["message"]
        assert calls.count(JoinChannelRequest) == 1
        with db() as conn:
            chat = conn.execute("SELECT * FROM chats WHERE chat_id = %s", (stored["chat_id"],)).fetchone()
            assert chat["group_code"] == "all" and chat["requires_verified_group"] is False
    finally:
        app.dependency_overrides.pop(verify_user, None)


@pytest.mark.parametrize("participant_kind", ["left", "banned"])
def test_public_worker_does_not_activate_left_or_banned_participant(db, participant_kind):
    import asyncio
    from types import SimpleNamespace
    from telethon.tl import types
    from telethon.tl.functions.channels import JoinChannelRequest
    from catix import source_requests as requests
    from catix.tguserbot import source_requests as worker

    request = requests.submit("public-owner", "owner@example.org", "t.me/PublicChannel", "all", consent=True)
    requests.approve(request["id"], 7, "all")
    channel = types.Channel(457, "Public channel", types.ChatPhotoEmpty(), None, megagroup=True, access_hash=12346, username="publicchannel")
    joined = False
    calls = []
    class Telegram:
        async def get_entity(self, username):
            return channel
        async def __call__(self, rpc, **kwargs):
            nonlocal joined
            calls.append(type(rpc))
            if isinstance(rpc, JoinChannelRequest):
                assert requests.get_request(request["id"])["join_started_at"] is not None
                joined = True
                return SimpleNamespace(chats=[channel])
            if participant_kind == "left":
                participant = types.ChannelParticipantLeft(types.PeerUser(7))
            else:
                participant = types.ChannelParticipantBanned(
                    types.PeerUser(7), 1, None, types.ChatBannedRights(until_date=None, view_messages=True), left=True,
                )
            return SimpleNamespace(participant=participant)

    assert asyncio.run(worker.process_one(Telegram()))
    result = requests.get_request(request["id"])
    assert result["status"] == "waiting_join"
    assert result["join_started_at"] is not None
    assert calls.count(JoinChannelRequest) == 1
    with db() as conn:
        assert conn.execute("SELECT count(*) AS n FROM chats").fetchone()["n"] == 0


@pytest.mark.parametrize("resolution_error", ["value", "invalid", "unoccupied"])
def test_public_worker_marks_missing_username_failed_without_join(db, resolution_error):
    import asyncio
    from telethon import errors
    from telethon.tl.functions.channels import JoinChannelRequest
    from catix import source_requests as requests
    from catix.tguserbot import source_requests as worker

    request = requests.submit("public-owner", "owner@example.org", "t.me/MissingChannel", "all", consent=True)
    requests.approve(request["id"], 7, "all")
    class Telegram:
        async def get_entity(self, username):
            if resolution_error == "value":
                raise ValueError("No user has 'missingchannel' as username")
            err = errors.UsernameInvalidError if resolution_error == "invalid" else errors.UsernameNotOccupiedError
            raise err(None)
        async def __call__(self, rpc, **kwargs):
            assert not isinstance(rpc, JoinChannelRequest)
            raise AssertionError("resolution failure must precede all join RPCs")

    assert asyncio.run(worker.process_one(Telegram()))
    result = requests.get_request(request["id"])
    assert result["status"] == "failed" and result["join_started_at"] is None


def test_public_worker_rejects_user_entities_without_join(db):
    import asyncio
    from telethon.tl import types
    from telethon.tl.functions.channels import JoinChannelRequest
    from catix import source_requests as requests
    from catix.tguserbot import source_requests as worker

    request = requests.submit("public-owner", "owner@example.org", "t.me/SomeBot", "all", consent=True)
    requests.approve(request["id"], 7, "all")
    class Telegram:
        async def get_entity(self, username):
            return types.User(99, bot=True, first_name="Bot")
        async def __call__(self, rpc, **kwargs):
            assert not isinstance(rpc, JoinChannelRequest)
            raise AssertionError("a resolved user must never be joined or activated")

    assert asyncio.run(worker.process_one(Telegram()))
    result = requests.get_request(request["id"])
    assert result["status"] == "failed" and result["join_started_at"] is None


def test_public_uncertain_join_is_reconciled_without_repeating_write(db):
    import asyncio
    from types import SimpleNamespace
    from telethon.tl import types
    from telethon.tl.functions.channels import JoinChannelRequest
    from catix import source_requests as requests
    from catix.tguserbot import source_requests as worker

    request = requests.submit("public-owner", "owner@example.org", "t.me/RetryChannel", "all", consent=True)
    requests.approve(request["id"], 7, "all")
    channel = types.Channel(458, "Retry channel", types.ChatPhotoEmpty(), None, megagroup=True, access_hash=12347, username="retrychannel")
    joined = False
    calls = []
    class Telegram:
        async def get_entity(self, username):
            return channel
        async def __call__(self, rpc, **kwargs):
            nonlocal joined
            calls.append(type(rpc))
            if isinstance(rpc, JoinChannelRequest):
                assert requests.get_request(request["id"])["join_started_at"] is not None
                joined = True
                raise TimeoutError("uncertain public join")
            if not joined:
                from telethon.errors import UserNotParticipantError
                raise UserNotParticipantError(rpc)
            return SimpleNamespace(participant=types.ChannelParticipantSelf(1, 2, None))

    telegram = Telegram()
    assert asyncio.run(worker.process_one(telegram))
    pending = requests.get_request(request["id"])
    assert pending["status"] == "waiting_join" and pending["join_started_at"]
    with db() as conn:
        conn.execute("UPDATE source_requests SET available_at = now() WHERE id = %s", (request["id"],))
    assert asyncio.run(worker.process_one(telegram))
    assert requests.get_request(request["id"])["status"] == "connected"
    assert calls.count(JoinChannelRequest) == 1


@pytest.mark.parametrize("audience", ["B26", "all"])
def test_max_proposal_is_record_only_until_separate_manual_catalog_confirmation(db, monkeypatch, audience):
    import asyncio
    from datetime import datetime, timezone
    from fastapi.testclient import TestClient
    from catix import groups, source_requests as requests
    from catix.api.app import app
    from catix.api.auth import UserTokenData, verify_user
    from catix.maxuserbot import state
    from catix.maxuserbot.models import db_chat_id
    from catix.tguserbot import source_requests as worker

    link = "https://max.ru/join/AbCd_private-123"
    raw_id = -456
    chat_id = db_chat_id(raw_id)
    state.upsert_catalog([{"raw_chat_id": raw_id, "kind": "chat", "title": "MAX source", "link": None}],
                         observed_at=datetime.now(timezone.utc))
    original = state.get_source(chat_id)
    client = TestClient(app)
    monkeypatch.setattr(groups, "website_groups", lambda _: ["B26"])
    app.dependency_overrides[verify_user] = lambda: UserTokenData(innohassle_id="owner", email="o@example.org")
    try:
        created = client.post("/sources/requests", json={"invite_link": link, "group_code": audience, "consent": True})
        assert created.status_code == 201
        request_id = created.json()["id"]
        assert created.json()["status"] == "pending"
        assert requests.get_request(request_id) in requests.pending_requests()
        assert requests.claim() is None
        assert requests.approve(request_id, 7, audience)
        assert not requests.approve(request_id, 7, audience)
        assert state.get_source(chat_id) == original

        class NoJoin:
            async def __call__(self, *args, **kwargs):
                pytest.fail("A MAX proposal must never cause a Telegram join or membership RPC")

        assert asyncio.run(worker.process_one(NoJoin())) is False
        approved = client.get("/sources/requests").json()["requests"][0]
        assert approved["status"] == "approved"
        assert "manual" in approved["message"].lower()
        assert "does not join or enable" in approved["message"]
        assert "invite_link" not in approved
        assert requests.backfill_pending() == set()
        assert groups.website_chat_ids(["B26"]) == set()

        # Discovery and fresh access do not accept the proposal's audience or enable it.
        with db() as conn:
            conn.execute("TRUNCATE max_account")
        state.account_connected(12345)
        state.apply_access(chat_id, generation=original["generation"], access="ready",
                           observed_at=datetime.now(timezone.utc))
        ready = state.get_source(chat_id)
        assert ready["enabled"] is False and ready["group_code"] == groups.ALL
        assert ready["requires_verified_group"] is True
        state.save_configuration(chat_id, "B26", enabled=True,
                                 expected_version=ready["config_version"], expected_generation=ready["generation"])
        enabled = state.get_source(chat_id)
        assert enabled["enabled"] is True and enabled["history_status"] == "pending"
        assert enabled["group_code"] == "B26" and enabled["requires_verified_group"] is True
        assert groups.website_chat_ids([]) == set()
        assert groups.website_chat_ids(["B26"]) == {chat_id}
        assert requests.get_request(request_id)["status"] == "approved"
        assert requests.get_request(request_id)["chat_id"] is None
        assert requests.backfill_pending() == set()
        with db() as conn:
            assert not conn.execute("SELECT 1 FROM userbot_listen").fetchone()
            assert not conn.execute("SELECT 1 FROM userbot_dialogs").fetchone()
            assert not conn.execute("SELECT 1 FROM source_request_join_intents").fetchone()
    finally:
        app.dependency_overrides.pop(verify_user, None)


@pytest.mark.parametrize("status", ["approved", "joining", "waiting_join", "connected"])
def test_max_proposal_records_never_enter_telegram_claims_or_backfills(db, status):
    from catix import source_requests as requests

    row = requests.submit("max-owner", "max@example.org", "https://max.ru/StudyGroup", "B26", consent=True)
    with db() as conn:
        conn.execute("UPDATE source_requests SET status=%s, chat_id=%s, backfill_pending=true WHERE id=%s",
                     (status, 2 * 10**15 - 456, row["id"]))
    assert requests.claim() is None
    viewed = requests.get_request(row["id"])
    assert viewed["status"] == status
    assert "MAX catalog" in viewed["message"]
    if status in {"joining", "waiting_join", "connected"}:
        assert "legacy" in viewed["message"] and "not an active userbot connection" in viewed["message"]
    assert requests.list_owned("max-owner") == [viewed]
    assert requests.submit("max-owner", "max@example.org", "https://max.ru/StudyGroup", "B26", consent=True) == viewed
    with db() as conn:
        saved = conn.execute("SELECT * FROM source_requests WHERE id=%s", (row["id"],)).fetchone()
        assert saved["status"] == status and saved["message"] is None
    assert requests.backfill_pending() == set()
    telegram = approved_request()
    job = requests.claim()
    assert job["id"] == telegram["id"]
    assert requests.activate(job, -123, "Telegram source", None, False)
    assert requests.backfill_pending() == {-123}
    assert requests.get_request(row["id"])["status"] == status


def test_stale_max_lease_cannot_join_activate_or_change_a_proposal(db):
    from catix import source_requests as requests

    row = requests.submit("owner", "o@example.org", "https://max.ru/StudyGroup", "B26", consent=True)
    token = "old-max-worker"
    with db() as conn:
        job = conn.execute("""UPDATE source_requests SET status='joining', token=%s,
                              lease_until=now()+interval '1 minute' WHERE id=%s RETURNING *""",
                           (token, row["id"])).fetchone()
        conn.execute("UPDATE source_request_lease SET token=%s, lease_until=now()+interval '1 minute' WHERE singleton", (token,))
    assert requests.begin_join(job) is False
    assert requests.activate(job, -123, "Not Telegram", None, False) is False
    assert requests.defer(job, "Must not rewrite a MAX proposal") is False
    viewed = requests.get_request(row["id"])
    assert viewed["status"] == job["status"] and viewed["token"] == job["token"]
    with db() as conn:
        assert conn.execute("SELECT * FROM source_requests WHERE id=%s", (row["id"],)).fetchone() == job
        assert not conn.execute("SELECT 1 FROM chats").fetchone()
        assert not conn.execute("SELECT 1 FROM userbot_listen").fetchone()
        assert not conn.execute("SELECT 1 FROM source_request_join_intents").fetchone()


@pytest.mark.parametrize("status", ["pending", "approved", "joining", "waiting_join", "connected"])
def test_max_moderation_dispatcher_exposes_manual_catalog_without_claiming_connection(monkeypatch, status):
    import asyncio
    from copy import deepcopy
    from datetime import datetime, timezone
    from aiogram import Bot, Dispatcher
    from aiogram.client.session.base import BaseSession
    from aiogram.methods import AnswerCallbackQuery, EditMessageText
    from aiogram.types import CallbackQuery, Chat, Message, Update, User
    from catix.tgbot import source_requests as moderation

    request = {"id": "a" * 32, "email": "owner@example.org", "invite_link": "https://max.ru/StudyGroup",
               "group_code": "B26", "comment": "Please review", "status": status,
               "message": "Source enabled for search; history is being indexed." if status == "connected" else None}
    approvals = []
    screens = []
    monkeypatch.setattr(moderation.changes, "admins", lambda: [7])
    monkeypatch.setattr(moderation.store, "get_request", lambda _: dict(request))

    def approve(request_id, admin_id, group_code):
        approvals.append((request_id, admin_id, group_code))
        request["status"] = "approved"
        return True

    monkeypatch.setattr(moderation.store, "approve", approve)

    class Telegram(BaseSession):
        async def close(self):
            pass

        async def stream_content(self, *args, **kwargs):
            raise AssertionError("No media downloads in source moderation")
            yield b""

        async def make_request(self, bot, method, timeout=None):
            if isinstance(method, AnswerCallbackQuery):
                return True
            assert isinstance(method, EditMessageText)
            screens.append(method)
            return Message(message_id=1, date=datetime.now(timezone.utc),
                           chat=Chat(id=7, type="private"), text=method.text)

    async def scenario():
        session = Telegram()
        bot = Bot("123456:TEST_TOKEN", session=session)
        dispatcher = Dispatcher()
        router = deepcopy(moderation.router)
        router._parent_router = None
        dispatcher.include_router(router)
        user = User(id=7, is_bot=False, first_name="Admin")
        message = Message(message_id=1, date=datetime.now(timezone.utc),
                          chat=Chat(id=7, type="private"), from_user=user, text="screen")

        async def press(action, sequence):
            query = CallbackQuery(id=str(sequence), from_user=user, chat_instance="private-test",
                                  message=message, data=f"sr:{action}:{request['id']}")
            await dispatcher.feed_update(bot, Update(update_id=sequence, callback_query=query))

        try:
            await press("show", 1)
            screen = screens[-1]
            assert "вручную" in screen.text and "одобрение не подключает" in screen.text
            assert any(b.callback_data == "mx:list:0" for row in screen.reply_markup.inline_keyboard for b in row)
            assert "Source enabled for search" not in screen.text
            assert "Источник подключён" not in screen.text
            if status == "pending":
                await press("review", 2)
                assert approvals == []
                assert "автоматического вступления нет" in screens[-1].text
                await press("approve", 3)
                assert approvals == [(request["id"], 7, "B26")]
                assert request["status"] == "approved"
                assert any(b.callback_data == "mx:list:0" for row in screens[-1].reply_markup.inline_keyboard for b in row)
        finally:
            await session.close()

    asyncio.run(scenario())
