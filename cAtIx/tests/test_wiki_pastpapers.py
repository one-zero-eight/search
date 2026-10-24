"""Past exam papers from the students' Notion database (sources/pastpapers.py): the rows Notion's API gives, the page of a subject."""

import httpx

from catix.wiki.sources import pastpapers

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
    monkeypatch.setattr(pastpapers, "BUNDLE", tmp_path / "wiki")
    pastpapers.save({
        "a": {"subject": "AGLA 1", "year": "2021", "exam": "Test 1", "files": {"k1": {"name": "t1.pdf", "sha256": "0", "method": "text layer"}}},
        "b": {"subject": "AGLA 1", "year": "2024", "exam": "Final", "files": {"k2": {"name": "f.pdf", "skipped": "nothing readable"}}},
    })
    (tmp_path / "raw" / "k1.txt").write_text("# 1. Find det(A)\nwhere A is 2x2", encoding="utf-8")
    pastpapers.compile_all()
    page = (tmp_path / "wiki" / "past-papers" / "agla-1.md").read_text(encoding="utf-8")
    assert 'title: "Past exam papers: AGLA 1"' in page and "source_kind: community" in page
    assert page.index("## 2024: Final") < page.index("## 2021: Test 1")
    assert "\\# 1. Find det(A)" in page  # a line of the paper is not a heading of the page
    assert f"({pastpapers.SITE}/a)" in page  # the row in Notion: the file's own link expires
