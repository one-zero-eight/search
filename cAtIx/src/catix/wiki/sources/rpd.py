"""Course programmes (РПД, рабочие программы дисциплин) from the archives of innopolis.university/sveden/education.

    catix-wiki rpd fetch [--all-years] [--limit N]   # the archives of every cohort (or the latest, see below) -> raw/rpd/ (text and meta of every PDF)
    catix-wiki rpd compile [--all-years] # raw/rpd -> wiki/course-programmes/<key>.md
    catix-wiki rpd refresh               # ask the site (HEAD) whether an archive read before changed; fetch reads a changed one again
    catix-wiki rpd status                # archives found and taken, programmes read

The site keeps one 7z archive per programme, cohort and semester (sveden.py lists them; the cell of the table says which).
Every PDF inside is one course: its text is kept as it is (as for the regulations, the program only turns the layout into
markdown), no model is asked, the title and the description are made by code from the header of the programme and the
place of the archive. Section 6 (the classrooms and equipment of the university) is the same in every programme and is left out.
Every cohort is taken (WIKI_RPD_ALL_YEARS, on by default): a student studies by the programme of their own cohort. With it off
only the latest cohort of a programme is taken (the applicants ask about it), and --all-years takes every one for one run.
"""

import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import httpx

from catix.settings import settings
from catix.wiki.sources import regulations, sveden
from catix.wiki.compile import BUNDLE, PRODUCER, yaml_value
from catix.wiki.paths import RAW

ROOT = RAW / "rpd"
INDEX = ROOT / "index.json"  # course key -> where it comes from and how it was read (in git; the files are not)
REMOTE = ROOT / "archives.json"  # archive URL -> what the site said about the file when it was read (regulations.signature)
FOLDER = "course-programmes"
CELL = re.compile(r"(?P<programme>.*?) — (?P<year>\d{4}) — (?P<kind>Рабочие программы дисциплин.*)$")
HEADING = re.compile(r"^(?:(?:РАБОЧАЯ\s+)?ПРОГРАММА|ФОНД ОЦЕНОЧНЫХ СРЕДСТВ)\b.*$", re.M)
CODE = re.compile(r"^([А-ЯA-Z]{1,4}\d?(?:\.[А-ЯA-Zа-я\d]+)+)[\s_]+(.*)$")
KINDS = {"ФОНД": "Фонд оценочных средств", "ФОС": "Фонд оценочных средств"}  # what else than a programme an archive of the column holds
SECTION = re.compile(r"^\s*(\d{1,2})\.\s*([А-ЯЁ][А-ЯЁ ,()«»-]{7,})\s*$", re.M)  # '2. ПЕРЕЧЕНЬ ПЛАНИРУЕМЫХ РЕЗУЛЬТАТОВ ОБУЧЕНИЯ'
FACILITIES = re.compile(r"^\s*6\.\s*МАТЕРИАЛЬНО-ТЕХНИЧЕСКОЕ ОБЕСПЕЧЕНИЕ.*?(?=^\s*7\.\s*[А-ЯЁ]{4})", re.M | re.S)
LEVELS = {"бакалавриата": "бакалавриат", "магистратуры": "магистратура", "подготовки кадров высшей квалификации": "аспирантура",
          "подготовки специалистов среднего звена": "СПО"}
AUDIENCE = {"аспирантура": ["postgraduate", "teacher"], "СПО": ["student", "teacher", "applicant"]}
TRANSLIT = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя", "a b v g d e e zh z i y k l m n o p r s t u f kh ts ch sh shch - y - e yu ya".split()))


def latin(text: str) -> str:
    out = "".join(TRANSLIT.get(c, c) for c in text.lower()).replace("-", "")
    return re.sub(r"[^a-z0-9]+", "-", out).strip("-")


def archives(all_years: bool | None = None, dead: set[str] = frozenset()) -> list[dict]:
    """The РПД archives that sveden.py found, with the programme and the cohort of their cell; only the latest cohort of each
    programme unless `all_years` (default: WIKI_RPD_ALL_YEARS). A cohort most of whose links are `dead` (404 on the site: every master's programme of 2026
    once) does not count: the one before it is taken."""
    found = []
    for d in sveden.load(sveden.INDEX):
        if d["ext"] in ("7z", "zip") and (m := CELL.match(d.get("context", ""))):
            found.append({"url": d["url"], "title": d["title"], "programme": m["programme"], "year": int(m["year"]), "ext": d["ext"]})
    if settings.wiki_rpd_all_years if all_years is None else all_years:
        return found
    alive, total, latest = Counter(), Counter(), Counter()
    for a in found:
        total[a["programme"], a["year"]] += 1
        alive[a["programme"], a["year"]] += a["url"] not in dead
    for (programme, year), n in total.items():
        if 2 * alive[programme, year] >= n:
            latest[programme] = max(latest[programme], year)
    return [a for a in found if a["year"] == latest[a["programme"]]]


def programme_label(cell: str) -> tuple[str, str]:
    """(level, a short label of the programme) from the cell's caption: 'бакалавриата: 09.03.01 Информатика...; Направленность
    программы (профиль) – Анализ данных*' -> ('бакалавриат', '09.03.01 Информатика..., профиль «Анализ данных»')."""
    school = "ПИШ, " if cell.startswith("Передовая инженерная школа") else ""
    cell = re.sub(r"^Передовая инженерная школа:\s*", "", cell)
    cell = re.sub(r"^Образовательная программа (?:среднего профессионального|высшего) образования\s*[-–]\s*программа\s*", "", cell)
    level = next((v for k, v in LEVELS.items() if cell.startswith(k)), "")
    rest = cell.split(":", 1)[1].strip() if ":" in cell else cell
    rest = re.sub(r";\s*\S{1,3}$", "", rest)  # the caption is cut at 170 characters: '…; К' was 'Квалификация'
    rest = re.sub(r";?\s*Направленность программы \(профиль\)\s*[-–]\s*(.+?)\*?$", r", профиль «\1»", rest).replace("*", "")
    return level, f"{school}{level} {rest}".strip()


def semester_of(archive_title: str, file_name: str) -> int | None:
    m = re.search(r"(\d{1,2})\s*семестр", archive_title) or re.search(r"\((\d{1,2})\s*с\.?\)", file_name)
    return int(m.group(1)) if m else None


def name_of(text: str, file_name: str) -> tuple[str, str, str]:
    """(kind, code, name) of the course from the header of its programme: 'Б1.О.15 Вычислительная математика' after 'РАБОЧАЯ
    ПРОГРАММА ДИСЦИПЛИНЫ (МОДУЛЯ)' or 'ФОНД ОЦЕНОЧНЫХ СРЕДСТВ ПО ДИСЦИПЛИНЕ' (the assessment materials, which some programmes
    publish in the same column), up to the line of the field of study or the first section. The file name cuts long names
    and joins words with '_', so it is the fallback."""
    stem = re.sub(r"^Визуализация_", "", Path(file_name).stem)
    kind = next((v for k, v in KINDS.items() if stem.upper().startswith(k + "_")), "Рабочая программа")
    if heading := HEADING.search(text[:6000]):
        kind = KINDS.get(heading.group(0).split()[0], "Рабочая программа")
        lines = []
        for line in text[heading.end():heading.end() + 600].strip().splitlines():
            # (the cycle of a СПО course and its programme follow the name: 'социально-гуманитарного цикла', 'Программа подготовки…')
            if re.match(r"\s*(\d\d\.\d\d\.\d\d|\d\.\d\.\d|\d\.\s|Направление|Специальность|Научная|Квалификация|Программа подготовки|Подготовка специалистов|Среднее общее)", line) \
                    or re.search(r"\bцикла\b", line) or not line.strip():
                break
            lines.append(line.strip())
        if (m := CODE.match(" ".join(lines))) and m.group(2):
            return kind, m.group(1), m.group(2)[:200]
    stem = re.sub(r"^ФОС_", "", stem)
    code, rest = (m.group(1), m.group(2)) if (m := CODE.match(stem)) else ("", stem)
    # The short name of the programme, the cohort and the date between the parts ('МОИИ_2025_…_25.12.2025') are not the name.
    words = [w for w in rest.split("_") if w and not re.fullmatch(r"[\d.]+|[А-ЯA-Z]{2,6}", w)]
    name = re.sub(r"\s*\(\d+\s*с\.?\)\s*$|\b\d\d\.\d\d\.\d{4}\b|^\d\d\s+|\s+Программист$", "", " ".join(words))
    name = re.sub(r"\s+", " ", name).strip()
    return kind, code, name or stem


def to_markdown(text: str) -> str:
    """The text as markdown, every section of the programme a heading. A programme numbers its sections 1-8 and has no
    clauses '2.1', so regulations.to_markdown would read the sections as clauses of a flat list."""
    text = text.replace("\f", "\n")  # a new page often starts with a heading: 'д.ф.-м.н.\f1. КРАТКАЯ ХАРАКТЕРИСТИКА…'
    parts = SECTION.split(text)
    out = [regulations.to_markdown(parts[0])]
    for number, heading, body in zip(parts[1::3], parts[2::3], parts[3::3]):
        out.append(f"## {number}. {heading.strip().capitalize()}\n\n{regulations.to_markdown(body)}")
    return "\n\n".join(p for p in out if p.strip())


def key_of(archive_url: str, member: str, code: str, name: str) -> str:
    return "rpd-" + hashlib.sha1(f"{archive_url}/{member}".encode()).hexdigest()[:8] + "-" + (latin(f"{code} {name}")[:40].strip("-") or "course")


def dead_links(index: dict) -> set[str]:
    return {c["archive"] for c in index.values() if c.get("skipped") == "404 on the site"}


def load() -> dict:
    return json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {}


def save(index: dict) -> None:
    INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def fetch(all_years: bool | None = None, limit: int | None = None) -> int:
    """Download the archives not read yet, unpack them and keep the text of every programme inside. Polite: one archive every
    `regulations.PAUSE` seconds, stop after `regulations.MAX_FAILURES` network errors in a row."""
    work = ROOT / "archives"
    work.mkdir(parents=True, exist_ok=True)
    index = load()
    remote = json.loads(REMOTE.read_text(encoding="utf-8")) if REMOTE.exists() else {}
    read = {c["archive"] for c in index.values()}
    todo = [a for a in archives(all_years, dead_links(index)) if a["url"] not in read][:limit]
    print(f"{len(todo)} archives to read")
    failures, total = 0, 0
    for n, a in enumerate(todo, 1):
        akey = hashlib.sha1(a["url"].encode()).hexdigest()[:10]
        path = work / f"{akey}.{a['ext']}"
        if not path.exists():
            try:
                resp = httpx.get(a["url"], timeout=300, follow_redirects=True, headers=regulations.HEADERS)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                print(f"  FAILED {a['url']}: {e}")
                if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 404:  # a dead link on the site itself: not asked again
                    index[f"archive-{akey}"] = {"archive": a["url"], "archive_title": a["title"], "skipped": "404 on the site"}
                    save(index)
                    time.sleep(regulations.PAUSE)
                    continue
                failures += 1
                if failures >= regulations.MAX_FAILURES:
                    print(f"{failures} failures in a row: the site is not answering, stopped (the rest is read by the next run)")
                    break
                time.sleep(regulations.PAUSE + 5 * failures)
                continue
            failures = 0
            path.write_bytes(resp.content)
            remote[a["url"]] = regulations.signature(resp.headers)
            REMOTE.write_text(json.dumps(remote, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
            time.sleep(regulations.PAUSE)
        unpacked = work / akey
        shutil.rmtree(unpacked, ignore_errors=True)
        unpacked.mkdir()
        # bsdtar reads 7z and zip; it refuses absolute paths and '..' in the archive by default.
        if subprocess.run(["bsdtar", "-xf", str(path), "-C", str(unpacked)], capture_output=True).returncode != 0:
            print(f"  cannot unpack {a['url']}")
            continue
        level, label = programme_label(a["programme"])
        found = 0
        for member in sorted(p for p in unpacked.rglob("*") if p.is_file() and not p.is_symlink() and p.suffix.lower() in {".pdf", ".docx", ".doc"}):
            rel = member.relative_to(unpacked).as_posix()
            try:
                text, method, _ = regulations.extract(regulations.to_pdf(member), 0)  # no OCR: the programmes have a text layer
            except (ValueError, subprocess.SubprocessError, AttributeError) as e:
                text, method = None, f"cannot read: {e}"
            kind, code, name = name_of(text or "", member.name)
            key = key_of(a["url"], rel, code, name)
            entry = {"archive": a["url"], "archive_title": a["title"], "member": rel, "programme": label, "level": level, "year": a["year"],
                     "semester": semester_of(a["title"], member.name), "kind": kind, "code": code, "name": name,
                     "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            if text is None or not regulations.readable(text):
                index[key] = {**entry, "skipped": method if text is None else "no readable text"}
                continue
            (ROOT / f"{key}.txt").write_text(text, encoding="utf-8")
            index[key] = {**entry, "sha256": hashlib.sha256(member.read_bytes()).hexdigest(), "method": method, "chars": len(text)}
            found += 1
        shutil.rmtree(unpacked, ignore_errors=True)  # the archive stays; its texts are in raw/rpd
        save(index)
        total += found
        print(f"{n}/{len(todo)} {label[:70]}, {a['year']}, {a['title'][:30]}: {found} programmes", flush=True)
    return total


def refresh() -> int:
    """HEAD every archive read before (one request every PAUSE seconds); a changed one loses its programmes from the index and its
    file, so that the next `fetch` reads it again (the pages stay until compile). The number of changed archives."""
    index = load()
    remote = json.loads(REMOTE.read_text(encoding="utf-8")) if REMOTE.exists() else {}
    urls = sorted({c["archive"] for c in index.values() if "sha256" in c})
    found, failures = 0, 0
    with httpx.Client(headers=regulations.HEADERS, timeout=60, follow_redirects=True) as client:
        for url in urls:
            try:
                resp = client.head(url)
            except httpx.HTTPError as e:
                failures += 1
                print(f"{url}: {e}")
                if failures >= regulations.MAX_FAILURES:
                    print(f"{failures} failures in a row: the site is not answering, stopped")
                    break
                time.sleep(regulations.PAUSE + 5 * failures)
                continue
            failures = 0
            time.sleep(regulations.PAUSE)
            if resp.status_code != 200:
                continue
            now = regulations.signature(resp.headers)
            if regulations.changed(remote.get(url), now):
                index = {k: c for k, c in index.items() if c["archive"] != url}
                akey = hashlib.sha1(url.encode()).hexdigest()[:10]
                for f in (ROOT / "archives").glob(f"{akey}.*"):
                    f.unlink()
                found += 1
                print(f"changed on the site: {url}")
            remote[url] = remote.get(url) or now  # (a changed one gets its new signature when fetch downloads it)
    save(index)
    REMOTE.write_text(json.dumps(remote, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(f"{found} archives changed on the site")
    return found


def compile_all(all_years: bool | None = None) -> None:
    """Every read programme of the archives taken now -> wiki/course-programmes/<key>.md, by code only (no model). A cohort
    that is no longer taken (a newer one came, or the one before replaced dead links) loses its pages."""
    out = BUNDLE / FOLDER
    out.mkdir(parents=True, exist_ok=True)
    index, written, keep = load(), 0, set()
    taken = {a["url"] for a in archives(all_years, dead_links(index))}
    for key, c in sorted(index.items()):
        if "sha256" not in c or c["archive"] not in taken:
            continue
        keep.add(key)
        if not (ROOT / f"{key}.txt").exists():  # (a fresh checkout of `wiki` has the pages but not the downloads: the page stays)
            continue
        text = (ROOT / f"{key}.txt").read_text(encoding="utf-8").replace("\f", "\n")  # (a section often opens a page)
        kind, code, name = name_of(text, Path(c["member"]).name)  # by code on every run: a better reading reaches the pages
        c = {**c, "kind": kind, "code": code, "name": name}
        body = to_markdown(FACILITIES.sub("6. МАТЕРИАЛЬНО-ТЕХНИЧЕСКОЕ ОБЕСПЕЧЕНИЕ\n\nТиповой раздел (аудитории, оборудование, программное обеспечение университета), одинаковый во всех рабочих программах: см. PDF.\n\n", text, count=1))
        semester = f", {c['semester']} семестр" if c.get("semester") else ""
        title = f"{c.get('kind', 'Рабочая программа')} «{c['name']}»" + (f" ({c['code']})" if c["code"] else "") + f" — {c['programme']}, набор {c['year']}{semester}"
        what = "Assessment materials (ФОС)" if c.get("kind", "").startswith("Фонд") else "Course programme (РПД)"
        desc = (f"{what} of «{c['name']}», {c['level'] or 'programme'} cohort {c['year']}{', semester ' + str(c['semester']) if c.get('semester') else ''}: "
                "learning outcomes, hours and topics, reading list, assessment and grading.")
        issued = regulations.issued_of(text, c["fetched_at"])
        resource = c["archive"]
        front = ["---", "type: course-programme", f"title: {yaml_value(title[:300])}", f"description: {yaml_value(desc[:300])}", f"resource: {yaml_value(resource)}",
                 f"tags: {yaml_value(['course-programme', 'rpd', *([latin(c['level'])] if c['level'] else [])])}",
                 f"audience: {yaml_value(AUDIENCE.get(c['level'], ['student', 'teacher', 'applicant']))}",
                 "source_kind: official-document", "language: ru", 'section: "sveden/education"',
                 f"course_code: {yaml_value(c['code'])}", f"programme: {yaml_value(c['programme'])}", f"cohort: {c['year']}",
                 *([f"semester: {c['semester']}"] if c.get("semester") else []),
                 "sources:", f"  - resource: {yaml_value(resource)}", f"    id: {yaml_value(c['sha256'][:12])}", f"    title: {yaml_value(title[:300])}",
                 f"    last_modified: {yaml_value(issued)}",
                 "generated:", f"  by: {yaml_value(f'{PRODUCER} rpd (code only, no model)')}", f"  at: {yaml_value(c['fetched_at'])}",
                 f"extraction: {yaml_value(c['method'])}", "status: draft", "---"]
        page = "\n".join(front) + f"\n\n# {title}\n\n{body}\n\n# Citations\n\n1. [{title}]({resource}), file «{c['member']}» in the archive, {c['sha256'][:12]}\n"
        target = out / f"{key}.md"
        if not target.exists() or target.read_text(encoding="utf-8") != page:
            target.write_text(page, encoding="utf-8")
            written += 1
    for page in out.glob("*.md"):
        if page.stem not in keep:
            page.unlink()
            print(f"{page.stem}: no longer read, page removed")
    print(f"{written} pages written, {len(keep)} programmes in the bundle")


def status() -> None:
    index = load()
    taken = archives(dead=dead_links(index))
    print(f"{len(archives(all_years=True))} archives of course programmes on the site, {len(taken)} taken "
          f"({'every cohort' if settings.wiki_rpd_all_years else 'the latest cohorts'})")
    print(f"{len({c['archive'] for c in index.values()})} archives read: {sum('sha256' in c for c in index.values())} programmes, "
          f"{sum('skipped' in c for c in index.values())} files skipped")
    for programme, n in Counter(c["programme"] for c in index.values() if "sha256" in c).most_common():
        print(f"  {n:>4}  {programme[:110]}")


def main() -> None:
    cmd, *args = sys.argv[2:] or ["status"]
    if cmd == "fetch":
        fetch(all_years=True if "--all-years" in args else None, limit=int(args[args.index("--limit") + 1]) if "--limit" in args else None)
    elif cmd == "compile":
        compile_all(all_years=True if "--all-years" in args else None)
    elif cmd == "refresh":
        refresh()
    elif cmd == "status":
        status()
    else:
        sys.exit(__doc__)
