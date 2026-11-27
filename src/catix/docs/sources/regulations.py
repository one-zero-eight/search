"""The documents of the bundle (the first regulations, and every PDF or office file the sites link, the disclosure section of
innopolis.university/sveden among them): their notes and text (kept in Postgres: document_files, notes.py) and the documents made of it.

    catix-docs regs fetch [N] [--no-ocr]   # the documents no run has read: download and extract them (N: at most N documents; --no-ocr: a scan is queued
                                # for a run with OCR, as the loop does); --key KEY: that document again, whatever its note says
    catix-docs regs queue       # the OCR queue (every source's scans waiting for OCR) and the scans too long for it (ocr_queue.py)

The text of a regulation is NOT rewritten by the model: the program only turns the layout into markdown (chapters, clauses, tables)
and the clause numbers stay, so that an answer can cite 'п. 5.3'. No model writes any of the page (compile_all). The originals live only in a temporary folder while a run reads them.
These concepts carry `source_kind: official-document`; a scanned one also `extraction: ocr` and a `review:` note.
"""

import functools
import hashlib
import threading
from collections import Counter
import re
import subprocess
import tempfile
import time
from argparse import Namespace
from collections.abc import Callable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from urllib.parse import unquote, urlsplit

from catix.settings import settings
from catix.docs import notes
from catix.docs.sources import hosts
from catix.docs.store import PRODUCER, Document

BASE = "https://innopolis.university/upload/iblock/"
DOCS = {  # key -> (title, path under BASE as the official page links it)
    "attestation-regulation": ("Положение о формах, периодичности и порядке проведения текущего контроля успеваемости и промежуточной аттестации (бакалавриат и магистратура)",
                               "bd2/y363qvj8ag33j0wotva5qullyxlyjc9g/Положение%20о%20формах,%20периодичности%20и%20порядке%20проведения%20текущего%20контроля%20успеваемости.pdf"),
    "transfer-expulsion-regulation": ("Положение о порядке и основаниях перевода, отчисления и восстановления обучающихся",
                                      "c06/49xocpxyo6mx0dri7yd8c5y0zwdmp4pz/Положение_о_порядке_и_основаниях_перевода__отчисления_и_восстановления.pdf"),
    "academic-leave-regulation": ("Положение о предоставлении академического отпуска, отпуска по беременности и родам, отпуска по уходу за ребенком",
                                  "1d2/f5dqw4glz92ni8l6ed30we4hk9ede261/Положение_о_предоставлении_академического_отпуска__отпуска_по_беременности_и_родам__отпуска_по_уходу_за_ребенком_до_д.pdf"),
    "enrollment-procedure-order": ("Порядок оформления возникновения, приостановления и прекращения образовательных отношений",
                                   "ec8/Порядок%20оформления%20возникновения,%20приостановления%20и%20прекращения%20образовательных%20отношений.pdf"),
    "tuition-to-budget-transfer-regulation": ("Положение о порядке и случаях перехода обучающихся с платного обучения на обучение за счет бюджетных ассигнований",
                                              "a01/67kqu68idvya20wr507ggfr1w0qdoii7/Положение_Переход_на_бесплатное.pdf"),
    "remote-attestation-order": ("Порядок проведения промежуточной аттестации с применением дистанционных образовательных технологий (бакалавриат и магистратура)",
                                 "94f/osb458fkdh07uzyvxznou2viyo5glxk9/poryadok_pa_bakmag_eodot_02.08.2022.pdf"),
    "final-attestation-regulation": ("Положение о порядке проведения государственной итоговой аттестации (бакалавриат и магистратура)",
                                     "0a9/oaov9ai9asxm9hlemq5m0kjpemzvek8j/Положение_о_ГИА_2026.pdf"),
    "credit-transfer-regulation": ("Положение о порядке зачета результатов освоения обучающимися учебных предметов, курсов, дисциплин (модулей), практики",
                                   "d7e/txxukdacbjlc0ym3x1qyy2vmhxfmu4wf/Положение_о_порядке_зачета_АНО_ВО__Университет_Иннополис__результатов_освоения_обучающимися_учебных_предметов__курсо.pdf"),
    "academic-integrity-regulation": ("Положение по применению дисциплинарных взысканий за нарушения академической добропорядочности",
                                      "88c/o6qcuf0gjap2g2ow7teqoal3a5aao0kz/приказ_от_01.02.2023___ОД_АД-03.pdf"),
}
MONTHS = {m: i for i, m in enumerate("января февраля марта апреля мая июня июля августа сентября октября ноября декабря".split(), 1)}


def issued_of(text: str, fallback: str) -> str:
    """When the document was issued: the latest date 'от 30 июня 2025' / 'от 30.06.2025' near its start, or a date in its header.
    Not the first such date: the first is often a law the document cites ('Федеральный закон от 29 декабря 2012 года № 273-ФЗ')."""
    words = r"(\d{1,2})\s+(" + "|".join(MONTHS) + r")\s+(\d{4})"
    found = [(int(y), MONTHS[mo], int(d)) for d, mo, y in re.findall(r"от\s+" + words, text[:4000]) + re.findall(words, text[:1500])]
    found += [(int(y), int(mo), int(d)) for d, mo, y in re.findall(r"от\s+(\d{1,2})\.(\d{1,2})\.(\d{4})", text[:4000])]
    today = datetime.now(timezone.utc).date()
    found = [f for f in found if 1 <= f[1] <= 12 and 1 <= f[2] <= 31 and 1990 <= f[0] and f <= (today.year, today.month, today.day)]
    if not found:
        return fallback
    y, mo, d = max(found)
    return f"{y}-{mo:02d}-{d:02d}T00:00:00+03:00"


DAY_FIRST = re.compile(r"(?<!\d)(\d{1,2})[.\-](\d{1,2})[.\-]((?:19|20)\d{2})(?!\d)")   # 01.02.2023, 21-08-2025
YEAR_FIRST = re.compile(r"(?<!\d)((?:19|20)\d{2})[.\-](\d{1,2})[.\-](\d{1,2})(?!\d)")  # 2019.12.23
YEAR = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")                                      # ГИА 2026, report-2016, 2026/2027
WORDY = re.compile(r"(?<!\d)(\d{1,2})\s+(" + "|".join(MONTHS) + r")\s+((?:19|20)\d{2})(?!\d)")


def date_in(name: str) -> tuple[str, str] | None:
    """(ISO date, 'day' or 'year') named in a title or a file name: the latest full date, else the latest year; none in the
    future, none before 1990."""
    name = name.replace("_", " ")
    today = datetime.now(timezone.utc).date()
    found = [(int(y), int(m), int(d)) for d, m, y in DAY_FIRST.findall(name)]
    found += [(int(y), int(m), int(d)) for y, m, d in YEAR_FIRST.findall(name)]
    found += [(int(y), MONTHS[m], int(d)) for d, m, y in WORDY.findall(name.lower())]
    found = [f for f in found if 1 <= f[1] <= 12 and 1 <= f[2] <= 31 and 1990 <= f[0] and f <= (today.year, today.month, today.day)]
    if found:
        y, m, d = max(found)
        return f"{y}-{m:02d}-{d:02d}T00:00:00+03:00", "day"
    years = [int(y) for y in YEAR.findall(name) if 1990 <= int(y) <= today.year]
    return (f"{max(years)}-01-01T00:00:00+03:00", "year") if years else None


def dated(text: str, title: str, url: str, member: str | None, pdf_created: str | None, fallback: str) -> tuple[str, str, str]:
    """(issued, from, precision): the text's own date (issued_of), else the title's, else the file name's (the archive
    member's, else the last part of the URL path, unquoted), else the PDF's CreationDate; else (fallback, '', '')."""
    if own := issued_of(text, ""):
        return own, "text", "day"
    if found := date_in(title):
        return found[0], "title", found[1]
    if found := date_in(Path(member).name if member else unquote(urlsplit(url).path.rsplit("/", 1)[-1])):
        return found[0], "filename", found[1]
    if pdf_created:
        return f"{pdf_created}T00:00:00+03:00", "pdf", "day"
    return fallback, "", ""


def pdf_created(pdf: Path) -> str | None:
    """The PDF's CreationDate (YYYY-MM-DD), None when it has none, is before 1990 or is in the future."""
    try:
        out = subprocess.run(["pdfinfo", "-isodates", str(pdf)], capture_output=True, text=True, timeout=60, check=False).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"^CreationDate:\s+(\d{4}-\d{2}-\d{2})", out, re.M)
    if not m or not "1990-01-01" <= m.group(1) <= datetime.now(timezone.utc).date().isoformat():
        return None
    return m.group(1)


MAX_BYTES, MAX_PAGES, MAX_OCR_PAGES = 25_000_000, 150, 40  # one document may not take hours of OCR
QUEUED, TOO_LONG = "queued", "too long"  # a scan's "ocr" in its note: waits for a run with OCR / longer than MAX_OCR_PAGES, put aside (ocr_state)
MAX_FAILURES = 5  # network errors in a row before a run gives up
PAUSE = 2  # seconds between requests: the site blocked us once after a burst, so stay well below what it tolerates
UNSIGNED_EVERY = timedelta(days=30)  # a file the site says nothing about (no ETag, date or size) is downloaded and compared by its bytes this often
READ_LOCK = threading.RLock()  # (read_new and recheck write the documents' notes: the crawl loop and the OCR thread one after the other)


def locked(fn: Callable) -> Callable:
    """Run `fn` holding READ_LOCK."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        with READ_LOCK:
            return fn(*args, **kwargs)

    return wrapper


OCR_BUDGET = 200  # pages of OCR per run of `regs fetch`; documents left over are done by the next run
AUDIENCE_OF_SECTION = {  # who a document is for, by the section of the site that lists it; a section of every kind of document names no one (everyone)
    "site/hotel": ["student", "postgraduate", "applicant", "public"],  # the dormitory's rules and prices, its guests
}


HEADERS = {"User-Agent": "catix-docs/0.1 (Innopolis University assistant; polite crawl)"}
LOGIN = re.compile(r"(?i)(?:^|[./])(?:sso|adfs|idp|cas|auth|oauth2?|login|signin|sign-in|passport)(?:[./?]|$)")  # the host or path of a login


def a_login(resp: httpx.Response) -> bool:
    """Whether the page a site sent in place of a file is a login (help sends to the university's SSO) by its address or its
    password field, not a page of the site (university.innopolis.ru/files/ sends to the start page of innopolis.university)."""
    from catix.docs.sources import sites

    return bool(LOGIN.search(f"{resp.url.host}{resp.url.path}") or sites.LOGIN_FORM.search(resp.text))


def signature(headers: httpx.Headers) -> dict:
    """What says that a file on the site is still the same one, without downloading it."""
    return {k: headers[h] for k, h in (("etag", "etag"), ("modified", "last-modified"), ("size", "content-length")) if h in headers}


def changed(old: dict | None, new: dict) -> bool:
    """A different ETag, or (without one) a different date or size. A file not seen before is not 'changed': it is recorded."""
    if not old or not new:
        return False
    if old.get("etag") and new.get("etag"):
        return old["etag"] != new["etag"]
    return (old.get("modified"), old.get("size")) != (new.get("modified"), new.get("size"))


SIGNED = re.compile(r"\s*\(документы? подписаны? (?:ПЭП|простой электронной подписью|электронной подписью)\)", re.I)  # says nothing about the content
GLUED = re.compile(r"^(\s*\d{1,2}(?:\.\d{1,2}){1,4}\.)(?=[^\W\d_]|«)|^(\s*\d{1,2}\.)(?=[А-ЯЁA-Z])", re.M)  # '3.2.Аспирант', '8.Во время'


def work_file(work: Path, key: str, d: dict) -> Path:
    """Where a document's file is in the work folder of a read (the originals live only there): a revision of a document, a file."""
    return work / (d.get("revision") or "_") / f"{key}.{d.get('ext', 'pdf')}"


def all_docs() -> dict[str, dict]:
    """Every document of the bundle: the first regulations (DOCS) and those the sites link (the disclosure section of the
    university's site among them, and those the documents' own text names: the rows of the frontier, sites.docs). A document is
    a key, and a `revision` ('' for a file at its URL; an archive's member, a PDF an archive URL served: its content's sha)."""
    from catix.docs.sources import archive_documents, sites

    docs = {k: {"title": t, "url": BASE + p, "section": "document"} for k, (t, p) in DOCS.items()}
    have = {sites.canonical(d["url"]) for d in docs.values()}
    docs.update({k: d for k, d in sites.docs().items() if d["url"] not in have})  # (one of DOCS the site links too is not read twice)
    if any(d.get("ext") in archive_documents.EXTENSIONS for d in docs.values()):
        from catix.docs.sources import rpd

        specialised = {sites.canonical(a["url"]) for a in rpd.archives()}
        read = {sites.canonical(c["archive"]) for c in rpd.load().values() if "sha256" in c}
        docs = {key: d for key, d in docs.items() if (url := sites.canonical(d["url"])) not in specialised  # (an archive read here
                or url not in read and archive_documents.exists(key)}  # before rpd took it: its files stay pages until rpd has read it)
    docs.update(archive_documents.members(docs))
    boiler = re.compile(r"^(?:Высшее образование\s*[-–]\s*\w+\s*)?(?:Образовательная программа высшего образования\s*[-–]\s*программа\s*\w+\s*)?")
    for d in docs.values():
        d["context"] = boiler.sub("", d.get("context", "")).strip()  # the level and 'educational programme of higher education' are the same for all
    titles = Counter(d["title"] for d in docs.values())
    for d in docs.values():  # the same title for many programmes ('Program of the final attestation'): the programme tells them apart
        if titles[d["title"]] > 1 and d.get("context") and not d["title"].startswith(d["context"][:20]):
            d["title"] = f"{d['context'][:220]} — {d['title']}"
    titles = Counter(d["title"].lstrip(": ") for d in docs.values())
    for d in docs.values():  # the same programme and title in several years: the file name carries the cohort or year
        d["title"] = d["title"].lstrip(": ")
        if titles[d["title"]] > 1:
            d["title"] += f" [{unquote(d['url'].rsplit('/', 1)[-1]).rsplit('.', 1)[0][:60]}]"
    return docs


def pages_of(pdf: Path) -> int:
    return int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout).group(1))


def to_pdf(path: Path) -> Path:
    """Word and RTF files are turned into a PDF with LibreOffice, so that one path reads them all."""
    if path.suffix.lower() == ".pdf":
        return path
    pdf = path.with_suffix(".pdf")
    if not pdf.exists():
        subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(path.parent), str(path)], capture_output=True, timeout=180)
    return pdf


TEXT_LAYER = "text layer (opendataloader)"
PDFPLUMBER = "text layer (pdfplumber)"  # a PDF opendataloader could not read, or read too little of
TABLES = 5  # the reading of the text layer (2: cells merged across columns, 3: a line on a table's edge once, 4: a table of one column is text, 5: opendataloader)


def _cell(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").replace("|", "/")).strip()


def table_markdown(rows: list[list[str | None]], wide: list[list[bool]] | None = None) -> str:
    """A table found by pdfplumber as a markdown table. A merged cell comes as None in the rows it spans: it takes the value
    above (the programme of every exam row), as tables.py does with rowspan. A cell merged across columns (`wide`, from
    spans_of) stays empty: the heading of a group of rows ("Расходные материалы") is not the row above it again. Empty rows
    and columns go."""
    out: list[list[str]] = []
    for r, row in enumerate(rows):
        cells = [_cell(c) for c in row]
        if out and any(cells):
            cells = [out[-1][i] if row[i] is None and i < len(out[-1]) and not (wide and wide[r][i]) else c for i, c in enumerate(cells)]
        if any(cells):
            out.append(cells)
    if len(out) < 2:
        return "\n".join(" ".join(c for c in r if c) for r in out)
    width = max(len(r) for r in out)
    out = [r + [""] * (width - len(r)) for r in out]
    keep = [i for i in range(width) if any(r[i] for r in out)]
    out = [[r[i] for i in keep] for r in out]
    if len(keep) == 1:  # a frame around text, not a table: its lines are text (a regulation in a box lost its clauses: '| 1.1. ... |')
        return "\n".join(r[0] for r in out)
    return "\n".join(["| " + " | ".join(out[0]) + " |", "|" + " --- |" * len(keep)] + ["| " + " | ".join(r) + " |" for r in out[1:]])


def spans_of(table) -> list[list[bool]]:
    """For each cell pdfplumber left out (None) of a table: whether a cell to its left in the same row covers it (merged
    across columns), not one above it."""
    lefts = [col.bbox[0] for col in table.columns]
    out = []
    for row in table.rows:
        flags, last = [], None
        for i, cell in enumerate(row.cells):
            flags.append(cell is None and last is not None and i < len(lefts) and last[2] > lefts[i] + 1)
            last = cell if cell is not None else last
        out.append(flags)
    return out


def text_layer(pdf: Path) -> str:
    """The text of a PDF with its tables as markdown tables, in reading order. pdftotext -layout aligned the columns with
    spaces, and a cell of several lines fell apart into rows of other cells (the exams of the rules of admission came out
    under the wrong level); pdfplumber finds the ruled tables and their cells."""
    import pdfplumber

    pages = []
    with pdfplumber.open(pdf) as doc:
        for page in doc.pages:
            tables = sorted((t for t in page.find_tables() if len(t.rows) >= 2), key=lambda t: t.bbox[1])
            boxes = [t.bbox for t in tables]

            def outside(obj: dict) -> bool:
                if obj.get("object_type") != "char":
                    return True
                x, y = (obj["x0"] + obj["x1"]) / 2, (obj["top"] + obj["bottom"]) / 2
                return not any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for b in boxes)

            rest = page.filter(outside)

            def band(top: float, bottom: float) -> str:
                """The text between two heights. A character belongs to the band its middle is in: crop() keeps what only
                touches the band, and a line on the edge of a table came out twice, above it and beside it."""
                if bottom - top <= 1:
                    return ""
                return rest.filter(lambda o: o.get("object_type") != "char" or top <= (o["top"] + o["bottom"]) / 2 < bottom).extract_text() or ""

            parts, y = [], 0.0
            for t in tables:
                parts += [band(y, t.bbox[1]), band(t.bbox[1], t.bbox[3]), table_markdown(t.extract(), spans_of(t))]  # (the text beside a table, its label, first)
                y = t.bbox[3]
            parts.append(band(y, page.height))
            pages.append("\n\n".join(p for p in parts if p.strip()))
    return "\f".join(pages)


def plumbed(pdf: Path) -> tuple[str, str]:
    """The text layer as pdfplumber reads it (pdftotext for a PDF it cannot parse)."""
    try:
        return text_layer(pdf), PDFPLUMBER
    except Exception as e:  # noqa: BLE001 - a PDF pdfplumber cannot parse is read the old way
        print(f"  pdfplumber failed ({e}), pdftotext instead")
        return subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True, check=True).stdout, "text layer"


def layer_text(pdf: Path, converted: Path | None = None, *, marked: bool = False) -> tuple[str, str] | None:
    """(text, method) of the text layer when the PDF has one (opendataloader; pdfplumber when it could not read it, or read
    too little); None for a scan. `converted`: the PDF's JSON when many were converted at once. `marked`: a `\\f<n>` line before
    each page's text (opendataloader.split_pages)."""
    from catix.docs.sources import opendataloader

    count = pages_of(pdf)
    text = opendataloader.text_of_pdf(pdf, converted, marked=marked)
    if text is not None and len(text.strip()) > 300 * count:
        return text, TEXT_LAYER
    text, method = plumbed(pdf)
    if len(text.strip()) > 300 * count:
        return (opendataloader.mark_pages(text.split("\f")) if marked else text), method
    return None


def ocr_refused(pages: int, ocr_left: float, limit: float = MAX_OCR_PAGES) -> str | None:
    """Why a scan of `pages` is not read now (with `ocr_left` pages of OCR left), None when it is."""
    if pages > limit:
        return "scan too long for OCR"
    return "ocr deferred" if pages > ocr_left else None


def limits(note: dict) -> tuple[float, float, float]:
    """(bytes, pages, OCR pages) a document may take: no limit for one a person asked for (the note's `force`, regs fetch --key)."""
    return (float("inf"),) * 3 if note.get("force") else (MAX_BYTES, MAX_PAGES, MAX_OCR_PAGES)


def ocr_state(note: dict, limit: int | None = None) -> str | None:
    """What a document's note says of its scan: QUEUED (it waits for a run with OCR), TOO_LONG (longer than `limit` pages,
    MAX_OCR_PAGES by default: put aside, out of the queue, no run reads it), None (not a scan waiting). By the pages, not the
    word written: a note queued before the long ones were put aside is a long one, and a long one is queued again once the
    limit covers it."""
    if note.get("ocr") not in (QUEUED, TOO_LONG):
        return None
    if note.get("force"):  # (a person asked for this very document: no page limit puts it aside)
        return QUEUED
    return TOO_LONG if note.get("pages", 0) > (MAX_OCR_PAGES if limit is None else limit) else QUEUED


def scan_notes() -> Iterator[tuple[str, dict, dict]]:
    """(key, document, note) of every scan queued for OCR or put aside as too long (ocr_state), of the revision of the document now."""
    docs = all_docs()
    for key, revision, note in notes.scans():
        if (d := docs.get(key)) is not None and d.get("revision", "") == revision and ocr_state(note):
            yield key, d, note


def queued() -> dict[str, int]:
    """The scans waiting for a manual run with OCR, key -> pages; not those too long for it (put aside: ocr_state)."""
    return {key: note.get("pages", 0) for key, _, note in scan_notes() if ocr_state(note) == QUEUED}


class NotRead(RuntimeError):
    """The OCR did not read a scan. `away`: no OCR engine is available (not the scan's fault); else a page of it failed."""

    def __init__(self, away: bool) -> None:
        super().__init__("no OCR engine is available (the LightOnOCR server does not answer, tesseract is not installed)" if away
                         else "the OCR could not read a page of it")
        self.away = away


def ocr_text(pdf: Path, *, marked: bool = False) -> tuple[str, str]:
    """(text, method) of a scan by LightOnOCR, by Tesseract only while its server does not answer; NotRead leaves the scan
    queued for a later attempt."""
    from catix.docs.sources import lighton, tesseract

    if lighton.available():
        text = lighton.text_of_pdf(pdf, marked=marked)
        if text and text.strip():
            return text, lighton.METHOD
        if lighton.available():  # the server answers: a page of this scan failed
            raise NotRead(away=False)
    print(f"  the LightOnOCR server {settings.ocr_route} does not answer: {pdf.name} read by tesseract", flush=True)
    if not tesseract.available():
        raise NotRead(away=True)
    text = tesseract.text_of_pdf(pdf, marked=marked)
    if text is None or not text.strip():
        raise NotRead(away=False)
    return text, tesseract.METHOD


def read_scans[T](scans: list[T], pdf_of: Callable[[T], Path], read: Callable[[Path], tuple[str, str]] | None = None) -> Iterator[tuple[T, Future]]:
    """The scans read several at once, each (scan, its future of `read`, ocr_text by default) as it is done. As many scans as
    OCR_PARALLEL are open at a time, their pages in one queue (page_pool): a scan of 3 pages does not leave the other
    slots idle while it is read, as one at a time did (LightOnOCR on inh-compute, llama.cpp with the vision encoder on the GPU: 10.4 pages a minute at one page at once, 14.7 at four, the agent's LLM decoding 25-33 % slower meanwhile; on the CPU it read 2.7)."""
    from catix.docs.sources import lighton, tesseract

    pool, finished = ThreadPoolExecutor(settings.ocr_parallel, thread_name_prefix="scan"), False
    try:
        futures = {pool.submit(read or ocr_text, pdf_of(scan)): scan for scan in scans}
        for future in as_completed(futures):
            yield futures[future], future
        finished = True
    finally:
        if not finished:  # a stopped run (Ctrl-C) does not wait for the scans and pages queued behind the ones being read
            lighton.cancel_pages()
            tesseract.cancel_pages()
        pool.shutdown(wait=finished, cancel_futures=not finished)


def extract(pdf: Path, ocr_left: int, converted: Path | None = None) -> tuple[str | None, str, int]:
    """(text, method, OCR pages used): the text layer when there is one, else OCR of the page images; None when OCR is not
    allowed now. `converted`: the PDF's JSON when many were converted at once."""
    if (layer := layer_text(pdf, converted)) is not None:
        return *layer, 0
    pages = pages_of(pdf)
    if why := ocr_refused(pages, ocr_left):
        return None, why, 0
    return *ocr_text(pdf), pages


def _fetch_once(limit: int | None = None, prefixes: tuple[str, ...] | None = None, ocr: bool = True) -> list[str]:
    """Download the documents not read yet (and those `refresh` found changed) into a temporary folder, then read them: the text layers all at once
    (one run of opendataloader's JVM, not one a file), the scans after them; the keys of those read. `prefixes`: only the
    documents whose key starts with one of them ('site-lab-': the documents of one site). Without `ocr` a scan (a PDF the text
    layer gives too little of) is not read: it is queued (`"ocr": "queued"` in its note) for a run with OCR, which downloads it again
    and reads it; the runs without OCR pass it by (the 6-hourly run needs no OCR model up).
    A scan the OCR does not read stays queued, regardless of the number of failed attempts. A scan longer than MAX_OCR_PAGES
    is not queued: it is put aside (`"ocr": "too long"`), and no run reads it or asks its text layer again until the limit
    covers it or the file changes on the site (ocr_state; `catix-docs regs queue` lists them apart).

    Every download ends in a note: a document no file came for (a host that does not answer, a login it was sent to) is
    `failed`, and no run asks it again before sites.RETRY; without the note every run asked it again (olymp.innopolis.ru has
    no address any more, university.innopolis.ru/files/ sends to the university's start page). A host that fails
    MAX_FAILURES times in a row is let be for the rest of the run; the other hosts are read (a dead host stopped the whole run)."""
    from catix.docs.sources import archive_documents, opendataloader, sites

    def skip(key: str, d: dict, why: str) -> None:
        notes.put_note(key, d.get("revision", ""), {"title": d["title"], "url": d["url"], "skipped": why})

    def put_off(key: str, d: dict, old: dict, why: str) -> None:
        """No file this time: why and when, and what an earlier run read of the document stays (its text, its page)."""
        notes.put_note(key, d.get("revision", ""), {**old, "title": d["title"], "url": d["url"], "failed": why,
                                                    "tried_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})

    def unchanged(key: str, d: dict, old: dict, remote: dict, why: str) -> None:
        """The file is the one already read: its text stays, nothing is extracted or OCR'd again."""
        keep = {k: v for k, v in old.items() if k not in ("refetch", "force", "failed", "tried_at")}
        notes.put_note(key, d.get("revision", ""), {**keep, "title": d["title"], "url": d["url"], "remote": remote or old.get("remote", {}),
                                                    "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
        print(f"  {why}: the text read before stays", flush=True)

    with tempfile.TemporaryDirectory(prefix="catix-docs-") as tmp:
        work = Path(tmp)
        removed = archive_documents.prepare(all_docs(), prefixes, work, ocr)
        docs, failures, downloaded, queued = all_docs(), Counter(), [], set()
        for key, d in docs.items():
            if archive_documents.is_archive(key, d) or prefixes and not key.startswith(prefixes):
                continue
            revision = d.get("revision", "")
            ext = d.get("ext", "pdf")
            src = work_file(work, key, d)
            old = notes.note(key, revision)
            has_text = bool(old.get("sha256")) and notes.has_text(key, revision)
            if ocr_state(old) == TOO_LONG and not old.get("refetch"):  # (put aside: no run reads it, its text layer is not asked again)
                if old["ocr"] != TOO_LONG:  # (queued before the long scans were put aside)
                    notes.put_note(key, revision, {**old, "ocr": TOO_LONG})
                continue
            waiting = ocr_state(old) == QUEUED  # (a scan queued by a run without OCR: a run with OCR downloads it again)
            if not waiting and old and (notes.has_text(key, revision) or "skipped" in old) and not old.get("refetch"):
                continue  # (a document that changed on the site is noticed by `regs refresh`; a skipped one stays skipped)
            if waiting and not ocr:
                continue
            host = httpx.URL(d["url"]).host
            if not waiting and (old.get("failed") and sites.recent(old.get("tried_at")) or failures[host] >= MAX_FAILURES):
                continue  # (no file came lately: asked again after RETRY; its host stopped answering in this run: the next run asks)
            if limit is not None and len(downloaded) >= limit:
                break
            print(key, flush=True)
            if d.get("member") or d.get("archived"):  # (members and standalone PDFs are downloaded through the archive boundary)
                if not src.exists():
                    print("  archive-managed source is missing locally: left for the next archive read")
                    continue
                remote = {}
                if has_text and not old.get("force") and hashlib.sha256(src.read_bytes()).hexdigest() == old["sha256"]:
                    unchanged(key, d, old, remote, "the same bytes as before")
                    continue
            else:
                try:
                    hosts.turn(d["url"])
                    conditional = {}
                    if has_text and not old.get("force"):
                        if (old.get("remote") or {}).get("etag"):
                            conditional = {"If-None-Match": old["remote"]["etag"]}
                        elif (old.get("remote") or {}).get("modified"):
                            conditional = {"If-Modified-Since": old["remote"]["modified"]}
                    resp = httpx.get(d["url"], timeout=120, follow_redirects=True, headers={**HEADERS, **conditional})
                    if resp.status_code == 304:  # (before raise_for_status: httpx raises on 3xx)
                        unchanged(key, d, old, {**old.get("remote", {}), **{k: v for k, v in signature(resp.headers).items() if k != "size"}}, "not modified (304)")
                        failures[host] = 0
                        time.sleep(PAUSE)
                        continue
                    resp.raise_for_status()
                    if len(resp.content) > limits(old)[0]:
                        print(f"  too big ({len(resp.content) // 1_000_000} MB), skipped")
                        skip(key, d, "file too big")
                        continue
                    if ext not in ("htm", "html") and re.match(rb"\s*<(!doctype html|html)\b", resp.content[:200], re.I):
                        if resp.url.host != host and a_login(resp):  # (help: the university's SSO): not skipped, asked again later
                            print(f"  sent to the login of {resp.url.host}: asked again in {sites.RETRY.days} days")
                            put_off(key, d, old, f"sent to the login of {resp.url.host}")
                        else:  # a broken link the site answers with one of its pages (or with the start page of another host of it)
                            print("  the site answers with a page, not the file, skipped" + (f" ({resp.url})" if resp.url.host != host else ""))
                            skip(key, d, "a page, not the file")
                        time.sleep(PAUSE)
                        continue
                except httpx.HTTPError as e:  # a moved file must not stop the others
                    print(f"  FAILED: {e}")
                    if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 404:  # a dead link on the site itself
                        skip(key, d, "404 on the site")
                        failures[host] = 0
                        time.sleep(PAUSE)
                        continue
                    failures[host] += 1
                    put_off(key, d, old, f"{type(e).__name__}: {str(e)[:200]}")
                    if failures[host] >= MAX_FAILURES:  # the host refuses connections: going on would only hammer it
                        print(f"  {failures[host]} failures in a row: {host} is not answering, its other documents wait for the next run")
                    time.sleep(PAUSE + 5 * failures[host])  # slower while the host is failing
                    continue
                failures[host] = 0
                src.parent.mkdir(parents=True, exist_ok=True)
                src.write_bytes(resp.content)
                remote = signature(resp.headers)
                time.sleep(PAUSE)
                if has_text and not old.get("force") and hashlib.sha256(resp.content).hexdigest() == old["sha256"]:
                    unchanged(key, d, old, remote, "the same bytes as before")
                    continue
            try:
                pdf = to_pdf(src)
                if not pdf.exists() or pages_of(pdf) > limits(old)[1]:
                    raise ValueError("cannot read or too long")
            except (ValueError, subprocess.SubprocessError, AttributeError) as e:
                print(f"  skipped: {e}")
                skip(key, d, str(e))
                continue
            downloaded.append((key, d, src, pdf, revision, old, remote))
            if waiting:
                queued.add(key)
        print(f"{len(downloaded)} documents to read" + (f", {len(queued)} of them scans queued for OCR" if queued else ""), flush=True)

        def store_new(item: tuple, text: str, method: str) -> None:
            key, d, src, pdf, revision, old, remote = item
            sha = hashlib.sha256(src.read_bytes()).hexdigest()
            notes.put_text(key, revision, text)
            notes.put_note(key, revision, {"title": d["title"], "url": d["url"], "sha256": sha, "method": method, "chars": len(text), "tables": TABLES, "section": d["section"], "context": d.get("context", ""),
                                    "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "remote": remote,
                                         **({"pdf_created": c} if (c := pdf_created(pdf)) else {})})
            print(f"{key}: {len(text)} chars by {method}" + (" (a new version)" if old.get("sha256") and old["sha256"] != sha else ""), flush=True)

        def queue(item: tuple, pages: int, state: str = QUEUED, **more: object) -> None:
            """The scan's note: QUEUED for a run with OCR, or TOO_LONG, put aside. (`refetch` is done: the file was downloaded again.)"""
            key, d, _, _, revision, old, remote = item
            old = {k: v for k, v in old.items() if k not in ("refetch", "failed", "tried_at")}
            notes.put_note(key, revision, {**old, "title": d["title"], "url": d["url"], "ocr": state, "pages": pages, "remote": remote,
                                         "queued_at": old.get("queued_at") or datetime.now(timezone.utc).isoformat(timespec="seconds"), **more})
            if state == QUEUED:
                from catix.docs import ocr_worker
                ocr_worker.wake()

        ocr_left, ocr_used, done, scans = OCR_BUDGET, 0, list(removed), []
        with opendataloader.converted([pdf for key, _, _, pdf, _, _, _ in downloaded if key not in queued]) as jsons:
            for item in downloaded:
                key, d, src, pdf, revision, old, remote = item
                if key not in queued:
                    try:
                        layer = layer_text(pdf, jsons.get(pdf))
                    except (ValueError, subprocess.SubprocessError, AttributeError) as e:
                        print(f"{key}: skipped: {e}")
                        skip(key, d, str(e))
                        continue
                    if layer is not None:
                        store_new(item, *layer)
                        done.append(key)
                        continue
                pages = pages_of(pdf)  # a scan: its pages are taken from the budget now, it is read with the others after the loop
                if pages > limits(old)[2]:  # (not queued: it would wait in the queue for ever)
                    print(f"{key}: a scan of {pages} pages, longer than {limits(old)[2]}: put aside, not queued for OCR")
                    queue(item, pages, TOO_LONG)
                    continue
                if not ocr:
                    print(f"{key}: a scan of {pages} pages, queued for a run with OCR")
                elif why := ocr_refused(pages, float("inf") if old.get("force") else ocr_left, limits(old)[2]):
                    print(f"{key}: {why}")
                else:
                    ocr_left -= 0 if old.get("force") else pages
                    ocr_used += pages
                    scans.append(item)
                    continue
                if key not in queued or old.get("ocr") != QUEUED:  # (the next runs do not ask its text layer again; a long one the limit covers now is queued)
                    queue(item, pages)
        if scans:
            print(f"{len(scans)} scans to read by OCR ({ocr_used} pages)", flush=True)
        for item, future in read_scans(scans, lambda item: item[3]):
            try:
                text, method = future.result()
            except NotRead as e:
                failed = item[5].get("ocr_failed", 0) + (not e.away)
                print(f"{item[0]}: {e}: stays queued for the next run with OCR" + (f" (OCR failed on it {failed} times)" if failed else ""), flush=True)
                queue(item, pages_of(item[3]), **({"ocr_failed": failed} if failed else {}))
                continue
            except (ValueError, subprocess.SubprocessError, AttributeError) as e:
                print(f"{item[0]}: skipped: {e}")
                skip(item[0], item[1], str(e))
                continue
            store_new(item, text, method)
            done.append(item[0])
        print(f"{len(done)} documents fetched" + (f"; OCR pages left in the budget: {ocr_left}" if ocr else "; scans wait for a run with OCR"))
        return done


def note_state(key: str, d: dict) -> tuple[str, str | None, timedelta | None]:
    """(state, why, delay) of the row of a document in the frontier, from what its notes say: the delay until it is read again,
    None for never.

        an archive whose manifest is ready                ok          DOCUMENT_EVERY
        an archive whose manifest is another status       tried       RETRY
        an archive with no manifest                       new         SOON
        a text read                                       ok          DOCUMENT_EVERY (UNSIGNED_EVERY when the site says nothing of the file)
        a scan queued for OCR or put aside as too long    ok          DOCUMENT_EVERY
        skipped                                           gone        never
        no file came lately                               tried       RETRY
        no note                                           new         SOON"""
    from catix.docs import frontier
    from catix.docs.sources import archive_documents

    if archive_documents.is_archive(key, d) or d.get("archived"):
        data = archive_documents.load(key)
        if not data:
            return "new", None, frontier.SOON
        if data.get("status") == "ready":
            return "ok", None, frontier.DOCUMENT_EVERY
        return "tried", data.get("status"), frontier.RETRY
    note = notes.note(key, d.get("revision", ""))
    if note.get("sha256") and notes.has_text(key, d.get("revision", "")):
        return "ok", None, frontier.DOCUMENT_EVERY if note.get("remote") else frontier.UNSIGNED_EVERY
    if ocr_state(note):
        return "ok", note["ocr"], frontier.DOCUMENT_EVERY
    if note.get("skipped"):
        return "gone", note["skipped"], None
    if note.get("failed"):
        return "tried", note["failed"], frontier.RETRY
    return "new", None, frontier.SOON


def fetch(limit: int | None = None, prefixes: tuple[str, ...] | None = None, ocr: bool = True) -> int:
    """The documents not read yet, read (read_new); how many."""
    return len(read_new(limit, prefixes, ocr))


@locked
def force(key: str, now: bool = False, ocr: bool = True) -> None:
    """Read one document again whatever its note says (read, skipped, put aside as too long, failed), with no limit of size, pages
    or OCR budget (the note's `force`, see limits). `now`: this process reads it at once, one pass over the keys that start with
    `key`; else its row of the frontier is asked for, and the crawl reads it next (its scan then the OCR thread). KeyError for an
    unknown key."""
    from catix.docs import frontier
    from catix.docs.sources import archive_documents, sites

    d = all_docs()[key]
    if archive_documents.is_archive(key, d):
        raise KeyError(f"{key}: an archive, read by rpd or the archives' reader, not by regs")
    revision = d.get("revision", "")
    notes.put_note(key, revision, {**{k: v for k, v in notes.note(key, revision).items() if k != "failed"}, "refetch": True, "force": True})
    if now:
        print(f"{len(read_new(prefixes=(key,), ocr=ocr))} documents read")
    else:
        frontier.request_address(sites.address(d["url"]))
        print(f"{key}: queued; the crawl reads it next")


@locked
def read_new(limit: int | None = None, prefixes: tuple[str, ...] | None = None, ocr: bool = True) -> list[str]:
    """Download and read the documents not read yet (_fetch_once), then note it in their rows of the frontier and add the
    documents and pages their text names (frontier.documents_read); the keys of those read. Without `ocr` the scans are
    queued for a run with OCR; those the OCR does not read stay queued too."""
    from catix.docs import frontier

    keys = _fetch_once(limit, prefixes, ocr)
    frontier.documents_read(keys)
    return keys


@locked
def recheck(keys: list[str]) -> list[str]:
    """Read the documents of these rows of the frontier again: an archive asks its site whether it changed (HEAD), a file that was
    read is asked for again with what the site said of it (If-None-Match: an unchanged one costs a 304), the others are read as
    new. Text layers only: a scan is queued for the OCR thread. Then the rows are noted (frontier.documents_read); the keys read."""
    from catix.docs import frontier
    from catix.docs.sources import archive_documents

    docs = all_docs()
    with httpx.Client(headers=HEADERS, timeout=60, follow_redirects=True) as client:
        for key in keys:
            if (d := docs.get(key)) is None:
                continue
            if archive_documents.is_archive(key, d) or d.get("archived"):
                try:
                    archive_documents.refresh(key, d, client)
                except httpx.HTTPError as e:
                    print(f"{key}: archive refresh failed: {e}")
            elif "sha256" in (note := notes.note(key, d.get("revision", ""))):
                notes.put_note(key, d.get("revision", ""), {**note, "refetch": True})
    done = _fetch_once(prefixes=tuple(keys), ocr=False)
    frontier.documents_read(keys)
    return done


def to_markdown(text: str) -> str:
    """Layout text -> markdown: chapters '## N. Title', clauses as paragraphs starting with their bold number, 3-space-gapped rows as tables.
    A text whose headings the OCR marked ('## 4 Процесс …', lighton) keeps them, and no line is guessed a chapter from its number:
    the guess took '1. Начало процесса:' (an item of a list) for one and missed '4 Процесс …' (a chapter with no dot)."""
    out, para, table, made = [], [], [], []
    text = GLUED.sub(lambda m: f"{m.group(1) or m.group(2)} ", text)  # a clause's number glued to its words (the text layer, OCR)
    flat = not re.search(r"^\s*(#{2,4} )?\d+\.\d+\.?\s", text, re.M)  # numbering 1., 2., 3. without chapters: every number opens a clause
    marked = re.search(r"^#{2,4} \S", text, re.M)  # (not '# Решение', a comment in the code of a course programme)

    def flush() -> None:
        nonlocal para, table, made
        if made:
            out.append("\n".join(made))
            made = []
        if para:
            out.append(" ".join(para))
            para = []
        if table:
            width = max(len(r) for r in table)
            rows = [r + [""] * (width - len(r)) for r in table]
            out.append("\n".join(["| " + " | ".join(rows[0]) + " |", "|" + " --- |" * width] + ["| " + " | ".join(r) + " |" for r in rows[1:]]))
            table = []

    for raw in text.replace("\f", "\n").splitlines():
        line = raw.strip()
        if not line or re.fullmatch(r"\d{1,3}", line):  # blank, or a page number
            flush()
            continue
        if marked and (heading := re.match(r"#{2,4} (\S.*)", line)):
            flush()
            if re.match(r"\d+(\.\d+)+\.?\s", title := heading.group(1)):  # a section of a chapter ('2.4 Работа в ЛВС') is a clause, as
                num, _, rest = title.partition(" ")                         # in the text layer: the cards cite it by its number
                para = [f"**{num}**", rest]
            else:
                out.append(f"## {title}")
            continue
        if line.startswith("| ") and line.endswith(" |") or re.fullmatch(r"\|( --- \|)+", line):  # a table the extraction already made
            if para or table:
                flush()
            made.append(line)
            continue
        if made:
            flush()
        cells = re.split(r"\s{3,}", line)
        if len(cells) >= 2 and not re.match(r"^\d+(\.\d+)+\.?\s", line):
            if para:
                flush()
            table.append(cells)
            continue
        if table:
            flush()
        if flat and re.match(r"^\d{1,3}\.\s+\S", line):  # (the rules of admission count to 130)
            flush()
            num, _, rest = line.partition(" ")
            para = [f"**{num}**", rest]
        elif not marked and re.match(r"^\d{1,2}\.\s+[А-ЯЁA-Z]", line) and not re.match(r"^\d+\.\d", line) and len(line) < 150 and not line.endswith((";", ",")):
            flush()
            out.append(f"## {line}")
        elif re.match(r"^\d+(\.\d+)+\.?\s", line):
            flush()
            num, _, rest = line.partition(" ")
            para = [f"**{num}**", rest]
        elif re.match(r"^(\d+\)|[а-яa-z]\)|[-–•])\s", line):
            flush()
            para = [f"- {line}"]
            flush()
        else:
            para.append(line)
    flush()
    return "\n\n".join(out)


def readable(text: str) -> bool:
    """Whether the text says anything: a short document is worth a page, only one with no letter or digit at all (empty, or
    nothing but lines, boxes and spaces: a scan that OCR could not read) is not."""
    return re.search(r"[^\W_]", text) is not None


def compile_all() -> list[Document]:
    """Every kept document -> a Document 'regulations/<key>', made by code on every run (title, date, audience, text, tables), so
    that a better extraction or a better title reaches the pages. No model: a description would retell the document's own
    title in English, its tags nothing reads; the audience follows from the section that lists it (AUDIENCE_OF_SECTION)."""
    from catix.docs.sources import archive_documents

    docs, out = all_docs(), []
    for key, d in docs.items():
        if archive_documents.is_archive(key, d):
            continue  # (a container has no page: its members have)
        meta = notes.note(key, d.get("revision", ""))
        if not meta or "sha256" not in meta:
            continue  # (a new revision is queued: the old member's text is not published)
        title = docs[key]["title"]  # (not the one stored at download time: the titles are made unique across all documents)
        text = notes.text(key, d.get("revision", ""))
        if text is None or not readable(text):
            print(f"{key}: no readable text, skipped")
            continue
        audience = d.get("audience") or AUDIENCE_OF_SECTION.get(d["section"], [])  # (a site that names its readers names those of its documents)
        body = to_markdown(text)
        issued, issued_from, precision = dated(text, title, meta["url"], d.get("member"), meta.get("pdf_created"), meta["fetched_at"])
        ocr = meta["method"].startswith("ocr")
        front = {"type": "regulation", "title": title, "resource": meta["url"],
                 **({"archive_member": d["member"], "archive_sha256": meta["sha256"]} if d.get("member") else {}),
                 **({"audience": audience} if audience else {}),
                 "source_kind": "official-document", "language": "ru", "section": meta.get("section", "document"),
                 "sources": [{"resource": meta["url"], "id": meta["sha256"][:12], "title": title, "last_modified": issued}],
                 "generated": {"by": f"{PRODUCER} regulations", "at": meta["fetched_at"]},
                 "extraction": meta["method"], "status": "draft",
                 **({"issued_from": issued_from, "issued_precision": precision} if issued_from else {}),
                 **({"review": "scanned document read by OCR: check numbers and dates against the PDF before relying on them"} if ocr else {})}
        if d.get("unlisted"):  # (no page of the site links it any more: removed or hidden; what it said stays, as possibly outdated)
            front["unlisted"] = d["unlisted"]
            front["stale_after"] = d["unlisted"] + "T00:00:00+00:00"
            body = f"> Ни одна видимая страница сайта не ссылается на этот документ (с {d['unlisted']}): ссылку убрали или скрыли, это может быть старая редакция.\n\n{body}"
        out.append(Document(f"regulations/{key}", front, f"# {title}\n\n{body}\n\n# Citations\n\n1. [{title}]({meta['url']}), file {meta['sha256'][:12]}\n"))
    return out


def main(args: Namespace) -> None:
    cmd = args.action
    if cmd == "fetch":
        ocr = not getattr(args, "no_ocr", False)
        if args.key:  # (one document, again, whatever its note says)
            try:
                force(args.key, now=args.now, ocr=ocr)
            except KeyError as e:
                raise SystemExit(str(e.args[0])) from None
            return
        print(f"{fetch(args.limit, ocr=ocr)} documents read")  # (the documents no run has read)
    elif cmd == "queue":
        from catix.docs.sources import ocr_queue

        ocr_queue.show()
