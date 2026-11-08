"""On-demand archive bytes; real decoder, synthetic university HTTP, no raw PDF cache."""

import hashlib
import io
import zipfile
from contextlib import contextmanager

import httpx
import pytest

from catix.settings import settings
from catix.wiki import previews
from catix.wiki.sources import archive_documents

URL = "https://innopolis.university/documents/programmes.zip"
MEMBER = "2026/Нужная программа.pdf"
PDF = b"%PDF-1.7\ncorrect member\n%%EOF"
SHA = hashlib.sha256(PDF).hexdigest()


def zipped(members):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as output:
        for name, body in members:
            output.writestr(name, body)
    return stream.getvalue()


@pytest.fixture
def remote(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "wiki_root", tmp_path / "readonly-wiki")
    metadata = {"archive_member": MEMBER, "sha256": SHA,
                "archive_preview": {"file": "missing.pdf", "sha256": SHA}}
    monkeypatch.setattr(previews, "_metadata", lambda *args: metadata)
    asked = []
    replies = {URL: httpx.Response(200, content=zipped([("wrong.pdf", b"%PDF-1.7\nwrong"), (MEMBER, PDF)]))}

    def handle(request):
        asked.append(request)
        return replies[str(request.url)]

    @contextmanager
    def stream(method, url, **kwargs):
        with httpx.Client(transport=httpx.MockTransport(handle)) as client:
            with client.stream(method, url, **kwargs) as response:
                yield response

    monkeypatch.setattr(archive_documents.httpx, "stream", stream)
    return metadata, replies, asked


def test_download_archive_then_open_exact_pdf_without_local_original(remote):
    metadata, replies, asked = remote
    found = previews.read("/raw/course-programmes/a.md", "a" * 16, URL)
    assert found == (PDF, "Нужная программа.pdf")
    assert len(asked) == 1 and str(asked[0].url) == URL
    assert "authorization" not in asked[0].headers
    assert not settings.wiki_root.exists()


def test_repeat_open_uses_verified_pdf_cache(remote):
    _, _, asked = remote
    assert previews.read("/raw/course-programmes/a.md", "a" * 16, URL)[0] == PDF
    assert previews.read("/raw/course-programmes/a.md", "a" * 16, URL)[0] == PDF
    assert len(asked) == 1


def test_waiting_for_another_worker_is_bounded(remote, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor, wait
    import fcntl
    from catix.wiki import preview_cache

    root = settings.archive_preview_cache
    root.mkdir(parents=True)
    monkeypatch.setattr(preview_cache, "LOCK_WAIT", 0, raising=False)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with (root / ".lock").open("a+b") as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            future = pool.submit(previews.read, "/raw/course-programmes/a.md", "a" * 16, URL)
            try:
                done, _ = wait([future], timeout=1)
                assert done, "request waited without a deadline"
                with pytest.raises(TimeoutError):
                    future.result()
            finally:
                fcntl.flock(held, fcntl.LOCK_UN)


def test_cache_is_bounded_and_abandoned_work_is_removed(remote, monkeypatch):
    from catix.wiki import preview_cache

    root = settings.archive_preview_cache
    root.mkdir(parents=True)
    old = root / ("0" * 64 + ".pdf")
    old.write_bytes(b"x" * 1000)
    abandoned = root / ".download-interrupted"
    abandoned.mkdir()
    (abandoned / "partial").write_bytes(b"partial")
    monkeypatch.setattr(preview_cache, "MAX_CACHE_BYTES", 500, raising=False)
    assert previews.read("/raw/course-programmes/a.md", "a" * 16, URL)[0] == PDF
    assert not old.exists() and not abandoned.exists()
    assert sum(p.stat().st_size for p in root.iterdir() if p.is_file()) <= 500


def test_concurrent_opens_share_one_download(remote):
    from concurrent.futures import ThreadPoolExecutor
    import threading

    _, _, asked = remote
    start = threading.Barrier(2)

    def open_pdf():
        start.wait(timeout=5)
        return previews.read("/raw/course-programmes/a.md", "a" * 16, URL)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: open_pdf(), range(2)))
    assert results == [(PDF, "Нужная программа.pdf")] * 2
    assert len(asked) == 1


@pytest.mark.parametrize("part", ["pdf", "archive"])
def test_corrupt_cache_never_serves_unverified_bytes(remote, part):
    _, _, asked = remote
    assert previews.read("/raw/course-programmes/a.md", "a" * 16, URL)[0] == PDF
    root = settings.archive_preview_cache
    cached = next(root.glob("*.pdf"))
    cached.write_bytes(b"%PDF-1.7\nwrong cached bytes")
    if part == "archive":
        next(root.glob("*.archive")).write_bytes(b"corrupt")
    assert previews.read("/raw/course-programmes/a.md", "a" * 16, URL)[0] == PDF
    assert len(asked) == (2 if part == "archive" else 1)


def test_new_cited_revision_refreshes_old_archive_cache(remote):
    metadata, replies, asked = remote
    assert previews.read("/raw/course-programmes/a.md", "a" * 16, URL)[0] == PDF
    changed = PDF + b"\nnew revision"
    metadata["sha256"] = hashlib.sha256(changed).hexdigest()
    replies[URL] = httpx.Response(200, content=zipped([(MEMBER, changed)]))
    assert previews.read("/raw/course-programmes/a.md", "b" * 16, URL)[0] == changed
    assert len(asked) == 2


def test_failed_refresh_preserves_previous_complete_cache(remote):
    metadata, replies, asked = remote
    assert previews.read("/raw/course-programmes/a.md", "a" * 16, URL)[0] == PDF
    root = settings.archive_preview_cache
    previous = {p.name: p.read_bytes() for p in root.iterdir() if p.suffix in {".pdf", ".archive"}}
    metadata["sha256"] = "b" * 64
    replies[URL] = httpx.Response(503)
    with pytest.raises(httpx.HTTPStatusError):
        previews.read("/raw/course-programmes/a.md", "b" * 16, URL)
    assert {p.name: p.read_bytes() for p in root.iterdir() if p.suffix in {".pdf", ".archive"}} == previous
    assert not list(root.glob(".download-*"))


def test_redirect_to_private_or_untrusted_host_is_not_followed(remote):
    from catix.wiki.sources.archives import ArchiveError

    _, replies, asked = remote
    replies[URL] = httpx.Response(302, headers={"Location": "http://127.0.0.1/private"})
    with pytest.raises(ArchiveError):
        previews.read("/raw/course-programmes/a.md", "a" * 16, URL)
    assert len(asked) == 1
    assert not list(settings.archive_preview_cache.glob("*.archive"))


def test_archive_download_byte_limit_is_enforced(remote, monkeypatch):
    from catix.wiki.sources import archives

    monkeypatch.setattr(archives, "MAX_ARCHIVE_BYTES", 10)
    with pytest.raises(archives.ArchiveError) as error:
        previews.read("/raw/course-programmes/a.md", "a" * 16, URL)
    assert error.value.status == "limit"
    assert not list(settings.archive_preview_cache.glob(".download-*"))


def test_idle_cache_is_reclaimed(remote):
    import os
    import time
    from catix.wiki import preview_cache

    root = settings.archive_preview_cache
    root.mkdir(parents=True)
    idle = root / ("f" * 64 + ".pdf")
    idle.write_bytes(b"idle")
    expired = time.time() - preview_cache.MAX_IDLE_SECONDS - 1
    os.utime(idle, (expired, expired))
    assert previews.read("/raw/course-programmes/a.md", "a" * 16, URL)[0] == PDF
    assert not idle.exists()


def test_another_member_reuses_downloaded_archive(remote):
    metadata, _, asked = remote
    assert previews.read("/raw/course-programmes/a.md", "a" * 16, URL)[0] == PDF
    other = b"%PDF-1.7\nwrong"
    metadata.update(archive_member="wrong.pdf", sha256=hashlib.sha256(other).hexdigest())
    assert previews.read("/raw/course-programmes/b.md", "b" * 16, URL) == (other, "wrong.pdf")
    assert len(asked) == 1
