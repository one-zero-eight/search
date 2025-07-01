import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag
from markdownify import markdownify

from src.storages.mongo.edu_wiki import EduWikiEntrySchema

START_URL = "https://eduwiki.innopolis.university/index.php/Main_Page"
OUTPUT_FILE = "./src/modules/eduwiki/eduwiki_content.md"
# Ignore everything except the main content of the page.
TARGET_CLASSES = ["mw-body"]
# Exclude redundant content like "table of content" or "From UI"
IGNORE_CLASSES = ["printfooter", "noprint", "mw-jump-link"]
# Exclude useless endpoints
IGNORE_ENDPOINTS = [
    "/index.php/Structure_of_the_MS_Degrees",
    "/index.php/About_this_document",
    "/index.php/All:Schedule",
    "/index.php/ALL:StudyPlan",
    "/index.php/AcademicCalendar",
    "/index.php/ARTICLE",
]


class EduWikiParser:
    """
    HTML parser for eduwiki.innopolis.university.
    DO NOT use it for other sites, since this impl. is not
    designed for it.
    """

    def __init__(self):
        self.start_url = START_URL
        self.domain = urlparse(self.start_url).netloc
        # TODO: allow these lists to be empty
        self.target_classes = TARGET_CLASSES
        self.ignore_classes = IGNORE_CLASSES
        self.ignore_endpoints = IGNORE_ENDPOINTS
        # Track already visited pages to not repeat them
        self.visited = set()

    def crawl(self):
        return self.crawl_page(self.start_url)

    def save_to_file(self, output_file: str):
        with open(output_file, "w", encoding="utf-8") as md_file:
            md_file.write("\n\n".join(self.parsed_content))

    def crawl_page(self, url: str, log_prefix: str = "", recursive: bool = True):
        # sleep(0.5)
        if url in self.visited:
            return
        self.visited.add(url)
        print(f"{log_prefix}Crawling {url}")

        # Uncomment for debug purposes :)
        # print(f"Crawling: {url}")

        try:
            response = httpx.get(url, timeout=2)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # Get the page title
            heading_element = soup.find(id="firstHeading")
            source_page_title = heading_element.get_text(strip=True) if heading_element else "Untitled"

            # Go to the links
            for a in soup.find_all("a", href=True):
                href = a["href"]

                if not href:
                    continue

                # Remove fragment since link and link#title are
                # different strings. Need to prevent double parsing
                if "#" in href and not href.startswith("#"):
                    href = href.split("#")[0]

                href_parts = urlparse(href)
                # Skip external links, ignored endpoints,
                # and links to the old versions of pages
                if (
                    recursive
                    and self.domain == href_parts.netloc
                    and href_parts.path not in self.ignore_endpoints
                    and "oldid" not in href_parts.query
                ):
                    yield from self.crawl_page(href, log_prefix + " ", recursive=recursive)

                # # Convert links in table of content: #title -> https://domain/page#title
                # if href.startswith("#"):
                #     a["href"] = urljoin(url, href)

            # Extract the table of contents (toc)
            toc = soup.find("div", id="toc", class_="toc")
            if toc:
                sections = {}
                for a in toc.find_all("a", href=True):
                    href = a["href"]
                    if href.startswith("#"):
                        section_id = href[1:]  # убираем #
                        section_name = a.get_text(strip=False)
                        sections[section_id] = section_name
                pivots = {}
                prev_pivot_name = None
                selections = {}

                # Search for all headings with the mw-headline class inside
                for header in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
                    span = header.find("span", class_="mw-headline", id=True)
                    if not span:
                        continue
                    name = span["id"]

                    if name in sections:
                        assert name not in pivots
                        pivots[name] = header
                        if prev_pivot_name:
                            prev_pivot = pivots[prev_pivot_name]
                            content = [prev_pivot]
                            element = prev_pivot.find_next_sibling()
                            while element and element != header:
                                content.append(element)
                                element = element.find_next_sibling()
                            selections[prev_pivot_name] = content
                        prev_pivot_name = name

                # For the last pivot, we collect all the remaining elements
                if prev_pivot_name:
                    prev_pivot = pivots[prev_pivot_name]
                    content = []
                    element = prev_pivot.find_next_sibling()
                    while element:
                        content.append(element)
                        element = element.find_next_sibling()
                    selections[prev_pivot_name] = content

                for section_name, elements in selections.items():
                    new_body = soup.new_tag("div", id="content", class_="mw-body", role="main")
                    for e in elements:
                        new_body.append(e)
                    md_content = self._soup_to_markdown(new_body, is_content_div=True)
                    clean_section_title = re.sub(r"^[\s:.0-9]+", "", sections[section_name])
                    yield EduWikiEntrySchema(
                        source_url=url + "#" + section_name, source_page_title=clean_section_title, content=md_content
                    )

            md_content = self._soup_to_markdown(soup, is_content_div=True)
            yield EduWikiEntrySchema(source_url=url, source_page_title=source_page_title, content=md_content)
        except Exception as e:
            # Use of specific logger here is overengineering,
            # since the parser is executed really rarely
            print(f"Failed to process {url}: {e}")

    def _soup_to_markdown(self, soup: BeautifulSoup | Tag, is_content_div: bool = False) -> str:
        res = ""
        if is_content_div:
            content_div = soup
        else:
            content_div = soup.find(class_="mw-body")
            if not content_div:
                return res

        # Remove junk like table of content
        for unwanted in content_div.find_all(class_=self.ignore_classes):
            unwanted.decompose()

        for img in content_div.find_all("img"):
            img.decompose()

        for table in content_div.find_all("table"):
            md_table: str = self._html_table_to_md(table)
            table.replace_with(NavigableString(md_table))

        res += markdownify(str(content_div), heading_style="ATX")

        return res

    @staticmethod
    def _html_table_to_md(table) -> str:
        rows = table.find_all("tr")
        if not rows:
            return ""

        md_rows = []
        for i, row in enumerate(rows):
            cols = row.find_all(["td", "th"])
            col_texts = [col.get_text(strip=True) for col in cols]
            md_rows.append("| " + " | ".join(col_texts) + " |")
            if i == 0:
                md_rows.append("| " + " | ".join(["---"] * len(cols)) + " |")

        return "\n".join(md_rows) + "\n"


def parse():
    parser = EduWikiParser()
    result = list(parser.crawl())
    return result


if __name__ == "__main__":
    parse()
