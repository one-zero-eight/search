"""Scans stay queued without OCR and can be read later, independently of a schedule or GPU switching; the scans too long for
OCR are put aside, out of the queue; the queue is shown (`regs queue`) and the admins are told when it grows."""

import contextlib
import json

import httpx
import pytest

from catix.wiki import autopilot
from catix.wiki.sources import chandra, ocr_queue, opendataloader, pastpapers, regulations, sites

LONG = regulations.MAX_OCR_PAGES + 1


def test_the_queue_counts_the_scans_a_run_with_ocr_reads_and_not_those_too_long(tmp_path, monkeypatch):
    for key, note in {"short": {"ocr": "queued", "pages": 3}, "long": {"ocr": "queued", "pages": LONG},
                      "aside": {"ocr": "too long", "pages": LONG}, "covered": {"ocr": "too long", "pages": 5},  # (the limit was raised)
                      "read": {"method": "text layer"}}.items():
        (tmp_path / f"{key}.json").write_text(json.dumps(note), encoding="utf-8")
    monkeypatch.setattr(regulations, "all_docs", lambda: {key: {"root": tmp_path} for key in ("short", "long", "aside", "covered", "read", "new")})
    assert regulations.queued() == {"short": 3, "covered": 5}
    assert {key: regulations.ocr_state(note) for key, _, note in regulations.scan_notes()} == {
        "short": "queued", "long": "too long", "aside": "too long", "covered": "queued"}


def _one_scan(monkeypatch, tmp_path, pages):
    """One document on a site, a scan of `pages`; what the run asked: [downloads], [text layers], [scans read by OCR]."""
    url, key = "https://hotel.innopolis.university/upload/report.pdf", "site-hotel-1-report"
    monkeypatch.setattr(regulations, "all_docs", lambda: {key: {"title": "Отчёт", "url": url, "root": tmp_path, "section": "site/hotel", "ext": "pdf"}})
    monkeypatch.setattr(sites, "collect_linked_docs", lambda: 0)
    monkeypatch.setattr(regulations, "discover_linked_documents", lambda: 0)
    monkeypatch.setattr(regulations, "PAUSE", 0)
    asked, layers, read = [], [], []
    monkeypatch.setattr(regulations.httpx, "get", lambda u, **k: asked.append(u) or httpx.Response(200, content=b"%PDF-1.4 a scan", request=httpx.Request("GET", u)))
    monkeypatch.setattr(regulations, "pages_of", lambda pdf: pages)
    monkeypatch.setattr(opendataloader, "converted", lambda pdfs: contextlib.nullcontext({}))
    monkeypatch.setattr(regulations, "layer_text", lambda pdf, converted=None: layers.append(pdf.name))  # (None: a scan)
    monkeypatch.setattr(regulations, "ocr_text", lambda pdf: read.append(pdf.name) or ("1. Общие положения " * 50, chandra.METHOD))
    return key, asked, layers, read


@pytest.mark.parametrize("ocr", [False, True])
def test_a_scan_too_long_for_ocr_is_put_aside_not_queued_and_no_run_reads_it(monkeypatch, tmp_path, ocr):
    key, asked, layers, read = _one_scan(monkeypatch, tmp_path, LONG)
    note = lambda: json.loads((tmp_path / f"{key}.json").read_text(encoding="utf-8"))  # noqa: E731

    assert regulations.read_new(ocr=ocr) == []
    assert note()["ocr"] == "too long" and note()["pages"] == LONG and note()["queued_at"] and not read
    assert regulations.queued() == {}
    for again in (False, True):  # (neither kind of run downloads it, asks its text layer or reads it again)
        assert regulations.read_new(ocr=again) == []
    assert len(asked) == 1 and len(layers) == 1 and not read and note()["ocr"] == "too long"
    monkeypatch.setattr(regulations, "MAX_OCR_PAGES", LONG)  # (the limit raised: it is queued again, and read by a run with OCR)
    assert regulations.queued() == {key: LONG}
    assert regulations.read_new() == [key] and read == [f"{key}.pdf"] and len(layers) == 1 and "ocr" not in note()


def test_a_long_scan_queued_before_the_long_ones_were_put_aside_is_marked_so(monkeypatch, tmp_path):
    key, asked, layers, read = _one_scan(monkeypatch, tmp_path, LONG)
    (tmp_path / f"{key}.pdf").write_bytes(b"%PDF-1.4 a scan")
    (tmp_path / f"{key}.json").write_text(json.dumps({"title": "Отчёт", "ocr": "queued", "pages": LONG, "queued_at": "2026-11-01T10:00:00+00:00"}), encoding="utf-8")
    assert regulations.read_new() == [] and not asked and not layers and not read
    assert json.loads((tmp_path / f"{key}.json").read_text(encoding="utf-8")) == {
        "title": "Отчёт", "ocr": "too long", "pages": LONG, "queued_at": "2026-11-01T10:00:00+00:00"}


def test_a_long_scan_changed_on_the_site_is_downloaded_and_looked_at_again(monkeypatch, tmp_path):
    key, asked, layers, _ = _one_scan(monkeypatch, tmp_path, 3)  # (the new version: 3 pages)
    (tmp_path / f"{key}.json").write_text(json.dumps({"ocr": "too long", "pages": LONG, "sha256": "old", "refetch": True}), encoding="utf-8")
    assert regulations.read_new(ocr=False) == [] and len(asked) == 1 and len(layers) == 1
    note = json.loads((tmp_path / f"{key}.json").read_text(encoding="utf-8"))
    assert note["ocr"] == "queued" and note["pages"] == 3 and "refetch" not in note


def test_a_past_paper_too_long_for_ocr_is_put_aside(monkeypatch, tmp_path):
    from types import SimpleNamespace

    monkeypatch.setattr(pastpapers, "ROOT", tmp_path)
    monkeypatch.setattr(pastpapers, "INDEX", tmp_path / "index.json")
    monkeypatch.setattr(pastpapers, "PAUSE", 0)
    url = "https://files.example/exam.pdf"
    key = pastpapers.file_key(url)
    monkeypatch.setattr(pastpapers, "rows", lambda client: [{"id": "r1", "space": "s", "subject": "Math", "year": "2026", "exam": "Final", "files": [("exam.pdf", url)]}])
    requests = []
    client = httpx.Client(transport=httpx.MockTransport(lambda req: requests.append(req.url) or httpx.Response(200, content=b"%PDF scan")))
    monkeypatch.setattr(pastpapers.httpx, "Client", lambda **kw: contextlib.nullcontext(client))
    monkeypatch.setattr(regulations, "pages_of", lambda pdf: pastpapers.MAX_SCAN_PAGES + 1)
    monkeypatch.setattr(pastpapers.subprocess, "run", lambda *a, **kw: SimpleNamespace(stdout=""))
    monkeypatch.setattr(chandra, "text_of_pdf", lambda *a, **kw: pytest.fail("a scan too long for OCR was read"))
    try:
        assert pastpapers.fetch() == 1 and pastpapers.load()["r1"]["files"][key]["ocr"] == "too long"
        assert pastpapers.fetch() == 0 and len(requests) == 1
        (tmp_path / "index.json").write_text(json.dumps({"r1": {"subject": "Math", "year": "2026", "exam": "Final",  # (queued before the long ones were put aside)
                                                                "files": {key: {"name": "exam.pdf", "ocr": "queued", "pages": 30}}}}))
        assert pastpapers.fetch() == 1 and pastpapers.load()["r1"]["files"][key] == {"name": "exam.pdf", "ocr": "too long", "pages": 30}
        assert len(requests) == 1
    finally:
        client.close()


def _scan(key, pages, too_long=False, source="regs", title=None):
    return ocr_queue.Scan(source, key, title or f"Документ {key}", f"https://example.org/{key}.pdf", pages, too_long, "2026-11-04T01:00:00+00:00")


def test_the_queue_shows_the_scans_waiting_and_apart_the_long_ones(monkeypatch, tmp_path, capsys):
    for key, note in {"short": {"ocr": "queued", "pages": 3, "ocr_failed": 2, "queued_at": "2026-11-01T10:00:00+00:00"},
                      "long": {"ocr": "too long", "pages": LONG}}.items():
        (tmp_path / f"{key}.json").write_text(json.dumps(note), encoding="utf-8")
    monkeypatch.setattr(regulations, "all_docs", lambda: {key: {"root": tmp_path, "title": f"Положение {key}", "url": f"https://u.example/{key}.pdf"}
                                                          for key in ("short", "long")})
    monkeypatch.setattr(pastpapers, "load", lambda: {"r-1": {"subject": "Math", "year": "2025", "exam": "Final", "files": {
        "p1": {"name": "final.pdf", "ocr": "queued", "pages": 2}, "p2": {"name": "all.pdf", "ocr": "too long", "pages": 30},
        "p3": {"name": "read.pdf", "sha256": "x"}}}})
    found = ocr_queue.scans()
    assert [(s.source, s.key, s.pages, s.too_long) for s in found] == [
        ("papers", "p1", 2, False), ("regs", "short", 3, False), ("papers", "p2", 30, True), ("regs", "long", LONG, True)]
    assert found[1].failed == 2 and found[1].since.startswith("2026-11-01") and found[0].title == "Math 2025 Final: final.pdf"
    assert found[0].url == f"{pastpapers.SITE}/r1"
    ocr_queue.show(found)
    out = capsys.readouterr().out
    queue, apart = out.split("Too long for OCR")
    assert queue.startswith("OCR queue: 2 scans, 5 pages") and "short" in queue and "chandra failed 2x" in queue and "regs fetch" in queue and "papers fetch" in queue
    assert "long" not in queue and "p2" not in queue and "2 scans, 71 pages" in apart and "https://u.example/long.pdf" in apart


def test_the_message_names_the_new_scans_only_and_none_when_nothing_is_new():
    found = [_scan("a", 3), _scan("b", 4), _scan("c", LONG, too_long=True)]
    assert ocr_queue.message(found, set()) is None
    text = ocr_queue.message(found, {("regs", "b")})
    assert text.startswith("🖨 Очередь OCR выросла: 2 скана, 7 стр. (новые: 1 скан, 4 стр.)") and "Документ b" in text and "Документ a" not in text
    assert "📕" not in text and "catix-wiki regs fetch" in text and "papers fetch" not in text
    text = ocr_queue.message(found, {("regs", "c")})
    assert "🖨" not in text and text.startswith("📕 Слишком длинные для OCR сканы отложены, в очереди их нет: 1 скан") and "Документ c" in text
    many = [_scan(str(n), 1) for n in range(8)]
    text = ocr_queue.message(many, {("regs", s.key) for s in many})
    assert "8 сканов, 8 стр.:" in text and "новые" not in text and "• и ещё 3" in text


def test_the_admins_are_told_of_each_new_scan_once(monkeypatch, tmp_path):
    found, told = [_scan("a", 3)], []
    monkeypatch.setattr(autopilot, "STATE", tmp_path / ".autopilot.json")
    monkeypatch.setattr(ocr_queue, "scans", lambda: list(found))
    monkeypatch.setattr(autopilot, "tell_admins", told.append)
    state = {}
    autopilot.tell_ocr_queue(state)
    assert len(told) == 1 and "Документ a" in told[0]
    assert json.loads((tmp_path / ".autopilot.json").read_text())["ocr_told"] == [["regs", "a", False]]
    autopilot.tell_ocr_queue(state)  # (nothing new: nothing said)
    assert len(told) == 1
    found.append(_scan("b", 5))
    autopilot.tell_ocr_queue(state)
    assert len(told) == 2 and "Документ b" in told[1] and "Документ a" not in told[1] and "2 скана, 8 стр." in told[1]
    found[:] = [_scan("b", 5)]  # (a was read by OCR: it leaves, nobody is told)
    autopilot.tell_ocr_queue(state)
    assert len(told) == 2 and state["ocr_told"] == [["regs", "b", False]]
    found.append(_scan("a", 3))  # (it came back: told again)
    autopilot.tell_ocr_queue(state)
    assert len(told) == 3 and "Документ a" in told[2]
    found[:] = [_scan("a", 3), _scan("b", 5, too_long=True)]  # (b moved out of the queue: told as put aside)
    autopilot.tell_ocr_queue(state)
    assert len(told) == 4 and told[3].startswith("📕") and "Документ b" in told[3]


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
