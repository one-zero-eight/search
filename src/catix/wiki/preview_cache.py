"""Download public archive originals on demand; never write to the wiki checkout."""

import fcntl
import hashlib
import re
import shutil
import tempfile
import time
from pathlib import Path, PurePosixPath

from catix.settings import settings
from catix.wiki.sources import archive_documents, archives

MAX_PDF_BYTES = 25_000_000
MAX_CACHE_BYTES = 512 * 1024 * 1024
MAX_IDLE_SECONDS = 24 * 60 * 60
LOCK_WAIT = 120


def _pdf(path: Path, digest: str) -> bytes | None:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_PDF_BYTES:
        return None
    with path.open("rb") as source:
        body = source.read(MAX_PDF_BYTES + 1)
    return body if len(body) <= MAX_PDF_BYTES and body.startswith(b"%PDF-") and hashlib.sha256(body).hexdigest() == digest else None


def _member(source: Path, folder: Path, member: str, digest: str) -> bytes | None:
    entries = archives.unpack(source, folder)
    found = next((item for item in entries if item["status"] == "ready" and item["ext"] == ".pdf"
                  and item["member"] == member and item["sha256"] == digest), None)
    if found is None or found["size"] > MAX_PDF_BYTES:
        return None
    return _pdf(folder / found["file"], digest)


def _prune(root: Path) -> None:
    files = []
    for path in root.iterdir():
        if path.name.startswith(".download-"):
            if path.is_symlink():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)  # Only under the exclusive lock: abandoned work, never an active extraction.
        elif re.fullmatch(r"[0-9a-f]{64}\.(pdf|archive)", path.name):
            if path.is_symlink():
                path.unlink()
                continue
            stat = path.stat()
            if time.time() - stat.st_mtime > MAX_IDLE_SECONDS:
                path.unlink()
            else:
                files.append((stat.st_mtime, stat.st_size, path))
    total = sum(size for _, size, _ in files)
    for _, size, path in sorted(files):
        if total <= MAX_CACHE_BYTES:
            break
        path.unlink()
        total -= size


def read(resource: str, member: str, digest: str) -> tuple[bytes, str] | None:
    root = settings.archive_preview_cache
    root.mkdir(parents=True, exist_ok=True)
    # Across threads and API workers: one bounded download/decoder at a time,
    # and no cleaner can remove files another request is reading.
    with (root / ".lock").open("a+b") as lock:
        deadline = time.monotonic() + LOCK_WAIT
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Archive preview is busy") from None
                time.sleep(0.05)
        _prune(root)
        try:
            return _read(root, resource, member, digest)
        finally:
            _prune(root)


def _read(root: Path, resource: str, member: str, digest: str) -> tuple[bytes, str] | None:
    key = hashlib.sha256(f"{resource}\n{member}\n{digest}".encode()).hexdigest()
    cached = root / f"{key}.pdf"
    if body := _pdf(cached, digest):
        cached.touch()
        return body, PurePosixPath(member).name
    with tempfile.TemporaryDirectory(dir=root, prefix=".download-") as temporary:
        work = Path(temporary)
        archive = root / f"{hashlib.sha256(resource.encode()).hexdigest()}.archive"
        body = None
        if not archive.is_symlink() and archive.is_file():
            try:
                body = _member(archive, work / "cached-members", member, digest)
                if body is not None:
                    archive.touch()
            except archives.ArchiveError:
                pass  # A damaged or obsolete cached container may be replaced by a fresh download.
        if body is None:
            source = work / "source.archive"
            archive_documents.download(resource, source)
            body = _member(source, work / "members", member, digest)
            source.replace(archive)  # Only a completely downloaded, safely decoded container is cached.
        if body is not None:
            ready = work / "preview.pdf"
            ready.write_bytes(body)
            ready.replace(cached)
        return (body, PurePosixPath(member).name) if body is not None else None
