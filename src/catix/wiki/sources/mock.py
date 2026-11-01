"""A source that is a plain web listing of documents: a stand-in for the university's site, to show and test the wiki's
own run (autopilot.py) on documents one can add and change at will.

    WIKI_MOCK_SITE=http://127.0.0.1:8765/ catix-wiki autopilot --source mock
    uv run python experiments/wiki_demo.py     # the whole story: a new document, then a new version of it

Every PDF or Word file the listing links is a kept document (raw/mock/index.json). From there it goes the same way as a
document of innopolis.university: regulations.fetch downloads and reads it, regulations.refresh asks the site (HEAD)
whether it changed, compile makes its page, the wiki's agent keeps cards on it.
"""

import hashlib
import html
import json
import re
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urljoin

import httpx

from catix.settings import settings
from catix.wiki.paths import RAW

ROOT = RAW / "mock"
INDEX = ROOT / "index.json"
LINK = re.compile(r'href="([^"]+\.(?:pdf|docx?))"', re.I)
PREFIX = "mock-"


def listed() -> list[dict]:
    return json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else []


def discover() -> int:
    """The documents the listing links now; the number added or gone."""
    page = httpx.get(str(settings.wiki_mock_site), timeout=30).text
    docs = [{"url": urljoin(str(settings.wiki_mock_site), html.unescape(m)), "title": unquote(Path(m).stem).replace("_", " ")} for m in LINK.findall(page)]
    before = {d["url"] for d in listed()}
    ROOT.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(docs, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(docs)} documents on the mock site")
    return len(before ^ {d["url"] for d in docs})


def docs() -> dict[str, dict]:
    """The listed documents as regulations.all_docs wants them."""
    out = {}
    for d in listed():
        name = re.sub(r"[^a-z0-9]+", "-", unquote(d["url"].rsplit("/", 1)[-1]).lower()).strip("-")[:30]
        key = PREFIX + hashlib.sha1(d["url"].encode()).hexdigest()[:8] + "-" + (name or "doc")
        out[key] = {"title": d["title"], "url": d["url"], "root": ROOT, "section": "mock", "ext": d["url"].rsplit(".", 1)[-1].lower()}
    return out


def update() -> int:
    """The source's step of the wiki's run: new documents of the listing, documents that changed on it."""
    from catix.wiki.sources import regulations

    return discover() + regulations.refresh(prefix=PREFIX) + regulations.fetch()


def serve(folder: Path, port: int = 8765) -> ThreadingHTTPServer:
    """The mock site: `folder` served with its listing, Last-Modified and Content-Length (what refresh compares)."""
    server = ThreadingHTTPServer(("127.0.0.1", port), partial(SimpleHTTPRequestHandler, directory=str(folder)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
