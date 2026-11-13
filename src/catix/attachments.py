"""Private, chat-scoped uploads. Blocking functions; API callers use a worker thread.

Originals and extracted pages live only in Postgres, never in the public wiki/index.
Page numbers are one-based. No inference, OCR, URLs or caller-selected disk paths.
"""
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import unicodedata
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

from psycopg import Connection, Error as DatabaseError
from psycopg.errors import ForeignKeyViolation
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from catix.db import pg

MAX_BYTES = 10 * 1024 * 1024
MAX_IDS = 3
MAX_OWNER_BYTES = 100 * 1024 * 1024
MAX_PENDING = 20
MAX_TOTAL = 50
WORKER_TIMEOUT = 45
_workers = threading.BoundedSemaphore(2)


class AttachmentInfo(BaseModel):
    id: str
    filename: str
    media_type: str
    size_bytes: int = Field(gt=0, le=MAX_BYTES)
    pages: int = Field(gt=0, le=20)


class AttachmentError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _worker(data: bytes, suffix: str, page: int = 0) -> bytes:
    if not _workers.acquire(blocking=False):
        raise AttachmentError(503, "Attachment processing is busy; try again.")
    process = None
    work = None
    try:
        work = tempfile.TemporaryDirectory(prefix="catix-attachment-")
        # Do not inherit account tokens, database credentials or model endpoints.
        env = {k: os.environ[k] for k in ("PATH", "LANG") if k in os.environ}
        env["TMPDIR"] = work.name
        env["WIKI_ROOT"] = work.name  # text_of imports wiki modules; never the real corpus.
        env["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent)
        process = subprocess.Popen(
            [sys.executable, str(Path(__file__).with_name("attachment_reader.py")), suffix, str(page)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env=env, cwd=work.name, start_new_session=True,
        )
        output, _ = process.communicate(data, timeout=WORKER_TIMEOUT)
        if process.returncode:
            raise AttachmentError(422, "The file could not be safely decoded.")
        return output
    except subprocess.TimeoutExpired:
        raise AttachmentError(422, "Attachment processing timed out.") from None
    except OSError:
        raise AttachmentError(503, "Attachment processing is unavailable.") from None
    finally:
        if process is not None:
            # Includes the JVM/poppler and descendants, on success, timeout or cancellation.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
        if work is not None:
            work.cleanup()
        _workers.release()


@contextmanager
def _connection() -> Iterator[Connection[dict[str, Any]]]:
    try:
        with pg.connection() as conn:
            yield cast(Connection[dict[str, Any]], conn)  # pg's pool uses dict_row
    except ForeignKeyViolation:
        raise AttachmentError(404, "Chat or attachment no longer exists.") from None
    except DatabaseError:
        # SQL diagnostics can include a failing row (including original/extracted data).
        raise AttachmentError(503, "Attachment storage is unavailable; try again.") from None


def _lock(conn: Connection[dict[str, Any]], owner: str) -> None:
    # Hash collisions only serialize unrelated owners; they never grant access.
    conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", ("attachments:" + owner,))
    conn.execute("""DELETE FROM api_attachments WHERE owner = %s AND chat_id IS NULL
                    AND created_at <= now() - interval '24 hours'""", (owner,))


def _validate_upload(filename: str, data: bytes) -> str:
    if len(data) > MAX_BYTES:
        raise AttachmentError(413, "Each attachment must be at most 10 MiB.")
    if (not filename or len(filename) > 200 or any(unicodedata.category(c).startswith("C") for c in filename)
            or len(filename.encode("utf-8")) > 255 or filename != filename.strip()
            or any(c in filename for c in ("/", "\\", ":"))):
        raise AttachmentError(422, "Use a filename of at most 200 characters without paths or control characters.")
    suffix = Path(filename).suffix.lower()
    if suffix not in {".txt", ".pdf", ".png", ".jpg", ".jpeg", ".webp"}:
        raise AttachmentError(415, "Only PDF, UTF-8 TXT, PNG, JPEG and WebP files are supported.")
    if not data:
        raise AttachmentError(422, "The attachment is empty.")
    if suffix == ".txt":
        # A text extension must not smuggle markup, scripts or a binary container.
        sample = data[:8192].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
        if (sample.startswith((b"#!", b"mz", b"\x7felf", b"pk\x03\x04", b"rar!", b"7z\xbc\xaf", b"%pdf-"))
                or re.search(rb"<\s*(?:!doctype|html|head|body|script|svg|\?xml)\b", sample)):
            raise AttachmentError(415, "The file is not plain text.")
    return suffix


def create(owner: str, filename: str, data: bytes) -> AttachmentInfo:
    suffix = _validate_upload(filename, data)
    parsed = json.loads(_worker(data, suffix))
    info = AttachmentInfo(id=uuid.uuid4().hex, filename=filename, media_type=parsed["media_type"],
                          size_bytes=len(data), pages=len(parsed["pages"]))
    with _connection() as conn:
        _lock(conn, owner)
        quota = conn.execute("""SELECT count(*) AS total,
                               count(*) FILTER (WHERE chat_id IS NULL) AS pending,
                               coalesce(sum(size_bytes), 0) AS bytes FROM api_attachments WHERE owner = %s""",
                             (owner,)).fetchone()
        assert quota is not None  # aggregate SELECT always returns a row
        if quota["total"] >= MAX_TOTAL or quota["pending"] >= MAX_PENDING or quota["bytes"] + len(data) > MAX_OWNER_BYTES:
            raise AttachmentError(413, "Attachment storage quota exceeded. Remove pending uploads or old chats.")
        conn.execute(
            """INSERT INTO api_attachments (id, owner, filename, media_type, size_bytes, pages, data, page_text)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (info.id, owner, info.filename, info.media_type, info.size_bytes, info.pages, data, Jsonb(parsed["pages"])),
        )
    return info


def _id(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{32}", value):
        raise AttachmentError(404, "Attachment not found.")


def _chat(conn, owner: str, chat_id: str) -> None:
    if conn.execute("SELECT chat_id FROM api_chats WHERE chat_id = %s AND innohassle_id = %s FOR UPDATE",
                    (chat_id, owner)).fetchone() is None:
        raise AttachmentError(404, "Chat not found.")


def _info(row: dict) -> AttachmentInfo:
    return AttachmentInfo(**{key: row[key] for key in AttachmentInfo.model_fields})


def recover_chat(owner: str, ids: list[str]) -> str | None:
    """Validate every upload and recover its single owned chat, never moving bound files."""
    if len(ids) > MAX_IDS:
        raise AttachmentError(422, "At most three attachments may be sent in one message.")
    for value in ids:
        _id(value)
    if len(set(ids)) != len(ids):
        raise AttachmentError(422, "Duplicate attachment IDs are not allowed.")
    with _connection() as conn:
        _lock(conn, owner)
        rows = conn.execute("""SELECT id, chat_id FROM api_attachments
                               WHERE owner = %s AND id = ANY(%s)
                               AND (chat_id IS NOT NULL OR created_at > now() - interval '24 hours')""",
                            (owner, ids)).fetchall()
        if {row["id"] for row in rows} != set(ids):
            raise AttachmentError(404, "Attachment not found.")
        chats = {row["chat_id"] for row in rows if row["chat_id"] is not None}
        if len(chats) > 1:
            raise AttachmentError(409, "An attachment cannot be moved to another chat.")
        chat_id = next(iter(chats), None)
        if chat_id is not None:
            _chat(conn, owner, chat_id)
        return chat_id


def bind(owner: str, chat_id: str, ids: list[str]) -> list[AttachmentInfo]:
    """Atomically bind all IDs, preserving input order. Existing same-chat IDs are allowed."""
    if len(ids) > MAX_IDS:
        raise AttachmentError(422, "At most three attachments may be sent in one message.")
    for value in ids:
        _id(value)
    if len(set(ids)) != len(ids):
        raise AttachmentError(422, "Duplicate attachment IDs are not allowed.")
    with _connection() as conn:
        _lock(conn, owner)
        _chat(conn, owner, chat_id)  # row lock prevents deletion between authorization and FK assignment
        if not ids:
            return []
        rows = conn.execute("""SELECT id, filename, media_type, size_bytes, pages, chat_id FROM api_attachments
                               WHERE owner = %s AND id = ANY(%s)
                               AND (chat_id IS NOT NULL OR created_at > now() - interval '24 hours') FOR UPDATE""",
                            (owner, ids)).fetchall()
        by_id = {row["id"]: row for row in rows}
        if set(by_id) != set(ids):
            raise AttachmentError(404, "Attachment not found.")
        if any(row["chat_id"] not in (None, chat_id) for row in rows):
            raise AttachmentError(409, "An attachment cannot be moved to another chat.")
        conn.execute("UPDATE api_attachments SET chat_id = %s WHERE owner = %s AND id = ANY(%s)", (chat_id, owner, ids))
        return [_info(by_id[value]) for value in ids]


def list_for_chat(owner: str, chat_id: str) -> list[AttachmentInfo]:
    """Metadata only, only after checking the chat belongs to this owner."""
    with _connection() as conn:
        _chat(conn, owner, chat_id)
        rows = conn.execute("""SELECT id, filename, media_type, size_bytes, pages FROM api_attachments
                               WHERE owner = %s AND chat_id = %s ORDER BY created_at, id""", (owner, chat_id)).fetchall()
    return [_info(row) for row in rows]


def _owned(conn: Connection[dict[str, Any]], owner: str, attachment_id: str) -> dict[str, Any] | None:
    # TTL is part of every read, not just opportunistic garbage collection.
    return conn.execute("""SELECT a.* FROM api_attachments a WHERE a.owner = %s AND a.id = %s
                           AND ((a.chat_id IS NULL AND a.created_at > now() - interval '24 hours')
                                OR EXISTS (SELECT 1 FROM api_chats c WHERE c.chat_id = a.chat_id
                                           AND c.innohassle_id = %s)) FOR UPDATE OF a""",
                        (owner, attachment_id, owner)).fetchone()


def get_content(owner: str, id: str) -> tuple[AttachmentInfo, bytes]:
    """Owned original, whether pending (less than 24h old) or bound to an owned chat."""
    _id(id)
    with _connection() as conn:
        row = _owned(conn, owner, id)
    if row is None:
        raise AttachmentError(404, "Attachment not found.")
    return _info(row), bytes(row["data"])


def _page(owner: str, chat_id: str, attachment_id: str, page: int) -> dict:
    _id(attachment_id)
    with _connection() as conn:
        row = _owned(conn, owner, attachment_id)
    if row is None or row["chat_id"] != chat_id or row["chat_id"] is None:
        raise AttachmentError(404, "Attachment not found.")
    if type(page) is not int or not 1 <= page <= row["pages"]:
        raise AttachmentError(422, "Page number is outside the attachment.")
    return row


def read_page(owner: str, chat_id: str, attachment_id: str, page: int) -> dict:
    """Bound page text, with explicit truncation and a note for image/scan/blank pages."""
    row = _page(owner, chat_id, attachment_id, page)
    result = {"id": attachment_id, "filename": row["filename"], "page": page, "pages": row["pages"],
              **row["page_text"][page - 1]}
    if not result["text"].strip() and not result.get("note"):
        result["note"] = "No extractable text on this page; no OCR was performed."
    return result


def image_page(owner: str, chat_id: str, attachment_id: str, page: int) -> bytes:
    """Bound PDF/image page as PNG, at most one megapixel. Never calls a model."""
    row = _page(owner, chat_id, attachment_id, page)
    if row["media_type"] == "text/plain":
        raise AttachmentError(415, "Text attachments do not have page images.")
    return _worker(bytes(row["data"]), Path(row["filename"]).suffix.lower(), page)


def discard(owner: str, id: str) -> bool:
    """Delete an owned unbound upload. Bound files live until their chat is deleted."""
    _id(id)
    with _connection() as conn:
        _lock(conn, owner)
        row = _owned(conn, owner, id)
        if row is None:
            return False
        if row["chat_id"] is not None:
            raise AttachmentError(409, "Bound attachments are deleted with their chat.")
        conn.execute("DELETE FROM api_attachments WHERE id = %s AND owner = %s AND chat_id IS NULL", (id, owner))
    return True
