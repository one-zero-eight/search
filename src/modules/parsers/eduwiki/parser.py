from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, NavigableString
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
        # Store every page
        self.parsed_content: list[str] = []

    def crawl(self):
        return self.__crawl_page(self.start_url)

    def save_to_file(self, output_file: str):
        with open(output_file, "w", encoding="utf-8") as md_file:
            md_file.write("\n\n".join(self.parsed_content))

    def __crawl_page(self, url: str):
        # sleep(0.5)
        if url in self.visited:
            return
        self.visited.add(url)

        # Uncomment for debug purposes :)
        # print(f"Crawling: {url}")

        try:
            response = httpx.get(url, timeout=2)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # Получаем заголовок страницы
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
                    self.domain == href_parts.netloc
                    and href_parts.path not in self.ignore_endpoints
                    and "oldid" not in href_parts.query
                ):
                    yield from self.__crawl_page(href)

                # Convert links in table of content: #title -> https://domain/page#title
                if href.startswith("#"):
                    a["href"] = urljoin(url, href)

            md_content = self.__soup_to_markdown(soup)
            self.parsed_content.append(self.__enrich_md_content(url, md_content))
            yield EduWikiEntrySchema(source_url=url, source_page_title=source_page_title, content=md_content)

        except Exception as e:
            # Use of specific logger here is overengineering,
            # since the parser is executed really rarely
            print(f"Failed to process {url}: {e}")

    def __soup_to_markdown(self, soup: BeautifulSoup) -> str:
        res = ""
        for target_class in self.target_classes:
            content_div = soup.find(class_=target_class)
            if not content_div:
                continue

            # Remove junk like table of content
            for unwanted in content_div.find_all(class_=self.ignore_classes):
                unwanted.decompose()

            for img in content_div.find_all("img"):
                img.decompose()

            for table in content_div.find_all("table"):
                md_table: str = self.__html_table_to_md(table)
                table.replace_with(NavigableString(md_table))

            res += markdownify(str(content_div), heading_style="ATX")

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

    @staticmethod
    def __enrich_md_content(url: str, md_content: str) -> str:
        """
        Enriches markdown content with metadata
        :param url: url from which md_content was crawled
        :param md_content: parsed page in Markdown format
        :return: Enriched data.
        """
        page_name = urlparse(url).path.split("/")[-1]
        return f'<article source_url="{url}" source_page_name="{page_name}">\n\n{md_content}\n\n<article/>'


def parse():
    parser = EduWikiParser()
    result = list(parser.crawl())
    return result
