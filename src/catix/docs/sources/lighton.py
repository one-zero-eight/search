"""OCR of a scanned PDF by LightOnOCR (a 1B vision-language model, served by llama.cpp as `lighton` at settings.ocr_route,
127.0.0.1:9931 on the server, always up): the image of a page in (no prompt), the page's markdown out (headings as '#', tables
as markdown or HTML, pictures as `![image](...)`). The markdown becomes the nodes opendataloader gives for a text layer, and
opendataloader.text_of makes the text of them as it does for one: a block a paragraph, a table as markdown, a paragraph going
on across a page.

The model gives no head or foot of a page apart from its text and no boxes. A picture is not text: its line is left out. An
answer that does not end (the model looping to its token limit) is asked again warmer. The server has one slot of 8192
tokens: a page's image (about 2500 tokens, LONGEST pixels on its longer side) and its answer (MAX_TOKENS) fit in it, so pages
are read one at a time (OCR_PARALLEL=1). A page the server cannot read leaves the document queued for another attempt; no
other OCR engine is used."""

import base64
import io
import re
import subprocess
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from pathlib import Path

import httpx

from catix.settings import settings

METHOD = "ocr (LightOnOCR)"
DPI = 200
LONGEST = 1540  # pixels of the longer side of the image, as the model was trained
MAX_TOKENS = 4096  # (a page is 1-3 thousand; the slot holds 8192 with the image)
TRIES = [(0.0, 0.9), (0.2, 0.9), (0.4, 0.9)]  # (temperature, top_p): greedy, then warmer for an answer that loops
PICTURE = re.compile(r"^\s*!\[[^\]]*\]\([^)]*\)\s*$")
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")
TABLE_RULE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


def available() -> bool:
    """Whether the OCR server answers and serves the model (another model on that port is not it)."""
    if settings.ocr_route is None:
        return False
    try:
        r = httpx.get(f"{str(settings.ocr_route).rstrip('/')}/models", timeout=10)
        r.raise_for_status()
        return any(settings.ocr_model in (m.get("id"), *m.get("aliases", [])) for m in r.json().get("data", []))
    except (httpx.HTTPError, ValueError):
        return False


def image_of(png: Path) -> str:
    """A page's image as the model takes it: the longer side LONGEST pixels; base64 PNG."""
    from PIL import Image

    img = Image.open(png).convert("RGB")
    w, h = img.size
    scale = LONGEST / max(w, h)
    img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def loops(text: str) -> bool:
    """The answer's end standing again and again (10..200 characters, 4 times or more): the model went round in a loop."""
    return any(len(text) >= 4 * n and text.endswith(text[-n:] * 4) for n in range(10, 201))


def read_page(png: Path) -> str:
    """The markdown of a page; an answer cut at the token limit or looping is asked again warmer, the last one kept."""
    content = [{"type": "image_url", "image_url": {"url": "data:image/png;base64," + image_of(png)}}]
    text = ""
    for temperature, top_p in TRIES:
        r = httpx.post(f"{str(settings.ocr_route).rstrip('/')}/chat/completions", timeout=900, json={
            "model": settings.ocr_model, "messages": [{"role": "user", "content": content}], "max_tokens": MAX_TOKENS,
            "temperature": temperature, "top_p": top_p})
        r.raise_for_status()
        choice = r.json()["choices"][0]
        text = choice["message"].get("content") or ""
        if choice.get("finish_reason") != "length" and not loops(text):
            break
    return text


def text_in(tag) -> str:
    """The words of a piece of HTML, a <br> a line break."""
    for br in tag.find_all("br"):
        br.replace_with("\n")
    return tag.get_text("")


def table_node(rows: list[list[str]]) -> dict:
    """A table as opendataloader's: each cell with its row and column on the grid."""
    out = [{"cells": [{"row number": r + 1, "column number": c + 1, "row span": 1, "column span": 1,
                       "kids": [{"type": "paragraph", "content": cell}]} for c, cell in enumerate(row)]} for r, row in enumerate(rows)]
    return {"type": "table", "number of rows": len(rows), "number of columns": max(map(len, rows), default=0), "rows": out}


def html_table_node(table) -> dict:
    """An HTML table as opendataloader's table: each cell with its row and column on the grid, its spans."""
    rows, taken = [], set()
    for r, tr in enumerate(table.find_all("tr")):
        c, cells = 0, []
        for cell in tr.find_all(["td", "th"], recursive=False):
            while (r, c) in taken:
                c += 1
            rs, cs = (int(m.group()) if (m := re.search(r"\d+", str(cell.get(a) or ""))) else 1 for a in ("rowspan", "colspan"))
            rs, cs = max(rs, 1), max(cs, 1)
            taken |= {(i, j) for i in range(r, r + rs) for j in range(c, c + cs)}
            cells.append({"row number": r + 1, "column number": c + 1, "row span": rs, "column span": cs,
                          "kids": [{"type": "paragraph", "content": text_in(cell)}]})
            c += cs
        rows.append({"cells": cells})
    return {"type": "table", "number of rows": len(rows), "number of columns": max((j for _, j in taken), default=-1) + 1, "rows": rows}


def nodes_of(markdown: str) -> list[dict]:
    """A page's markdown as opendataloader's nodes: a '#' line a heading, a block of '|' rows or an HTML <table> a table, the
    other blocks (apart by a blank line) paragraphs; a picture's line is left out."""
    from bs4 import BeautifulSoup

    nodes: list[dict] = []
    for block in re.split(r"\n\s*\n", markdown):
        lines = [line for line in block.splitlines() if line.strip() and not PICTURE.match(line)]
        if not lines:
            continue
        if "<table" in block.lower():
            for table in BeautifulSoup(block, "html.parser").find_all("table"):
                nodes.append(html_table_node(table))
            continue
        words: list[str] = []
        rows: list[list[str]] = []

        def flush() -> None:
            if words:
                nodes.append({"type": "paragraph", "content": "\n".join(words)})
                words.clear()
            if rows:
                nodes.append(table_node(rows[:]))
                rows.clear()

        for line in lines:
            if (heading := re.match(r"\s*#{1,6}\s+(.*\S)", line)):
                flush()
                nodes.append({"type": "heading", "content": heading.group(1).strip()})
            elif TABLE_ROW.match(line):
                if words:
                    flush()
                if not TABLE_RULE.match(line):
                    rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
            else:
                if rows:
                    flush()
                words.append(line.strip())
        flush()
    return nodes


_pages: ThreadPoolExecutor | None = None
_pages_lock = threading.Lock()


def page_pool() -> ThreadPoolExecutor:
    """The pages being read, of every scan the process reads at once: as many as the server has slots (OCR_PARALLEL)."""
    global _pages
    with _pages_lock:
        if _pages is None:
            _pages = ThreadPoolExecutor(settings.ocr_parallel, thread_name_prefix="lighton-page")
        return _pages


def cancel_pages() -> None:
    """The pages waiting in page_pool not read (a stopped run): those being read end, the next page_pool is a new one."""
    global _pages
    with _pages_lock:
        if _pages is not None:
            _pages.shutdown(wait=False, cancel_futures=True)
            _pages = None


def text_of_pdf(pdf: Path, *, marked: bool = False) -> str | None:
    """The text of a scanned PDF, its pages read in page_pool beside those of other scans; None when the server is away or
    a page could not be read (the caller leaves the document queued)."""
    if not available():
        return None
    with tempfile.TemporaryDirectory(prefix="lighton-") as work:
        subprocess.run(["pdftoppm", "-r", str(DPI), "-png", str(pdf), str(Path(work) / "p")], check=True)
        pngs = sorted(Path(work).glob("p-*.png"), key=lambda p: int(p.stem.rsplit("-", 1)[1]))
        futures = [page_pool().submit(read_page, png) for png in pngs]
        try:
            pages = [f.result() for f in futures]
        except (httpx.HTTPError, KeyError, ValueError) as e:
            for f in futures:  # the scan stays queued: cancel unsent pages and wait for those already being read
                f.cancel()
            wait(futures)  # (they read the images of this folder)
            print(f"  lighton failed ({type(e).__name__}: {e}), scan stays queued", flush=True)
            return None
    return text_of_pages(pages, marked=marked)


def text_of_pages(pages: list[str], *, marked: bool = False) -> str:
    """The text of a scan from the markdown of its pages, its '#' headings marked; `marked`: a `\\f<n>` line before each page."""
    from catix.docs.sources import opendataloader

    nodes = [node | {"page number": i} for i, page in enumerate(pages, 1) for node in nodes_of(page)]
    return opendataloader.text_of({"kids": nodes}, headings=True, marked=marked)
