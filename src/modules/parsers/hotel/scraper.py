import sys
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

START_URL = "https://hotel.innopolis.university/"


def fetch_html(url: str, timeout: int = 10) -> str:
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

    for div in soup.find_all(
        "div", class_=lambda x: x and any(c in x.lower() for c in ["landing-footer", "landing-header"])
    ):
        div.decompose()

    # Clean empty headers
    for header in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        text = header.get_text().strip()
        if not text:
            header.decompose()

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

        a["href"] = full

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
    return links
