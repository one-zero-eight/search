import re
from urllib.parse import urljoin, urlparse

import markdownify
from bs4 import BeautifulSoup

from src.modules.parsers.campus_life.base import BASE_URL, fetch_html, parse_tilda_table
from src.storages.mongo.campus_life import CampusLifeEntrySchema

PATH = "/clubs"
_CLUB_PATH_RE = re.compile(r"^/[a-z0-9_]+_clubs/?$", re.I)  # pattern: "/something_clubs"


def html_to_markdown(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    # Remove header
    for header in soup.find_all("header"):
        header.decompose()

    # Remove footer
    for footer in soup.find_all("footer"):
        footer.decompose()

    # Remove all images
    for img in soup.find_all("img"):
        img.decompose()

    # Convert links and buttons to Markdown format
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)

        if not text:
            a.decompose()
            continue

        if href.startswith("/"):
            href = urljoin(BASE_URL, href)

        # Handle Tilda button-style links (inside <table>)
        a.replace_with(f"[{text}]({href})")

    # Convert Tilda-style headers to Markdown headers
    for div in soup.find_all(
        "div",
        class_=lambda x: x and any(c in x.lower() for c in ["t-title", "title_xxl", "title_xl"]),
    ):
        text = div.get_text(strip=True)
        if text and len(text) < 100:
            level = 2 if "xxl" in div.get("class", [""])[0].lower() else 3
            header_tag = soup.new_tag(f"h{level}")
            header_tag.string = text
            div.replace_with(header_tag)

    # Convert Tilda tables to Markdown
    for tbl in soup.find_all("div", class_=lambda x: x and re.match(r"t\d+", x)):
        if md_table := parse_tilda_table(tbl):
            tbl.replace_with(BeautifulSoup(f'<div class="markdown-table">{md_table}</div>', "html.parser"))

    # Final conversion to Markdown string
    body = soup.body
    html_to_convert = str(body) if body else str(soup)

    md = markdownify.markdownify(html_to_convert, heading_style="ATX")
    md = re.sub(r"\\\|", "|", md)
    md = re.sub(r"```markdown\n|```", "", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


def extract_catalogue_links(html: str) -> list[str]:
    """
    Extracts all internal paths like "/xxx_clubs" from the Student Clubs Catalogue section.
    """
    soup = BeautifulSoup(html, "html.parser")

    # 1. Find the anchor with name="student_clubs"
    anchor = soup.find(attrs={"name": "student_clubs"})
    if not anchor:
        return []

    links: set[str] = set()

    # 2. Traverse subsequent records until no links are found
    for record in anchor.find_all_next("div", class_="r"):
        for a in record.find_all("a", href=True):
            href = a["href"].strip()

            # Relative or same-domain links only
            if href.startswith("/"):
                path = urlparse(href).path
            elif href.startswith(BASE_URL):
                path = urlparse(href).path
            else:
                continue

            # Filter only paths matching the club pattern
            if _CLUB_PATH_RE.match(path):
                links.add(path.rstrip("/"))

    return sorted(links)


def parse():
    result = list()

    # 1. Main catalogue page
    html = fetch_html(PATH)
    main_md = html_to_markdown(html)
    result.append(
        CampusLifeEntrySchema(source_url=BASE_URL + PATH, source_page_title="Student Clubs Catalogue", content=main_md)
    )

    # 2. Process all sub-pages for individual clubs
    for sub_path in extract_catalogue_links(html):
        try:
            sub_html = fetch_html(sub_path)
            md = html_to_markdown(sub_html)
            filename = sub_path.lstrip("/").replace("/", "_") + ".md"
            title = filename.removesuffix(".md").replace("_", " ").title()

            result.append(CampusLifeEntrySchema(source_url=BASE_URL + sub_path, source_page_title=title, content=md))

            # 3. Find pairs of content-tab1_<n> and content-tab2_<n>
            sub_soup = BeautifulSoup(sub_html, "html.parser")

            tab1_blocks = {}
            tab2_blocks = {}

            # Collect all content-tab1_<n> blocks
            for div in sub_soup.find_all("div", id=re.compile(r"content-tab1_(\d+)", re.I)):
                match = re.search(r"content-tab1_(\d+)", div.get("id", ""))
                if match:
                    tab_number = match.group(1)
                    tab1_blocks[tab_number] = div

            # Collect all content-tab2_<n> blocks
            for div in sub_soup.find_all("div", id=re.compile(r"content-tab2_(\d+)", re.I)):
                match = re.search(r"content-tab2_(\d+)", div.get("id", ""))
                if match:
                    tab_number = match.group(1)
                    tab2_blocks[tab_number] = div

            # 4. Combine pairs and convert to Markdown
            for tab_number in sorted(tab1_blocks.keys()):
                tab1_div = tab1_blocks.get(tab_number)
                tab2_div = tab2_blocks.get(tab_number)

                if not tab2_div:
                    print(f"   └─ ⚠️ Tab2 for club {tab_number} not found, skipping")
                    continue

                combined_html = str(tab1_div) + str(tab2_div)
                combined_md = html_to_markdown(combined_html)

                club_title = f"Club {tab_number}"
                heading_elem = tab1_div.find(class_=lambda x: x and "t-heading" in x.lower())
                if heading_elem:
                    title_text = heading_elem.get_text(strip=True)
                    if title_text:
                        club_title = title_text

                result.append(
                    CampusLifeEntrySchema(
                        source_url=BASE_URL + sub_path + f"#!/tab/{str(tab_number)}-1",
                        source_page_title=club_title,
                        content=combined_md,
                    )
                )

        except Exception as e:
            print(f"   └─ ❌ Error while parsing {sub_path}: {e}")

    return result
