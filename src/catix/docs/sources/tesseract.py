"""OCR of a scanned PDF by the local Tesseract (`rus+eng`), the only OCR engine of the documents and the course files: each
page of the PDF is drawn by pdftoppm (DPI) and read by `tesseract` (page segmentation mode 3, a plain text out). The text
of the pages becomes the nodes opendataloader gives for a text layer (a block a paragraph), and opendataloader.text_of makes
the text of them as it does for one: a paragraph going on across a page. Tesseract gives no headings, tables or boxes: the
headings are guessed from the numbers as for a text layer. A page it cannot read leaves the document queued for another
attempt."""

import functools
import shutil
import subprocess
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from pathlib import Path

from catix.settings import settings

METHOD = "ocr (Tesseract)"
LANGUAGES = {"rus", "eng"}
DPI = 300
PAGE_TIMEOUT = 300  # seconds for one page


@functools.cache
def available() -> bool:
    """Whether `tesseract` is installed with both languages."""
    if shutil.which("tesseract") is None or shutil.which("pdftoppm") is None:
        return False
    try:
        listed = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True, timeout=30, check=True).stdout
    except (subprocess.SubprocessError, OSError):
        return False
    return LANGUAGES <= set(listed.split())


def read_page(png: Path) -> str:
    """The text of a page image; CalledProcessError when tesseract fails on it."""
    done = subprocess.run(["tesseract", str(png), "stdout", "-l", "+".join(sorted(LANGUAGES, reverse=True)), "--psm", "3"],
                          capture_output=True, text=True, encoding="utf-8", timeout=PAGE_TIMEOUT, check=True)
    return done.stdout


def nodes_of(text: str) -> list[dict]:
    """A page's text as opendataloader's nodes: the blocks apart by a blank line are paragraphs."""
    blocks = (" ".join(line.strip() for line in block.splitlines() if line.strip()) for block in text.split("\n\n"))
    return [{"type": "paragraph", "content": block} for block in blocks if block]


_pages: ThreadPoolExecutor | None = None
_pages_lock = threading.Lock()


def page_pool() -> ThreadPoolExecutor:
    """The pages being read, of every scan the process reads at once: OCR_PARALLEL of them."""
    global _pages
    with _pages_lock:
        if _pages is None:
            _pages = ThreadPoolExecutor(settings.ocr_parallel, thread_name_prefix="tesseract-page")
        return _pages


def cancel_pages() -> None:
    """The pages waiting in page_pool not read (a stopped run): those being read end, the next page_pool is a new one."""
    global _pages
    with _pages_lock:
        if _pages is not None:
            _pages.shutdown(wait=False, cancel_futures=True)
            _pages = None


def text_of_pdf(pdf: Path, *, marked: bool = False) -> str | None:
    """The text of a scanned PDF, its pages read in page_pool beside those of other scans; None when Tesseract is missing or
    a page could not be read (the caller leaves the document queued)."""
    if not available():
        return None
    with tempfile.TemporaryDirectory(prefix="tesseract-") as work:
        subprocess.run(["pdftoppm", "-r", str(DPI), "-png", str(pdf), str(Path(work) / "p")], check=True)
        pngs = sorted(Path(work).glob("p-*.png"), key=lambda p: int(p.stem.rsplit("-", 1)[1]))
        futures = [page_pool().submit(read_page, png) for png in pngs]
        try:
            pages = [f.result() for f in futures]
        except (subprocess.SubprocessError, OSError) as e:
            for f in futures:  # the scan stays queued: cancel unsent pages and wait for those already being read
                f.cancel()
            wait(futures)  # (they read the images of this folder)
            print(f"  tesseract failed ({type(e).__name__}: {e}), scan stays queued", flush=True)
            return None
    return text_of_pages(pages, marked=marked)


def text_of_pages(pages: list[str], *, marked: bool = False) -> str:
    """The text of a scan from the text of its pages; `marked`: a `\\f<n>` line before each page."""
    from catix.docs.sources import opendataloader

    nodes = [node | {"page number": i} for i, page in enumerate(pages, 1) for node in nodes_of(page)]
    return opendataloader.text_of({"kids": nodes}, marked=marked)
