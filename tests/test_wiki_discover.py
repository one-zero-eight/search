"""Finding new sites of the university (wiki/sources/discover.py): which hosts are candidates, what the probe refuses, and that
a found site waits for a person (autopilot.py)."""

import dataclasses
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
    monkeypatch.setattr(sites, "CONFIG", tmp_path / "sites.yaml")
    sites.CONFIG.write_text("blocked: []\nsites: {}\n", encoding="utf-8")
    monkeypatch.setattr(sites, "SITES", dict(sites.SITES))
    monkeypatch.setattr(discover, "public", lambda host: True)
    monkeypatch.setattr(discover.regulations, "all_docs", lambda: {})  # (the documents of the real data name hosts too)

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
    assert [(h, k) for h, k, _ in found] == [("lab2.innopolis.university", "university"), ("inno-shop.ru", "inno")]  # (a host of the university first; one link is enough)
    assert found[1][2] == ["/raw/sites/apply/a.md", "/raw/sites/apply/b.md", "/raw/sites/apply/c.md"]
    bundle("d", "https://inno-cinema.ru/")
    assert "inno-cinema.ru" in [h for h, _, _ in discover.candidates(set())]  # (a host with `inno` linked by a single page)


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
    assert found["login.innopolis.university"]["status"] == "closed"  # (a login page needs access, it is not a failure)
    site = sites.load_sites(sites.pending_file())["lab"]  # (a line of sites-pending.yaml: read from now on, with the settings that cannot do harm)
    assert (site.base, site.robots, site.max_pages, site.pause) == ("https://lab.innopolis.university/", True, sites.DISCOVERED_PAGES, sites.DISCOVERED_PAUSE)
    assert sites.pending_sites()["lab"] == site and "lab" in sites.every_site()
    assert "lab" not in sites.SITES and sites.pending_file() == sites.DISCOVERED.with_name("sites-pending.yaml")  # (not trusted: no line in sites.yaml)
    assert discover.pending_hosts() == ["lab.innopolis.university"]
    assert "lab.innopolis.university" in discover.known_hosts() and "login.innopolis.university" not in discover.known_hosts()


def test_discover_takes_few_sites_a_run_and_tries_a_failed_one_again_later(bundle):
    hosts = [f"s{i}.innopolis.university" for i in range(discover.MAX_NEW + 2)]
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
    assert "lab.innopolis.university" not in sites.discovered()
    assert "lab" in sites.SITES and not discover.pending_hosts() and not sites.pending_file().exists()
    assert sites.load_sites(sites.CONFIG)["lab"].max_pages == sites.DISCOVERED_PAGES  # (its line moved to sites.yaml as it was)
    from catix.wiki.sources import crawl

    assert crawl.provider("https://lab.innopolis.university/news") == "lab"  # (trusted from now on)
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
    assert not sites.DISCOVERED.exists() and not sites.pending_file().exists() and "lab" not in sites.every_site()


def test_a_host_that_did_not_answer_is_tried_again_sooner():
    now = datetime.now(timezone.utc)
    tried = (now - timedelta(days=discover.RETRY_UNREACHABLE_DAYS + 1)).isoformat()
    found = {"down.innopolis.ru": {"status": "failed", "reason": "no answer (ConnectError)", "tried": tried},
             "login.innopolis.ru": {"status": "failed", "reason": "a login page ('Вход')", "tried": tried}}
    assert not discover.retry_later(found, "down.innopolis.ru", now)  # (a week has passed: asked again)
    assert discover.retry_later(found, "login.innopolis.ru", now)  # (a login does not change in a week)


# --- a bot check that answers in place of the site's page ---

WALLED = '<html><head><title>Вы не робот?</title></head><body><div class="smart-captcha">Подтвердите, что вы не робот</div></body></html>'


def test_a_bot_check_is_asked_again_until_the_page_comes_through(monkeypatch):
    monkeypatch.setattr(discover, "public", lambda host: True)
    monkeypatch.setattr(sites, "BOT_PAUSE", 0)
    asked = []

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        asked.append(str(request.url))
        return html(WALLED if len(asked) < 3 else PAGE)  # (the wall twice, then it lets a request through)

    result = discover.probe("lab.innopolis.university", httpx.Client(transport=httpx.MockTransport(handle), follow_redirects=True))
    assert result == {"title": "Robotics lab", "words": result["words"], "language": "en"} and result["words"] >= discover.MIN_WORDS
    assert len(asked) == 3  # (the start page was asked for again, not read as the wall's few words)


def test_a_host_a_bot_check_never_releases_is_named_and_tried_again_soon(monkeypatch):
    monkeypatch.setattr(discover, "public", lambda host: True)
    monkeypatch.setattr(sites, "BOT_PAUSE", 0)
    result = discover.probe("club.timepad.ru", client({"https://club.timepad.ru/": html(WALLED)}))
    assert "a bot check" in result and "Вы не робот" in result  # (not 'a login, or an empty shell': the wall is not the site)
    now = datetime.now(timezone.utc)
    found = {"club.timepad.ru": {"status": "failed", "reason": result, "tried": now.isoformat()}}
    assert discover.retry_later(found, "club.timepad.ru", now)  # (the wall comes and goes: asked again in a week, not in a month)


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


def lately_failed(host: str) -> None:
    sites.DISCOVERED.parent.mkdir(parents=True, exist_ok=True)
    entry = {"status": "failed", "reason": "a login page", "tried": datetime.now(timezone.utc).isoformat()}
    sites.DISCOVERED.write_text(json.dumps({"sites": {host: entry}}), encoding="utf-8")


def test_a_normal_run_takes_few_and_leaves_a_host_that_failed_lately(bundle):
    hosts = [f"s{i}.innopolis.university" for i in range(discover.MAX_PROBES + 4)]
    bundle("a", *[f"https://{h}/" for h in hosts])
    lately_failed(hosts[0])
    assert discover.discover(client=client({f"https://{h}/": html() for h in hosts}), pause=0) == discover.MAX_NEW
    assert hosts[0] not in discover.pending_hosts()


def test_everything_has_no_limits_and_asks_failed_hosts_again(bundle):
    hosts = [f"s{i}.innopolis.university" for i in range(discover.MAX_PROBES + 4)]
    bundle("a", *[f"https://{h}/" for h in hosts])
    lately_failed(hosts[0])
    assert discover.discover(client=client({f"https://{h}/": html() for h in hosts}), pause=0, everything=True) == len(hosts)
    assert len(discover.pending_hosts()) == len(hosts)


def test_only_new_reads_the_pending_sites_and_not_on_a_schedule(bundle, monkeypatch):
    from catix.wiki import sources as registry
    from catix.wiki.sources import regulations

    bundle("a", "https://lab.innopolis.university/", "https://third.innopolis.university/")
    discover.discover(client=client({f"https://{h}.innopolis.university/": html() for h in ("lab", "third")}), pause=0)
    discover.accept_pending(["lab.innopolis.university"])  # (a person accepted it: the weekly run reads it)
    assert discover.pending_hosts() == ["third.innopolis.university"]

    asked = []
    monkeypatch.setattr(sites, "fetch", lambda names=None, **kwargs: asked.append((names, kwargs)) or 5)  # (pages and the documents they link)
    monkeypatch.setattr(regulations, "fetch", lambda *args, **kwargs: pytest.fail("sites.fetch reads the documents in its waves"))
    assert registry.ON_REQUEST[0].name == "new-sites" and registry.ON_REQUEST[0].update() == 5
    assert asked == [(["third"], {"documents": True, "ocr": False})]

    assert "new-sites" not in [s.name for s in registry.SOURCES]
    assert [s.name for s in autopilot.due({}, datetime.now(timezone.utc))] == [s.name for s in registry.SOURCES]  # (never due by itself)


# --- explore: rounds until nothing is new, then a person chooses ---


@pytest.fixture
def web(bundle, tmp_path, monkeypatch):
    """A chain of sites: the page of each links the next one. 'Reading' a site makes its page in the bundle, as sites.fetch and
    compile_all do; a log tells what was read."""
    from catix.wiki import autopilot

    monkeypatch.setattr(autopilot, "STATE", tmp_path / ".autopilot.json")
    monkeypatch.setattr(sites, "ROOT", tmp_path / "raw" / "sites")
    read, chain = [], {}

    def fetch(names=None, **kwargs):
        for name in names:
            host = f"{name}.innopolis.university"
            read.append(name)
            page = discover.DOCS / sites.FOLDER / name / "home.md"
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text(f"[next]({chain[host]})" if chain.get(host) else "no links", encoding="utf-8")
            (sites.ROOT / name).mkdir(parents=True, exist_ok=True)
            (sites.ROOT / name / "index.json").write_text(json.dumps({"pages": {"home": {"title": f"Home of {name}"}}, "docs": {}}), encoding="utf-8")
        return len(names)

    monkeypatch.setattr(sites, "fetch", fetch)
    monkeypatch.setattr(sites, "compile_all", lambda: None)

    def make(*hosts: str):
        for here, there in zip(hosts, [*hosts[1:], None]):
            chain[here] = f"https://{there}/" if there else ""
        bundle("start", f"https://{hosts[0]}/")
        return client({f"https://{h}/": html() for h in hosts})

    make.read = read
    return make


def test_explore_follows_the_links_of_the_sites_it_found_until_nothing_is_new(web):
    http = web("a.innopolis.university", "b.innopolis.university", "c.innopolis.university")
    found = discover.explore(set(), client=http, pause=0)
    assert found == ["a.innopolis.university", "b.innopolis.university", "c.innopolis.university"]  # (a's page led to b, b's to c)
    assert web.read == ["a", "b", "c"] and discover.pending_hosts() == found


def test_explore_stops_at_the_limit_of_sites_and_of_rounds(web):
    hosts = [f"s{i}.innopolis.university" for i in range(6)]
    assert discover.explore(set(), max_sites=2, client=web(*hosts), pause=0) == hosts[:2]


def test_explore_asks_a_host_that_failed_once_only(web):
    http = web("a.innopolis.university", "b.innopolis.university")
    discover.DOCS.joinpath("sites", "apply", "dead.md").write_text("[x](https://dead.innopolis.university/)", encoding="utf-8")
    probed = []
    real = discover.probe
    discover.probe = lambda host, c: probed.append(host) or real(host, c)
    try:
        discover.explore(set(), client=http, pause=0)
    finally:
        discover.probe = real
    assert probed.count("dead.innopolis.university") == 1  # (round 2 and 3 did not ask it again)


def test_a_person_accepts_some_and_rejects_the_rest(web, capsys):
    from catix.wiki import autopilot

    discover.explore(set(), client=web("a.innopolis.university", "b.innopolis.university", "c.innopolis.university"), pause=0)
    discover.review()
    out = capsys.readouterr().out
    assert "a   a.innopolis.university" in out and "1 pages read" in out and "Home of b" in out

    assert discover.accept_pending(discover.resolve(["a"])) == ["a.innopolis.university"]  # (a name does as well as a host)
    discover.reject(discover.resolve(["c.innopolis.university"]))
    assert discover.pending_hosts() == ["b.innopolis.university"]
    assert "a.innopolis.university" not in sites.discovered() and "c.innopolis.university" not in sites.discovered()
    assert "a" in sites.SITES
    assert not (sites.ROOT / "c").exists() and not (discover.DOCS / sites.FOLDER / "c").exists() and "c" not in sites.every_site()  # (what was read of it is gone)
    assert list(sites.load_sites(sites.pending_file())) == ["b"]
    assert (sites.ROOT / "a").exists()
    assert autopilot.load_state()["rejected_sites"] == ["c.innopolis.university"]
    with pytest.raises(SystemExit):
        discover.resolve(["c"])  # (nothing pending by that name any more)


# --- hosts that need access ---


def test_a_login_or_401_403_is_a_host_that_needs_access(monkeypatch):
    monkeypatch.setattr(discover, "public", lambda host: True)
    for status in (401, 403):
        assert discover.probe("pay.innopolis.university", client({"https://pay.innopolis.university/": httpx.Response(status)})) == f"{discover.CLOSED} (HTTP {status})"
    assert discover.probe("lk.innopolis.university", client({"https://lk.innopolis.university/": html(LOGIN)})).startswith(discover.CLOSED)
    assert not discover.probe("x.innopolis.university", client({"https://x.innopolis.university/": httpx.Response(404)})).startswith(discover.CLOSED)  # (404: nothing to open)


def test_closed_hosts_are_listed_with_who_links_them_and_can_be_forgotten(bundle, capsys, monkeypatch):
    from catix.wiki import autopilot

    monkeypatch.setattr(autopilot.settings, "database_url", None)  # (check would measure the real search)

    bundle("a", "https://pay.innopolis.university/", "https://lab.innopolis.university/", "https://gone.innopolis.university/")
    routes = {"https://pay.innopolis.university/": httpx.Response(403), "https://lab.innopolis.university/": html()}
    assert discover.discover(client=client(routes), pause=0) == 1  # (lab; gone answers 404: failed)

    found = sites.discovered()
    assert found["pay.innopolis.university"]["status"] == "closed" and found["pay.innopolis.university"]["examples"] == ["/raw/sites/apply/a.md"]
    assert found["gone.innopolis.university"]["status"] == "failed" and "examples" not in found["gone.innopolis.university"]
    assert discover.closed_hosts() == ["pay.innopolis.university"] and discover.pending_hosts() == ["lab.innopolis.university"]  # (a closed host does not hold up the review)
    assert "pay" not in sites.SITES and "pay.innopolis.university" not in discover.known_hosts()  # (asked again later, not read)
    assert autopilot.check(SimpleNamespace(lint_errors=0, agent=None), False).failed  # (the pending lab does)

    capsys.readouterr()  # (what discover said)
    discover.review()
    out = capsys.readouterr().out
    assert "== need access (1)" in out and "pay.innopolis.university   [university] HTTP 403; linked from 1 pages, e.g. /raw/sites/apply/a.md" in out
    assert "gone.innopolis.university" not in out

    discover.reject(discover.resolve(["pay"], closed=True))
    assert "pay.innopolis.university" not in sites.discovered()
    with pytest.raises(SystemExit):
        discover.resolve(["pay"])  # (not pending; closed ones only when asked for)


# --- documents, and sites a person added ---


def test_explore_reads_a_site_a_person_added_and_only_the_documents_of_the_sites_it_read(web, monkeypatch):
    from catix.wiki.sources import regulations

    http = web("a.innopolis.university")
    found = {"mine.innopolis.ru": {"status": "pending", "kind": "manual", "language": "ru"}}
    discover.write(found)  # (added by hand with `sites add`: no page links it)
    sites.load_discovered()
    prefixes_seen = []
    def fetch(limit=None, prefixes=None, ocr=True):
        assert ocr is False  # (exploration queues scans too; no OCR server is needed)
        prefixes_seen.append(prefixes)
        return 0

    monkeypatch.setattr(regulations, "fetch", fetch)
    discover.explore(set(), client=http, pause=0)
    assert "mine-innopolis-ru" in web.read and "a" in web.read  # (the added one was read in the first round, the found one too)
    assert prefixes_seen and all(p is not None and all(x.startswith("site-") for x in p) for p in prefixes_seen)
    assert prefixes_seen[0] == ("site-a-", "site-mine-innopolis-ru-")  # (the documents of these two sites, not of all the others)


def test_the_documents_of_the_universitys_hosts_that_other_sites_link_are_collected(tmp_path, monkeypatch):
    docs = tmp_path / "wiki" / "raw"
    monkeypatch.setattr(sites, "DOCS", docs)
    monkeypatch.setattr(sites, "ROOT", tmp_path / "raw" / "sites")
    monkeypatch.setattr(sites, "DISCOVERED", tmp_path / "raw" / "sites-discovered.json")
    monkeypatch.setattr(sites, "SITES", {n: sites.SITES[n] for n in ("career", "apply", "university", "digitalinnopolisdays-ru")})
    for name, body in (("career", "[Образец](https://innopolis.university/upload/iblock/a/Образец%20согласия.docx) [x](https://example.org/a.pdf) [ПИШ](https://innopolis.university/upload/b/944225_ПИШ.pdf) "
                                  "[![](https://static.tildacdn.com/tild1/cover.png)](https://innopolis.university/filespublic/cases_cdto.pdf) "  # (a picture that is a link)
                                  "[Политика](https://reg.digitalinnopolisdays.ru/upload/medialibrary/61a/policy.pdf)"),  # (a trusted site off the university's domains)
                       ("apply", "[Guide](https://apply.innopolis.university/upload/files/guide.pdf) [Образец](https://innopolis.university/upload/iblock/a/%D0%9E%D0%B1%D1%80%D0%B0%D0%B7%D0%B5%D1%86%20%D1%81%D0%BE%D0%B3%D0%BB%D0%B0%D1%81%D0%B8%D1%8F.docx)")):
        (docs / "sites" / name).mkdir(parents=True)
        (docs / "sites" / name / "home.md").write_text(body, encoding="utf-8")
        (sites.ROOT / name).mkdir(parents=True)
        (sites.ROOT / name / "index.json").write_text(json.dumps({"pages": {}, "docs": {}}), encoding="utf-8")

    assert sites.collect_linked_docs() == 5  # (the same file spelled two ways is one; a document of a site not in SITES is not taken)
    assert sorted(sites.load("career")["docs"]) == ["https://innopolis.university/filespublic/cases_cdto.pdf", "https://innopolis.university/upload/b/944225_%D0%9F%D0%98%D0%A8.pdf",
                                                   "https://innopolis.university/upload/iblock/a/%D0%9E%D0%B1%D1%80%D0%B0%D0%B7%D0%B5%D1%86%20%D1%81%D0%BE%D0%B3%D0%BB%D0%B0%D1%81%D0%B8%D1%8F.docx",
                                                   "https://reg.digitalinnopolisdays.ru/upload/medialibrary/61a/policy.pdf"]
    assert list(sites.load("apply")["docs"]) == ["https://apply.innopolis.university/upload/files/guide.pdf"]
    assert sites.collect_linked_docs() == 0  # (nothing twice)


def test_discovered_sites_never_become_configuration_automatically(web, monkeypatch):
    discover.write({
        "sport.innopolis.ru": {"status": "accepted", "kind": "university", "language": "ru"},  # (sport has its own line in SITES)
        "late.innopolis.university": {"status": "accepted", "kind": "university", "language": "ru"},  # (accepted, never read)
        "gone.innopolis.university": {"status": "failed", "reason": "x", "tried": "2020-01-01T00:00:00+00:00"},
    })
    monkeypatch.setitem(sites.SITES, "sport", sites.Site("https://sport.innopolis.ru/", "ru", "sport", ""))
    assert sites.load_discovered() == 0
    assert "sport-innopolis-ru" not in sites.SITES and "late" not in sites.SITES
    assert discover.unread_hosts() == []
    found = discover.explore(set(), client=web("x.innopolis.university"), pause=0)
    assert "late" not in web.read and discover.unread_hosts() == []


def test_a_name_with_a_dot_at_the_end_is_the_same_host():
    assert discover.host_of("https://InnopolisCamp.ru./page") == "innopoliscamp.ru" == discover.host_of("https://www.innopoliscamp.ru/")


# --- an app: the HTML is an empty shell, the browser shows the page ---

SHELL = '<!doctype html><html><head><title>1519 scholarship</title></head><body><div id="root"></div><script type="module" src="/assets/index.js"></script></body></html>'


def test_an_app_is_probed_in_the_browser_and_read_that_way(monkeypatch, bundle):
    monkeypatch.setattr(discover, "public", lambda host: True)
    monkeypatch.delitem(sites.SITES, "1519", raising=False)  # an approved site is static and therefore no longer a candidate
    monkeypatch.setattr(sites, "CHROMIUM", "/usr/bin/chromium")
    shown = "<html><head><title>1519 scholarship</title></head><body><h2>Стипендия</h2><p>" + "Тридцать стипендий для студентов бакалавриата. " * 10 + "</p></body></html>"
    monkeypatch.setattr(sites, "render_page", lambda url: shown)
    result = discover.probe("1519.innopolis.university", client({"https://1519.innopolis.university/": html(SHELL)}))
    assert result["render"] is True and result["words"] >= discover.MIN_WORDS and result["language"] == "ru"

    bundle("a", "https://1519.innopolis.university/")
    assert discover.discover(client=client({"https://1519.innopolis.university/": html(SHELL)}), pause=0) == 1
    assert sites.pending_sites()["1519"].render is True  # (read by the browser from now on)


def test_an_empty_shell_stays_refused_when_the_browser_shows_nothing_either(monkeypatch):
    monkeypatch.setattr(discover, "public", lambda host: True)
    monkeypatch.setattr(sites, "CHROMIUM", "/usr/bin/chromium")
    monkeypatch.setattr(sites, "render_page", lambda url: None)
    assert "0 words" in discover.probe("x.innopolis.university", client({"https://x.innopolis.university/": html(SHELL)}))
    monkeypatch.setattr(sites, "render_page", lambda url: '<title>Sign in</title><form><input type="password"></form>')
    assert discover.probe("x.innopolis.university", client({"https://x.innopolis.university/": html(SHELL)})).startswith(discover.CLOSED)


def test_a_plain_page_is_not_sent_to_the_browser(monkeypatch):
    monkeypatch.setattr(discover, "public", lambda host: True)
    monkeypatch.setattr(sites, "render_page", lambda url: pytest.fail("a page with words needs no browser"))
    assert "render" not in discover.probe("lab.innopolis.university", client({"https://lab.innopolis.university/": html()}))


def test_a_host_a_document_names_is_a_candidate_too(bundle, tmp_path, monkeypatch):
    docs = tmp_path / "raw" / "regulations"
    docs.mkdir(parents=True)
    (docs / "rules.txt").write_text("Положение размещено на https://lab.innopolis.university/docs, сведения: https://innopolis.universityСайт/ "
                                    "и https://lab.innopolis.university/team, https://inno-cup.ru/ и https://innopolis.unive\nrsity/x", encoding="utf-8")
    (docs / "plan.txt").write_text("См. https://lab.innopolis.university/.", encoding="utf-8")
    (discover.DOCS / "regulations").mkdir(parents=True)
    (discover.DOCS / "regulations" / "plan.md").write_text("x", encoding="utf-8")
    monkeypatch.setattr(discover.regulations, "all_docs", lambda: {
        "rules": {"title": "Rules", "url": "https://innopolis.university/upload/rules.pdf", "root": docs},
        "plan": {"title": "Plan", "url": "https://innopolis.university/upload/plan.pdf", "root": docs},
        "unread": {"title": "Not read", "url": "https://innopolis.university/upload/unread.pdf", "root": docs}})
    found = discover.candidates(set())
    assert [(h, k) for h, k, _ in found] == [("lab.innopolis.university", "university")]  # (not an address the PDF cut or glued, not an `inno` host)
    assert found[0][2] == ["/raw/regulations/plan.md", "https://innopolis.university/upload/rules.pdf"]  # (a document by its page, or its address before it has one)


def test_approve_adds_the_line_at_the_end_of_sites_yaml_and_leaves_the_rest_as_it_was(bundle, monkeypatch):
    head = "blocked:\n- moodle.innopolis.university\nsites:\n  hotel:\n    base: https://hotel.innopolis.university/\n    language: ru\n    about: the hotel\n    skip: ^x$  # by hand\n\n"
    sites.CONFIG.write_text(head, encoding="utf-8")
    sites.add_pending("lab.innopolis.university", {"status": "pending", "title": "Robotics lab", "language": "en"})
    lines = sites.load_sites(sites.pending_file())
    sites.write_pending({"lab": dataclasses.replace(lines["lab"], max_pages=200)})  # (a person raised its limit before approving)
    assert sites.approve_discovered("lab.innopolis.university", {}) == "lab"
    text = sites.CONFIG.read_text(encoding="utf-8")
    assert text.startswith(head.rstrip("\n") + "\n  lab:\n    base: https://lab.innopolis.university/\n")  # (the comment and the order kept)
    config = sites.load_sites(sites.CONFIG)
    assert list(config) == ["hotel", "lab"] and config["lab"].max_pages == 200 and config["lab"].about == "lab.innopolis.university, found by the wiki's run: Robotics lab"
    assert not sites.pending_file().exists() and sites.SITES["lab"] == config["lab"]
