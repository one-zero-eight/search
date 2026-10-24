"""The wiki's own run (autopilot.py) without sources, model or database: what it may commit, when it asks, what it writes."""

from datetime import datetime, timedelta, timezone

from catix.wiki import autopilot, sources


def test_only_the_data_may_be_committed():
    assert autopilot.outside(["wiki/guides/retakes.md", "raw/topics.json"]) == []
    assert autopilot.outside(["wiki/x.md", "src/catix/agent/roles.py", ".gitignore"]) == ["src/catix/agent/roles.py", ".gitignore"]


def test_a_source_is_asked_when_its_interval_has_passed():
    now = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)
    state = {"asked": {"eduwiki": (now - timedelta(hours=7)).isoformat(), "sveden": (now - timedelta(hours=2)).isoformat()}}
    assert [s.name for s in autopilot.due(state, now)] == ["eduwiki", "files", "sites"]  # files and sites were never asked
    assert [s.name for s in sources.SOURCES] == ["eduwiki", "sveden", "files", "sites"]


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
    monkeypatch.setattr(autopilot.settings, "wiki_agent", False)  # (the wiki's agent has tests of its own)
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
