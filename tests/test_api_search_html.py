"""GET /search/html: the page of the wiki without its scripts, for a sandboxed frame on the site. The university's site is faked."""

import httpx
import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from catix.api import search
from catix.api.app import app
from catix.innohassle import token

AUTH = {"Authorization": "Bearer good"}
PAGE = "https://innopolis.university/team-rector/"
WORDS = "Ректор университета Иннополис руководит всем университетом и отвечает за его развитие в целом и по частям"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(token, "claims", lambda t: {"uid": "u1", "email": "a@innopolis.university", "telegram_id": 7} if t == "good" else None)
    monkeypatch.setattr(search.doc_store, "has_resource", lambda url: url == PAGE)
    return TestClient(app)


@pytest.fixture
def site(monkeypatch):
    """The university's site: `answers` maps a URL to its response; every request it got is in `asked`."""
    answers: dict[str, httpx.Response] = {}
    asked: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        asked.append(str(request.url))
        return answers.get(str(request.url), httpx.Response(404))

    monkeypatch.setattr(search, "site_http", lambda: httpx.AsyncClient(transport=httpx.MockTransport(handle), follow_redirects=False))
    return type("Site", (), {"answers": answers, "asked": asked})


def html(body: str, **headers) -> httpx.Response:
    return httpx.Response(200, content=body.encode("cp1251"), headers={"Content-Type": "text/html; charset=windows-1251", **headers})


def get(client):
    return client.get("/search/html", params={"url": PAGE}, headers=AUTH)


def test_a_page_of_the_wiki_is_given_without_its_scripts(client, site):
    site.answers[PAGE] = html(
        "<html><head><title>Ректор</title><script>x()</script><meta http-equiv='refresh' content='0;url=/'></head>"
        f'<body onload="x()"><p>{WORDS}</p><img src="data:," data-src="/a.png"><a href="javascript:x()">a</a>'
        "<iframe src='/f'></iframe></body></html>",
        **{"X-Frame-Options": "SAMEORIGIN"},
    )
    answer = get(client)
    assert answer.status_code == 200 and answer.headers["content-type"].startswith("text/html")
    assert "x-frame-options" not in answer.headers and answer.headers["content-security-policy"].startswith("sandbox")
    soup = BeautifulSoup(answer.text, "html.parser")
    assert not soup.find_all(["script", "iframe"]) and "onload" not in soup.body.attrs
    assert "href" not in soup.a.attrs and soup.img["src"] == "/a.png"
    base = soup.head.find("base")
    assert base["href"] == PAGE and base["target"] == "_blank" and soup.find_all("base") == [base]
    assert "script-src 'none'" in soup.find("meta", attrs={"http-equiv": "Content-Security-Policy"})["content"]
    assert soup.find("meta", attrs={"http-equiv": "refresh"}) is None
    assert WORDS in soup.p.text


def test_only_pages_of_the_wiki(client, site):
    assert client.get("/search/html", params={"url": "https://x.example/"}, headers=AUTH).status_code == 404
    assert client.get("/search/html", params={"url": PAGE}).status_code == 401
    assert site.asked == []


def test_a_redirect_stays_on_the_host(client, site):
    www = "https://www.innopolis.university/team-rector/"
    site.answers[PAGE] = httpx.Response(302, headers={"Location": www})
    site.answers[www] = html(f"<html><head><title>Ректор</title></head><body><p>{WORDS}</p></body></html>")
    answer = get(client)
    assert answer.status_code == 200 and BeautifulSoup(answer.text, "html.parser").base["href"] == www

    sso = "https://sso.innopolis.university/login"
    site.answers[PAGE] = httpx.Response(302, headers={"Location": sso})
    assert get(client).status_code == 502
    assert sso not in site.asked


@pytest.mark.parametrize("answer", [
    html('<html><body><noscript>You need to enable JavaScript to run this app.</noscript><div id="root"></div></body></html>'),
    html(f'<html><head><title>Вход</title></head><body><p>{WORDS}</p><input type="password"></body></html>'),
    html(f"<html><head><title>Just a moment...</title></head><body><p>{WORDS}</p></body></html>"),
    httpx.Response(200, content=b"%PDF-1.7", headers={"Content-Type": "application/pdf"}),
    httpx.Response(500),
])
def test_what_is_not_the_page_is_an_error(client, site, answer):
    site.answers[PAGE] = answer
    assert get(client).status_code == 502
