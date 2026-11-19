"""Chat-image OCR is local, conservative, bounded, and cancellation-safe."""
import asyncio
import io
from types import SimpleNamespace

import httpx
import pytest
from PIL import Image

from catix.ingest import images


def png(size=(1200, 800)):
    out = io.BytesIO()
    Image.new("RGB", size, "white").save(out, format="PNG")
    return out.getvalue()


TSV_HEADER = "level\tpage_num\tblock_num\tpar_num\tline_num\tconf\ttext\n"


def tsv(*words):
    return TSV_HEADER + "".join("\t".join(map(str, word)) + "\n" for word in words)


def word(text, confidence=95, *, page=1, block=1, paragraph=1, line=1):
    return (5, page, block, paragraph, line, confidence, text)


class Child:
    def __init__(self, stdout, stderr, code, hanging):
        self.stdout = asyncio.StreamReader()
        self.stderr = asyncio.StreamReader()
        self.stdout.feed_data(stdout)
        self.stderr.feed_data(stderr)
        self.returncode = None if hanging else code
        self.exited = asyncio.Event()
        self.written = bytearray()
        self.closed = False
        self.killed = False
        self.reaped = False
        self.stdin = SimpleNamespace(write=self.written.extend, drain=self.drain, close=self.close)
        if not hanging:
            self.finish(code)

    async def drain(self):
        await asyncio.sleep(0)

    def close(self):
        self.closed = True

    def finish(self, code):
        self.returncode = code
        self.stdout.feed_eof()
        self.stderr.feed_eof()
        self.exited.set()

    def kill(self):
        self.killed = True
        self.finish(-9)

    async def wait(self):
        await self.exited.wait()
        self.reaped = True
        return self.returncode


@pytest.fixture
def ocr_child(monkeypatch):
    children = []

    def forbidden(**kwargs):
        pytest.fail("chat OCR must never use HTTP")

    monkeypatch.setattr(images.httpx, "AsyncClient", forbidden)

    def configure(stdout=TSV_HEADER, *, stderr=b"", code=0, hanging=False, missing=False):
        async def spawn(*args, **kwargs):
            if missing:
                raise FileNotFoundError("private installation path")
            child = Child(stdout.encode() if isinstance(stdout, str) else stdout, stderr, code, hanging)
            children.append(child)
            return child
        monkeypatch.setattr(images.asyncio, "create_subprocess_exec", spawn)
        return children

    return configure


def test_local_ocr_preserves_confident_russian_english_lines(ocr_child):
    ocr_child(tsv(word("Экзамен 12 ноября в 18:30"), word("Аудитория 305", line=2),
                  word("Registration deadline: 10.11.2026", line=3)))
    assert asyncio.run(images.transcribe(png())) == (
        "Экзамен 12 ноября в 18:30\nАудитория 305\nRegistration deadline: 10.11.2026")


@pytest.mark.parametrize("words,expected", [
    ([word("Exam", 89)], ""),
    ([word("Exam", 79), word("registration", 100)], ""),
    ([word("305", 89), word("registration", 100)], ""),
    ([word("Exam", 80), word("registration", 100)], "Exam registration"),
    ([word("Exam", 90), word("305", 90)], "Exam 305"),
    ([word("Экзамен", 90)], "Экзамен"),
    ([(1, 1, 0, 0, 0, -1, ""), (4, 1, 1, 1, 1, -1, "")], ""),
    ([word("...", 100)], ""),
    ([word("", 0), word("Exam", 90)], "Exam"),
])
def test_confidence_accepts_or_skips_whole_image(ocr_child, words, expected):
    ocr_child(tsv(*words))
    assert asyncio.run(images.transcribe(png())) == expected


def test_tsv_preserves_lines_and_structural_breaks():
    assert images._tesseract_text(tsv(
        word("a"), word("b"), word("c", line=2), word("d", paragraph=2),
        word("e", block=2), word("f", page=2),
    )) == "a b\nc\n\nd\n\ne\n\nf"


@pytest.mark.parametrize("value", ["NaN", "inf", "-inf", "oops", -1, 101])
def test_invalid_word_confidence_is_technical_failure(value):
    with pytest.raises(ValueError, match="Invalid Tesseract TSV"):
        images._tesseract_text(tsv(word("private", value)))


@pytest.mark.parametrize("body", [
    "", "text\nprivate\n", TSV_HEADER + "5\t1\n",
    tsv(("x", 1, 1, 1, 1, 95, "private")),
    tsv(word("private", page=0)), tsv(word("private", block=-1)),
    tsv(word("private", line="NaN")), tsv(word("private", paragraph=0)),
    tsv((6, 1, 1, 1, 1, 95, "private")),
    TSV_HEADER + "5\t1\t1\t1\t1\t95\tprivate\textra\n",
])
def test_malformed_tsv_is_technical_failure(body):
    with pytest.raises(ValueError, match="Invalid Tesseract TSV"):
        images._tesseract_text(body)


def test_ocr_text_limit_skips_without_truncating(monkeypatch):
    monkeypatch.setattr(images, "MAX_TEXT", 5)
    assert images._tesseract_text(tsv(word("12345"))) == "12345"
    assert images._tesseract_text(tsv(word("123456"))) == ""


def test_invalid_image_does_not_spawn_tesseract(ocr_child):
    children = ocr_child()
    with pytest.raises((ValueError, OSError)):
        asyncio.run(images.transcribe(b"not an image"))
    assert children == []


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


@pytest.mark.parametrize("options", [
    {"stdout": "not TSV"}, {"stdout": tsv(word("private", "NaN"))},
    {"stdout": b"\xff"}, {"missing": True}, {"code": 1, "stderr": b"private missing language"},
    {"stdout": tsv(word("English")), "stderr": b"Failed loading language 'rus' private"},
    {"stderr": b"private" * 3000, "hanging": True},
])
def test_technical_ocr_failure_retries_without_finish(ocr_child, queue_calls, caplog, options):
    children = ocr_child(**options)
    _, calls = queue_calls
    async def download(job, ref):
        return png()
    assert not asyncio.run(images.process(JOB, download))
    assert calls == [("fail",)]
    assert "private" not in caplog.text
    assert all(child.reaped and child.returncode is not None for child in children)


@pytest.mark.parametrize("overflow", [False, True], ids=["timeout", "stdout-overflow"])
def test_complex_ocr_kills_child_and_finishes_empty(monkeypatch, ocr_child, queue_calls, overflow):
    children = ocr_child(stdout=b"x" * (images.MAX_RESPONSE + 1) if overflow else b"", hanging=True)
    monkeypatch.setattr(images, "TESSERACT_TIMEOUT", 0.01)
    _, calls = queue_calls
    async def download(job, ref):
        return png()
    assert asyncio.run(images.process({**JOB, "image_caption": "Keep caption"}, download))
    assert calls == [("finish", ""), ("publish", [(-100123, 42)])]
    assert children[0].killed and children[0].reaped and children[0].closed


def test_low_confidence_caption_finishes_successfully(ocr_child, queue_calls):
    ocr_child(tsv(word("uncertain", 42)))
    _, calls = queue_calls
    async def download(job, ref):
        return png()
    assert asyncio.run(images.process({**JOB, "image_caption": "Keep caption"}, download))
    assert calls == [("finish", ""), ("publish", [(-100123, 42)])]


def test_album_skips_complex_image_without_renumbering(monkeypatch, ocr_child, queue_calls):
    outputs = iter([tsv(word("Первое")), tsv(word("uncertain", 42)), tsv(word("Third"))])
    _, calls = queue_calls
    async def download(job, ref):
        ocr_child(next(outputs))
        return png()
    assert asyncio.run(images.process({**JOB, "refs": ["first", "complex", "third"]}, download))
    assert calls == [("finish", "[image 1]\nПервое\n\n[image 3]\nThird"), ("publish", [(-100123, 42)])]


def test_technical_second_image_never_finishes_partial_album(ocr_child, queue_calls):
    outputs = iter([tsv(word("Первое")), "invalid private TSV"])
    _, calls = queue_calls
    async def download(job, ref):
        ocr_child(next(outputs))
        return png()
    assert not asyncio.run(images.process({**JOB, "refs": ["first", "broken"]}, download))
    assert calls == [("fail",)]


@pytest.mark.parametrize("during_spawn", [False, True])
def test_cancellation_reaps_child_without_finishing_or_failing(monkeypatch, ocr_child, queue_calls, during_spawn):
    children = ocr_child(hanging=True)
    _, calls = queue_calls
    spawn = images.asyncio.create_subprocess_exec

    async def scenario():
        started = asyncio.Event()
        release = asyncio.Event()
        async def delayed_spawn(*args, **kwargs):
            started.set()
            await release.wait()
            return await spawn(*args, **kwargs)
        if during_spawn:
            monkeypatch.setattr(images.asyncio, "create_subprocess_exec", delayed_spawn)
        async def download(job, ref):
            return png()
        task = asyncio.create_task(images.process(JOB, download))
        if during_spawn:
            await started.wait()
        else:
            while not children or not children[0].written:
                await asyncio.sleep(0)
        task.cancel()
        # Also cancel during cleanup; the child must still be reaped.
        await asyncio.sleep(0)
        task.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(scenario())
    assert calls == []
    assert children[0].killed and children[0].reaped


def test_job_deadline_bounds_ocr_and_reaps_child(monkeypatch, ocr_child, queue_calls):
    children = ocr_child(hanging=True)
    _, calls = queue_calls
    monkeypatch.setattr(images, "JOB_TIMEOUT", 0.05)
    async def download(job, ref):
        return png()
    assert not asyncio.run(images.process(JOB, download))
    assert calls == [("fail",)]
    assert children[0].killed and children[0].reaped


def test_blank_image_is_success_not_failure(ocr_child):
    ocr_child(TSV_HEADER)
    assert asyncio.run(images.transcribe(png())) == ""
