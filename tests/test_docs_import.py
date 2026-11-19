"""The one-off import of the old wiki's raw/ folder into source_files."""

import json

import pytest

from catix.docs import build, files, import_wiki


def test_only_the_sources_state_and_text_are_imported(tmp_path, monkeypatch, memory_files):
    raw = tmp_path / "raw"
    for rel, text in {
        "sites/hotel/index.json": json.dumps({"pages": {}}),
        "sites/hotel/a.md": "# A",
        "regulations/x.pdf": "%PDF",
        "regulations/x.txt": "text",
        "regulations/x.chandra/p-001.html": "<p>",
        "eduwiki/graph-cache.json": "{}",
    }.items():
        (raw / rel).parent.mkdir(parents=True, exist_ok=True)
        (raw / rel).write_text(text)
    rebuilt = []
    monkeypatch.setattr(build, "rebuild", lambda: rebuilt.append(1) or {})
    monkeypatch.setattr(import_wiki.store, "queued", lambda: 0)
    import_wiki.main(tmp_path)
    assert sorted(p for p in memory_files.items if not p.startswith("catalog/")) == ["regulations/x.txt", "sites/hotel/a.md", "sites/hotel/index.json"]
    assert files.read_json("sites/hotel/index.json") == {"pages": {}}
    assert rebuilt == [1]


def test_a_folder_without_raw_is_refused(tmp_path):
    with pytest.raises(SystemExit):
        import_wiki.main(tmp_path)
