"""The mutable site registry belongs to the wiki data, not the installed package."""

import json
import os
import subprocess
import sys
from dataclasses import asdict
import pytest
import yaml

from catix.wiki.sources import crawl, discover, sites


def test_catalog_reloads_after_another_process_changes_the_data_file(tmp_path, monkeypatch):
    config = tmp_path / "raw" / "sites.yaml"
    config.parent.mkdir()
    monkeypatch.setattr(sites, "CONFIG", config)
    monkeypatch.setattr(sites, "DISCOVERED", config.with_name("sites-discovered.json"))
    monkeypatch.setattr(sites, "SITES", {})
    config.write_text("blocked: []\nsites: {}\n")
    assert crawl.provider("https://lab.example/") is None
    config.write_text("blocked: []\nsites:\n  lab:\n    base: https://lab.example/\n    language: en\n    about: Lab\n    skip: ''\n")
    assert crawl.provider("https://lab.example/") == "lab"
    assert "lab.example" in discover.known_hosts()
    config.write_text("blocked: [lab.example]\nsites: {}\n")
    assert crawl.provider("https://lab.example/") is None
    assert "lab" not in sites.SITES


def test_approval_moves_pending_settings_into_the_data_catalog(monkeypatch):
    configured = sites.Site("https://lab.example/", "en", "Lab", "private", max_pages=7, robots=True,
                            pause=4, render=True, aliases=("old-lab.example",))
    entry = {"status": "pending", "kind": "external", "name": "lab-project", "config": asdict(configured)}
    discover.write({"lab.example": entry, "closed.example": {"status": "closed"}})
    approved_before = sites.CONFIG.read_bytes()
    assert sites.pending_sites()["lab-project"] == configured
    assert sites.every_site()["lab-project"] == configured
    assert crawl.provider("https://lab.example/") is None
    assert sites.CONFIG.read_bytes() == approved_before
    assert not sites.DISCOVERED.with_name("sites-pending.yaml").exists()

    assert discover.accept_pending(["lab.example"]) == ["lab.example"]
    assert sites.load_sites()["lab-project"] == configured
    assert sites.discovered() == {"closed.example": {"status": "closed"}}
    assert sites.pending_sites() == {}
    assert crawl.provider("https://lab.example/") == "lab-project"
    assert crawl.provider("https://old-lab.example/") == "lab-project"
    snapshot = sites.CONFIG.read_bytes(), sites.DISCOVERED.read_bytes()
    assert discover.accept_pending() == []
    assert snapshot == (sites.CONFIG.read_bytes(), sites.DISCOVERED.read_bytes())


def test_migration_preserves_catalog_and_pending_overrides_and_is_idempotent(tmp_path, monkeypatch):
    legacy = tmp_path / "code" / "sites.yaml"
    legacy.parent.mkdir()
    legacy.write_bytes(sites.CONFIG.read_bytes())
    original = legacy.read_bytes()
    config = tmp_path / "data" / "raw" / "sites.yaml"
    config.parent.mkdir(parents=True)
    monkeypatch.setattr(sites, "CONFIG", config)
    monkeypatch.setattr(sites, "DISCOVERED", config.with_name("sites-discovered.json"))
    old_pending = config.with_name("sites-pending.yaml")
    settings = json.loads(json.dumps(asdict(sites.Site("https://lab.example/", "en", "Lab", "private", render=True, max_pages=9))))
    old_pending.write_text(yaml.safe_dump({"sites": {"lab-custom": settings}}))
    pending_bytes = old_pending.read_bytes()
    discover.write({"lab.example": {"status": "pending", "title": "Lab", "pages": 3},
                    "approved.example": {"status": "accepted", "title": "Approved"},
                    "failed.example": {"status": "failed", "reason": "offline"}})

    sites.migrate_catalog(legacy)
    assert legacy.read_bytes() == original
    assert sites.CONFIG.parent == config.parent
    assert "university" in sites.load_sites() and "approved-example" in sites.load_sites()
    entry = sites.discovered()["lab.example"]
    assert entry["name"] == "lab-custom" and entry["config"] == settings and entry["pages"] == 3
    assert sites.pending_sites()["lab-custom"].max_pages == 9
    assert sites.discovered()["failed.example"] == {"status": "failed", "reason": "offline"}
    assert "approved.example" not in sites.discovered()
    assert not old_pending.exists()
    assert old_pending.with_suffix(".yaml.bak").read_bytes() == pending_bytes
    snapshot = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in config.parent.iterdir()}
    sites.migrate_catalog(legacy)
    assert snapshot == {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in config.parent.iterdir()}


def test_cli_migrates_catalog_and_approves_without_editing_source(tmp_path, monkeypatch):
    from catix.wiki import cli

    monkeypatch.setattr(discover, "build_approved", lambda names: None)  # real HTTP-to-wiki coverage: test_wiki_site_approval.py
    source = tmp_path / "source.yaml"
    source.write_bytes(sites.CONFIG.read_bytes())
    before = source.read_bytes()
    sites.CONFIG.unlink()
    cli.main(["sites", "migrate", "--from", str(source)])
    assert sites.CONFIG.read_bytes() == before
    discover.write({"lab.example": {"status": "pending"}})
    cli.main(["sites", "approve", "lab-example"])
    assert "lab-example" in sites.load_sites()
    assert sites.discovered() == {}
    assert source.read_bytes() == before


def test_custom_pending_name_is_used_by_only_new(monkeypatch):
    from catix.wiki import sources
    from catix.wiki.sources import regulations

    discover.write({"lab.example": {"status": "pending", "name": "lab-project"}})
    seen = []
    monkeypatch.setattr(sites, "fetch", lambda names, **kwargs: seen.extend(names) or 1)
    monkeypatch.setattr(regulations, "fetch", lambda: 0)
    assert sources.ON_REQUEST[0].update() == 1
    assert seen == ["lab-project"]


def test_import_with_empty_wiki_root_does_not_create_a_catalog(tmp_path):
    root = tmp_path / "empty-wiki"
    result = subprocess.run([sys.executable, "-c", "from catix.wiki.sources import sites; print(sites.CONFIG)"],
                            env={**os.environ, "WIKI_ROOT": str(root)}, capture_output=True, text=True, check=True)
    assert result.stdout.strip() == str(root / "raw" / "sites.yaml")
    assert not root.exists()


def test_migration_conflict_does_not_change_any_file():
    pending = sites.DISCOVERED.with_name("sites-pending.yaml")
    pending.write_text(yaml.safe_dump({"sites": {"lab": asdict(sites.Site("https://lab.example/", "en", "Lab", ""))}}))
    discover.write({"lab.example": {"status": "closed", "reason": "login"}})
    snapshot = {p: p.read_bytes() for p in (sites.CONFIG, sites.DISCOVERED, pending)}
    with pytest.raises(ValueError, match="conflicts"):
        sites.migrate_catalog()
    assert snapshot == {p: p.read_bytes() for p in snapshot}


def test_approval_and_git_rollback_share_the_data_checkout(tmp_path, monkeypatch):
    from catix.wiki import autopilot

    root = tmp_path / "wiki-checkout"
    subprocess.run(["git", "init", "-q", "-b", "wiki", str(root)], check=True)
    (root / "raw").mkdir()
    (root / "wiki").mkdir()
    (root / ".gitignore").write_text(".autopilot.*\n")
    config = root / "raw" / "sites.yaml"
    config.write_text("blocked: []\nsites: {}\n")
    monkeypatch.setattr(sites, "CONFIG", config)
    monkeypatch.setattr(sites, "DISCOVERED", config.with_name("sites-discovered.json"))
    monkeypatch.setattr(autopilot, "DATA", root)
    monkeypatch.setattr(autopilot, "STATE", root / ".autopilot.json")
    monkeypatch.setattr(autopilot.settings, "database_url", None)
    discover.write({})
    autopilot.git("add", "-A")
    autopilot.git("commit", "-q", "-m", "initial data")
    discover.write({"lab.example": {"status": "pending"}})
    (root / "wiki" / "lab.md").write_text("Lab page\n")
    builds = []
    monkeypatch.setattr(discover, "build_approved", lambda names: builds.append(names))
    assert autopilot.accept(push=False).startswith("committed")
    assert builds == [["lab-example"]]
    changed = set(autopilot.git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines())
    assert changed == {"raw/sites.yaml", "wiki/lab.md"}
    assert "lab-example" in yaml.safe_load(autopilot.git("show", "HEAD:raw/sites.yaml"))["sites"]
    assert not autopilot.git("status", "--porcelain")
    discover.write({"second.example": {"status": "pending"}})
    discover.accept_pending()
    assert crawl.provider("https://second.example/") == "second-example"
    autopilot.discard()
    assert crawl.provider("https://second.example/") is None
    assert crawl.provider("https://lab.example/") == "lab-example"


def test_pending_name_collision_cannot_delete_an_approved_sites_pages(tmp_path, monkeypatch):
    from catix.wiki import autopilot

    monkeypatch.setattr(sites, "ROOT", tmp_path / "raw" / "sites")
    monkeypatch.setattr(discover, "DOCS", tmp_path / "wiki" / "raw")
    monkeypatch.setattr(autopilot, "STATE", tmp_path / ".autopilot.json")
    page = sites.ROOT / "university" / "home.md"
    page.parent.mkdir(parents=True)
    page.write_text("approved page")
    discover.write({"other.example": {"status": "closed", "name": "university"}})
    with pytest.raises(ValueError, match="approved"):
        discover.reject(["other.example"])
    assert page.read_text() == "approved page"
    assert "other.example" in sites.discovered()


def test_pending_name_collision_is_not_silently_hidden():
    discover.write({"other.example": {"status": "pending", "name": "university"}})
    with pytest.raises(ValueError, match="another approved host"):
        sites.pending_sites()


def test_missing_catalog_cannot_delete_existing_wiki_pages(tmp_path, monkeypatch):
    monkeypatch.setattr(sites, "DOCS", tmp_path / "wiki" / "raw")
    page = sites.DOCS / "sites" / "lab" / "home.md"
    page.parent.mkdir(parents=True)
    page.write_text("existing page")
    sites.CONFIG.unlink()
    with pytest.raises(FileNotFoundError, match="catalog missing"):
        sites.compile_all()
    assert page.read_text() == "existing page"


def test_rejected_pending_record_restored_by_git_is_not_read(monkeypatch, tmp_path):
    from catix.wiki import autopilot

    monkeypatch.setattr(autopilot, "STATE", tmp_path / ".autopilot.json")
    autopilot.save_state({"rejected_sites": ["lab.example"]})
    discover.write({"lab.example": {"status": "pending"}})
    assert sites.pending_sites() == {}
    assert discover.pending_hosts() == []
