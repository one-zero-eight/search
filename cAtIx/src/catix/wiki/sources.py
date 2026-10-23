"""The sources of the wiki: what each one is, how often it is asked, and how it finds out what changed.

A source is code: `update` asks the source what is new or changed since the last time and brings it into raw/ (the
wiki's run then makes pages of it, autopilot.py). It returns how many things changed; 0 means there is nothing to make.
Each source asks in its own way: the eduwiki by revision numbers (one listing), the disclosure section of the site by
its list of documents, the documents already read by what the site says about the file (HEAD: ETag, date, size),
without downloading them.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

from catix.settings import settings
from catix.wiki import fetch, mock, regulations, rpd, sveden


@dataclass(frozen=True)
class Source:
    name: str
    every: timedelta  # how often it is asked
    update: Callable[[], int]  # brings what changed into raw/; the number of changes
    about: str


def _sveden() -> int:
    """New documents of the disclosure section: the listing, the model's decision about the new ones, then the files of
    the kept ones and the course programmes of new archives."""
    changed = sveden.discover()
    sveden.triage()
    return changed + regulations.fetch() + rpd.fetch()


def _files() -> int:
    """Documents already read that changed on the site under the same link; fetch downloads them again."""
    changed = regulations.refresh() + rpd.refresh()
    return changed and regulations.fetch() + rpd.fetch()


SOURCES = [
    Source("eduwiki", timedelta(hours=6), lambda: fetch.fetch([0]), "eduwiki.innopolis.university: pages whose revision changed"),
    Source("sveden", timedelta(days=1), _sveden, "innopolis.university/sveden: documents and course programmes added to the site"),
    Source("files", timedelta(days=7), _files, "documents and archives read before that changed on the site (HEAD, ~1 request every 2 s)"),
]
if settings.wiki_mock_site:  # a stand-in site for showing and testing the run (mock.py)
    SOURCES.append(Source("mock", timedelta(minutes=1), mock.update, f"{settings.wiki_mock_site}: new documents and new versions of them"))
