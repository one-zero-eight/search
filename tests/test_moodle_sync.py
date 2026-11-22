"""The user's Moodle data (api/moodle.py, moodle_sync.py): written by the browser extension, private to the user. Runs on the
local dev database, like tests/test_calendar_feed.py."""

import hashlib
import json
import time
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from catix import groups, moodle_files, moodle_sync
from catix.agent import moodle_tools
from catix.api.app import app
from catix.db import pg
from catix.worker import moodle_reader
from catix.innohassle import token
from catix.settings import settings

U1, U2 = "test-moodle-u1", "test-moodle-u2"
A = {"Authorization": "Bearer good"}
B = {"Authorization": "Bearer other"}
FILE_URL = "https://moodle.innopolis.university/pluginfile.php/1/mod_resource/content/0/slides.pdf"


def _clear_requests():
    with pg.connection() as conn:
        conn.execute("DELETE FROM source_requests WHERE owner IN (%s, %s)", (U1, U2))
        conn.execute("DELETE FROM source_requests WHERE invite_link LIKE 'https://t.me/+catixMoodleTest%%'")


@pytest.fixture
def client(monkeypatch):
    claims = {"good": {"uid": U1, "email": "a@innopolis.university"}, "other": {"uid": U2, "email": "b@innopolis.university"}}
    monkeypatch.setattr(token, "claims", lambda t: claims.get(t))
    monkeypatch.setattr(settings, "reranker_route", None)
    monkeypatch.setattr(groups, "website_groups", lambda token: [])
    monkeypatch.setattr(pg, "embed", lambda texts, query=False: [[1.0] + [0.0] * 1023 for _ in texts])
    _clear_requests()
    for uid in (U1, U2):
        moodle_sync.forget(uid)
    yield TestClient(app)
    _clear_requests()
    for uid in (U1, U2):
        moodle_sync.forget(uid)


def overview(username="a@innopolis.university", **extra):
    body = {
        "moodle_user_id": 10,
        "moodle_username": username,
        "courses": [
            {"course_id": 1, "fullname": "Course one", "shortname": "C1"},
            {"course_id": 2, "fullname": "Course two", "shortname": "C2"},
        ],
    }
    return body | extra


def page_content(html="<p>Hello</p>", **extra):
    return {
        "sections": [{"section_id": 7, "name": "Week 1", "summary_html": "<p>Intro</p>",
                      "modules": [{"module_id": 5, "name": "Page", "module": "page", "html": html, **extra}]}]
    }


def texts(text: str) -> int:
    with pg.connection() as conn:
        return pg.scalar(conn, "SELECT count(*) FROM moodle_texts WHERE text = %s", (text,))


def test_sync_round_trip_and_privacy(client):
    event = {"event_id": 1, "course_id": 1, "name": "Lab", "description_html": "<p>Room <b>301</b></p>", "event_type": "due",
             "starts_at": 4102444800, "duration_seconds": 3600, "pending": True}
    items = [{"item_id": i, "name": n, "item_type": "mod"} for i, n in ((3, "B"), (2, "A"))]
    put = client.put("/users/my-moodle/overview", headers=A,
                     json=overview("A@innopolis.university", events=[event], grades=[{"course_id": 1, "items": items}]))
    assert put.json() == {"courses_without_content": [1, 2]}
    assert client.put("/users/my-moodle/courses/1/content", headers=A, json=page_content()).status_code == 200

    got = client.get("/users/my-moodle", headers=A)
    assert got.headers["cache-control"] == "private, no-store"
    [ev] = got.json()["events"]
    assert ev["description"] == "Room **301**"
    assert ev["ends_at"][:19] == "2100-01-01T01:00:00"
    assert [g["name"] for g in got.json()["grades"]] == ["B", "A"]
    content = client.get("/users/my-moodle/courses/1", headers=A).json()
    assert content["sections"][0]["summary"] == "Intro"
    assert content["sections"][0]["modules"][0]["text"] == "Hello"

    assert client.get("/users/my-moodle", headers=B).status_code == 404
    assert client.get("/users/my-moodle/courses/1", headers=B).status_code == 404


def test_account_mismatch_is_rejected(client):
    assert client.put("/users/my-moodle/overview", headers=A, json=overview("x@innopolis.university")).status_code == 409
    assert client.get("/users/my-moodle", headers=A).status_code == 404


def test_content_needs_the_course_first(client):
    assert client.put("/users/my-moodle/courses/9/content", headers=A, json=page_content()).status_code == 404


def test_shared_text_is_stored_once_and_collected(client):
    for headers, username in ((A, "a@innopolis.university"), (B, "b@innopolis.university")):
        client.put("/users/my-moodle/overview", headers=headers, json=overview(username))
        client.put("/users/my-moodle/courses/1/content", headers=headers, json=page_content("<p>Same</p>"))
    assert texts("Same") == 1
    client.delete("/users/my-moodle", headers=A)
    assert client.get("/users/my-moodle/courses/1", headers=B).json()["sections"][0]["modules"][0]["text"] == "Same"
    assert texts("Same") == 1
    client.delete("/users/my-moodle", headers=B)
    assert texts("Same") == 0


def test_partial_sync_keeps_what_moodle_did_not_return(client):
    event = {"event_id": 1, "course_id": 1, "name": "Lab", "event_type": "due", "starts_at": 4102444800}
    full = overview(
        events=[event],
        grades=[{"course_id": 2, "items": [{"item_id": 1, "name": "G", "item_type": "mod"}]}],
        assignments=[{"course_id": 2, "items": [{"assignment_id": 1, "module_id": 1, "name": "HW"}]}],
        quizzes=[{"course_id": 2, "items": [{"quiz_id": 1, "module_id": 2, "name": "Quiz"}]}],
        completion=[{"course_id": 2, "items": [{"module_id": 1, "state": 1}]}],
        groups=[{"course_id": 2, "groups": [{"group_id": 1, "name": "G1"}]}],
    )
    client.put("/users/my-moodle/overview", headers=A, json=full)
    client.put("/users/my-moodle/courses/2/content", headers=A, json=page_content("<p>Only two</p>", files=[
        {"filename": "slides.pdf", "url": FILE_URL}]) | {"announcements": [
            {"discussion_id": 1, "title": "News", "html": "<p>Only news</p>", "posted_at": 1700000000}]})

    client.put("/users/my-moodle/overview", headers=A, json=overview(events=None))
    kept = client.get("/users/my-moodle", headers=A).json()
    assert [len(kept[k]) for k in ("events", "grades", "assignments", "quizzes", "completion", "groups")] == [1] * 6

    client.put("/users/my-moodle/overview", headers=A, json=overview(events=None) | {"courses": [overview()["courses"][0]]})
    assert [c["course_id"] for c in client.get("/users/my-moodle", headers=A).json()["courses"]] == [1]
    assert client.get("/users/my-moodle", headers=A).json()["grades"] == []
    assert client.get("/users/my-moodle/courses/2", headers=A).status_code == 404
    assert (texts("Only two"), texts("Only news")) == (0, 0)
    with pg.connection() as conn:
        assert pg.scalar(conn, "SELECT count(*) FROM moodle_files WHERE innohassle_id = %s", (U1,)) == 0

    client.put("/users/my-moodle/overview", headers=A, json=overview() | {"moodle_user_id": 11})
    assert client.get("/users/my-moodle", headers=A).json()["events"] == []


def test_extra_data_round_trip(client):
    extra = dict(
        assignments=[{"course_id": 1, "items": [{"assignment_id": 1, "module_id": 4, "name": "HW", "due_at": 4102444800,
                                                  "submission_status": "submitted"}]}],
        quizzes=[{"course_id": 1, "items": [{"quiz_id": 1, "module_id": 6, "name": "Q", "attempts_allowed": 2,
                                              "attempts_used": 1}]}],
        completion=[{"course_id": 1, "items": [{"module_id": 5, "state": 1}]}],
        groups=[{"course_id": 1, "groups": [{"group_id": 3, "name": "B24-SD-01"}]}],
    )
    client.put("/users/my-moodle/overview", headers=A, json=overview(**extra))
    content = page_content(files=[{"filename": "slides.pdf", "url": FILE_URL}])
    content["announcements"] = [{"discussion_id": 1, "title": "News", "html": "<p>Lecture moved</p>", "posted_at": 1700000000}]
    assert client.put("/users/my-moodle/courses/1/content", headers=A, json=content).status_code == 200

    got = client.get("/users/my-moodle", headers=A).json()
    assert got["assignments"][0]["submission_status"] == "submitted"
    assert (got["quizzes"][0]["attempts_allowed"], got["quizzes"][0]["attempts_used"]) == (2, 1)
    assert got["completion"][0]["state"] == "complete"
    assert got["groups"][0]["name"] == "B24-SD-01"
    course = client.get("/users/my-moodle/courses/1", headers=A).json()
    assert course["announcements"][0]["text"] == "Lecture moved"
    assert course["sections"][0]["modules"][0]["files"][0]["filename"] == "slides.pdf"

    bad = {"event_id": 1, "name": "x", "event_type": "user", "starts_at": 4102444800, "url": "javascript:alert(1)"}
    assert client.put("/users/my-moodle/overview", headers=A, json=overview(events=[bad])).status_code == 422

    client.put("/users/my-moodle/overview", headers=B, json=overview("b@innopolis.university"))
    client.put("/users/my-moodle/courses/1/content", headers=B, json=content)
    assert texts("Lecture moved") == 1


def file_content(sha):
    return page_content(files=[{"filename": "notes.txt", "url": FILE_URL, "sha256": sha}])


def put_file(client, headers, sha, data):
    return client.put(f"/users/my-moodle/files/{sha}", headers=headers | {"Content-Type": "application/octet-stream"}, content=data)


def read_all():
    """Read every queued file (the dev database may hold others), then embed them."""
    while moodle_files.chunk_texts():
        pass
    while moodle_reader.read_once():
        pass
    while moodle_files.embed_batch():
        pass


def test_file_upload_extract_and_search(client, keyword_only):
    data = b"Eigenvalues of a symmetric matrix are real.\n"
    sha = hashlib.sha256(data).hexdigest()
    client.put("/users/my-moodle/overview", headers=A, json=overview())
    put = client.put("/users/my-moodle/courses/1/content", headers=A, json=file_content(sha))
    assert (put.status_code, put.json()) == (200, {"files_missing": [sha]})
    assert put_file(client, A, sha, b"x").status_code == 422
    assert put_file(client, A, sha, data).status_code == 204
    assert client.put("/users/my-moodle/courses/1/content", headers=A, json=file_content(sha)).json() == {"files_missing": []}
    course = client.get("/users/my-moodle/courses/1", headers=A).json()
    assert course["sections"][0]["modules"][0]["files"][0]["text_status"] == "queued"

    read_all()
    course = client.get("/users/my-moodle/courses/1", headers=A).json()
    assert course["sections"][0]["modules"][0]["files"][0]["text_status"] == "read"
    hits = client.get("/users/my-moodle/search", headers=A, params={"q": "eigenvalues"}).json()
    assert [h["title"] for h in hits] == ["notes.txt"]
    assert "symmetric" in hits[0]["text"]
    assert client.get("/users/my-moodle/search", headers=B, params={"q": "eigenvalues"}).json() == []
    got = client.get(f"/users/my-moodle/files/{sha}", headers=A)
    assert got.content == data
    assert got.headers["content-disposition"].startswith("inline")
    assert client.get(f"/users/my-moodle/files/{sha}", headers=B).status_code == 404


@pytest.fixture
def keyword_only(monkeypatch):
    """Search by words alone: the test embedding is one vector for every text, which would make every piece a vector hit."""
    monkeypatch.setattr(moodle_files, "_embed_all", lambda queries: [])


def asking(user, groups=()):
    return SimpleNamespace(context=SimpleNamespace(innohassle_id=user, verified_study_groups=groups))


def test_course_texts_are_searched_with_their_path(client, keyword_only):
    client.put("/users/my-moodle/overview", headers=A, json=overview())
    client.put("/users/my-moodle/courses/1/content", headers=A, json=page_content("<p>Gradient descent converges slowly</p>"))
    read_all()
    [hit] = client.get("/users/my-moodle/search", headers=A, params={"q": "gradient"}).json()
    assert (hit["kind"], hit["path"], hit["page"], hit["shared"]) == ("module", "Course one › Week 1 › Page", None, False)
    assert client.get("/users/my-moodle/search", headers=B, params={"q": "gradient"}).json() == []


def test_moodle_deadlines_leave_out_mirrored_events_and_later_ones(client):
    now = int(time.time())
    day = 86400
    client.put("/users/my-moodle/overview", headers=A, json=overview(
        assignments=[{"course_id": 1, "items": [{"assignment_id": 1, "module_id": 5, "name": "HW", "due_at": now + 3 * day}]}],
        quizzes=[{"course_id": 1, "items": [{"quiz_id": 1, "module_id": 6, "name": "Quiz", "closes_at": now + 20 * day}]}],
        events=[
            {"event_id": 1, "course_id": 1, "name": "HW due", "event_type": "due", "module": "assign", "starts_at": now + 3 * day},
            {"event_id": 2, "course_id": 1, "name": "Lesson", "event_type": "open", "module": "lesson", "starts_at": now + 2 * day},
        ],
    ))
    result = moodle_tools.get_my_moodle.func(asking(U1), "deadlines")
    assert [i["kind"] for i in result["items"]] == ["event", "assignment"]
    assert result["total"] == 2
    first = datetime.now(settings.tz).date()
    assert result["range"] == [first.isoformat(), (first + timedelta(days=13)).isoformat()]
    assert moodle_tools.get_my_moodle.func(asking(U2), "deadlines")["error"].startswith("No Moodle data")


def test_a_group_reads_shared_materials_but_not_grades_or_hidden_modules(client, keyword_only, monkeypatch):
    monkeypatch.setattr(groups, "website_groups", lambda token: ["B24-SD-01"])
    due = int(time.time()) + 3 * 86400
    client.put("/users/my-moodle/overview", headers=A, json=overview(
        assignments=[{"course_id": 1, "items": [{"assignment_id": 1, "module_id": 5, "name": "HW", "due_at": due,
                                                 "submission_status": "submitted"}]}],
        grades=[{"course_id": 1, "items": [{"item_id": 1, "name": "G", "item_type": "mod", "grade": 9}]}],
    ))
    modules = [
        {"module_id": 5, "name": "Page", "module": "page", "html": "<p>Gradient descent converges</p>", "shareable": True},
        {"module_id": 6, "name": "Key", "module": "page", "html": "<p>Hidden answers key</p>", "shareable": False},
    ]
    client.put("/users/my-moodle/courses/1/content", headers=A,
               json={"sections": [{"section_id": 7, "name": "Week 1", "shareable": True, "modules": modules}]})
    read_all()

    seen = []
    shared = client.get("/users/my-moodle/search", headers=B, params={"q": "gradient"})
    seen.append(shared.text)
    [hit] = shared.json()
    assert hit["shared"] is True
    hidden = client.get("/users/my-moodle/search", headers=B, params={"q": "answers"})
    seen.append(hidden.text)
    assert hidden.json() == []

    ask = asking(U2, ("B24-SD-01",))
    deadlines = moodle_tools.get_my_moodle.func(ask, "deadlines")
    seen.append(json.dumps(deadlines))
    [item] = deadlines["items"]
    assert (item["kind"], item["shared"], item["submission_status"]) == ("assignment", True, None)
    grades = moodle_tools.get_my_moodle.func(ask, "grades")
    seen.append(json.dumps(grades))
    assert grades["items"] == []
    assert not any(U1 in text for text in seen)

    assert moodle_tools.get_my_moodle.func(asking(U2, ("B24-SD-02",)), "deadlines")["error"].startswith("No Moodle data")
    client.delete("/users/my-moodle", headers=A)
    assert client.get("/users/my-moodle/search", headers=B, params={"q": "gradient"}).json() == []


def test_file_not_listed_is_refused(client):
    data = b"Nobody lists this file.\n"
    client.put("/users/my-moodle/overview", headers=A, json=overview())
    assert put_file(client, A, hashlib.sha256(data).hexdigest(), data).status_code == 404


def test_shared_file_stored_once_and_collected(client):
    data = b"Shared lecture about eigenvalues.\n"
    sha = hashlib.sha256(data).hexdigest()

    def blobs():
        with pg.connection() as conn:
            return pg.scalar(conn, "SELECT count(*) FROM moodle_blobs WHERE sha256 = %s", (sha,))

    for headers, username in ((A, "a@innopolis.university"), (B, "b@innopolis.university")):
        client.put("/users/my-moodle/overview", headers=headers, json=overview(username))
        client.put("/users/my-moodle/courses/1/content", headers=headers, json=file_content(sha))
        assert put_file(client, headers, sha, data).status_code == 204
    assert blobs() == 1
    client.delete("/users/my-moodle", headers=A)
    assert blobs() == 1
    read_all()
    assert client.get("/users/my-moodle/search", headers=B, params={"q": "eigenvalues"}).json()[0]["title"] == "notes.txt"
    client.delete("/users/my-moodle", headers=B)
    assert blobs() == 0


def test_reader_reads_text_and_refuses_binary():
    assert moodle_files.read_file(b"hello", ".txt").page_texts == [(None, "hello")]
    with pytest.raises(moodle_files.ReadFailed):
        moodle_files.read_file(b"\x00\x01", ".txt")


def test_course_chat_links_become_pending_requests(client, monkeypatch):
    link = "https://t.me/+catixMoodleTest" + "A" * 8
    content = {"sections": [{
        "section_id": 1, "summary_html": f'<a href="{link}">chat</a>',
        "modules": [
            {"module_id": 2, "name": "Chat", "module": "url", "external_url": link.replace("t.me", "telegram.me")},
            {"module_id": 3, "name": "L", "module": "label", "html": "https://t.me/some_bot https://t.me/durov/1"},
        ],
    }]}

    def rows():
        with pg.connection() as conn:
            return conn.execute("SELECT * FROM source_requests WHERE invite_link = %s", (link,)).fetchall()

    monkeypatch.setattr(groups, "website_groups", lambda token: [])
    assert client.put("/users/my-moodle/overview", headers=A, json=overview()).status_code == 200
    assert client.put("/users/my-moodle/courses/1/content", headers=A, json=content).status_code == 200
    assert rows() == []

    monkeypatch.setattr(groups, "website_groups", lambda token: ["B24-SD-01"])
    assert client.put("/users/my-moodle/courses/1/content", headers=A, json=content).status_code == 200
    [row] = rows()
    assert (row["owner"], row["status"], row["group_code"], row["comment"], row["decided_by"]) == (
        U1, "pending", "B24-SD-01", "Moodle: Course one", None)
    assert row["decided_at"] is None

    assert client.put("/users/my-moodle/overview", headers=B, json=overview("b@innopolis.university")).status_code == 200
    assert client.put("/users/my-moodle/courses/1/content", headers=B, json=content).status_code == 200
    assert len(rows()) == 1
