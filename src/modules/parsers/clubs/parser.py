import requests
import re

from src.storages.mongo.clubs import ClubsEntrySchema

BASE_URL = "https://innohassle.ru/clubs"
API_BASE_URL = "https://api.innohassle.ru"


def escape_md_underscores(text: str) -> str:
    return re.sub(r"_", r"\_", text)


def parse():
    result = []
    response = requests.get(API_BASE_URL + "/clubs/v0/clubs/", verify=False).json()
    all_clubs_content = ''
    art_clubs_content, sport_clubs_content, tech_clubs_content, hobby_clubs_content = '', '', '', ''

    for club in response:
        md_content = f"# {club['title']}\n{club['short_description']}"
        leader = requests.get(API_BASE_URL + "/clubs/v0/leaders/by-club-id/" + club["id"], verify=False).json()

        if leader:
            md_content += f"\n\n**Club leader:** {leader['name']}"
            if leader.get('telegram_alias'):
                alias = escape_md_underscores(leader['telegram_alias'])
                md_content += f" [@{alias}](https://t.me/{alias})"

        for link in club["links"]:
            if link["type"] not in ("telegram_channel", "telegram_chat", "external_url"):
                continue

            link_url = escape_md_underscores(link["link"])

            if link["type"] == "telegram_channel":
                md_content += f"\n\n**Telegram channel:** [see]({link_url})"
            elif link["type"] == "telegram_chat":
                md_content += f"\n\n**Telegram chat:** [join]({link_url})"
            elif link["type"] == "external_url":
                md_content += f"\n\n**Website:** [check]({link_url})"

        result.append(
            ClubsEntrySchema(
                source_url=BASE_URL + f"/{club['slug']}",
                source_page_title=club['title'],
                content=md_content,
            )
        )

        all_clubs_content += md_content + "\n\n"
        if club['type'] == 'hobby':
            hobby_clubs_content += md_content + "\n\n"
        elif club['type'] == 'sport':
            sport_clubs_content += md_content + "\n\n"
        elif club['type'] == 'tech':
            tech_clubs_content += md_content + "\n\n"
        else:
            art_clubs_content += md_content + "\n\n"
    result.append(
        ClubsEntrySchema(
            source_url=BASE_URL,
            source_page_title="List of Innopolis University Clubs",
            content=all_clubs_content,
        )
    )
    result.append(
        ClubsEntrySchema(
            source_url=BASE_URL,
            source_page_title="Sport Clubs",
            content=sport_clubs_content,
        )
    )
    result.append(
        ClubsEntrySchema(
            source_url=BASE_URL,
            source_page_title="Tech Clubs",
            content=tech_clubs_content,
        )
    )
    result.append(
        ClubsEntrySchema(
            source_url=BASE_URL,
            source_page_title="Special Interests Clubs",
            content=hobby_clubs_content,
        )
    )
    result.append(
        ClubsEntrySchema(
            source_url=BASE_URL,
            source_page_title="Art Clubs",
            content=art_clubs_content,
        )
    )
    return result

