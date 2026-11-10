"""Recursive reading uses the existing providers and their page rules, not a second registry."""

from contextlib import nullcontext
import pytest

from catix.docs.sources import sites


@pytest.fixture
def providers(monkeypatch):
    monkeypatch.setattr(sites, "SITES", {
        "a": sites.Site("https://a.example/", "en", "Provider A", r"^(login|upload)(/|$)", sitemap=False, pause=0, aliases=("old-a.example",)),
        "b": sites.Site("https://b.example/", "en", "Provider B", r"^private(/|$)", sitemap=False, pause=0),
        "other": sites.Site("https://other.example/", "en", "Other site", r"^private(/|$)", sitemap=False, pause=0),
    })


def test_existing_providers_and_skip_rules_are_the_policy(providers):
    from catix.docs.sources import crawl

    assert crawl.provider("https://a.example/news") == "a"
    assert crawl.provider("https://old-a.example/news") == "a"
    assert crawl.provider("https://b.example/news") == "b"
    assert crawl.provider("https://child.a.example/news") == "a"
    assert crawl.provider("https://other.example/") == "other"
    assert crawl.provider("https://unknown.example/") is None
    assert crawl.provider("https://unknown.innopolis.university/") is None
    assert crawl.provider("https://a.example.evil.org/") is None
    assert crawl.provider("https://a.example/login") is None
    assert crawl.provider("https://b.example/private/page") is None
    # /upload is excluded from HTML crawling, not from the existing document path.
    assert crawl.provider("https://a.example/upload/rules.pdf") == "a"
    assert crawl.provider("https://a.example:8443/news") is None
    assert crawl.provider("https://user:password@a.example/news") is None


def test_material_links_follow_only_the_sites_of_the_catalog(providers):
    from catix.docs.sources import crawl

    text = " ".join([
        "https://a.example/docs/one.pdf,",
        "https://b.example/docs/two.docx.",
        "https://unknown.example/docs/three.pdf",
        "https://unknown.example/docs/four.pdf",
        "https://a.example/news",
    ])
    assert crawl.document_links(text, "https://a.example/docs/source.pdf") == [
        "https://a.example/docs/one.pdf", "https://b.example/docs/two.docx",
    ]


def test_archives_are_documents_not_html_pages(providers):
    from catix.docs.sources import crawl

    urls = ["https://a.example/upload/rules.zip", "https://b.example/programmes.7z"]
    text = " ".join(urls + ["https://unknown.example/private.zip"])
    assert crawl.document_links(text, "https://a.example/source.pdf") == urls
    assert crawl.text_page_links(text, "https://a.example/source.pdf") == []
    assert all(sites.DOC.search(url) for url in urls)


def test_linked_documents_are_persisted_and_are_input_to_regulations(providers, memory_files):
    from catix.docs.sources import regulations

    root = "sites/a/docs"
    memory_files.write_text(f"{root}/site-a-source.txt", "See https://b.example/docs/next.pdf for the next rule.")
    added = regulations.discover_linked_documents({
        "site-a-source": {"title": "Source", "url": "https://a.example/docs/source.pdf", "root": root, "section": "site/a", "ext": "pdf"}
    })
    assert list(added.values()) == ["site-a-source"]  # (the document added -> the one that names it)
    docs = regulations.all_docs()
    found = [d for d in docs.values() if d["url"] == "https://b.example/docs/next.pdf"]
    assert len(found) == 1 and found[0]["root"] == "sites/b/docs"
    assert memory_files.read_json(regulations.LINKED)["documents"]["https://b.example/docs/next.pdf"]["from"] == ["https://a.example/docs/source.pdf"]


def test_sites_fetch_follows_html_pages_across_trusted_providers(providers, monkeypatch, memory_files):
    import httpx
    from catix.docs.sources import sites

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
    assert memory_files.exists("sites/a/home.md") and memory_files.exists("sites/b/article.md")


def test_only_new_page_links_are_collected_from_existing_site_pages(providers, memory_files):
    from catix.docs.sources import sites

    memory_files.write_text("sites/a/home.md", "[new](https://b.example/new) [old](https://a.example/old) ![image](https://b.example/image.png)")
    sites.save("a", {"pages": {"old": {"url": "https://a.example/old"}}, "docs": {}})
    sites.save("b", {"pages": {}, "docs": {}})
    assert sites.new_linked_pages(["a"]) == {"b": {"https://b.example/new"}}


def test_alias_is_fetched_once_under_the_primary_host(providers, memory_files):
    import httpx

    requested = []
    def respond(request):
        requested.append(str(request.url))
        assert str(request.url) == "https://a.example/news"
        return httpx.Response(200, headers={"content-type": "text/html"}, text=(
            "<html><title>News</title><p>" + "Study rules and student opportunities. " * 20
            + '</p><a href="https://old-a.example/news">Again</a></html>'))

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        assert sites.fetch_site("a", sites.SITES["a"], client, start=["https://old-a.example/news"]) == 1
        assert requested == ["https://a.example/news"]
        pages = sites.load("a")["pages"]
        assert list(pages) == ["news"]
        assert pages["news"]["url"] == "https://a.example/news"
        memory_files.write_text("sites/a/news.md", "[old spelling](https://old-a.example/news)")
        assert sites.new_linked_pages(["a"]) == {}


def test_an_existing_alias_cache_keeps_its_slug(providers):
    import httpx

    def respond(request):
        return httpx.Response(200, headers={"content-type": "text/html"}, text=(
            "<html><title>News</title><p>" + "Study rules and student opportunities. " * 20 + "</p></html>"))

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        sites.fetch_site("a", sites.SITES["a"], client, start=["https://a.example/news"])
        index = sites.load("a")
        index["pages"]["news"]["url"] = "https://old-a.example/news"
        sites.save("a", index)
        assert sites.fetch_site("a", sites.SITES["a"], client, start=["https://a.example/news"]) == 0
    assert list(sites.load("a")["pages"]) == ["news"]


@pytest.mark.parametrize("blocked", ["old-a.example", "a.example"])
def test_alias_normalization_does_not_bypass_blocking(providers, monkeypatch, blocked):
    import httpx
    from catix.docs.sources import crawl

    monkeypatch.setattr(sites, "BLOCKED", frozenset({blocked}))
    url = "https://old-a.example/news"
    assert not sites._taken(sites.SITES["a"], url)
    assert crawl.page_links(f"[news]({url})", "https://b.example/") == []
    def forbidden(request) -> httpx.Response:
        raise AssertionError(f"blocked URL was requested: {request.url}")
    with httpx.Client(transport=httpx.MockTransport(forbidden)) as client:
        assert sites.fetch_site("a", sites.SITES["a"], client, start=[url]) == 0


def test_a_primary_host_wins_over_another_sites_alias(providers, monkeypatch):
    from dataclasses import replace
    from catix.docs.sources import crawl

    monkeypatch.setitem(sites.SITES, "a", replace(sites.SITES["a"], aliases=("b.example",)))
    assert crawl.provider("https://b.example/news", page=True) == "b"
    assert not sites._taken(sites.SITES["a"], "https://b.example/news")
    assert not sites._taken(sites.SITES["a"], "https://b.example/private/news")
    assert crawl.page_links("[private](https://b.example/private/news)", "https://a.example/") == []
    assert sites.address("https://b.example/news") == "https://b.example/news"


@pytest.mark.parametrize("url", [
    "https://old-a.example/login/private", "https://old-a.example/upload/rules.pdf",
    "https://a.example.evil.org/news", "https://a.example:8443/news", "https://a.example:bad/news",
    "https://user:password@old-a.example/news", "ftp://old-a.example/news", "//old-a.example/news",
    "https://[broken/news",
])
def test_page_policy_rejects_unsafe_or_excluded_aliases(providers, url):
    from catix.docs.sources import crawl

    assert not sites._taken(sites.SITES["a"], url)
    assert crawl.provider(url, page=True) is None


def test_alias_waves_compile_and_incremental_crawl_share_one_identity(providers, monkeypatch):
    import httpx
    from catix.docs.sources import regulations

    monkeypatch.setitem(sites.SITES, "child", sites.Site(
        "https://child.a.example/", "en", "Child", r"^private(/|$)", sitemap=False, pause=0, aliases=("old-child.example",)))
    sites.save("child", {"pages": {}, "docs": {}})  # a partial run enters only a site already read by the weekly crawl
    routes = {
        "https://a.example/": '<a href="https://old-child.example/news">Child</a>'
                              '<a href="https://unknown.a.example/news">Unknown</a>'
                              '<a href="https://unknown.example/news">Elsewhere</a>',
        "https://child.a.example/news": '<a href="https://old-a.example/">Parent</a>',
    }
    requested = []
    def respond(request):
        url = str(request.url)
        requested.append(url)
        return httpx.Response(200, headers={"content-type": "text/html"}, text=(
            f"<html><title>{request.url.host}</title><p>" + f"Study opportunities from {request.url.host}. " * 20
            + "</p>" + routes[url] + "</html>"))

    class Client(httpx.Client):
        def __init__(self, **kwargs):
            super().__init__(transport=httpx.MockTransport(respond), **kwargs)
    monkeypatch.setattr(httpx, "Client", Client)
    assert sites.fetch(["a"]) == 2
    assert requested == ["https://a.example/", "https://child.a.example/news"]
    assert sites.fetch(["a", "child"], only_new=True) == 0
    assert len(requested) == 2
    monkeypatch.setattr(regulations, "all_docs", lambda: {})
    docs, keep = sites.compile_all()
    pages = {d.path: d for d in docs}
    parent, child = pages["sites/a/home"], pages["sites/child/news"]
    assert keep == ("sites/b/", "sites/other/")  # (a site never read here keeps what other machines read)
    assert "[Child](https://old-child.example/news)" in parent.body
    assert "[Parent](https://old-a.example/)" in child.body
    assert "[Unknown](https://unknown.a.example/news)" in parent.body
    assert sites.compile_all()[0] == docs  # (the same cache gives the same documents)


def test_regulations_fetch_resumes_until_the_trusted_document_queue_is_empty(monkeypatch):
    from catix.docs.sources import regulations

    calls, waves = [], iter([["one"], ["two"], []])
    monkeypatch.setattr(regulations, "_fetch_once", lambda limit, prefixes, ocr: calls.append((limit, prefixes, ocr)) or next(waves))
    monkeypatch.setattr(regulations, "discover_linked_documents", lambda: {"site-b-linked-1-two": "one"} if len(calls) < 2 else {})
    assert regulations.fetch(limit=5, prefixes=("site-a-",)) == 2
    assert calls == [(5, ("site-a-",), True), (4, ("site-b-linked-1-two",), True)]  # (the document "one" names, of another provider)
    calls.clear()
    waves = iter([["three"], []])
    monkeypatch.setattr(regulations, "discover_linked_documents", dict)
    assert regulations.read_new(prefixes=("site-a-",), ocr=False) == ["three"]  # (the keys of those read; without OCR in every pass)
    assert calls == [(None, ("site-a-",), False)]


def test_a_run_of_a_few_sites_reads_the_documents_its_documents_name_and_not_every_unread_one(monkeypatch):
    """A request for the hotel read 54 documents of the university that no run had read yet: a pass after the first took every
    unread document. It takes those named by the documents of the run's sites and by those it read; the others are only
    remembered, for the weekly run."""
    from catix.docs.sources import regulations

    scopes, waves = [], iter([["site-hotel-rules"], ["site-university-linked-1-map"], ["site-media-linked-3-plan"]])
    found = iter([{"site-university-linked-1-map": "site-hotel-rules", "site-media-linked-2-old": "site-university-report"},
                  {"site-media-linked-3-plan": "site-university-linked-1-map"}, {}])
    monkeypatch.setattr(regulations, "_fetch_once", lambda limit, prefixes, ocr: scopes.append(prefixes) or next(waves))
    monkeypatch.setattr(regulations, "discover_linked_documents", lambda: next(found))
    assert regulations.read_new(prefixes=("site-hotel-",), ocr=False) == ["site-hotel-rules", "site-university-linked-1-map", "site-media-linked-3-plan"]
    assert scopes == [("site-hotel-",), ("site-university-linked-1-map",), ("site-media-linked-3-plan",)]  # (not the one an old report names)
    scopes.clear()
    waves = iter([["site-hotel-rules"], ["site-media-linked-2-old"]])
    found = iter([{"site-media-linked-2-old": "site-university-report"}, {}])
    assert regulations.read_new(ocr=False) == ["site-hotel-rules", "site-media-linked-2-old"]  # (the weekly run: every document found)
    assert scopes == [None, ("site-media-linked-2-old",)]


def test_regulations_fetch_downloads_a_document_found_in_the_previous_one(providers, monkeypatch, memory_files, tmp_path):
    import tempfile

    import httpx
    from catix.docs.sources import opendataloader, regulations

    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    monkeypatch.setattr(regulations, "DOCS", {})
    memory_files.write_json(regulations.LINKED, {"documents": {
        "https://a.example/docs/one.pdf": {"key": "site-a-linked-one", "title": "One", "ext": "pdf", "provider": "a", "from": []}
    }})
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
    assert memory_files.exists("sites/a/docs/site-a-linked-one.txt")
    assert any(p.startswith("sites/b/docs/site-b-linked-") and p.endswith(".txt") for p in memory_files.items)
    assert list(tmp_path.iterdir()) == []  # the downloaded originals are gone


def test_the_pages_a_document_names_are_those_of_trusted_sites(providers, memory_files):
    from catix.docs.sources import crawl, regulations

    text = ("Подробнее: https://a.example/news/item, https://b.example/private/x https://other.example/about "
            "https://unknown.example/page https://a.example/docs/one.pdf https://old-a.example/news/item. https://a.example/source")
    assert crawl.text_page_links(text, "https://a.example/source") == ["https://a.example/news/item", "https://other.example/about"]

    root = "docs"
    memory_files.write_text(f"{root}/site-a-1-rules.txt", "См. https://b.example/rules/ и https://a.example/news")
    with pytest.MonkeyPatch.context() as m:
        m.setattr(regulations, "all_docs", lambda: {
            "site-a-1-rules": {"title": "Rules", "url": "https://a.example/upload/rules.pdf", "root": root},
            "site-b-2-plan": {"title": "Plan", "url": "https://b.example/upload/plan.pdf", "root": root}})  # (not read: no text)
        assert regulations.page_links_of() == {"a": {"https://a.example/news"}, "b": {"https://b.example/rules/"}}
        assert regulations.page_links_of(["site-b-2-plan", "gone"]) == {}
