"""The queue of the API's requests to the wiki's run (parse_requests.py) and how the run serves them (autopilot.py), in memory."""

from datetime import datetime, timedelta, timezone

import pytest

from catix.wiki import autopilot, parse_requests, sources
from catix.wiki.parse_requests import Request

NOW = datetime(2026, 11, 4, 12, tzinfo=timezone.utc)
NOTHING_DUE = {"asked": {s.name: NOW.isoformat() for s in sources.SOURCES}}


def request(source: str, sites: list[str] = (), parsing: bool = True) -> Request:
    return Request(id="1", section=source, source=source, sites=list(sites), parsing=parsing)


def test_a_run_takes_every_waiting_request_and_says_what_it_did(parse_queue):
    a = parse_requests.submit("sites", "sites", ["hotel"])
    b = parse_requests.submit("eduwiki", "eduwiki", [])
    taken = parse_requests.take()
    assert [(r.id, r.status, r.attempts) for r in taken] == [(a.id, "running", 1), (b.id, "running", 1)]
    assert parse_requests.get(a.id).status == "running"
    parse_requests.finish(taken, "review", "checks failed, changes sent to wiki-review/20261104-1200 for review: lint: 1 errors")
    assert parse_queue.lrange(parse_requests.RUNNING, 0, -1) == [] and parse_requests.take() == []
    done = parse_requests.get(a.id)
    assert (done.status, done.outcome) == ("done", "review") and done.result.startswith("checks failed")
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
    parse_requests.finish([request("eduwiki")], "committed", "x")  # (nothing to tell: the run goes on)
    with pytest.raises(parse_requests.Unavailable):
        parse_requests.submit("eduwiki", "eduwiki", [])


def test_only_known_sources_are_queued():
    with pytest.raises(ValueError):
        parse_requests.submit("moodle", "moodle", [])


def test_requests_add_their_sources_to_the_due_ones():
    assert autopilot.with_requests(None, None, [], NOTHING_DUE, NOW) == (None, None)
    assert autopilot.with_requests(None, None, [request("eduwiki")], NOTHING_DUE, NOW) == (["eduwiki"], None)
    due = {"asked": {**NOTHING_DUE["asked"], "papers": (NOW - timedelta(days=8)).isoformat()}}
    assert autopilot.with_requests(None, None, [request("sites", ["hotel"])], due, NOW) == (["papers", "sites"], ["hotel"])


def test_sites_of_several_requests_are_read_together_and_every_site_wins():
    two = [request("sites", ["hotel"]), request("sites", ["campuslife", "hotel"])]
    assert autopilot.with_requests(None, None, two, NOTHING_DUE, NOW) == (["sites"], ["hotel", "campuslife"])
    assert autopilot.with_requests(["sites"], None, two, NOTHING_DUE, NOW) == (["sites"], None)  # (--source sites reads every site)
    assert autopilot.with_requests(["sites"], ["media"], two, NOTHING_DUE, NOW) == (["sites"], ["media", "hotel", "campuslife"])
    weekly = {"asked": {**NOTHING_DUE["asked"], "sites": (NOW - timedelta(days=8)).isoformat()}}
    assert autopilot.with_requests(None, None, two, weekly, NOW) == (["sites"], None)


def test_a_request_without_parsing_asks_no_source():
    assert autopilot.with_requests(None, None, [request("sites", ["hotel"], parsing=False)], NOTHING_DUE, NOW) == (["build-only"], None)
    assert autopilot.with_requests(["eduwiki"], None, [request("sites", ["hotel"], parsing=False)], NOTHING_DUE, NOW) == (["eduwiki"], None)


def test_a_request_whose_source_failed_fails(parse_queue):
    hotel, wiki = parse_requests.submit("sites", "sites", ["hotel"]), parse_requests.submit("eduwiki", "eduwiki", [])
    line = autopilot.Outcome("committed", "committed 1a2b3c: 3 files (failed: sites (hotel); see the log)")
    line.failed = ("sites (hotel)",)
    autopilot.served(parse_requests.take(), line)
    assert (parse_requests.get(hotel.id).status, parse_requests.get(hotel.id).outcome) == ("failed", "error")
    assert (parse_requests.get(wiki.id).status, parse_requests.get(wiki.id).outcome) == ("done", "committed")


def test_a_run_that_raises_fails_its_requests(parse_queue, monkeypatch, tmp_path):
    from argparse import Namespace

    asked = parse_requests.submit("eduwiki", "eduwiki", [])
    monkeypatch.setattr(autopilot, "ready", lambda: None)
    monkeypatch.setattr(autopilot, "LOCK", tmp_path / "lock")
    monkeypatch.setattr(autopilot, "load_state", lambda: NOTHING_DUE)

    def broken(*a, **kw):
        raise RuntimeError("the run changed paths outside the data, nothing committed: ['src/x.py']")

    monkeypatch.setattr(autopilot, "run_once", broken)
    autopilot.main(Namespace(action="run", source=None, site=None, only_new=False, build=False, no_push=True, no_answers=True, loop=False))
    failed = parse_requests.get(asked.id)
    assert (failed.status, failed.outcome) == ("failed", "error") and "outside the data" in failed.result


def test_the_sleep_of_the_loop_ends_for_a_request(monkeypatch):
    slept = []
    monkeypatch.setattr(autopilot.time, "sleep", lambda s: slept.append(s) or (len(slept) == 2 and parse_requests.submit("eduwiki", "eduwiki", [])))
    autopilot.pause(15 * 60)
    assert slept == [autopilot.REQUEST_POLL] * 2


def test_named_sites_are_read_as_the_weekly_source_without_its_schedule(monkeypatch):
    from catix.wiki.sources import regulations
    from catix.wiki.sources import sites as site_source

    asked = []
    monkeypatch.setattr(site_source, "every_site", lambda: {"hotel": None, "campuslife": None})
    monkeypatch.setattr(regulations, "refresh", lambda prefix: asked.append(("refresh", prefix)) or 1)
    monkeypatch.setattr(site_source, "fetch", lambda names, **kw: asked.append(("fetch", names, kw)) or 2)
    source = sources.sites_of(["hotel", "gone", "hotel"])
    assert source.name == "sites (hotel, gone)" and source not in sources.SOURCES
    assert source.update() == 3
    assert asked == [("refresh", "site-hotel-"), ("fetch", ["hotel"], {"documents": True, "ocr": False})]
    assert sources.sites_of(["gone"]).update() == 0  # (never sites.fetch with a name it does not know: it would exit)
