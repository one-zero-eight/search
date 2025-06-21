from urllib.parse import urlparse

from bs4 import BeautifulSoup
from markdownify import markdownify as md

from src.storages.mongo.hotel import HotelEntrySchema

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


def get_title_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    header_block = soup.find("div", class_=lambda x: x and "landing-block-card-header" in x and "text-uppercase" in x)

    if header_block:
        h2 = header_block.find("h2")
        if h2:
            p = h2.find("p")
            return p.get_text(strip=True) if p else h2.get_text(strip=True)

    return "Untitled Page"


def process_pages(base_url: str, timeout: int):
    """
    Fetch main page and all internal links, save each as .md in out_dir.
    """
    domain = urlparse(base_url).netloc

    html = fetch_html(base_url, timeout)
    main_md, links_map = convert_page_to_markdown(html, base_url, domain)
    page_title = get_title_from_html(html)
    yield HotelEntrySchema(source_url=base_url, source_page_title=page_title, content=main_md)

    for url, fname in links_map.items():
        if fname == "zayavkanabronirovanie.md":
            continue
        html2 = fetch_html(url, timeout)
        md2, _ = convert_page_to_markdown(html2, url, domain)
        page_title = get_title_from_html(html2)
        yield HotelEntrySchema(source_url=url, source_page_title=page_title, content=md2)
