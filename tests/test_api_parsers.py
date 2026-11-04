"""POST /{section}/parse queues a request for the wiki's own run: the API never reads a source nor writes the wiki."""

from argparse import Namespace

import pytest
from fastapi.testclient import TestClient

from catix.api.app import app
from catix.innohassle import token
from catix.wiki import autopilot, parse_requests
from catix.wiki import compile as compiler
from catix.wiki.sources import eduwiki, sites

AUTH = {"Authorization": "Bearer good"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(token, "claims", lambda t: {"uid": "u1", "email": "a@innopolis.university"} if t == "good" else None)
    monkeypatch.setattr(sites, "SITES", {name: sites.SITES[name] for name in ("hotel", "campuslife")})

    def never(*args, **kwargs):
        pytest.fail("the API read a source or wrote the wiki")

    for module, name in ((sites, "fetch"), (sites, "compile_all"), (eduwiki, "fetch"), (compiler, "compile_pages"), (compiler, "link")):
        monkeypatch.setattr(module, name, never)
    return TestClient(app)


def queued(fake) -> list[parse_requests.Request]:
    return [parse_requests.get(i) for i in fake.lrange(parse_requests.QUEUED, 0, -1)]


def test_sites_request_is_queued_not_run(client, parse_queue):
    response = client.post("/sites/parse", params=[("sites", "hotel"), ("sites", "campuslife")], headers=AUTH)
    assert response.status_code == 202, response.text
    body = response.json()
    assert {k: body[k] for k in ("section", "source", "sites", "parsing", "status", "outcome")} == {
        "section": "sites", "source": "sites", "sites": ["hotel", "campuslife"], "parsing": True, "status": "queued", "outcome": ""}
    assert [(r.id, r.source, r.sites) for r in queued(parse_queue)] == [(body["id"], "sites", ["hotel", "campuslife"])]


def test_the_same_waiting_request_is_queued_once(client, parse_queue):
    first = client.post("/sites/parse?sites=hotel", headers=AUTH).json()
    again = client.post("/resources/parse?sites=hotel", headers=AUTH).json()
    other = client.post("/sites/parse?sites=campuslife", headers=AUTH).json()
    assert again["id"] == first["id"] and other["id"] != first["id"]
    assert len(queued(parse_queue)) == 2
    parse_requests.take()  # (a run took it: the same request asked now may need a new read)
    assert client.post("/sites/parse?sites=hotel", headers=AUTH).json()["id"] not in {first["id"], other["id"]}


def test_status_follows_the_request(client):
    request = client.post("/eduwiki/parse", headers=AUTH).json()
    assert client.get(f"/parse/{request['id']}", headers=AUTH).json()["status"] == "queued"
    taken = parse_requests.take()
    assert client.get(f"/parse/{request['id']}", headers=AUTH).json()["status"] == "running"
    parse_requests.finish(taken, "committed", "committed 1a2b3c: 4 files and pushed")
    done = client.get(f"/parse/{request['id']}", headers=AUTH).json()
    assert (done["status"], done["outcome"], done["result"]) == ("done", "committed", "committed 1a2b3c: 4 files and pushed")
    assert done["started_at"] and done["finished_at"]
    assert client.get("/parse/999", headers=AUTH).status_code == 404


def test_without_a_queue_the_request_is_refused(client, monkeypatch):
    def unavailable():
        raise parse_requests.Unavailable("REDIS_URL is not set")

    monkeypatch.setattr(parse_requests, "connect", unavailable)
    assert client.post("/sites/parse?sites=hotel", headers=AUTH).status_code == 503
    assert client.get("/parse/1", headers=AUTH).status_code == 503


def test_site_choices_come_from_the_configured_catalog(client):
    response = client.get("/sites", headers=AUTH)
    assert response.status_code == 200
    assert response.json() == [{"name": name, "url": sites.SITES[name].base, "about": sites.SITES[name].about}
                               for name in ("campuslife", "hotel")]


def test_api_reloads_approved_sites_after_external_catalog_change(client, parse_queue):
    assert "lab" not in {item["name"] for item in client.get("/sites", headers=AUTH).json()}
    sites.CONFIG.write_text("blocked: []\nsites:\n  lab:\n    base: https://lab.example/\n    language: en\n    about: Lab\n    skip: ^private\n")
    assert [item["name"] for item in client.get("/sites", headers=AUTH).json()] == ["lab"]
    response = client.post("/sites/parse?sites=lab", headers=AUTH)
    assert response.status_code == 202 and [r.sites for r in queued(parse_queue)] == [["lab"]]


@pytest.mark.parametrize("method,path", [("get", "/sites"), ("post", "/sites/parse")])
def test_site_routes_work_without_every_site(client, monkeypatch, method, path):
    monkeypatch.delattr(sites, "every_site", raising=False)
    response = client.request(method, path, headers=AUTH)
    assert response.status_code in (200, 202), response.text
    names = [site["name"] for site in response.json()] if method == "get" else response.json()["sites"]
    assert names == ["campuslife", "hotel"]


@pytest.mark.parametrize("section,names,status", [
    ("sites", ["hotel", "unknown"], 400), ("sites", [""], 400),
    ("sites", ["http://127.0.0.1/"], 400), ("wiki", ["hotel"], 400),
    ("hotel", ["campuslife"], 400), ("moodle", [], 410), ("unknown", [], 422),
])
def test_invalid_selection_queues_nothing(client, parse_queue, section, names, status):
    response = client.post(f"/{section}/parse", params=[("sites", name) for name in names], headers=AUTH)
    assert response.status_code == status, response.text
    assert queued(parse_queue) == []


@pytest.mark.parametrize("section,names,source,expected", [
    ("sites", [], "sites", ["campuslife", "hotel"]), ("resources", ["hotel", "hotel"], "sites", ["hotel"]),
    ("hotel", [], "sites", ["hotel"]), ("campuslife", [], "sites", ["campuslife"]),
    ("wiki", [], "eduwiki", []), ("eduwiki", [], "eduwiki", []),
])
def test_sections_name_their_source(client, section, names, source, expected):
    response = client.post(f"/{section}/parse", params=[("sites", name) for name in names], headers=AUTH)
    assert response.status_code == 202, response.text
    assert (response.json()["source"], response.json()["sites"]) == (source, expected)


def test_parser_routes_require_auth(client):
    assert client.get("/sites").status_code == 401
    assert client.post("/sites/parse").status_code == 401
    assert client.get("/parse/1").status_code == 401


def test_no_parsing_asks_the_run_to_build_only(client):
    response = client.post("/sites/parse?sites=hotel&parsing_is_needed=false", headers=AUTH)
    assert response.status_code == 202 and response.json()["parsing"] is False


def test_neither_parse_nor_index_is_a_bad_request(client, parse_queue):
    response = client.post("/sites/parse?parsing_is_needed=false&indexing_is_needed=false", headers=AUTH)
    assert response.status_code == 400 and queued(parse_queue) == []


def test_the_wiki_run_serves_the_request_with_its_checks_and_commit(client, monkeypatch, tmp_path):
    """The request reaches autopilot.main: it asks the named sites as the source `sites` and the queue gets what the run did."""
    first = client.post("/sites/parse?sites=hotel", headers=AUTH).json()
    second = client.post("/eduwiki/parse", headers=AUTH).json()
    calls = []
    monkeypatch.setattr(autopilot, "ready", lambda: None)
    monkeypatch.setattr(autopilot, "LOCK", tmp_path / "lock")
    monkeypatch.setattr(autopilot, "load_state", lambda: {"asked": {s.name: "2999-01-01T00:00:00+00:00" for s in autopilot.sources.SOURCES}})
    monkeypatch.setattr(autopilot, "run_once", lambda *a, **kw: calls.append((a, kw)) or autopilot.Outcome("committed", "committed 1a2b3c: 2 files and pushed"))
    autopilot.main(Namespace(action="run", source=None, site=None, only_new=False, build=False, no_push=False, no_answers=False, loop=False))
    assert calls == [((["sites", "eduwiki"],), {"push": True, "answers": True, "sites": ["hotel"]})]
    for request in (first, second):
        status = client.get(f"/parse/{request['id']}", headers=AUTH).json()
        assert (status["status"], status["outcome"], status["result"]) == ("done", "committed", "committed 1a2b3c: 2 files and pushed")
