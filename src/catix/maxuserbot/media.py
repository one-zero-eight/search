"""Refetch native PHOTO attachments without persisting or authenticating CDN URLs."""

from datetime import datetime, timezone

from catix.ingest import image_queue, images

from . import state
from .models import ProtocolError, normalize_id, normalize_message


async def allowed(job: dict) -> bool:
    source = await images.database_call(state.get_source, job["chat_id"])
    return bool(source and source["enabled"] and source["access"] == "ready"
                and source["generation"] == job["generation"]
                and source["raw_chat_id"] == job["raw_chat_id"])


async def download(client, job: dict, ref: str) -> bytes:
    """Validate the entire claimed album/caption before downloading one fresh PHOTO URL."""
    if not await allowed(job):
        raise ValueError("source_unavailable")
    # Legacy URL refs and noncanonical/native identities must never reach the CDN.
    if not isinstance(ref, str) or not ref.startswith("photo:"):
        raise ProtocolError()
    photo_id = normalize_id(ref[6:])
    if ref != f"photo:{photo_id}" or ref not in job["refs"]:
        raise ProtocolError()
    observed_at = datetime.now(timezone.utc)
    rows = await client.messages(job["raw_chat_id"], [job["msg_id"]])
    if not await allowed(job):
        raise ValueError("source_unavailable")
    if not rows:
        # Absence is not an explicit removal; the queue applies its bounded retry policy.
        raise ValueError("message_unavailable")
    if len(rows) != 1:
        raise ProtocolError()
    raw = rows[0]
    snapshot = normalize_message(raw, job["raw_chat_id"])
    if snapshot is None:
        raise ValueError("message_unavailable")
    if snapshot.message_id != job["msg_id"]:
        raise ProtocolError()
    refs = [f"photo:{photo.photo_id}" for photo in snapshot.photos]
    if snapshot.deleted or refs != list(job["refs"]) or snapshot.text != (job["image_caption"] or ""):
        await images.database_call(state.apply_snapshot, job["chat_id"], snapshot.to_dict(),
                                   generation=job["generation"], observed_at=observed_at)
        # A newer live fetch may have won; in either case this old claim cannot finish.
        await images.database_call(image_queue.discard, job)
        raise ValueError("message_changed")
    matching = [attach for attach in raw.get("attaches", [])
                if attach.get("_type") == "PHOTO" and normalize_id(attach.get("photoId")) == photo_id]
    if len(matching) != 1 or not isinstance(matching[0].get("baseUrl"), str):
        raise ProtocolError()
    if not await allowed(job):
        raise ValueError("source_unavailable")
    return await images.download_url(matching[0]["baseUrl"])
