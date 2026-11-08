"""Opt-in upload -> real agent -> same Sage vision -> history, using disposable SQL only."""
import io
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont
from pydantic import SecretStr

from catix.api import ask
from catix.api.app import app
from catix.api.auth import UserTokenData, verify_asker, verify_user
from catix.db import pg
from catix.settings import settings

pytestmark = [pytest.mark.model,
              pytest.mark.skipif(not os.getenv("ATTACHMENTS_TEST_DATABASE_URL"), reason="needs explicitly disposable attachment database")]


def test_upload_and_reopen_with_real_agent(monkeypatch):
    assert settings.database_url == os.environ["ATTACHMENTS_TEST_DATABASE_URL"]
    assert "catix_attachments_test" in settings.database_url
    owner = "vision-test:" + uuid.uuid4().hex
    user = UserTokenData(innohassle_id=owner, email="synthetic@innopolis.university", token=SecretStr("synthetic-not-a-service-token"))
    monkeypatch.setattr(ask.groups, "website_chat_ids", lambda *a: set())
    monkeypatch.setattr(ask.groups, "website_groups", lambda *a: [])
    monkeypatch.setattr(ask.titles, "name", lambda query: "Attachment test")
    monkeypatch.setattr(settings, "agent_plan_thinking", False)

    async def no_offers(answer, origins=None):
        return []

    monkeypatch.setattr(ask, "calendar_offers", no_offers)
    # No upstream accounts or mutations are authorized by this synthetic identity.
    from catix.agent import api_tools
    def no_service(*args, **kwargs):
        raise AssertionError("Attachment-only questions must not call external services")
    async def no_async_service(*args, **kwargs):
        return no_service(*args, **kwargs)
    monkeypatch.setattr(api_tools.mcp_client, "request_sync", no_service)
    monkeypatch.setattr(api_tools.mcp_client, "request", no_async_service)
    app.dependency_overrides[verify_user] = lambda: user
    app.dependency_overrides[verify_asker] = lambda: user
    try:
        with TestClient(app) as client:
            upload = client.post("/ask/attachments",
                                 content="Сдать отчёт нужно до 18 ноября 2026 года, 16:45. Кабинет 407.".encode(),
                                 headers={"Content-Type": "application/octet-stream", "X-Attachment-Filename": "deadline.txt"})
            assert upload.status_code == 200, upload.text
            file = upload.json()
            response = client.post("/ask/", json={"query": "Какой дедлайн указан в приложенном файле deadline.txt?", "attachment_ids": [file["id"]]})
            assert response.status_code == 200, response.text
            first = response.json()
            assert "18" in first["answer"] and "ноябр" in first["answer"] and "16:45" in first["answer"], first["answer"]
            assert first["attachments"] == [file] and first["approval"] is None
            assert first["ask_query_id"] is None, "private file conversations must not be exported to tracing"

            image = Image.new("RGB", (900, 350), "white")
            draw = ImageDraw.Draw(image)
            font = ImageFont.truetype("/usr/share/fonts/liberation/LiberationSans-Regular.ttf", 38)
            draw.text((30, 55), "Встреча студенческой команды", fill="black", font=font)
            draw.text((30, 125), "Аудитория 512", fill="black", font=font)
            draw.text((30, 195), "Начало: 17:35", fill="black", font=font)
            image_bytes = io.BytesIO()
            image.save(image_bytes, format="PNG")
            uploaded_image = client.post("/ask/attachments", content=image_bytes.getvalue(),
                                         headers={"Content-Type": "application/octet-stream", "X-Attachment-Filename": "meeting.png"})
            assert uploaded_image.status_code == 200, uploaded_image.text
            second_file = uploaded_image.json()
            response = client.post("/ask/", json={"query": "Какая аудитория и время начала на прикреплённом объявлении meeting.png?",
                                                  "chat_id": first["chat_id"], "attachment_ids": [second_file["id"]]})
            assert response.status_code == 200, response.text
            second = response.json()
            assert "512" in second["answer"] and "17:35" in second["answer"], second["answer"]
            assert second["approval"] is None
            history = client.get(f"/ask/chats/{first['chat_id']}").json()
            assert [a["attachments"] for a in history["answers"]] == [[file], [second_file]]
            download = client.get(f"/ask/attachments/{second_file['id']}/content")
            assert download.status_code == 200 and download.content == image_bytes.getvalue()
            deleted = client.delete(f"/ask/chats/{first['chat_id']}")
            assert deleted.status_code == 200
            assert client.get(f"/ask/attachments/{file['id']}/content").status_code == 404
            assert client.get(f"/ask/attachments/{second_file['id']}/content").status_code == 404
    finally:
        app.dependency_overrides.pop(verify_user, None)
        app.dependency_overrides.pop(verify_asker, None)
        with pg.connection() as conn:
            conn.execute("DELETE FROM api_chats WHERE innohassle_id = %s", (owner,))
            conn.execute("DELETE FROM api_attachments WHERE owner = %s", (owner,))
        pg.close()
