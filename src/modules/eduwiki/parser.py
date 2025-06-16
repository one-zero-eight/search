from time import sleep
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup, NavigableString
from markdownify import markdownify

START_URL = "https://eduwiki.innopolis.university/index.php/Main_Page"
OUTPUT_FILE = "./src/modules/eduwiki/eduwiki_content.md"
# Ignore everything except the main content of the page.
TARGET_CLASSES = ["mw-body"]
# Exclude redundant content like "table of content" or "From UI"
IGNORE_CLASSES = ["toc", "printfooter", "noprint", "mw-jump-link"]
# Exclude useless endpoints
IGNORE_ENDPOINTS = [
    "/index.php/Structure_of_the_MS_Degrees",
    "/index.php/About_this_document",
    "/index.php/All:Schedule",
    "/index.php/ALL:StudyPlan",
    "/index.php/AcademicCalendar",
]


class EduWikiParser:
    """
    HTML parser for eduwiki.innopolis.university.
    DO NOT use it for other sites, since this impl. is not
    designed for it.
    """

    def __init__(
        self, start_url: str, target_classes: list[str], ignore_classes: list[str], ignore_endpoints: list[str]
    ):
        self.start_url = start_url
        self.domain = urlparse(self.start_url).netloc
        # TODO: allow these lists to be empty
        self.target_classes = target_classes
        self.ignore_classes = ignore_classes
        self.ignore_endpoints = ignore_endpoints
        # Track already visited pages to not repeat them
        self.visited = set()
        # Store every page
        self.parsed_content: list[str] = []

    def crawl(self):
        self.__crawl_page(self.start_url)

    def save_to_file(self, output_file: str):
        with open(output_file, "w", encoding="utf-8") as md_file:
            md_file.write("\n\n".join(self.parsed_content))

    def __crawl_page(self, url: str):
        sleep(0.5)
        if url in self.visited:
            return
        self.visited.add(url)
        print(f"Crawling: {url}")

        try:
            response = httpx.get(url, timeout=2)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # Go to the links
            for a in soup.find_all("a"):
                href = a.get("href")

                if not href:
                    continue

                # Remove fragment since link and link#title are
                # different strings. Need to prevent double parsing
                if "#" in href:
                    href = href.split("#")[0]

                href_parts = urlparse(href)
                # Skip external links, ignored endpoints,
                # and links to the old versions of pages
                if (
                    self.domain == href_parts.netloc
                    and href_parts.path not in self.ignore_endpoints
                    and "oldid" not in href_parts.query
                ):
                    self.__crawl_page(href)

            markdown_content = self.__soup_to_markdown(soup)
            self.parsed_content.append(f"# parsed from: {url}\n{markdown_content}")

        except Exception as e:
            print(f"Failed to process {url}: {e}")

    def __soup_to_markdown(self, soup: BeautifulSoup) -> str:
        res = ""
        for target_class in self.target_classes:
            content_div = soup.find(class_=target_class)
            if not content_div:
                break

            # Remove junk like table of content
            for unwanted in content_div.find_all(class_=self.ignore_classes):
                unwanted.decompose()

            for img in content_div.find_all("img"):
                img.decompose()

            for a in content_div.find_all("a"):
                a.unwrap()

            for table in content_div.find_all("table"):
                md_table: str = self.__html_table_to_md(table)
                table.replace_with(NavigableString(md_table))

            res += markdownify(
                str(content_div), heading_style="ATX", strip=["ul", "ol", "li", "strong", "b", "em", "i"]
            )

        return res

    @staticmethod
    def __html_table_to_md(table) -> str:
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


parser = EduWikiParser(START_URL, TARGET_CLASSES, IGNORE_CLASSES, IGNORE_ENDPOINTS)
parser.crawl()
parser.save_to_file(OUTPUT_FILE)
