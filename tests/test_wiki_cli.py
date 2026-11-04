"""The wiki CLI validates arguments before calling code that reads or writes data."""

import importlib
import sys
from pathlib import Path

import pytest

from catix.wiki import cli


def test_nested_help_does_not_start_discovery(monkeypatch, capsys):
    from catix.wiki.sources import discover

    def unexpected(*args, **kwargs):
        pytest.fail("help must not probe or write sites")

    monkeypatch.setattr(discover, "discover", unexpected)
    monkeypatch.setattr(sys, "argv", ["catix-wiki", "sites", "discover", "--help"])
    with pytest.raises(SystemExit) as result:
        cli.main()
    assert result.value.code == 0
    output = capsys.readouterr().out
    assert "--dry-run" in output and "--all" in output


def test_typed_options_are_passed_to_the_source(monkeypatch):
    from catix.wiki.sources import rpd

    calls = []
    monkeypatch.setattr(rpd, "fetch", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(sys, "argv", ["unrelated", "arguments"])
    cli.main(["rpd", "fetch", "--limit=3", "--all-years"])
    assert calls == [{"all_years": True, "limit": 3}]


def test_sites_fetch_only_new_is_typed(monkeypatch):
    from catix.wiki.sources import sites

    calls = []
    monkeypatch.setattr(sites, "fetch", lambda names, only_new=False: calls.append((names, only_new)))
    cli.main(["sites", "fetch", "apply", "--only-new"])
    assert calls == [(["apply"], True)]


@pytest.mark.parametrize("words", [
    ["unknown"], ["status", "extra"], ["fetch", "not-a-number"],
    ["sites", "disover"], ["sites", "discover", "--al"], ["sites", "discover", "--unknown"],
    ["sites", "explore", "--rounds"], ["sites", "explore", "--rounds=zero"],
    ["sites", "explore", "--rounds=0"], ["sites", "explore", "--max-sites=-1"],
    ["sites", "add"], ["sites", "accept"], ["sites", "reject"],
    ["sites", "accept", "lab", "--all"], ["sites", "reject", "--all", "lab"],
    ["regs"], ["regs", "fetch", "many"], ["rpd", "fetch", "--limit"],
    ["sveden", "override", "maybe", "x"], ["sveden", "override", "keep"],
    ["agent", "unknown"], ["agent", "notes", "--check", "--link"],
    ["agent", "candidates", "--output"], ["compile"], ["compile", "--random"],
    ["compile", "--sample", "--all"], ["compile", "--all", "Page"], ["compile", "link", "Page"],
    ["index", "export"], ["index", "import"], ["index", "status", "extra"],
    ["index", "status", "--no-embed"], ["autopilot", "--source"],
    ["autopilot", "accept", "--loop"], ["autopilot", "discard", "--no-push"],
])
def test_invalid_arguments_exit_two_before_work(words, capsys):
    with pytest.raises(SystemExit) as result:
        cli.main(words)
    assert result.value.code == 2
    assert "error:" in capsys.readouterr().err


@pytest.mark.parametrize("words,command,action", [
    ([], "status", None), (["sites"], "sites", "status"), (["sveden"], "sveden", "status"),
    (["papers"], "papers", "status"), (["rpd"], "rpd", "status"),
    (["agent"], "agent", "queue"), (["autopilot"], "autopilot", "run"), (["index"], "index", "sync"),
])
def test_defaults(words, command, action):
    parsed = cli.parse_args(words)
    assert (parsed.command, getattr(parsed, "action", None)) == (command, action)


@pytest.mark.parametrize("words,module,function,positional,keywords", [
    ([], "sources.eduwiki", "status", (), {}),
    (["fetch"], "sources.eduwiki", "fetch", ([0],), {}),
    (["fetch", "0", "14"], "sources.eduwiki", "fetch", ([0, 14],), {}),
    (["sveden"], "sources.sveden", "status", (), {}),
    (["sveden", "discover"], "sources.sveden", "discover", (), {}),
    (["sveden", "triage", "--redo"], "sources.sveden", "triage", (True,), {}),
    (["sveden", "override", "keep", "one", "two"], "sources.sveden", "override", ("keep", ["one", "two"]), {}),
    (["regs", "fetch", "3"], "sources.regulations", "fetch", (3,), {}),
    (["regs", "compile"], "sources.regulations", "compile_all", (), {}),
    (["regs", "refresh"], "sources.regulations", "refresh", (), {}),
    (["regs", "reextract"], "sources.regulations", "reextract", (), {}),
    (["rpd"], "sources.rpd", "status", (), {}),
    (["rpd", "compile"], "sources.rpd", "compile_all", (), {"all_years": None}),
    (["rpd", "compile", "--all-years"], "sources.rpd", "compile_all", (), {"all_years": True}),
    (["rpd", "refresh"], "sources.rpd", "refresh", (), {}),
    (["papers"], "sources.pastpapers", "status", (), {}),
    (["papers", "fetch"], "sources.pastpapers", "fetch", (), {}),
    (["papers", "compile"], "sources.pastpapers", "compile_all", (), {}),
    (["sites"], "sources.sites", "status", (), {}),
    (["sites", "fetch", "apply", "hotel"], "sources.sites", "fetch", (["apply", "hotel"],), {"only_new": False}),
    (["sites", "compile"], "sources.sites", "compile_all", (), {}),
    (["sites", "docs"], "sources.sites", "collect_linked_docs", (), {}),
    (["sites", "review"], "sources.discover", "review", (), {}),
    (["sites", "add", "https://example.org/"], "sources.discover", "add", (["https://example.org/"],), {}),
    (["compile", "--all"], "compile", "compile_pages", (None,), {}),
    (["compile", "--random=3"], "compile", "compile_pages", (None, 3), {}),
    (["compile", "Page A", "Page B"], "compile", "compile_pages", (["Page A", "Page B"],), {}),
    (["compile", "link"], "compile", "link", (), {}),
    (["link"], "compile", "link", (), {}),
    (["layout", "--dry-run"], "layout", "migrate", (True,), {}),
    (["graph", "--no-model"], "graph", "main", (), {"use_model": False}),
    (["agent"], "agent", "run", (), {}),
])
def test_commands_dispatch_typed_arguments(words, module, function, positional, keywords, monkeypatch):
    target = importlib.import_module("catix.wiki." + module)
    calls = []
    monkeypatch.setattr(target, function, lambda *args, **kwargs: calls.append((args, kwargs)) or 0)
    monkeypatch.setattr(sys, "argv", ["unrelated", "arguments"])
    cli.main(words)
    assert calls == [(positional, keywords)]


def test_explore_and_discover_options(monkeypatch):
    from catix.wiki import autopilot
    from catix.wiki.sources import discover

    calls = []
    monkeypatch.setattr(autopilot, "load_state", lambda: {"rejected_sites": ["no.example"]})
    monkeypatch.setattr(discover, "pending_hosts", lambda: [])
    monkeypatch.setattr(discover, "discover", lambda *a, **kw: calls.append((a, kw)) or 0)
    monkeypatch.setattr(discover, "explore", lambda *a, **kw: calls.append((a, kw)) or [])
    cli.main(["sites", "discover", "--all", "--dry-run"])
    cli.main(["sites", "explore", "--rounds=2", "--max-sites", "5"])
    assert calls == [(({"no.example"},), {"dry_run": True, "everything": True}), (({"no.example"}, 2, 5), {})]


def test_accept_changes_only_selected_pending_sites(tmp_path, monkeypatch):
    from catix.wiki.sources import discover, sites

    builds = []
    monkeypatch.setattr(discover, "build_approved", lambda names: builds.append(names))
    monkeypatch.setattr(sites, "DISCOVERED", tmp_path / "sites-discovered.json")
    monkeypatch.setattr(sites, "CONFIG", tmp_path / "sites.yaml")
    monkeypatch.setattr(sites, "SITES", dict(sites.SITES))
    sites.CONFIG.write_text("blocked: []\nsites: {}\n", encoding="utf-8")
    discover.write({"a.innopolis.university": {"status": "pending"}, "b.innopolis.university": {"status": "pending"},
                    "closed.innopolis.university": {"status": "closed"}})
    cli.main(["sites", "accept", "a"])
    assert "a.innopolis.university" not in sites.discovered()
    assert "a" in sites.load_config(sites.CONFIG)[0]
    assert sites.discovered()["b.innopolis.university"]["status"] == "pending"
    cli.main(["sites", "accept", "--all"])
    assert "b.innopolis.university" not in sites.discovered()
    assert {"a", "b"} <= set(sites.load_config(sites.CONFIG)[0])
    assert sites.discovered()["closed.innopolis.university"]["status"] == "closed"
    assert builds == [["a"], ["b"]]


def test_reject_all_includes_closed_but_not_accepted(tmp_path, monkeypatch):
    from catix.wiki import autopilot
    from catix.wiki.sources import discover, sites

    monkeypatch.setattr(sites, "DISCOVERED", tmp_path / "sites-discovered.json")
    monkeypatch.setattr(sites, "ROOT", tmp_path / "raw" / "sites")
    monkeypatch.setattr(sites, "SITES", {})
    monkeypatch.setattr(discover, "DOCS", tmp_path / "wiki" / "raw")
    monkeypatch.setattr(autopilot, "STATE", tmp_path / ".autopilot.json")
    discover.write({"a.innopolis.university": {"status": "pending"}, "b.innopolis.university": {"status": "closed"},
                    "kept.innopolis.university": {"status": "accepted"}})
    cli.main(["sites", "reject", "--all"])
    assert list(sites.discovered()) == ["kept.innopolis.university"]
    assert autopilot.load_state()["rejected_sites"] == ["a.innopolis.university", "b.innopolis.university"]


def test_autopilot_collects_repeated_sources_and_options(tmp_path, monkeypatch):
    from catix.wiki import autopilot

    calls = []
    monkeypatch.setattr(autopilot, "ready", lambda: None)
    monkeypatch.setattr(autopilot, "LOCK", tmp_path / "lock")
    monkeypatch.setattr(autopilot, "run_once", lambda *a, **kw: calls.append((a, kw)) or "done")
    cli.main(["autopilot", "--source", "sites", "files", "--no-answers", "--source", "papers", "--no-push"])
    assert calls == [((["sites", "files", "papers"],), {"push": False, "answers": False})]


def test_agent_keeps_legacy_paths_and_notes_get_only_paths(monkeypatch):
    from catix.wiki import agent, notes

    calls = []
    monkeypatch.setattr(agent, "Index", lambda: "index")
    monkeypatch.setattr(agent, "resolve", lambda page, idx: page + "-resolved")
    monkeypatch.setattr(agent, "run", lambda pages: calls.append(pages))
    monkeypatch.setattr(notes, "run", lambda pages: calls.append(pages))
    cli.main(["agent", "/raw/a.md", "/raw/b.md"])
    cli.main(["agent", "notes", "/raw/a.md", "/raw/b.md"])
    assert calls == [["/raw/a.md-resolved", "/raw/b.md-resolved"], ["/raw/a.md", "/raw/b.md"]]


@pytest.mark.parametrize("action", ["export", "import"])
def test_index_file_is_a_path(action, monkeypatch):
    from catix.wiki import search_index

    calls = []
    monkeypatch.setattr(search_index.settings, "database_url", "configured-for-test")
    monkeypatch.setattr(search_index, "export" if action == "export" else "import_", calls.append)
    monkeypatch.setattr(search_index.pg, "close", lambda: None)
    cli.main(["index", action, "index.tar.gz"])
    assert calls == [Path("index.tar.gz")]


@pytest.mark.parametrize("action", ["accept", "discard"])
def test_autopilot_review_dispatch(action, monkeypatch):
    from catix.wiki import autopilot

    calls = []
    monkeypatch.setattr(autopilot, "ready", lambda: None)
    monkeypatch.setattr(autopilot, "accept", lambda push: calls.append(push))
    monkeypatch.setattr(autopilot, "discard", lambda: calls.append("discard"))
    cli.main(["autopilot", action, *(["--no-push"] if action == "accept" else [])])
    assert calls == ([False] if action == "accept" else ["discard"])


def test_offline_build_does_not_update_sources(monkeypatch):
    from types import SimpleNamespace
    from catix.wiki import build

    calls = []
    monkeypatch.setattr(build.sources, "SOURCES", [SimpleNamespace(name="test", update=lambda: pytest.fail("offline build fetched a source"))])
    monkeypatch.setattr(build, "rebuild", lambda: calls.append("build") or build.Report())
    with pytest.raises(SystemExit) as result:
        cli.main(["build", "--offline"])
    assert result.value.code == 0 and calls == ["build"]


def test_agent_link_and_candidate_options(monkeypatch):
    from types import SimpleNamespace
    from catix.wiki import links

    calls = []
    monkeypatch.setattr(links, "apply", lambda **kw: calls.append(kw) or SimpleNamespace(links=0, cards_linked=0, cards=0, names=0, changed=[], ambiguous=[]))
    monkeypatch.setattr(links, "candidates", lambda **kw: calls.append(kw) or SimpleNamespace(phrases=0, articles=0, items=[], output=kw["output"]))
    cli.main(["agent", "links", "--dry-run"])
    cli.main(["agent", "candidates", "--output", "report.json", "--folders", "courses,pages"])
    assert calls == [{"dry_run": True}, {"output": Path("report.json"), "skip": ("courses", "pages")}]


@pytest.mark.parametrize("command", [
    [], ["sites"], ["sites", "discover"], ["sites", "explore"], ["sites", "accept"], ["sites", "reject"],
    ["agent"], ["agent", "notes"], ["agent", "candidates"], ["autopilot"], ["index"], ["compile"],
])
def test_help_is_available_at_each_level(command, capsys):
    with pytest.raises(SystemExit) as result:
        cli.main([*command, "--help"])
    assert result.value.code == 0
    assert "usage:" in capsys.readouterr().out
