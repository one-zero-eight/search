"""Where the wiki's data lives: wiki/ (the OKF bundle) and raw/ (what it is made from), under one root.

The root is `settings.wiki_root`, a checkout of the orphan `wiki` branch that the wiki's own run commits to
(autopilot.py); without it, the repository itself (development, tests). Code and data are separate: the code of `main`
reads and writes the data of `wiki`.

The bundle has two owners, and its folders say which:
    wiki/raw/      the documents: written by code from the sources (regulations, course programmes, eduwiki, sites, ...)
                   and never by the model. They are the only evidence: a sentence the model writes cites them.
    wiki/notes/    the model's note on one document (notes.py), beside it, never inside it
    wiki/<other>/  the model's own folders: the knowledge cards (knowledge/) and the folders it makes for the entities the
                   documents name (people/, positions/, units/, ...: agent.py), each declared in wiki/folders.json
(The raw/ beside wiki/ is something else: what the sources downloaded, the input of the code that writes wiki/raw/.)
"""

import json
from pathlib import Path

from catix.settings import settings

REPO = Path(__file__).resolve().parents[3]
DATA = (settings.wiki_root or REPO).resolve()
BUNDLE = DATA / "wiki"
RAW = DATA / "raw"
DOCS_FOLDER = "raw"  # the bundle's folder of the documents
DOCS = BUNDLE / DOCS_FOLDER
NOTES_FOLDER = "notes"
FOLDERS_FILE = "folders.json"  # the model's folders: name -> what it holds (the root index says it)
RESERVED = {DOCS_FOLDER, NOTES_FOLDER, "index", "log"}  # names no folder of the model may take


def is_document(rel: str) -> bool:
    """Whether a bundle path ('/raw/regulations/x.md') is a document: evidence, written by code only."""
    return rel.startswith(f"/{DOCS_FOLDER}/")


def folder_of(rel: str) -> str:
    """The folder a bundle path belongs to: 'regulations' for a document ('/raw/regulations/x.md'), 'people' for
    '/people/x.md'."""
    parts = rel.strip("/").split("/")
    return parts[1] if parts[0] == DOCS_FOLDER and len(parts) > 2 else parts[0]


def model_folders(bundle: Path = BUNDLE) -> dict[str, str]:
    """The folders the model writes cards in, with what each holds (wiki/folders.json); knowledge/ is always one."""
    path = bundle / FOLDERS_FILE
    found = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return {"knowledge": "Knowledge cards: what many documents say on one subject, every sentence cited", **found}


def card_folders(bundle: Path = BUNDLE) -> list[str]:
    """The folders of the model's cards: knowledge/ and the ones it declared. A folder nobody declared (a document folder
    left from before wiki/raw/, a folder a person made in Obsidian) is not the model's."""
    return sorted(model_folders(bundle))


def declare_folder(name: str, about: str, bundle: Path = BUNDLE) -> None:
    """A new folder of the model, with the line the root index says of it."""
    path = bundle / FOLDERS_FILE
    found = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    found[name] = about.strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(sorted(found.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
