"""The queue of the API's requests to the run of catix-docs (parse_requests.py), the lock of the run and the admins' alerts (runner.py), in memory."""

from argparse import Namespace
from datetime import datetime, timedelta, timezone

import pytest

from catix.docs import parse_requests, runner
from catix.docs.parse_requests import Request
from catix.docs.sources import sites as site_source


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


def test_requests_being_served_are_not_taken_again(parse_queue):
    a = parse_requests.submit("sites", "sites", ["hotel"])
    (first,) = parse_requests.take()
    assert parse_requests.take({a.id}) == [] and parse_requests.get(a.id).attempts == first.attempts


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


class Lock:
    """The connection of the advisory lock of the run: `got` is what pg_try_advisory_lock answers."""

    def __init__(self, got: bool = True):
        self.got, self.autocommit = got, False

    def execute(self, sql, params=None):
        assert "pg_try_advisory_lock" in sql and params == (runner.LOCK_ID,)
        return self

    def fetchone(self):
        return {"got": self.got}


def test_a_second_run_exits_while_another_holds_the_lock(monkeypatch):
    monkeypatch.setattr(runner.pg, "connect", lambda: Lock(got=False))
    with pytest.raises(SystemExit) as result:
        runner.main(Namespace(source=None, site=None, build=False, loop=False))
    assert "another run" in str(result.value.code)


def test_the_run_with_the_lock_shares_the_hosts_and_runs(monkeypatch):
    calls = []
    lock = Lock()
    monkeypatch.setattr(runner.pg, "connect", lambda: lock)
    monkeypatch.setattr(runner.hosts, "share", lambda: calls.append("share"))
    monkeypatch.setattr(runner, "run", lambda args: calls.append(("run", args)))
    given = Namespace(source=None, site=None, build=False, loop=False)
    runner.main(given)
    assert lock.autocommit and calls == ["share", ("run", given)]


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
