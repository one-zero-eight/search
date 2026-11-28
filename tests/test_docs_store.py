"""The store in a real Postgres (the docs_db fixture): temporary tables, the permanent ones are not touched."""

import pytest

from catix.docs import store
from catix.docs.store import Document

def doc(path: str, *paragraphs: str) -> Document:
    body = "# Title\n\n## Part\n\n" + "\n\n".join(paragraphs) + "\n"
    return Document(path, {"title": "Title", "type": "regulation"}, body)


def ids(docs_db, path: str) -> dict[str, int]:
    return {r["text"]: r["id"] for r in docs_db.execute("SELECT id, text FROM document_chunks WHERE path = %s", (path,)).fetchall()}


def test_a_second_sync_of_the_same_documents_changes_nothing(docs_db):
    docs = [doc("regulations/a", "First paragraph.")]
    assert store.sync("regulations/", docs)["pages new"] == 1
    assert store.sync("regulations/", docs) == {"pages unchanged": 1}


def test_a_changed_paragraph_replaces_only_its_own_piece(docs_db):
    long = "x" * 1100
    store.sync("regulations/", [doc("regulations/a", "Stays the same. " + long, "Will change. " + long)])
    before = ids(docs_db, "regulations/a")
    counts = store.sync("regulations/", [doc("regulations/a", "Stays the same. " + long, "Changed now. " + long)])
    after = ids(docs_db, "regulations/a")
    assert counts["pages changed"] == 1 and counts["pieces new"] == 1 and counts["pieces deleted"] == 1
    assert after["Stays the same. " + long] == before["Stays the same. " + long]


def test_a_document_that_is_gone_is_deleted_unless_its_prefix_is_kept(docs_db):
    store.sync("sites/", [doc("sites/a/x", "One."), doc("sites/b/y", "Two.")])
    store.sync("sites/", [], keep=("sites/b/",))
    assert [r["path"] for r in docs_db.execute("SELECT path FROM documents").fetchall()] == ["sites/b/y"]


def test_other_prefixes_are_not_touched_and_foreign_paths_are_refused(docs_db):
    store.sync("regulations/", [doc("regulations/a", "One.")])
    store.sync("sites/", [])
    assert docs_db.execute("SELECT count(*) AS n FROM documents").fetchone()["n"] == 1
    with pytest.raises(ValueError, match="sites/x"):
        store.sync("regulations/", [doc("sites/x", "Two.")])
