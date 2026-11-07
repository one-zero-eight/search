"""Small, code-only crawl helpers shared by site and document collection."""

import re
from urllib.parse import unquote, urlsplit

from catix.wiki.sources import sites

DOCUMENT = sites.DOC
URL = re.compile(r"https?://[^\s<>()\[\]{}\"']+", re.I)
PAGE = re.compile(r"(?<!\!)\[[^\]]*\]\((https?://[^)\s]+)\)", re.I)
TRAILING = ",.;:!?)]}>'"


def _site_hosts(site) -> set[str]:
    return {(urlsplit(site.base).hostname or "").lower().rstrip("."), *(h.lower().rstrip(".") for h in site.aliases)}


def provider(url: str, *, page: bool = False) -> str | None:
    """The configured provider name for a safe URL, or None. Documents may use a provider's subdomains;
    HTML pages require an explicit site/alias and that site's page rules (the same rules as fetch_site).

    SITES contains only the approved raw/sites.yaml catalog, refreshed from disk.
    Pending JSON records may be crawled explicitly, but do not grant provider trust.
    """
    sites.reload_catalog()
    try:
        parts = urlsplit(url)
        if parts.scheme not in ({"http", "https"} if page else {"https"}) or parts.port is not None or parts.username or parts.password or not parts.hostname:
            return None
    except ValueError:
        return None
    host = parts.hostname.lower().rstrip(".")
    if any(host == blocked or host.endswith("." + blocked) for blocked in sites.BLOCKED):
        return None
    found = sites.discovered()
    matches = [(name, site, trusted) for name, site in sites.SITES.items()
               for trusted in _site_hosts(site) if host == trusted or not page and host.endswith("." + trusted)]
    for name, site, _ in sorted(matches, key=lambda item: (len(item[2]), host == urlsplit(item[1].base).hostname), reverse=True):
        primary = (urlsplit(site.base).hostname or "").lower().rstrip(".")
        if any(found.get(candidate, {}).get("status") == "pending" for candidate in (host, primary)):
            return None
        if page:
            return name if sites._taken(site, url) else None
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


def text_page_links(text: str, source_url: str) -> list[str]:
    """Canonical trusted HTML page URLs written out in the text of a document (a regulation's 'see https://...'): its addresses
    stand bare in the text, not as markdown links."""
    found = []
    seen = {sites.canonical(source_url)}
    for raw in URL.findall(text):
        url = raw.rstrip(TRAILING)
        if (name := provider(url, page=True)) is None:
            continue
        if (canonical := sites.page_url(sites.SITES[name], url)) not in seen:
            seen.add(canonical)
            found.append(canonical)
    return found


def page_links(text: str, source_url: str) -> list[str]:
    """Canonical trusted HTML page URLs in a compiled site's markdown."""
    found = []
    seen = set()
    for raw in PAGE.findall(text):
        url = raw.rstrip(TRAILING)
        if (name := provider(url, page=True)) is None:
            continue
        canonical = sites.page_url(sites.SITES[name], url)
        if canonical != sites.canonical(source_url) and canonical not in seen:
            seen.add(canonical)
            found.append(canonical)
    return found
