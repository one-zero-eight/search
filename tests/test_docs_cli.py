"""The documents CLI validates arguments before calling code that reads or writes data."""

import importlib
import sys

import pytest

from catix.docs import cli
from catix.settings import settings


@pytest.fixture(autouse=True)
def database(monkeypatch):
    from catix.docs import frontier

    monkeypatch.setattr(settings, "database_url", "configured-for-test")
    monkeypatch.setattr(sys, "argv", ["unrelated", "arguments"])
    monkeypatch.setattr(frontier, "ensure_imported", lambda: None)  # (the old store is imported before the commands that read: no database here)
    monkeypatch.setattr(frontier, "status", lambda: None)


def test_nested_help_does_not_read_sources(monkeypatch, capsys):
    from catix.docs.sources import sites

    monkeypatch.setattr(sites, "main", lambda *a, **kw: pytest.fail("help must not read sites"))
    with pytest.raises(SystemExit) as result:
        cli.main(["sites", "unvisited", "--help"])
    assert result.value.code == 0
    output = capsys.readouterr().out
    assert "--summary" in output and "SITE" in output


def test_typed_options_are_passed_to_the_source(monkeypatch):
    from catix.docs.sources import rpd

    calls = []
    monkeypatch.setattr(rpd, "fetch", lambda **kwargs: calls.append(kwargs))
    cli.main(["rpd", "fetch", "--limit=3", "--all-years"])
    assert calls == [{"all_years": True, "limit": 3}]


def test_the_old_store_is_imported_before_a_command_that_reads_the_sources(monkeypatch):
    from catix.docs import frontier
    from catix.docs.sources import rpd

    calls = []
    monkeypatch.setattr(frontier, "ensure_imported", lambda: calls.append("import"))
    monkeypatch.setattr(rpd, "status", lambda: calls.append("status"))
    cli.main(["rpd"])
    assert calls == ["import", "status"]


def test_without_a_database_nothing_runs(monkeypatch):
    monkeypatch.setattr(settings, "database_url", "")
    with pytest.raises(SystemExit) as result:
        cli.main(["status"])
    assert "DATABASE_URL" in str(result.value.code)


@pytest.mark.parametrize("words", [
    ["unknown"], ["status", "extra"], ["fetch", "not-a-number"],
    ["sites", "disover"], ["sites", "discover"], ["sites", "explore"], ["sites", "add", "https://example.org/"],
    ["sites", "accept", "lab"], ["sites", "reject", "lab"], ["sites", "review"], ["sites", "migrate"], ["sites", "compile"],
    ["regs"], ["regs", "fetch", "many"], ["regs", "fetch", "0"], ["regs", "compile"], ["regs", "reextract"],
    ["rpd", "fetch", "--limit"], ["rpd", "compile"], ["papers"],
    ["sveden"], ["agent"], ["layout"], ["compile"], ["link"], ["graph"], ["lint"], ["index"],
    ["autopilot"], ["autopilot", "accept"], ["fetch"], ["build", "--offline"],
    ["run", "--source"], ["run", "--no-push"], ["run", "--only-new"], ["import-wiki"],
    ["regs", "refresh"], ["sites", "fetch"], ["sites", "new"], ["sites", "docs"],
])
def test_invalid_arguments_exit_two_before_work(words, capsys):
    with pytest.raises(SystemExit) as result:
        cli.main(words)
    assert result.value.code == 2
    assert "error:" in capsys.readouterr().err


@pytest.mark.parametrize("words,command,action", [
    ([], "status", None), (["status"], "status", None),
    (["eduwiki"], "eduwiki", "status"), (["sites"], "sites", "status"),
    (["rpd"], "rpd", "status"),
    (["run"], "run", None), (["build"], "build", None),
])
def test_defaults(words, command, action):
    parsed = cli.parse_args(words)
    assert (parsed.command, getattr(parsed, "action", None)) == (command, action)


def test_run_options_are_collected():
    parsed = cli.parse_args(["run", "--source", "rpd", "rpd-refresh", "--source", "eduwiki", "--site", "hotel", "--site", "campuslife", "--loop", "--build"])
    assert (parsed.source, parsed.site, parsed.loop, parsed.build) == (["rpd", "rpd-refresh", "eduwiki"], ["hotel", "campuslife"], True, True)
    parsed = cli.parse_args(["run"])
    assert (parsed.source, parsed.site, parsed.loop, parsed.build) == (None, None, False, False)


@pytest.mark.parametrize("words,module,function,positional,keywords", [
    ([], "store", "status", (), {}),
    (["status"], "store", "status", (), {}),
    (["eduwiki"], "sources.eduwiki", "status", (), {}),
    (["eduwiki", "fetch"], "sources.eduwiki", "fetch", ([0],), {}),
    (["eduwiki", "fetch", "0", "14"], "sources.eduwiki", "fetch", ([0, 14],), {}),
    (["regs", "fetch", "3"], "sources.regulations", "fetch", (3,), {"ocr": True}),
    (["rpd"], "sources.rpd", "status", (), {}),
    (["rpd", "refresh"], "sources.rpd", "refresh", (), {}),
    (["sites", "status"], "sources.sites", "main", None, None),
])
def test_commands_dispatch_typed_arguments(words, module, function, positional, keywords, monkeypatch):
    target = importlib.import_module("catix.docs." + module)
    calls = []
    monkeypatch.setattr(target, function, lambda *args, **kwargs: calls.append((args, kwargs)) or 0)
    cli.main(words)
    if positional is None:  # (the sites' commands go through main(args))
        assert len(calls) == 1
    else:
        assert calls == [(positional, keywords)]


def test_regs_fetch_reads_the_documents_only(monkeypatch):
    from catix.docs.sources import regulations

    calls = []
    monkeypatch.setattr(regulations, "fetch", lambda *args, **kwargs: calls.append((args, kwargs)) or 2)
    cli.main(["regs", "fetch", "--no-ocr"])
    cli.main(["regs", "fetch", "3"])
    assert calls == [((None,), {"ocr": False}), ((3,), {"ocr": True})]  # (the crawl follows the links to the pages: no pass over sites here)


def test_run_hands_its_arguments_to_the_runner(monkeypatch):
    from catix.docs import runner

    calls = []
    monkeypatch.setattr(runner, "main", calls.append)
    cli.main(["run", "--source", "rpd", "rpd-refresh", "--site", "hotel", "--loop"])
    (args,) = calls
    assert (args.source, args.site, args.loop, args.build) == (["rpd", "rpd-refresh"], ["hotel"], True, False)


@pytest.mark.parametrize("embed", [False, True])
def test_build_rebuilds_and_optionally_embeds(embed, monkeypatch):
    from catix.docs import build, store

    calls = []
    monkeypatch.setattr(build, "rebuild", lambda groups=None: calls.append("build") or {})
    monkeypatch.setattr(store, "embed_all", lambda: calls.append("embed") or 0)
    cli.main(["build", *(["--embed"] if embed else [])])
    assert calls == (["build", "embed"] if embed else ["build"])


@pytest.mark.parametrize("command", [
    [], ["run"], ["build"], ["eduwiki"], ["eduwiki", "fetch"], ["regs"], ["regs", "fetch"],
    ["rpd"], ["sites"], ["sites", "unvisited"], ["sites", "request"],
])
def test_help_is_available_at_each_level(command, capsys):
    with pytest.raises(SystemExit) as result:
        cli.main([*command, "--help"])
    assert result.value.code == 0
    assert "usage:" in capsys.readouterr().out
