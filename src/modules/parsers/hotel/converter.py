import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from markdownify import markdownify as md

from src.storages.mongo.hotel import HotelEntrySchema

from .scraper import clean_soup, fetch_html, find_internal_links


def convert_page_to_markdown(url: str):
    """
    Turn rendered HTML into clean Markdown and extract links map.
    """
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    clean_soup(soup)
    selections = {}
    prev_header = None
    for header in soup.find_all("h2"):
        title = header.get_text().strip().upper()
        parent_with_id = header.find_parent(lambda tag: tag.has_attr("id"))
        if title and parent_with_id:
            if prev_header is not None:
                current = selections[prev_header][0].find_next_sibling()
                while current and current != parent_with_id:
                    selections[prev_header].append(current)
                    current = current.find_next_sibling()
            # print(header.get_text(), parent_with_id['id'])
            prev_header = title
            header.decompose()
            selections[prev_header] = [parent_with_id]
    if prev_header is None:  # https://hotel.innopolis.university/zayavkanabronirovanie/
        return
    current = selections[prev_header][0].find_next_sibling()
    while current:
        selections[prev_header].append(current)
        current = current.find_next_sibling()
    for title, block_list in selections.items():
        anchor = block_list[0]["id"]
        new_soup = BeautifulSoup("", "html.parser")
        for element in block_list:
            new_soup.append(element)
        main_md = md(str(new_soup), heading_style="ATX", bullets="*")
        main_md = re.sub(r"•", "\n* ", main_md)
        main_md = re.sub(r"\n{3,}", "\n\n", main_md)
        main_md = re.sub(r" {2,}", " ", main_md)
        main_md = main_md.strip("\n").strip()
        if main_md:
            content_md = f"# {title}\n\n" + main_md
            yield HotelEntrySchema(source_url=url + "#" + anchor, source_page_title=title, content=content_md)


def process_pages(base_url: str, timeout: int):
    """
    Fetch main page and all internal links, save each as .md in out_dir.
    """
    domain = urlparse(base_url).netloc
    html = fetch_html(base_url, timeout)
    soup = BeautifulSoup(html, "html.parser")
    links = find_internal_links(soup, base_url, domain)
    yield from convert_page_to_markdown(base_url)

    for url in links:
        yield from convert_page_to_markdown(url)


if __name__ == "__main__":
    process_pages("https://hotel.innopolis.university/en/contacts/", 10)
