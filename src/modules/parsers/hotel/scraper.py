import re
import sys
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


def fetch_html(url: str, timeout: int) -> str:
    """
    Send a GET request and return HTML content.
    """
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        sys.exit(f"Error fetching {url}: {e}")


def clean_soup(soup: BeautifulSoup) -> BeautifulSoup:
    """
    Remove scripts, styles, frames, footers, and images.
    """
    for tag in soup(["script", "style", "noscript", "iframe", "footer", "img"]):
        tag.decompose()
    return soup


def find_internal_links(soup: BeautifulSoup, base_url: str, domain: str) -> dict:
    """
    Rewrite internal <a> tags to local .md files, skip external/PDF links.
    Returns map {full_url: filename.md}.
    """
    links = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith(("mailto:", "tel:", "#")):
            continue
        full = urljoin(base_url, href)
        p = urlparse(full)
        if p.netloc != domain:
            continue
        if p.path.lower().endswith(".pdf"):
            continue
        path = p.path.rstrip("/")
        if path in ("", "/en"):
            continue
        slug = path.lstrip("/").replace("/", "_")
        fname = f"{slug}.md"
        links[full] = fname
        a["href"] = fname
    return links


def sanitize_markdown(text: str) -> str:
    """
    Strip Russian headers, empty lines, and menu lists at start of markdown.
    """
    lines = text.splitlines()
    cleaned = []
    skipping = True
    for line in lines:
        if skipping:
            if not line.strip():
                continue
            if re.search(r"[А-Яа-яЁё]", line):
                continue
            if re.match(r"\s*\*\s*\[.*\]", line):
                continue
            skipping = False
            cleaned.append(line)
        else:
            cleaned.append(line)
    return "\n".join(cleaned)
