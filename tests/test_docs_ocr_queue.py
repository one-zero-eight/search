"""Scans stay queued without OCR and can be read later, independently of a schedule or GPU switching; the scans too long for
OCR are put aside, out of the queue; the queue is shown (`regs queue`) and the admins are told when it grows."""

import contextlib
import json
import tempfile

import httpx
import pytest

from catix.docs import notes, runner
from catix.docs.sources import lighton, tesseract, ocr_queue, opendataloader, regulations
from tests.helpers import link_document

LONG = regulations.MAX_OCR_PAGES + 1


def test_the_queue_counts_the_scans_a_run_with_ocr_reads_and_not_those_too_long(monkeypatch, docs_db):
    for key, note in {"short": {"ocr": "queued", "pages": 3}, "long": {"ocr": "queued", "pages": LONG},
                      "aside": {"ocr": "too long", "pages": LONG}, "covered": {"ocr": "too long", "pages": 5},  # (the limit was raised)
                      "read": {"method": "text layer"}}.items():
        notes.put_note(key, "", note)
    monkeypatch.setattr(regulations, "all_docs", lambda: {key: {} for key in ("short", "long", "aside", "covered", "read", "new")})
    assert regulations.queued() == {"short": 3, "covered": 5}
    assert {key: regulations.ocr_state(note) for key, _, note in regulations.scan_notes()} == {
        "short": "queued", "long": "too long", "aside": "too long", "covered": "queued"}


def test_the_queue_is_of_the_revision_of_the_document_now(monkeypatch, docs_db):
    """A member of an archive is read again under a new revision: the scan of the old revision is no longer waiting."""
    notes.put_note("member", "old", {"ocr": "queued", "pages": 3})
    notes.put_note("member", "new", {"ocr": "queued", "pages": 4})
    monkeypatch.setattr(regulations, "all_docs", lambda: {"member": {"revision": "new"}, "gone": {}})
    notes.put_note("gone", "", {"ocr": "queued", "pages": 1})
    notes.put_note("other", "", {"ocr": "queued", "pages": 2})  # (not a document any more)
    assert regulations.queued() == {"member": 4, "gone": 1}


def _one_scan(monkeypatch, tmp_path, pages):
    """One document on a site, a scan of `pages`; what the run asked: [downloads], [text layers], [scans read by OCR]."""
    url, key = "https://hotel.innopolis.university/upload/report.pdf", "site-hotel-1-report"
    monkeypatch.setattr(regulations, "all_docs", lambda: {key: {"title": "Отчёт", "url": url, "section": "site/hotel", "ext": "pdf"}})
    monkeypatch.setattr(regulations, "PAUSE", 0)
    asked, layers, read = [], [], []
    monkeypatch.setattr(regulations.httpx, "get", lambda u, **k: asked.append(u) or httpx.Response(200, content=b"%PDF-1.4 a scan", request=httpx.Request("GET", u)))
    monkeypatch.setattr(regulations, "pages_of", lambda pdf: pages)
    monkeypatch.setattr(opendataloader, "converted", lambda pdfs: contextlib.nullcontext({}))
    monkeypatch.setattr(regulations, "layer_text", lambda pdf, converted=None: layers.append(pdf.name))  # (None: a scan)
    monkeypatch.setattr(regulations, "ocr_text", lambda pdf: read.append(pdf.name) or ("1. Общие положения " * 50, lighton.METHOD))
    return key, asked, layers, read


@pytest.mark.parametrize("ocr", [False, True])
def test_a_scan_too_long_for_ocr_is_put_aside_not_queued_and_no_run_reads_it(monkeypatch, tmp_path, docs_db, ocr):
    key, asked, layers, read = _one_scan(monkeypatch, tmp_path, LONG)
    note = lambda: notes.note(key)  # noqa: E731

    assert regulations.read_new(ocr=ocr) == []
    assert note()["ocr"] == "too long" and note()["pages"] == LONG and note()["queued_at"] and not read
    assert regulations.queued() == {}
    for again in (False, True):  # (neither kind of run downloads it, asks its text layer or reads it again)
        assert regulations.read_new(ocr=again) == []
    assert len(asked) == 1 and len(layers) == 1 and not read and note()["ocr"] == "too long"
    monkeypatch.setattr(regulations, "MAX_OCR_PAGES", LONG)  # (the limit raised: it is queued again, and read by a run with OCR, which downloads it again)
    assert regulations.queued() == {key: LONG}
    assert regulations.read_new() == [key] and read == [f"{key}.pdf"] and len(layers) == 1 and len(asked) == 2 and "ocr" not in note()


def test_a_long_scan_queued_before_the_long_ones_were_put_aside_is_marked_so(monkeypatch, tmp_path, docs_db):
    key, asked, layers, read = _one_scan(monkeypatch, tmp_path, LONG)
    notes.put_note(key, "", {"title": "Отчёт", "ocr": "queued", "pages": LONG, "queued_at": "2026-11-01T10:00:00+00:00"})
    assert regulations.read_new() == [] and not asked and not layers and not read
    assert notes.note(key) == {"title": "Отчёт", "ocr": "too long", "pages": LONG, "queued_at": "2026-11-01T10:00:00+00:00"}


def test_a_long_scan_changed_on_the_site_is_downloaded_and_looked_at_again(monkeypatch, tmp_path, docs_db):
    key, asked, layers, _ = _one_scan(monkeypatch, tmp_path, 3)  # (the new version: 3 pages)
    notes.put_note(key, "", {"ocr": "too long", "pages": LONG, "sha256": "old", "refetch": True})
    assert regulations.read_new(ocr=False) == [] and len(asked) == 1 and len(layers) == 1
    note = notes.note(key)
    assert note["ocr"] == "queued" and note["pages"] == 3 and "refetch" not in note


def _scan(key, pages, too_long=False, source="regs", title=None):
    return ocr_queue.Scan(source, key, title or f"Документ {key}", f"https://example.org/{key}.pdf", pages, too_long, "2026-11-04T01:00:00+00:00")


def test_the_queue_shows_the_scans_waiting_and_apart_the_long_ones(monkeypatch, capsys, docs_db):
    for key, note in {"short": {"ocr": "queued", "pages": 3, "ocr_failed": 2, "queued_at": "2026-11-01T10:00:00+00:00"},
                      "long": {"ocr": "too long", "pages": LONG}}.items():
        notes.put_note(key, "", note)
    monkeypatch.setattr(regulations, "all_docs", lambda: {key: {"title": f"Положение {key}", "url": f"https://u.example/{key}.pdf"}
                                                          for key in ("short", "long")})
    found = ocr_queue.scans()
    assert [(s.source, s.key, s.pages, s.too_long) for s in found] == [("regs", "short", 3, False), ("regs", "long", LONG, True)]
    assert found[0].failed == 2 and found[0].since.startswith("2026-11-01")
    ocr_queue.show(found)
    out = capsys.readouterr().out
    queue, apart = out.split("Too long for OCR")
    assert queue.startswith("OCR queue: 1 scan, 3 pages") and "short" in queue and "OCR failed 2x" in queue and "regs fetch" in queue
    assert "long" not in queue and "1 scan, 41 pages" in apart and "https://u.example/long.pdf" in apart


def test_the_message_names_the_new_scans_only_and_none_when_nothing_is_new():
    found = [_scan("a", 3), _scan("b", 4), _scan("c", LONG, too_long=True)]
    assert ocr_queue.message(found, set()) is None
    text = ocr_queue.message(found, {("regs", "b")})
    assert text.startswith("🖨 Очередь OCR выросла: 2 скана, 7 стр. (новые: 1 скан, 4 стр.)") and "Документ b" in text and "Документ a" not in text
    assert "📕" not in text and "catix-docs regs fetch" in text
    text = ocr_queue.message(found, {("regs", "c")})
    assert "🖨" not in text and text.startswith("📕 Слишком длинные для OCR сканы отложены, в очереди их нет: 1 скан") and "Документ c" in text
    many = [_scan(str(n), 1) for n in range(8)]
    text = ocr_queue.message(many, {("regs", s.key) for s in many})
    assert "8 сканов, 8 стр.:" in text and "новые" not in text and "• и ещё 3" in text


def test_the_admins_are_told_of_each_new_scan_once(monkeypatch):
    found, told, saved = [_scan("a", 3)], [], []
    monkeypatch.setattr(ocr_queue, "scans", lambda: list(found))
    monkeypatch.setattr(runner, "tell_admins", told.append)
    monkeypatch.setattr(runner, "save_state", lambda state: saved.append(json.loads(json.dumps(state))))
    state = {}
    runner.tell_ocr_queue(state)
    assert len(told) == 1 and "Документ a" in told[0]
    assert saved[-1]["ocr_told"] == [["regs", "a", False]]
    runner.tell_ocr_queue(state)  # (nothing new: nothing said)
    assert len(told) == 1
    found.append(_scan("b", 5))
    runner.tell_ocr_queue(state)
    assert len(told) == 2 and "Документ b" in told[1] and "Документ a" not in told[1] and "2 скана, 8 стр." in told[1]
    found[:] = [_scan("b", 5)]  # (a was read by OCR: it leaves, nobody is told)
    runner.tell_ocr_queue(state)
    assert len(told) == 2 and state["ocr_told"] == [["regs", "b", False]]
    found.append(_scan("a", 3))  # (it came back: told again)
    runner.tell_ocr_queue(state)
    assert len(told) == 3 and "Документ a" in told[2]
    found[:] = [_scan("a", 3), _scan("b", 5, too_long=True)]  # (b moved out of the queue: told as put aside)
    runner.tell_ocr_queue(state)
    assert len(told) == 4 and told[3].startswith("📕") and "Документ b" in told[3]


def test_a_scan_lighton_fails_on_stays_queued_and_tesseract_is_not_asked_while_its_server_answers(monkeypatch, tmp_path, docs_db):
    key = "site-hotel-1-rules"
    monkeypatch.setattr(regulations, "all_docs", lambda: {key: {"title": "Правила", "url": "https://hotel.innopolis.university/r.pdf",
                                                               "section": "site/hotel", "ext": "pdf"}})
    notes.put_note(key, "", {"ocr": "queued", "pages": 3, "queued_at": "2026-11-01T10:00:00+00:00"})
    monkeypatch.setattr(regulations, "PAUSE", 0)
    monkeypatch.setattr(regulations.httpx, "get", lambda u, **k: httpx.Response(200, content=b"%PDF-1.4 a scan", request=httpx.Request("GET", u)))
    monkeypatch.setattr(regulations, "pages_of", lambda pdf: 3)
    monkeypatch.setattr(opendataloader, "converted", lambda pdfs: contextlib.nullcontext({}))
    up = [True]
    monkeypatch.setattr(lighton, "text_of_pdf", lambda pdf, **kw: None)
    monkeypatch.setattr(lighton, "available", lambda: up[0])
    monkeypatch.setattr(tesseract, "available", lambda: False)
    monkeypatch.setattr(tesseract, "text_of_pdf", lambda pdf, **kw: pytest.fail("tesseract was asked while the server answers"))
    monkeypatch.setattr(regulations, "pdf_created", lambda pdf: None)  # (pdfinfo is not an OCR engine, but the guard below stops every subprocess)
    monkeypatch.setattr(regulations.subprocess, "run", lambda *a, **k: pytest.fail("another OCR engine was started"))
    note = lambda: notes.note(key)  # noqa: E731

    assert regulations.read_new() == []
    assert note()["ocr"] == "queued" and note()["ocr_failed"] == 1 and note()["queued_at"] == "2026-11-01T10:00:00+00:00"
    up[0] = False  # (the server went away: not the scan's fault, not counted)
    assert regulations.read_new() == [] and note()["ocr_failed"] == 1
    up[0] = True
    for failed in range(2, 6):
        assert regulations.read_new() == []
        assert note()["ocr"] == "queued" and note()["ocr_failed"] == failed
        assert not notes.has_text(key)
    monkeypatch.setattr(lighton, "text_of_pdf", lambda pdf, **kw: "1. Общие положения " * 50)
    assert regulations.read_new() == [key]
    assert "ocr" not in note() and note()["method"] == lighton.METHOD


@pytest.mark.parametrize("lighton_up", [True, False])
@pytest.mark.parametrize("text", [None, "", "  \n"])
def test_an_unreadable_scan_is_not_successful_text(monkeypatch, tmp_path, text, lighton_up):
    engine = lighton if lighton_up else tesseract  # (the engine that is up reads the scan)
    monkeypatch.setattr(engine, "text_of_pdf", lambda pdf, **kw: text)
    monkeypatch.setattr(lighton, "available", lambda: lighton_up)
    monkeypatch.setattr(tesseract, "available", lambda: True)
    with pytest.raises(regulations.NotRead):
        regulations.ocr_text(tmp_path / "scan.pdf")


def test_tesseract_reads_a_scan_while_the_lighton_server_is_away(monkeypatch, tmp_path):
    monkeypatch.setattr(lighton, "available", lambda: False)
    monkeypatch.setattr(lighton, "text_of_pdf", lambda pdf, **kw: pytest.fail("the away server was asked"))
    monkeypatch.setattr(tesseract, "available", lambda: True)
    monkeypatch.setattr(tesseract, "text_of_pdf", lambda pdf, **kw: "1. Общие положения " * 50)
    assert regulations.ocr_text(tmp_path / "scan.pdf") == ("1. Общие положения " * 50, tesseract.METHOD)


def test_a_scan_lighton_drops_mid_read_is_read_by_tesseract(monkeypatch, tmp_path):
    answers = iter([True, False])
    monkeypatch.setattr(lighton, "available", lambda: next(answers))
    monkeypatch.setattr(lighton, "text_of_pdf", lambda pdf, **kw: None)
    monkeypatch.setattr(tesseract, "available", lambda: True)
    monkeypatch.setattr(tesseract, "text_of_pdf", lambda pdf, **kw: "1. Общие положения " * 50)
    assert regulations.ocr_text(tmp_path / "scan.pdf")[1] == tesseract.METHOD


def test_the_scan_is_not_kept_after_a_run_and_a_run_without_ocr_does_not_download_it(monkeypatch, tmp_path, docs_db):
    key, asked, layers, read = _one_scan(monkeypatch, tmp_path, 3)
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    assert regulations.read_new(ocr=False) == [] and len(asked) == 1
    assert regulations.read_new(ocr=False) == [] and len(asked) == 1  # (waits for a run with OCR: not downloaded)
    assert notes.note(key)["ocr"] == "queued" and not notes.has_text(key)
    assert not list(tmp_path.iterdir())  # (the original lived in the temporary folder of the run)
    assert regulations.read_new() == [key] and len(asked) == 2 and read == [f"{key}.pdf"]  # (a run with OCR downloads it again)
    assert notes.text(key) and not list(tmp_path.iterdir())


def test_a_document_forced_by_a_person_is_queued_for_the_loop_and_read_with_no_limit(monkeypatch, tmp_path, docs_db):
    key, asked, layers, read = _one_scan(monkeypatch, tmp_path, LONG)
    url = "https://hotel.innopolis.university/upload/report.pdf"
    note = lambda: notes.note(key)  # noqa: E731
    link_document("hotel", url, "Отчёт", key=key)
    docs_db.execute("UPDATE crawl_urls SET next_at = now() + interval '3 days', priority = 2 WHERE doc_key = %s", (key,))  # (read lately: it waits)
    assert regulations.read_new() == [] and note()["ocr"] == "too long"  # (put aside: no run reads it)

    regulations.force(key)  # (queue only: this process reads nothing; the crawl's row of the document is asked for at once)
    assert len(asked) == 1 and regulations.queued() == {key: LONG}
    row = docs_db.execute("SELECT priority, next_at <= now() AS due FROM crawl_urls WHERE doc_key = %s", (key,)).fetchone()
    assert row["priority"] == 0 and row["due"]
    monkeypatch.setattr(regulations, "OCR_BUDGET", 1)  # (the OCR thread's run: neither the budget nor the page limit holds for it)
    assert regulations.read_new() == [key] and read == [f"{key}.pdf"] and len(asked) == 2
    assert "force" not in note() and "ocr" not in note()  # (read: it is an ordinary document again)
