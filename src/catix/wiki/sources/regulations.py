"""Official regulations (PDF files on innopolis.university/sveden/document) as a second source of the bundle.

    catix-wiki regs fetch [N] [--no-ocr]   # every trusted link no run has processed: download and extract the documents, after each material follow
                                # links to documents on configured SITES providers; then read the pages of trusted sites that cached pages and
                                # documents link and no run has read (sites.fetch, only_new) and their documents, until nothing new comes
                                # (N: at most N documents, and no pages; --no-ocr: a scan is queued for a run with OCR, as the 6-hourly run does)
    catix-wiki regs reextract   # extract downloaded PDFs again; scans use chandra or its saved page HTML
    catix-wiki regs refresh     # ask the site (HEAD) whether a downloaded document changed; a changed one is downloaded again by fetch
    catix-wiki regs compile     # raw/regulations -> wiki/raw/regulations/<key>.md
    catix-wiki regs queue       # the OCR queue (every source's scans waiting for chandra) and the scans too long for it (ocr_queue.py)

The text of a regulation is NOT rewritten by the model: the program only turns the layout into markdown (chapters, clauses, tables)
and the clause numbers stay, so that a card can quote 'п. 5.3'. No model writes any of the page (compile_all).
These concepts carry `source_kind: official-document`; a scanned one also `extraction: ocr` and a `review:` note.
"""

import hashlib
import json
from collections import Counter
import re
import subprocess
import time
from argparse import Namespace
from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import httpx
from urllib.parse import unquote

from catix.settings import settings
from catix.wiki.compile import PRODUCER, yaml_value
from catix.wiki import paths
from catix.wiki.paths import RAW

ROOT = RAW / "regulations"
LINKED = ROOT / "linked.json"  # documents found in already processed trusted-provider materials
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


SVEDEN_ROOT = ROOT.parent / "sveden"
MAX_BYTES, MAX_PAGES, MAX_OCR_PAGES = 25_000_000, 150, 40  # one document may not take hours of OCR
QUEUED, TOO_LONG = "queued", "too long"  # a scan's "ocr" in its note: waits for a run with OCR / longer than MAX_OCR_PAGES, put aside (ocr_state)
MAX_FAILURES = 5  # network errors in a row before a run gives up
PAUSE = 2  # seconds between requests: the site blocked us once after a burst, so stay well below what it tolerates
OCR_BUDGET = 200  # pages of OCR per run of `regs fetch`; documents left over are done by the next run
AUDIENCE_OF_SECTION = {  # who a document is for, by the section of the site that lists it; a section of every kind of document names no one (everyone)
    "sveden/education": ["student", "postgraduate", "applicant", "teacher"],  # programmes, study plans, practice
    "sveden/eduStandarts": ["student", "postgraduate", "applicant", "teacher"],
    "sveden/apply": ["applicant"],
    "sveden/grants": ["student", "postgraduate"],  # scholarships, material support
    "sveden/paid_edu": ["student", "postgraduate", "applicant", "public"],  # contracts and prices, courses for anyone
    "sveden/struct": ["staff", "management"],  # the units' regulations
    "site/hotel": ["student", "postgraduate", "applicant", "public"],  # the dormitory's rules and prices, its guests
}


HEADERS = {"User-Agent": "catix-wiki/0.1 (Innopolis University assistant; polite crawl)"}
LOGIN = re.compile(r"(?i)(?:^|[./])(?:sso|adfs|idp|cas|auth|oauth2?|login|signin|sign-in|passport)(?:[./?]|$)")  # the host or path of a login


def a_login(resp: httpx.Response) -> bool:
    """Whether the page a site sent in place of a file is a login (help sends to the university's SSO) by its address or its
    password field, not a page of the site (university.innopolis.ru/files/ sends to the start page of innopolis.university)."""
    from catix.wiki.sources import sites

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


SIGNED = re.compile(r"\s*\(документ подписан (?:ПЭП|простой электронной подписью|электронной подписью)\)", re.I)  # says nothing about the content
GLUED = re.compile(r"^(\s*\d{1,2}(?:\.\d{1,2}){1,4}\.)(?=[^\W\d_]|«)|^(\s*\d{1,2}\.)(?=[А-ЯЁA-Z])", re.M)  # '3.2.Аспирант', '8.Во время'


def all_docs() -> dict[str, dict]:
    """Every document of the bundle's official source: the first regulations (DOCS) and those the model kept from the disclosure section (sveden.py)."""
    docs = {k: {"title": t, "url": BASE + p, "root": ROOT, "section": "document"} for k, (t, p) in DOCS.items()}
    index = {d["url"]: d for d in json.loads((SVEDEN_ROOT / "index.json").read_text(encoding="utf-8"))} if (SVEDEN_ROOT / "index.json").exists() else {}
    decisions = json.loads((SVEDEN_ROOT / "triage.json").read_text(encoding="utf-8")) if (SVEDEN_ROOT / "triage.json").exists() else {}
    known = {d["url"] for d in docs.values()}
    for url, dec in decisions.items():
        if dec["decision"] != "keep" or url not in index or url in known:
            continue
        d = index[url]
        title = SIGNED.sub("", d["title"]).strip()
        if len(title) < 30 or re.fullmatch(r"[\d\s./()–-]+", title) or title.lower().startswith(("учебный план", "календарный", "рабочая программа")):
            title = f"{d['context'][:220]} — {title}" if d.get("context") else title  # 'Study plan' alone says nothing: the programme is in the list it sits in
        key = "sveden-" + hashlib.sha1(url.encode()).hexdigest()[:8] + "-" + (re.sub(r"[^a-z0-9]+", "-", unquote(url.rsplit("/", 1)[-1]).lower()).strip("-")[:30] or "doc")
        docs[key] = {"title": title, "url": url, "root": SVEDEN_ROOT, "section": "sveden/" + d["sections"][0], "context": d.get("context", ""), "ext": d["ext"]}
    from catix.wiki.sources import sites

    have = {sites.canonical(d["url"]) for d in docs.values()}
    docs.update({k: d for k, d in sites.docs().items() if d["url"] not in have})  # the documents the sites link (the rules and prices of the dormitories); one sveden has is not read twice
    have |= {sites.canonical(d["url"]) for d in docs.values()}
    for url, found in linked_documents().items():
        if url in have:
            continue
        provider = found["provider"]
        docs[found["key"]] = {"title": found["title"], "url": url, "root": sites.ROOT / provider / "docs",
                               "section": f"site/{provider}", "ext": found["ext"]}
        have.add(url)
    if settings.wiki_mock_site:
        from catix.wiki.sources import mock

        docs.update(mock.docs())
    from catix.wiki.sources import archive_documents

    if any(d.get("ext") in archive_documents.EXTENSIONS for d in docs.values()):
        from catix.wiki.sources import rpd

        specialised = {sites.canonical(a["url"]) for a in rpd.archives()}
        docs = {key: d for key, d in docs.items() if sites.canonical(d["url"]) not in specialised}
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


def linked_documents() -> dict[str, dict]:
    """The documents found in extracted text, persisted so a later run resumes the graph."""
    if not LINKED.exists():
        return {}
    return json.loads(LINKED.read_text(encoding="utf-8")).get("documents", {})


def discover_linked_documents(docs: dict[str, dict] | None = None) -> dict[str, str]:
    """Remember new document links from trusted-provider materials (of `docs`, of every document when None): the key of each
    document added -> the key of the document whose text names it."""
    from catix.wiki.sources import crawl, sites

    registry = linked_documents()
    known = {sites.canonical(d["url"]) for d in all_docs().values()}
    found: dict[str, str] = {}
    source_docs = docs or all_docs()
    for key, d in source_docs.items():
        text_path = d["root"] / f"{key}.txt"
        if not text_path.exists():
            continue
        text = text_path.read_text(encoding="utf-8")
        for url in crawl.document_links(text, d["url"]):
            if url in known or url in registry:
                continue
            provider = crawl.provider(url)
            if provider is None:
                continue
            filename = unquote(url.rsplit("/", 1)[-1])
            stem, ext = filename.rsplit(".", 1)
            new = f"site-{provider}-linked-{hashlib.sha1(url.encode()).hexdigest()[:8]}-{re.sub(r'[^a-z0-9]+', '-', stem.lower()).strip('-')[:40] or 'document'}"
            registry[url] = {"key": new, "title": re.sub(r"\s+", " ", stem.replace("_", " ")).strip(), "ext": ext.lower(),
                             "provider": provider, "from": [d["url"]]}
            known.add(url)
            found[new] = key
    if found:
        LINKED.parent.mkdir(parents=True, exist_ok=True)
        LINKED.write_text(json.dumps({"documents": registry}, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    return found


def page_links_of(keys: Iterable[str] | None = None) -> dict[str, set[str]]:
    """provider -> the pages of trusted sites the text of the documents names (of those of `keys`, of every document read when
    None): the waves of sites.fetch and fetch_new read them, so a page only a document links (a regulation's 'see
    innopolis.university/...') is reached as the pages another site links are."""
    from catix.wiki.sources import crawl

    docs, found = all_docs(), {}
    for key in docs if keys is None else [k for k in keys if k in docs]:
        text_path = docs[key]["root"] / f"{key}.txt"
        if text_path.exists():
            for url in crawl.text_page_links(text_path.read_text(encoding="utf-8"), docs[key]["url"]):
                if provider := crawl.provider(url, page=True):
                    found.setdefault(provider, set()).add(url)
    return found


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
TABLES = 5  # the reading of the text layer: when it changes, `regs reextract` reads the text layers again (2: cells merged across columns, 3: a line on a table's edge once, 4: a table of one column is text, 5: opendataloader)


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


def layer_text(pdf: Path, converted: Path | None = None) -> tuple[str, str] | None:
    """(text, method) of the text layer when the PDF has one (opendataloader; pdfplumber when it could not read it, or read
    too little); None for a scan. `converted`: the PDF's JSON when many were converted at once."""
    from catix.wiki.sources import opendataloader

    pages = pages_of(pdf)
    text = opendataloader.text_of_pdf(pdf, converted)
    if text is not None and len(text.strip()) > 300 * pages:
        return text, TEXT_LAYER
    text, method = plumbed(pdf)
    if len(text.strip()) > 300 * pages:
        return text, method
    return None


def ocr_refused(pages: int, ocr_left: int) -> str | None:
    """Why a scan of `pages` is not read now (with `ocr_left` pages of OCR left), None when it is."""
    if pages > MAX_OCR_PAGES:
        return "scan too long for OCR"
    return "ocr deferred" if pages > ocr_left else None


def ocr_state(note: dict, limit: int | None = None) -> str | None:
    """What a document's note says of its scan: QUEUED (it waits for a run with OCR), TOO_LONG (longer than `limit` pages,
    MAX_OCR_PAGES by default: put aside, out of the queue, no run reads it), None (not a scan waiting). By the pages, not the
    word written: a note queued before the long ones were put aside is a long one, and a long one is queued again once the
    limit covers it."""
    if note.get("ocr") not in (QUEUED, TOO_LONG):
        return None
    return TOO_LONG if note.get("pages", 0) > (MAX_OCR_PAGES if limit is None else limit) else QUEUED


def scan_notes() -> Iterator[tuple[str, dict, dict]]:
    """(key, document, note) of every scan queued for OCR or put aside as too long (ocr_state)."""
    for key, d in all_docs().items():
        meta = d["root"] / f"{key}.json"
        if meta.exists() and ocr_state(note := json.loads(meta.read_text(encoding="utf-8"))):
            yield key, d, note


def queued() -> dict[str, int]:
    """The scans waiting for a manual run with OCR, key -> pages; not those too long for it (put aside: ocr_state)."""
    return {key: note.get("pages", 0) for key, _, note in scan_notes() if ocr_state(note) == QUEUED}


class NotRead(RuntimeError):
    """chandra did not read a scan. `away`: its server is gone (not the scan's fault); else a page of it failed."""

    def __init__(self, away: bool) -> None:
        super().__init__("chandra's server went away" if away else "chandra could not read a page of it")
        self.away = away


def ocr_text(pdf: Path) -> tuple[str, str]:
    """(text, method) of a scan by chandra alone; NotRead leaves the scan queued for a later attempt."""
    from catix.wiki.sources import chandra

    text = chandra.text_of_pdf(pdf, pdf.with_suffix(".chandra"))  # (its pages' HTML beside the PDF)
    if text is None or not text.strip():
        raise NotRead(away=not chandra.available())
    return text, chandra.METHOD


def read_scans[T](scans: list[T], pdf_of: Callable[[T], Path], read: Callable[[Path], tuple[str, str]] | None = None) -> Iterator[tuple[T, Future]]:
    """The scans read several at once, each (scan, its future of `read`, ocr_text by default) as it is done. As many scans as the OCR server
    has slots are open at a time, their pages in one queue (chandra.page_pool): a scan of 3 pages does not leave the other
    slots idle while it is read, as one at a time did (1Cat vLLM: 16.3 pages a minute at 16 at once, 11.8 at 6)."""
    from catix.wiki.sources import chandra

    pool, finished = ThreadPoolExecutor(settings.ocr_parallel, thread_name_prefix="scan"), False
    try:
        futures = {pool.submit(read or ocr_text, pdf_of(scan)): scan for scan in scans}
        for future in as_completed(futures):
            yield futures[future], future
        finished = True
    finally:
        if not finished:  # a stopped run (Ctrl-C) does not wait for the scans and pages queued behind the ones being read
            chandra.cancel_pages()
        pool.shutdown(wait=finished, cancel_futures=not finished)


def extract(pdf: Path, ocr_left: int, converted: Path | None = None) -> tuple[str | None, str, int]:
    """(text, method, OCR pages used): the text layer when there is one, else OCR of the page images; None when OCR is not
    allowed now. `converted`: the PDF's JSON when reextract converted many at once."""
    if (layer := layer_text(pdf, converted)) is not None:
        return *layer, 0
    pages = pages_of(pdf)
    if why := ocr_refused(pages, ocr_left):
        return None, why, 0
    return *ocr_text(pdf), pages


def _fetch_once(limit: int | None = None, prefixes: tuple[str, ...] | None = None, ocr: bool = True) -> list[str]:
    """Download the documents not read yet (and those `refresh` found changed), then read them: the text layers all at once
    (one run of opendataloader's JVM, not one a file), the scans after them; the keys of those read. `prefixes`: only the
    documents whose key starts with one of them ('site-lab-': the documents of one site). Without `ocr` a scan (a PDF the text
    layer gives too little of) is not read: it is queued (`"ocr": "queued"` in its note) for a run with OCR, which reads it
    without asking its text layer again; the runs without OCR pass it by (the 6-hourly run needs no OCR model up).
    A scan chandra does not read stays queued, regardless of the number of failed attempts. A scan longer than MAX_OCR_PAGES
    is not queued: it is put aside (`"ocr": "too long"`), and no run reads it or asks its text layer again until the limit
    covers it or the file changes on the site (ocr_state; `catix-wiki regs queue` lists them apart).

    Every download ends in a note: a document no file came for (a host that does not answer, a login it was sent to) is
    `failed`, and no run asks it again before sites.RETRY; without the note every run asked it again (olymp.innopolis.ru has
    no address any more, university.innopolis.ru/files/ sends to the university's start page). A host that fails
    MAX_FAILURES times in a row is let be for the rest of the run; the other hosts are read (a dead host stopped the whole run)."""
    from catix.wiki.sources import archive_documents, opendataloader, sites

    # Pick up university-hosted files already present in compiled site pages;
    # the site crawl itself records the links it saw while reading a page.
    sites.collect_linked_docs()

    def skip(d: dict, meta: Path, why: str) -> None:
        meta.write_text(json.dumps({"title": d["title"], "url": d["url"], "skipped": why}), encoding="utf-8")

    def put_off(d: dict, meta: Path, old: dict, why: str) -> None:
        """No file this time: why and when, and what an earlier run read of the document stays (its text, its page)."""
        meta.write_text(json.dumps({**old, "title": d["title"], "url": d["url"], "failed": why,
                                    "tried_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}, ensure_ascii=False, indent=1), encoding="utf-8")

    removed = archive_documents.prepare(all_docs(), prefixes)
    docs, failures, downloaded, queued = all_docs(), Counter(), [], set()
    for key, d in docs.items():
        if archive_documents.is_archive(key, d) or prefixes and not key.startswith(prefixes):
            continue
        root: Path = d["root"]
        root.mkdir(parents=True, exist_ok=True)
        ext = d.get("ext", "pdf")
        src, meta = root / f"{key}.{ext}", root / f"{key}.json"
        old = json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else {}
        if ocr_state(old) == TOO_LONG and not old.get("refetch"):  # (put aside: no run reads it, its text layer is not asked again)
            if old["ocr"] != TOO_LONG:  # (queued before the long scans were put aside)
                meta.write_text(json.dumps({**old, "ocr": TOO_LONG}, ensure_ascii=False, indent=1), encoding="utf-8")
            continue
        waiting = ocr_state(old) == QUEUED and src.exists()  # (a scan queued by a run without OCR, downloaded already)
        if not waiting and old and ((root / f"{key}.txt").exists() or "skipped" in old) and not old.get("refetch"):
            continue  # (a document that changed on the site is noticed by `regs refresh`; a skipped one stays skipped)
        if waiting and not ocr:
            continue
        host = httpx.URL(d["url"]).host
        if not src.exists() and (old.get("failed") and sites.recent(old.get("tried_at")) or failures[host] >= MAX_FAILURES):
            continue  # (no file came lately: asked again after RETRY; its host stopped answering in this run: the next run asks)
        if limit is not None and len(downloaded) >= limit:
            break
        print(key, flush=True)
        if not src.exists():
            if d.get("member") or d.get("archive_root"):
                print("  archive-managed source is missing locally: left for the next archive read")
                continue  # members and standalone PDFs must be downloaded through the archive boundary
            try:
                resp = httpx.get(d["url"], timeout=120, follow_redirects=True, headers=HEADERS)
                resp.raise_for_status()
                if len(resp.content) > MAX_BYTES:
                    print(f"  too big ({len(resp.content) // 1_000_000} MB), skipped")
                    skip(d, meta, "file too big")
                    continue
                if ext not in ("htm", "html") and re.match(rb"\s*<(!doctype html|html)\b", resp.content[:200], re.I):
                    if resp.url.host != host and a_login(resp):  # (help: the university's SSO): not skipped, read once someone logged in fetches it
                        print(f"  sent to the login of {resp.url.host}: asked again in {sites.RETRY.days} days, or read once a person puts the file beside its note")
                        put_off(d, meta, old, f"sent to the login of {resp.url.host}")
                    else:  # a broken link the site answers with one of its pages (or with the start page of another host of it)
                        print("  the site answers with a page, not the file, skipped" + (f" ({resp.url})" if resp.url.host != host else ""))
                        skip(d, meta, "a page, not the file")
                    time.sleep(PAUSE)
                    continue
            except httpx.HTTPError as e:  # a moved file must not stop the others
                print(f"  FAILED: {e}")
                if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 404:  # a dead link on the site itself
                    skip(d, meta, "404 on the site")
                    failures[host] = 0
                    time.sleep(PAUSE)
                    continue
                failures[host] += 1
                put_off(d, meta, old, f"{type(e).__name__}: {str(e)[:200]}")
                if failures[host] >= MAX_FAILURES:  # the host refuses connections: going on would only hammer it
                    print(f"  {failures[host]} failures in a row: {host} is not answering, its other documents wait for the next run")
                time.sleep(PAUSE + 5 * failures[host])  # slower while the host is failing
                continue
            failures[host] = 0
            src.write_bytes(resp.content)
            remote = signature(resp.headers)
            time.sleep(PAUSE)
        else:
            remote = old.get("remote", {})
        try:
            pdf = to_pdf(src)
            if not pdf.exists() or pages_of(pdf) > MAX_PAGES:
                raise ValueError("cannot read or too long")
        except (ValueError, subprocess.SubprocessError, AttributeError) as e:
            print(f"  skipped: {e}")
            skip(d, meta, str(e))
            continue
        downloaded.append((key, d, src, pdf, meta, old, remote))
        if waiting:
            queued.add(key)
    print(f"{len(downloaded)} documents to read" + (f", {len(queued)} of them scans queued for OCR" if queued else ""), flush=True)

    def store_new(item: tuple, text: str, method: str) -> None:
        key, d, src, _, meta, old, remote = item
        sha = hashlib.sha256(src.read_bytes()).hexdigest()
        (d["root"] / f"{key}.txt").write_text(text, encoding="utf-8")
        meta.write_text(json.dumps({"title": d["title"], "url": d["url"], "sha256": sha, "method": method, "chars": len(text), "tables": TABLES, "section": d["section"], "context": d.get("context", ""),
                                    "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "remote": remote}, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{key}: {len(text)} chars by {method}" + (" (a new version)" if old.get("sha256") and old["sha256"] != sha else ""), flush=True)

    def queue(item: tuple, pages: int, state: str = QUEUED, **more: object) -> None:
        """The scan's note: QUEUED for a run with OCR, or TOO_LONG, put aside. (`refetch` is done: the file was downloaded again.)"""
        _, d, _, _, meta, old, remote = item
        old = {k: v for k, v in old.items() if k not in ("refetch", "failed", "tried_at")}
        meta.write_text(json.dumps({**old, "title": d["title"], "url": d["url"], "ocr": state, "pages": pages, "remote": remote,
                                    "queued_at": old.get("queued_at") or datetime.now(timezone.utc).isoformat(timespec="seconds"), **more},
                                   ensure_ascii=False, indent=1), encoding="utf-8")

    ocr_left, done, scans = OCR_BUDGET, list(removed), []
    with opendataloader.converted([pdf for key, _, _, pdf, _, _, _ in downloaded if key not in queued]) as jsons:
        for item in downloaded:
            key, d, src, pdf, meta, old, remote = item
            if key not in queued:
                try:
                    layer = layer_text(pdf, jsons.get(pdf))
                except (ValueError, subprocess.SubprocessError, AttributeError) as e:
                    print(f"{key}: skipped: {e}")
                    skip(d, meta, str(e))
                    continue
                if layer is not None:
                    store_new(item, *layer)
                    done.append(key)
                    continue
            pages = pages_of(pdf)  # a scan: its pages are taken from the budget now, it is read with the others after the loop
            if pages > MAX_OCR_PAGES:  # (not queued: it would wait in the queue for ever)
                print(f"{key}: a scan of {pages} pages, longer than {MAX_OCR_PAGES}: put aside, not queued for OCR")
                queue(item, pages, TOO_LONG)
                continue
            if not ocr:
                print(f"{key}: a scan of {pages} pages, queued for a run with OCR")
            elif why := ocr_refused(pages, ocr_left):
                print(f"{key}: {why}")
            else:
                ocr_left -= pages
                scans.append(item)
                continue
            if key not in queued or old.get("ocr") != QUEUED:  # (the next runs do not ask its text layer again; a long one the limit covers now is queued)
                queue(item, pages)
    if scans:
        print(f"{len(scans)} scans to read by OCR ({OCR_BUDGET - ocr_left} pages)", flush=True)
    for item, future in read_scans(scans, lambda item: item[3]):
        try:
            text, method = future.result()
        except NotRead as e:
            failed = item[5].get("ocr_failed", 0) + (not e.away)
            print(f"{item[0]}: {e}: stays queued for the next run with OCR" + (f" (chandra failed on it {failed} times)" if failed else ""), flush=True)
            queue(item, pages_of(item[3]), **({"ocr_failed": failed} if failed else {}))
            continue
        except (ValueError, subprocess.SubprocessError, AttributeError) as e:
            print(f"{item[0]}: skipped: {e}")
            skip(item[1], item[4], str(e))
            continue
        store_new(item, text, method)
        done.append(item[0])
    print(f"{len(done)} documents fetched" + (f"; OCR pages left in the budget: {ocr_left}" if ocr else "; scans wait for a run with OCR"))
    return done


def fetch(limit: int | None = None, prefixes: tuple[str, ...] | None = None, ocr: bool = True) -> int:
    """The documents not read yet, read (read_new); how many."""
    return len(read_new(limit, prefixes, ocr))


def read_new(limit: int | None = None, prefixes: tuple[str, ...] | None = None, ocr: bool = True) -> list[str]:
    """Fetch documents and recursively queue links to documents on configured providers; the keys of those read. Without
    `ocr` the scans are queued for a run with OCR; those chandra does not read stay queued too (_fetch_once).

    The existing SITES entries decide which providers and paths are trusted. A
    newly found document is persisted before the next pass, so an interrupted
    crawl resumes without rereading completed files.

    A pass after the first reads the documents found in the one before, of any trusted provider, and no other document not
    read yet. With `prefixes` (a run of a few sites) only those a document of the prefixes or one this run read names: the
    pass that read every document no run had read yet took 54 of the university's for a request for the hotel. Every link
    found is remembered all the same (every document is looked at: an old document may name a site approved since), and
    the weekly run, which has no prefixes, reads them.
    """
    read, remaining, scope = [], limit, prefixes
    while True:
        done = _fetch_once(remaining, scope, ocr)
        read += done
        if remaining is not None:
            remaining -= len(done)
            if remaining <= 0:
                break
        reached = set(read)
        scope = tuple(new for new, source in discover_linked_documents().items()  # (recursion may cross from one trusted provider to another)
                      if prefixes is None or source.startswith(prefixes) or source in reached)
        if not scope:
            break
    return read


def refresh(prefix: str = "") -> int:
    """Ask the site (HEAD, one request every PAUSE seconds) whether each downloaded document is still the same file. A changed
    one is marked `refetch`: the next `fetch` downloads and reads it again (its page stays until then). The first check of a
    document only records what the site says about it. The number of changed documents."""
    from catix.wiki.sources import archive_documents

    found, failures = 0, 0
    with httpx.Client(headers=HEADERS, timeout=60, follow_redirects=True) as client:
        for key, d in all_docs().items():
            if d.get("member") or not key.startswith(prefix):
                continue
            if archive_documents.is_archive(key, d) or d.get("archive_root"):
                try:
                    found += archive_documents.refresh(key, d, client)
                except httpx.HTTPError as e:
                    print(f"{key}: archive refresh failed: {e}")
                time.sleep(PAUSE)
                continue
            path = d["root"] / f"{key}.json"
            meta = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            if not key.startswith(prefix) or "sha256" not in meta or meta.get("refetch"):
                continue
            try:
                resp = client.head(d["url"])
            except httpx.HTTPError as e:
                failures += 1
                print(f"{key}: {e}")
                if failures >= MAX_FAILURES:
                    print(f"{failures} failures in a row: the site is not answering, stopped")
                    break
                time.sleep(PAUSE + 5 * failures)
                continue
            failures = 0
            time.sleep(PAUSE)
            if resp.status_code != 200:  # (a document gone from the list of the site leaves the bundle through `sveden discover`)
                continue
            now = signature(resp.headers)
            if changed(meta.get("remote"), now):
                meta["refetch"] = True
                for old_file in {d["root"] / f"{key}.{d.get('ext', 'pdf')}", d["root"] / f"{key}.pdf"}:  # (and the PDF made of a Word file)
                    old_file.unlink(missing_ok=True)
                found += 1
                print(f"{key}: changed on the site")
            elif not meta.get("remote"):
                meta["remote"] = now
            else:
                continue
            path.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{found} documents changed on the site")
    return found


def to_markdown(text: str) -> str:
    """Layout text -> markdown: chapters '## N. Title', clauses as paragraphs starting with their bold number, 3-space-gapped rows as tables.
    A text whose headings the OCR marked ('## 4 Процесс …', chandra) keeps them, and no line is guessed a chapter from its number:
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
    """Enough words to be worth a page (a scan that OCR could not read, a form with only lines and boxes, is not), or a table
    of data under its heading (an exam's results, the places for admission: few words, the rows say it)."""
    words = len(re.findall(r"[^\W\d_]{3,}", text))
    return words >= 60 or words >= 30 and re.search(r"^\|.*\d.*\|$", text, re.M) is not None


def compile_all() -> None:
    """Every kept document -> wiki/raw/regulations/<key>.md, made by code on every run (title, date, audience, text, tables), so
    that a better extraction or a better title reaches the pages. No model: a description would retell the document's own
    title in English, its tags nothing reads; the audience follows from the section that lists it (AUDIENCE_OF_SECTION)."""
    from catix.wiki.sources import archive_documents

    paths.DOCS.joinpath("regulations").mkdir(parents=True, exist_ok=True)
    docs = all_docs()
    for page in paths.DOCS.joinpath("regulations").glob("sveden-*.md"):
        if page.stem not in docs:  # the document is no longer kept (a new decision of the triage, or it left the site)
            page.unlink()
            print(f"{page.stem}: no longer kept, page removed")
    for page in paths.DOCS.joinpath("regulations").glob("*-member-*.md"):
        if page.stem not in docs and "\narchive_member:" in page.read_text(encoding="utf-8"):
            page.unlink()  # only a successfully published archive manifest can remove its old members
    written = 0
    for key, d in docs.items():
        if archive_documents.is_archive(key, d):
            if archive_documents.load(key, d).get("status") == "ready":
                # A URL that used to deliver a standalone PDF now delivers a validated container.
                (paths.DOCS / "regulations" / f"{key}.md").unlink(missing_ok=True)
            continue
        root: Path = d["root"]
        if not (root / f"{key}.json").exists():
            continue
        meta = json.loads((root / f"{key}.json").read_text(encoding="utf-8"))
        target = paths.DOCS / "regulations" / f"{key}.md"
        if "sha256" not in meta:
            if d.get("member"):
                target.unlink(missing_ok=True)  # a new revision is queued: do not publish the old member's text
            continue
        title = docs[key]["title"]  # (not the one stored at download time: the titles are made unique across all documents)
        text = (root / f"{key}.txt").read_text(encoding="utf-8")
        if not readable(text):
            print(f"{key}: no readable text, skipped")
            continue
        old = target.read_text(encoding="utf-8") if target.exists() else ""
        audience = d.get("audience") or AUDIENCE_OF_SECTION.get(d["section"], [])  # (a site that names its readers names those of its documents)
        body = to_markdown(text)
        issued = issued_of(text, meta["fetched_at"])
        ocr = meta["method"].startswith("ocr")
        front = ["---", "type: regulation", f"title: {yaml_value(title)}", f"resource: {yaml_value(meta['url'])}",
                 *([f"archive_member: {yaml_value(d['member'])}"] if d.get("member") else []), *([f"audience: {yaml_value(audience)}"] if audience else []),
                 "source_kind: official-document", "language: ru", f"section: {yaml_value(meta.get('section', 'document'))}",
                 "sources:", f"  - resource: {yaml_value(meta['url'])}", f"    id: {yaml_value(meta['sha256'][:12])}", f"    title: {yaml_value(title)}", f"    last_modified: {yaml_value(issued)}",
                 "generated:", f"  by: {yaml_value(PRODUCER + ' regulations')}", f"  at: {yaml_value(meta['fetched_at'])}",
                 f"extraction: {yaml_value(meta['method'])}", "status: draft",
                 *(['review: "scanned document read by OCR: check numbers and dates against the PDF before relying on them"'] if ocr else []), "---"]
        page = "\n".join(front) + f"\n\n# {title}\n\n{body}\n\n# Citations\n\n1. [{title}]({meta['url']}), file {meta['sha256'][:12]}\n"
        if page != old:
            target.write_text(page, encoding="utf-8")
            written += 1
            if not old:
                print(f"{key}: {len(body)} chars of markdown")
    print(f"{written} pages written")


def reextract() -> None:
    """The text of every downloaded PDF that has a text layer, extracted again if it was read the old way or before the
    reading of tables changed (TABLES); and every scan not read by chandra, when its server answers (hours: a scan is
    written as soon as it is read, so a stopped run goes on where it was). A text that comes out the same is not written:
    its page does not change. opendataloader reads them a hundred at a time (a JVM a run)."""
    from catix.wiki.sources import chandra, opendataloader

    todo, scans, remade = [], [], 0
    for key, d in all_docs().items():
        root: Path = d["root"]
        meta_path = root / f"{key}.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        method = str(meta.get("method", ""))
        if not (root / f"{key}.pdf").exists():
            continue
        if method == chandra.METHOD:  # made again from the HTML kept of its pages: the way it becomes text may have changed
            if (text := chandra.kept_text(root / f"{key}.chandra")) is not None:
                remade += store(key, root, meta_path, meta, text, method)
        elif method.startswith("ocr"):
            scans.append((key, root, meta_path, meta))
        elif method.startswith("text layer") and not (method in (TEXT_LAYER, PDFPLUMBER) and meta.get("tables") == TABLES):
            todo.append((key, root, meta_path, meta))
    print(f"{remade} scans read by {chandra.METHOD} came out different from the HTML of their pages")
    print(f"{len(todo)} documents to read again", flush=True)
    with opendataloader.converted([root / f"{key}.pdf" for key, root, _, _ in todo]) as jsons:
        done = sum(read_again(key, root, meta_path, meta, jsons.get(root / f"{key}.pdf")) for key, root, meta_path, meta in todo)
    print(f"{done} documents read again came out different")
    if scans and not chandra.available():
        print(f"{len(scans)} scans not read by {chandra.METHOD}: its server ({settings.ocr_route}) does not answer, left as they are")
    elif scans:
        done, to_read = 0, []
        with opendataloader.converted([root / f"{key}.pdf" for key, root, _, _ in scans]) as jsons:
            for scan in scans:  # (one that has a text layer now is read by it; one too long for OCR is left)
                key, root, meta_path, meta = scan
                pdf = root / f"{key}.pdf"
                try:
                    layer = layer_text(pdf, jsons.get(pdf))
                except (ValueError, subprocess.SubprocessError) as e:
                    print(f"{key}: {e}")
                    continue
                if layer is not None:
                    done += store(key, root, meta_path, meta, *layer)
                elif why := ocr_refused(pages_of(pdf), MAX_OCR_PAGES):
                    print(f"{key}: {why}")
                else:
                    to_read.append(scan)
        print(f"{len(to_read)} scans to read again by {chandra.METHOD} ({sum(pages_of(root / f'{key}.pdf') for key, root, _, _ in to_read)} pages)", flush=True)
        for n, ((key, root, meta_path, meta), future) in enumerate(read_scans(to_read, lambda scan: scan[1] / f"{scan[0]}.pdf"), 1):
            print(f"[{n}/{len(to_read)}] {key}", flush=True)  # (a scan is written as soon as it is read: a stopped run goes on where it was)
            try:
                done += store(key, root, meta_path, meta, *future.result())
            except (NotRead, ValueError, subprocess.SubprocessError) as e:
                print(f"{key}: {e}")
        print(f"{done} scans read again came out different")


def read_again(key: str, root: Path, meta_path: Path, meta: dict, converted: Path | None, ocr_left: int = 0) -> bool:
    """A document read again (reextract): whether its text changed. A scan is read again only with `ocr_left` pages."""
    try:
        text, method, _ = extract(root / f"{key}.pdf", ocr_left, converted)
    except (NotRead, ValueError, subprocess.SubprocessError) as e:
        print(f"{key}: {e}")
        return False
    return text is not None and store(key, root, meta_path, meta, text, method)


def store(key: str, root: Path, meta_path: Path, meta: dict, text: str, method: str) -> bool:
    """A text read again, written when it differs: whether it did."""
    txt = root / f"{key}.txt"
    same = txt.exists() and txt.read_text(encoding="utf-8") == text
    if not same:
        txt.write_text(text, encoding="utf-8")
    meta_path.write_text(json.dumps({**meta, "method": method, "chars": len(text), "tables": TABLES}, ensure_ascii=False, indent=1), encoding="utf-8")
    if not same:
        print(f"  {key}: the text changed ({method})", flush=True)
    return not same


def main(args: Namespace) -> None:
    cmd = args.action
    if cmd == "fetch":
        from catix.wiki.sources import sites

        ocr = not getattr(args, "no_ocr", False)
        read = fetch(args.limit, ocr=ocr)  # (the documents no run has read, and those they name)
        if args.limit is None:  # (then the pages of trusted sites no run has read, their documents, ...; N: a quick run of documents only)
            read += sites.fetch(only_new=True, documents=True, ocr=ocr)
        print(f"{read} documents and pages read")
    elif cmd == "compile":
        compile_all()
    elif cmd == "reextract":
        reextract()
    elif cmd == "refresh":
        refresh()
    elif cmd == "queue":
        from catix.wiki.sources import ocr_queue

        ocr_queue.show()
