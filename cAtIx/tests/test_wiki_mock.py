"""The stand-in site (wiki/mock.py): a listing becomes documents, a new version is found by HEAD like on the real site."""

import json
import os
import time


def test_a_listed_document_is_found_and_its_new_version_noticed(tmp_path, monkeypatch):
    from catix.wiki import mock, regulations

    site, raw = tmp_path / "site", tmp_path / "mock"
    site.mkdir()
    (site / "Положение_о_тесте.pdf").write_bytes(b"%PDF version 1")
    server = mock.serve(site, port=0)
    try:
        monkeypatch.setattr(mock.settings, "wiki_mock_site", f"http://127.0.0.1:{server.server_port}/")
        monkeypatch.setattr(mock, "ROOT", raw)
        monkeypatch.setattr(mock, "INDEX", raw / "index.json")
        monkeypatch.setattr(regulations, "PAUSE", 0)
        assert mock.discover() == 1
        (key, doc), = mock.docs().items()
        assert key.startswith("mock-") and doc["title"] == "Положение о тесте" and doc["root"] == raw

        meta = raw / f"{key}.json"
        meta.write_text(json.dumps({"sha256": "x", "url": doc["url"]}))
        assert regulations.refresh(prefix="mock-") == 0  # the first look only records what the site says
        assert json.loads(meta.read_text())["remote"]["size"] == str(len(b"%PDF version 1"))

        (site / "Положение_о_тесте.pdf").write_bytes(b"%PDF version 2, longer")
        os.utime(site / "Положение_о_тесте.pdf", (time.time() + 5, time.time() + 5))
        assert regulations.refresh(prefix="mock-") == 1
        assert json.loads(meta.read_text())["refetch"] is True
    finally:
        server.shutdown()
