"""Past exam papers of the English bachelor programmes: a public Notion database the students keep ("IU B23 Academic
Materials", Past Papers [EN programs]), with the subject, the year, the name of the exam and its file.

    catix-docs papers fetch      # the rows of the database and the files not read yet (one request every PAUSE seconds)
    catix-docs papers status

Not an official source: the students collected the papers, a paper may be a variant or a reconstruction. The pages are
made by code only (no model): the list of a subject's papers, newest first, each with a link to its row in Notion and the
text of its file (the text layer; scans wait for a manual run with chandra, those over MAX_SCAN_PAGES are put aside:
`catix-docs regs queue` shows both). They answer "what was on the exam", not "what are the rules".
"""

import hashlib
import re
import subprocess
import tempfile
import time
from argparse import Namespace
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

import httpx

from catix.docs import files
from catix.docs.store import PRODUCER, Document
from catix.docs.sources import regulations
from catix.docs.sources.rpd import latin

SITE = "https://glebpopov.notion.site"
PAGE = "4ef3de0c-7e68-495b-89ef-086301361603"  # the database's own page
TITLE = "IU B23 Academic Materials: Past Papers [EN programs]"
ROOT = "past-papers"
INDEX = f"{ROOT}/index.json"  # row id -> the row and its files
FOLDER = "past-papers"
PAUSE = 2
MAX_CHARS = 8000  # of one paper on the page: the start says what was asked, a long one is in its file
OCR_PAGES = 120  # per run: scans left over are read by the next run
MAX_SCAN_PAGES = 20  # of one scan: a longer one is put aside ("ocr": "too long"), not queued (regulations.ocr_state)


def _value(record: dict) -> dict:
    """A record of Notion's API, whichever of its two wrappings it comes in."""
    value = record.get("value", {})
    return value.get("value", value) if isinstance(value, dict) else {}


def _post(client: httpx.Client, method: str, body: dict) -> dict:
    resp = client.post(f"{SITE}/api/v3/{method}", json=body)
    resp.raise_for_status()
    time.sleep(PAUSE)
    return resp.json()


def rows(client: httpx.Client) -> list[dict]:
    """Every row of the database: id, subject, year, exam, files [(name, url)]. The first view of the page shows them all."""
    chunk = _post(client, "loadCachedPageChunkV2", {"page": {"id": PAGE}, "limit": 50, "cursor": {"stack": []}, "verticalColumns": False})["recordMap"]
    page = _value(chunk["block"][PAGE])
    space, view = page["space_id"], page["view_ids"][0]
    collection = _value(next(iter(chunk["collection"].values())))
    names = {key: prop["name"] for key, prop in collection["schema"].items()}
    data = _post(client, "queryCollection", {
        "source": {"type": "collection", "id": collection["id"], "spaceId": space},
        "collectionView": {"id": view, "spaceId": space},
        "loader": {"type": "reducer", "reducers": {"collection_group_results": {"type": "results", "limit": 2000}}, "searchQuery": "", "userTimeZone": "Europe/Moscow"},
    })
    out = []
    for record in data["recordMap"]["block"].values():
        block = _value(record)
        if block.get("parent_table") != "collection" or block.get("alive") is False:
            continue
        props = {names.get(k, k): v for k, v in (block.get("properties") or {}).items()}
        text = lambda name: "".join(part[0] for part in props.get(name, [])).strip()  # noqa: E731
        attached = [(part[0], part[1][0][1]) for part in props.get("File", []) if len(part) > 1 and part[1] and part[1][0][0] == "a"]
        out.append({"id": block["id"], "space": space, "subject": text("Subject"), "year": text("Year"), "exam": text("Exam") or text("title"), "files": attached})
    return out


def load() -> dict:
    return files.read_json(INDEX) or {}


def save(index: dict) -> None:
    files.write_json(INDEX, index)


def file_key(url: str) -> str:
    return hashlib.sha1(url.split("?")[0].encode()).hexdigest()[:12]


TOO_LONG_FOR_OCR = "scan too long for OCR"


def read_pdf(path, ocr_left: int = 20) -> tuple[str | None, str]:
    """The text layer, else chandra within the page budget. None means queued, or put aside when the scan is longer than
    MAX_SCAN_PAGES (TOO_LONG_FOR_OCR); NotRead means chandra failed."""
    pages = regulations.pages_of(path)
    text = subprocess.run(["pdftotext", str(path), "-"], capture_output=True, text=True).stdout
    if len(re.findall(r"[^\W\d_]{3,}", text)) >= 15 * max(1, pages) or len(text.strip()) > 300 * pages:
        return text, "text layer"
    if pages > MAX_SCAN_PAGES:
        return None, TOO_LONG_FOR_OCR
    if ocr_left <= 0 or pages > ocr_left:
        return None, "scan queued for OCR"
    return regulations.ocr_text(path)


def fetch(ocr: bool = True) -> int:
    """New rows and the files not read yet (a file is downloaded into a temporary folder and deleted after it is read; a scan queued
    for OCR is downloaded again by a run with OCR); a row gone from the database leaves the index. The number of rows added,
    changed or removed."""
    index, changed, ocr_left = load(), 0, OCR_PAGES
    with tempfile.TemporaryDirectory(prefix="catix-docs-") as tmp, httpx.Client(headers=regulations.HEADERS, timeout=120, follow_redirects=True) as client:
        found = rows(client)
        for row in found:
            old = index.get(row["id"], {})
            entry = {**{k: row[k] for k in ("subject", "year", "exam")}, "files": dict(old.get("files", {}))}  # (a copy: else the old entry changes too and nothing looks changed)
            for name, url in row["files"]:
                key = file_key(url)
                if key in entry["files"] and ("sha256" in entry["files"][key] or "skipped" in entry["files"][key]):
                    continue
                if regulations.ocr_state(note := entry["files"].get(key, {}), MAX_SCAN_PAGES) == regulations.TOO_LONG:
                    entry["files"][key] = {**note, "ocr": regulations.TOO_LONG}  # (put aside; one queued before that is marked so)
                    continue
                if not name.lower().endswith(".pdf"):
                    entry["files"][key] = {"name": name, "skipped": "not a PDF"}
                    continue
                path = Path(tmp) / f"{key}.pdf"
                waiting = regulations.ocr_state(note, MAX_SCAN_PAGES) == regulations.QUEUED
                if waiting and not ocr:
                    continue
                signed = f"{SITE}/signed/{quote(url, safe='')}?table=block&id={row['id']}&spaceId={row['space']}"
                try:
                    resp = client.get(signed)
                    resp.raise_for_status()
                except httpx.HTTPError as e:
                    print(f"  FAILED {name}: {e}")
                    time.sleep(PAUSE)
                    continue
                time.sleep(PAUSE)
                path.write_bytes(resp.content)
                pages = regulations.pages_of(path)
                try:
                    if waiting:
                        text, method = regulations.ocr_text(path) if ocr and ocr_left > 0 and pages <= min(MAX_SCAN_PAGES, ocr_left) else (None, "scan queued for OCR")
                    else:
                        text, method = read_pdf(path, ocr_left=ocr_left if ocr else 0)
                    if method.startswith("ocr"):
                        ocr_left -= pages
                except regulations.NotRead as e:
                    text, method = None, str(e)
                    ocr_left -= pages
                if text is None:
                    entry["files"][key] = {"name": name, "ocr": regulations.TOO_LONG if method == TOO_LONG_FOR_OCR else regulations.QUEUED, "pages": pages}
                else:
                    files.write_text(f"{ROOT}/{key}.txt", text)
                    entry["files"][key] = {"name": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "method": method, "chars": len(text)}
                print(f"  {row['subject']} {row['year']} {row['exam']}: {name}, {method}")
            if entry != old:
                index[row["id"]] = entry
                changed += 1
                save(index)
        for gone in set(index) - {row["id"] for row in found} if found else ():
            del index[gone]
            changed += 1
    save(index)
    print(f"{len(found)} rows, {changed} new, changed or gone")
    return changed


def _year(entry: dict) -> int:
    return int(entry["year"]) if entry["year"].isdigit() else 0


def compile_all() -> list[Document]:
    """One document per subject, 'past-papers/<subject>': its papers, newest first, each with its link and the start of its text."""
    by_subject: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for row_id, entry in load().items():
        if entry["subject"]:
            by_subject[entry["subject"]].append((row_id, entry))
    out = []
    for subject, papers in sorted(by_subject.items()):
        key = latin(subject) or "subject"
        papers.sort(key=lambda p: (-_year(p[1]), p[1]["exam"]))
        years = sorted({_year(e) for _, e in papers if _year(e)})
        span = f"{years[0]}–{years[-1]}" if len(years) > 1 else (str(years[0]) if years else "")
        title = f"Past exam papers: {subject}"
        desc = f"Past exams and tests of {subject} at Innopolis University ({len(papers)} papers{', ' + span if span else ''}), collected by students: tasks, formats, points."
        resource = f"{SITE}/{PAGE.replace('-', '')}"
        body = [f"Exams and tests of **{subject}** from previous years, as the students collected them in [{TITLE}]({resource}). "
                "Not an official source: a paper may be one variant of several, or written down from memory. Newest first.", ""]
        for row_id, entry in papers:
            link = f"{SITE}/{row_id.replace('-', '')}"
            body += [f"## {entry['year'] or 'Year unknown'}: {entry['exam']}", "", f"Files: [{', '.join(f['name'] for f in entry['files'].values()) or 'the row'}]({link})", ""]
            for fkey, f in entry["files"].items():
                if "sha256" not in f or (paper := files.read_text(f"{ROOT}/{fkey}.txt")) is None:
                    continue
                text = re.sub(r"\n{3,}", "\n\n", paper.replace("\f", "\n")).strip()
                text = re.sub(r"(?m)^(#+)", r"\\\1", text)  # (a line of the paper that starts with '#' is not a heading of the page)
                cut = text[:MAX_CHARS] + ("\n\n(the rest is in the file)" if len(text) > MAX_CHARS else "")
                body += [f"### {f['name']}" if len(entry["files"]) > 1 else "", cut, ""]
        meta = {"type": "page", "title": title, "description": desc, "resource": resource,
                "tags": ["past-papers", "exams", "bachelor", latin(subject)], "audience": ["student"], "source_kind": "community",
                "language": "en", "section": "notion/past-papers", "subject": subject,
                "sources": [{"resource": resource, "title": TITLE}],
                "generated": {"by": f"{PRODUCER} past-papers (code only, no model)"}, "status": "draft"}
        out.append(Document(f"{FOLDER}/{key}", meta, f"# {title}\n\n" + "\n".join(line for line in body).strip() + f"\n\n# Citations\n\n1. [{TITLE}]({resource})\n"))
    return out


def status() -> None:
    index = load()
    papers = [f for e in index.values() for f in e["files"].values()]
    print(f"{len(index)} rows, {len(papers)} files: {sum('sha256' in f for f in papers)} read, {sum('skipped' in f for f in papers)} skipped, "
          f"{sum(regulations.ocr_state(f, MAX_SCAN_PAGES) == regulations.QUEUED for f in papers)} scans queued for OCR, "
          f"{sum(regulations.ocr_state(f, MAX_SCAN_PAGES) == regulations.TOO_LONG for f in papers)} too long for it")


def main(args: Namespace) -> None:
    cmd = args.action
    if cmd == "fetch":
        fetch()
    elif cmd == "status":
        status()
