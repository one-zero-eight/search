"""Parser routes use the wiki's incremental readers, never the autopilot or live services."""

import fcntl

import httpx
import pytest
from fastapi.testclient import TestClient

from catix.api import parsers
from catix.api.app import app
from catix.innohassle import token
from catix.settings import settings
from catix.wiki import compile as compiler
from catix.wiki import lint, search_index
from catix.wiki.paths import DATA
from catix.wiki.sources import eduwiki, sites
from catix.wiki.sources.sites import fetch as fetch_sites

AUTH = {"Authorization": "Bearer good"}


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(token, "claims", lambda t: {"uid": "u1", "email": "a@innopolis.university"} if t == "good" else None)
    monkeypatch.setattr(parsers, "LOCK", tmp_path / ".autopilot.lock")
    monkeypatch.setattr(sites, "SITES", {name: sites.SITES[name] for name in ("hotel", "campuslife")})

    def no_fetch(*args, **kwargs):
        pytest.fail("unexpected fetch")

    monkeypatch.setattr(sites, "fetch", no_fetch)
    return TestClient(app)


def test_selected_sites_reuse_fetch_and_compile_changes(client, monkeypatch):
    calls = []
    monkeypatch.setattr(sites, "fetch", lambda names, **kw: calls.append(("fetch", names, kw)) or 2)
    monkeypatch.setattr(sites, "compile_all", lambda: calls.append("compile"))
    monkeypatch.setattr(compiler, "link", lambda: calls.append("link"))
    response = client.post("/sites/parse", params=[("sites", "hotel"), ("sites", "campuslife"),
                                                 ("indexing_is_needed", "false")], headers=AUTH)
    assert response.status_code == 200, response.text
    assert response.json() == {"section": "sites", "sites": ["hotel", "campuslife"], "changed": 2,
                               "processed": True, "indexed": False, "index": {}, "embedded": 0}
    assert calls == [("fetch", ["hotel", "campuslife"], {}), "compile", "link"]


def test_site_choices_come_from_the_configured_catalog(client):
    response = client.get("/sites", headers=AUTH)
    assert response.status_code == 200
    assert response.json() == [{"name": name, "url": sites.SITES[name].base, "about": sites.SITES[name].about}
                               for name in ("campuslife", "hotel")]


@pytest.mark.parametrize("method,path", [("get", "/sites"), ("post", "/sites/parse?indexing_is_needed=false")])
def test_site_routes_work_without_every_site(client, monkeypatch, method, path):
    monkeypatch.delattr(sites, "every_site", raising=False)
    monkeypatch.setattr(sites, "fetch", lambda names: 0)
    response = client.request(method, path, headers=AUTH)
    assert response.status_code == 200, response.text
    names = [site["name"] for site in response.json()] if method == "get" else response.json()["sites"]
    assert names == ["campuslife", "hotel"]


@pytest.mark.parametrize("section,names,status", [
    ("sites", ["hotel", "unknown"], 400), ("sites", [""], 400),
    ("sites", ["http://127.0.0.1/"], 400), ("wiki", ["hotel"], 400),
    ("hotel", ["campuslife"], 400), ("moodle", [], 410), ("unknown", [], 422),
])
def test_invalid_selection_never_starts_fetch(client, section, names, status):
    response = client.post(f"/{section}/parse", params=[("indexing_is_needed", "false"),
                                                      *(("sites", name) for name in names)], headers=AUTH)
    assert response.status_code == status, response.text


@pytest.mark.parametrize("section,names,expected", [
    ("sites", [], ["campuslife", "hotel"]), ("resources", ["hotel", "hotel"], ["hotel"]),
    ("hotel", [], ["hotel"]), ("campuslife", [], ["campuslife"]),
])
def test_site_selection_and_legacy_paths(client, monkeypatch, section, names, expected):
    calls = []
    monkeypatch.setattr(sites, "fetch", lambda names: calls.append(names) or 0)
    response = client.post(f"/{section}/parse", params=[("indexing_is_needed", "false"),
                                                      *(("sites", name) for name in names)], headers=AUTH)
    assert response.status_code == 200, response.text
    assert calls == [expected]
    assert response.json()["sites"] == expected
    assert response.json()["processed"] is False


def test_parser_routes_require_auth(client):
    assert client.get("/sites").status_code == 401
    assert client.post("/sites/parse").status_code == 401


@pytest.fixture
def pipeline(monkeypatch):
    calls = []
    monkeypatch.setattr(settings, "database_url", "postgresql://unused")
    monkeypatch.setattr(sites, "compile_all", lambda: calls.append("sites"))
    monkeypatch.setattr(compiler, "compile_pages", lambda titles: calls.append(("wiki", titles)))
    monkeypatch.setattr(compiler, "link", lambda: calls.append("link"))
    monkeypatch.setattr(lint, "lint", lambda: calls.append("lint") or 0)
    monkeypatch.setattr(search_index, "sync", lambda: calls.append("index") or {"pages new": 2})
    monkeypatch.setattr(search_index, "embed_all", lambda: calls.append("embed") or 3)
    return calls


@pytest.mark.parametrize("section", ["wiki", "eduwiki"])
@pytest.mark.parametrize("changed", [0, 2])
def test_wiki_uses_revision_fetch_and_only_processes_changes(client, monkeypatch, pipeline, section, changed):
    monkeypatch.setattr(eduwiki, "fetch", lambda namespaces: pipeline.append(("fetch", namespaces)) or changed)
    response = client.post(f"/{section}/parse", headers=AUTH)
    assert response.status_code == 200, response.text
    assert pipeline == [("fetch", [0])] + ([("wiki", None), "link", "lint", "index", "embed"] if changed else [])
    assert response.json()["changed"] == changed
    assert response.json()["indexed"] is bool(changed)
    assert response.json()["embedded"] == (3 if changed else 0)


def test_sites_changes_reach_the_index(client, monkeypatch, pipeline):
    monkeypatch.setattr(sites, "fetch", lambda names: 2)
    response = client.post("/sites/parse?sites=hotel", headers=AUTH)
    assert response.status_code == 200, response.text
    assert pipeline == ["sites", "link", "lint", "index", "embed"]
    assert response.json()["index"] == {"pages new": 2}


def test_unchanged_sites_skip_processing_and_index(client, monkeypatch, pipeline):
    monkeypatch.setattr(sites, "fetch", lambda names: 0)
    response = client.post("/sites/parse?sites=hotel", headers=AUTH)
    assert response.status_code == 200
    assert pipeline == []
    assert response.json()["indexed"] is False


def test_reprocess_cache_without_fetch(client, pipeline):
    response = client.post("/sites/parse?sites=hotel&parsing_is_needed=false", headers=AUTH)
    assert response.status_code == 200, response.text
    assert pipeline == ["sites", "link", "lint", "index", "embed"]


def test_neither_parse_nor_index_is_a_bad_request(client):
    response = client.post("/sites/parse?parsing_is_needed=false&indexing_is_needed=false", headers=AUTH)
    assert response.status_code == 400


def test_index_requires_database_before_fetch(client, monkeypatch):
    monkeypatch.setattr(settings, "database_url", "")
    assert client.post("/sites/parse", headers=AUTH).status_code == 503


def test_broken_bundle_is_not_indexed(client, monkeypatch, pipeline):
    monkeypatch.setattr(sites, "fetch", lambda names: 1)
    monkeypatch.setattr(lint, "lint", lambda: 1)
    response = client.post("/sites/parse?sites=hotel", headers=AUTH)
    assert response.status_code == 409
    assert pipeline == ["sites", "link"]


def test_parser_does_not_overlap_autopilot(client, monkeypatch, tmp_path):
    # The same lock file as autopilot.main, not just an in-process mutex.
    monkeypatch.setattr(parsers, "LOCK", tmp_path / ".autopilot.lock", raising=False)
    with parsers.LOCK.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        response = client.post("/sites/parse?indexing_is_needed=false", headers=AUTH)
    assert response.status_code == 409


def test_lock_is_shared_with_autopilot():
    assert getattr(parsers, "LOCK", None) == DATA / ".autopilot.lock"


def test_fetch_error_is_reported_and_releases_lock(client, monkeypatch):
    def broken(names):
        raise RuntimeError("source unavailable")

    monkeypatch.setattr(sites, "fetch", broken)
    response = client.post("/sites/parse?indexing_is_needed=false", headers=AUTH)
    assert response.status_code == 502
    monkeypatch.setattr(sites, "fetch", lambda names: 0)
    assert client.post("/sites/parse?indexing_is_needed=false", headers=AUTH).status_code == 200


def test_http_route_with_real_fetch_and_compiler_is_incremental(client, monkeypatch, tmp_path):
    """Only HTTP is replaced: page hashes, cache and compiled markdown are the real implementation."""
    catalog = {name: sites.Site(f"https://{name}.example/", "ru", name, r"^never$", sitemap=False, pause=0)
               for name in ("hotel", "campuslife")}
    monkeypatch.setattr(sites, "SITES", catalog)
    monkeypatch.setattr(sites, "ROOT", tmp_path / "raw" / "sites")
    monkeypatch.setattr(sites, "DOCS", tmp_path / "wiki" / "raw")
    monkeypatch.setattr(sites.regulations, "all_docs", lambda: {})
    monkeypatch.setattr(sites, "fetch", fetch_sites)
    links = []
    monkeypatch.setattr(compiler, "link", lambda: links.append("link"))
    text = ["Студенты могут проживать в кампусе университета и пользоваться комнатами для подготовки к занятиям. " * 5]
    requests = []

    def respond(request):
        requests.append(str(request.url))
        assert request.url.host == "hotel.example"
        return httpx.Response(200, headers={"Content-Type": "text/html"},
                              text=f"<html><head><title>Кампус</title></head><body><p>{text[0]}</p></body></html>")

    http_client = httpx.Client
    monkeypatch.setattr(sites.httpx, "Client", lambda **kw: http_client(transport=httpx.MockTransport(respond), **kw))
    url = "/sites/parse?sites=hotel&indexing_is_needed=false"
    first = client.post(url, headers=AUTH)
    assert first.status_code == 200, first.text
    assert first.json()["changed"] == 1
    page, = (sites.DOCS / "sites" / "hotel").glob("*.md")
    before = page.read_bytes()
    before_mtime = page.stat().st_mtime_ns
    again = client.post(url, headers=AUTH)
    assert again.status_code == 200, again.text
    assert again.json()["changed"] == 0 and again.json()["processed"] is False
    assert page.read_bytes() == before and page.stat().st_mtime_ns == before_mtime
    text[0] += " Новое правило проживания: соблюдать тишину после полуночи."
    changed = client.post(url, headers=AUTH)
    assert changed.status_code == 200, changed.text
    assert changed.json()["changed"] == 1
    assert "Новое правило проживания" in page.read_text()
    assert links == ["link", "link"]
    assert requests == ["https://hotel.example/"] * 3
    assert not (sites.ROOT / "campuslife").exists()
