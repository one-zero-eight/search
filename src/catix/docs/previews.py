"""Resolve a cited archive member from the metadata the store keeps for a document, then open it on demand.

A preview is pinned to the indexed document's fingerprint and the original member's full digest: a document that was
rebuilt from another member or digest fails closed.
"""

import re
from pathlib import PurePosixPath

from catix.db.docs import DocHit


def _member(hit: DocHit) -> tuple[str, str] | None:
    if not hit.path.startswith(("regulations/", "course-programmes/")) or not hit.resource:
        return None
    member, digest = hit.archive_member, hit.archive_sha256
    if not isinstance(member, str) or not member.lower().endswith(".pdf"):
        return None
    name = PurePosixPath(member)
    if (name.is_absolute() or name.as_posix() != member or ".." in name.parts
            or "\\" in member or ":" in member or any(ord(c) < 32 or ord(c) == 127 for c in member)):
        return None
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        return None
    return member, digest


def describe(hit: DocHit) -> dict | None:
    """Public identity, never a local path or an arbitrary archive member URL."""
    member = _member(hit)
    return {"page": hit.path, "revision": hit.page_sha, "member": member[0]} if member else None


def read(hit: DocHit) -> tuple[bytes, str] | None:
    from catix.docs import preview_cache

    member = _member(hit)
    return preview_cache.read(hit.resource, *member) if member else None
