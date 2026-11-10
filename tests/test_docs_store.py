"""The store and the files of the sources in a real Postgres: temporary tables, the permanent ones are not touched."""

import os
from contextlib import contextmanager

import pytest

from catix.db import pg
from catix.docs import files, store
from catix.docs.store import Document

URL = os.environ.get("DOCS_TEST_DATABASE_URL")

SCHEMA = """
CREATE TEMP TABLE documents (path text PRIMARY KEY, sha text NOT NULL, title text NOT NULL, type text NOT NULL, trust text NOT NULL,
    audience text[] NOT NULL DEFAULT '{}', resource text, status text, review text, source_warning text, stale_after date, issued date,
    indexed_at timestamptz NOT NULL DEFAULT now(), body text NOT NULL DEFAULT '', meta jsonb NOT NULL DEFAULT '{}');
CREATE TEMP TABLE document_chunks (id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    path text NOT NULL REFERENCES documents (path) ON DELETE CASCADE ON UPDATE CASCADE, trust text NOT NULL, seq int NOT NULL,
    heading text NOT NULL, clause text NOT NULL, sha text NOT NULL, text text NOT NULL, search_text text NOT NULL,
    cites jsonb NOT NULL DEFAULT '[]', copy_of bigint REFERENCES document_chunks (id) ON DELETE SET NULL);
CREATE TEMP TABLE document_embedding_queue (chunk_id bigint PRIMARY KEY REFERENCES document_chunks (id) ON DELETE CASCADE, queued_at timestamptz NOT NULL DEFAULT now());
CREATE TEMP TABLE document_chunk_embeddings (chunk_id bigint PRIMARY KEY REFERENCES document_chunks (id) ON DELETE CASCADE);
CREATE TEMP TABLE docs_meta (key text PRIMARY KEY, value text NOT NULL);
CREATE TEMP TABLE source_files (path text PRIMARY KEY, data jsonb, text text, updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK ((data IS NULL) <> (text IS NULL)));
"""


@pytest.fixture
def conn(monkeypatch):
    if not URL:
        pytest.skip("requires a disposable DOCS_TEST_DATABASE_URL")
    import psycopg
    from psycopg.rows import dict_row

    connection = psycopg.connect(URL, row_factory=dict_row, autocommit=True)
    connection.execute(SCHEMA)

    @contextmanager
    def same():
        yield connection

    monkeypatch.setattr(pg, "connection", same)
    monkeypatch.setattr(store.settings, "embeddings_model", "test-model")
    monkeypatch.setattr(files, "BACKEND", files.PostgresFiles())
    yield connection
    connection.close()


def doc(path: str, *paragraphs: str) -> Document:
    body = "# Title\n\n## Part\n\n" + "\n\n".join(paragraphs) + "\n"
    return Document(path, {"title": "Title", "type": "regulation"}, body)


def ids(conn, path: str) -> dict[str, int]:
    return {r["text"]: r["id"] for r in conn.execute("SELECT id, text FROM document_chunks WHERE path = %s", (path,)).fetchall()}


def test_a_second_sync_of_the_same_documents_changes_nothing(conn):
    docs = [doc("regulations/a", "First paragraph.")]
    assert store.sync("regulations/", docs)["pages new"] == 1
    assert store.sync("regulations/", docs) == {"pages unchanged": 1}


def test_a_changed_paragraph_replaces_only_its_own_piece(conn):
    long = "x" * 1100
    store.sync("regulations/", [doc("regulations/a", "Stays the same. " + long, "Will change. " + long)])
    before = ids(conn, "regulations/a")
    counts = store.sync("regulations/", [doc("regulations/a", "Stays the same. " + long, "Changed now. " + long)])
    after = ids(conn, "regulations/a")
    assert counts["pages changed"] == 1 and counts["pieces new"] == 1 and counts["pieces deleted"] == 1
    assert after["Stays the same. " + long] == before["Stays the same. " + long]


def test_a_document_that_is_gone_is_deleted_unless_its_prefix_is_kept(conn):
    store.sync("sites/", [doc("sites/a/x", "One."), doc("sites/b/y", "Two.")])
    store.sync("sites/", [], keep=("sites/b/",))
    assert [r["path"] for r in conn.execute("SELECT path FROM documents").fetchall()] == ["sites/b/y"]


def test_other_prefixes_are_not_touched_and_foreign_paths_are_refused(conn):
    store.sync("regulations/", [doc("regulations/a", "One.")])
    store.sync("sites/", [])
    assert conn.execute("SELECT count(*) AS n FROM documents").fetchone()["n"] == 1
    with pytest.raises(ValueError, match="sites/x"):
        store.sync("regulations/", [doc("sites/x", "Two.")])


def test_files_keep_json_and_text_under_one_path(conn):
    files.write_json("sites/a/index.json", {"n": 1})
    assert files.read_json("sites/a/index.json") == {"n": 1} and files.read_text("sites/a/index.json") is None
    files.write_text("sites/a/index.json", "now text")
    assert files.read_json("sites/a/index.json") is None and files.read_text("sites/a/index.json") == "now text"
    files.write_text("sites/a/p.md", "page")
    files.write_json("sites/b/index.json", [])
    assert files.list("sites/a/") == ["sites/a/index.json", "sites/a/p.md"]
    assert files.list("sites/a/", ".md") == ["sites/a/p.md"]
    assert files.delete_prefix("sites/a/") == 2 and files.exists("sites/b/index.json")
