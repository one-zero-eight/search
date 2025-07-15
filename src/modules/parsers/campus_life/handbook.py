import re

import markdownify
from bs4 import BeautifulSoup

from src.modules.parsers.campus_life.base import BASE_URL, fetch_html, parse_tilda_table
from src.storages.mongo.campus_life import CampusLifeEntrySchema

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
    result = list()
    soup = BeautifulSoup(html, "html.parser")
    for element in soup.select("header, img"):
        element.decompose()
    for person_wrapper in soup.find_all(class_=lambda x: x and "personwrapper" in x.lower()):
        person_wrapper.decompose()

    for title_div in soup.find_all(
        "div", class_=lambda x: x and any(c in x.lower() for c in ["t-title", "title_xxl", "title_xl", "t-card__title"])
    ):
        text = title_div.get_text(strip=True)
        if text and len(text) < 100:
            class_list = [cls.lower() for cls in title_div.get("class", [])]

            if any("xxl" in cls for cls in class_list):
                level = 2
            elif any("xl" in cls for cls in class_list):
                level = 3
            else:
                level = 3

            title_div.name = f"h{level}"  # Просто меняем имя тега

    # Handle Tilda-style tables
    for table_div in soup.find_all("div", class_=lambda x: x and re.match(r"t\d+", x)):
        if md_list := parse_tilda_table(table_div):
            md_list = md_list.replace("\t", "&nbsp;&nbsp;")
            list_html = BeautifulSoup(f'<div class="markdown-list">\n{md_list}\n</div>', "html.parser")
            table_div.replace_with(list_html)

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

    sections = {}
    # For every link with # anchor
    for link in soup.find_all("a", href=True):
        href = link["href"].strip()

        if href.startswith("#"):
            sections[href[1:]] = link.get_text(strip=True)

    # Each section starts with:
    # <div id="rec210971790" class="r t-rec t-rec_pt_0 t-rec_pb_0" style="padding-top:0px;padding-bottom:0px; " data-record-type="215">
    #   <a name="academic" style="font-size:0;"></a>
    # </div>

    # print(sections)
    pivots = {}
    prev_pivot_name = None
    selections = {}
    for a in soup.find_all("a", attrs={"name": True}):
        name = a["name"]

        if name in sections:
            assert name not in pivots
            pivots[name] = a
            if prev_pivot_name:
                prev_pivot = pivots[prev_pivot_name]
                content = []
                element = prev_pivot.find_next()
                while element and element != a:
                    if any(c == a for c in element.children):
                        break
                    content.append(element)
                    element = element.find_next_sibling()
                selections[prev_pivot_name] = content
            prev_pivot_name = name

    if prev_pivot_name:
        prev_pivot = pivots[prev_pivot_name]
        content = []
        element = prev_pivot.find_next()
        while element:
            content.append(element)
            element = element.find_next_sibling()
        selections[prev_pivot_name] = content
    for section_name, elements in selections.items():
        fragment_html = "".join(str(el) for el in elements)

        md_content = markdownify.markdownify(fragment_html, heading_style="ATX")
        md_content = md_content.replace("\xa0", " ")
        md_content = re.sub(r"\[\s*\|\s*.*?\|\s*\]\(.*?\)", "", md_content, flags=re.DOTALL)

        md_content = md_content.replace("\\|", "|").strip()
        result.append(
            CampusLifeEntrySchema(
                source_url=BASE_URL + PATH + "#" + section_name,
                source_page_title=sections[section_name],
                content=md_content,
            )
        )

    return result


def parse():
    html = fetch_html(PATH)
    result = html_to_markdown(html)

    return result


if __name__ == "__main__":
    parse()
