"""Exact archive previews: existing wiki metadata, real ZIP decoder and synthetic HTTP."""

import hashlib
import json
import os
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
import httpx
import yaml
from fastapi.testclient import TestClient

from catix.api import search
from catix.api.app import app
from catix.db.wiki import WikiHit, page as read_wiki_page
from catix.innohassle import token
from catix.settings import settings
from tests.test_archive_preview_download import zipped

AUTH = {"Authorization": "Bearer good"}
ARCHIVE = "https://innopolis.university/documents/programmes.zip"
PDF = b"%PDF-1.7\noriginal first member\n%%EOF"
MEMBER = "2026/Первая программа.pdf"


@pytest.fixture
def archive(tmp_path, monkeypatch):
    from catix.wiki.search_index import fingerprint

    from catix.wiki.sources import archive_documents

    root = tmp_path / "wiki-data"
    monkeypatch.setattr(settings, "wiki_root", root)
    monkeypatch.setattr(settings, "archive_preview_cache", tmp_path / "api-cache")
    raw = root / "raw" / "rpd" / "index.json"
    raw.parent.mkdir(parents=True)
    key = "rpd-" + hashlib.sha1(f"{ARCHIVE}/{MEMBER}".encode()).hexdigest()[:8] + "-first"
    digest = hashlib.sha256(PDF).hexdigest()
    record = {"archive": ARCHIVE, "member": MEMBER, "sha256": digest}
    raw.write_text(json.dumps({key: record}))
    path = f"/raw/course-programmes/{key}.md"
    page = root / "wiki" / path.lstrip("/")
    page.parent.mkdir(parents=True)
    meta = {"type": "course-programme", "title": "First programme", "resource": ARCHIVE,
            "archive_member": MEMBER, "sources": [{"resource": ARCHIVE, "id": digest[:12]}]}
    text = "---\n" + yaml.safe_dump(meta, allow_unicode=True) + "---\n\n# First programme\n\nOriginal text.\n"
    page.write_text(text)
    revision = fingerprint(text)
    hit = WikiHit(id=1, path=path, seq=0, heading="Chapter", clause="", sha="chunk", text="Original text.", cites=[],
                  title="First programme", type="course-programme", trust="official", audience=[], resource=ARCHIVE,
                  status=None, review=None, source_warning=None, stale_after=None, issued=None)
    hit.page_sha = revision
    monkeypatch.setattr(search.wiki_store, "page", lambda value: [hit] if value == path else [])
    monkeypatch.setattr(token, "claims", lambda value: {"uid": "u1", "email": "a@innopolis.university"} if value == "good" else None)
    remote = {"body": zipped([("other.pdf", b"%PDF-1.7\nother"), (MEMBER, PDF)]), "status": 200}
    asked = []

    def handle(request):
        asked.append(request)
        return httpx.Response(remote["status"], content=remote["body"])

    @contextmanager
    def stream(method, url, **kwargs):
        with httpx.Client(transport=httpx.MockTransport(handle)) as client:
            with client.stream(method, url, **kwargs) as response:
                yield response

    monkeypatch.setattr(archive_documents.httpx, "stream", stream)
    return SimpleNamespace(page=page, raw=raw, hit=hit, meta=meta, text=text, key=key, record=record, remote=remote, asked=asked,
                           params={"page": path, "revision": revision})


def test_open_exact_archive_pdf(archive):
    response = TestClient(app).get("/search/archive-document", params=archive.params, headers=AUTH)
    assert response.status_code == 200
    assert response.content == PDF
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("inline; filename*=UTF-8''%D0%9F")
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize("problem", ["server_error", "not_archive", "unsafe_archive"])
def test_download_failures_have_a_safe_http_error(archive, problem):
    if problem == "server_error":
        archive.remote["status"] = 503
    elif problem == "not_archive":
        archive.remote["body"] = b"<html>Login</html>"
    else:
        archive.remote["body"] = zipped([(MEMBER, PDF), ("../escape.pdf", PDF)])
    response = TestClient(app).get("/search/archive-document", params=archive.params, headers=AUTH)
    assert response.status_code == 502
    assert response.json()["detail"] == "The archive could not be downloaded or opened"
    assert len(archive.asked) == 1


@pytest.mark.parametrize("error,status", [(httpx.ReadTimeout("timeout"), 504), (PermissionError("private path"), 503)])
def test_timeout_and_cache_error_are_not_internal_server_errors(archive, monkeypatch, error, status):
    from catix.wiki import preview_cache

    def fail(*args):
        raise error

    monkeypatch.setattr(preview_cache, "read", fail)
    response = TestClient(app).get("/search/archive-document", params=archive.params, headers=AUTH)
    assert response.status_code == status
    assert "private path" not in response.text


def test_search_and_answer_sources_keep_the_exact_member(archive, monkeypatch):
    from catix.agent.sources import Collector, cite

    expected = {**archive.params, "member": archive.meta["archive_member"]}
    monkeypatch.setattr(search.wiki_store, "search", lambda *args, **kwargs: [archive.hit])
    response = TestClient(app).get("/search/search", params={"query": "programme", "response_types": "pdf"}, headers=AUTH)
    card = response.json()["responses"][0]["source"]
    assert card.get("archive_document") == expected
    assert card["url"] == ARCHIVE

    runtime = SimpleNamespace(state={"sources": {}}, config={"configurable": {"thread_id": "archive-card"}})
    collector = Collector(runtime)
    ref = collector.add_wiki(archive.hit)
    assert collector.new[ref]["archive_document"] == expected
    saved = cite(f"Programme [{ref}].", collector.new).sources[0].model_dump()
    assert saved["archive_document"] == expected
    assert "file" not in saved["archive_document"]
    assert saved["url"] == ARCHIVE


def test_same_title_members_are_not_collapsed(archive):
    from dataclasses import replace
    from catix.agent import sources

    from catix.wiki.search_index import fingerprint

    member = "2026/Вторая программа.pdf"
    key = "rpd-" + hashlib.sha1(f"{ARCHIVE}/{member}".encode()).hexdigest()[:8] + "-second"
    second_page = archive.page.with_name(key + ".md")
    text = archive.text.replace(MEMBER, member)
    second_page.write_text(text)
    archive.raw.write_text(json.dumps({archive.key: archive.record, key: {**archive.record, "member": member}}))
    second = replace(archive.hit, id=2, path=f"/raw/course-programmes/{key}.md", page_sha=fingerprint(text))
    cards = search.to_responses([archive.hit, archive.hit, second], search.ALL_SOURCES)
    assert len(cards) == 2
    collector = sources.Collector(SimpleNamespace(state={"sources": {}}, config={}))
    first_ref, second_ref = collector.add_wiki(archive.hit), collector.add_wiki(second)
    answer = sources.cite(f"First [{first_ref}], second [{second_ref}].", collector.new)
    assert answer.answer == "First [1], second [2]."
    assert len(answer.sources) == 2
    assert [source.archive_document.member for source in answer.sources] == [MEMBER, member]


@pytest.mark.parametrize("change", ["file_changed", "file_missing", "page_changed", "index_changed", "wrong_revision", "wrong_page"])
def test_never_substitute_a_different_member_or_revision(archive, change):
    params = dict(archive.params)
    if change == "file_changed":
        archive.remote["body"] = zipped([(MEMBER, b"%PDF-1.7\nnew version\n%%EOF")])
    elif change == "file_missing":
        archive.remote["body"] = zipped([("other.pdf", PDF)])
    elif change == "page_changed":
        archive.page.write_text(archive.text + "Changed document.\n")
    elif change == "index_changed":
        archive.hit.page_sha = "f" * 16
    elif change == "wrong_revision":
        params["revision"] = "f" * 16
    else:
        params["page"] = "/raw/course-programmes/not-indexed.md"
    response = TestClient(app).get("/search/archive-document", params=params, headers=AUTH)
    assert response.status_code == 404
    assert "unavailable" in response.json()["detail"]


def test_authentication_precedes_lookup(archive, monkeypatch):
    monkeypatch.setattr(search.wiki_store, "page", lambda value: pytest.fail("must authenticate first"))
    for headers in ({}, {"Authorization": "Bearer wrong"}):
        assert TestClient(app).get("/search/archive-document", params=archive.params, headers=headers).status_code == 401


@pytest.mark.parametrize("page", ["../outside.md", "/outside.md", "/raw/course-programmes/../../../outside.md", "/raw/course-programmes\\outside.md", "/raw//course-programmes/original.md"])
def test_page_path_cannot_escape_wiki(archive, page, monkeypatch):
    archive.hit.path = page
    monkeypatch.setattr(search.wiki_store, "page", lambda value: [archive.hit])  # Reach the filesystem guard, not an earlier missing-row check.
    response = TestClient(app).get("/search/archive-document", params={**archive.params, "page": page}, headers=AUTH)
    assert response.status_code == 404
    assert not archive.asked


def test_symlink_cannot_escape_raw(archive):
    outside = archive.raw.parents[3] / "outside.pdf"
    archive.raw.rename(outside)
    archive.raw.symlink_to(outside)
    assert TestClient(app).get("/search/archive-document", params=archive.params, headers=AUTH).status_code == 404


def test_byte_limit_is_enforced(archive, monkeypatch):
    from catix.wiki import preview_cache

    monkeypatch.setattr(preview_cache, "MAX_PDF_BYTES", len(PDF) - 1)
    assert TestClient(app).get("/search/archive-document", params=archive.params, headers=AUTH).status_code == 404


def test_non_pdf_is_not_served_even_with_a_matching_digest(archive):
    from catix.wiki.search_index import fingerprint

    body = b"<html>Not a PDF</html>"
    archive.remote["body"] = zipped([(MEMBER, body)])
    archive.record["sha256"] = hashlib.sha256(body).hexdigest()
    archive.raw.write_text(json.dumps({archive.key: archive.record}))
    archive.meta["sources"][0]["id"] = archive.record["sha256"][:12]
    text = "---\n" + yaml.safe_dump(archive.meta) + "---\n\nText."
    archive.page.write_text(text)
    archive.hit.page_sha = fingerprint(text)
    params = {**archive.params, "revision": fingerprint(text)}
    assert TestClient(app).get("/search/archive-document", params=params, headers=AUTH).status_code == 404


def test_stale_search_hit_is_not_enriched_with_the_new_page(archive):
    archive.page.write_text(archive.text + "Changed document.\n")
    assert search.to_source(archive.hit).archive_document is None


def test_retained_chunk_gets_a_new_source_identity_for_a_new_revision(archive):
    from catix.agent.sources import Collector
    from catix.wiki.search_index import fingerprint

    runtime = SimpleNamespace(state={"sources": {}}, config={})
    first = Collector(runtime)
    ref = first.add_wiki(archive.hit)
    runtime.state["sources"] = first.new
    text = archive.text + "New document metadata.\n"
    archive.page.write_text(text)
    archive.hit.page_sha = fingerprint(text)
    second = Collector(runtime)
    new_ref = second.add_wiki(archive.hit)
    assert new_ref != ref
    assert first.new[ref]["archive_document"]["revision"] == archive.params["revision"]
    assert second.new[new_ref]["archive_document"]["revision"] == fingerprint(text)


def test_saved_answer_sources_keep_their_identity_when_checkout_changes(archive):
    from catix.agent.sources import Collector, cite
    from catix.api.schemas import AskResponses

    collector = Collector(SimpleNamespace(state={"sources": {}}, config={}))
    ref = collector.add_wiki(archive.hit)
    cited = cite(f"Answer [{ref}].", collector.new)
    response = AskResponses(query="programme", answer=cited.answer, sources=cited.sources, messages=[])
    saved = response.model_dump_json()
    archive.page.write_text(archive.text + "New version.")
    restored = AskResponses.model_validate_json(saved)
    descriptor = restored.sources[0].archive_document
    assert descriptor is not None
    assert descriptor.revision == archive.params["revision"]
    assert TestClient(app).get("/search/archive-document", params={"page": descriptor.page, "revision": descriptor.revision}, headers=AUTH).status_code == 404


def test_real_sql_index_to_archive_preview(archive, monkeypatch):
    """An opt-in disposable PostgreSQL; real index writer, WikiHit query and HTTP endpoint."""
    import psycopg
    from psycopg.rows import dict_row
    from catix.db import pg
    from catix.wiki.chunks import cut
    from catix.wiki.search_index import write_page

    url = os.environ.get("ARCHIVE_PREVIEW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("requires a disposable ARCHIVE_PREVIEW_TEST_DATABASE_URL")
    with psycopg.connect(url, row_factory=dict_row) as conn:
        # TEMP tables shadow any public names and disappear on close.
        conn.execute("""CREATE TEMP TABLE wiki_pages (
            path text PRIMARY KEY, sha text, title text, type text, trust text, audience text[], resource text,
            status text, review text, source_warning text, stale_after date, issued date, indexed_at timestamptz)""")
        conn.execute("""CREATE TEMP TABLE wiki_chunks (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, path text, trust text, seq int, heading text,
            clause text, sha text, text text, search_text text, cites jsonb)""")
        meta, chunks = cut(archive.text)
        write_page(conn, archive.hit.path, archive.hit.page_sha, meta, chunks)

        @contextmanager
        def connection():
            yield conn

        monkeypatch.setattr(pg, "connection", connection)
        monkeypatch.setattr(search.wiki_store, "page", read_wiki_page)
        hits = read_wiki_page(archive.hit.path)
        assert hits[0].page_sha == archive.hit.page_sha
        source = search.to_source(hits[0])
        assert source.archive_document.page == archive.hit.path
        response = TestClient(app).get("/search/archive-document", params=archive.params, headers=AUTH)
        assert response.status_code == 200 and response.content == PDF
