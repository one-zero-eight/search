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
