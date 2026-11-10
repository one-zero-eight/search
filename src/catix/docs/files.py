"""What the sources kept as files in raw/, kept in Postgres (the table source_files): the state of a crawl (JSON), the text read
from a document, the cache of the pages of a site. The originals (PDF, Word, archives, pictures) are not kept anywhere: a source
downloads one into a temporary folder, reads it and deletes it.

A path is a string without a leading '/', with the file names the sources used below raw/: 'sites/hotel/index.json',
'regulations/x.txt'. A path holds either JSON or text.
"""

import json
from typing import Protocol

from catix.db import pg


class Files(Protocol):
    def read_json(self, path: str) -> dict | list | None: ...
    def write_json(self, path: str, data: dict | list) -> None: ...
    def read_text(self, path: str) -> str | None: ...
    def write_text(self, path: str, text: str) -> None: ...
    def exists(self, path: str) -> bool: ...
    def delete(self, path: str) -> None: ...
    def delete_prefix(self, prefix: str) -> int: ...
    def list(self, prefix: str, suffix: str = "") -> list[str]: ...  # sorted paths


class PostgresFiles:
    """source_files through pg.connection(); one statement per call."""

    def read_json(self, path: str) -> dict | list | None:
        with pg.connection() as conn:
            row = conn.execute("SELECT data FROM source_files WHERE path = %s", (path,)).fetchone()
        return row["data"] if row else None

    def write_json(self, path: str, data: dict | list) -> None:
        with pg.connection() as conn:
            conn.execute(
                """INSERT INTO source_files (path, data, text, updated_at) VALUES (%s, %s::jsonb, NULL, now())
                   ON CONFLICT (path) DO UPDATE SET data = excluded.data, text = NULL, updated_at = now()""",
                (path, json.dumps(data, ensure_ascii=False)),
            )

    def read_text(self, path: str) -> str | None:
        with pg.connection() as conn:
            row = conn.execute("SELECT text FROM source_files WHERE path = %s", (path,)).fetchone()
        return row["text"] if row else None

    def write_text(self, path: str, text: str) -> None:
        with pg.connection() as conn:
            conn.execute(
                """INSERT INTO source_files (path, data, text, updated_at) VALUES (%s, NULL, %s, now())
                   ON CONFLICT (path) DO UPDATE SET text = excluded.text, data = NULL, updated_at = now()""",
                (path, text),
            )

    def exists(self, path: str) -> bool:
        with pg.connection() as conn:
            return conn.execute("SELECT 1 FROM source_files WHERE path = %s", (path,)).fetchone() is not None

    def delete(self, path: str) -> None:
        with pg.connection() as conn:
            conn.execute("DELETE FROM source_files WHERE path = %s", (path,))

    def delete_prefix(self, prefix: str) -> int:
        with pg.connection() as conn:
            return conn.execute("DELETE FROM source_files WHERE starts_with(path, %s)", (prefix,)).rowcount

    def list(self, prefix: str, suffix: str = "") -> list[str]:
        with pg.connection() as conn:
            rows = conn.execute(
                "SELECT path FROM source_files WHERE starts_with(path, %s) AND (%s = '' OR right(path, length(%s)) = %s) ORDER BY path",
                (prefix, suffix, suffix, suffix),
            ).fetchall()
        return [r["path"] for r in rows]


BACKEND: Files = PostgresFiles()


def read_json(path: str) -> dict | list | None:
    return BACKEND.read_json(path)


def write_json(path: str, data: dict | list) -> None:
    BACKEND.write_json(path, data)


def read_text(path: str) -> str | None:
    return BACKEND.read_text(path)


def write_text(path: str, text: str) -> None:
    BACKEND.write_text(path, text)


def exists(path: str) -> bool:
    return BACKEND.exists(path)


def delete(path: str) -> None:
    BACKEND.delete(path)


def delete_prefix(prefix: str) -> int:
    return BACKEND.delete_prefix(prefix)


def list(prefix: str, suffix: str = "") -> list[str]:  # noqa: A001 - the same name as the protocol's
    return BACKEND.list(prefix, suffix)
