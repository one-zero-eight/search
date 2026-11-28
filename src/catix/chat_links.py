"""Canonical Telegram and MAX chat links: private invitations, public usernames, MAX paths."""
import re

INVITE_RE = re.compile(r"(?:https://)?t\.me/(?:\+|joinchat/)([A-Za-z0-9_-]{16,128})", re.ASCII)
PUBLIC_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{3,30}[A-Za-z0-9]", re.ASCII)
MAX_LINK_RE = re.compile(r"(?:https://)?max\.ru/((?:join/)?[A-Za-z0-9_-]{1,128})", re.ASCII)
RESERVED_USERNAMES = frozenset({
    "joinchat", "share", "proxy", "socks", "login", "confirmphone", "setlanguage",
    "addstickers", "addemoji", "addtheme", "bg", "invoice", "giftcode", "addlist",
    "boost", "contact",
})


def invite_hash(link: str) -> str:
    match = INVITE_RE.fullmatch(link)
    if not match:
        raise ValueError("Use a private https://t.me/+… or https://t.me/joinchat/… invitation")
    return match[1]


def public_username(link: str) -> str | None:
    """Return a canonical public username, or None for an accepted private invite."""
    if not isinstance(link, str):
        raise ValueError("Use a Telegram t.me public username or private invitation")
    if INVITE_RE.fullmatch(link):
        return None
    match = re.fullmatch(r"(?:https://)?t\.me/([^/?#]+)", link, re.ASCII)
    if not match:
        raise ValueError("Use a Telegram t.me public username or private invitation")
    username = match[1]
    if not PUBLIC_RE.fullmatch(username) or username.lower() in RESERVED_USERNAMES:
        raise ValueError("Telegram public link must contain a valid, non-reserved username")
    return username.lower()


def normalize_link(link: str) -> str:
    """Validate the entire submitted link and return its canonical HTTPS URL."""
    if isinstance(link, str):
        link = link.strip()
        if match := MAX_LINK_RE.fullmatch(link):
            if match[1] != "join":
                return f"https://max.ru/{match[1]}"
    username = public_username(link)
    if username is not None:
        return f"https://t.me/{username}"
    match = INVITE_RE.fullmatch(link)
    assert match is not None
    return f"https://t.me/+{match[1]}"


def canonical_links(candidates: list[str | None]) -> list[str]:
    """The canonical links of the candidates that are chat links (others are skipped), for matching proposed_chats."""
    links = []
    for candidate in candidates:
        try:
            links.append(normalize_link(candidate or ""))
        except (ValueError, AssertionError):
            continue
    return links
