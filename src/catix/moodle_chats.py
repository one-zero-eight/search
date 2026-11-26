"""The Telegram and MAX chats a Moodle course links to (its sections, modules, `url` modules' targets, announcements),
recorded in proposed_chats when the course is synced (api/moodle.py put_course_content), for the admins to look through."""
import logging
import re

from catix import chat_links
from catix.db import pg
from catix.moodle_sync import MoodleCourseContentIn

LINK_RE = re.compile(r"(?:https?://)?(?:www\.)?(t\.me|telegram\.me|max\.ru)/([A-Za-z0-9_+-]+(?:/[A-Za-z0-9_-]+)?)", re.ASCII)
log = logging.getLogger("catix.moodle_chats")


def links(content: MoodleCourseContentIn) -> list[str]:
    texts: list[str] = []
    for section in content.sections:
        texts.append(section.summary_html)
        for module in section.modules:
            texts.append(module.html)
            texts.append(module.external_url or "")
    texts.extend(a.html for a in content.announcements)
    found: dict[str, None] = {}
    for text in texts:
        for m in LINK_RE.finditer(text):
            candidate = f"{'max.ru' if m[1] == 'max.ru' else 't.me'}/{m[2]}"
            try:
                link = chat_links.normalize_link(candidate)
            except (ValueError, AssertionError):
                continue
            if link.startswith("https://t.me/") and not link.startswith("https://t.me/+") and link.lower().endswith("bot"):
                continue
            found.setdefault(link)
    return list(found)


def record_chats(owner: str, course_id: int, content: MoodleCourseContentIn) -> int:
    """Record the chats the course links to in proposed_chats (a link already there keeps its first finder); how many
    were new."""
    found = links(content)
    if not found:
        return 0
    with pg.connection() as conn:
        course = pg.scalar(conn, "SELECT fullname FROM moodle_courses WHERE innohassle_id = %s AND course_id = %s",
                           (owner, course_id)) or ""
        new = sum(conn.execute("INSERT INTO proposed_chats (link, owner, course) VALUES (%s, %s, %s) ON CONFLICT (link) DO NOTHING",
                               (link, owner, course)).rowcount for link in found)
    log.info("moodle course %s: %d chat links, %d new", course_id, len(found), new)
    return new


def connected_links() -> list[str]:
    """The canonical links of the chats already on the admins' list (listened Telegram chats, enabled MAX sources). A
    private invitation cannot be matched to a Telegram chat unless it is the chat's stored link."""
    with pg.connection() as conn:
        telegram = conn.execute(
            "SELECT d.username, c.link FROM userbot_listen l LEFT JOIN userbot_dialogs d ON d.chat_id = l.chat_id "
            "LEFT JOIN chats c ON c.chat_id = l.chat_id").fetchall()
        max_ = conn.execute("SELECT c.link FROM max_sources m JOIN chats c ON c.chat_id = m.chat_id WHERE m.enabled").fetchall()
    candidates: list[str | None] = [f"https://t.me/{row['username']}" if row["username"] else None for row in telegram]
    candidates += [row["link"] for row in telegram] + [row["link"] for row in max_]
    return chat_links.canonical_links(candidates)


def proposals(offset: int, limit: int) -> tuple[int, list[dict]]:
    """(total, the page of proposed chats with their owner's study groups), the newest first, without the chats that are
    already connected. Read-only: nothing here joins a chat."""
    connected = connected_links()
    with pg.connection() as conn:
        total = pg.scalar(conn, "SELECT count(*) FROM proposed_chats WHERE link <> ALL(%s)", (connected,)) or 0
        rows = conn.execute(
            "SELECT p.link, p.owner, p.course, p.found_at, coalesce(a.study_groups, '{}') AS study_groups "
            "FROM proposed_chats p LEFT JOIN moodle_accounts a ON a.innohassle_id = p.owner WHERE p.link <> ALL(%s) "
            "ORDER BY p.found_at DESC, p.link OFFSET %s LIMIT %s",
            (connected, offset, limit),
        ).fetchall()
    return total, [dict(row) for row in rows]
