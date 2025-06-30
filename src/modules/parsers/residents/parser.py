import os

import requests
from bs4 import BeautifulSoup

from src.storages.mongo.residents import ResidentsEntrySchema

BASE = "https://sez-innopolis.ru"
LIST_URL = f"{BASE}/residents/"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def parse() -> list[ResidentsEntrySchema]:
    response = requests.get(LIST_URL, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    pages_number = soup.find("div", class_="ws512PN")
    max_page = int(pages_number.find_all("a")[-1].text.strip() if pages_number else "1")

    os.makedirs("residents", exist_ok=True)
    index_lines = ["# Residents of Innopolis SEZ\n"]
    result: list[ResidentsEntrySchema] = []

    for page in range(1, max_page + 1):
        url = f"{LIST_URL}ooo-kf-venchurs?PAGEN_1={page}" if page > 1 else f"{LIST_URL}ooo-kf-venchurs"

        response = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.find_all("a", class_="newsSliderItem")

        for i, card in enumerate(cards):
            try:
                name = card.find("span").text.strip()
                href = card["href"]
                slug = href.strip("/").split("/")[-1]
                full_url = BASE + href if href.startswith("/") else href

                response = requests.get(full_url, headers=HEADERS)
                detail = BeautifulSoup(response.text, "html.parser")

                title_tag = detail.find("h1")
                title = title_tag.text.strip() if title_tag else name

                logo_tag = card.find("img")
                logo_url = BASE + logo_tag["src"] if logo_tag and logo_tag.get("src") else ""

                props = detail.select("div.props div")
                contact_info = [f"- {prop.get_text(' ', strip=True)}" for prop in props]

                activity_header = detail.find("h2", string="Сфера деятельности")
                description = activity_header.find_parent("div") if activity_header else None
                description_text = ""
                if description:
                    description_text = description.get_text(separator="\n", strip=True)
                    description_text = "\n".join(description_text.splitlines()[1:])  # Skip the header line

                filename = f"residents/{slug}.md"
                with open(filename, "w", encoding="utf-8") as file:
                    file.write(f"#{title}\n\n")
                    file.write(f"[Go to web-site]({full_url})\n\n")
                    if logo_url:
                        file.write(f"![{title}]({logo_url})\n\n")
                    if description_text:
                        file.write(f"## Field of activity\n{description_text}\n\n")
                    if contact_info:
                        file.write("## Contact Information\n" + "\n".join(contact_info))

                index_lines.append(f"- [{name}]({slug}.md)")

                try:
                    content_parts = []
                    if description_text:
                        content_parts.append(description_text)
                    if contact_info:
                        content_parts.extend(contact_info)

                    content = "\n".join(content_parts)
                    entry = ResidentsEntrySchema(
                        source_page_title=title,
                        content=content,
                        source_url=full_url,
                    )
                    result.append(entry)

                except Exception as e:
                    print(f"Error inserting resident {name} into database: {e}")

            except Exception as e:
                print(f"Error processing resident {i}: {e}")

    with open("residents/index.md", "w", encoding="utf-8") as file:
        file.write("\n".join(index_lines))

    return result
