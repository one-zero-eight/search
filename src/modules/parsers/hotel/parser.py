import argparse
import sys
from pathlib import Path

from src.modules.parsers.hotel.converter import process_pages

# Base directory of this module (modules/dorms)
BASE_DIR = Path(__file__).parent.resolve()
sys.argv = ["parser.py", "https://hotel.innopolis.university/"]


def parse():
    parser = argparse.ArgumentParser(
        description="Fetch the English Innopolis Campus site and output clean Markdown without images."
    )
    parser.add_argument("url", help="Base URL of the site (e.g., https://hotel.innopolis.university/)")
    parser.add_argument(
        "-o",
        "--output",
        default=str(BASE_DIR / "campus_site"),
        help="Output directory for Markdown files (default: modules/dorms/campus_site)",
    )
    parser.add_argument("-t", "--timeout", type=int, default=10, help="HTTP request timeout in seconds")
    args = parser.parse_args()

    # Ensure we fetch the /en version
    base_url = args.url.rstrip("/")
    if not base_url.endswith("/en"):
        base_url += "/en"

    result = process_pages(base_url, args.timeout)
    return list(result)
