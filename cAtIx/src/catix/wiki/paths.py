"""Where the wiki's data lives: wiki/ (the OKF bundle) and raw/ (what it is made from), under one root.

The root is `settings.wiki_root`, a checkout of the orphan `wiki` branch that the wiki's own run commits to
(autopilot.py); without it, the repository itself (development, tests). Code and data are separate: the code of `main`
reads and writes the data of `wiki`.
"""

from pathlib import Path

from catix.settings import settings

REPO = Path(__file__).resolve().parents[3]
DATA = (settings.wiki_root or REPO).resolve()
BUNDLE = DATA / "wiki"
RAW = DATA / "raw"
TOPICS_FILE = RAW / "topics.json"  # the guides proposed and accepted (topics.py): written by the model's run, so data
