"""User-visible chat sources, scoped like the website assistant (not an admin directory)."""
from catix import groups, userbot_config
from catix.db import pg


def website_sources(verified_groups: list[str]) -> list[dict]:
    allowed = {chat_id for chat_id in groups.website_chat_ids(verified_groups) if chat_id < groups.MAX_CHAT_BASE // 2}
    if not allowed:
        return []
    with pg.connection() as conn:
        rows = conn.execute(
            """SELECT c.chat_id, c.title, c.group_code, c.bot_member, d.forum,
                      d.chat_id IS NOT NULL AS userbot_member,
                      l.topic_ids, l.reader, l.topic_policy,
                      EXISTS (SELECT 1 FROM messages m WHERE m.chat_id = c.chat_id) AS has_stored_messages
               FROM chats c LEFT JOIN userbot_listen l USING (chat_id)
               LEFT JOIN userbot_dialogs d USING (chat_id)
               WHERE c.chat_id = ANY(%s::bigint[])
               ORDER BY lower(c.title), c.chat_id""", (sorted(allowed),),
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
            "forum": forum, "default_mode": policy["default"], "topics": topics,
            "has_stored_messages": row["has_stored_messages"],
        })
    return result


def _available_mode(mode: str, can_store: bool, can_search: bool) -> str:
    """Configured capability with known reader membership, not a real-time health claim."""
    if mode == "store" and can_store:
        return "store"
    if mode != "off" and can_search:
        return "search"
    return "off"
