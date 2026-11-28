"""POST /{section}/parse queues a request for `catix-docs run`: the API never reads a source nor builds documents."""

from argparse import Namespace

import pytest
from fastapi.testclient import TestClient

from catix.api.app import app
from catix.innohassle import token
from catix.docs import build, frontier, parse_requests, runner, sources
from catix.docs.sources import eduwiki, regulations, sites

AUTH = {"Authorization": "Bearer good"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(token, "claims", lambda t: {"uid": "u1", "email": "a@innopolis.university"} if t == "good" else None)
    monkeypatch.setattr(sites, "SITES", {name: sites.SITES[name] for name in ("hotel", "campuslife")})

    def never(*args, **kwargs):
        pytest.fail("the API read a source or built documents")

    for module, name in ((sites, "read_page"), (sites, "compile_all"), (eduwiki, "fetch"), (eduwiki, "compile_all"), (build, "rebuild")):
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
    parse_requests.finish(taken, "changed", "documents: 4 new, 0 changed, 0 removed; 9 pieces wait for a vector")
    done = client.get(f"/parse/{request['id']}", headers=AUTH).json()
    assert (done["status"], done["outcome"], done["result"]) == ("done", "changed", "documents: 4 new, 0 changed, 0 removed; 9 pieces wait for a vector")
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
    sites.save_catalog({"sites": {"lab": {"base": "https://lab.example/", "language": "en", "about": "Lab", "skip": "^private"}}})
    assert [item["name"] for item in client.get("/sites", headers=AUTH).json()] == ["lab"]
    response = client.post("/sites/parse?sites=lab", headers=AUTH)
    assert response.status_code == 202 and [r.sites for r in queued(parse_queue)] == [["lab"]]


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


class Lock:
    autocommit = False

    def execute(self, sql, params=None):
        return self

    def fetchone(self):
        return {"got": True}


def test_the_run_serves_the_request(client, monkeypatch, docs_db):
    """The request reaches runner.main: the rows of the named sites are read first, the run rebuilds only their documents, the queue gets what it did."""
    request = client.post("/sites/parse?sites=hotel", headers=AUTH).json()
    read, built = [], []

    def read_page(http, row):
        read.append((row.site, row.priority))
        frontier.save(row, state="ok")
        return row.site == "hotel"

    monkeypatch.setattr(runner.pg, "connect", lambda: Lock())
    monkeypatch.setattr(runner, "load_state", lambda: {})
    monkeypatch.setattr(runner, "save_state", lambda state: None)
    monkeypatch.setattr(runner, "tell_ocr_queue", lambda state: None)
    monkeypatch.setattr(sources, "JOBS", [])
    monkeypatch.setattr(sites, "read_page", read_page)
    monkeypatch.setattr(sites, "read_listing", lambda http, row: frontier.save(row, state="ok") and False)
    monkeypatch.setattr(regulations, "recheck", lambda keys: [])
    monkeypatch.setattr(build, "rebuild", lambda groups=None: built.append(groups) or {"pages new": 2, "pages changed": 0, "pages removed": 0})
    monkeypatch.setattr(runner.store, "queued", lambda: 5)
    runner.main(Namespace(source=None, site=None, build=False, loop=False))
    assert read[0] == ("hotel", frontier.REQUEST) and built == [{"sites/hotel"}]
    status = client.get(f"/parse/{request['id']}", headers=AUTH).json()
    assert (status["status"], status["outcome"]) == ("done", "changed")
    assert status["result"] == "documents: 2 new, 0 changed, 0 removed; 5 pieces wait for a vector"


def test_a_new_site_request_is_queued_with_its_name(client, parse_queue):
    response = client.post("/sites/new?url=https://new.example/path", headers=AUTH)
    assert response.status_code == 202, response.text
    body = response.json()
    assert (body["source"], body["sites"], body["url"]) == ("new-site", ["new-example"], "https://new.example/")
    taken = client.post("/sites/new?url=https://hotel.innopolis.university/", headers=AUTH)
    assert taken.status_code == 400 and "hotel" in taken.json()["detail"]
    assert client.post("/sites/new?url=notaurl", headers=AUTH).status_code == 400
    assert len(queued(parse_queue)) == 1
