"""Archive containers and their document members. Publish a complete manifest only after safe extraction.

A member's identity is its archive URL and path inside it. Its local revision is content-addressed: changing an archive
never overwrites a queued scan or its extracted text before the new manifest is complete. No OCR lives in this module.
"""

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urljoin

import httpx

from catix.wiki.sources import archives

EXTENSIONS = {"zip", "7z"}


def manifest_path(key: str, doc: dict) -> Path:
    return doc.get("archive_root", doc["root"]) / f"{key}.archive.json"


def load(key: str, doc: dict) -> dict:
    path = manifest_path(key, doc)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save(key: str, doc: dict, data: dict) -> None:
    path = manifest_path(key, doc)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def install(source: Path, destination: Path) -> None:
    """Publish immutable bytes atomically; an interrupted copy is never a readable revision."""
    if destination.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    shutil.copyfile(source, temporary)
    temporary.replace(destination)


def is_archive(key: str, doc: dict) -> bool:
    return not doc.get("member") and not doc.get("archive_root") and (doc.get("ext") in EXTENSIONS or manifest_path(key, doc).exists())


def members(docs: dict[str, dict]) -> dict[str, dict]:
    found = {}
    for key, doc in docs.items():
        if not is_archive(key, doc):
            continue
        data = load(key, doc)
        if item := data.get("document"):
            # Same document and citation, not a synthetic archive member. The
            # boundary still owns download/refresh and immutable local revisions.
            found[key] = {**doc, "root": doc["root"] / item["storage"], "ext": item["ext"],
                          "archive_root": doc["root"], "content_sha": data["sha256"]}
        for item in data.get("members", []):
            if item["status"] != "ready":
                continue
            found[item["key"]] = {**doc, "root": doc["root"] / item["storage"], "ext": item["ext"], "member": item["member"],
                                   "archive_key": key, "title": f"{doc['title']} — {item['member']}", "content_sha": item["sha256"]}
    return found


def document_type(source: Path) -> str | None:
    """Recognize standalone PDFs without admitting HTML or guessing from MIME.

    Validate before replacing a good manifest; a PDF signature alone does not
    make a truncated response a usable document. Other formats stay unsupported.
    """
    from catix.wiki.sources import regulations

    with source.open("rb") as stream:
        header = stream.read(8)
    if not re.match(rb"%PDF-[12]\.\d", header):
        return None
    if source.stat().st_size > regulations.MAX_BYTES:
        raise archives.ArchiveError("limit", "Standalone PDF exceeds the document byte limit")
    try:
        result = subprocess.run(["pdfinfo", str(source)], capture_output=True, timeout=archives.TIMEOUT, check=True)
    except subprocess.TimeoutExpired as error:
        raise archives.ArchiveError("limit", "PDF inspection timed out") from error
    except subprocess.CalledProcessError as error:
        raise archives.ArchiveError("invalid", "Cannot read standalone PDF") from error
    if not re.search(rb"(?m)^Pages:\s+[1-9]\d*\s*$", result.stdout):
        raise archives.ArchiveError("invalid", "Standalone PDF has no pages")
    return "pdf"


def download(url: str, destination: Path) -> dict:
    """A bounded download; redirects must stay on a trusted document provider."""
    from catix.wiki.sources import crawl, regulations

    for _ in range(6):
        if crawl.provider(url) is None:
            raise archives.ArchiveError("unsafe", f"untrusted archive URL: {url}")
        with httpx.stream("GET", url, headers=regulations.HEADERS, timeout=60, follow_redirects=False) as response:
            if response.is_redirect:
                url = urljoin(url, response.headers.get("location", ""))
                continue
            response.raise_for_status()
            declared = response.headers.get("content-length", "")
            if declared.isdigit() and int(declared) > archives.MAX_ARCHIVE_BYTES:
                raise archives.ArchiveError("limit", "archive download exceeds the byte limit")
            size, started = 0, time.monotonic()
            with destination.open("wb") as output:
                for chunk in response.iter_bytes(65536):
                    size += len(chunk)
                    if size > archives.MAX_ARCHIVE_BYTES or time.monotonic() - started > archives.TIMEOUT:
                        raise archives.ArchiveError("limit", "archive download exceeds its byte or time limit")
                    output.write(chunk)
            return regulations.signature(response.headers)
    raise archives.ArchiveError("unsafe", "too many archive redirects")


def prepare(docs: dict[str, dict], prefixes: tuple[str, ...] | None = None) -> list[str]:
    """Download/unpack pending containers. Return removed member keys so deletion-only updates trigger a rebuild."""
    removed = []
    for key, doc in docs.items():
        if not (is_archive(key, doc) or doc.get("archive_root")) or prefixes and not key.startswith(prefixes):
            continue
        doc = {**doc, "root": doc.get("archive_root", doc["root"])}
        old = load(key, doc)
        if old.get("status") == "ready" and not old.get("refetch") and all(
                (doc["root"] / item["storage"] / f"{item['key']}.{item['ext']}").exists()
                for item in [*old.get("members", []), *([old["document"]] if old.get("document") else [])] if item["status"] == "ready"):
            continue
        with tempfile.TemporaryDirectory(prefix="catix-archive-") as work:
            work = Path(work)
            source = work / "source"
            try:
                cached = doc["root"] / old["source"] if old.get("source") else None
                if cached and cached.exists() and not old.get("refetch"):
                    shutil.copyfile(cached, source)
                    remote = old.get("remote", {})
                else:
                    remote = download(doc["url"], source)
                digest = hashlib.sha256(source.read_bytes()).hexdigest()
                ext = document_type(source)
                document = None
                if ext:
                    document = {"key": key, "ext": ext, "storage": f"{key}.documents/{digest}", "status": "ready"}
                    install(source, doc["root"] / document["storage"] / f"{key}.{ext}")
                    entries = []
                else:
                    entries = archives.unpack(source, work / "members")
                for item in entries:
                    item["ext"] = item["ext"].lstrip(".")  # document readers store extensions without the dot
                    if item["status"] != "ready":
                        continue
                    identity = hashlib.sha256(f"{doc['url']}\n{item['member']}".encode()).hexdigest()[:20]
                    item["key"] = f"{key}-member-{identity}"
                    item["storage"] = f"{key}.members/{identity}/{item['sha256']}"
                    folder = doc["root"] / item["storage"]
                    target = folder / f"{item['key']}.{item['ext']}"
                    install(work / "members" / item["file"], target)
                before = {m["key"] for m in old.get("members", []) if m["status"] == "ready"}
                after = {m["key"] for m in entries if m["status"] == "ready"}
                if old.get("document"):
                    before.add(key)
                if document:
                    after.add(key)
                archive_file = f"{key}.archives/{digest}.archive"
                install(source, doc["root"] / archive_file)
                save(key, doc, {"url": doc["url"], "sha256": digest, "source": archive_file, "remote": remote, "status": "ready", "members": entries,
                                **({"document": document} if document else {})})
                removed.extend(sorted(before - after))
                print(f"{key}: archive read, {len(after)} documents, {len(before - after)} removed", flush=True)
            except (archives.ArchiveError, httpx.HTTPError, OSError) as error:
                status = error.status if isinstance(error, archives.ArchiveError) else "unavailable"
                save(key, doc, {**old, "url": doc["url"], "status": status, "error": str(error), "refetch": True})
                print(f"{key}: archive {status}: {error}; previous members kept", flush=True)
    return removed


def refresh(key: str, doc: dict, client: httpx.Client) -> bool:
    """Only the container has a remote version; children never issue HEAD on the archive individually."""
    from catix.wiki.sources import regulations

    data = load(key, doc)
    if not data.get("sha256") or data.get("refetch"):
        return False
    response = client.head(doc["url"])
    if response.status_code != 200:
        return False
    remote = regulations.signature(response.headers)
    changed = regulations.changed(data.get("remote"), remote)
    if changed:
        data["refetch"] = True
    if changed or not data.get("remote"):
        data["remote"] = remote
        save(key, doc, data)
    return changed
