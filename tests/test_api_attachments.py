"""Attachment API in isolation: no API lifespan or production DB/model calls."""
import importlib
import importlib.util
from unittest.mock import MagicMock
from urllib.parse import quote

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from catix.api.auth import UserTokenData, verify_user
from catix.attachments import AttachmentInfo


def client_and_router(auth=True):
    assert importlib.util.find_spec("catix.api.attachments") is not None, "attachment API router is missing"
    api = importlib.import_module("catix.api.attachments")
    app = FastAPI()
    app.include_router(api.router)
    if auth:
        app.dependency_overrides[verify_user] = lambda: UserTokenData(innohassle_id="alice", email="a@innopolis.university")
    return TestClient(app), api


def test_raw_upload_and_openapi_binary_schema(monkeypatch):
    client, api = client_and_router()
    info = AttachmentInfo(id="a" * 32, filename="hello.txt", media_type="text/plain", size_bytes=5, pages=1)
    create = MagicMock(return_value=info)
    monkeypatch.setattr(api.attachments, "create", create)
    response = client.post("/ask/attachments", content=b"hello", headers={"content-type": "application/octet-stream", "X-Attachment-Filename": "hello.txt"})
    assert response.status_code == 200 and response.json() == info.model_dump()
    create.assert_called_once_with("alice", "hello.txt", b"hello")
    schema = client.get("/openapi.json").json()["paths"]["/ask/attachments"]["post"]
    assert schema["requestBody"]["content"]["application/octet-stream"]["schema"] == {"type": "string", "format": "binary"}
    assert [(p["name"], p["in"], p["required"]) for p in schema["parameters"]] == [("X-Attachment-Filename", "header", True)]


@pytest.mark.parametrize("filename", ["PRIVATE.pdf", "Приватный résumé.pdf", "literal%20%25+name.txt"])
def test_filename_header_decodes_exactly_once(monkeypatch, filename):
    client, api = client_and_router()
    info = AttachmentInfo(id="a" * 32, filename=filename, media_type="text/plain", size_bytes=5, pages=1)
    create = MagicMock(return_value=info)
    monkeypatch.setattr(api.attachments, "create", create)
    response = client.post("/ask/attachments", content=b"hello", headers={
        "Content-Type": "application/octet-stream", "X-Attachment-Filename": quote(filename, safe=""),
    })
    assert response.status_code == 200
    assert response.request.url.query == b""
    assert filename not in str(response.request.url)
    assert response.json()["filename"] == filename
    create.assert_called_once_with("alice", filename, b"hello")


@pytest.mark.parametrize("encoded", [b"PRIVATE%.txt", b"PRIVATE%2.txt", b"PRIVATE%GG.txt", b"PRIVATE%FF.txt", b"PRIVATE%C0%AF.txt", b"PRIVATE%ED%A0%80.txt", b"PRIVATE\xe9.txt", b"", b"x" * 201])
def test_invalid_filename_header_is_rejected_without_echo_or_storage(monkeypatch, encoded):
    client, api = client_and_router()
    info = AttachmentInfo(id="a" * 32, filename="x.txt", media_type="text/plain", size_bytes=1, pages=1)
    create = MagicMock(return_value=info)
    monkeypatch.setattr(api.attachments, "create", create)
    response = client.post("/ask/attachments", content=b"x", headers={
        "Content-Type": "application/octet-stream", "X-Attachment-Filename": encoded,
    })
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid attachment filename header."}
    assert "PRIVATE" not in response.text
    create.assert_not_called()


def test_upload_requires_filename_header_not_query(monkeypatch):
    client, api = client_and_router()
    create = MagicMock()
    monkeypatch.setattr(api.attachments, "create", create)
    response = client.post("/ask/attachments", params={"filename": "old-client.txt"}, content=b"x",
                           headers={"Content-Type": "application/octet-stream"})
    assert response.status_code == 422
    create.assert_not_called()


def test_upload_filename_is_absent_from_real_uvicorn_access_log(monkeypatch, caplog):
    import logging
    import socket
    import threading
    import time

    import httpx
    import uvicorn

    client, api = client_and_router()
    filename = "PRIVATE_FILENAME_SENTINEL.pdf"
    info = AttachmentInfo(id="a" * 32, filename=filename, media_type="application/pdf", size_bytes=5, pages=1)
    monkeypatch.setattr(api.attachments, "create", MagicMock(return_value=info))
    caplog.set_level(logging.INFO, logger="uvicorn.access")
    monkeypatch.setattr(logging.getLogger("uvicorn.access"), "propagate", True)
    server = uvicorn.Server(uvicorn.Config(client.app, log_config=None, lifespan="off", http="h11"))
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 5
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.01)
            assert server.started
            response = httpx.post(f"http://127.0.0.1:{sock.getsockname()[1]}/ask/attachments", content=b"hello",
                                  headers={"Content-Type": "application/octet-stream", "X-Attachment-Filename": filename})
            assert response.status_code == 200
        finally:
            server.should_exit = True
            thread.join(timeout=5)
        assert not thread.is_alive()
    access = [r.getMessage() for r in caplog.records if r.name == "uvicorn.access"]
    assert any('"POST /ask/attachments HTTP/1.1" 200' in line for line in access)
    assert filename not in "\n".join(access)


def test_upload_is_authenticated():
    client, _ = client_and_router(auth=False)
    assert client.post("/ask/attachments", content=b"hello", headers={"X-Attachment-Filename": "hello.txt"}).status_code == 401


def test_upload_rejects_non_binary_content_type(monkeypatch):
    client, api = client_and_router()
    create = MagicMock()
    monkeypatch.setattr(api.attachments, "create", create)
    assert client.post("/ask/attachments", content=b"hello", headers={"content-type": "text/plain", "X-Attachment-Filename": "hello.txt"}).status_code == 415
    create.assert_not_called()


def test_oversize_stream_stops_before_consuming_rest(monkeypatch):
    import asyncio
    import pytest
    from fastapi import HTTPException
    from starlette.requests import Request
    _, api = client_and_router()
    monkeypatch.setattr(api.attachments, "MAX_BYTES", 5)
    create = MagicMock()
    monkeypatch.setattr(api.attachments, "create", create)
    reads = []
    async def receive():
        reads.append(1)
        assert len(reads) <= 2, "read beyond limit"
        return {"type": "http.request", "body": b"1234", "more_body": True}
    request = Request({"type": "http", "method": "POST", "path": "/ask/attachments", "headers": [(b"content-type", b"application/octet-stream")]}, receive)
    with pytest.raises(HTTPException) as error:
        asyncio.run(api.upload(request, UserTokenData(innohassle_id="alice", email="a@innopolis.university"), "x.txt"))
    assert error.value.status_code == 413 and len(reads) == 2
    create.assert_not_called()


def test_content_length_limit_rejects_before_read(monkeypatch):
    client, api = client_and_router()
    create = MagicMock()
    monkeypatch.setattr(api.attachments, "create", create)
    response = client.post("/ask/attachments", content=b"x", headers={"content-type": "application/octet-stream", "content-length": str(api.attachments.MAX_BYTES + 1), "X-Attachment-Filename": "x.txt"})
    assert response.status_code == 413
    create.assert_not_called()


def test_download_has_private_safe_binary_headers(monkeypatch):
    client, api = client_and_router()
    info = AttachmentInfo(id="a" * 32, filename='résumé "final".txt', media_type="text/plain", size_bytes=5, pages=1)
    get = MagicMock(return_value=(info, b"hello"))
    monkeypatch.setattr(api.attachments, "get_content", get)
    response = client.get(f"/ask/attachments/{info.id}/content")
    assert response.status_code == 200 and response.content == b"hello"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-disposition"] == "attachment; filename*=UTF-8''r%C3%A9sum%C3%A9%20%22final%22.txt"
    get.assert_called_once_with("alice", info.id)
    schema = client.get("/openapi.json").json()["paths"]["/ask/attachments/{attachment_id}/content"]["get"]
    assert schema["responses"]["200"]["content"] == {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}


def test_delete_unbound_and_map_domain_errors(monkeypatch):
    from catix.attachments import AttachmentError
    client, api = client_and_router()
    discard = MagicMock(return_value=True)
    monkeypatch.setattr(api.attachments, "discard", discard)
    assert client.delete("/ask/attachments/" + "a" * 32).status_code == 204
    discard.assert_called_once_with("alice", "a" * 32)
    discard.return_value = False
    assert client.delete("/ask/attachments/" + "a" * 32).status_code == 404
    discard.side_effect = AttachmentError(409, "Bound attachments are deleted with their chat.")
    assert client.delete("/ask/attachments/" + "a" * 32).status_code == 409
    monkeypatch.setattr(api.attachments, "get_content", MagicMock(side_effect=AttachmentError(404, "Attachment not found.")))
    assert client.get("/ask/attachments/" + "a" * 32 + "/content").status_code == 404
    unauth, _ = client_and_router(auth=False)
    assert unauth.get("/ask/attachments/" + "a" * 32 + "/content").status_code == 401
    assert unauth.delete("/ask/attachments/" + "a" * 32).status_code == 401
