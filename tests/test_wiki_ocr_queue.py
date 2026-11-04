"""Scans stay queued without OCR and can be read later, independently of a schedule or GPU switching."""

import contextlib
import json

import pytest

from catix.wiki.sources import chandra, opendataloader, regulations, sites


def test_the_queue_counts_the_scans_a_run_with_ocr_reads_and_not_those_too_long(tmp_path, monkeypatch):
    for key, note in {"short": {"ocr": "queued", "pages": 3}, "long": {"ocr": "queued", "pages": regulations.MAX_OCR_PAGES + 1},
                      "read": {"method": "text layer"}}.items():
        (tmp_path / f"{key}.json").write_text(json.dumps(note), encoding="utf-8")
    monkeypatch.setattr(regulations, "all_docs", lambda: {key: {"root": tmp_path} for key in ("short", "long", "read", "new")})
    assert regulations.queued() == {"short": 3}


def test_a_failed_scan_stays_queued_without_falling_back_after_retries(monkeypatch, tmp_path):
    key = "site-hotel-1-rules"
    monkeypatch.setattr(regulations, "all_docs", lambda: {key: {"title": "Правила", "url": "https://hotel.innopolis.university/r.pdf", "root": tmp_path,
                                                               "section": "site/hotel", "ext": "pdf"}})
    (tmp_path / f"{key}.pdf").write_bytes(b"%PDF-1.4 a scan")
    (tmp_path / f"{key}.json").write_text(json.dumps({"ocr": "queued", "pages": 3, "queued_at": "2026-11-01T10:00:00+00:00"}), encoding="utf-8")
    monkeypatch.setattr(sites, "collect_linked_docs", lambda: 0)
    monkeypatch.setattr(regulations, "discover_linked_documents", lambda: 0)
    monkeypatch.setattr(regulations, "pages_of", lambda pdf: 3)
    monkeypatch.setattr(opendataloader, "converted", lambda pdfs: contextlib.nullcontext({}))
    up = [True]
    monkeypatch.setattr(chandra, "text_of_pdf", lambda pdf, keep=None: None)
    monkeypatch.setattr(chandra, "available", lambda: up[0])
    monkeypatch.setattr(regulations.subprocess, "run", lambda *a, **k: pytest.fail("another OCR engine was started"))
    note = lambda: json.loads((tmp_path / f"{key}.json").read_text(encoding="utf-8"))  # noqa: E731

    assert regulations.read_new() == []
    assert note()["ocr"] == "queued" and note()["ocr_failed"] == 1 and note()["queued_at"] == "2026-11-01T10:00:00+00:00"
    up[0] = False  # (the server went away: not the scan's fault, not counted)
    assert regulations.read_new() == [] and note()["ocr_failed"] == 1
    up[0] = True
    for failed in range(2, 6):
        assert regulations.read_new() == []
        assert note()["ocr"] == "queued" and note()["ocr_failed"] == failed
        assert not (tmp_path / f"{key}.txt").exists()
    monkeypatch.setattr(chandra, "text_of_pdf", lambda pdf, keep=None: "1. Общие положения " * 50)
    assert regulations.read_new() == [key]
    assert "ocr" not in note() and note()["method"] == chandra.METHOD


@pytest.mark.parametrize("text", [None, "", "  \n"])
def test_an_unreadable_scan_is_not_successful_text(monkeypatch, tmp_path, text):
    monkeypatch.setattr(chandra, "text_of_pdf", lambda pdf, keep=None: text)
    monkeypatch.setattr(chandra, "available", lambda: True)
    with pytest.raises(regulations.NotRead):
        regulations.ocr_text(tmp_path / "scan.pdf")


def test_reextract_keeps_existing_text_when_chandra_fails(monkeypatch, tmp_path):
    key = "scan"
    meta = {"method": "ocr (legacy)", "chars": 8}
    (tmp_path / f"{key}.pdf").write_bytes(b"%PDF scan")
    (tmp_path / f"{key}.txt").write_text("old text")
    note = tmp_path / f"{key}.json"
    note.write_text(json.dumps(meta))
    monkeypatch.setattr(regulations, "all_docs", lambda: {key: {"root": tmp_path}})
    monkeypatch.setattr(opendataloader, "converted", lambda pdfs: contextlib.nullcontext({}))
    monkeypatch.setattr(regulations, "layer_text", lambda pdf, converted=None: None)
    monkeypatch.setattr(regulations, "pages_of", lambda pdf: 1)
    monkeypatch.setattr(chandra, "available", lambda: True)
    monkeypatch.setattr(chandra, "text_of_pdf", lambda pdf, keep=None: None)
    regulations.reextract()
    assert (tmp_path / f"{key}.txt").read_text() == "old text"
    assert json.loads(note.read_text()) == meta
    assert not regulations.read_again(key, tmp_path, note, meta, None, ocr_left=1)
