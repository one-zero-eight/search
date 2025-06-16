import re
from urllib.parse import urlparse

import markdownify
from base import BASE_URL, fetch_html, parse_tilda_table, save_markdown
from bs4 import BeautifulSoup

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
    if not body:
        raise ValueError("Main content container not found.")

    md = markdownify.markdownify(str(body), heading_style="ATX")
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
    # 1. Main catalogue page
    html = fetch_html(PATH)
    save_markdown(html_to_markdown(html), "clubs.md")
    print("✅ clubs.md saved.")

    # 2. Process all sub-pages for individual clubs
    for sub_path in extract_catalogue_links(html):
        try:
            sub_html = fetch_html(sub_path)
            md = html_to_markdown(sub_html)
            filename = sub_path.lstrip("/").replace("/", "_") + ".md"
            save_markdown(md, filename)
            print(f"   └─ ✅ {filename} saved.")
        except Exception as e:
            print(f"   └─ ❌ Error parsing {sub_path}: {e}")
