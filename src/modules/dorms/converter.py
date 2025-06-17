import os
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from markdownify import markdownify as md

from .scraper import clean_soup, fetch_html, find_internal_links, sanitize_markdown


def convert_page_to_markdown(html: str, base_url: str, domain: str):
    """
    Turn rendered HTML into clean Markdown and extract links map.
    """
    soup = BeautifulSoup(html, "html.parser")
    clean_soup(soup)
    links_map = find_internal_links(soup, base_url, domain)
    raw = md(str(soup), heading_style="ATX", bullets="*")
    clean = sanitize_markdown(raw)
    return clean, links_map


def process_pages(base_url: str, out_dir: str, timeout: int):
    """
    Fetch main page and all internal links, save each as .md in out_dir.
    """
    os.makedirs(out_dir, exist_ok=True)
    domain = urlparse(base_url).netloc

    # Main page
    html = fetch_html(base_url, timeout)
    main_md, links_map = convert_page_to_markdown(html, base_url, domain)
    main_file = os.path.join(out_dir, "campus_en.md")
    with open(main_file, "w", encoding="utf-8") as f:
        f.write(main_md)

    # Internal pages
    for url, fname in links_map.items():
        html2 = fetch_html(url, timeout)
        md2, _ = convert_page_to_markdown(html2, url, domain)
        out2 = os.path.join(out_dir, fname)
        with open(out2, "w", encoding="utf-8") as f:
            f.write(md2)
