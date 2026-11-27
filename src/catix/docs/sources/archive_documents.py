"""Archive containers and their document members. Publish a complete manifest only after safe extraction.

A member's identity is its archive URL and path inside it. Its local revision is content-addressed: changing an archive
never overwrites a queued scan or its extracted text before the new manifest is complete. No OCR lives in this module.
"""

import hashlib
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import httpx

from psycopg.types.json import Jsonb

from catix.db import pg
from catix.docs import notes
from catix.docs.sources import archives, hosts

EXTENSIONS = {"zip", "7z"}


def load(key: str) -> dict:
    """The manifest of a container (the table archives): its columns that are set, `document` (a PDF the URL served) and `members`
    (the documents inside); {} when there is none."""
    with pg.connection() as conn:
        row = conn.execute("SELECT url, sha256, remote, status, error, refetch, tried_at, document, members FROM archives WHERE key = %s", (key,)).fetchone()
    if row is None:
        return {}
    data = {k: v for k, v in row.items() if v is not None and k not in ("remote", "refetch", "tried_at")}
    if row["remote"]:
        data["remote"] = row["remote"]
    if row["refetch"]:
        data["refetch"] = True
    if row["tried_at"]:
        data["tried_at"] = row["tried_at"].astimezone(timezone.utc).isoformat(timespec="seconds")
    return data


def exists(key: str) -> bool:
    with pg.connection() as conn:
        return conn.execute("SELECT 1 FROM archives WHERE key = %s", (key,)).fetchone() is not None


def save(key: str, data: dict) -> None:
    with pg.connection() as conn:
        conn.execute(
            """INSERT INTO archives (key, url, sha256, remote, status, error, refetch, tried_at, document, members) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (key) DO UPDATE SET url = excluded.url, sha256 = excluded.sha256, remote = excluded.remote, status = excluded.status, error = excluded.error,
               refetch = excluded.refetch, tried_at = excluded.tried_at, document = excluded.document, members = excluded.members""",
            (key, data["url"], data.get("sha256"), Jsonb(data.get("remote") or {}), data.get("status"), data.get("error"), bool(data.get("refetch")),
             datetime.fromisoformat(data["tried_at"]) if data.get("tried_at") else None, Jsonb(data["document"]) if data.get("document") else None,
             Jsonb(data.get("members", []))))


def install(source: Path, destination: Path) -> None:
    """Put the file where the readers of this run find it (the work folder)."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def is_archive(key: str, doc: dict) -> bool:
    return not doc.get("member") and not doc.get("archived") and (doc.get("ext") in EXTENSIONS or exists(key))


def members(docs: dict[str, dict]) -> dict[str, dict]:
    found = {}
    for key, doc in docs.items():
        if not is_archive(key, doc):
            continue
        data = load(key)
        if item := data.get("document"):
            # Same document and citation, not a synthetic archive member. The
            # boundary still owns download/refresh and the revisions kept by content.
            found[key] = {**doc, "revision": data["sha256"], "ext": item["ext"], "archived": True, "content_sha": data["sha256"]}
        for item in data.get("members", []):
            if item["status"] != "ready":
                continue
            found[item["key"]] = {**doc, "revision": item["sha256"], "ext": item["ext"], "member": item["member"],
                                  "archive_key": key, "title": f"{doc['title']} — {item['member']}", "content_sha": item["sha256"]}
    return found


def document_type(source: Path) -> str | None:
    """Recognize standalone PDFs without admitting HTML or guessing from MIME.

    Validate before replacing a good manifest; a PDF signature alone does not
    make a truncated response a usable document. Other formats stay unsupported.
    """
    from catix.docs.sources import regulations

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
    from catix.docs.sources import crawl, regulations

    for _ in range(6):
        if crawl.provider(url) is None:
            raise archives.ArchiveError("unsafe", f"untrusted archive URL: {url}")
        hosts.turn(url)
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


def settled(item: dict, revision: str, ocr: bool) -> bool:
    """Whether a ready item of a container (its document of that revision) needs no file: its text is read, it was skipped, it is put
    aside as too long, or it is a scan queued and this run reads no scans."""
    from catix.docs.sources.regulations import QUEUED, TOO_LONG

    if notes.has_text(item["key"], revision):
        return True
    note = notes.note(item["key"], revision)
    return "skipped" in note or note.get("ocr") == TOO_LONG or note.get("ocr") == QUEUED and not ocr


def prepare(docs: dict[str, dict], prefixes: tuple[str, ...] | None, work: Path, ocr: bool) -> list[str]:
    """Download/unpack pending containers into `work` (the originals live only there). Return removed member keys so
    deletion-only updates trigger a rebuild. A container that failed (a 404, a host down, one over the limits) is asked again
    after sites.RETRY, not by every run: one over the byte limit was downloaded up to it every few hours. A container whose
    members are all read (or need no file now: `settled`) is not downloaded."""
    from catix.docs.sources import regulations, sites

    removed = []
    for key, doc in docs.items():
        if not (is_archive(key, doc) or doc.get("archived")) or prefixes and not key.startswith(prefixes):
            continue
        old = load(key)
        if old.get("status") not in (None, "ready") and sites.recent(old.get("tried_at")):
            continue
        if old.get("status") == "ready" and not old.get("refetch") and all(
                settled(item, item.get("sha256") or old["sha256"], ocr)
                for item in [*old.get("members", []), *([old["document"]] if old.get("document") else [])] if item["status"] == "ready"):
            continue
        with tempfile.TemporaryDirectory(prefix="catix-docs-") as tmp:
            tmp = Path(tmp)
            source = tmp / "source"
            try:
                remote = download(doc["url"], source)
                digest = hashlib.sha256(source.read_bytes()).hexdigest()
                ext = document_type(source)
                document = None
                if ext:
                    document = {"key": key, "ext": ext, "status": "ready"}
                    install(source, regulations.work_file(work, key, {"revision": digest, "ext": ext}))
                    entries = []
                else:
                    entries = archives.unpack(source, tmp / "members")
                for item in entries:
                    item["ext"] = item["ext"].lstrip(".")  # document readers store extensions without the dot
                    if item["status"] != "ready":
                        continue
                    identity = hashlib.sha256(f"{doc['url']}\n{item['member']}".encode()).hexdigest()[:20]
                    item["key"] = f"{key}-member-{identity}"
                    install(tmp / "members" / item["file"], regulations.work_file(work, item["key"], {"revision": item["sha256"], "ext": item["ext"]}))
                before = {m["key"] for m in old.get("members", []) if m["status"] == "ready"}
                after = {m["key"] for m in entries if m["status"] == "ready"}
                if old.get("document"):
                    before.add(key)
                if document:
                    after.add(key)
                save(key, {"url": doc["url"], "sha256": digest, "remote": remote, "status": "ready", "members": entries,
                                **({"document": document} if document else {})})
                removed.extend(sorted(before - after))
                print(f"{key}: archive read, {len(after)} documents, {len(before - after)} removed", flush=True)
            except (archives.ArchiveError, httpx.HTTPError, OSError) as error:
                status = error.status if isinstance(error, archives.ArchiveError) else "unavailable"
                save(key, {**old, "url": doc["url"], "status": status, "error": str(error), "refetch": True,
                                "tried_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
                print(f"{key}: archive {status}: {error}; previous members kept", flush=True)
    return removed


def refresh(key: str, doc: dict, client: httpx.Client) -> bool:
    """Only the container has a remote version; children never issue HEAD on the archive individually."""
    from catix.docs.sources import regulations

    data = load(key)
    if not data.get("sha256") or data.get("refetch"):
        return False
    hosts.turn(doc["url"])
    response = client.head(doc["url"])
    if response.status_code != 200:
        return False
    remote = regulations.signature(response.headers)
    changed = regulations.changed(data.get("remote"), remote)
    if changed:
        data["refetch"] = True
    if changed or not data.get("remote"):
        data["remote"] = remote
        save(key, data)
    return changed
