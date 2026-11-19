"""The Telegram and MAX chats a Moodle course links to (its sections, modules, `url` modules' targets, announcements),
requested for moderation when the course is synced (api/moodle.py put_course_content): once an admin approves, the
userbots join and the chat is seen by the study group of the user whose course it is (source_requests.submit_found)."""
import logging
import re

from catix import groups, source_requests
from catix.db import pg
from catix.moodle_sync import MoodleCourseContentIn

LINK_RE = re.compile(r"(?:https?://)?(?:www\.)?(t\.me|telegram\.me|max\.ru)/([A-Za-z0-9_+-]+(?:/[A-Za-z0-9_-]+)?)", re.ASCII)
MAX_PER_SYNC = 3  # new links requested from one course sync; a course page lists its chat, not dozens
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
                link = source_requests.normalize_link(candidate)
            except (ValueError, AssertionError):
                continue
            if link.startswith("https://t.me/") and not link.startswith("https://t.me/+") and link.lower().endswith("bot"):
                continue
            found.setdefault(link)
    return list(found)


def request_chats(owner: str, email: str, token: str | None, course_id: int, content: MoodleCourseContentIn) -> list[dict]:
    found = links(content)
    if not found:
        return []
    verified = groups.website_groups(token)
    if not verified:
        log.info("moodle course %s: %d chat links, no verified study group: not requested", course_id, len(found))
        return []
    group = verified[0]
    with pg.connection() as conn:
        fullname = pg.scalar(conn, "SELECT fullname FROM moodle_courses WHERE innohassle_id = %s AND course_id = %s",
                             (owner, course_id))
    comment = f"Moodle: {fullname}"
    created: list[dict] = []
    for link in found:
        if len(created) >= MAX_PER_SYNC:
            break
        try:
            row = source_requests.submit_found(owner, email, link, group, comment)
        except ValueError:
            continue
        if row:
            created.append(row)
    for row in created:
        log.info("moodle course %s: requested %s for %s", course_id, row["id"], group)
    return created
