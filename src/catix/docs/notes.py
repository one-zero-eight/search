"""The notes and the texts of the documents read (table document_files): what regulations._fetch_once knows of a file, and the text
read from it. A document is a key and a revision: '' for a file at its own URL, the content sha for a member of an archive or for
an archive URL that served a PDF (the revisions of one key coexist until the new one is read).

A note is a dict of the columns in COLUMNS that are set: the times are ISO strings (UTC, seconds), a flag that is false and
an empty `remote` are left out, so `note.get("refetch")` and `"skipped" in note` mean what they did when the notes were files.
"""

from datetime import datetime, timezone

from psycopg.types.json import Jsonb

from catix.db import pg

COLUMNS = ("url", "title", "section", "context", "sha256", "method", "chars", "tables", "pdf_created", "remote", "ocr", "pages",
           "queued_at", "ocr_failed", "skipped", "failed", "tried_at", "checked_at", "fetched_at", "refetch", "force")
TIMES = frozenset({"queued_at", "tried_at", "checked_at", "fetched_at"})
FLAGS = frozenset({"refetch", "force"})
_LIST = ", ".join(COLUMNS)


def _note(row: dict) -> dict:
    out = {}
    for column in COLUMNS:
        value = row[column]
        if value is None or (column in FLAGS and not value) or (column == "remote" and not value):
            continue
        out[column] = value.astimezone(timezone.utc).isoformat(timespec="seconds") if column in TIMES else value
    return out


def note(key: str, revision: str = "") -> dict:
    """The note of a document; {} when there is none."""
    with pg.connection() as conn:
        row = conn.execute(f"SELECT {_LIST} FROM document_files WHERE key = %s AND revision = %s", (key, revision)).fetchone()
    return _note(row) if row else {}


def put_note(key: str, revision: str, note: dict) -> None:
    """The note of a document, whole (what was there is replaced; the text is kept). ValueError for a key that is no column."""
    for column in note:
        if column not in COLUMNS:
            raise ValueError(column)
    values = []
    for column in COLUMNS:
        value = note.get(column)
        if value is False and column not in FLAGS:
            value = None  # (the old notes wrote `"failed": false` to say it was cleared)
        if column in FLAGS:
            value = bool(value)
        elif column == "remote":
            value = Jsonb(value or {})
        elif column in TIMES and value is not None:
            value = datetime.fromisoformat(value) if isinstance(value, str) else value
        values.append(value)
    marks = ", ".join(["%s"] * len(COLUMNS))
    sets = ", ".join(f"{c} = excluded.{c}" for c in COLUMNS)
    with pg.connection() as conn:
        conn.execute(f"INSERT INTO document_files (key, revision, {_LIST}) VALUES (%s, %s, {marks}) ON CONFLICT (key, revision) DO UPDATE SET {sets}",
                     (key, revision, *values))


def text(key: str, revision: str = "") -> str | None:
    with pg.connection() as conn:
        row = conn.execute("SELECT text FROM document_files WHERE key = %s AND revision = %s", (key, revision)).fetchone()
    return row["text"] if row else None


def put_text(key: str, revision: str, text: str) -> None:
    with pg.connection() as conn:
        conn.execute("INSERT INTO document_files (key, revision, text) VALUES (%s, %s, %s) ON CONFLICT (key, revision) DO UPDATE SET text = excluded.text",
                     (key, revision, text))


def has_text(key: str, revision: str = "") -> bool:
    with pg.connection() as conn:
        return conn.execute("SELECT 1 FROM document_files WHERE key = %s AND revision = %s AND text IS NOT NULL", (key, revision)).fetchone() is not None


def scans() -> list[tuple[str, str, dict]]:
    """(key, revision, note) of every note that says its scan is queued for OCR or put aside as too long."""
    with pg.connection() as conn:
        rows = conn.execute(f"SELECT key, revision, {_LIST} FROM document_files WHERE ocr IS NOT NULL ORDER BY key, revision").fetchall()
    return [(r["key"], r["revision"], _note(r)) for r in rows]


def delete_except(current: set[tuple[str, str]]) -> int:
    """Delete the notes and texts of every (key, revision) that is not in `current`; how many."""
    with pg.connection() as conn:
        have = [(r["key"], r["revision"]) for r in conn.execute("SELECT key, revision FROM document_files").fetchall()]
        gone = [pair for pair in have if pair not in current]
        for i in range(0, len(gone), 500):
            part = gone[i:i + 500]
            conn.execute("DELETE FROM document_files WHERE (key, revision) IN (SELECT * FROM unnest(%s::text[], %s::text[]))",
                         ([k for k, _ in part], [r for _, r in part]))
    return len(gone)
