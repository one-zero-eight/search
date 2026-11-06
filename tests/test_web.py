"""The docs helper's web search (agent/web_tools.py), with Tavily faked: only after the knowledge base, the official sites
first, a few calls a question, pages cited with their site; without a key the helper has no web search."""

import json
from types import SimpleNamespace

import pytest
from langchain_core.messages import HumanMessage, ToolMessage
from pydantic import SecretStr

from catix.agent import roles, sources, web_tools
from catix.agent.core import helper_tools
from catix.settings import settings

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


@pytest.fixture
def tavily(monkeypatch):
    asked: list[tuple[str, dict]] = []

    def fake(path, body):
        asked.append((path, body))
        if path == "/search":
            return {"results": [
                {"title": "Новый корпус", "url": NEWS, "content": "Корпус откроется 1 декабря.", "published_date": "2026-11-01T10:00:00Z"},
                {"title": "Blog", "url": BLOG, "content": "Слухи о корпусе."},
            ]}  # fmt: skip
        return {"results": [{"url": body["urls"][0], "raw_content": "Корпус откроется 1 декабря, в 10:00."}], "failed_results": []}

    monkeypatch.setattr(web_tools, "_tavily", fake)
    return asked


def test_the_web_is_searched_only_after_the_knowledge_base(tavily):
    payload, new, _ = _out(web_tools.search_web.func("новый корпус Иннополис", _runtime()))
    assert payload == {"error": web_tools.WIKI_FIRST} and not new and not tavily
    payload, _, _ = _out(web_tools.search_web.func("новый корпус", _runtime("search_wiki", "search_web", "search_web")))
    assert "No more web searches" in payload["error"] and not tavily


def test_a_web_search_keeps_to_the_official_sites_and_gives_refs(tavily):
    payload, new, artifact = _out(web_tools.search_web.func("новый корпус", _runtime("search_wiki")))
    assert tavily[0][1]["include_domains"] == web_tools.OFFICIAL_SITES and tavily[0][1]["search_depth"] == "basic"
    assert [(r["url"], r["official_site"], r["date"]) for r in payload["results"]] == [(NEWS, True, "2026-11-01")]
    ref = payload["results"][0]["ref"]
    assert new[ref] == {"key": f"web:{NEWS}", "web": True, "title": "Новый корпус", "link": NEWS, "official_site": True}
    assert artifact == {"relevant": [ref]}, "found something: no fallback to the chats helper"

    payload, _, _ = _out(web_tools.search_web.func("новый корпус", _runtime("search_wiki"), anywhere=True))
    assert "include_domains" not in tavily[1][1]
    assert [r["official_site"] for r in payload["results"]] == [True, False] and "may be wrong" in payload["note"]


def test_only_a_page_the_search_found_is_read(tavily):
    known = {"m3": {"key": f"web:{NEWS}", "web": True, "title": "Новый корпус", "link": NEWS, "official_site": True}}
    payload, _, _ = _out(web_tools.read_web_page.func("https://evil.example.com/page", _runtime("search_web", known=known)))
    assert "Only a page that search_web found" in payload["error"] and not tavily
    payload, new, _ = _out(web_tools.read_web_page.func(NEWS, _runtime("search_web", known=known)))
    assert payload["ref"] == "m3" and "1 декабря" in payload["text"] and not new, "the same page keeps its ref"
    assert tavily[0][1]["query"] == "когда откроется новый корпус?"  # the question picks the parts of the page
    payload, _, _ = _out(web_tools.read_web_page.func(NEWS, _runtime("search_web", "read_web_page", known=known)))
    assert "No more web reads" in payload["error"]


def test_a_web_source_names_its_site_and_one_off_the_official_ones_is_from_the_web():
    registry = {
        "m0": {"key": f"web:{NEWS}", "web": True, "title": "Новый корпус", "link": NEWS, "official_site": True},
        "m1": {"key": f"web:{BLOG}", "web": True, "title": "Blog", "link": BLOG, "official_site": False},
    }
    cited = sources.cite("Корпус откроется 1 декабря [m0], а в блоге пишут иначе [m1].", registry)
    assert f"[1] [«Новый корпус»]({NEWS}) (media.innopolis.university)" in cited
    assert f"[2] [«Blog»]({BLOG}) (blog.example.com, из интернета)" in cited


@pytest.mark.parametrize(("url", "official"), [
    ("https://innopolis.university/abiturientam", True), ("https://www.innopolis.com/news", True),
    ("https://campuslife.innopolis.ru/x", True), ("https://innopolis.university.evil.com/x", False),
    ("https://notinnopolis.ru/x", False),
])  # fmt: skip
def test_the_official_sites_are_the_universitys_and_the_citys_with_their_subdomains(url, official):
    assert web_tools.official(url) is official


def test_the_docs_helper_has_the_web_search_only_with_a_key(monkeypatch):
    docs = roles.ROLES["docs"]
    monkeypatch.setattr(settings, "tavily_api_key", None)
    assert not {t.name for t in helper_tools(docs)} & web_tools.NAMES and "search_web" not in roles.prompt("docs")
    monkeypatch.setattr(settings, "tavily_api_key", SecretStr("tvly-test"))
    assert web_tools.NAMES <= {t.name for t in helper_tools(docs)} and "search_web" in roles.prompt("docs")
    assert not {t.name for t in helper_tools(roles.ROLES["chats"])} & web_tools.NAMES, "only the docs helper"
