"""User-visible Telegram and MAX sources, scoped like the website assistant (not an admin directory)."""
from typing import Literal

from catix import groups, source_requests, userbot_config
from catix.db import pg


def website_sources(verified_groups: list[str]) -> list[dict]:
    allowed = groups.website_chat_ids(verified_groups)
    if not allowed:
        return []
    with pg.connection() as conn:
        rows = conn.execute(
            """SELECT c.chat_id, c.title, c.group_code, c.bot_member, c.link,
                      COALESCE(c.username, d.username) AS username, d.forum,
                      d.chat_id IS NOT NULL AS userbot_member,
                      l.topic_ids, l.reader, l.topic_policy,
                      mx.chat_id IS NOT NULL AS is_max, mx.enabled, mx.access,
                      EXISTS (SELECT 1 FROM messages m WHERE m.chat_id = c.chat_id) AS has_stored_messages
               FROM chats c LEFT JOIN userbot_listen l USING (chat_id)
               LEFT JOIN userbot_dialogs d USING (chat_id)
               LEFT JOIN max_sources mx USING (chat_id)
               WHERE c.chat_id = ANY(%s::bigint[])
                 AND (mx.chat_id IS NOT NULL
                      OR (c.chat_id < %s AND (d.chat_id IS NULL OR d.kind IN ('group', 'channel'))))
               ORDER BY lower(c.title), c.chat_id""", (sorted(allowed), groups.MAX_CHAT_BASE // 2),
        ).fetchall()
        found_topics = conn.execute(
            "SELECT chat_id, topic_id, title FROM userbot_topics WHERE chat_id = ANY(%s::bigint[]) ORDER BY topic_id",
            (sorted(allowed),),
        ).fetchall()
    topic_titles: dict[int, dict[int, str]] = {}
    for topic in found_topics:
        topic_titles.setdefault(topic["chat_id"], {})[topic["topic_id"]] = topic["title"]
    result = []
    for row in rows:
        if row["is_max"]:
            mode = "store" if row["enabled"] and row["access"] == "ready" else "off"
            if mode == "off" and not row["has_stored_messages"]:
                continue
            result.append({
                "chat_id": str(row["chat_id"]), "title": row["title"], "group_code": row["group_code"],
                "platform": "max", "link": _source_link(row["link"], "max"),
                "forum": False, "default_mode": mode, "topics": [],
                "has_stored_messages": row["has_stored_messages"],
            })
            continue
        policy = (userbot_config._policy((row["topic_ids"], row["reader"], row["topic_policy"]))
                  if row["reader"] is not None else {"default": "off", "topics": {}})
        reader = userbot_config.effective_reader(row["reader"], row["userbot_member"]) if row["reader"] else None
        can_store = (reader == "userbot" and row["userbot_member"]) or (reader == "bot" and row["bot_member"])
        policy = {
            "default": _available_mode(policy["default"], can_store, row["userbot_member"]),
            "topics": {t: _available_mode(mode, can_store, row["userbot_member"]) for t, mode in policy["topics"].items()},
        }
        titles = topic_titles.get(row["chat_id"], {})
        forum = bool(row["forum"] or titles or (policy["topics"].keys() - {1}))
        if not forum:
            policy = {"default": policy["topics"].get(1, policy["default"]), "topics": {}}
        if not row["has_stored_messages"] and policy["default"] == "off" and all(mode == "off" for mode in policy["topics"].values()):
            continue
        topics = []
        if forum:
            for topic_id in sorted({1, *titles, *policy["topics"]}):
                topics.append({
                    "topic_id": str(topic_id), "title": titles.get(topic_id, "General" if topic_id == 1 else str(topic_id)),
                    "mode": policy["topics"].get(topic_id, policy["default"]),
                })
        result.append({
            "chat_id": str(row["chat_id"]), "title": row["title"], "group_code": row["group_code"],
            "platform": "telegram",
            "link": _source_link(row["link"], "telegram", username=row["username"]),
            "forum": forum, "default_mode": policy["default"], "topics": topics,
            "has_stored_messages": row["has_stored_messages"],
        })
    return result


def _source_link(link: str | None, platform: Literal["telegram", "max"], *, username: str | None = None) -> str | None:
    """Prefer a public username, otherwise validate a saved HTTPS chat link or invitation."""
    if platform == "telegram" and username:
        try:
            public_name = source_requests.public_username(f"https://t.me/{username}")
        except ValueError:
            public_name = None
        if public_name is not None:
            return f"https://t.me/{public_name}"
    if not isinstance(link, str):
        return None
    if platform == "telegram":
        if not link.startswith("https://t.me/"):
            return None
        try:
            username = source_requests.public_username(link)
            if username is not None:
                return f"https://t.me/{username}"
            return f"https://t.me/+{source_requests.invite_hash(link)}"
        except ValueError:
            return None
    if not link.startswith("https://max.ru/"):
        return None
    match = source_requests.MAX_LINK_RE.fullmatch(link)
    if not match or match[1].lower() in {"join", "joinchat"}:
        return None
    return f"https://max.ru/{match[1]}"


def _available_mode(mode: str, can_store: bool, can_search: bool) -> str:
    """Configured capability with known reader membership, not a real-time health claim."""
    if mode == "store" and can_store:
        return "store"
    if mode != "off" and can_search:
        return "search"
    return "off"
