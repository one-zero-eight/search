"""Resolve a cited archive member from existing wiki metadata, then open it on demand.

A preview is pinned to the indexed wiki page's fingerprint and the original
member's full digest. A stale checkout or changed source fails closed.
"""

import hashlib
import json
import re
from pathlib import Path, PurePosixPath

import yaml

from catix.settings import settings

MAX_PAGE_BYTES = 8_000_000


def _inside(root: Path, relative: str) -> Path | None:
    path = PurePosixPath(relative)
    if not relative or path.is_absolute() or path.as_posix() != relative or ".." in path.parts or "\\" in relative or "\x00" in relative:
        return None
    target = (root / relative).resolve()
    return target if target.is_relative_to(root.resolve()) else None


def _metadata(page: str, revision: str, resource: str) -> dict | None:
    if settings.wiki_root is None or not re.fullmatch(r"[0-9a-f]{16}", revision):
        return None
    parts = PurePosixPath(page).parts
    if len(parts) != 4 or parts[:2] != ("/", "raw") or parts[2] not in {"regulations", "course-programmes"} or not page.endswith(".md"):
        return None
    try:
        target = _inside(settings.wiki_root, "wiki/" + page.removeprefix("/"))
        if target is None or not target.is_file() or target.stat().st_size > MAX_PAGE_BYTES:
            return None
        text = target.read_text(encoding="utf-8")
        # Lazy: API startup and ordinary sources need no configured wiki checkout.
        from catix.wiki.compile import front_of
        from catix.wiki.search_index import fingerprint

        if fingerprint(text) != revision:
            return None
        meta = front_of(text)
        if not isinstance(meta, dict) or meta.get("resource") != resource:
            return None
        key = PurePosixPath(page).stem
        entry = _source_entry(settings.wiki_root, parts[2], key, resource)
        if entry is None:
            return None
        member, digest = entry.get("member"), entry.get("sha256")
        if not isinstance(member, str) or not member.lower().endswith(".pdf"):
            return None
        name = PurePosixPath(member)
        if (name.is_absolute() or name.as_posix() != member or ".." in name.parts
                or "\\" in member or ":" in member or any(ord(c) < 32 or ord(c) == 127 for c in member)):
            return None
        if "archive_member" in meta and meta["archive_member"] != member:
            return None
        if parts[2] == "course-programmes":
            # RPD's generated key pins the original path even on legacy pages
            # which have no compiled archive_member field.
            identity = hashlib.sha1(f"{resource}/{member}".encode()).hexdigest()[:8]
            if not key.startswith(f"rpd-{identity}-"):
                return None
        else:
            identity = hashlib.sha256(f"{resource}\n{member}".encode()).hexdigest()[:20]
            if key.rpartition("-member-")[2] != identity:
                return None
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            return None
        sources = meta.get("sources")
        if not isinstance(sources, list) or not any(isinstance(source, dict) and source.get("resource") == resource
                                                   and source.get("id") in (digest, digest[:12]) for source in sources):
            return None
        return {**meta, "archive_member": member, "sha256": digest}
    except (OSError, ValueError, IndexError, yaml.YAMLError):
        return None


def _json(root: Path, relative: str) -> dict:
    target = _inside(root, relative)
    if target is None or not target.is_file() or target.stat().st_size > MAX_PAGE_BYTES:
        return {}
    data = json.loads(target.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _source_entry(root: Path, folder: str, key: str, resource: str) -> dict | None:
    """Look up an exact generated basename in the readers' known metadata roots."""
    if folder == "course-programmes":
        entry = _json(root, "raw/rpd/index.json").get(key)
        return entry if isinstance(entry, dict) and entry.get("archive") == resource else None
    base, separator, _ = key.rpartition("-member-")
    if not separator or not base:
        return None
    candidates = [f"raw/regulations/{base}.archive.json"]
    sites = _inside(root, "raw/sites")
    if sites is not None and sites.is_dir():
        # One directory level only, not all_docs(), a crawler or a recursive scan.
        for count, site in enumerate(sites.iterdir()):
            if count >= 1024:
                return None
            candidates.append(f"raw/sites/{site.name}/docs/{base}.archive.json")
    matches = []
    for relative in candidates:
        manifest = _json(root, relative)
        if manifest.get("url") != resource or manifest.get("status") != "ready":
            continue
        members = manifest.get("members")
        if not isinstance(members, list):
            return None
        for entry in members:
            if (isinstance(entry, dict) and entry.get("key") == key
                    and entry.get("status") == "ready" and entry.get("ext") == "pdf"):
                matches.append(entry)
    return matches[0] if len(matches) == 1 else None


def describe(page: str, revision: str, resource: str) -> dict | None:
    """Public identity, never a local path or an arbitrary archive member URL."""
    meta = _metadata(page, revision, resource)
    return {"page": page, "revision": revision, "member": meta["archive_member"]} if meta else None


def read(page: str, revision: str, resource: str) -> tuple[bytes, str] | None:
    from catix.wiki import preview_cache

    meta = _metadata(page, revision, resource)
    if meta is None:
        return None
    return preview_cache.read(resource, meta["archive_member"], meta["sha256"])
