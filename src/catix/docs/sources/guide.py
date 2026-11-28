"""Source `guide`: catix's own guide (what the assistant, its Telegram bot and the InNoHassle browser extension do), as documents.

The folder `src/catix/docs/guide/` holds one markdown file per topic and language, `<topic>.<lang>.md`: a `# Title` line, then
`##` sections (each becomes a search piece, so each answers one question). The documents are rebuilt from the repo's files, no
network and no table of the crawl; their meta carries no date, so `store.sync` finds an unchanged document by its fingerprint and
leaves it alone at every start of the loop.
"""

import re
from pathlib import Path

from catix.docs.store import PRODUCER, Document

PREFIX = "guide/"
FOLDER = Path(__file__).resolve().parent.parent / "guide"
LINKS = {
    "catix": "https://innohassle.ru/search/ask",
    "telegram": "https://t.me/catlxbot",
    "browser-extension": "https://innohassle.ru/extension",
}
FILE = re.compile(r"^(?P<topic>[a-z-]+)\.(?P<lang>ru|en)\.md$")
TITLE = re.compile(r"^# (.+)$")


def compile_all() -> list[Document]:
    """The guide files as documents (guide/<topic>.<lang>)."""
    documents = []
    for file in sorted(FOLDER.glob("*.md")):
        found = FILE.match(file.name)
        if not found:
            raise ValueError(f"guide file name: {file.name}")
        topic, lang = found["topic"], found["lang"]
        if topic not in LINKS:
            raise ValueError(f"guide topic without a link: {topic}")
        text = file.read_text(encoding="utf-8").strip()
        heading = TITLE.match(text.split("\n", 1)[0])
        if not heading:
            raise ValueError(f"guide file without a # title: {file.name}")
        title = heading[1].strip()
        documents.append(Document(
            path=f"guide/{topic}.{lang}",
            meta={"type": "guide", "title": title, "resource": LINKS[topic], "language": lang,
                  "sources": [{"resource": LINKS[topic], "title": title}],
                  "generated": {"by": f"{PRODUCER} guide"}, "status": "published"},
            body=text + "\n",
        ))
    return documents
