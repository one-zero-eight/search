import re

import markdownify
from bs4 import BeautifulSoup

from src.storages.mongo.campus_life import CampusLifeEntrySchema

from .base import BASE_URL, fetch_html, parse_tilda_table

PATH = "/handbook2023"


def process_nested_divs(element, indent_level=0):
    """Recursively processes nested divs and formats them into line-by-line strings."""
    content = []

    for child in element.children:
        # Skip technical blocks
        if hasattr(child, "get"):
            class_attr = child.get("class", [])
            if isinstance(class_attr, list) and any("personwrapper" in cls.lower() for cls in class_attr):
                continue

        if child.name == "br":
            content.append("")
            continue

        if child.name == "a" and child.get("href"):
            href = child["href"].strip()
            link_text = child.get_text(strip=True)
            if href and link_text:
                content.append(f"[{link_text}]({href})")
            continue

        if child.name == "div":
            nested = process_nested_divs(child, indent_level)
            if nested:
                content.extend(nested)
            continue

        if child.name is None and isinstance(child, str) and child.strip():
            content.append(child.strip())

    return content


def html_to_markdown(html):
    soup = BeautifulSoup(html, "html.parser")

    # Remove unnecessary elements
    for element in soup.select("header, img"):
        element.decompose()

    # Handle hyperlinks
    for link in soup.find_all("a", href=True):
        href = link["href"].strip()
        if href.startswith("#"):
            link.replace_with(link.get_text(strip=True))
            continue

        if not link.find("table"):
            link_text = link.get_text(strip=True)
            if link_text:
                link.replace_with(f"[{link_text}]({href})")
        else:
            td = link.find("td", {"data-field": "buttontitle"})
            if td:
                link.replace_with(f"[{td.get_text(strip=True)}]({href})")

    # Convert title divs to markdown headings
    for title_div in soup.find_all(
        "div", class_=lambda x: x and any(c in x.lower() for c in ["t-title", "title_xxl", "title_xl", "t-card__title"])
    ):
        text = title_div.get_text(strip=True)
        if text and len(text) < 100:
            level = 2 if "xxl" in title_div.get("class", [""])[0].lower() else 3
            new_tag = soup.new_tag(f"h{level}")
            new_tag.string = text
            title_div.replace_with(new_tag)

    # Remove technical blocks
    for person_wrapper in soup.find_all(class_=lambda x: x and "personwrapper" in x.lower()):
        person_wrapper.decompose()

    # Process structured content sections
    for section in soup.find_all(
        class_=lambda x: x and ("col-wrapper" in x.lower() or "sectioninfowrapper" in x.lower())
    ):
        content_lines = process_nested_divs(section)

        if content_lines:
            # Create markdown-style list with line breaks
            md_content = "- " + "<br>  ".join(content_lines)
            item_container = soup.new_tag("div")
            item_container.string = md_content
            section.replace_with(item_container)
        else:
            section.decompose()

    # Handle Tilda-style tables
    for table_div in soup.find_all("div", class_=lambda x: x and re.match(r"t\d+", x)):
        if md_table := parse_tilda_table(table_div):
            table_html = BeautifulSoup(f'<div class="markdown-table">{md_table}</div>', "html.parser")
            table_div.replace_with(table_html)

    # Final conversion to markdown
    content_div = soup.body
    if not content_div:
        raise ValueError("Main content container not found.")

    md_content = markdownify.markdownify(str(content_div), heading_style="ATX")
    md_content = re.sub(r"\\\|", "|", md_content)
    md_content = re.sub(r"```markdown\n|```", "", md_content)
    md_content = re.sub(r"\n{3,}", "\n\n", md_content)
    return md_content.strip()


def parse() -> CampusLifeEntrySchema:
    html = fetch_html(PATH)
    markdown = html_to_markdown(html)

    return CampusLifeEntrySchema(source_url=BASE_URL + PATH, source_page_title="HANDBOOK2023", content=markdown)
