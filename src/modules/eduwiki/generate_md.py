from parser import EduWikiParser

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
    "/index.php/ARTICLE"
]

parser = EduWikiParser(START_URL, TARGET_CLASSES, IGNORE_CLASSES, IGNORE_ENDPOINTS)
print("Started crawling")
parser.crawl()
print("Finished crawling")
print("Started writing to file")
parser.save_to_file(OUTPUT_FILE)
print("Finished writing to file")
