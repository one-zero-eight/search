"""Approving a site builds its wiki pages without running the wiki agent."""

from dataclasses import asdict

import httpx
import pytest

from catix.wiki import cli, compile as compiler
from catix.wiki.sources import discover, sites


@pytest.fixture
def website(tmp_path, monkeypatch):
    monkeypatch.setattr(sites, "ROOT", tmp_path / "raw" / "sites")
    monkeypatch.setattr(sites, "DOCS", tmp_path / "wiki" / "raw")
    monkeypatch.setattr(compiler, "BUNDLE", tmp_path / "wiki")
    site = sites.Site("https://lab.example/", "en", "Lab", "^private", sitemap=False, robots=False, pause=0)
    discover.write({"lab.example": {"status": "pending", "name": "lab", "config": asdict(site)}})
    requests = []
    status = {"code": 200}

    def handle(request):
        requests.append(str(request.url))
        return httpx.Response(status["code"], headers={"content-type": "text/html"}, text=(
            "<html><title>Robotics lab</title><h1>Robotics lab</h1><p>"
            + "Our laboratory offers research projects and internships for university students. " * 10
            + "</p></html>"))

    real_client = httpx.Client
    monkeypatch.setattr(sites.httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs))
    return tmp_path, requests, status


@pytest.mark.parametrize("action", ["approve", "accept"])
def test_approval_fetches_and_builds_the_selected_site(website, action):
    root, requests, _ = website
    cli.main(["sites", action, "lab"])
    assert "lab" in sites.load_sites() and "lab.example" not in sites.discovered()
    assert requests == ["https://lab.example/"]
    page = root / "wiki" / "raw" / "sites" / "lab" / "home.md"
    assert page.exists() and "research projects and internships" in page.read_text()
    assert (root / "wiki" / "index.md").exists()
    assert "/raw/sites/lab/home.md" in (root / "wiki" / "raw" / "sites" / "index.md").read_text()


def test_failed_first_fetch_is_reported_and_approval_can_be_retried(website, capsys):
    root, requests, status = website
    status["code"] = 503
    with pytest.raises(SystemExit) as error:
        cli.main(["sites", "approve", "lab"])
    assert error.value.code != 0
    assert "lab" in sites.load_sites()  # approval persists; a fetch failure is not a trust decision
    assert "built" not in capsys.readouterr().out
    status["code"] = 200
    cli.main(["sites", "approve", "lab"])
    assert requests == ["https://lab.example/", "https://lab.example/"]
    assert (root / "wiki" / "raw" / "sites" / "lab" / "home.md").exists()


def test_approval_does_not_write_when_another_wiki_update_holds_the_lock(website):
    import fcntl
    from catix.wiki import autopilot

    _, requests, _ = website
    before = sites.CONFIG.read_bytes(), sites.DISCOVERED.read_bytes()
    autopilot.LOCK.parent.mkdir(parents=True, exist_ok=True)
    with autopilot.LOCK.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(SystemExit, match="another wiki update"):
            cli.main(["sites", "approve", "lab"])
    assert before == (sites.CONFIG.read_bytes(), sites.DISCOVERED.read_bytes())
    assert requests == []


def test_approval_build_error_is_not_reported_as_success(website, monkeypatch):
    def broken():
        raise RuntimeError("compiler failed")

    monkeypatch.setattr(sites, "compile_all", broken)
    with pytest.raises(SystemExit, match="sites remain approved, but building failed: compiler failed"):
        cli.main(["sites", "approve", "lab"])
    assert "lab" in sites.load_sites()
