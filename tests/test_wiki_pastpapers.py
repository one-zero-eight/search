"""Past exam papers from the students' Notion database (sources/pastpapers.py): the rows Notion's API gives, the page of a subject."""

import contextlib
from types import SimpleNamespace

import httpx
import pytest

from catix.wiki.sources import chandra, pastpapers, regulations

SCHEMA = {"GXY<": {"name": "Subject", "type": "select"}, "Isak": {"name": "File", "type": "file"}, "M_lr": {"name": "Year", "type": "select"},
          "title": {"name": "Exam", "type": "title"}}


def _row(row_id, subject, year, exam, files, alive=True):
    props = {"GXY<": [[subject]], "M_lr": [[year]], "title": [[exam]], "Isak": [[n, [["a", u]]] for n, u in files]}
    return {"spaceId": "s", "value": {"value": {"id": row_id, "parent_table": "collection", "alive": alive, "properties": props}}}


def test_the_rows_come_with_their_subject_year_exam_and_files(monkeypatch):
    answers = {
        "loadCachedPageChunkV2": {"recordMap": {
            "block": {pastpapers.PAGE: {"value": {"value": {"id": pastpapers.PAGE, "space_id": "s", "view_ids": ["all", "first-term"]}}}},
            "collection": {"c": {"value": {"value": {"id": "c", "schema": SCHEMA}}}}}},
        "queryCollection": {"recordMap": {"block": {
            "r1": _row("r1", "AGLA 1", "2022", "Test 1", [("AGLA_1_Test_1_2022.pdf", "https://s3/x/AGLA_1_Test_1_2022.pdf")]),
            "r2": _row("r2", "DSA", "2024", "Final", [], alive=False),
            pastpapers.PAGE: {"value": {"value": {"id": pastpapers.PAGE, "type": "collection_view_page"}}}}}},
    }
    asked = []

    def post(client, method, body):
        asked.append((method, body))
        return answers[method]

    monkeypatch.setattr(pastpapers, "_post", post)
    with httpx.Client() as client:
        rows = pastpapers.rows(client)
    assert rows == [{"id": "r1", "space": "s", "subject": "AGLA 1", "year": "2022", "exam": "Test 1",
                     "files": [("AGLA_1_Test_1_2022.pdf", "https://s3/x/AGLA_1_Test_1_2022.pdf")]}]
    assert asked[1][1]["collectionView"]["id"] == "all"  # the first view: every row, not one term's


def test_a_subject_is_one_page_newest_paper_first(tmp_path, monkeypatch):
    monkeypatch.setattr(pastpapers, "ROOT", tmp_path / "raw")
    monkeypatch.setattr(pastpapers, "INDEX", tmp_path / "raw" / "index.json")
    monkeypatch.setattr(pastpapers, "DOCS", tmp_path / "wiki" / "raw")
    pastpapers.save({
        "a": {"subject": "AGLA 1", "year": "2021", "exam": "Test 1", "files": {"k1": {"name": "t1.pdf", "sha256": "0", "method": "text layer"}}},
        "b": {"subject": "AGLA 1", "year": "2024", "exam": "Final", "files": {"k2": {"name": "f.pdf", "skipped": "nothing readable"}}},
    })
    (tmp_path / "raw" / "k1.txt").write_text("# 1. Find det(A)\nwhere A is 2x2", encoding="utf-8")
    pastpapers.compile_all()
    page = (tmp_path / "wiki" / "raw" / "past-papers" / "agla-1.md").read_text(encoding="utf-8")
    assert 'title: "Past exam papers: AGLA 1"' in page and "source_kind: community" in page
    assert page.index("## 2024: Final") < page.index("## 2021: Test 1")
    assert "\\# 1. Find det(A)" in page  # a line of the paper is not a heading of the page
    assert f"({pastpapers.SITE}/a)" in page  # the row in Notion: the file's own link expires


def test_paper_scans_use_only_chandra(monkeypatch, tmp_path):
    monkeypatch.setattr(regulations, "pages_of", lambda pdf: 2)

    def text_layer(args, **kwargs):
        assert args[0] == "pdftotext", "another OCR engine was started"
        return SimpleNamespace(stdout="")

    monkeypatch.setattr(pastpapers.subprocess, "run", text_layer)
    monkeypatch.setattr(chandra, "text_of_pdf", lambda pdf, keep=None: "Find the determinant")
    assert pastpapers.read_pdf(tmp_path / "exam.pdf") == ("Find the determinant", chandra.METHOD)
    monkeypatch.setattr(chandra, "text_of_pdf", lambda pdf, keep=None: None)
    monkeypatch.setattr(chandra, "available", lambda: False)
    with pytest.raises(regulations.NotRead):
        pastpapers.read_pdf(tmp_path / "exam.pdf")


@pytest.mark.parametrize("pages,budget", [(0, 0), (2, 0), (3, 2), (21, 120)])
def test_paper_scans_respect_disabled_ocr_and_page_limits(monkeypatch, tmp_path, pages, budget):
    monkeypatch.setattr(regulations, "pages_of", lambda pdf: pages)
    monkeypatch.setattr(pastpapers.subprocess, "run", lambda *a, **kw: SimpleNamespace(stdout=""))
    monkeypatch.setattr(chandra, "text_of_pdf", lambda *a, **kw: pytest.fail("OCR ran outside its budget"))
    assert pastpapers.read_pdf(tmp_path / "exam.pdf", ocr_left=budget) == (None, "scan queued for OCR")


def test_paper_queue_survives_unavailable_ocr_without_redownloading(monkeypatch, tmp_path):
    monkeypatch.setattr(pastpapers, "ROOT", tmp_path)
    monkeypatch.setattr(pastpapers, "INDEX", tmp_path / "index.json")
    monkeypatch.setattr(pastpapers, "PAUSE", 0)
    url = "https://files.example/exam.pdf"
    key = pastpapers.file_key(url)
    monkeypatch.setattr(pastpapers, "rows", lambda client: [{"id": "r1", "space": "s", "subject": "Math", "year": "2026",
                                                           "exam": "Final", "files": [("exam.pdf", url)]}])
    requests, layers, attempts = [], [], []
    client = httpx.Client(transport=httpx.MockTransport(lambda req: requests.append(req.url) or httpx.Response(200, content=b"%PDF scan")))
    monkeypatch.setattr(pastpapers.httpx, "Client", lambda **kw: contextlib.nullcontext(client))
    monkeypatch.setattr(regulations, "pages_of", lambda pdf: 2)
    monkeypatch.setattr(pastpapers.subprocess, "run", lambda args, **kw: layers.append(args[0]) or SimpleNamespace(stdout=""))

    def unavailable(pdf, keep=None):
        attempts.append(pdf)
        return None

    monkeypatch.setattr(chandra, "text_of_pdf", unavailable)
    monkeypatch.setattr(chandra, "available", lambda: False)
    try:
        assert pastpapers.fetch(ocr=False) == 1
        assert pastpapers.load()["r1"]["files"][key]["ocr"] == "queued"
        assert not attempts and layers == ["pdftotext"]
        assert pastpapers.fetch(ocr=False) == 0
        assert pastpapers.fetch() == 0  # unavailable: still queued, not permanently skipped
        assert len(attempts) == 1 and len(requests) == 1 and layers == ["pdftotext"]
        assert pastpapers.load()["r1"]["files"][key]["ocr"] == "queued"
        monkeypatch.setattr(chandra, "text_of_pdf", lambda pdf, keep=None: "Find the determinant")
        assert pastpapers.fetch() == 1
        note = pastpapers.load()["r1"]["files"][key]
        assert "ocr" not in note and note["method"] == chandra.METHOD
        assert (tmp_path / f"{key}.txt").read_text() == "Find the determinant"
        assert pastpapers.fetch() == 0 and len(requests) == 1
    finally:
        client.close()
