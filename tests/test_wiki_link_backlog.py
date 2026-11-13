"""Old links become readable when their provider is approved, without refreshing their source page."""

import contextlib
from dataclasses import asdict

import httpx
import pytest
import yaml

from catix.wiki import cli, compile as compiler, paths, sources
from catix.wiki.sources import chandra, discover, opendataloader, regulations, sites


@pytest.fixture
def backlog(tmp_path, monkeypatch):
    monkeypatch.setattr(sites, "ROOT", tmp_path / "raw" / "sites")
    monkeypatch.setattr(sites, "DOCS", tmp_path / "wiki" / "raw")
    monkeypatch.setattr(paths, "DOCS", sites.DOCS)
    monkeypatch.setattr(compiler, "BUNDLE", tmp_path / "wiki")
    monkeypatch.setattr(regulations, "DOCS", {})
    monkeypatch.setattr(regulations, "ROOT", tmp_path / "raw" / "regulations")
    monkeypatch.setattr(regulations, "LINKED", tmp_path / "raw" / "linked.json")
    monkeypatch.setattr(regulations, "PAUSE", 0)
    source = sites.Site("https://source.example/", "en", "Source", r"^private", sitemap=False, pause=0)
    lab = sites.Site("https://lab.example/", "en", "Lab", r"^private", sitemap=False, pause=0)
    sites.CONFIG.write_text(yaml.safe_dump({"sites": {"source": asdict(source)}}))
    sites.reload_catalog()
    discover.write({"lab.example": {"status": "pending", "name": "lab", "config": asdict(lab)}})
    url = "https://lab.example/rules.pdf"
    unknown = "https://not-approved.example/rules.pdf"
    requests = []

    def answer(request):
        address = str(request.url)
        requests.append((request.method, address))
        if address == url:
            return httpx.Response(200, content=b"%PDF synthetic fixture", headers={"content-type": "application/pdf"})
        assert address in {source.base, source.base + "old", lab.base}, address
        links = (f'<a href="{url}">Rules</a><a href="{unknown}">Unapproved</a>' if address == source.base + "old"
                 else '<a href="/old">Old page</a>' if address == source.base else "")
        return httpx.Response(200, headers={"content-type": "text/html"}, text=(
            f"<html><title>{request.url.host}</title><p>" + "University students follow the published admission rules. " * 30
            + "</p>" + links + "</html>"))

    class Client(httpx.Client):
        def __init__(self, **kwargs):
            super().__init__(transport=httpx.MockTransport(answer), **kwargs)
    monkeypatch.setattr(httpx, "Client", Client)
    client = Client()
    monkeypatch.setattr(httpx, "get", client.get)
    monkeypatch.setattr(httpx, "stream", client.stream)
    monkeypatch.setattr(regulations, "pages_of", lambda pdf: 1)
    monkeypatch.setattr(opendataloader, "converted", lambda pdfs: contextlib.nullcontext({}))
    monkeypatch.setattr(regulations, "layer_text", lambda *a: ("1. Student admission rules apply to every applicant. " * 40, "text layer"))
    monkeypatch.setattr(chandra, "text_of_pdf", lambda *a, **kw: pytest.fail("the scheduled backlog asked for OCR"))

    assert sites.fetch_site("source", source, client) == 2
    sites.compile_all()
    assert url not in sites.load("source")["docs"]
    source_cache = sites.ROOT / "source" / "old.md"
    before = source_cache.read_bytes(), source_cache.stat().st_mtime_ns
    cli.main(["sites", "approve", "lab"])
    assert "lab" in sites.SITES and "lab.example" not in sites.discovered()
    assert before == (source_cache.read_bytes(), source_cache.stat().st_mtime_ns)
    assert ("GET", url) not in requests  # approval itself is HTML-only
    requests.clear()
    yield url, unknown, requests
    client.close()


def test_regs_fetch_reconsiders_old_links_after_approval(backlog):
    url, unknown, requests = backlog
    cli.main(["regs", "fetch", "--no-ocr"])
    docs = {key: doc for key, doc in regulations.all_docs().items() if doc["url"] == url}
    assert len(docs) == 1
    key, doc = next(iter(docs.items()))
    assert (doc["root"] / f"{key}.txt").exists()
    assert requests == [("GET", url)]
    cli.main(["regs", "fetch", "--no-ocr"])
    assert requests == [("GET", url)]
    assert unknown not in {doc["url"] for doc in regulations.all_docs().values()}


def test_autopilot_new_pages_reads_backlog_even_when_html_is_unchanged(backlog):
    url, unknown, requests = backlog
    source = next(s for s in sources.SOURCES if s.name == "new-pages")
    assert source.update() == 1  # no changed HTML, one newly permitted document
    assert requests.count(("GET", url)) == 1
    assert ("GET", "https://source.example/old") not in requests
    assert all(address != unknown for _, address in requests)
    docs = {key: doc for key, doc in regulations.all_docs().items() if doc["url"] == url}
    assert len(docs) == 1
    key, doc = next(iter(docs.items()))
    assert (doc["root"] / f"{key}.txt").exists()
    assert source.update() == 0
    assert requests.count(("GET", url)) == 1


def test_autopilot_publishes_the_old_link_after_approval(backlog, monkeypatch):
    from catix.wiki import autopilot, build

    url, _, requests = backlog
    root = sites.ROOT.parent.parent
    monkeypatch.setattr(autopilot, "DATA", root)
    monkeypatch.setattr(autopilot, "STATE", root / ".autopilot.json")
    (root / ".gitignore").write_text(".autopilot.*\n")
    autopilot.git("init", "-q", "-b", "wiki")
    autopilot.git("add", "-A")
    autopilot.git("commit", "-q", "-m", "approved provider, unchanged pages")

    def rebuild():
        regulations.compile_all()
        sites.compile_all()
        compiler.link()
        return build.Report()

    monkeypatch.setattr(build, "rebuild", rebuild)  # exercise source compilers, not model/index integration
    monkeypatch.setattr(autopilot, "check", lambda *a: autopilot.Checks(passed=["fixture checks"]))
    result = autopilot.run_once(["new-pages"], push=False, answers=False)
    assert result.kind == "committed" and not result.failed
    key = next(key for key, doc in regulations.all_docs().items() if doc["url"] == url)
    assert "Student admission rules" in autopilot.git("show", f"HEAD:wiki/raw/regulations/{key}.md")
    assert f"[Rules](/raw/regulations/{key}.md)" in autopilot.git("show", "HEAD:wiki/raw/sites/source/old.md")
    assert requests.count(("GET", url)) == 1
    assert autopilot.run_once(["new-pages"], push=False, answers=False).kind == "unchanged"
    assert requests.count(("GET", url)) == 1
