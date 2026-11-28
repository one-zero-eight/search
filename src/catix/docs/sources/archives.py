"""ZIP/7z containers feed document readers; never extract archive paths.

Decoding runs in a resource-limited child, not the crawler process. Destinations
must not exist; failed attempts remove only the directory this call created.
"""

import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import resource
import shutil
import stat
import zipfile
import subprocess
import sys
import tempfile

MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_FILES = 1000
MAX_MEMBER_BYTES = 100 * 1024 * 1024
MAX_TOTAL_BYTES = 500 * 1024 * 1024
TIMEOUT = 60
MAX_MEMORY_BYTES = 512 * 1024 * 1024
_MAX_RESULT_BYTES = 16 * 1024 * 1024
_LIMITS = ("MAX_ARCHIVE_BYTES", "MAX_FILES", "MAX_MEMBER_BYTES", "MAX_TOTAL_BYTES", "TIMEOUT", "MAX_MEMORY_BYTES")


class ArchiveError(Exception):
    def __init__(self, status: str, message: str):
        super().__init__(message)
        self.status = status


def kind(path: Path) -> str | None:
    """Recognize signatures, excluding Office ZIP packages when readable.

    A damaged/encrypted ZIP still returns ``zip`` so unpack can report why it
    cannot be consumed. Metadata inspection uses the same bounded child.
    """
    detected = _magic(path)
    if detected == "zip":
        try:
            return _run(path, None)
        except ArchiveError:
            pass
    return detected


def _magic(path: Path) -> str | None:
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ArchiveError("unsafe", "Archive input must be a regular file")
    with path.open("rb") as source:
        magic = source.read(6)
    if magic.startswith((b"PK\x03\x04", b"PK\x05\x06")):
        return "zip"
    if magic == b"7z\xbc\xaf\x27\x1c":
        return "7z"
    return None


def unpack(path: Path, destination: Path) -> list[dict]:
    """Return a manifest; supported documents have generated local filenames."""
    try:
        destination.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise ArchiveError("unsafe", "Destination must be new") from exc
    try:
        return _run(path, destination)
    except BaseException:
        shutil.rmtree(destination)
        raise


def _run(path: Path, destination: Path | None):
    if path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ArchiveError("limit", "Compressed archive exceeds limit")
    request = dict(path=str(path.absolute()), destination=str(destination.absolute()) if destination is not None else None, limits={name: globals()[name] for name in _LIMITS})
    # A file, not PIPE: malformed input cannot grow the parent's stdout buffer.
    with tempfile.TemporaryFile() as output:
        try:
            child = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker"], input=json.dumps(request).encode(), stdout=output, stderr=subprocess.DEVNULL, timeout=TIMEOUT, check=False)
        except subprocess.TimeoutExpired as exc:
            raise ArchiveError("limit", "Archive decoder timed out") from exc
        if child.returncode:
            raise ArchiveError("limit" if child.returncode < 0 else "invalid", "Archive decoder failed")
        output.seek(0)
        result = output.read(_MAX_RESULT_BYTES + 1)
    if len(result) > _MAX_RESULT_BYTES:
        raise ArchiveError("limit", "Archive manifest exceeds limit")
    try:
        response = json.loads(result)
    except (ValueError, UnicodeError) as exc:
        raise ArchiveError("invalid", "Invalid decoder response") from exc
    if "error" in response:
        raise ArchiveError(response["error"], "Archive rejected: " + response["error"])
    return response["rows"]


def _member(name: str) -> str:
    # Treat backslashes as separators before checking traversal, even on POSIX.
    if isinstance(name, bytes):  # legacy Windows archives, also handled by the old RPD reader
        for encoding in ("utf-8", "cp866", "cp1251"):
            try:
                name = name.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
    if not isinstance(name, str) or len(name) > 4096 or "\x00" in name:
        raise ArchiveError("unsafe", "Invalid member name")
    name = name.replace("\\", "/")
    parts = name.split("/")
    if name.startswith("/") or ".." in parts or any(":" in part for part in parts):
        raise ArchiveError("unsafe", "Non-relative member name")
    normalized = str(PurePosixPath(name))
    if normalized == ".":
        raise ArchiveError("unsafe", "Empty member name")
    return normalized


def _zip_office(path: Path) -> bool:
    # zipfile exposes Unix types libarchive may coerce (notably FIFO), and
    # requires a complete central directory rather than accepting truncated ZIPs.
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_FILES:
            raise ArchiveError("limit", "Too many ZIP entries")
        names = set()
        for entry in entries:
            member = _member(entry.orig_filename)
            if member in names:
                raise ArchiveError("unsafe", "Duplicate ZIP member")
            names.add(member)
            mode = stat.S_IFMT(entry.external_attr >> 16)
            if entry.create_system == 3 and mode not in {0, stat.S_IFREG, stat.S_IFDIR}:
                raise ArchiveError("unsafe", "Special ZIP entry")
            if entry.is_dir() and entry.file_size:
                raise ArchiveError("unsafe", "Directory has a payload")
            if entry.flag_bits & 1:
                raise ArchiveError("encrypted", "Encrypted ZIP entry")
        return "[Content_Types].xml" in names and any(name.startswith(("word/", "xl/", "ppt/")) for name in names)


def _extract(path: Path, destination: Path) -> list[dict]:
    import libarchive

    detected = _magic(path)
    if detected is None or (detected == "zip" and _zip_office(path)):
        raise ArchiveError("unsupported", "Not a ZIP/7z container")
    rows = []
    total = 0
    seen = set()
    with libarchive.file_reader(str(path), format_name="zip" if detected == "zip" else "7zip", filter_name="none") as source:
        for index, entry in enumerate(source):
            if index >= MAX_FILES:
                raise ArchiveError("limit", "Too many entries")
            member = _member(entry.pathname)
            if member in seen:
                raise ArchiveError("unsafe", "Duplicate member name")
            seen.add(member)
            if entry.issym or entry.islnk or not (entry.isreg or entry.isdir):
                raise ArchiveError("unsafe", "Links and special entries are forbidden")
            if entry.isdir:
                if entry.size or any(entry.get_blocks(64 * 1024)):
                    raise ArchiveError("unsafe", "Directory has a payload")
                continue
            ext = PurePosixPath(member).suffix.lower()
            supported = ext in {".pdf", ".doc", ".docx", ".rtf"}
            filename = f"{index:04d}{ext}" if supported else None
            digest = hashlib.sha256()
            size = 0
            output = (destination / filename).open("xb") if filename else None
            try:
                for block in entry.get_blocks(64 * 1024):
                    size += len(block)
                    total += len(block)
                    if size > MAX_MEMBER_BYTES or total > MAX_TOTAL_BYTES:
                        raise ArchiveError("limit", "Decompressed bytes exceed limit")
                    if output:
                        output.write(block)
                        digest.update(block)
            finally:
                if output:
                    output.close()
            if filename:
                extracted = destination / filename
                nested = _magic(extracted)
                if nested:
                    try:
                        supported = nested == "zip" and ext == ".docx" and _zip_office(extracted)
                    except (ArchiveError, zipfile.BadZipFile):
                        supported = False
                    if not supported:
                        extracted.unlink()
                        filename = None
            rows.append(dict(member=member, file=filename, sha256=digest.hexdigest() if supported else None, size=size, ext=ext, status="ready" if supported else "unsupported"))
    if not rows:
        raise ArchiveError("invalid", "Archive contains no files")
    return rows


def _worker():
    request = json.load(sys.stdin)
    globals().update(request["limits"])
    resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY_BYTES, MAX_MEMORY_BYTES))
    cpu = max(1, math.ceil(TIMEOUT))
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    file_limit = max(MAX_MEMBER_BYTES, _MAX_RESULT_BYTES)
    resource.setrlimit(resource.RLIMIT_FSIZE, (file_limit, file_limit))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    try:
        path = Path(request["path"])
        if request["destination"] is None:
            result = {"rows": None if _zip_office(path) else "zip"}
        else:
            result = {"rows": _extract(path, Path(request["destination"]))}
    except ArchiveError as exc:
        result = {"error": exc.status}
    except MemoryError:
        # Do not allocate a JSON encoder after exhausting address space.
        sys.stdout.write('{"error":"limit"}')
        return
    except Exception as exc:
        message = str(exc).lower()
        if isinstance(exc, OSError) and exc.errno == 12 or any(word in message for word in ("cannot allocate memory", "out of memory", "failed to map segment")):
            result = {"error": "limit"}
        else:
            result = {"error": "encrypted" if any(word in message for word in ("encrypt", "passphrase", "password")) else "invalid"}
    sys.stdout.write(json.dumps(result))


if __name__ == "__main__":
    _worker()
