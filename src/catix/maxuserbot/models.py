"""Native account identities; never compare these IDs with legacy Bot API seq/mid."""

from dataclasses import asdict, dataclass
import re

MAX_USER_CHAT_BASE = 4 * 10**15


class ProtocolError(Exception):
    code = "protocol_error"

    def __init__(self, code: str = "protocol_error"):
        self.code = code
        super().__init__(code)


def normalize_id(value) -> int:
    if isinstance(value, str) and re.fullmatch(r"-?[0-9]+", value, flags=re.ASCII):
        try:
            value = int(value)
        except ValueError:
            raise ProtocolError() from None
    if type(value) is not int or not -(2**63) <= value < 2**63:
        raise ProtocolError()
    return value


def db_chat_id(raw_id: int) -> int:
    raw_id = normalize_id(raw_id)
    if not -10**13 < raw_id < 10**13:
        raise ProtocolError("identity_range")
    return MAX_USER_CHAT_BASE + raw_id


@dataclass(frozen=True)
class PhotoRef:
    photo_id: int


@dataclass(frozen=True)
class MessageSnapshot:
    raw_chat_id: int
    message_id: int
    created_ms: int
    text: str
    sender_id: int | None
    sender_name: str | None
    reply_to: int | None
    photos: tuple[PhotoRef, ...]
    deleted: bool

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_chat(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        raise ProtocolError()
    kind = raw.get("type")
    if kind == "DIALOG":
        return None
    if kind not in {"CHAT", "CHANNEL"}:
        raise ProtocolError()
    raw_id = normalize_id(raw.get("id"))
    db_chat_id(raw_id)
    title, status, link = raw.get("title"), raw.get("status"), raw.get("link")
    if title is not None and not isinstance(title, str):
        raise ProtocolError()
    if not isinstance(status, str) or (link is not None and not isinstance(link, str)):
        raise ProtocolError()
    return {"raw_chat_id": raw_id, "kind": kind.lower(), "title": title or str(raw_id),
            "status": status, "link": link}


def normalize_message(raw: dict, raw_chat_id: int) -> MessageSnapshot | None:
    if not isinstance(raw, dict):
        raise ProtocolError()
    raw_chat_id = normalize_id(raw_chat_id)
    db_chat_id(raw_chat_id)
    if raw.get("postId") is not None:
        return None
    if raw.get("chatId") is not None and normalize_id(raw["chatId"]) != raw_chat_id:
        raise ProtocolError()
    message_id = normalize_id(raw.get("id"))
    deleted = raw.get("status") == "REMOVED"
    created_ms = normalize_id(raw.get("time", 0) if deleted else raw.get("time"))
    if created_ms < 0:
        raise ProtocolError()
    text = raw.get("text", "")
    if not isinstance(text, str):
        raise ProtocolError()
    attaches = raw.get("attaches", [])
    if not isinstance(attaches, list) or any(not isinstance(a, dict) for a in attaches):
        raise ProtocolError()
    photos = tuple(PhotoRef(normalize_id(a.get("photoId"))) for a in attaches if a.get("_type") == "PHOTO")
    for a in attaches:
        if a.get("_type") == "FILE" and isinstance(a.get("name"), str):
            text += f"\n[file: {a['name']}]"
    sender_id = normalize_id(raw["sender"]) if raw.get("sender") is not None else None
    reply_to = None
    link = raw.get("link")
    if link is not None:
        if not isinstance(link, dict):
            raise ProtocolError()
        message = link.get("message", {})
        if not isinstance(message, dict):
            raise ProtocolError()
        if link.get("type") == "REPLY" and message.get("id") is not None:
            reply_to = normalize_id(message["id"])
        elif link.get("type") == "FORWARD" and isinstance(message.get("text"), str):
            text += f"\n[forward: {message['text']}]"
    return MessageSnapshot(raw_chat_id, message_id, created_ms, text, sender_id, None, reply_to, photos, deleted)


def normalize_event(opcode: int, payload: dict) -> dict | None:
    """Notifications retain identities only; content always comes from fresh MSG_GET."""
    if not isinstance(payload, dict):
        raise ProtocolError()
    if payload.get("postId") is not None:
        return None
    if opcode == 135:
        chat = payload.get("chat")
        if not isinstance(chat, dict):
            raise ProtocolError()
        if chat.get("type") == "DIALOG":
            return None
        raw_id = normalize_id(chat.get("id"))
        db_chat_id(raw_id)
        return {"kind": "metadata", "raw_chat_id": raw_id, "status": chat.get("status")}
    raw_id = normalize_id(payload.get("chatId"))
    db_chat_id(raw_id)
    try:
        if opcode in {128, 67}:
            message_id = normalize_id(payload.get("id"))
            return {"kind": "removed" if payload.get("status") == "REMOVED" else "message",
                    "raw_chat_id": raw_id, "message_ids": [message_id]}
        if opcode == 142:
            ids = payload.get("messageIds")
            if not isinstance(ids, list):
                raise ProtocolError()
            return {"kind": "removed", "raw_chat_id": raw_id,
                    "message_ids": [normalize_id(value) for value in ids]}
        if opcode == 140:
            return {"kind": "reconcile_deleted", "raw_chat_id": raw_id}
        raise ProtocolError()
    except ProtocolError:
        return {"kind": "invalid", "raw_chat_id": raw_id}
