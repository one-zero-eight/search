"""Finding new sites of the university (wiki/sources/discover.py): which hosts are candidates, what the probe refuses, and that
a found site waits for a person (autopilot.py)."""

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

from catix.wiki import autopilot
from catix.wiki.sources import discover, sites

PAGE = "<html><head><title>Robotics lab</title></head><body><h1>Robotics lab</h1><p>" + "Projects of the lab and its team. " * 20 + "</p></body></html>"
LOGIN = '<html><head><title>Welcome</title></head><body><form><input type="password" name="p"></form>' + "<p>word </p>" * 60 + "</body></html>"


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    """A bundle with pages of two sites, an empty list of found sites and a copy of SITES that a test may add to."""
    docs = tmp_path / "wiki" / "raw"
    (docs / "sites" / "apply").mkdir(parents=True)
    monkeypatch.setattr(discover, "DOCS", docs)
    monkeypatch.setattr(sites, "DISCOVERED", tmp_path / "raw" / "sites-discovered.json")
    monkeypatch.setattr(sites, "SITES", dict(sites.SITES))
    monkeypatch.setattr(discover, "public", lambda host: True)

    def link(page: str, *urls: str) -> None:
        (docs / "sites" / "apply" / f"{page}.md").write_text("\n".join(f"[x]({u})" for u in urls), encoding="utf-8")

    return link


def client(routes: dict[str, httpx.Response]) -> httpx.Client:
    def handle(request: httpx.Request) -> httpx.Response:
        return routes.get(str(request.url), httpx.Response(404))

    return httpx.Client(transport=httpx.MockTransport(handle), follow_redirects=True)


def html(text: str = PAGE) -> httpx.Response:
    return httpx.Response(200, text=text, headers={"content-type": "text/html; charset=utf-8"})


def test_kinds_of_hosts():
    assert discover.kind_of("dovuz.innopolis.university") == "university"
    assert discover.kind_of("innopolis.college") == "university"
    assert discover.kind_of("a.b.innopolis.ru") == "university"
    assert discover.kind_of("innohassle.ru") == "inno"
    assert discover.kind_of("inno-agency.ru") == "inno"
    assert discover.kind_of("innopolis-mobile.ru") == "inno"
    assert discover.kind_of("innovation.com") is None  # the word `inno` alone, inside another word, is not it
    assert discover.kind_of("innogames.com") is None
    assert discover.kind_of("notinnopolis.university.evil.com") == "inno"  # only a candidate: a person still reads what it gave
    assert discover.kind_of("telegram.org") is None


def test_candidates_need_enough_pages_and_are_not_read_yet(bundle):
    bundle("a", "https://lab2.innopolis.university/x", "https://inno-shop.ru/", "https://campuslife.innopolis.ru/", "https://t.me/x")
    bundle("b", "https://inno-shop.ru/b", "https://rejected.innopolis.university/", "https://university.innopolis.ru/")
    bundle("c", "https://inno-shop.ru/c")
    found = discover.candidates({"rejected.innopolis.university"})
    assert [(h, k) for h, k, _ in found] == [("lab2.innopolis.university", "university"), ("inno-shop.ru", "inno")]  # (a host of the university first)
    assert found[1][2] == ["/raw/sites/apply/a.md", "/raw/sites/apply/b.md", "/raw/sites/apply/c.md"]


def test_the_probe_takes_a_page_of_words_and_refuses_the_rest(monkeypatch):
    monkeypatch.setattr(discover, "public", lambda host: True)
    ok = discover.probe("lab.innopolis.university", client({"https://lab.innopolis.university/": html(), "https://lab.innopolis.university/robots.txt": httpx.Response(404)}))
    assert ok == {"title": "Robotics lab", "words": ok["words"], "language": "en"} and ok["words"] >= discover.MIN_WORDS

    def reason(routes: dict) -> str:
        return discover.probe("lab.innopolis.university", client(routes))

    assert "login" in reason({"https://lab.innopolis.university/": html(LOGIN)})
    assert "login" in reason({"https://lab.innopolis.university/": html(PAGE.replace("Robotics lab</title>", "Личный кабинет</title>"))})
    assert "words" in reason({"https://lab.innopolis.university/": html("<title>x</title><p>few words</p>")})
    assert "robots.txt" in reason({"https://lab.innopolis.university/robots.txt": httpx.Response(200, text="User-agent: *\nDisallow: /"), "https://lab.innopolis.university/": html()})
    assert "HTTP 404" in reason({})
    assert "redirects to evil.example" in reason({"https://lab.innopolis.university/": httpx.Response(302, headers={"location": "https://evil.example/"}),
                                                  "https://evil.example/": html()})
    assert "redirects away from https" in reason({"https://lab.innopolis.university/": httpx.Response(302, headers={"location": "http://lab.innopolis.university/"}),
                                                  "http://lab.innopolis.university/": html()})
    assert reason({"https://lab.innopolis.university/": httpx.Response(302, headers={"location": "https://apply.innopolis.university/"}),
                   "https://apply.innopolis.university/": html()}).startswith("is apply.innopolis.university")


def test_a_name_that_is_not_public_is_not_probed(monkeypatch):
    monkeypatch.setattr(discover, "public", lambda host: False)
    assert "public" in discover.probe("intranet.innopolis.university", client({}))


def test_public_refuses_private_addresses(monkeypatch):
    def fake(addresses):
        monkeypatch.setattr(discover.socket, "getaddrinfo", lambda *a, **k: [(0, 0, 0, "", (a_, 443)) for a_ in addresses])

    fake(["93.184.216.34"])
    assert discover.public("x.test")
    for private in ("127.0.0.1", "10.1.2.3", "169.254.169.254", "192.168.0.7"):
        fake(["93.184.216.34", private])
        assert not discover.public("x.test")


def test_discover_keeps_a_found_site_pending_with_safe_settings(bundle):
    bundle("a", "https://lab.innopolis.university/", "https://login.innopolis.university/")
    routes = {"https://lab.innopolis.university/": html(), "https://login.innopolis.university/": html(LOGIN)}
    assert discover.discover(client=client(routes), pause=0) == 1
    found = json.loads(sites.DISCOVERED.read_text(encoding="utf-8"))["sites"]
    assert found["lab.innopolis.university"]["status"] == "pending" and found["lab.innopolis.university"]["examples"] == ["/raw/sites/apply/a.md"]
    assert found["login.innopolis.university"]["status"] == "failed"
    site = sites.SITES["lab"]  # (read from now on, with the settings that cannot do harm)
    assert (site.base, site.robots, site.max_pages, site.pause) == ("https://lab.innopolis.university/", True, sites.DISCOVERED_PAGES, sites.DISCOVERED_PAUSE)
    assert discover.pending_hosts() == ["lab.innopolis.university"]
    assert "lab.innopolis.university" in discover.known_hosts() and "login.innopolis.university" not in discover.known_hosts()


def test_discover_takes_few_sites_a_run_and_tries_a_failed_one_again_later(bundle):
    hosts = [f"s{i}.innopolis.university" for i in range(5)]
    bundle("a", *[f"https://{h}/" for h in hosts])
    routes = {f"https://{h}/": html() for h in hosts}
    assert discover.discover(client=client(routes), pause=0) == discover.MAX_NEW

    found = sites.discovered()
    found["s3.innopolis.university"] = {"status": "failed", "reason": "x", "tried": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()}
    assert discover.retry_later(found, "s3.innopolis.university", datetime.now(timezone.utc))
    found["s3.innopolis.university"]["tried"] = (datetime.now(timezone.utc) - timedelta(days=discover.RETRY_DAYS + 1)).isoformat()
    assert not discover.retry_later(found, "s3.innopolis.university", datetime.now(timezone.utc))


def test_a_rejected_host_is_not_found_again(bundle):
    bundle("a", "https://lab.innopolis.university/")
    assert discover.discover({"lab.innopolis.university"}, client=client({"https://lab.innopolis.university/": html()}), pause=0) == 0


def test_a_pending_site_never_reaches_the_branch_by_itself(bundle, monkeypatch):
    monkeypatch.setattr(autopilot.settings, "database_url", None)
    report = SimpleNamespace(lint_errors=0, agent=None)
    assert not any("new sites" in f for f in autopilot.check(report, False).failed)

    bundle("a", "https://lab.innopolis.university/")
    discover.discover(client=client({"https://lab.innopolis.university/": html()}), pause=0)
    assert any("new sites wait" in f and "lab.innopolis.university" in f for f in autopilot.check(report, False).failed)

    assert discover.accept_pending() == ["lab.innopolis.university"]  # (a person accepted: no look again)
    assert sites.discovered()["lab.innopolis.university"]["status"] == "accepted" and not discover.pending_hosts()
    assert not any("new sites" in f for f in autopilot.check(report, False).failed)


def test_a_host_another_source_reads_is_known(bundle):
    bundle("a", "https://eduwiki.innopolis.university/index.php/Page", "https://lab.innopolis.university/")
    assert "eduwiki.innopolis.university" in discover.known_hosts()  # (the eduwiki has a source of its own, not a line of SITES)
    assert [h for h, _, _ in discover.candidates(set())] == ["lab.innopolis.university"]


def test_a_dry_run_probes_but_keeps_nothing(bundle, capsys):
    bundle("a", "https://lab.innopolis.university/", "https://sso.innopolis.university/")
    routes = {"https://lab.innopolis.university/": html()}  # (the other one answers 404)
    assert discover.discover(client=client(routes), dry_run=True, pause=0) == 1
    out = capsys.readouterr().out
    assert "lab.innopolis.university: would be found" in out and "sso.innopolis.university: not taken: HTTP 404" in out
    assert not sites.DISCOVERED.exists() and "lab" not in sites.SITES


def test_a_host_that_did_not_answer_is_tried_again_sooner():
    now = datetime.now(timezone.utc)
    tried = (now - timedelta(days=discover.RETRY_UNREACHABLE_DAYS + 1)).isoformat()
    found = {"down.innopolis.ru": {"status": "failed", "reason": "no answer (ConnectError)", "tried": tried},
             "login.innopolis.ru": {"status": "failed", "reason": "a login page ('Вход')", "tried": tried}}
    assert not discover.retry_later(found, "down.innopolis.ru", now)  # (a week has passed: asked again)
    assert discover.retry_later(found, "login.innopolis.ru", now)  # (a login does not change in a week)


def test_every_host_the_code_names_is_known():
    """A new source or tool that reads another host must be listed in discover.read_by_code (or be a site of SITES), or the
    run would find that host in a link and read it a second time."""
    import re
    from pathlib import Path

    root = Path(discover.__file__).resolve().parents[2]  # src/catix
    named = set()
    for path in root.rglob("*.py"):
        if path.name == "discover.py":
            continue
        for url in re.findall(r"https?://[A-Za-z0-9.-]+", path.read_text(encoding="utf-8")):
            if discover.kind_of(discover.host_of(url)):
                named.add(discover.host_of(url))
    broken = {"media.innopolis.universitymedia.innopolis.university"}  # (the example of a repaired link in sites.repaired's docstring)
    assert named - broken - discover.known_hosts() == set()
    assert {"eduwiki.innopolis.university", "api.innohassle.ru", "innopolis.university"} <= discover.read_by_code()
