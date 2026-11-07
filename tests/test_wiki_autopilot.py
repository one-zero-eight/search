"""The wiki's own run (autopilot.py) without sources, model or database: what it may commit, when it asks, what it writes."""

from datetime import datetime, timedelta, timezone

from catix.wiki import autopilot, sources


def test_only_the_data_may_be_committed():
    assert autopilot.outside(["wiki/guides/retakes.md", "raw/topics.json"]) == []
    assert autopilot.outside(["wiki/x.md", "src/catix/agent/roles.py", ".gitignore"]) == ["src/catix/agent/roles.py", ".gitignore"]


def test_a_source_is_asked_when_its_interval_has_passed():
    now = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)
    state = {"asked": {"eduwiki": (now - timedelta(hours=7)).isoformat(), "files": (now - timedelta(hours=2)).isoformat()}}
    assert [s.name for s in autopilot.due(state, now)] == ["eduwiki", "new-pages", "discover", "sites", "papers"]  # files was asked 2 h ago, the others after eduwiki never
    assert [s.name for s in sources.SOURCES] == ["eduwiki", "new-pages", "files", "discover", "sites", "papers"]
    night = datetime(2026, 10, 24, 0, 30, tzinfo=timezone.utc)
    assert "ocr" not in [s.name for s in autopilot.due(state, night)]
    assert "ocr" not in [s.name for s in sources.ON_REQUEST]


def test_sites_still_run_weekly_without_ocr(monkeypatch):
    from catix.wiki.sources import regulations, sites

    asked = []
    monkeypatch.setattr(regulations, "refresh", lambda **kw: asked.append(("refresh", kw)) or 1)
    monkeypatch.setattr(sites, "fetch", lambda **kw: asked.append(("fetch", kw)) or 2)
    weekly = next(s for s in sources.SOURCES if s.name == "sites")
    assert weekly.every == timedelta(days=7)
    assert weekly.update() == 3
    assert asked == [("refresh", {"prefix": "site-"}), ("fetch", {"documents": True, "ocr": False})]
    now = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)
    state = {"asked": {"sites": now.isoformat()}}
    assert weekly not in autopilot.due(state, now + timedelta(days=6))
    assert weekly in autopilot.due(state, now + timedelta(days=7))
    assert next(s for s in sources.SOURCES if s.name == "new-pages").every == timedelta(hours=6)


def test_the_mock_source_cannot_drain_the_ocr_queue(monkeypatch):
    from catix.wiki.sources import mock, regulations

    asked = []
    monkeypatch.setattr(mock, "discover", lambda: 1)
    monkeypatch.setattr(regulations, "refresh", lambda **kw: 0)
    monkeypatch.setattr(regulations, "fetch", lambda **kw: asked.append(kw) or 0)
    assert sources._mock() == 1
    assert asked == [{"ocr": False}]


def test_scheduled_exam_papers_leave_scans_queued(monkeypatch):
    from catix.wiki.sources import pastpapers

    asked = []
    monkeypatch.setattr(pastpapers, "fetch", lambda **kw: asked.append(kw) or 1)
    assert sources._papers() == 1 and asked == [{"ocr": False}]


def test_the_commit_message_counts_changes_per_folder():
    diff = "A\twiki/regulations/a.md\nA\twiki/regulations/b.md\nM\twiki/guides/retakes.md\nD\twiki/regulations/c.md\nM\traw/topics.json"
    assert autopilot.summary(diff) == "raw/topics.json: 1 changed\nwiki/guides: 1 changed\nwiki/regulations: 2 new, 1 removed"


def _data(tmp_path, monkeypatch, write, failed=()):
    """A checkout of `wiki` in tmp_path; one source that always brings something; a rebuild that runs `write`."""
    import subprocess
    from datetime import timedelta

    from catix.wiki import build

    subprocess.run(["git", "init", "-q", "-b", "wiki", str(tmp_path)], check=True)
    (tmp_path / "wiki").mkdir()
    (tmp_path / "wiki" / "a.md").write_text("a\n")
    (tmp_path / ".gitignore").write_text(".autopilot.*\n")
    monkeypatch.setattr(autopilot, "DATA", tmp_path)
    monkeypatch.setattr(autopilot, "STATE", tmp_path / ".autopilot.json")
    autopilot.git("add", "-A")
    autopilot.git("commit", "-q", "-m", "start")
    monkeypatch.setattr(sources, "SOURCES", [sources.Source("fake", timedelta(0), lambda: 1, "test")])

    def rebuild():
        write(tmp_path)
        return build.Report()

    monkeypatch.setattr(build, "rebuild", rebuild)
    monkeypatch.setattr(autopilot, "check", lambda *a: autopilot.Checks(failed=list(failed), passed=["lint: 0 errors"]))


def test_changes_that_pass_the_checks_are_committed_to_wiki(tmp_path, monkeypatch):
    _data(tmp_path, monkeypatch, lambda d: (d / "wiki" / "b.md").write_text("b\n"))
    assert autopilot.run_once(push=False).startswith("committed")
    assert autopilot.git("log", "-1", "--format=%an|%s") == "cAtIx wiki|wiki: fake 1"
    assert "wiki/b.md: 1 new" in autopilot.git("log", "-1", "--format=%b") and not autopilot.git("status", "--porcelain")


def test_named_sites_are_committed_without_moving_the_schedule(tmp_path, monkeypatch):
    import pytest

    _data(tmp_path, monkeypatch, lambda d: (d / "wiki" / "b.md").write_text("b\n"))
    monkeypatch.setattr(sources, "SOURCES", [sources.Source("sites", timedelta(days=7), lambda: pytest.fail("every site read"), "all")])
    monkeypatch.setattr(sources, "sites_of", lambda names: sources.Source(f"sites ({', '.join(names)})", timedelta(0), lambda: 1, "some"))
    line = autopilot.run_once(["sites"], push=False, sites=["hotel"])
    assert line.kind == "committed" and line.failed == ()
    assert autopilot.git("log", "-1", "--format=%s") == "wiki: sites (hotel) 1"
    assert "sites" not in autopilot.load_state().get("asked", {})  # (the weekly run of every site is still due)


def test_a_source_that_raises_is_named_in_the_outcome(tmp_path, monkeypatch):
    _data(tmp_path, monkeypatch, lambda d: None)

    def broken():
        raise RuntimeError("the site does not answer")

    monkeypatch.setattr(sources, "SOURCES", [sources.Source("eduwiki", timedelta(0), broken, "test")])
    line = autopilot.run_once(push=False)
    assert (line.kind, line.failed) == ("unchanged", ("eduwiki",)) and "failed: eduwiki" in line


def test_changes_that_fail_go_to_a_review_branch_and_wiki_stays(tmp_path, monkeypatch):
    _data(tmp_path, monkeypatch, lambda d: (d / "wiki" / "b.md").write_text("b\n"), failed=["search: hit@5 70%"])
    head = autopilot.git("rev-parse", "HEAD")
    assert "sent to wiki-review/" in autopilot.run_once(push=False)
    assert autopilot.git("rev-parse", "HEAD") == head and (tmp_path / "wiki" / "b.md").exists()
    review = autopilot.git("for-each-ref", "--format=%(refname:short)", "refs/heads/wiki-review/")
    assert autopilot.git("show", f"{review}:wiki/b.md") == "b"
    monkeypatch.setattr(sources, "SOURCES", [])  # nothing new: the run does not check the same changes again
    assert "wait for review" in autopilot.run_once(push=False)
    assert autopilot.accept(push=False).startswith("committed") and autopilot.git("show", "HEAD:wiki/b.md") == "b"


def test_a_run_that_touches_code_commits_nothing(tmp_path, monkeypatch):
    import pytest

    def write(d):
        (d / "src").mkdir()
        (d / "src" / "x.py").write_text("x = 1\n")

    _data(tmp_path, monkeypatch, write)
    with pytest.raises(RuntimeError, match="outside the data"):
        autopilot.run_once(push=False)
    assert autopilot.git("log", "--format=%s") == "start"


def _pytest(monkeypatch, *runs):
    """The pytest of the answers, faked: each run is (its tests: {name: passed | failed | skipped} or None for no report, its
    exit code, its stderr); the commands asked are returned."""
    import subprocess
    from pathlib import Path

    calls = []

    def run(command, **kwargs):
        tests, code, stderr = runs[len(calls)]
        calls.append(command)
        report = next(a.removeprefix("--junitxml=") for a in command if a.startswith("--junitxml="))
        inner = {"passed": "", "failed": '<failure message="assert 12 in answer"/>', "skipped": '<skipped type="pytest.skip" message="the model server (llm) does not answer"/>'}
        if tests is not None:
            cases = "".join(f'<testcase classname="tests.test_docs_answers" name="{n}">{inner[r]}</testcase>' for n, r in tests.items())
            Path(report).write_text(f'<testsuites><testsuite name="pytest">{cases}</testsuite></testsuites>')
        return subprocess.CompletedProcess(command, code, "", stderr)

    monkeypatch.setattr(autopilot.subprocess, "run", run)
    return calls


def test_answers_pytest_did_not_run_fail_and_say_why(monkeypatch, capsys):
    """Regression: a .venv moved with the code kept scripts whose first line named the old interpreter; `uv run pytest` did not
    start, and the run sent its changes for review as if the agent had answered wrong. Now pytest runs as `python -m pytest`
    and a pytest that ran nothing is named as such."""
    import sys

    calls = _pytest(monkeypatch, (None, 1, f"{sys.executable}: No module named pytest"))
    ok, line = autopilot.answers_check()
    assert not ok and line.startswith("answers: not checked, pytest did not run") and "No module named pytest" in line
    assert calls[0][:3] == [sys.executable, "-m", "pytest"] and len(calls) == 1  # (nothing to try again)
    assert "No module named pytest" in capsys.readouterr().out  # (the log has what pytest said)


def test_skipped_answers_checked_nothing(monkeypatch):
    _pytest(monkeypatch, ({"test_leave": "skipped", "test_retakes": "skipped"}, 0, ""))
    ok, line = autopilot.answers_check()
    assert not ok and line == "answers: not checked, 2 of 2 skipped in tests/test_docs_answers.py (the model server (llm) does not answer)"


def test_a_failed_answer_is_asked_once_more(monkeypatch):
    calls = _pytest(monkeypatch, ({"test_leave": "passed", "test_retakes": "failed"}, 1, ""), ({"test_retakes": "passed"}, 0, ""))
    assert autopilot.answers_check() == (True, "answers: 2 of 2 passed in tests/test_docs_answers.py (test_retakes on the second try)")
    assert calls[1][-1] == "tests/test_docs_answers.py::test_retakes"


def test_an_answer_that_fails_twice_is_named(monkeypatch):
    _pytest(monkeypatch, ({"test_leave": "passed", "test_retakes": "failed"}, 1, ""), ({"test_retakes": "failed"}, 1, ""))
    assert autopilot.answers_check() == (False, "answers: 1 of 2 failed twice in tests/test_docs_answers.py: test_retakes")


def test_the_results_come_from_pytest_s_own_report():
    """A real pytest: the ids made from its JUnit report are the ones it runs again."""
    one = "tests/test_wiki_autopilot.py::test_only_the_data_may_be_committed"
    run = autopilot.run_answers(one)
    assert run.results == {one: "passed"} and not run.broken, run.output


def test_a_page_taken_away_with_nothing_in_its_place_is_lost_one_renamed_or_replaced_is_not(tmp_path, monkeypatch):
    def page(resource, member=None):
        return "\n".join(["---", "type: regulation", f'resource: "{resource}"', *([f'archive_member: "{member}"'] if member else []), "---", "", "# x", ""])

    head = {"wiki/raw/regulations/sveden-1-a.md": page("https://u/a.pdf"), "wiki/raw/regulations/sveden-2-b.md": page("https://u/b.pdf"),
            "wiki/raw/regulations/site-u-3-rpd-member-1.md": page("https://u/%D0%A0%D0%9F%D0%94%201.7z", "x/Матанализ.pdf"), "wiki/raw/regulations/index.md": page("i")}
    monkeypatch.setattr(autopilot, "DATA", tmp_path)
    monkeypatch.setattr(autopilot, "git", lambda *args, check=True: head[args[1].removeprefix("HEAD:")])
    left = tmp_path / "wiki" / "raw" / "regulations"
    left.mkdir(parents=True)
    (left / "site-university-1-a.md").write_text(page("https://u/a.pdf"), encoding="utf-8")  # (a under its new key)
    status = "\n".join(f"D\t{path}" for path in head) + "\nA\twiki/raw/regulations/site-university-1-a.md"
    assert autopilot.lost_pages(status) == ["wiki/raw/regulations/sveden-2-b.md", "wiki/raw/regulations/site-u-3-rpd-member-1.md"]
    (left / "rpd-course.md").write_text(page("https://u/РПД 1.7z"), encoding="utf-8")  # (the course, read by rpd: the archive with spaces)
    assert autopilot.lost_pages(status) == ["wiki/raw/regulations/sveden-2-b.md"]
