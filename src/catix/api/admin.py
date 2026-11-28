"""cAtIx administration on the site (/search/admin): the admins, the Telegram and MAX sources, the chat proposals and the abuse list.

Access is decided here: `AdminDep` (api/auth.py) lets in the admins by InNoHassle id (admins.py) only.
"""

from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel

from catix import abuse, admins, groups, moodle_chats, official, userbot_config
from catix.api.auth import AdminDep, VerifiedDep
from catix.db import pg, store
from catix.maxuserbot import state
from catix.settings import settings

router = APIRouter(prefix="/admin", tags=["Admin"])

Mode = Literal["store", "search", "off"]
REPEATABLE = {"complete", "partial", "failed", "cancelled"}


# ---- me and admins --------------------------------------------------------------------------------------------


class AdminMe(BaseModel):
    innohassle_id: str
    is_admin: bool


class AdminView(BaseModel):
    innohassle_id: str
    email: str | None
    telegram_id: int | None
    fixed: bool
    added_at: datetime | None


class AdminIn(BaseModel):
    innohassle_id: str


@router.get("/me", response_model=AdminMe)
def me(user: VerifiedDep, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    is_admin = admins.is_admin(user.innohassle_id)
    if is_admin:
        admins.seen(user.innohassle_id, user.email, user.telegram_id)
    return AdminMe(innohassle_id=user.innohassle_id, is_admin=is_admin)


def _admin_view(a: admins.Admin) -> AdminView:
    return AdminView(innohassle_id=a.innohassle_id, email=a.email, telegram_id=a.telegram_id, fixed=a.fixed, added_at=a.added_at)


@router.get("/admins", response_model=list[AdminView])
def list_admins(user: AdminDep):
    return [_admin_view(a) for a in admins.listing()]


@router.post("/admins", response_model=AdminView, status_code=201)
def add_admin(body: AdminIn, user: AdminDep):
    innohassle_id = body.innohassle_id.strip().lower()
    if not admins.ID_RE.match(innohassle_id):
        raise HTTPException(422, "invalid_innohassle_id")
    if not admins.add(innohassle_id, user.innohassle_id):
        raise HTTPException(409, "already_admin")
    return next(_admin_view(a) for a in admins.listing() if a.innohassle_id == innohassle_id)


@router.delete("/admins/{innohassle_id}", status_code=204)
def remove_admin(innohassle_id: str, user: AdminDep):
    if innohassle_id == user.innohassle_id:
        raise HTTPException(400, "cannot_remove_self")
    if innohassle_id in admins.configured():
        raise HTTPException(409, "fixed_admin")
    if not admins.remove(innohassle_id):
        raise HTTPException(404, "not_found")
    return Response(status_code=204)


# ---- Telegram chats -------------------------------------------------------------------------------------------


class TelegramChatView(BaseModel):
    chat_id: str
    title: str
    username: str | None
    forum: bool
    bot_only: bool
    bot_in: bool
    listened: bool
    reader: Literal["auto", "userbot", "bot", "search"]
    group_code: str
    official: bool


class TelegramTopicView(BaseModel):
    topic_id: int
    title: str
    closed: bool
    mode: Mode


class TelegramChatDetail(TelegramChatView):
    default_mode: Mode
    topics: list[TelegramTopicView]
    message_count: int


class TelegramChatIn(BaseModel):
    group_code: str
    default_mode: Mode
    topic_modes: dict[int, Mode]
    reader: Literal["auto", "userbot", "bot"]


class Deleted(BaseModel):
    deleted: int


class OfficialIn(BaseModel):
    official: bool


class OfficialView(BaseModel):
    official: bool


def _groups_of(chat_ids: list[int]) -> dict[int, str]:
    with pg.connection() as conn:
        found = conn.execute("SELECT chat_id, group_code FROM chats WHERE chat_id = ANY(%s::bigint[])", (chat_ids,)).fetchall()
    return {r["chat_id"]: r["group_code"] for r in found}


def _telegram_view(d: userbot_config.Dialog, listened: bool, reader: str, group: str, marked: bool) -> dict:
    return {
        "chat_id": str(d.chat_id), "title": d.title, "username": d.username, "forum": bool(d.forum and not d.bot_only),
        "bot_only": d.bot_only, "bot_in": d.bot_in, "listened": listened, "reader": reader, "group_code": group, "official": marked,
    }


@router.get("/groups", response_model=list[str])
def list_groups(user: AdminDep):
    return groups.known_codes()


def _topics(chat_id: int) -> list[userbot_config.Topic]:
    found = userbot_config.topics(chat_id)
    if not any(t.topic_id == store.GENERAL_TOPIC_ID for t in found):
        found = [userbot_config.Topic(store.GENERAL_TOPIC_ID, "General / Общий", False), *found]
    return found


def _telegram_detail(chat_id: int) -> dict:
    dialog = userbot_config.dialog(chat_id)
    if dialog is None:
        raise HTTPException(404, "chat_not_found")
    on = chat_id in userbot_config.listened()
    policy = {"default": "off", "topics": {}} if dialog.bot_only and not on else userbot_config.get_policy(chat_id)
    view = _telegram_view(
        dialog, on, userbot_config.readers().get(chat_id, "auto"),
        _groups_of([chat_id]).get(chat_id, groups.ALL), official.flags([chat_id]).get(chat_id, False),
    )
    topics = []
    if view["forum"]:
        topics = [
            {"topic_id": t.topic_id, "title": t.title, "closed": t.closed, "mode": policy["topics"].get(t.topic_id, policy["default"])}
            for t in _topics(chat_id)
        ]
    return {**view, "default_mode": policy["default"], "topics": topics, "message_count": store.chat_message_count(chat_id)}


@router.get("/telegram/chats/{chat_id}", response_model=TelegramChatDetail)
def telegram_chat(chat_id: int, user: AdminDep):
    return _telegram_detail(chat_id)


@router.put("/telegram/chats/{chat_id}", response_model=TelegramChatDetail)
def save_telegram_chat(chat_id: int, body: TelegramChatIn, user: AdminDep):
    try:
        userbot_config.save_configuration(chat_id, body.group_code, body.default_mode, body.topic_modes, body.reader)
    except ValueError as error:
        raise HTTPException(409, str(error)) from error
    return _telegram_detail(chat_id)


@router.delete("/telegram/chats/{chat_id}/listen", status_code=204)
def disconnect_telegram_chat(chat_id: int, user: AdminDep):
    """Messages stay."""
    if chat_id not in userbot_config.listened():
        raise HTTPException(409, "not_listened")
    userbot_config.set_listen(chat_id, False)
    return Response(status_code=204)


@router.delete("/telegram/chats/{chat_id}/messages", response_model=Deleted)
def clear_telegram_chat(chat_id: int, user: AdminDep):
    if userbot_config.dialog(chat_id) is None:
        raise HTTPException(404, "chat_not_found")
    return {"deleted": store.clear_chat(chat_id)}


@router.post("/telegram/refresh", status_code=202)
def refresh_telegram(user: AdminDep):
    userbot_config.request_refresh()
    return Response(status_code=202)


@router.put("/chats/{chat_id}/official", response_model=OfficialView)
def set_official(chat_id: int, body: OfficialIn, user: AdminDep):
    dialog = userbot_config.dialog(chat_id)
    if dialog is not None:
        store.upsert_chat(dialog.chat_id, dialog.title, dialog.username)  # the chat row holds the mark and may not exist yet
    if not official.set_official(chat_id, body.official):
        raise HTTPException(404, "chat_not_found")
    return {"official": official.flags([chat_id]).get(chat_id, False)}


# ---- MAX ------------------------------------------------------------------------------------------------------


class MaxAccountView(BaseModel):
    online: bool
    catalog_status: str
    catalog_error: str | None


class MaxSourceView(BaseModel):
    chat_id: str
    raw_chat_id: str
    title: str
    group_code: str
    enabled: bool
    access: str
    history_status: str
    catchup_status: str
    last_error: str | None
    legacy_chat_id: str | None
    official: bool
    config_version: int
    generation: int


class ChatListItem(BaseModel):
    platform: Literal["telegram", "max"]
    chat_id: str
    title: str
    group_code: str
    official: bool
    connected: bool  # Telegram: listened; MAX: reading enabled
    forum: bool
    bot_in: bool
    search_only: bool
    raw_chat_id: str | None  # MAX only
    access: str | None  # MAX only
    history_status: str | None  # MAX only


class ChatsView(BaseModel):
    max_account: MaxAccountView
    chats: list[ChatListItem]


class MaxLegacyCandidate(BaseModel):
    chat_id: str
    raw_chat_id: str
    title: str
    message_count: int
    matches_raw_id: bool


class MaxSourceDetail(MaxSourceView):
    message_count: int
    legacy_candidates: list[MaxLegacyCandidate]


class MaxSourceIn(BaseModel):
    group_code: str
    enabled: bool
    legacy_chat_id: str | None = None
    config_version: int
    generation: int


class MaxVersions(BaseModel):
    config_version: int
    generation: int


def _online(account: dict | None) -> bool:
    heartbeat = account.get("heartbeat_at") if account else None
    return isinstance(heartbeat, datetime) and heartbeat.tzinfo is not None and heartbeat >= datetime.now(timezone.utc) - timedelta(seconds=60)


def _max_view(source: dict) -> dict:
    legacy = source.get("legacy_chat_id")
    return {
        "chat_id": str(source["chat_id"]), "raw_chat_id": str(source["raw_chat_id"]), "title": source["title"] or "",
        "group_code": source["group_code"], "enabled": source["enabled"], "access": source["access"],
        "history_status": source["history_status"], "catchup_status": source["catchup_status"], "last_error": source["last_error"],
        "legacy_chat_id": None if legacy is None else str(legacy), "official": bool(source.get("official")),
        "config_version": source["config_version"], "generation": source["generation"],
    }


def _legacy_candidates(chat_id: int, source: dict) -> list[dict]:
    if source.get("legacy_chat_id") is not None:
        return []
    rows = [row for row in state.list_legacy() if row.get("linked_chat_id") in (None, chat_id)]
    rows.sort(key=lambda row: (row["chat_id"] - groups.MAX_CHAT_BASE != source["raw_chat_id"], (row["title"] or "").lower(), row["chat_id"]))
    return [
        {
            "chat_id": str(row["chat_id"]), "raw_chat_id": str(row["chat_id"] - groups.MAX_CHAT_BASE), "title": row["title"] or "",
            "message_count": row["message_count"], "matches_raw_id": row["chat_id"] - groups.MAX_CHAT_BASE == source["raw_chat_id"],
        }
        for row in rows
    ]


def _max_detail(chat_id: int) -> dict:
    source = state.get_source(chat_id)
    if source is None:
        raise HTTPException(404, "source_not_found")
    return {**_max_view(source), "message_count": store.chat_message_count(chat_id), "legacy_candidates": _legacy_candidates(chat_id, source)}


@router.get("/max/{chat_id}", response_model=MaxSourceDetail)
def max_source(chat_id: int, user: AdminDep):
    return _max_detail(chat_id)


def _unavailable() -> HTTPException:
    state.request_catalog()
    return HTTPException(409, "source_unavailable")


@router.put("/max/{chat_id}", response_model=MaxSourceDetail)
def save_max_source(chat_id: int, body: MaxSourceIn, user: AdminDep):
    detail = _max_detail(chat_id)
    legacy = None
    if body.legacy_chat_id is not None:
        if body.legacy_chat_id not in {c["chat_id"] for c in detail["legacy_candidates"]}:
            raise HTTPException(409, "changed")
        legacy = int(body.legacy_chat_id)
    try:
        state.save_configuration(
            chat_id, body.group_code, enabled=body.enabled, expected_version=body.config_version,
            expected_generation=body.generation, legacy_chat_id=legacy,
        )
    except (state.ConfigurationConflict, state.SourceNotFound) as error:
        raise HTTPException(409, "changed") from error
    except state.SourceUnavailable as error:
        raise _unavailable() from error
    except ValueError as error:
        raise HTTPException(422, "invalid_group") from error
    return _max_detail(chat_id)


@router.post("/max/{chat_id}/history", status_code=202)
def retry_max_history(chat_id: int, body: MaxVersions, user: AdminDep):
    source = state.get_source(chat_id)
    if source is None:
        raise HTTPException(404, "source_not_found")
    if not (source["enabled"] and source["access"] == "ready" and source["history_status"] in REPEATABLE):
        raise HTTPException(409, "history_unavailable")
    try:
        state.request_history(chat_id, expected_version=body.config_version, expected_generation=body.generation)
    except (state.ConfigurationConflict, state.SourceNotFound) as error:
        raise HTTPException(409, "changed") from error
    except state.SourceUnavailable as error:
        raise _unavailable() from error
    return Response(status_code=202)


@router.delete("/max/{chat_id}/messages", response_model=Deleted)
def clear_max_messages(chat_id: int, config_version: int, generation: int, user: AdminDep):
    try:
        deleted = state.clear_history(chat_id, expected_version=config_version, expected_generation=generation)
    except (state.ConfigurationConflict, state.SourceNotFound) as error:
        raise HTTPException(409, "changed") from error
    return {"deleted": deleted}


@router.post("/max/refresh", status_code=202)
def refresh_max(user: AdminDep):
    state.request_catalog()
    return Response(status_code=202)


# ---- proposals and abuse --------------------------------------------------------------------------------------


class ProposalView(BaseModel):
    link: str
    owner: str
    course: str
    found_at: datetime
    study_groups: list[str]


class ProposalsView(BaseModel):
    total: int
    items: list[ProposalView]


class AbuseUserView(BaseModel):
    user_key: str
    strikes: int
    pauses: int
    paused_until: datetime | None


class AbuseListView(BaseModel):
    window_hours: int
    warn_at: int
    pause_at: int
    users: list[AbuseUserView]


class AbuseEntryView(BaseModel):
    category: str
    at: datetime
    preview: str


class AbuseDetail(BaseModel):
    user_key: str
    paused_until: datetime | None
    entries: list[AbuseEntryView]


@router.get("/chat-proposals", response_model=ProposalsView)
def chat_proposals(user: AdminDep, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)):
    total, items = moodle_chats.proposals(offset, limit)
    return {"total": total, "items": items}


@router.get("/abuse", response_model=AbuseListView)
def abuse_list(user: AdminDep):
    return {
        "window_hours": settings.abuse_window_hours, "warn_at": settings.abuse_warn_at, "pause_at": settings.abuse_pause_at,
        "users": [{"user_key": u.user_key, "strikes": u.strikes, "pauses": u.pauses, "paused_until": u.paused_until} for u in abuse.offenders()],
    }


@router.get("/abuse/{user_key}", response_model=AbuseDetail)
def abuse_detail(user_key: str, user: AdminDep):
    return {
        "user_key": user_key, "paused_until": abuse.paused_until(user_key),
        "entries": [{"category": e.category, "at": e.at, "preview": e.preview} for e in abuse.recent(user_key, 20)],
    }


@router.delete("/abuse/{user_key}", status_code=204)
def abuse_forgive(user_key: str, user: AdminDep):
    if not abuse.forgive(user_key):
        raise HTTPException(404, "not_found")
    return Response(status_code=204)


# ---- the list of both platforms -------------------------------------------------------------------------------


def _telegram_items() -> list[dict]:
    dialogs = userbot_config.dialogs()
    ids = [d.chat_id for d in dialogs]
    on = userbot_config.listened()
    readers = userbot_config.readers()
    group_of = _groups_of(ids)
    marks = official.flags(ids)
    return [
        {
            "platform": "telegram", "chat_id": str(d.chat_id), "title": d.title, "group_code": group_of.get(d.chat_id, groups.ALL),
            "official": marks.get(d.chat_id, False), "connected": d.chat_id in on, "forum": bool(d.forum and not d.bot_only),
            "bot_in": d.bot_in, "search_only": readers.get(d.chat_id) == "search", "raw_chat_id": None, "access": None,
            "history_status": None,
        }
        for d in dialogs
    ]


def _max_items() -> list[dict]:
    return [
        {
            "platform": "max", "chat_id": str(s["chat_id"]), "title": s["title"] or "", "group_code": s["group_code"],
            "official": bool(s.get("official")), "connected": s["enabled"], "forum": False, "bot_in": False, "search_only": False,
            "raw_chat_id": str(s["raw_chat_id"]), "access": s["access"], "history_status": s["history_status"],
        }
        for s in state.list_sources()
    ]


@router.get("/chats", response_model=ChatsView)
def list_chats(user: AdminDep):
    """Telegram dialogs and MAX sources in one list; the MAX account status goes with it."""
    account = state.get_account()
    return {
        "max_account": {
            "online": _online(account),
            "catalog_status": account.get("catalog_status", "idle") if account else "idle",
            "catalog_error": account.get("catalog_error") if account else None,
        },
        "chats": [*_telegram_items(), *_max_items()],
    }
