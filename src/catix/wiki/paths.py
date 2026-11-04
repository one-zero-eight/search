"""Where the wiki's data lives: wiki/ (the OKF bundle) and raw/ (what it is made from), under one root.

The root is `settings.wiki_root` (WIKI_ROOT), a checkout of the orphan `wiki` branch that the wiki's own run commits to
(autopilot.py). It is required, and it is never the code's checkout: code and data are separate, the code of `main` reads
and writes the data of `wiki` (a run without WIKI_ROOT wrote its data into the code, and it was committed there).

The bundle is wiki/raw/: the documents, written by code from the sources (regulations, course programmes, eduwiki,
sites, ...).
(The raw/ beside wiki/ is something else: what the sources downloaded, the input of the code that writes wiki/raw/.)
"""

from pathlib import Path

from catix.settings import settings

REPO = Path(__file__).resolve().parents[3]
if settings.wiki_root is None:
    raise RuntimeError("WIKI_ROOT is not set: the wiki's data (wiki/, raw/) lives in a checkout of the `wiki` branch "
                       "(DEPLOY.md, section 2a), never in the code")
DATA = settings.wiki_root.resolve()
if DATA == REPO:
    raise RuntimeError(f"WIKI_ROOT is the code's checkout ({REPO}): the wiki's data lives in a checkout of the `wiki` branch")
BUNDLE = DATA / "wiki"
RAW = DATA / "raw"
DOCS_FOLDER = "raw"  # the bundle's folder of the documents
DOCS = BUNDLE / DOCS_FOLDER
