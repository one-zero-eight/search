"""Chat-image OCR is literal, bounded, and uses the already loaded agent model."""
import asyncio
import io
import json
from types import SimpleNamespace

import httpx
import pytest
from PIL import Image

from catix.ingest import images
from catix.settings import settings


def png(size=(1200, 800)):
    out = io.BytesIO()
    Image.new("RGB", size, "white").save(out, format="PNG")
    return out.getvalue()


def test_ocr_uses_agent_endpoint_and_preserves_literal_text(monkeypatch):
    seen = []
    text = "Мидтерм\n12 ноября, 18:30\nАудитория 305\nРегистрация до 10.11"

    def respond(request):
        payload = json.loads(request.content)
        seen.append((str(request.url), payload))
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps({"text": text}, ensure_ascii=False)}}]})

    client = httpx.AsyncClient
    monkeypatch.setattr(images.httpx, "AsyncClient", lambda **kw: client(transport=httpx.MockTransport(respond), **kw))
    monkeypatch.setattr(settings, "llm_priority", True)
    result = asyncio.run(images.transcribe(png()))
    assert result == text
    url, payload = seen[0]
    assert url == str(settings.llm_route).rstrip("/") + "/chat/completions"
    assert payload["model"] == settings.llm_model
    assert payload["priority"] == 0
    assert payload["chat_template_kwargs"] == {"enable_thinking": False}
    assert "tools" not in payload
    assert "transcribe" in payload["messages"][0]["content"].lower()
    assert "untrusted" in payload["messages"][0]["content"].lower()
    assert payload["messages"][1]["content"][0]["type"] == "image_url"


@pytest.mark.parametrize("choice", [
    {"finish_reason": "length", "message": {"content": '{"text":"half a page"}'}},
    {"finish_reason": "stop", "message": {"content": "A plausible summary"}},
    {"finish_reason": "stop", "message": {"content": '{"text":42}'}},
    {"finish_reason": "stop", "message": {"content": '{"text":"ok"}', "tool_calls": [{}]}},
])
def test_incomplete_or_unstructured_ocr_is_not_indexed(monkeypatch, choice):
    client = httpx.AsyncClient
    monkeypatch.setattr(images.httpx, "AsyncClient", lambda **kw: client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"choices": [choice]})), **kw))
    with pytest.raises(ValueError):
        asyncio.run(images.transcribe(png()))


def test_image_normalization_keeps_readable_resolution_and_strips_metadata():
    normalized = Image.open(io.BytesIO(images.normalize(png((1800, 1200)))))
    assert normalized.size == (1800, 1200)
    assert normalized.mode == "RGB"
    assert not normalized.getexif()


def test_non_images_and_oversize_inputs_are_rejected_before_model(monkeypatch):
    monkeypatch.setattr(images, "MAX_BYTES", 10)
    with pytest.raises(ValueError):
        images.normalize(b"x" * 11)
    with pytest.raises((ValueError, OSError)):
        images.normalize(b"not image")


def test_download_buffer_limits_before_allocation(monkeypatch):
    monkeypatch.setattr(images, "MAX_BYTES", 4)
    with images.LimitedBuffer() as buffer:
        buffer.write(b"1234")
        with pytest.raises(ValueError):
            buffer.write(b"5")
        assert buffer.getvalue() == b"1234"


@pytest.mark.parametrize("url", [
    "http://i.oneme.ru/x", "https://localhost/x", "https://127.0.0.1/x",
    "https://i.oneme.ru.evil.test/x", "https://@i.oneme.ru/x", "https://i.oneme.ru:8080/x",
    "https://i.oneme.ru/x#fragment", "https://example.com/image.png",
])
def test_download_rejects_untrusted_urls_without_requests(monkeypatch, url):
    def unexpected(**kw):
        pytest.fail("an unsafe URL reached HTTP")
    monkeypatch.setattr(images.httpx, "AsyncClient", unexpected)
    with pytest.raises(ValueError):
        asyncio.run(images.download_url(url))


def test_download_never_forwards_auth_or_follows_redirects(monkeypatch):
    requests = []
    def respond(request):
        requests.append(request)
        return httpx.Response(302, headers={"Location": "http://localhost/private"})
    client = httpx.AsyncClient
    monkeypatch.setattr(images.httpx, "AsyncClient", lambda **kw: client(transport=httpx.MockTransport(respond), **kw))
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(images.download_url("https://i.oneme.ru/image"))
    assert len(requests) == 1
    assert "authorization" not in requests[0].headers


@pytest.mark.parametrize("host", ["i.oneme.ru", "i.okcdn.ru"])
def test_download_signed_url_is_redacted_from_httpx_logs(monkeypatch, caplog, host):
    import logging

    url = f"https://{host}/private-image?token=synthetic-cdn-secret&expires=123"
    seen = []
    def respond(request):
        seen.append(str(request.url))
        return httpx.Response(200, content=b"image")
    client = httpx.AsyncClient
    monkeypatch.setattr(images.httpx, "AsyncClient", lambda **kw: client(
        transport=httpx.MockTransport(respond), **kw))
    caplog.set_level(logging.INFO)
    assert asyncio.run(images.download_url(url)) == b"image"
    assert seen == [url]  # The real HTTPX path must still receive the signature.
    assert "synthetic-cdn-secret" not in caplog.text
    assert "private-image" not in caplog.text
    assert url not in caplog.text

    async def unrelated_request():
        async with images.httpx.AsyncClient() as other:
            await other.get("https://example.com/health")
    asyncio.run(unrelated_request())
    assert "https://example.com/health" in caplog.text
    monkeypatch.setattr(images, "MAX_BYTES", 4)
    with pytest.raises(ValueError, match="size limit"):
        asyncio.run(images.download_url(url))
    assert "synthetic-cdn-secret" not in caplog.text


def test_download_valid_image_and_size_bound(monkeypatch):
    client = httpx.AsyncClient
    monkeypatch.setattr(images.httpx, "AsyncClient", lambda **kw: client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, content=b"12345")), **kw))
    assert asyncio.run(images.download_url("https://i.oneme.ru/image")) == b"12345"
    monkeypatch.setattr(images, "MAX_BYTES", 4)
    with pytest.raises(ValueError):
        asyncio.run(images.download_url("https://i.oneme.ru/image"))


@pytest.fixture
def queue_calls(monkeypatch):
    from catix import ingest
    from catix.ingest import publish
    calls = []
    queue = SimpleNamespace(
        finish=lambda job, text: calls.append(("finish", text)) or True,
        fail=lambda job: calls.append(("fail",)) or True,
        discard=lambda job: calls.append(("discard",)) or True,
    )
    monkeypatch.setattr(ingest, "image_queue", queue, raising=False)
    async def published(ids):
        calls.append(("publish", ids))
    monkeypatch.setattr(publish, "publish", published)
    return queue, calls


JOB = {"message_id": 1, "chat_id": -100123, "msg_id": 42, "topic_id": None, "refs": ["photo:1"], "token": "claim"}


def test_worker_finishes_same_message_then_publishes(monkeypatch, queue_calls):
    _, calls = queue_calls
    async def download(job, ref):
        assert job == JOB and ref == "photo:1"
        calls.append(("download",))
        return b"image"
    async def recognize(data):
        assert data == b"image"
        return "12 ноября, 18:30, 305"
    monkeypatch.setattr(images, "transcribe", recognize)
    assert asyncio.run(images.process(JOB, download))
    assert calls == [("download",), ("finish", "12 ноября, 18:30, 305"), ("publish", [(-100123, 42)])]


def test_worker_does_not_publish_stale_result(monkeypatch, queue_calls):
    queue, calls = queue_calls
    queue.finish = lambda job, text: False
    async def download(job, ref):
        return b"image"
    async def recognize(data):
        return "old picture text"
    monkeypatch.setattr(images, "transcribe", recognize)
    assert not asyncio.run(images.process(JOB, download))
    assert calls == []


@pytest.mark.parametrize("revoked_after_read", [False, True])
def test_worker_rechecks_listening_and_topic_before_storing(monkeypatch, queue_calls, revoked_after_read):
    _, calls = queue_calls
    checks = iter([True, False] if revoked_after_read else [False])
    async def allowed(job):
        return next(checks)
    async def download(job, ref):
        assert revoked_after_read, "unselected chat must not download images"
        return b"image"
    async def recognize(data):
        return "do not store this"
    monkeypatch.setattr(images, "transcribe", recognize)
    assert not asyncio.run(images.process(JOB, download, allowed))
    assert calls == [("discard",)]


def test_worker_does_not_index_partial_album(monkeypatch, queue_calls):
    _, calls = queue_calls
    async def download(job, ref):
        if ref == "bad":
            raise ValueError("private signed URL must not be logged")
        return b"image"
    async def recognize(data):
        return "only first image"
    monkeypatch.setattr(images, "transcribe", recognize)
    assert not asyncio.run(images.process({**JOB, "refs": ["ok", "bad"]}, download))
    assert calls == [("fail",)]


def test_worker_deadline_bounds_download_and_records_failure(monkeypatch, queue_calls):
    _, calls = queue_calls
    monkeypatch.setattr(images, "JOB_TIMEOUT", 0.01)
    async def download(job, ref):
        await asyncio.sleep(10)
        pytest.fail("deadline did not cancel download")
    assert not asyncio.run(images.process(JOB, download))
    assert calls == [("fail",)]


def test_worker_cancellation_leaves_claim_for_restart(queue_calls):
    _, calls = queue_calls
    async def download(job, ref):
        raise asyncio.CancelledError
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(images.process(JOB, download))
    assert calls == []


def test_worker_run_retries_database_failure_and_cancels_cleanly(monkeypatch, queue_calls):
    queue, calls = queue_calls
    claims = []
    def claim(source):
        claims.append(source)
        if len(claims) == 1:
            raise OSError("private db URL")
        return JOB
    queue.claim = claim
    async def download(job, ref):
        raise asyncio.CancelledError
    monkeypatch.setattr(images, "POLL_SECONDS", 0)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(images.run("tgbot", download))
    assert claims == ["tgbot", "tgbot"]
    assert calls == []


def test_blank_image_is_success_not_failure(monkeypatch):
    client = httpx.AsyncClient
    monkeypatch.setattr(images.httpx, "AsyncClient", lambda **kw: client(transport=httpx.MockTransport(
        lambda r: httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": '{"text":""}'}}]})
    ), **kw))
    assert asyncio.run(images.transcribe(png())) == ""
