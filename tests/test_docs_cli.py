"""The documents CLI validates arguments before calling code that reads or writes data."""

import importlib
import sys
from pathlib import Path

import pytest

from catix.docs import cli
from catix.settings import settings


@pytest.fixture(autouse=True)
def database(monkeypatch):
    monkeypatch.setattr(settings, "database_url", "configured-for-test")
    monkeypatch.setattr(sys, "argv", ["unrelated", "arguments"])


def test_nested_help_does_not_read_sources(monkeypatch, capsys):
    from catix.docs.sources import sites

    monkeypatch.setattr(sites, "fetch", lambda *a, **kw: pytest.fail("help must not read sites"))
    with pytest.raises(SystemExit) as result:
        cli.main(["sites", "fetch", "--help"])
    assert result.value.code == 0
    output = capsys.readouterr().out
    assert "--only-new" in output and "SITE" in output


def test_typed_options_are_passed_to_the_source(monkeypatch):
    from catix.docs.sources import rpd

    calls = []
    monkeypatch.setattr(rpd, "fetch", lambda **kwargs: calls.append(kwargs))
    cli.main(["rpd", "fetch", "--limit=3", "--all-years"])
    assert calls == [{"all_years": True, "limit": 3}]


def test_sites_fetch_only_new_is_typed(monkeypatch):
    from catix.docs.sources import sites

    calls = []
    monkeypatch.setattr(sites, "fetch", lambda names, only_new=False, documents=False: calls.append((names, only_new, documents)) or 0)
    cli.main(["sites", "fetch", "apply", "--only-new"])
    assert calls == [(["apply"], True, False)]  # (only the new linked pages: not the documents' waves)


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
    ["rpd", "fetch", "--limit"], ["rpd", "compile"], ["papers", "compile"],
    ["sveden"], ["agent"], ["layout"], ["compile"], ["link"], ["graph"], ["lint"], ["index"],
    ["autopilot"], ["autopilot", "accept"], ["fetch"], ["build", "--offline"],
    ["run", "--source"], ["run", "--no-push"], ["run", "--only-new"], ["import-wiki"],
])
def test_invalid_arguments_exit_two_before_work(words, capsys):
    with pytest.raises(SystemExit) as result:
        cli.main(words)
    assert result.value.code == 2
    assert "error:" in capsys.readouterr().err


@pytest.mark.parametrize("words,command,action", [
    ([], "status", None), (["status"], "status", None),
    (["eduwiki"], "eduwiki", "status"), (["sites"], "sites", "status"),
    (["papers"], "papers", "status"), (["rpd"], "rpd", "status"),
    (["run"], "run", None), (["build"], "build", None),
])
def test_defaults(words, command, action):
    parsed = cli.parse_args(words)
    assert (parsed.command, getattr(parsed, "action", None)) == (command, action)


def test_run_options_are_collected():
    parsed = cli.parse_args(["run", "--source", "sites", "files", "--source", "papers", "--site", "hotel", "--site", "campuslife", "--loop", "--build"])
    assert (parsed.source, parsed.site, parsed.loop, parsed.build) == (["sites", "files", "papers"], ["hotel", "campuslife"], True, True)
    parsed = cli.parse_args(["run"])
    assert (parsed.source, parsed.site, parsed.loop, parsed.build) == (None, None, False, False)


@pytest.mark.parametrize("words,module,function,positional,keywords", [
    ([], "store", "status", (), {}),
    (["status"], "store", "status", (), {}),
    (["eduwiki"], "sources.eduwiki", "status", (), {}),
    (["eduwiki", "fetch"], "sources.eduwiki", "fetch", ([0],), {}),
    (["eduwiki", "fetch", "0", "14"], "sources.eduwiki", "fetch", ([0, 14],), {}),
    (["regs", "fetch", "3"], "sources.regulations", "fetch", (3,), {"ocr": True}),
    (["regs", "refresh"], "sources.regulations", "refresh", (), {}),
    (["rpd"], "sources.rpd", "status", (), {}),
    (["rpd", "refresh"], "sources.rpd", "refresh", (), {}),
    (["papers"], "sources.pastpapers", "status", (), {}),
    (["papers", "fetch"], "sources.pastpapers", "fetch", (), {}),
    (["sites"], "sources.sites", "status", (), {}),
    (["sites", "fetch", "apply", "hotel"], "sources.sites", "fetch", (["apply", "hotel"],), {"only_new": False, "documents": True}),
    (["sites", "fetch", "--only-new"], "sources.sites", "fetch", ([],), {"only_new": True, "documents": False}),
    (["sites", "new", "apply"], "sources.sites", "fetch_new", (["apply"],), {"documents": True}),
    (["sites", "docs"], "sources.sites", "collect_linked_docs", (), {}),
    (["import-wiki", "/data/wiki"], "import_wiki", "main", (Path("/data/wiki"),), {}),
])
def test_commands_dispatch_typed_arguments(words, module, function, positional, keywords, monkeypatch):
    target = importlib.import_module("catix.docs." + module)
    calls = []
    monkeypatch.setattr(target, function, lambda *args, **kwargs: calls.append((args, kwargs)) or 0)
    cli.main(words)
    assert calls == [(positional, keywords)]


def test_regs_fetch_reads_the_documents_then_the_trusted_pages_no_run_has_read(monkeypatch):
    from catix.docs.sources import regulations, sites

    calls = []
    monkeypatch.setattr(regulations, "fetch", lambda *args, **kwargs: calls.append(("documents", args, kwargs)) or 2)
    monkeypatch.setattr(sites, "fetch", lambda *args, **kwargs: calls.append(("pages", args, kwargs)) or 3)
    cli.main(["regs", "fetch", "--no-ocr"])
    assert calls == [("documents", (None,), {"ocr": False}), ("pages", (), {"only_new": True, "documents": True, "ocr": False})]
    calls.clear()
    cli.main(["regs", "fetch", "3"])
    assert calls == [("documents", (3,), {"ocr": True})]  # (N: a quick run of documents only, no pages)


def test_run_hands_its_arguments_to_the_runner(monkeypatch):
    from catix.docs import runner

    calls = []
    monkeypatch.setattr(runner, "main", calls.append)
    cli.main(["run", "--source", "sites", "files", "--site", "hotel", "--loop"])
    (args,) = calls
    assert (args.source, args.site, args.loop, args.build) == (["sites", "files"], ["hotel"], True, False)


@pytest.mark.parametrize("embed", [False, True])
def test_build_rebuilds_and_optionally_embeds(embed, monkeypatch):
    from catix.docs import build, store

    calls = []
    monkeypatch.setattr(build, "rebuild", lambda: calls.append("build") or {})
    monkeypatch.setattr(store, "embed_all", lambda: calls.append("embed") or 0)
    cli.main(["build", *(["--embed"] if embed else [])])
    assert calls == (["build", "embed"] if embed else ["build"])


@pytest.mark.parametrize("command", [
    [], ["run"], ["build"], ["import-wiki"], ["eduwiki"], ["eduwiki", "fetch"], ["regs"], ["regs", "fetch"],
    ["rpd"], ["papers"], ["sites"], ["sites", "fetch"], ["sites", "new"],
])
def test_help_is_available_at_each_level(command, capsys):
    with pytest.raises(SystemExit) as result:
        cli.main([*command, "--help"])
    assert result.value.code == 0
    assert "usage:" in capsys.readouterr().out
