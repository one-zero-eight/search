"""Recursive reading uses the existing providers and their page rules, not a second registry."""

from contextlib import nullcontext

import httpx
import pytest

from catix.docs import frontier, notes
from catix.docs.sources import crawl, regulations, sites
from tests import crawl_helpers as h


@pytest.fixture(autouse=True)
def fresh_caches(monkeypatch):
    monkeypatch.setattr(sites, "_common", {})
    monkeypatch.setattr(sites, "_robots", {})


@pytest.fixture
def providers(monkeypatch):
    monkeypatch.setattr(sites, "SITES", {
        "a": sites.Site("https://a.example/", "en", "Provider A", r"^(login|upload)(/|$)", sitemap=False, pause=0, aliases=("old-a.example",)),
        "b": sites.Site("https://b.example/", "en", "Provider B", r"^private(/|$)", sitemap=False, pause=0),
        "other": sites.Site("https://other.example/", "en", "Other site", r"^private(/|$)", sitemap=False, pause=0),
    })


def test_existing_providers_and_skip_rules_are_the_policy(providers):
    assert crawl.provider("https://a.example/news") == "a"
    assert crawl.provider("https://old-a.example/news") == "a"
    assert crawl.provider("https://b.example/news") == "b"
    assert crawl.provider("https://child.a.example/news") is None
    assert crawl.provider("https://child.a.example/rules.pdf") is None  # (a document on a subdomain is not a's either)
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
    urls = ["https://a.example/upload/rules.zip", "https://b.example/programmes.7z"]
    text = " ".join(urls + ["https://unknown.example/private.zip"])
    assert crawl.document_links(text, "https://a.example/source.pdf") == urls
    assert crawl.text_page_links(text, "https://a.example/source.pdf") == []
    assert all(sites.DOC.search(url) for url in urls)


def test_the_documents_a_document_names_become_rows_of_the_frontier(providers, docs_db):
    source = h.put("https://a.example/docs/source.pdf", "a", kind="document", doc_key="site-a-source")
    notes.put_text("site-a-source", "", "See https://b.example/docs/next.pdf for the next rule.")
    assert frontier.documents_read(["site-a-source"]) == {source.address}
    (found,) = h.rows("b", "document").values()
    assert found.url == "https://b.example/docs/next.pdf" and found.doc_key == sites.doc_key("b", found.url) and found.priority == frontier.NEW
    assert [key for key, d in regulations.all_docs().items() if d["url"] == found.url] == [found.doc_key]  # (the document added is one of the regulations)
    assert [r["dst"] for r in docs_db.execute("SELECT dst FROM crawl_links WHERE src = %s", (source.address,)).fetchall()] == [found.address]
    assert h.row_of(source.url).state == "new"  # (no note yet: it is read)


def test_reading_a_page_adds_the_pages_of_the_trusted_providers_it_links(providers, docs_db):
    routes = {
        "https://a.example/": f"<html><title>A</title><p>{'Study rules and student opportunities. ' * 20}</p><a href='https://b.example/article'>B</a></html>",
        "https://b.example/article": f"<html><title>B</title><p>{'Read university documents and student regulations. ' * 20}</p></html>",
    }

    class Client:
        def get(self, url):
            return httpx.Response(200, headers={"content-type": "text/html"}, text=routes[str(url)], request=httpx.Request("GET", url))

    start = h.put("https://a.example/", "a", pinned=True)
    assert sites.read_page(Client(), start) is True
    article = h.row_of("https://b.example/article")
    assert (article.site, article.kind, article.state) == ("b", "page", "new")  # (b's own crawl reads it, as it reads any page of b)
    assert sites.read_page(Client(), article) is True
    assert [(r.site, r.slug) for r in h.rows(kind="page").values()] == [("a", "home"), ("b", "article")]


def test_only_the_addresses_that_are_not_rows_yet_are_added_from_a_page(providers, docs_db):
    h.page("https://a.example/old", "a", "old", "Old words of the page " * 20)

    class Client:
        def get(self, url):
            html = ("<html><title>A</title><p>" + "Study rules and student opportunities. " * 20 +
                    "</p><a href='https://b.example/new'>new</a> <a href='https://a.example/old'>old</a> <img src='https://b.example/image.png'></html>")
            return httpx.Response(200, headers={"content-type": "text/html"}, text=html, request=httpx.Request("GET", url))

    sites.read_page(Client(), h.put("https://a.example/", "a", pinned=True))
    assert set(h.rows()) == {"https://a.example", "https://a.example/old", "https://b.example/new"}
    assert h.row_of("https://a.example/old").state == "ok" and h.row_of("https://b.example/new").state == "new"


def test_alias_is_fetched_once_under_the_primary_host(providers, docs_db):
    requested = []

    def respond(request):
        requested.append(str(request.url))
        assert str(request.url) in ("https://a.example/", "https://a.example/news")
        links = '<a href="https://old-a.example/news">News</a>' if request.url.path == "/" else '<a href="https://old-a.example/news">Again</a>'
        return httpx.Response(200, headers={"content-type": "text/html"}, text=(
            "<html><title>News</title><p>" + "Study rules and student opportunities. " * 20 + f"</p>{links}</html>"))

    h.put("https://a.example/", "a", pinned=True)
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        assert h.crawl(client) == 2
    assert requested == ["https://a.example/", "https://a.example/news"]
    assert sorted(h.by_slug("a")) == ["home", "news"] and h.by_slug("a")["news"].url == "https://a.example/news"
    assert len(h.rows()) == 2  # (the alias is the same address: no row of its own)


def test_an_existing_alias_row_keeps_its_slug(providers, docs_db):
    def respond(request):
        return httpx.Response(200, headers={"content-type": "text/html"}, text=(
            "<html><title>News</title><p>" + "Study rules and student opportunities. " * 20 + "</p></html>"))

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        row = h.put("https://a.example/news", "a")
        assert sites.read_page(client, row) is True
        docs_db.execute("UPDATE crawl_urls SET url = 'https://old-a.example/news'")
        assert sites.read_page(client, h.row_of("https://a.example/news")) is False
    assert list(h.by_slug("a")) == ["news"] and len(h.rows()) == 1


@pytest.mark.parametrize("blocked", ["old-a.example", "a.example"])
def test_alias_normalization_does_not_bypass_blocking(providers, monkeypatch, docs_db, blocked):
    monkeypatch.setattr(sites, "BLOCKED", frozenset({blocked}))
    url = "https://old-a.example/news"
    assert not sites._taken(sites.SITES["a"], url)
    assert crawl.text_page_links(f"[news]({url})", "https://b.example/") == []

    def forbidden(request) -> httpx.Response:
        raise AssertionError(f"blocked URL was requested: {request.url}")

    with httpx.Client(transport=httpx.MockTransport(forbidden)) as client:
        row = h.put(url, "a")
        assert sites.read_page(client, row) is False
    assert (row.state, row.why, row.next_at) == ("gone", "not taken", None)


def test_a_primary_host_wins_over_another_sites_alias(providers, monkeypatch):
    from dataclasses import replace

    monkeypatch.setitem(sites.SITES, "a", replace(sites.SITES["a"], aliases=("b.example",)))
    assert crawl.provider("https://b.example/news", page=True) == "b"
    assert not sites._taken(sites.SITES["a"], "https://b.example/news")
    assert not sites._taken(sites.SITES["a"], "https://b.example/private/news")
    assert crawl.text_page_links("[private](https://b.example/private/news)", "https://a.example/") == []
    assert sites.address("https://b.example/news") == "https://b.example/news"


@pytest.mark.parametrize("url", [
    "https://old-a.example/login/private", "https://old-a.example/upload/rules.pdf",
    "https://a.example.evil.org/news", "https://a.example:8443/news", "https://a.example:bad/news",
    "https://user:password@old-a.example/news", "ftp://old-a.example/news", "//old-a.example/news",
    "https://[broken/news",
])
def test_page_policy_rejects_unsafe_or_excluded_aliases(providers, url):
    assert not sites._taken(sites.SITES["a"], url)
    assert crawl.provider(url, page=True) is None


def test_alias_pages_compile_and_the_crawl_share_one_identity(providers, monkeypatch, docs_db):
    monkeypatch.setitem(sites.SITES, "child", sites.Site(
        "https://child.a.example/", "en", "Child", r"^private(/|$)", sitemap=False, pause=0, aliases=("old-child.example",)))
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

    h.put("https://a.example/", "a", pinned=True)
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        assert h.crawl(client, ("a", "child")) == 2
        assert requested == ["https://a.example/", "https://child.a.example/news"]  # (the alias of child is child's page; a's link back is a's own row)
        assert h.crawl(client, ("a", "child")) == 0
    assert len(requested) == 2 and set(h.rows()) == {"https://a.example", "https://child.a.example/news"}  # (an unknown host is a link, not a row)
    docs, keep = sites.compile_all()
    pages = {d.path: d for d in docs}
    parent, child = pages["sites/a/home"], pages["sites/child/news"]
    assert keep == ("sites/b/", "sites/other/")  # (a site never read here keeps what other machines read)
    assert "[Child](https://old-child.example/news)" in parent.body
    assert "[Parent](https://old-a.example/)" in child.body
    assert "[Unknown](https://unknown.a.example/news)" in parent.body
    assert sites.compile_all()[0] == docs  # (the same rows give the same documents)


def test_read_new_notes_what_it_read_in_the_rows_of_the_frontier(monkeypatch):
    calls = []
    monkeypatch.setattr(regulations, "_fetch_once", lambda limit, prefixes, ocr: calls.append((limit, prefixes, ocr)) or ["three"])
    monkeypatch.setattr(frontier, "documents_read", lambda keys: calls.append(keys) or set())
    assert regulations.read_new(prefixes=("site-a-",), ocr=False) == ["three"]  # (the keys of those read; without OCR in every pass)
    assert calls == [(None, ("site-a-",), False), ["three"]]


def test_regulations_read_new_downloads_a_document_found_in_the_previous_one(providers, monkeypatch, docs_db, tmp_path):
    import tempfile

    from catix.docs.sources import opendataloader

    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    monkeypatch.setattr(regulations, "DOCS", {})
    h.put("https://a.example/docs/one.pdf", "a", kind="document", doc_key="site-a-linked-one", ext="pdf")
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
    assert regulations.read_new(limit=5) == ["site-a-linked-one"]
    assert [r.url for r in h.rows("b", "document").values()] == ["https://b.example/docs/two.pdf"]  # (found in its text)
    assert len(regulations.read_new(limit=5)) == 1
    assert requested == ["https://a.example/docs/one.pdf", "https://b.example/docs/two.pdf"]
    assert notes.has_text("site-a-linked-one")
    (two,) = h.rows("b", "document").values()
    assert two.doc_key.startswith("site-b-") and notes.has_text(two.doc_key) and two.state == "ok"
    assert list(tmp_path.iterdir()) == []  # the downloaded originals are gone


def test_the_pages_a_document_names_are_those_of_trusted_sites(providers, docs_db):
    text = ("Подробнее: https://a.example/news/item, https://b.example/private/x https://other.example/about "
            "https://unknown.example/page https://a.example/docs/one.pdf https://old-a.example/news/item. https://a.example/source")
    assert crawl.text_page_links(text, "https://a.example/source") == ["https://a.example/news/item", "https://other.example/about"]

    h.put("https://a.example/upload/rules.pdf", "a", kind="document", doc_key="site-a-1-rules")
    h.put("https://b.example/upload/plan.pdf", "b", kind="document", doc_key="site-b-2-plan")
    notes.put_text("site-a-1-rules", "", "См. https://b.example/rules/ и https://a.example/news")
    assert frontier.documents_read(["site-a-1-rules", "site-b-2-plan", "gone"]) == {sites.address("https://a.example/upload/rules.pdf"), sites.address("https://b.example/upload/plan.pdf")}  # (not read: no text; gone: no row)
    assert {(r.site, r.url) for r in h.rows(kind="page").values()} == {("a", "https://a.example/news"), ("b", "https://b.example/rules/")}
    assert h.row_of("https://b.example/upload/plan.pdf").state == "new" and h.row_of("https://a.example/upload/rules.pdf").state == "new"
