"""DeepSeek Search & Fetch: HTTP contracts, wiki first, official sites, citations, budgets, cache and failures."""

import base64
import json
import socket
import threading
from types import SimpleNamespace

import httpx
import pytest
from langchain_core.messages import HumanMessage, ToolMessage
from pydantic import SecretStr, ValidationError

from catix.agent import roles, sources, web_tools
from catix.agent.core import helper_tools
from catix.settings import Settings, settings

NEWS = "https://media.innopolis.university/news/new-building"
BLOG = "https://blog.example.com/innopolis"


def _runtime(*done: str, known: dict | None = None):
    """A tool's runtime in the docs helper's run, after the tools `done` returned."""
    messages = [HumanMessage("когда откроется новый корпус?"),
                *(ToolMessage(content="{}", tool_call_id=f"c{i}", name=name) for i, name in enumerate(done))]  # fmt: skip
    return SimpleNamespace(state={"messages": messages, "sources": known or {}}, config={"configurable": {"thread_id": "web"}},
                           tool_call_id="now", context=None)  # fmt: skip


def _out(command) -> tuple[dict, dict, dict | None]:
    message = command.update["messages"][0]
    return json.loads(message.content), command.update["sources"], message.artifact


def test_deepseek_key_controls_the_docs_helper(monkeypatch):
    configured = Settings(_env_file=None, deepseek_api_key="sk-test")  # type: ignore[call-arg]
    assert "deepseek_api_key" in Settings.model_fields
    monkeypatch.setattr(settings, "deepseek_api_key", configured.deepseek_api_key)
    assert web_tools.enabled()
    assert web_tools.NAMES <= {t.name for t in helper_tools(roles.ROLES["docs"])}
    assert "search_web" in roles.prompt("docs")
    monkeypatch.setattr(settings, "deepseek_api_key", None)
    assert not web_tools.enabled()
    assert not {t.name for t in helper_tools(roles.ROLES["docs"])} & web_tools.NAMES
    assert "search_web" not in roles.prompt("docs")


@pytest.fixture
def deepseek(monkeypatch):
    asked: list[tuple[str, dict]] = []

    def fake(request):
        path, body = request.url.path, json.loads(request.content)
        assert request.headers["Authorization"] == "Bearer sk-test"
        asked.append((path, body))
        if path == "/v1/tools/search":
            return httpx.Response(200, json={"results": [
                {"title": "Новый корпус", "url": NEWS, "summary": "Корпус откроется 1 декабря.", "content": "", "date": "2026-11-01T10:00:00Z", "rerank_score": 2.4},
                {"title": "Blog", "url": BLOG, "snippet": "Слухи о корпусе.", "date": None, "rerank_score": 1.8},
            ]})  # fmt: skip
        assert path == "/v1/tools/fetch"
        assert body == {"url": NEWS}, "Fetch gets only the URL, never the user's messages"
        return httpx.Response(200, json={"title": "Новый корпус", "content": "Корпус откроется 1 декабря, в 10:00."})

    monkeypatch.setattr(settings, "deepseek_api_key", SecretStr("sk-test"))
    monkeypatch.setattr(web_tools, "_down", (0.0, ""))
    with httpx.Client(base_url="https://api.deepseek.com", transport=httpx.MockTransport(fake)) as client:
        monkeypatch.setattr(web_tools, "_client", lambda: client)
        yield asked


def test_the_web_is_searched_only_after_the_knowledge_base(deepseek):
    payload, new, _ = _out(web_tools.search_web.func("новый корпус Иннополис", _runtime()))
    assert payload == {"error": web_tools.WIKI_FIRST} and not new and not deepseek
    payload, _, _ = _out(web_tools.search_web.func("новый корпус", _runtime("search_wiki", "search_web", "search_web")))
    assert "No more web searches" in payload["error"] and not deepseek


def test_a_web_search_keeps_to_the_official_sites_and_gives_refs(deepseek):
    payload, new, artifact = _out(web_tools.search_web.func("новый корпус", _runtime("search_wiki")))
    queries = [body["query"] for _, body in deepseek]
    assert all(q.startswith("новый корпус site:") and len(q) <= 128 for q in queries)
    assert {word.removeprefix("site:") for q in queries for word in q.split() if word.startswith("site:")} == set(web_tools.OFFICIAL_SITES)
    assert [(r["url"], r["official_site"], r["date"]) for r in payload["results"]] == [(NEWS, True, "2026-11-01")]
    ref = payload["results"][0]["ref"]
    assert new[ref] == {"key": f"web:{NEWS}", "web": True, "title": "Новый корпус", "link": NEWS, "official_site": True}
    assert artifact == {"relevant": [ref]}, "found something: no fallback to the chats helper"

    payload, _, _ = _out(web_tools.search_web.func("новый корпус", _runtime("search_wiki"), anywhere=True))
    assert deepseek[-1] == ("/v1/tools/search", {"query": "новый корпус", "count": web_tools.MAX_RESULTS, "need_content": False})
    assert [r["official_site"] for r in payload["results"]] == [True, False] and "may be wrong" in payload["note"]


def test_search_uses_deepseek_summaries_and_snippets(deepseek):
    payload, _, _ = _out(web_tools.search_web.func("новый корпус", _runtime("search_wiki"), anywhere=True))
    assert deepseek == [("/v1/tools/search", {"query": "новый корпус", "count": web_tools.MAX_RESULTS, "need_content": False})]
    assert [r["text"] for r in payload["results"]] == ["Корпус откроется 1 декабря.", "Слухи о корпусе."]
    assert "date" not in payload["results"][1]


@pytest.mark.parametrize(("query", "anywhere"), [("", False), ("   ", True), ("я" * 103, False), ("я" * 129, True)])
def test_invalid_queries_are_refused_without_truncation_or_a_request(deepseek, query, anywhere):
    payload, _, _ = _out(web_tools.search_web.func(query, _runtime("search_wiki"), anywhere=anywhere))
    assert "nonblank search query" in payload["error"] and not deepseek


@pytest.mark.parametrize(("size", "anywhere"), [(102, False), (128, True)])
def test_query_length_boundary_preserves_every_character(deepseek, size, anywhere):
    query = "я" * size
    payload, _, _ = _out(web_tools.search_web.func(query, _runtime("search_wiki"), anywhere=anywhere))
    assert payload["total"] > 0
    assert all(body["query"].startswith(query) and len(body["query"]) <= 128 for _, body in deepseek)
    assert len(deepseek) == (1 if anywhere else len(web_tools.OFFICIAL_SITES))


def test_official_results_are_filtered_deduplicated_and_ranked_before_the_limit(monkeypatch, deepseek):
    requests = []

    def respond(request):
        requests.append(request)
        hits = [{"url": BLOG, "rerank_score": 3}] * web_tools.MAX_RESULTS
        hits += [{"url": f"https://innopolis.ru/news/{i}", "summary": "я" * 1000, "rerank_score": i / 10} for i in range(8)]
        return httpx.Response(200, json={"results": hits})

    with httpx.Client(base_url=web_tools.DEEPSEEK, transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr(web_tools, "_client", lambda: client)
        payload, known, _ = _out(web_tools.search_web.func("новости", _runtime("search_wiki")))
        assert payload["total"] == len(known) == web_tools.MAX_RESULTS
        assert [r["url"] for r in payload["results"]] == [f"https://innopolis.ru/news/{i}" for i in range(7, 2, -1)]
        assert all(r["text"] == "я" * web_tools.TEXT_CHARS + " [...cut]" for r in payload["results"])
        count = len(requests)
        cached, _, _ = _out(web_tools.search_web.func("новости", _runtime("search_wiki", known=known)))
        assert cached == payload and len(requests) == count


@pytest.mark.parametrize("status", [401, 402, 403, 408, 429, 500, 504])
def test_provider_failures_pause_requests_but_keep_cached_results(monkeypatch, deepseek, status):
    first, known, _ = _out(web_tools.search_web.func("cached", _runtime("search_wiki"), anywhere=True))
    requests = []

    def fail(request):
        requests.append(request)
        return httpx.Response(status, json={"error": {"message": "private provider diagnostic"}})

    with httpx.Client(base_url=web_tools.DEEPSEEK, transport=httpx.MockTransport(fail)) as client:
        monkeypatch.setattr(web_tools, "_client", lambda: client)
        failed, _, _ = _out(web_tools.search_web.func("fails", _runtime("search_wiki"), anywhere=True))
        assert "error" in failed and "private provider diagnostic" not in failed["error"]
        cached, _, _ = _out(web_tools.search_web.func("cached", _runtime("search_wiki", known=known), anywhere=True))
        assert cached == first
        paused, _, _ = _out(web_tools.search_web.func("another", _runtime("search_wiki"), anywhere=True))
        assert paused == failed and len(requests) == 1


@pytest.mark.parametrize("status", [403, 404])
def test_fetch_page_failure_does_not_disable_other_searches(monkeypatch, deepseek, status):
    known = {"m3": {"key": f"web:{NEWS}", "web": True, "title": "Новый корпус", "link": NEWS, "official_site": True}}

    def respond(request):
        return httpx.Response(status if request.url.path.endswith("/fetch") else 200, json={"results": []})

    with httpx.Client(base_url=web_tools.DEEPSEEK, transport=httpx.MockTransport(respond)) as client:
        monkeypatch.setattr(web_tools, "_client", lambda: client)
        payload, _, _ = _out(web_tools.read_web_page.func(NEWS, _runtime("search_web", known=known)))
        assert "page could not be read" in payload["error"]
        payload, _, _ = _out(web_tools.search_web.func("another", _runtime("search_wiki"), anywhere=True))
        assert payload["total"] == 0 and "error" not in payload


def test_only_a_page_the_search_found_is_read(deepseek):
    known = {"m3": {"key": f"web:{NEWS}", "web": True, "title": "Новый корпус", "link": NEWS, "official_site": True}}
    payload, _, _ = _out(web_tools.read_web_page.func("https://evil.example.com/page", _runtime("search_web", known=known)))
    assert "Only a page that search_web found" in payload["error"] and not deepseek
    payload, new, _ = _out(web_tools.read_web_page.func(NEWS, _runtime("search_web", known=known)))
    assert payload["ref"] == "m3" and "1 декабря" in payload["text"] and not new, "the same page keeps its ref"
    assert deepseek == [("/v1/tools/fetch", {"url": NEWS})]
    payload, _, _ = _out(web_tools.read_web_page.func(NEWS, _runtime("search_web", "read_web_page", known=known)))
    assert "No more web reads" in payload["error"]


@pytest.mark.parametrize("content", ["", "page " * 1000])
def test_fetch_handles_empty_pages_and_bounds_the_text(monkeypatch, deepseek, content):
    known = {"m3": {"key": f"web:{NEWS}", "web": True, "title": "Новый корпус", "link": NEWS, "official_site": True}}
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"title": "Page", "content": content}))
    with httpx.Client(base_url=web_tools.DEEPSEEK, transport=transport) as client:
        monkeypatch.setattr(web_tools, "_client", lambda: client)
        payload, _, _ = _out(web_tools.read_web_page.func(NEWS, _runtime("search_web", known=known)))
        if content:
            assert payload["ref"] == "m3" and payload["text"] == content[:web_tools.PAGE_CHARS].rstrip() + " [...cut]"
        else:
            assert "page could not be read" in payload["error"]


def test_a_web_source_names_its_site_and_one_off_the_official_ones_is_from_the_web():
    registry = {
        "m0": {"key": f"web:{NEWS}", "web": True, "title": "Новый корпус", "link": NEWS, "official_site": True},
        "m1": {"key": f"web:{BLOG}", "web": True, "title": "Blog", "link": BLOG, "official_site": False},
    }
    cited = sources.cite("Корпус откроется 1 декабря [m0], а в блоге пишут иначе [m1].", registry)
    assert cited.answer == "Корпус откроется 1 декабря [1], а в блоге пишут иначе [2]."
    assert [(source.number, source.title, source.url, source.kind, source.official) for source in cited.sources] == [
        (1, "Новый корпус", NEWS, "web", True), (2, "Blog", BLOG, "web", False),
    ]


@pytest.mark.parametrize(("url", "official"), [
    ("https://innopolis.university/abiturientam", True), ("https://www.innopolis.com/news", True),
    ("https://campuslife.innopolis.ru/x", True), ("https://innopolis.university.evil.com/x", False),
    ("https://notinnopolis.ru/x", False),
])  # fmt: skip
def test_the_official_sites_are_the_universitys_and_the_citys_with_their_subdomains(url, official):
    assert web_tools.official(url) is official


@pytest.mark.parametrize("proxy", [None, "http://127.0.0.1:3128"])
def test_the_docs_helper_has_the_web_search_only_with_a_key_with_a_proxy_or_without(monkeypatch, proxy):
    docs = roles.ROLES["docs"]
    monkeypatch.setattr(settings, "deepseek_proxy", proxy and SecretStr(proxy))
    monkeypatch.setattr(settings, "deepseek_api_key", None)
    assert not {t.name for t in helper_tools(docs)} & web_tools.NAMES and "search_web" not in roles.prompt("docs")
    monkeypatch.setattr(settings, "deepseek_api_key", SecretStr("sk-test"))
    assert web_tools.NAMES <= {t.name for t in helper_tools(docs)} and "search_web" in roles.prompt("docs")
    assert not {t.name for t in helper_tools(roles.ROLES["chats"])} & web_tools.NAMES, "only the docs helper"


def test_without_a_proxy_deepseek_is_asked_directly(monkeypatch):
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(settings, "deepseek_proxy", None)
    web_tools._client.cache_clear()
    try:
        assert web_tools._client()._mounts == {}, "no proxy mounted"
        assert str(web_tools._client().base_url) == "https://api.deepseek.com"
    finally:
        web_tools._client.cache_clear()


def test_an_empty_key_or_proxy_in_env_is_none():
    unset = Settings(_env_file=None, deepseek_api_key="", deepseek_proxy=" ")  # type: ignore[call-arg]
    assert unset.deepseek_api_key is None and unset.deepseek_proxy is None


@pytest.mark.parametrize("url", ["socks5://u:p@h:1080", "http://bot:hunter2@host-without-port", "proxy.example:3128"])
def test_a_proxy_that_is_not_an_http_one_stops_the_start_without_showing_its_password(url):
    with pytest.raises(ValidationError, match="DEEPSEEK_PROXY is an HTTP proxy") as e:
        Settings(_env_file=None, deepseek_proxy=url)  # type: ignore[call-arg]
    assert "hunter2" not in str(e.value) and "u:p" not in str(e.value)


def _proxy(reply: bytes | None) -> tuple[str, list[bytes]]:
    """A proxy on 127.0.0.1 that keeps what it is asked and answers `reply`; None: nobody listens on its port."""
    server = socket.create_server(("127.0.0.1", 0))
    port, seen = server.getsockname()[1], []
    if reply is None:
        server.close()
        return f"http://bot:secret@127.0.0.1:{port}", seen

    def serve() -> None:
        while True:
            try:
                conn, _ = server.accept()
            except OSError:
                return
            with conn:
                seen.append(conn.recv(4096))
                conn.sendall(reply)

    threading.Thread(target=serve, daemon=True).start()
    return f"http://bot:secret@127.0.0.1:{port}", seen


@pytest.mark.parametrize("reply", [b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n", None], ids=["refuses", "nobody"])
def test_deepseek_is_asked_through_the_proxy_and_one_that_does_not_work_stops_the_web_for_a_while(monkeypatch, reply):
    url, seen = _proxy(reply)
    monkeypatch.setattr(settings, "deepseek_api_key", SecretStr("sk-test"))
    monkeypatch.setattr(settings, "deepseek_proxy", SecretStr(url))
    monkeypatch.setattr(settings, "redis_url", None)  # (nothing cached)
    monkeypatch.setattr(web_tools, "_down", (0.0, ""))
    web_tools._client.cache_clear()
    try:
        payload, _, _ = _out(web_tools.search_web.func("новый корпус", _runtime("search_wiki")))
        assert payload == {"error": "The web search is not available now (it cannot be reached): report without it."}
        if reply is not None:
            assert seen[0].startswith(b"CONNECT api.deepseek.com:443 ")
            assert b"Proxy-Authorization: Basic " + base64.b64encode(b"bot:secret") in seen[0]
        payload, _, _ = _out(web_tools.search_web.func("другой запрос", _runtime("search_wiki")))
        assert "cannot be reached" in payload["error"] and len(seen) == (0 if reply is None else 1), "not asked again yet"
    finally:
        web_tools._client.cache_clear()
