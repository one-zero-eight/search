import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from catix import personal_calendar
from catix.api import users
from catix.api.auth import TokenAccount, verify_account
from catix.personal_calendar import PersonalEvent
from catix.settings import settings
from catix.db import pg


@pytest.fixture
def client(monkeypatch):
    api = FastAPI()
    api.include_router(users.router)
    api.dependency_overrides[verify_account] = lambda: TokenAccount(innohassle_id="alice")
    monkeypatch.setattr(users.calendar_export, "get_key", lambda owner: None)
    monkeypatch.setattr(users.calendar_export, "create_key", lambda owner: "k" * 43)
    monkeypatch.setattr(users.calendar_export, "revoke_key", lambda owner: None)
    monkeypatch.setattr(users.calendar_export, "owner_for_key", lambda key: "ih:alice" if key == "k" * 43 else None)
    monkeypatch.setattr(users.personal_calendar, "ics", lambda owner, *, include_sources=True: f"ICS:{owner}:{include_sources}")
    return TestClient(api)


def test_export_key_status_get_does_not_create(client, monkeypatch):
    calls = []
    original = users.calendar_export.get_key
    monkeypatch.setattr(users.calendar_export, "get_key", lambda owner: calls.append(owner) or original(owner))
    monkeypatch.setattr(users.calendar_export, "create_key", lambda owner: pytest.fail("GET must not create a key"))
    response = client.get("/users/my-calendar/export-key")
    assert response.status_code == 200 and response.json() == {"access_key": None}
    assert response.headers["cache-control"] == "no-store"
    assert calls == ["ih:alice"]


def test_export_key_create_and_revoke_are_authenticated_and_no_store(client):
    created = client.post("/users/my-calendar/export-key")
    assert created.status_code == 200 and created.json() == {"access_key": "k" * 43}
    assert created.headers["cache-control"] == "no-store"
    revoked = client.delete("/users/my-calendar/export-key")
    assert revoked.status_code == 204 and revoked.headers["cache-control"] == "no-store"


def test_export_key_contract_is_typed_in_openapi(client):
    paths = client.get("/openapi.json").json()["paths"]
    status_schema = paths["/users/my-calendar/export-key"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    create_schema = paths["/users/my-calendar/export-key"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert status_schema != create_schema
    assert "CalendarExportKeyStatus" in str(status_schema)
    assert "CalendarExportKeyCreated" in str(create_schema)


def test_public_export_documents_calendar_and_not_found(client):
    operation = client.get("/openapi.json").json()["paths"]["/users/calendar-export.ics"]["get"]
    assert "text/calendar" in operation["responses"]["200"]["content"]
    assert "404" in operation["responses"]


def test_export_key_routes_require_authentication():
    api = FastAPI()
    api.include_router(users.router)
    client = TestClient(api)
    assert client.get("/users/my-calendar/export-key").status_code == 401
    assert client.post("/users/my-calendar/export-key").status_code == 401
    assert client.delete("/users/my-calendar/export-key").status_code == 401


@pytest.mark.parametrize("key", [None, "", "bad", "a" * 43, "unknown"])
def test_public_export_has_uniform_private_not_found_and_safe_headers(client, key):
    response = client.get("/users/calendar-export.ics", params={} if key is None else {"access_key": key})
    assert response.status_code == 404
    assert response.text == "Calendar not found"
    assert not key or key not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_public_export_uses_only_key_owner_without_sources(client):
    response = client.get("/users/calendar-export.ics", params={"access_key": "k" * 43})
    assert response.status_code == 200
    assert response.text == "ICS:ih:alice:False"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_ics_include_sources_flag_preserves_private_default(monkeypatch):
    rows = [PersonalEvent(7, "Study", datetime(2026, 11, 9, 10, tzinfo=settings.tz), None, False, "108",
                          "https://example.test/source", "private source note")]
    monkeypatch.setattr(users.personal_calendar.pg, "connection", lambda: __import__("contextlib").nullcontext(object()))
    monkeypatch.setattr(users.personal_calendar.pg, "rows", lambda *args: rows)
    private = users.personal_calendar.ics("ih:alice")
    public = users.personal_calendar.ics("ih:alice", include_sources=False)
    assert "X-WR-LINK:https://example.test/source" in private
    assert "URL:https://example.test/source" in private
    assert "DESCRIPTION:private source note" in private
    assert "X-WR-LINK" not in public and "URL:" not in public and "private source note" not in public
    assert "UID:personal-7@ctx" in public and "DTSTART:" in public
    assert "DTEND:" not in public


@pytest.fixture
def export_db(monkeypatch):
    url = os.environ.get("CALENDAR_TEST_DATABASE_URL")
    if not url:
        pytest.skip("CALENDAR_TEST_DATABASE_URL is not set (use disposable PostgreSQL)")
    owner = f"ih:calendar-export-{uuid.uuid4().hex}"
    schema = Path(__file__).parents[1].joinpath("db/schema.sql").read_text()
    ddl = schema[schema.index("CREATE TABLE IF NOT EXISTS personal_events ("):schema.index("-- Events the agent offered")]
    with psycopg.connect(url, row_factory=dict_row, autocommit=True) as conn:
        assert "test" in conn.info.dbname.lower(), "refusing non-test database"
        conn.execute(ddl)
        conn.execute("""CREATE TABLE IF NOT EXISTS calendar_export_keys (
            user_key text PRIMARY KEY, access_key text NOT NULL UNIQUE,
            revoked_at timestamptz, created_at timestamptz NOT NULL DEFAULT now())""")
        conn.execute("DELETE FROM calendar_export_keys WHERE user_key = ANY(%s)", ([owner, owner + "-foreign"],))
        conn.execute("DELETE FROM personal_events WHERE user_key = ANY(%s)", ([owner, owner + "-foreign"],))

    @contextmanager
    def connection():
        with psycopg.connect(url, row_factory=dict_row) as conn:
            yield conn

    monkeypatch.setattr(pg, "connection", connection)
    yield owner
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("DELETE FROM calendar_export_keys WHERE user_key = ANY(%s)", ([owner, owner + "-foreign"],))
        conn.execute("DELETE FROM personal_events WHERE user_key = ANY(%s)", ([owner, owner + "-foreign"],))


def test_sql_export_key_is_owner_scoped_idempotent_and_revocable(export_db):
    owner = export_db
    key = users.calendar_export.create_key(owner)
    assert len(key) == 43 and users.calendar_export.valid_key_shape(key)
    assert users.calendar_export.get_key(owner) == key
    assert users.calendar_export.create_key(owner) == key
    assert users.calendar_export.get_key(owner + "-other") is None
    assert users.calendar_export.owner_for_key(key) == owner
    users.calendar_export.revoke_key(owner)
    users.calendar_export.revoke_key(owner)
    assert users.calendar_export.get_key(owner) is None
    assert users.calendar_export.owner_for_key(key) is None
    replacement = users.calendar_export.create_key(owner)
    assert replacement != key and users.calendar_export.owner_for_key(replacement) == owner
    assert users.calendar_export.owner_for_key(key) is None


def test_sql_concurrent_create_returns_one_durable_secret(export_db):
    with ThreadPoolExecutor(max_workers=8) as pool:
        keys = list(pool.map(lambda _: users.calendar_export.create_key(export_db), range(16)))
    assert len(set(keys)) == 1
    assert users.calendar_export.get_key(export_db) == keys[0]


def test_signed_accounts_manage_only_their_own_subscription(export_db, monkeypatch):
    from catix.innohassle import token as innohassle_token
    from tests.test_calendar_feed import Keys, token

    monkeypatch.setattr(innohassle_token, "_keys", Keys())
    api = FastAPI()
    api.include_router(users.router)
    client = TestClient(api)
    owner = export_db
    mine = {"Authorization": f"Bearer {token(uid=owner.removeprefix('ih:'))}"}
    other = {"Authorization": f"Bearer {token(uid=owner.removeprefix('ih:') + '-foreign')}"}
    assert client.get("/users/my-calendar/export-key", headers=mine).json() == {"access_key": None}
    created = client.post("/users/my-calendar/export-key", headers=mine)
    assert created.status_code == 200
    key = created.json()["access_key"]
    assert client.get("/users/my-calendar/export-key", headers=mine).json() == {"access_key": key}
    assert client.post("/users/my-calendar/export-key", headers=mine).json() == {"access_key": key}
    assert client.get("/users/my-calendar/export-key", headers=other).json() == {"access_key": None}
    assert client.delete("/users/my-calendar/export-key", headers=other).status_code == 204
    assert client.get("/users/calendar-export.ics", params={"access_key": key}).status_code == 200
    assert client.get("/users/my-calendar/export-key", headers={"Authorization": f"Bearer {key}"}).status_code == 401
    assert client.delete("/users/my-calendar/export-key", headers=mine).status_code == 204
    assert client.get("/users/calendar-export.ics", params={"access_key": key}).status_code == 404
    replacement = client.post("/users/my-calendar/export-key", headers=mine).json()["access_key"]
    assert replacement != key
    assert client.get("/users/calendar-export.ics", params={"access_key": key}).status_code == 404
    assert client.get("/users/calendar-export.ics", params={"access_key": replacement}).status_code == 200


def test_public_feed_tracks_sql_edits_deletes_and_hides_provenance(export_db):
    owner = export_db
    key = users.calendar_export.create_key(owner)
    foreign_owner = owner + "-foreign"
    foreign_key = users.calendar_export.create_key(foreign_owner)
    start = datetime(2099, 11, 9, 10, tzinfo=settings.tz)
    with pg.connection() as conn:
        event_id = pg.scalar(conn, """INSERT INTO personal_events
            (user_key,title,starts_at,ends_at,all_day,room,source_url,source_note)
            VALUES (%s,'Original',%s,NULL,false,'108','https://private.example/source','private source note') RETURNING id""",
            (owner, start))
        conn.execute("INSERT INTO personal_events (user_key,title,starts_at) VALUES (%s,'Foreign owner event',%s)", (foreign_owner, start))
    api = FastAPI()
    api.include_router(users.router)
    api.dependency_overrides[verify_account] = lambda: TokenAccount(innohassle_id=owner.removeprefix("ih:"))
    client = TestClient(api)
    private = client.get("/users/my-calendar.ics")
    assert private.status_code == 200 and "X-WR-LINK:https://private.example/source" in private.text
    response = client.get("/users/calendar-export.ics", params={"access_key": key})
    assert response.status_code == 200 and "SUMMARY:Original" in response.text
    assert "UID:personal-" + str(event_id) + "@ctx" in response.text
    assert "X-WR-LINK" not in response.text and "URL:" not in response.text and "private source note" not in response.text
    assert "Foreign owner event" not in response.text
    foreign_feed = client.get("/users/calendar-export.ics", params={"access_key": foreign_key})
    assert foreign_feed.status_code == 200 and "Foreign owner event" in foreign_feed.text and "SUMMARY:Original" not in foreign_feed.text
    assert "DTSTART:20991109T070000Z" in response.text and "DTEND:" not in response.text
    with pg.connection() as conn:
        conn.execute("INSERT INTO personal_events (user_key,title,starts_at,ends_at,all_day) VALUES (%s,'All day',%s,%s,true)",
                     (owner, datetime(2099, 11, 10, 0, tzinfo=settings.tz), datetime(2099, 11, 12, 0, tzinfo=settings.tz)))
    all_day_feed = client.get("/users/calendar-export.ics", params={"access_key": key}).text
    assert "DTSTART;VALUE=DATE:20991110" in all_day_feed
    assert "DTEND;VALUE=DATE:20991112" in all_day_feed
    changed = personal_calendar.update_event(owner, event_id, title="Updated", starts_at=start, all_day=False, room="109")
    assert changed and "SUMMARY:Updated" in client.get("/users/calendar-export.ics", params={"access_key": key}).text
    assert personal_calendar.delete_event(owner, event_id)
    assert "SUMMARY:Updated" not in client.get("/users/calendar-export.ics", params={"access_key": key}).text
    users.calendar_export.revoke_key(owner)
    assert client.get("/users/calendar-export.ics", params={"access_key": key}).status_code == 404


def test_calendar_export_key_cannot_authorize_another_api():
    api = FastAPI()
    api.include_router(users.router)
    client = TestClient(api)
    response = client.get("/users/my-calendar.ics", headers={"Authorization": f"Bearer {'x' * 43}"})
    assert response.status_code == 401


def test_real_uvicorn_access_logs_never_include_calendar_export_queries(monkeypatch, capfd):
    import logging
    import socket
    import threading
    import time

    import httpx
    import uvicorn

    from catix.api.app import app

    monkeypatch.setattr(users.calendar_export, "owner_for_key", lambda key: None)
    server = uvicorn.Server(uvicorn.Config(app, lifespan="off", http="h11"))
    monkeypatch.setattr(logging.getLogger("uvicorn.access"), "propagate", True)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 5
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert server.started
            port = sock.getsockname()[1]
            for query in ("access_key=INVALID_QUERY_SENTINEL", f"access_key={'Q' * 43}"):
                response = httpx.get(f"http://127.0.0.1:{port}/users/calendar-export.ics?{query}")
                assert response.status_code == 404
        finally:
            server.should_exit = True
            thread.join(timeout=5)
        assert not thread.is_alive()
    output = "".join(capfd.readouterr())
    assert output.count('"GET /users/calendar-export.ics HTTP/1.1" 404') >= 2
    assert "INVALID_QUERY_SENTINEL" not in output
    assert "Q" * 43 not in output
