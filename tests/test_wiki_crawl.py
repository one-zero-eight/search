"""Recursive reading uses the existing providers and their page rules, not a second registry."""

import json
from contextlib import nullcontext
import pytest

from catix.wiki.sources import sites


@pytest.fixture
def providers(tmp_path, monkeypatch):
    monkeypatch.setattr(sites, "ROOT", tmp_path / "raw" / "sites")
    monkeypatch.setattr(sites, "DOCS", tmp_path / "wiki" / "raw")
    monkeypatch.setattr(sites, "DISCOVERED", tmp_path / "raw" / "sites-discovered.json")
    monkeypatch.setattr(sites, "SITES", {
        "a": sites.Site("https://a.example/", "en", "Provider A", r"^(login|upload)(/|$)", sitemap=False, pause=0, aliases=("old-a.example",)),
        "b": sites.Site("https://b.example/", "en", "Provider B", r"^private(/|$)", sitemap=False, pause=0),
        "pending": sites.Site("https://pending.example/", "en", "Found site", "", sitemap=False, pause=0),
        "accepted": sites.Site("https://accepted.example/", "en", "Accepted site", "", sitemap=False, pause=0),
    })
    sites.DISCOVERED.parent.mkdir(parents=True)
    sites.DISCOVERED.write_text(json.dumps({"sites": {
        "pending.example": {"status": "pending"}, "accepted.example": {"status": "accepted"},
    }}))
    return tmp_path


def test_existing_providers_and_skip_rules_are_the_policy(providers):
    from catix.wiki.sources import crawl

    assert crawl.provider("https://a.example/news") == "a"
    assert crawl.provider("https://old-a.example/news") == "a"
    assert crawl.provider("https://b.example/news") == "b"
    assert crawl.provider("https://child.a.example/news") == "a"
    assert crawl.provider("https://accepted.example/") == "accepted"
    assert crawl.provider("https://pending.example/") is None
    assert crawl.provider("https://unknown.innopolis.university/") is None
    assert crawl.provider("https://a.example.evil.org/") is None
    assert crawl.provider("https://a.example/login") is None
    assert crawl.provider("https://b.example/private/page") is None
    # /upload is excluded from HTML crawling, not from the existing document path.
    assert crawl.provider("https://a.example/upload/rules.pdf") == "a"
    assert crawl.provider("https://a.example:8443/news") is None
    assert crawl.provider("https://user:password@a.example/news") is None


def test_material_links_follow_only_accepted_providers(providers):
    from catix.wiki.sources import crawl

    text = " ".join([
        "https://a.example/docs/one.pdf,",
        "https://b.example/docs/two.docx.",
        "https://pending.example/docs/three.pdf",
        "https://unknown.example/docs/four.pdf",
        "https://a.example/news",
    ])
    assert crawl.document_links(text, "https://a.example/docs/source.pdf") == [
        "https://a.example/docs/one.pdf", "https://b.example/docs/two.docx",
    ]


def test_linked_documents_are_persisted_and_are_input_to_regulations(providers):
    from catix.wiki.sources import regulations

    regulations.LINKED = providers / "raw" / "regulations" / "linked.json"
    (providers / "raw" / "a" / "docs").mkdir(parents=True)
    source = providers / "raw" / "a" / "docs" / "site-a-source.txt"
    source.write_text("See https://b.example/docs/next.pdf for the next rule.", encoding="utf-8")
    added = regulations.discover_linked_documents({
        "site-a-source": {"title": "Source", "url": "https://a.example/docs/source.pdf", "root": source.parent, "section": "site/a", "ext": "pdf"}
    })
    assert added == 1
    docs = regulations.all_docs()
    found = [d for d in docs.values() if d["url"] == "https://b.example/docs/next.pdf"]
    assert len(found) == 1 and found[0]["root"] == providers / "raw" / "sites" / "b" / "docs"
    assert json.loads(regulations.LINKED.read_text())["documents"]["https://b.example/docs/next.pdf"]["from"] == ["https://a.example/docs/source.pdf"]


def test_sites_fetch_follows_html_pages_across_trusted_providers(providers, monkeypatch):
    import httpx
    from catix.wiki.sources import sites

    monkeypatch.setattr(sites, "PAUSE", 0)
    routes = {
        "https://a.example/": f"<html><title>A</title><p>{'Study rules and student opportunities. ' * 20}</p><a href='https://b.example/article'>B</a></html>",
        "https://b.example/article": f"<html><title>B</title><p>{'Read university documents and student regulations. ' * 20}</p></html>",
    }

    class Client:
        def get(self, url):
            return httpx.Response(200, headers={"content-type": "text/html"}, text=routes[str(url)], request=httpx.Request("GET", url))

    monkeypatch.setattr(sites, "httpx", httpx)
    # fetch() owns the client in production; this direct call proves the recursive page hand-off.
    pending = {}
    sites.fetch_site("a", sites.SITES["a"], Client(), linked=pending)
    assert pending == {"b": {"https://b.example/article"}}
    sites.fetch_site("b", sites.SITES["b"], Client(), start=sorted(pending["b"]), linked={})
    assert (sites.ROOT / "a" / "home.md").exists() and (sites.ROOT / "b" / "article.md").exists()


def test_only_new_page_links_are_collected_from_existing_site_pages(providers):
    from catix.wiki.sources import sites

    (sites.ROOT / "a").mkdir(parents=True)
    (sites.ROOT / "a" / "home.md").write_text(
        "[new](https://b.example/new) [old](https://a.example/old) ![image](https://b.example/image.png)", encoding="utf-8")
    sites.save("a", {"pages": {"old": {"url": "https://a.example/old"}}, "docs": {}})
    sites.save("b", {"pages": {}, "docs": {}})
    assert sites.new_linked_pages(["a"]) == {"b": {"https://b.example/new"}}


def test_regulations_fetch_resumes_until_the_trusted_document_queue_is_empty(monkeypatch):
    from catix.wiki.sources import regulations

    calls, waves = [], iter([["one"], ["two"], []])
    monkeypatch.setattr(regulations, "_fetch_once", lambda limit, prefixes, ocr: calls.append((limit, prefixes, ocr)) or next(waves))
    monkeypatch.setattr(regulations, "discover_linked_documents", lambda: 1 if len(calls) < 2 else 0)
    assert regulations.fetch(limit=5, prefixes=("site-a-",)) == 2
    assert calls == [(5, ("site-a-",), True), (4, None, True)]
    calls.clear()
    waves = iter([["three"], []])
    monkeypatch.setattr(regulations, "discover_linked_documents", lambda: 0)
    assert regulations.read_new(prefixes=("site-a-",), ocr=False) == ["three"]  # (the keys of those read; without OCR in every pass)
    assert calls == [(None, ("site-a-",), False)]


def test_regulations_fetch_downloads_a_document_found_in_the_previous_one(providers, monkeypatch):
    import httpx
    from catix.wiki.sources import opendataloader, regulations

    regulations.ROOT = providers / "raw" / "regulations"
    regulations.LINKED = regulations.ROOT / "linked.json"
    regulations.SVEDEN_ROOT = providers / "raw" / "sveden"
    regulations.DOCS = {}
    regulations.LINKED.parent.mkdir(parents=True)
    regulations.LINKED.write_text(json.dumps({"documents": {
        "https://a.example/docs/one.pdf": {"key": "site-a-linked-one", "title": "One", "ext": "pdf", "provider": "a", "from": []}
    }}))
    monkeypatch.setattr(regulations, "PAUSE", 0)
    monkeypatch.setattr(regulations, "pages_of", lambda _: 1)
    monkeypatch.setattr(regulations, "to_pdf", lambda path: path)
    monkeypatch.setattr(opendataloader, "converted", lambda pdfs: nullcontext({}))
    monkeypatch.setattr(regulations, "layer_text", lambda pdf, converted=None: (
        "See https://b.example/docs/two.pdf" if pdf.name == "site-a-linked-one.pdf" else "No more links", "text layer"))

    requested = []
    def get(url, **kwargs):
        requested.append(url)
        return httpx.Response(200, content=b"not really a pdf", request=httpx.Request("GET", url))

    monkeypatch.setattr(regulations.httpx, "get", get)
    assert regulations.fetch(limit=5) == 2
    assert requested == ["https://a.example/docs/one.pdf", "https://b.example/docs/two.pdf"]
    assert (providers / "raw" / "sites" / "a" / "docs" / "site-a-linked-one.txt").exists()
    assert any(p.name.startswith("site-b-linked-") and p.suffix == ".txt" for p in (providers / "raw" / "sites" / "b" / "docs").iterdir())





def test_the_pages_a_document_names_are_those_of_trusted_sites(providers):
    from catix.wiki.sources import crawl, regulations

    text = ("Подробнее: https://a.example/news/item, https://b.example/private/x https://pending.example/about "
            "https://unknown.example/page https://a.example/docs/one.pdf https://old-a.example/news/item. https://a.example/source")
    assert crawl.text_page_links(text, "https://a.example/source") == ["https://a.example/news/item", "https://old-a.example/news/item"]

    regulations.LINKED = providers / "raw" / "regulations" / "linked.json"
    docs = providers / "raw" / "docs"
    docs.mkdir(parents=True)
    (docs / "site-a-1-rules.txt").write_text("См. https://b.example/rules/ и https://a.example/news", encoding="utf-8")
    import pytest as _pytest

    with _pytest.MonkeyPatch.context() as m:
        m.setattr(regulations, "all_docs", lambda: {
            "site-a-1-rules": {"title": "Rules", "url": "https://a.example/upload/rules.pdf", "root": docs},
            "site-b-2-plan": {"title": "Plan", "url": "https://b.example/upload/plan.pdf", "root": docs}})  # (not read: no text)
        assert regulations.page_links_of() == {"a": {"https://a.example/news"}, "b": {"https://b.example/rules/"}}
        assert regulations.page_links_of(["site-b-2-plan", "gone"]) == {}
