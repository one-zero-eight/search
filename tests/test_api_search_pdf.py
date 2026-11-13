"""GET /search/pdf: the original PDF of a page of the wiki, for a frame on the site. The university's site is faked."""

import httpx
import pytest
from fastapi.testclient import TestClient

from catix.api import search
from catix.api.app import app
from catix.innohassle import token

AUTH = {"Authorization": "Bearer good"}
DOC = "https://innopolis.university/upload/iblock/6e9/Положение.pdf"
PDF = b"%PDF-1.7\n1 0 obj\n...%%EOF"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(token, "claims", lambda t: {"uid": "u1", "email": "a@innopolis.university", "telegram_id": 7} if t == "good" else None)
    monkeypatch.setattr(search.wiki_store, "has_resource", lambda url: url == DOC)
    return TestClient(app)


@pytest.fixture
def site(monkeypatch):
    """The university's site: `answers` maps a URL to its response; every request it got is in `asked`."""
    answers: dict[str, httpx.Response] = {}
    asked: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        asked.append(str(request.url))
        return answers.get(str(request.url), httpx.Response(404))

    monkeypatch.setattr(search, "pdf_http", lambda: httpx.AsyncClient(transport=httpx.MockTransport(handle), follow_redirects=False))
    site = type("Site", (), {"answers": answers, "asked": asked})
    return site


def pdf(**headers) -> httpx.Response:
    return httpx.Response(200, content=PDF, headers={"Content-Type": "application/pdf", "X-Frame-Options": "SAMEORIGIN", **headers})


def test_a_document_of_the_wiki_is_given_for_a_frame(client, site):
    site.answers[str(httpx.URL(DOC))] = pdf()
    answer = client.get("/search/pdf", params={"url": DOC}, headers=AUTH)
    assert answer.status_code == 200 and answer.content == PDF
    assert answer.headers["content-type"] == "application/pdf" and "x-frame-options" not in answer.headers
    assert answer.headers["content-disposition"].startswith("inline; filename*=UTF-8''%D0%9F")


def test_only_documents_of_the_wiki(client, site):
    assert client.get("/search/pdf", params={"url": "http://127.0.0.1:8080/x.pdf"}, headers=AUTH).status_code == 404
    assert client.get("/search/pdf", params={"url": DOC}).status_code == 401
    assert site.asked == []


def test_a_redirect_stays_on_the_site(client, site):
    files = "https://files.innopolis.university/doc.pdf"
    site.answers[str(httpx.URL(DOC))] = httpx.Response(302, headers={"Location": files})
    site.answers[files] = pdf()
    assert client.get("/search/pdf", params={"url": DOC}, headers=AUTH).content == PDF

    site.answers[files] = httpx.Response(302, headers={"Location": "http://10.0.0.1/doc.pdf"})
    assert client.get("/search/pdf", params={"url": DOC}, headers=AUTH).status_code == 502
    assert "http://10.0.0.1/doc.pdf" not in site.asked


def test_no_pdf_is_an_error(client, site):
    site.answers[str(httpx.URL(DOC))] = httpx.Response(200, text="<html>login</html>", headers={"Content-Type": "text/html"})
    assert client.get("/search/pdf", params={"url": DOC}, headers=AUTH).status_code == 502
    site.answers[str(httpx.URL(DOC))] = httpx.Response(500)
    assert client.get("/search/pdf", params={"url": DOC}, headers=AUTH).status_code == 502


def test_a_document_too_big_is_not_given(client, site, monkeypatch):
    monkeypatch.setattr(search, "PDF_MAX_BYTES", 10)
    site.answers[str(httpx.URL(DOC))] = pdf()
    assert client.get("/search/pdf", params={"url": DOC}, headers=AUTH).status_code == 502
