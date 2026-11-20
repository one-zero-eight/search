"""Exact archive previews: the metadata of the store, real ZIP decoder and synthetic HTTP."""

import hashlib
import os
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
import httpx
from fastapi.testclient import TestClient

from catix.api import search
from catix.api.app import app
from catix.db.docs import DocHit, page as read_wiki_page
from catix.innohassle import token
from catix.settings import settings
from tests.test_archive_preview_download import zipped

AUTH = {"Authorization": "Bearer good"}
ARCHIVE = "https://innopolis.university/documents/programmes.zip"
PDF = b"%PDF-1.7\noriginal first member\n%%EOF"
MEMBER = "2026/Первая программа.pdf"


@pytest.fixture
def archive(tmp_path, monkeypatch):
    from catix.docs.sources import archive_documents

    monkeypatch.setattr(settings, "archive_preview_cache", tmp_path / "api-cache")
    key = "rpd-" + hashlib.sha1(f"{ARCHIVE}/{MEMBER}".encode()).hexdigest()[:8] + "-first"
    digest = hashlib.sha256(PDF).hexdigest()
    path = f"course-programmes/{key}"
    hit = DocHit(id=1, path=path, seq=0, heading="Chapter", clause="", sha="chunk", text="Original text.", cites=[],
                 title="First programme", type="course-programme", trust="official", audience=[], resource=ARCHIVE,
                 status=None, review=None, source_warning=None, stale_after=None, issued=None, page_sha="a1b2c3d4e5f60718",
                 archive_member=MEMBER, archive_sha256=digest)
    hits = {path: hit}
    monkeypatch.setattr(search.doc_store, "page", lambda value: [hits[value]] if value in hits else [])
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
    return SimpleNamespace(hit=hit, hits=hits, key=key, digest=digest, remote=remote, asked=asked,
                           params={"page": path, "revision": hit.page_sha})


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
    from catix.docs import preview_cache

    def fail(*args):
        raise error

    monkeypatch.setattr(preview_cache, "read", fail)
    response = TestClient(app).get("/search/archive-document", params=archive.params, headers=AUTH)
    assert response.status_code == status
    assert "private path" not in response.text


def test_search_and_answer_sources_keep_the_exact_member(archive, monkeypatch):
    from catix.agent.sources import Collector, cite

    expected = {**archive.params, "member": MEMBER}
    monkeypatch.setattr(search.doc_store, "search", lambda *args, **kwargs: [archive.hit])
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


def test_a_guide_document_is_cited_as_a_guide(archive):
    from dataclasses import replace
    from catix.agent.sources import Collector, cite

    guide = replace(archive.hit, path="guide/telegram.en", archive_member=None, trust="wiki")
    collector = Collector(SimpleNamespace(state={"sources": {}}, config={}))
    ref = collector.add_wiki(guide)
    assert cite(f"Notifications [{ref}].", collector.new).sources[0].kind == "guide"


def test_same_title_members_are_not_collapsed(archive):
    from dataclasses import replace
    from catix.agent import sources

    member = "2026/Вторая программа.pdf"
    key = "rpd-" + hashlib.sha1(f"{ARCHIVE}/{member}".encode()).hexdigest()[:8] + "-second"
    second = replace(archive.hit, id=2, path=f"course-programmes/{key}", page_sha="b1b2c3d4e5f60718", archive_member=member)
    cards = search.to_responses([archive.hit, archive.hit, second], search.ALL_SOURCES)
    assert len(cards) == 2
    collector = sources.Collector(SimpleNamespace(state={"sources": {}}, config={}))
    first_ref, second_ref = collector.add_wiki(archive.hit), collector.add_wiki(second)
    answer = sources.cite(f"First [{first_ref}], second [{second_ref}].", collector.new)
    assert answer.answer == "First [1], second [2]."
    assert len(answer.sources) == 2
    assert [source.archive_document.member for source in answer.sources] == [MEMBER, member]


@pytest.mark.parametrize("change", ["file_changed", "file_missing", "index_changed", "wrong_revision", "wrong_digest", "unknown_page"])
def test_never_substitute_a_different_member_or_revision(archive, change):
    params = dict(archive.params)
    if change == "file_changed":
        archive.remote["body"] = zipped([(MEMBER, b"%PDF-1.7\nnew version\n%%EOF")])
    elif change == "file_missing":
        archive.remote["body"] = zipped([("other.pdf", PDF)])
    elif change == "index_changed":
        archive.hit.page_sha = "f" * 16  # (the page was indexed again: the old revision is gone)
    elif change == "wrong_revision":
        params["revision"] = "f" * 16
    elif change == "wrong_digest":
        archive.hit.archive_sha256 = "f" * 63  # (not a digest: closed)
    else:
        params["page"] = "course-programmes/not-indexed"
    response = TestClient(app).get("/search/archive-document", params=params, headers=AUTH)
    assert response.status_code == 404
    assert "unavailable" in response.json()["detail"]


def test_authentication_precedes_lookup(archive, monkeypatch):
    monkeypatch.setattr(search.doc_store, "page", lambda value: pytest.fail("must authenticate first"))
    for headers in ({}, {"Authorization": "Bearer wrong"}):
        assert TestClient(app).get("/search/archive-document", params=archive.params, headers=headers).status_code == 401


@pytest.mark.parametrize("page", ["../outside.md", "/outside.md", "course-programmes/../../outside", "course-programmes\\outside",
                                  "/raw/course-programmes/original.md", "regulations/unknown"])
def test_unknown_page_is_not_found_and_downloads_nothing(archive, page):
    response = TestClient(app).get("/search/archive-document", params={**archive.params, "page": page}, headers=AUTH)
    assert response.status_code == 404
    assert not archive.asked


def test_byte_limit_is_enforced(archive, monkeypatch):
    from catix.docs import preview_cache

    monkeypatch.setattr(preview_cache, "MAX_PDF_BYTES", len(PDF) - 1)
    assert TestClient(app).get("/search/archive-document", params=archive.params, headers=AUTH).status_code == 404


def test_non_pdf_is_not_served_even_with_a_matching_digest(archive):
    body = b"<html>Not a PDF</html>"
    archive.remote["body"] = zipped([(MEMBER, body)])
    archive.hit.archive_sha256 = hashlib.sha256(body).hexdigest()
    assert TestClient(app).get("/search/archive-document", params=archive.params, headers=AUTH).status_code == 404


def test_a_hit_without_an_archive_member_has_no_preview(archive):
    from dataclasses import replace

    assert search.to_source(replace(archive.hit, archive_member=None)).archive_document is None
    assert search.to_source(replace(archive.hit, archive_sha256=None)).archive_document is None


def test_retained_chunk_gets_a_new_source_identity_for_a_new_revision(archive):
    from catix.agent.sources import Collector

    runtime = SimpleNamespace(state={"sources": {}}, config={})
    first = Collector(runtime)
    ref = first.add_wiki(archive.hit)
    runtime.state["sources"] = first.new
    archive.hit.page_sha = "e" * 16
    second = Collector(runtime)
    new_ref = second.add_wiki(archive.hit)
    assert new_ref != ref
    assert first.new[ref]["archive_document"]["revision"] == archive.params["revision"]
    assert second.new[new_ref]["archive_document"]["revision"] == "e" * 16


def test_saved_answer_sources_keep_their_identity_when_the_page_is_indexed_again(archive):
    from catix.agent.sources import Collector, cite
    from catix.api.schemas import AskResponses

    collector = Collector(SimpleNamespace(state={"sources": {}}, config={}))
    ref = collector.add_wiki(archive.hit)
    cited = cite(f"Answer [{ref}].", collector.new)
    response = AskResponses(query="programme", answer=cited.answer, sources=cited.sources, messages=[])
    saved = response.model_dump_json()
    archive.hit.page_sha = "e" * 16
    restored = AskResponses.model_validate_json(saved)
    descriptor = restored.sources[0].archive_document
    assert descriptor is not None
    assert descriptor.revision == archive.params["revision"]
    assert TestClient(app).get("/search/archive-document", params={"page": descriptor.page, "revision": descriptor.revision}, headers=AUTH).status_code == 404


def test_real_sql_index_to_archive_preview(archive, monkeypatch):
    """An opt-in disposable PostgreSQL; real store writer, DocHit query and HTTP endpoint."""
    import psycopg
    from psycopg.rows import dict_row
    from catix.db import pg
    from catix.docs import store
    from catix.docs.chunks import cut

    url = os.environ.get("ARCHIVE_PREVIEW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("requires a disposable ARCHIVE_PREVIEW_TEST_DATABASE_URL")
    document = store.Document(
        path=archive.hit.path,
        meta={"type": "course-programme", "title": "First programme", "resource": ARCHIVE, "archive_member": MEMBER,
              "archive_sha256": archive.digest, "sources": [{"resource": ARCHIVE, "id": archive.digest[:12]}]},
        body="# First programme\n\nOriginal text.\n")
    revision = store.fingerprint(document)
    with psycopg.connect(url, row_factory=dict_row) as conn:
        # TEMP tables shadow any public names and disappear on close.
        conn.execute("""CREATE TEMP TABLE documents (
            path text PRIMARY KEY, sha text, title text, type text, trust text, audience text[], resource text,
            status text, review text, source_warning text, stale_after date, issued date, indexed_at timestamptz,
            body text NOT NULL DEFAULT '', meta jsonb NOT NULL DEFAULT '{}')""")
        conn.execute("""CREATE TEMP TABLE document_chunks (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, path text, trust text, seq int, heading text,
            clause text, sha text, text text, search_text text, cites jsonb, copy_of bigint)""")
        store.write_page(conn, document, revision, cut(document.body))

        @contextmanager
        def connection():
            yield conn

        monkeypatch.setattr(pg, "connection", connection)
        monkeypatch.setattr(search.doc_store, "page", read_wiki_page)
        hits = read_wiki_page(document.path)
        assert hits[0].page_sha == revision and (hits[0].archive_member, hits[0].archive_sha256) == (MEMBER, archive.digest)
        source = search.to_source(hits[0])
        assert source.archive_document.page == document.path
        response = TestClient(app).get("/search/archive-document", params={"page": document.path, "revision": revision}, headers=AUTH)
        assert response.status_code == 200 and response.content == PDF
        assert TestClient(app).get("/search/archive-document", params={"page": "regulations/none", "revision": revision}, headers=AUTH).status_code == 404
