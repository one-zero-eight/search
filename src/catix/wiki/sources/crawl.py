"""Small, code-only crawl helpers shared by site and document collection."""

import re
from urllib.parse import unquote, urlsplit

from catix.wiki.sources import sites

DOCUMENT = re.compile(r"\.(?:pdf|docx?|rtf)$", re.I)
URL = re.compile(r"https?://[^\s<>()\[\]{}\"']+", re.I)
PAGE = re.compile(r"(?<!\!)\[[^\]]*\]\((https?://[^)\s]+)\)", re.I)
TRAILING = ",.;:!?)]}>'"


def _site_hosts(site) -> set[str]:
    return {urlsplit(site.base).hostname or "", *site.aliases}


def provider(url: str) -> str | None:
    """The configured provider name for a safe URL, or None.

    Explicit SITES entries are trusted. A discovered site is trusted only after
    its persisted status becomes ``accepted``; pending sites are deliberately
    excluded even though load_discovered adds them to SITES for safe crawling.
    """
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.port is not None or parts.username or parts.password or not parts.hostname:
        return None
    host = parts.hostname.lower().rstrip(".")
    if any(host == blocked or host.endswith("." + blocked) for blocked in sites.BLOCKED):
        return None
    found = sites.discovered()
    matches = [(name, site, trusted) for name, site in sites.SITES.items()
               for trusted in _site_hosts(site) if host == trusted or host.endswith("." + trusted)]
    for name, site, _ in sorted(matches, key=lambda item: len(item[2]), reverse=True):
        if found.get(host, {}).get("status") == "pending":
            return None
        path = unquote(parts.path).lstrip("/")
        if not DOCUMENT.search(parts.path) and site.skip and re.search(site.skip, path, re.I):
            return None
        return name
    return None


def document_links(text: str, source_url: str) -> list[str]:
    """Canonical trusted document URLs mentioned in extracted material."""
    found = []
    seen = set()
    for raw in URL.findall(text):
        url = raw.rstrip(TRAILING)
        if not DOCUMENT.search(urlsplit(url).path) or provider(url) is None:
            continue
        canonical = sites.canonical(url)
        if canonical != sites.canonical(source_url) and canonical not in seen:
            seen.add(canonical)
            found.append(canonical)
    return found


def page_links(text: str, source_url: str) -> list[str]:
    """Canonical trusted HTML page URLs in a compiled site's markdown."""
    found = []
    seen = set()
    for raw in PAGE.findall(text):
        url = raw.rstrip(TRAILING)
        if DOCUMENT.search(urlsplit(url).path) or provider(url) is None:
            continue
        canonical = sites.canonical(url)
        if canonical != sites.canonical(source_url) and canonical not in seen:
            seen.add(canonical)
            found.append(canonical)
    return found
