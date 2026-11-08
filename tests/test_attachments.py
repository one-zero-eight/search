"""Private attachments: real bounded decoders, fake database boundaries only."""
import importlib
import importlib.util
import io
from unittest.mock import MagicMock

import pytest
from PIL import Image


def module():
    # Keep missing implementation a clear RED assertion, not a collection error.
    assert importlib.util.find_spec("catix.attachments") is not None, "private attachment module is missing"
    return importlib.import_module("catix.attachments")


def test_utf8_text_is_parsed_before_being_stored(monkeypatch):
    a = module()
    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.execute.return_value.fetchone.return_value = {"total": 0, "pending": 0, "bytes": 0}
    monkeypatch.setattr(a.pg, "connection", lambda: conn)
    info = a.create("alice", "notes.txt", "Привет\nworld".encode())
    assert set(info.model_dump()) == {"id", "filename", "media_type", "size_bytes", "pages"}
    assert info.filename == "notes.txt" and info.pages == 1 and info.media_type == "text/plain"
    assert info.size_bytes == len("Привет\nworld".encode())
    calls = conn.__enter__().execute.call_args_list
    # The transaction context is the mock's entered connection.
    inserts = [c for c in calls if "INSERT INTO api_attachments" in c.args[0]]
    assert len(inserts) == 1
    assert "Привет" in str(inserts[0].args[1][-1].obj)


@pytest.mark.parametrize("filename,data,status", [
    ("../notes.txt", b"hello", 422), ("bad\r\n.txt", b"hello", 422),
    ("bad\u202e.txt", b"hello", 422), ("n" * 201 + ".txt", b"hello", 422),
    ("notes.txt", b"", 422), ("notes.txt", b"x" * (10 * 1024 * 1024 + 1), 413),
    ("notes.txt", b"\xff\x00", 422), ("notes.txt", b"<html><script>bad()</script></html>", 415),
    ("notes.txt", b"<svg xmlns='x'></svg>", 415), ("notes.txt", b"PK\x03\x04zip", 415),
    ("notes.txt", b"\x7fELFbinary", 415), ("notes.txt", b"#!/bin/sh\necho x", 415),
    ("file.svg", b"<svg/>", 415), ("file.pdf", b"not pdf", 422),
], ids=lambda value: str(value)[:40])
def test_bad_upload_never_reaches_storage(monkeypatch, filename, data, status):
    a = module()
    db = MagicMock(side_effect=AssertionError("must not open DB"))
    monkeypatch.setattr(a.pg, "connection", db)
    with pytest.raises(a.AttachmentError) as error:
        a.create("alice", filename, data)
    assert error.value.status_code == status
    db.assert_not_called()


@pytest.mark.parametrize("quota", [
    {"total": 50, "pending": 0, "bytes": 0},
    {"total": 20, "pending": 20, "bytes": 0},
    {"total": 10, "pending": 0, "bytes": 100 * 1024 * 1024},
])
def test_quota_is_checked_under_transaction_lock(monkeypatch, quota):
    a = module()
    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.execute.return_value.fetchone.return_value = quota
    monkeypatch.setattr(a.pg, "connection", lambda: conn)
    with pytest.raises(a.AttachmentError) as error:
        a.create("alice", "n.txt", b"hello")
    assert error.value.status_code == 413
    sqls = [c.args[0] for c in conn.execute.call_args_list]
    assert "pg_advisory_xact_lock" in sqls[0]
    assert any("interval '24 hours'" in sql for sql in sqls)
    assert not any("INSERT INTO" in sql for sql in sqls)


def image_bytes(fmt="PNG", size=(40, 20)):
    out = io.BytesIO()
    Image.new("RGB", size, "red").save(out, format=fmt)
    return out.getvalue()


@pytest.mark.parametrize("fmt,suffix,mime", [("PNG", ".png", "image/png"), ("JPEG", ".jpg", "image/jpeg"), ("WEBP", ".webp", "image/webp")])
def test_images_decode_and_render_as_small_png(fmt, suffix, mime):
    import json
    a = module()
    data = image_bytes(fmt, (1600, 1200))
    result = json.loads(a._worker(data, suffix))
    assert result["media_type"] == mime and len(result["pages"]) == 1
    assert not result["pages"][0]["text"] and result["pages"][0]["note"]
    png = a._worker(data, suffix, 1)
    with Image.open(io.BytesIO(png)) as im:
        assert im.format == "PNG" and im.width * im.height <= 1_000_000
        assert im.getpixel((0, 0))[0] > 240


def test_render_composites_transparent_images_on_white():
    a = module()
    source = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    source.putpixel((5, 5), (0, 0, 0, 255))
    out = io.BytesIO()
    source.save(out, format="PNG")
    with Image.open(io.BytesIO(a._worker(out.getvalue(), ".png", 1))) as image:
        assert image.getpixel((0, 0)) == (255, 255, 255)
        assert image.getpixel((5, 5)) == (0, 0, 0)


def test_decoded_format_must_match_the_filename():
    a = module()
    with pytest.raises(a.AttachmentError):
        a._worker(image_bytes(), ".jpg")


def test_image_pixel_limit_is_checked_before_decoding():
    import struct
    import zlib
    a = module()
    data = bytearray(image_bytes())
    data[16:24] = struct.pack(">II", 100_000, 100_000)
    data[29:33] = struct.pack(">I", zlib.crc32(data[12:29]))
    with pytest.raises(a.AttachmentError):
        a._worker(bytes(data), ".png")


def pdf_bytes(texts=("First page", "", "Last page")):
    """Small real PDF, no optional fixture-generation dependency."""
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for text in texts:
        page_id = len(objects) + 1
        kids.append(f"{page_id} 0 R")
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 400] /Resources << /Font << /F1 3 0 R >> >> /Contents {page_id + 1} 0 R >>".encode())
        stream = (f"BT /F1 12 Tf 20 350 Td ({text}) Tj ET".encode() if text is not None else
                  b"q 100 0 0 100 20 200 cm BI /W 1 /H 1 /CS /RGB /BPC 8 ID \xff\x00\x00 EI Q")
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
    objects[1] = f"<< /Type /Pages /Count {len(kids)} /Kids [{' '.join(kids)}] >>".encode()
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for n, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{n} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    for offset in offsets[1:]:
        out += f"{offset:010} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


def test_real_pdf_preserves_text_and_blank_page_numbers():
    import json
    a = module()
    result = json.loads(a._worker(pdf_bytes(), ".pdf"))
    assert result["media_type"] == "application/pdf"
    assert len(result["pages"]) == 3
    assert "First page" in result["pages"][0]["text"]
    assert result["pages"][1]["text"] == "" and result["pages"][1]["note"]
    assert "Last page" in result["pages"][2]["text"]
    assert not any(p["truncated"] for p in result["pages"])
    png = a._worker(pdf_bytes(), ".pdf", 3)
    with Image.open(io.BytesIO(png)) as im:
        assert im.format == "PNG" and im.width * im.height <= 1_000_000


def test_pdf_page_limit_and_broken_pdf_are_rejected():
    a = module()
    for data in (pdf_bytes(["x"] * 21), b"%PDF-1.4\nbroken"):
        with pytest.raises(a.AttachmentError):
            a._worker(data, ".pdf")


def record(id="a" * 32, chat_id=None):
    return {"id": id, "owner": "alice", "filename": "n.txt", "media_type": "text/plain", "size_bytes": 5,
            "pages": 1, "data": b"hello", "chat_id": chat_id, "page_text": [{"text": "hello", "truncated": False}]}


def fake_connection(monkeypatch, *, rows=None, chat=True, row=None):
    a = module()
    conn = MagicMock()
    conn.__enter__.return_value = conn
    def execute(sql, params=None):
        result = MagicMock()
        if "FROM api_chats" in sql and "SELECT chat_id" in sql:
            result.fetchone.return_value = {"chat_id": "chat"} if chat else None
        else:
            result.fetchone.return_value = row
        result.fetchall.return_value = rows or []
        return result
    conn.execute.side_effect = execute
    monkeypatch.setattr(a.pg, "connection", lambda: conn)
    return conn


def test_bind_is_atomic_owned_and_idempotent(monkeypatch):
    a = module()
    assert hasattr(a, "bind"), "binding is missing"
    rows = [record("b" * 32, "chat"), record()]
    conn = fake_connection(monkeypatch, rows=rows)
    result = a.bind("alice", "chat", ["a" * 32, "b" * 32])
    assert [r.id for r in result] == ["a" * 32, "b" * 32]
    calls = conn.execute.call_args_list
    selects = [c for c in calls if "FROM api_chats" in c.args[0]]
    assert "innohassle_id = %s" in selects[0].args[0] and "FOR UPDATE" in selects[0].args[0]
    assert selects[0].args[1] == ("chat", "alice")
    attachment_select = next(c for c in calls if "SELECT" in c.args[0] and "FROM api_attachments" in c.args[0])
    assert "owner = %s" in attachment_select.args[0] and "FOR UPDATE" in attachment_select.args[0]
    assert sum("UPDATE api_attachments" in c.args[0] for c in calls) == 1


@pytest.mark.parametrize("rows,chat,status", [([], True, 404), ([record(chat_id="other")], True, 409), ([record()], False, 404)])
def test_bind_never_partially_binds_bad_set(monkeypatch, rows, chat, status):
    a = module()
    assert hasattr(a, "bind"), "binding is missing"
    conn = fake_connection(monkeypatch, rows=rows, chat=chat)
    with pytest.raises(a.AttachmentError) as error:
        a.bind("alice", "chat", ["a" * 32])
    assert error.value.status_code == status
    assert not any("UPDATE api_attachments" in c.args[0] for c in conn.execute.call_args_list)


@pytest.mark.parametrize("ids", [["a" * 32] * 2, [str(n) * 32 for n in range(4)], ["../bad"], ["https://host/a"], ["A" * 32]])
def test_bind_rejects_invalid_ids_before_db(monkeypatch, ids):
    a = module()
    assert hasattr(a, "bind"), "binding is missing"
    conn = MagicMock(side_effect=AssertionError("no DB"))
    monkeypatch.setattr(a.pg, "connection", conn)
    with pytest.raises(a.AttachmentError):
        a.bind("alice", "chat", ids)
    conn.assert_not_called()


def test_list_requires_chat_ownership_and_returns_only_metadata(monkeypatch):
    a = module()
    assert hasattr(a, "list_for_chat"), "list is missing"
    conn = fake_connection(monkeypatch, rows=[record(chat_id="chat")])
    assert [x.model_dump() for x in a.list_for_chat("alice", "chat")] == [{k: record()[k] for k in ("id", "filename", "media_type", "size_bytes", "pages")}]
    fake_connection(monkeypatch, rows=[record(chat_id="chat")], chat=False)
    with pytest.raises(a.AttachmentError) as error:
        a.list_for_chat("bob", "chat")
    assert error.value.status_code == 404


def test_read_and_content_enforce_owner_ttl_and_chat_scope(monkeypatch):
    a = module()
    assert hasattr(a, "read_page") and hasattr(a, "get_content"), "read functions missing"
    conn = fake_connection(monkeypatch, row=record(chat_id="chat"))
    result = a.read_page("alice", "chat", "a" * 32, 1)
    assert result == {"id": "a" * 32, "filename": "n.txt", "page": 1, "pages": 1, "text": "hello", "truncated": False}
    info, data = a.get_content("alice", "a" * 32)
    assert info.filename == "n.txt" and data == b"hello"
    selects = [c for c in conn.execute.call_args_list if "SELECT" in c.args[0]]
    assert all("a.owner = %s" in c.args[0] and "innohassle_id" in c.args[0] and "interval '24 hours'" in c.args[0] for c in selects)
    assert all(c.args[1][0] == "alice" for c in selects)
    with pytest.raises(a.AttachmentError) as error:
        a.read_page("alice", "other-chat", "a" * 32, 1)
    assert error.value.status_code == 404
    fake_connection(monkeypatch, row=None)
    with pytest.raises(a.AttachmentError) as error:
        a.get_content("bob", "a" * 32)
    assert error.value.status_code == 404


@pytest.mark.parametrize("page", [0, -1, 2, True, "1"])
def test_read_rejects_invalid_pages(monkeypatch, page):
    a = module()
    assert hasattr(a, "read_page"), "read missing"
    fake_connection(monkeypatch, row=record(chat_id="chat"))
    with pytest.raises(a.AttachmentError) as error:
        a.read_page("alice", "chat", "a" * 32, page)
    assert error.value.status_code == 422


def test_image_page_uses_owned_original_and_rejects_text(monkeypatch):
    a = module()
    assert hasattr(a, "image_page"), "image read missing"
    row = record(chat_id="chat")
    fake_connection(monkeypatch, row=row)
    with pytest.raises(a.AttachmentError) as error:
        a.image_page("alice", "chat", row["id"], 1)
    assert error.value.status_code == 415
    row.update(filename="image.png", media_type="image/png", data=image_bytes())
    data = a.image_page("alice", "chat", row["id"], 1)
    assert data.startswith(b"\x89PNG")
    with pytest.raises(a.AttachmentError) as error:
        a.image_page("alice", "other", row["id"], 1)
    assert error.value.status_code == 404


def test_discard_only_unbound_owned_live_uploads(monkeypatch):
    a = module()
    assert hasattr(a, "discard"), "discard missing"
    fake_connection(monkeypatch, row=record())
    assert a.discard("alice", "a" * 32)
    fake_connection(monkeypatch, row=None)
    assert not a.discard("bob", "a" * 32)
    conn = fake_connection(monkeypatch, row=record(chat_id="chat"))
    with pytest.raises(a.AttachmentError) as error:
        a.discard("alice", "a" * 32)
    assert error.value.status_code == 409
    assert not any("DELETE FROM api_attachments WHERE id" in c.args[0] for c in conn.execute.call_args_list)


def test_metadata_pages_are_positive():
    from pydantic import ValidationError
    a = module()
    with pytest.raises(ValidationError):
        a.AttachmentInfo(id="a" * 32, filename="x.pdf", media_type="application/pdf", size_bytes=5, pages=0)


@pytest.mark.parametrize("source", ["First page", "First !!!"])
def test_partial_nonempty_pdf_extraction_is_not_reported_complete(monkeypatch, tmp_path, source):
    import json
    import opendataloader_pdf
    from catix import attachment_reader as reader
    monkeypatch.chdir(tmp_path)
    def partial(**kwargs):
        (tmp_path / "input.json").write_text(json.dumps({"number of pages": 1, "kids": [
            {"type": "paragraph", "page number": 1, "content": "First"}]}))
    monkeypatch.setattr(opendataloader_pdf, "convert", partial)
    page = reader._pdf_text(pdf_bytes([source]))["pages"][0]
    assert page["text"] == "First" and page["truncated"] is True
    assert "incomplete" in page["note"].lower()


def test_txt_html_after_long_prefix_is_rejected():
    a = module()
    with pytest.raises(a.AttachmentError):
        a._worker(b" " * 10_000 + b"<html>not text</html>", ".txt")


def test_truncated_png_is_rejected_even_if_pixels_decode():
    a = module()
    with pytest.raises(a.AttachmentError):
        a._worker(image_bytes()[:-12], ".png")


def test_filename_surrogate_is_a_safe_domain_error(monkeypatch):
    a = module()
    monkeypatch.setattr(a.pg, "connection", MagicMock(side_effect=AssertionError("no DB")))
    with pytest.raises(a.AttachmentError) as error:
        a.create("alice", "bad\ud800.txt", b"hello")
    assert error.value.status_code == 422


def test_storage_failure_does_not_expose_database_payload(monkeypatch):
    from psycopg.errors import CheckViolation
    a = module()
    conn = MagicMock()
    conn.__enter__.return_value = conn
    def execute(sql, params):
        if "INSERT INTO" in sql:
            raise CheckViolation("private uploaded text must not escape")
        result = MagicMock()
        result.fetchone.return_value = {"total": 0, "pending": 0, "bytes": 0}
        return result
    conn.execute.side_effect = execute
    monkeypatch.setattr(a.pg, "connection", lambda: conn)
    with pytest.raises(a.AttachmentError) as error:
        a.create("alice", "n.txt", b"hello")
    assert error.value.status_code == 503
    assert "private uploaded" not in error.value.detail
    assert conn.__exit__.call_args.args[0] is CheckViolation


def test_mixed_scan_pdf_preserves_the_image_page():
    import json
    a = module()
    data = pdf_bytes(["First page", None, "Last page"])
    result = json.loads(a._worker(data, ".pdf"))
    assert len(result["pages"]) == 3
    assert result["pages"][1]["text"] == "" and "no OCR" in result["pages"][1]["note"]
    assert "First page" in result["pages"][0]["text"] and "Last page" in result["pages"][2]["text"]
    with Image.open(io.BytesIO(a._worker(data, ".pdf", 2))) as image:
        assert image.width * image.height <= 1_000_000
        assert image.convert("RGB").getextrema()[1][0] < 100  # rendered red embedded image, not an empty page


def test_text_truncation_is_explicit_and_original_unchanged():
    import json
    a = module()
    data = b"x" * 60_001
    parsed = json.loads(a._worker(data, ".txt"))
    assert parsed["pages"] == [{"text": "x" * 60_000, "truncated": True}]
    assert len(data) == 60_001


def test_even_empty_password_encrypted_pdf_is_rejected():
    import base64
    import pdfplumber
    # PDFBox fixture with a valid empty user password, so rejection must be the explicit encryption guard.
    data = base64.b64decode(
        "JVBERi0xLjYKJfbk/N8KMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKL1ZlcnNpb24gLzEuNgo+PgplbmRvYmoKNSAwIG9iago8PAovTGVuZ3RoIDQ1Cj4+CnN0cmVhbQ0KE3j6Y+6sVDk5Z5e6Q4HBHP2+gHEvLpsvr95vuECbROsp81YGbD9CwMp1J+gmDQplbmRzdHJlYW0KZW5kb2JqCjYgMCBvYmoKPDwKL0xlbmd0aCAxNTcKL1R5cGUgL09ialN0bQovTiAzCi9GaWx0ZXIgL0ZsYXRlRGVjb2RlCi9GaXJzdCAxNAo+PgpzdHJlYW0NCioCXury3kF1dmoyQGJx3KbD/SW7AYvo8prNGGcEfcCZZUzTcAfIQU65Mowv8cBbeThiGS1fik+vYwnP/khDxVcHs1hO1qbwYLAFSlSue5cEEBpBztm6bC8YEtFaQM117D3OsHl/AkCGTsTBK7dFU4yge88eYsfWCfjEbX+ezcBAllzr5JsVPrSLs81gZyWzSkIy1DDaAh5o+/Q+V7kNCmVuZHN0cmVhbQplbmRvYmoKNyAwIG9iago8PAovRmlsdGVyIC9TdGFuZGFyZAovViAyCi9SIDMKL0xlbmd0aCAxMjgKL1AgLTQKL08gPDZBMzEzNzYzRjBFOTZCM0QxQkI1MjI4M0E2Njg0MDhGRUQ3OUMyMDk0MkRCOTMxNTYzMEJGMTZGNjdCQjNCNDc+Ci9VIDwwMUY4RUQyOUQ1MzBCNTkyQjkyRjc0Q0I3MjJBMDY5MDI4QkY0RTVFNEU3NThBNDE2NDAwNEU1NkZGRkEwMTA4Pgo+PgplbmRvYmoKOCAwIG9iago8PAovTGVuZ3RoIDM2Ci9Sb290IDEgMCBSCi9JRCBbPDZBMDk5NTIyQjgzMTIzNzQzM0JDQTJDMEQ3REQ5ODIwPiA8NkEwOTk1MjJCODMxMjM3NDMzQkNBMkMwRDdERDk4MjA+XQovRW5jcnlwdCA3IDAgUgovVHlwZSAvWFJlZgovU2l6ZSA5Ci9JbmRleCBbMCA4XQovVyBbMSAyIDFdCi9GaWx0ZXIgL0ZsYXRlRGVjb2RlCj4+CnN0cmVhbQ0KeJxjYGD4z8jAz8DEwAbCjEDMxMjgx8DIsJ6BkXEzAwApMwLfDQplbmRzdHJlYW0KZW5kb2JqCnN0YXJ0eHJlZgo2NDIKJSVFT0YK"
    )
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        assert pdf.doc.encryption and pdf.pages[0].extract_text() == "Encrypted page"
    a = module()
    with pytest.raises(a.AttachmentError):
        a._worker(data, ".pdf")


def test_timeout_kills_worker_and_its_child_and_releases_slot(monkeypatch, tmp_path):
    import sys
    import subprocess
    from pathlib import Path
    a = module()
    processes = []
    popen = subprocess.Popen
    pidfile = tmp_path / "child.pid"
    script = ("import subprocess,sys,time,pathlib; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); "
              f"pathlib.Path({str(pidfile)!r}).write_text(str(p.pid)); time.sleep(30)")
    def slow(*args, **kwargs):
        assert set(kwargs["env"]) <= {"PATH", "LANG", "TMPDIR", "WIKI_ROOT", "PYTHONPATH"}
        process = popen([sys.executable, "-c", script], **kwargs)
        processes.append(process)
        return process
    monkeypatch.setattr(a.subprocess, "Popen", slow)
    monkeypatch.setattr(a, "WORKER_TIMEOUT", 1)
    with pytest.raises(a.AttachmentError) as error:
        a._worker(b"hello", ".txt")
    assert error.value.status_code == 422 and "timed out" in error.value.detail
    assert processes[0].poll() is not None
    child = int(pidfile.read_text())
    state = Path(f"/proc/{child}/stat")
    # The init process may not have reaped the grandchild yet, but it must no longer run.
    assert not state.exists() or state.read_text().split()[2] == "Z"
    monkeypatch.setattr(a.subprocess, "Popen", popen)
    assert b"hello" in a._worker(b"hello", ".txt")


@pytest.fixture
def disposable_db(monkeypatch):
    import os
    import uuid
    import psycopg
    from psycopg.rows import dict_row
    dsn = os.environ.get("CATIX_ATTACHMENT_TEST_DSN")
    if not dsn:
        pytest.skip("set CATIX_ATTACHMENT_TEST_DSN to a disposable PostgreSQL, never production")
    assert "catix_attachments_test" in dsn, "refuse a non-test database"
    a = module()
    owner = "attachments-test:" + uuid.uuid4().hex
    c1, c2 = uuid.uuid4().hex, uuid.uuid4().hex
    def connect():
        return psycopg.connect(dsn, row_factory=dict_row)
    monkeypatch.setattr(a.pg, "connection", connect)
    with connect() as conn:
        for chat in (c1, c2):
            conn.execute("INSERT INTO api_chats (chat_id, innohassle_id, title) VALUES (%s, %s, 'attachment test')", (chat, owner))
    try:
        yield owner, c1, c2, connect
    finally:
        with connect() as conn:
            conn.execute("DELETE FROM api_attachments WHERE owner = %s", (owner,))
            conn.execute("DELETE FROM api_chats WHERE innohassle_id = %s", (owner,))
            assert conn.execute("SELECT count(*) AS n FROM api_attachments WHERE owner = %s", (owner,)).fetchone()["n"] == 0
            assert conn.execute("SELECT count(*) AS n FROM api_chats WHERE innohassle_id = %s", (owner,)).fetchone()["n"] == 0


def test_postgres_ownership_atomic_binding_expiry_and_cascade(disposable_db):
    a = module()
    owner, c1, c2, connect = disposable_db
    txt = a.create(owner, "notes.txt", b"hello")
    pdf = a.create(owner, "pages.pdf", pdf_bytes())
    pending = a.create(owner, "image.png", image_bytes())
    assert a.get_content(owner, txt.id) == (txt, b"hello")
    for fn in (lambda: a.get_content("not-owner", txt.id), lambda: a.list_for_chat("not-owner", c1),
               lambda: a.bind("not-owner", c1, [txt.id]), lambda: a.read_page(owner, c1, txt.id, 1)):
        with pytest.raises(a.AttachmentError) as error:
            fn()
        assert error.value.status_code == 404
    with pytest.raises(a.AttachmentError):
        a.bind(owner, c1, [txt.id, "f" * 32])
    assert a.list_for_chat(owner, c1) == []
    assert a.bind(owner, c1, [txt.id, pdf.id]) == [txt, pdf]
    assert a.bind(owner, c1, [txt.id]) == [txt]
    assert {i.id for i in a.list_for_chat(owner, c1)} == {txt.id, pdf.id}
    with pytest.raises(a.AttachmentError) as error:
        a.bind(owner, c2, [pending.id, txt.id])
    assert error.value.status_code == 409 and a.list_for_chat(owner, c2) == []
    assert a.read_page(owner, c1, pdf.id, 3)["text"] == "Last page"
    assert a.image_page(owner, c1, pdf.id, 1).startswith(b"\x89PNG")
    with pytest.raises(a.AttachmentError) as error:
        a.discard(owner, txt.id)
    assert error.value.status_code == 409
    assert a.discard("not-owner", pending.id) is False
    with connect() as conn:
        conn.execute("UPDATE api_attachments SET created_at = now() - interval '25 hours' WHERE id = %s", (pending.id,))
    with pytest.raises(a.AttachmentError) as error:
        a.get_content(owner, pending.id)
    assert error.value.status_code == 404
    with pytest.raises(a.AttachmentError):
        a.bind(owner, c2, [pending.id])
    assert a.discard(owner, pending.id) is False
    with connect() as conn:
        conn.execute("DELETE FROM api_chats WHERE chat_id = %s", (c1,))
        assert conn.execute("SELECT count(*) AS n FROM api_attachments WHERE id = ANY(%s)", ([txt.id, pdf.id],)).fetchone()["n"] == 0
    with pytest.raises(a.AttachmentError):
        a.get_content(owner, txt.id)


def test_postgres_quotas_serialize_concurrent_uploads(disposable_db, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    a = module()
    owner, c1, _, connect = disposable_db
    monkeypatch.setattr(a, "MAX_PENDING", 1)
    def upload(_):
        try:
            return a.create(owner, "n.txt", b"hello")
        except a.AttachmentError as error:
            return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(upload, range(2)))
    successes = [r for r in results if isinstance(r, a.AttachmentInfo)]
    assert len(successes) == 1 and results.count(413) == 1
    a.bind(owner, c1, [successes[0].id])
    monkeypatch.setattr(a, "MAX_TOTAL", 1)
    assert upload(0) == 413
    monkeypatch.setattr(a, "MAX_TOTAL", 50)
    monkeypatch.setattr(a, "MAX_OWNER_BYTES", 5)
    assert upload(0) == 413
    with connect() as conn:
        assert conn.execute("SELECT count(*) AS n FROM api_attachments WHERE owner = %s", (owner,)).fetchone()["n"] == 1
