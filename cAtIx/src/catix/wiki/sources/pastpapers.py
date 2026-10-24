"""Past exam papers of the English bachelor programmes: a public Notion database the students keep ("IU B23 Academic
Materials", Past Papers [EN programs]), with the subject, the year, the name of the exam and its file.

    catix-wiki papers fetch      # the rows of the database and the files not read yet -> raw/past-papers/ (one request every PAUSE seconds)
    catix-wiki papers compile    # raw/past-papers -> wiki/past-papers/<subject>.md, one page per subject
    catix-wiki papers status

Not an official source: the students collected the papers, a paper may be a variant or a reconstruction. The pages are
made by code only (no model): the list of a subject's papers, newest first, each with a link to its row in Notion and the
text of its file (the text layer; a scan is read by OCR in English). The wiki's agent does not make cards of them
(their section is not in WIKI_AGENT_SECTIONS): they answer "what was on the exam", not "what are the rules".
"""

import hashlib
import json
import re
import subprocess
import sys
import time
from collections import defaultdict
from urllib.parse import quote

import httpx

from catix.wiki.compile import BUNDLE, PRODUCER, yaml_value
from catix.wiki.paths import RAW
from catix.wiki.sources import regulations
from catix.wiki.sources.rpd import latin

SITE = "https://glebpopov.notion.site"
PAGE = "4ef3de0c-7e68-495b-89ef-086301361603"  # the database's own page
TITLE = "IU B23 Academic Materials: Past Papers [EN programs]"
ROOT = RAW / "past-papers"
INDEX = ROOT / "index.json"  # row id -> the row and its files (in git; the downloads are not)
FOLDER = "past-papers"
PAUSE = 2
MAX_CHARS = 8000  # of one paper on the page: the start says what was asked, a long one is in its file
OCR_PAGES = 120  # per run: scans left over are read by the next run


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
        files = [(part[0], part[1][0][1]) for part in props.get("File", []) if len(part) > 1 and part[1] and part[1][0][0] == "a"]
        out.append({"id": block["id"], "space": space, "subject": text("Subject"), "year": text("Year"), "exam": text("Exam") or text("title"), "files": files})
    return out


def load() -> dict:
    return json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {}


def save(index: dict) -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def file_key(url: str) -> str:
    return hashlib.sha1(url.split("?")[0].encode()).hexdigest()[:12]


def read_pdf(path) -> tuple[str | None, str]:
    """The text of a paper: its text layer, else OCR (English) of its pages. (None, why) when there is nothing to read."""
    pages = regulations.pages_of(path)
    text = subprocess.run(["pdftotext", str(path), "-"], capture_output=True, text=True).stdout
    if len(re.findall(r"[^\W\d_]{3,}", text)) >= 15 * max(1, pages) or len(text.strip()) > 300 * pages:
        return text, "text layer"
    if pages > 20:
        return None, "a scan too long for OCR"
    work = path.with_suffix(".ocr")
    work.mkdir(exist_ok=True)
    subprocess.run(["pdftoppm", "-r", "200", "-png", str(path), str(work / "p")], check=True)
    text = "\f".join(subprocess.run(["tesseract", str(png), "-", "-l", "eng"], capture_output=True, text=True).stdout for png in sorted(work.glob("p-*.png")))
    for png in work.glob("*.png"):
        png.unlink()
    work.rmdir()
    return (text, "ocr (tesseract eng)") if text.strip() else (None, "nothing readable")


def fetch() -> int:
    """New rows and the files not read yet; a row gone from the database leaves the index. The number of rows added,
    changed or removed."""
    index, changed, ocr_left = load(), 0, OCR_PAGES
    files = ROOT / "files"
    files.mkdir(parents=True, exist_ok=True)
    with httpx.Client(headers=regulations.HEADERS, timeout=120, follow_redirects=True) as client:
        found = rows(client)
        for row in found:
            old = index.get(row["id"], {})
            entry = {**{k: row[k] for k in ("subject", "year", "exam")}, "files": dict(old.get("files", {}))}  # (a copy: else the old entry changes too and nothing looks changed)
            for name, url in row["files"]:
                key = file_key(url)
                if key in entry["files"] and ("sha256" in entry["files"][key] or "skipped" in entry["files"][key]):
                    continue
                if not name.lower().endswith(".pdf"):
                    entry["files"][key] = {"name": name, "skipped": "not a PDF"}
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
                path = files / f"{key}.pdf"
                path.write_bytes(resp.content)
                if ocr_left <= 0 and len(subprocess.run(["pdftotext", str(path), "-"], capture_output=True, text=True).stdout.strip()) < 100:
                    continue  # a scan: the next run reads it
                text, method = read_pdf(path)
                if method.startswith("ocr"):
                    ocr_left -= regulations.pages_of(path)
                if text is None:
                    entry["files"][key] = {"name": name, "skipped": method}
                else:
                    (ROOT / f"{key}.txt").write_text(text, encoding="utf-8")
                    entry["files"][key] = {"name": name, "sha256": hashlib.sha256(resp.content).hexdigest(), "method": method, "chars": len(text)}
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


def compile_all() -> None:
    """One page per subject: its papers, newest first, each with its link and the start of its text."""
    out = BUNDLE / FOLDER
    out.mkdir(parents=True, exist_ok=True)
    by_subject: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for row_id, entry in load().items():
        if entry["subject"]:
            by_subject[entry["subject"]].append((row_id, entry))
    keep, written = set(), 0
    for subject, papers in sorted(by_subject.items()):
        key = latin(subject) or "subject"
        keep.add(key)
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
                if "sha256" not in f or not (ROOT / f"{fkey}.txt").exists():
                    continue
                text = re.sub(r"\n{3,}", "\n\n", (ROOT / f"{fkey}.txt").read_text(encoding="utf-8").replace("\f", "\n")).strip()
                text = re.sub(r"(?m)^(#+)", r"\\\1", text)  # (a line of the paper that starts with '#' is not a heading of the page)
                cut = text[:MAX_CHARS] + ("\n\n(the rest is in the file)" if len(text) > MAX_CHARS else "")
                body += [f"### {f['name']}" if len(entry["files"]) > 1 else "", cut, ""]
        front = ["---", "type: page", f"title: {yaml_value(title)}", f"description: {yaml_value(desc)}", f"resource: {yaml_value(resource)}",
                 f"tags: {yaml_value(['past-papers', 'exams', 'bachelor', latin(subject)])}", 'audience: ["student"]', "source_kind: community",
                 "language: en", 'section: "notion/past-papers"', f"subject: {yaml_value(subject)}",
                 "sources:", f"  - resource: {yaml_value(resource)}", f"    title: {yaml_value(TITLE)}",
                 "generated:", f"  by: {yaml_value(f'{PRODUCER} past-papers (code only, no model)')}", "status: draft", "---"]
        page = "\n".join(front) + f"\n\n# {title}\n\n" + "\n".join(line for line in body).strip() + f"\n\n# Citations\n\n1. [{TITLE}]({resource})\n"
        target = out / f"{key}.md"
        if not target.exists() or target.read_text(encoding="utf-8") != page:
            target.write_text(page, encoding="utf-8")
            written += 1
    for page in out.glob("*.md"):
        if page.stem not in keep and page.name != "index.md":
            page.unlink()
            print(f"{page.stem}: no papers left, page removed")
    print(f"{written} pages written, {len(keep)} subjects")


def status() -> None:
    index = load()
    files = [f for e in index.values() for f in e["files"].values()]
    print(f"{len(index)} rows, {len(files)} files: {sum('sha256' in f for f in files)} read, {sum('skipped' in f for f in files)} skipped")


def main() -> None:
    cmd, *_ = sys.argv[2:] or ["status"]
    if cmd == "fetch":
        fetch()
    elif cmd == "compile":
        compile_all()
    elif cmd == "status":
        status()
    else:
        sys.exit(__doc__)
