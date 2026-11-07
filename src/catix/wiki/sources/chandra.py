"""OCR of a scanned PDF by chandra-ocr-2 (datalab's vision-language model, served by llama.cpp on the GPU machine at
settings.ocr_route): the image of a page in, its blocks as HTML out (text, headings, lists, tables with their merged cells,
the page's head and foot, pictures). The HTML becomes the nodes opendataloader gives for a text layer, and
opendataloader.text_of makes the text of them as it does for one: a block a paragraph, a table as markdown, a page's head
once, a paragraph going on across a page.

On 12 pages with a text layer (its words the truth; the page clean and with a scan's noise) chandra misread 1.2% / 1.1% of
the words and found every number. On 24 pages of real scans it left out noise from stamps and signatures, but its errors are words that exist: one of
like meaning ('промышленными' for 'индустриальными', 'специальности' for 'специалитета'), once English ('date'); a
spelling check does not find them. OvisOCR2 broke Russian words with English ('Иннопоolis', 'Federalным'), PaddleOCR-VL
wrote English of its own in place of a clause, Xiaomi-OCR-0 misspelt more words ('Россииской', 'адьюнктуре') and left a
clause's first line out (the bench of 2026-10-30).

A picture is not text: a seal or a signature chandra describes (in English) is left out. An answer that does not end (the
model looping to its token limit) is asked again warmer, as chandra's own client does. A page the server cannot read leaves
the document queued for another attempt; no other OCR engine is used."""

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

METHOD = "ocr (chandra-ocr-2)"
DPI = 192  # (chandra's own)
MAX_PIXELS, GRID = 3072 * 2048, 28  # the image as chandra sizes it: at most this many pixels, sides a multiple of GRID
MAX_TOKENS = 8192  # (a page is 1-3 thousand; chandra allows 12384, but a looping page ran 135 s to that)
TRIES = [(0.0, 0.1), (0.2, 0.95), (0.4, 0.95)]  # (temperature, top_p): greedy, then warmer for an answer that loops
PICTURES = {"Image", "Figure", "Diagram", "Chemical-Block", "Blank-Page"}
HEADINGS = {"h1", "h2", "h3", "h4", "h5"}

# chandra.prompts.OCR_LAYOUT_PROMPT of chandra-ocr 0.2.0: the prompt the model was trained with
ALLOWED_TAGS = ["math", "br", "i", "b", "u", "del", "sup", "sub", "table", "tr", "td", "p", "th", "div", "pre", "h1", "h2", "h3",
                "h4", "h5", "ul", "ol", "li", "input", "a", "span", "img", "hr", "tbody", "small", "caption", "strong", "thead",
                "big", "code", "chem"]
ALLOWED_ATTRIBUTES = ["class", "colspan", "rowspan", "display", "checked", "type", "border", "value", "style", "href", "alt", "align",
                      "data-bbox", "data-label"]
PROMPT = f"""OCR this image to HTML, arranged as layout blocks.  Each layout block should be a div with the data-bbox attribute representing the bounding box of the block in x0 y0 x1 y1 format.  Bboxes are normalized 0-1000. The data-label attribute is the label for the block.

Use the following labels:
- Caption
- Footnote
- Equation-Block
- List-Group
- Page-Header
- Page-Footer
- Image
- Section-Header
- Table
- Text
- Complex-Block
- Code-Block
- Form
- Table-Of-Contents
- Figure
- Chemical-Block
- Diagram
- Bibliography
- Blank-Page

Only use these tags {ALLOWED_TAGS}, and these attributes {ALLOWED_ATTRIBUTES}.

Guidelines:
* Inline math: Surround math with <math>...</math> tags. Math expressions should be rendered in KaTeX-compatible LaTeX. Use display for block math.
* Tables: Use colspan and rowspan attributes to match table structure.
* Formatting: Maintain consistent formatting with the image, including spacing, indentation, subscripts/superscripts, and special characters.
* Images: Include a description of any images in the alt attribute of an <img> tag. Do not fill out the src property. Describe in detail inside the div tag. Also convert charts to high fidelity data, and convert diagrams to mermaid.
* Forms: Mark checkboxes and radio buttons properly.
* Text: join lines together properly into paragraphs using <p>...</p> tags.  Use <br> tags for line breaks within paragraphs, but only when absolutely necessary to maintain meaning.
* Chemistry: Use <chem>...</chem> tags for chemical formulas with reactive SMILES.
* Lists: Preserve indents and proper list markers.
* Use the simplest possible HTML structure that accurately represents the content of the block.
* Make sure the text is accurate and easy for a human to read and interpret.  Reading order should be correct and natural."""


def available() -> bool:
    """Whether the OCR server answers and serves chandra (another model on that port is not it)."""
    if settings.ocr_route is None:
        return False
    try:
        r = httpx.get(f"{str(settings.ocr_route).rstrip('/')}/models", timeout=10)
        r.raise_for_status()
        return any(settings.ocr_model in (m.get("id"), *m.get("aliases", [])) for m in r.json().get("data", []))
    except (httpx.HTTPError, ValueError):
        return False


def image_of(png: Path) -> str:
    """A page's image as chandra takes it (scale_to_fit): within MAX_PIXELS, sides a multiple of GRID; base64 PNG."""
    from PIL import Image

    img = Image.open(png).convert("RGB")
    w, h = img.size
    scale = min(1.0, (MAX_PIXELS / (w * h)) ** 0.5)
    img = img.resize((max(GRID, round(w * scale / GRID) * GRID), max(GRID, round(h * scale / GRID) * GRID)), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def loops(text: str) -> bool:
    """The answer's end standing again and again (10..200 characters, 4 times or more): the model went round in a loop."""
    return any(len(text) >= 4 * n and text.endswith(text[-n:] * 4) for n in range(10, 201))


def read_page(png: Path) -> str:
    """The HTML of a page; an answer cut at the token limit or looping is asked again warmer, the last one kept."""
    content = [{"type": "image_url", "image_url": {"url": "data:image/png;base64," + image_of(png)}}, {"type": "text", "text": PROMPT}]
    html = ""
    for temperature, top_p in TRIES:
        r = httpx.post(f"{str(settings.ocr_route).rstrip('/')}/chat/completions", timeout=900, json={
            "model": settings.ocr_model, "messages": [{"role": "user", "content": content}], "max_tokens": MAX_TOKENS,
            "temperature": temperature, "top_p": top_p,
            "chat_template_kwargs": {"enable_thinking": False}})  # (thinking on, it answers a JSON of boxes, not its HTML)
        r.raise_for_status()
        choice = r.json()["choices"][0]
        html = choice["message"].get("content") or ""
        if choice.get("finish_reason") != "length" and not loops(html):
            break
    return html


def text_in(tag) -> str:
    """The words of a piece of HTML, a <br> a line break."""
    for br in tag.find_all("br"):
        br.replace_with("\n")
    return tag.get_text("")


def table_node(table) -> dict:
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


def list_node(lst) -> dict:
    """An HTML list as opendataloader's: an item's own words its content, a list inside it a kid."""
    items = []
    for li in lst.find_all("li", recursive=False):
        inner = [sub.extract() for sub in li.find_all(["ul", "ol"], recursive=False)]
        items.append({"content": text_in(li), "kids": [list_node(sub) for sub in inner]})
    return {"type": "list", "list items": items}


def block_nodes(block) -> list[dict]:
    """The nodes of a block's HTML in their order: headings, paragraphs, lists, tables."""
    nodes, words = [], []

    def flush() -> None:
        if "".join(words).strip():
            nodes.append({"type": "paragraph", "content": "".join(words)})
        words.clear()

    for child in list(block.children):
        name = getattr(child, "name", None)
        if name is None:
            words.append(str(child))
        elif name == "br":
            words.append("\n")
        elif name in HEADINGS:
            flush()
            nodes.append({"type": "heading", "content": text_in(child)})
        elif name in ("ul", "ol"):
            flush()
            nodes.append(list_node(child))
        elif name == "table":
            flush()
            nodes.append(table_node(child))
        elif name in ("p", "div", "pre", "caption"):
            flush()
            nodes.extend(block_nodes(child) if child.find(["table", "ul", "ol", "p"] + sorted(HEADINGS)) else
                         [{"type": "paragraph", "content": text_in(child)}])
        else:  # inline: b, i, span, math, a, ...
            words.append(text_in(child))
    flush()
    return nodes


def nodes_of(html: str) -> list[dict]:
    """A page's HTML as opendataloader's nodes: its head and foot as such, pictures left out (a picture in a block of text
    with the description chandra wrote after it, in English)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        for sibling in list(img.next_siblings):  # 'A handwritten signature in black ink, ...'
            if getattr(sibling, "name", None) is None and not re.search(r"[А-Яа-яЁё]", str(sibling)):
                sibling.extract()
            else:
                break
        img.decompose()
    blocks = soup.find_all("div", attrs={"data-label": True}, recursive=False) or [soup]
    nodes = []
    for block in blocks:
        label = block.get("data-label") if block is not soup else "Text"
        if label in PICTURES:
            continue
        if label in ("Page-Header", "Page-Footer"):
            nodes.append({"type": "header" if label == "Page-Header" else "footer", "kids": [{"type": "paragraph", "content": text_in(block)}]})
        else:
            nodes.extend(block_nodes(block))
    return nodes


_pages: ThreadPoolExecutor | None = None
_pages_lock = threading.Lock()


def page_pool() -> ThreadPoolExecutor:
    """The pages being read, of every scan the process reads at once: as many as the server has slots (OCR_PARALLEL), so
    the short scans read side by side fill them as one long one does."""
    global _pages
    with _pages_lock:
        if _pages is None:
            _pages = ThreadPoolExecutor(settings.ocr_parallel, thread_name_prefix="chandra-page")
        return _pages


def cancel_pages() -> None:
    """The pages waiting in page_pool not read (a stopped run): those being read end, the next page_pool is a new one."""
    global _pages
    with _pages_lock:
        if _pages is not None:
            _pages.shutdown(wait=False, cancel_futures=True)
            _pages = None


def text_of_pdf(pdf: Path, keep: Path | None = None) -> str | None:
    """The text of a scanned PDF, its pages read in page_pool beside those of other scans; None when the server is away or
    a page could not be read (the caller leaves the document queued). `keep`: a folder for the HTML of each page as
    chandra answered it (p-001.html, ...), to look at, or to make the text again without reading the scan again."""
    if not available():
        return None
    with tempfile.TemporaryDirectory(prefix="chandra-") as work:
        subprocess.run(["pdftoppm", "-r", str(DPI), "-png", str(pdf), str(Path(work) / "p")], check=True)
        pngs = sorted(Path(work).glob("p-*.png"), key=lambda p: int(p.stem.rsplit("-", 1)[1]))
        futures = [page_pool().submit(read_page, png) for png in pngs]
        try:
            pages = [f.result() for f in futures]
        except (httpx.HTTPError, KeyError, ValueError) as e:
            for f in futures:  # the scan stays queued: cancel unsent pages and wait for those already being read
                f.cancel()
            wait(futures)  # (they read the images of this folder)
            print(f"  chandra failed ({type(e).__name__}: {e}), scan stays queued", flush=True)
            return None
    if keep is not None:
        keep.mkdir(parents=True, exist_ok=True)
        for old in keep.glob("p-*.html"):
            old.unlink()
        for n, html in enumerate(pages, 1):
            (keep / f"p-{n:03d}.html").write_text(html, encoding="utf-8")
    return text_of_pages(pages)


def text_of_pages(pages: list[str]) -> str:
    """The text of a scan from chandra's HTML of its pages, its headings (its Section-Header blocks) marked."""
    from catix.wiki.sources import opendataloader

    return opendataloader.text_of({"kids": [node for html in pages for node in nodes_of(html)]}, headings=True)


def kept_text(keep: Path) -> str | None:
    """The text of a scan made again from the HTML kept of its pages (p-001.html, ...), without reading the scan again."""
    pages = sorted(keep.glob("p-*.html")) if keep.is_dir() else []
    return text_of_pages([p.read_text(encoding="utf-8") for p in pages]) if pages else None
