"""The queue of the API's requests to the run of catix-docs (parse_requests.py) and how the run serves them (runner.py), in memory."""

from collections import Counter
from datetime import datetime, timedelta, timezone

import pytest

from argparse import Namespace

from catix.docs import build, parse_requests, runner, sources, store
from catix.docs.sources import sites as site_source
from catix.docs.parse_requests import Request

JUST_ASKED = {"asked": {s.name: "2999-01-01T00:00:00+00:00" for s in sources.SOURCES}}  # (due for no clock)


def request(source: str, sites: list[str] = (), parsing: bool = True) -> Request:
    return Request(id="1", section=source, source=source, sites=list(sites), parsing=parsing)


def test_a_run_takes_every_waiting_request_and_says_what_it_did(parse_queue):
    a = parse_requests.submit("sites", "sites", ["hotel"])
    b = parse_requests.submit("eduwiki", "eduwiki", [])
    taken = parse_requests.take()
    assert [(r.id, r.status, r.attempts) for r in taken] == [(a.id, "running", 1), (b.id, "running", 1)]
    assert parse_requests.get(a.id).status == "running"
    parse_requests.finish(taken, "changed", "documents: 2 new, 0 changed, 0 removed; 5 pieces wait for a vector")
    assert parse_queue.lrange(parse_requests.RUNNING, 0, -1) == [] and parse_requests.take() == []
    done = parse_requests.get(a.id)
    assert (done.status, done.outcome) == ("done", "changed") and done.result.startswith("documents: 2 new")
    assert parse_queue.ttl[done.key()] == parse_requests.KEEP


def test_requests_a_dead_run_left_are_taken_again_then_failed(parse_queue):
    asked = parse_requests.submit("sites", "sites", ["hotel"])
    for attempt in range(parse_requests.ATTEMPTS):
        assert [r.attempts for r in parse_requests.take()] == [attempt + 1]  # (the run died: nobody finished them)
    assert parse_requests.take() == []
    gone = parse_requests.get(asked.id)
    assert (gone.status, gone.outcome) == ("failed", "error") and "stopped" in gone.result


def test_without_redis_the_run_serves_no_requests(monkeypatch):
    def unavailable():
        raise parse_requests.Unavailable("REDIS_URL is not set")

    monkeypatch.setattr(parse_requests, "connect", unavailable)
    assert parse_requests.take() == [] and parse_requests.waiting() is False
    parse_requests.finish([request("eduwiki")], "changed", "x")  # (nothing to tell: the run goes on)
    with pytest.raises(parse_requests.Unavailable):
        parse_requests.submit("eduwiki", "eduwiki", [])


def test_only_known_sources_are_queued():
    with pytest.raises(ValueError):
        parse_requests.submit("moodle", "moodle", [])


def test_requests_ask_only_their_own_sources():
    assert runner.with_requests([request("eduwiki")]) == (["eduwiki"], None)
    assert runner.with_requests([request("sites", ["hotel"])]) == (["sites"], ["hotel"])


def test_sites_of_several_requests_are_read_together_and_every_site_wins():
    two = [request("sites", ["hotel"]), request("sites", ["campuslife", "hotel"])]
    assert runner.with_requests(two) == (["sites"], ["hotel", "campuslife"])
    assert runner.with_requests([request("sites"), request("sites", ["hotel"])]) == (["sites"], None)


def test_a_request_without_parsing_asks_no_source():
    assert runner.with_requests([request("sites", ["hotel"], parsing=False)]) == (["build-only"], None)


def test_a_request_whose_source_failed_fails(parse_queue):
    hotel, wiki = parse_requests.submit("sites", "sites", ["hotel"]), parse_requests.submit("eduwiki", "eduwiki", [])
    line = runner.Outcome("changed", "documents: 3 new, 0 changed, 0 removed; 0 pieces wait for a vector (failed: sites (hotel); see the log)")
    line.failed = ("sites (hotel)",)
    runner.served(parse_requests.take(), line)
    assert (parse_requests.get(hotel.id).status, parse_requests.get(hotel.id).outcome) == ("failed", "error")
    assert (parse_requests.get(wiki.id).status, parse_requests.get(wiki.id).outcome) == ("done", "changed")


class Lock:
    """The connection of the advisory lock of the run: `got` is what pg_try_advisory_lock answers."""

    def __init__(self, got: bool = True):
        self.got, self.autocommit = got, False

    def execute(self, sql, params=None):
        assert "pg_try_advisory_lock" in sql and params == (runner.LOCK_ID,)
        return self

    def fetchone(self):
        return {"got": self.got}


@pytest.fixture
def lock(monkeypatch):
    monkeypatch.setattr(runner.pg, "connect", lambda: Lock())


def args(**kw) -> Namespace:
    return Namespace(**{"source": None, "site": None, "build": False, "loop": False, **kw})


def test_a_run_that_raises_fails_its_requests(parse_queue, monkeypatch, lock):
    asked = parse_requests.submit("eduwiki", "eduwiki", [])
    monkeypatch.setattr(runner, "load_state", lambda: JUST_ASKED)

    def broken(*a, **kw):
        raise RuntimeError("the database went away")

    monkeypatch.setattr(runner, "run_once", broken)
    runner.main(args())
    failed = parse_requests.get(asked.id)
    assert (failed.status, failed.outcome) == ("failed", "error") and "the database went away" in failed.result


def test_a_second_run_exits_while_another_holds_the_lock(monkeypatch):
    monkeypatch.setattr(runner.pg, "connect", lambda: Lock(got=False))
    with pytest.raises(SystemExit) as result:
        runner.main(args())
    assert "another run" in str(result.value.code)


def test_the_run_serves_the_request_with_what_it_did(parse_queue, monkeypatch, lock):
    asked = parse_requests.submit("sites", "sites", ["hotel"])
    calls = []
    monkeypatch.setattr(runner, "load_state", lambda: JUST_ASKED)
    monkeypatch.setattr(runner, "run_once", lambda names=None, sites=None, backlog=False, wait_for=None:
                        calls.append((names, sites, backlog)) or runner.Outcome("unchanged", "nothing new"))
    runner.main(args())
    assert calls == [(["sites"], ["hotel"], False), (None, None, True)]
    done = parse_requests.get(asked.id)
    assert (done.status, done.outcome, done.result) == ("done", "unchanged", "nothing new")


def test_site_option_is_the_source_sites_limited(monkeypatch, lock):
    calls = []
    monkeypatch.setattr(runner, "load_state", lambda: JUST_ASKED)
    monkeypatch.setattr(runner, "run_once", lambda names=None, sites=None, backlog=False, wait_for=None:
                        calls.append((names, sites)) or runner.Outcome("unchanged", "x"))
    runner.main(args(site=["hotel", "campuslife"]))
    runner.main(args(build=True))
    assert calls == [(["sites"], ["hotel", "campuslife"]), (["build-only"], None)]


class Run:
    """run_once with the state in a dict, the sources stubbed, and build.rebuild answering `counts`."""

    def __init__(self, monkeypatch, counts, updates):
        self.state, self.built, self.saved = {"asked": {}}, 0, []
        self.asked = []

        def update(name):
            def call():
                self.asked.append(name)
                result = updates[name]
                if isinstance(result, Exception):
                    raise result
                return result
            return call

        stubs = [sources.Source(name, timedelta(days=1), update(name), name) for name in updates]
        monkeypatch.setattr(sources, "SOURCES", stubs)
        monkeypatch.setattr(runner, "load_state", lambda: self.state)
        monkeypatch.setattr(runner, "save_state", lambda state: self.saved.append(dict(state)))
        monkeypatch.setattr(runner, "tell_ocr_queue", lambda state: None)
        monkeypatch.setattr(runner, "build", type("B", (), {"rebuild": lambda _: self.rebuilt(counts)})())
        monkeypatch.setattr(store, "queued", lambda: 7)

    def rebuilt(self, counts):
        self.built += 1
        assert self.state.get("rebuild") is True  # (a run cut off here is owed a rebuild)
        return counts


def test_a_run_with_new_documents_says_changed(monkeypatch):
    run = Run(monkeypatch, {"pages new": 2, "pages changed": 1, "pages removed": 3}, {"eduwiki": 4})
    line = runner.run_once()
    assert (line.kind, str(line)) == ("changed", "documents: 2 new, 1 changed, 3 removed; 7 pieces wait for a vector")
    assert run.built == 1 and "rebuild" not in run.state and "eduwiki" in run.state["asked"]


def test_sources_that_changed_without_moving_the_documents_are_unchanged(monkeypatch):
    run = Run(monkeypatch, {"pages unchanged": 9}, {"eduwiki": 1})
    line = runner.run_once()
    assert (line.kind, str(line)) == ("unchanged", "sources changed, the documents did not") and run.built == 1


def test_nothing_new_builds_nothing(monkeypatch):
    run = Run(monkeypatch, {}, {"eduwiki": 0, "papers": 0})
    line = runner.run_once()
    assert line.kind == "unchanged" and line.startswith("nothing new") and run.built == 0


def test_an_owed_rebuild_is_done_without_news(monkeypatch):
    run = Run(monkeypatch, {"pages new": 1}, {"eduwiki": 0})
    run.state["rebuild"] = True
    assert runner.run_once().kind == "changed" and run.built == 1


def test_build_only_asks_no_source(monkeypatch):
    run = Run(monkeypatch, {"pages changed": 1}, {"eduwiki": 1})
    assert runner.run_once(["build-only"]).kind == "changed"
    assert run.asked == [] and run.built == 1


def test_a_failed_source_does_not_stop_the_others_and_is_named(monkeypatch):
    run = Run(monkeypatch, {"pages new": 1}, {"eduwiki": RuntimeError("down"), "papers": 2})
    line = runner.run_once(["eduwiki", "papers"])
    assert line.kind == "changed" and line.failed == ("eduwiki",) and "(failed: eduwiki; see the log)" in line
    assert run.asked == ["eduwiki", "papers"] and "eduwiki" not in run.state["asked"] and "papers" in run.state["asked"]


def test_a_waiting_request_is_next_after_the_source_that_runs(monkeypatch):
    run = Run(monkeypatch, {"pages new": 1}, {"eduwiki": 3, "papers": 2})
    line = runner.run_once(["eduwiki", "papers"], wait_for=lambda: True)
    assert line.kind == "deferred" and "papers" in line
    assert run.asked == ["eduwiki"] and run.built == 0
    assert run.state["rebuild"] is True
    assert "eduwiki" in run.state["asked"] and "papers" not in run.state["asked"]


def test_the_backlog_runs_before_the_due_sources(monkeypatch):
    run = Run(monkeypatch, {}, {"eduwiki": 0})
    monkeypatch.setattr(sources, "BACKLOG", sources.Source("unvisited", timedelta(0), lambda: run.asked.append("unvisited") or 0, "x"))
    runner.run_once(backlog=True)
    assert run.asked == ["unvisited", "eduwiki"] and "unvisited" not in run.state["asked"]


def test_the_sleep_of_the_loop_ends_for_a_request(monkeypatch):
    slept = []
    monkeypatch.setattr(runner.time, "sleep", lambda s: slept.append(s) or (len(slept) == 2 and parse_requests.submit("eduwiki", "eduwiki", [])))
    runner.pause(15 * 60)
    assert slept == [runner.REQUEST_POLL] * 2


def test_named_sites_are_read_as_the_weekly_source_without_its_schedule(monkeypatch):
    from catix.docs.sources import regulations
    from catix.docs.sources import sites as site_source

    asked = []
    monkeypatch.setattr(site_source, "reload_catalog", lambda: None)
    monkeypatch.setattr(site_source, "SITES", {"hotel": None, "campuslife": None})
    monkeypatch.setattr(regulations, "refresh", lambda prefix: asked.append(("refresh", prefix)) or 1)
    monkeypatch.setattr(site_source, "fetch", lambda names, **kw: asked.append(("fetch", names, kw)) or 2)
    source = sources.sites_of(["hotel", "gone", "hotel"])
    assert source.name == "sites (hotel, gone)" and source not in sources.SOURCES
    assert source.update() == 3
    assert asked == [("refresh", "site-hotel-"), ("fetch", ["hotel"], {"documents": True, "ocr": False})]
    assert sources.sites_of(["gone"]).update() == 0  # (never sites.fetch with a name it does not know: it would exit)


def test_a_new_site_request_says_what_went_wrong(parse_queue, monkeypatch, lock):
    told = []
    monkeypatch.setattr(runner, "tell_admins", told.append)
    monkeypatch.setattr(runner, "load_state", lambda: JUST_ASKED)
    monkeypatch.setattr(sources, "BACKLOG", sources.Source("unvisited", timedelta(0), lambda: 0, "x"))
    calls = []
    monkeypatch.setattr(runner, "run_once", lambda names=None, sites=None, backlog=False, wait_for=None:
                        calls.append(names) or runner.Outcome("changed", "documents: 3 new"))
    monkeypatch.setattr(site_source, "read_new_site", lambda url, name: site_source.NewSite("new-example", url, 0, 0, Counter({"a bot check": 2})))
    failed = parse_requests.submit("sites", "new-site", ["new-example"], url="https://new.example/")
    runner.main(args())
    got = parse_requests.get(failed.id)
    assert (got.status, got.outcome) == ("failed", "error") and "2× a bot check" in got.result
    assert ["build-only"] not in calls
    assert "не прочитан" in told[-1]

    monkeypatch.setattr(site_source, "read_new_site", lambda url, name: site_source.NewSite(name, url, 3, 1, Counter()))
    done = parse_requests.submit("sites", "new-site", ["other-example"], url="https://other.example/")
    runner.main(args())
    got = parse_requests.get(done.id)
    assert (got.status, got.outcome) == ("done", "changed") and "3 pages read" in got.result
    assert ["build-only"] in calls


def test_an_ended_login_is_told_once_a_week(monkeypatch):
    told = []
    monkeypatch.setattr(runner, "tell_admins", told.append)
    monkeypatch.setattr(runner, "save_state", lambda state: None)
    monkeypatch.setattr(site_source, "ENDED", {"my": "x"})
    state: dict = {}
    runner.tell_ended_sessions(state)
    site_source.ENDED = {"my": "x"}
    runner.tell_ended_sessions(state)
    assert len(told) == 1 and "my" in told[0] and site_source.ENDED == {}
    state["session_told"]["my"] = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(timespec="seconds")
    site_source.ENDED = {"my": "x"}
    runner.tell_ended_sessions(state)
    assert len(told) == 2
