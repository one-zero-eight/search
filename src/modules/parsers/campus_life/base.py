import http.client
import re
import ssl
from urllib.parse import urlparse

from fake_useragent import UserAgent

ua = UserAgent()

context = ssl._create_unverified_context()
BASE_URL = "https://www.campuslife.innopolis.ru"


def fetch_html(path):
    full_url = f"{BASE_URL}{path}"
    parsed_url = urlparse(full_url)  # we get an object with .netloc, .path, etc.
    connection = http.client.HTTPSConnection(parsed_url.netloc, context=context)
    path = parsed_url.path or "/"

    headers = {
        "User-Agent": ua.random,
        "Accept": "text/html",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Host": parsed_url.netloc,
        "Referer": f"http://{parsed_url.netloc}/",
    }

    connection.request("GET", path, headers=headers)
    response = connection.getresponse()

    if response.status != 200:
        raise Exception(f"HTTP Error: {response.status} {response.reason}")

    html = response.read().decode("utf-8")
    connection.close()
    return html


def save_markdown(content, filename):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)


def parse_tilda_table(table_div):
    data_parts = table_div.find_all("div", class_=lambda x: x and re.match(r"t\d+__data-part\d+", x))

    if len(data_parts) < 2:
        return None

    headers = [h.strip() for h in data_parts[0].get_text().split(";") if h.strip()]
    raw_data = data_parts[1].get_text()

    rows = []
    for line in raw_data.strip().split("\n"):
        cols = [col.strip() for col in line.split(";")]
        if any(cols):
            if len(cols) < len(headers):
                cols += [""] * (len(headers) - len(cols))
            elif len(cols) > len(headers):
                cols = cols[: len(headers)]
            rows.append(cols)

    md_res = ""
    for row in rows:
        md_res += f"- {row[0]}\n"
        for i, el in enumerate(row[1:]):
            if el:
                md_res += f"\t- {headers[i + 1]}: {el}\n"

    return md_res
