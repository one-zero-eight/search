"""The sites of the university's services as a source of the bundle: campuslife.innopolis.ru (student life: the handbook,
the FAQ, scholarships, clubs; English) and hotel.innopolis.university (the campus and its dormitories; Russian).

    catix-wiki sites fetch      # the pages of every site -> raw/sites/<site>/ (one request every PAUSE seconds); the number that changed
    catix-wiki sites compile    # raw/sites -> wiki/sites/<site>-<slug>.md
    catix-wiki sites status     # pages and documents found on every site

A page's text is kept as the site shows it: the program turns the markup into markdown and drops what every page of the
site repeats (menus, footers); the model writes only the description, once per version of the text. The documents a site
links (PDF, DOCX: the rules of the dormitories, their prices) go the way of the regulations (regulations.py, which asks
`docs()`): wiki/regulations/, quoted by clause, `source_kind: official-document`. The pages themselves are `website`.
Every run reads all pages again (a few dozen) and compares their text: these sites say nothing reliable about changes.
"""

import hashlib
import json
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import quote, unquote, urljoin, urlsplit

import httpx

from catix.wiki.compile import BUNDLE, PRODUCER, front_of, yaml_value
from catix.wiki.paths import RAW
from catix.wiki.sources import regulations
from catix.wiki.sources.rpd import latin

ROOT = RAW / "sites"
FOLDER = "sites"
PAUSE = 2  # seconds between requests
MAX_PAGES = 60  # per site: the crawl follows the links of the site, this stops a calendar or a catalogue from running away
DOC = re.compile(r"\.(pdf|docx?|rtf)$", re.I)


@dataclass(frozen=True)
class Site:
    base: str
    language: str
    about: str
    skip: str  # paths not taken: past events, old copies, forms, the other language
    sitemap: bool = True


SITES = {
    "campuslife": Site("https://campuslife.innopolis.ru/", "en", "student life at Innopolis University: handbook, FAQ, scholarships, clubs, services",
                       r"20\d\d|_old\b|^page\d+\.html$|^tilda/|talentshow|rockballqueen|battle_rage|covey_workshop|^ibc$"),
    "hotel": Site("https://hotel.innopolis.university/", "ru", "the campus of Innopolis University: dormitories, their rules, prices and documents",
                  r"^en(/|$)|zayavka|bitrix|upload/", sitemap=False),
}


def canonical(url: str) -> str:
    """One spelling of a link: the site writes the same file with spaces, Cyrillic or %-escapes."""
    parts = urlsplit(url)
    return f"https://{parts.netloc}{quote(unquote(parts.path), safe='/')}"


def slug_of(site: Site, url: str) -> str:
    path = unquote(urlsplit(url).path).strip("/")
    return re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-")[:60] or "home"


class _Markdown(HTMLParser):
    """HTML -> markdown lines: headings, paragraphs, list items, table rows; the links to files and to pages on the side."""

    HIDDEN = {"script", "style", "noscript", "svg", "form", "select", "button", "template", "iframe", "head"}
    BLOCK = {"p", "div", "section", "article", "br", "tr", "ul", "ol", "table", "blockquote", "dd", "dt"}

    def __init__(self, base: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base, self.lines, self.line, self.hidden = base, [], "", 0
        self.links: list[tuple[str, str]] = []  # (url, text)
        self.href: str | None = None
        self.anchor = ""
        self.title = ""
        self._in_title = False

    def _flush(self) -> None:
        text = re.sub(r"\s+", " ", self.line).strip()
        if text and text not in {"-", "|", "## ", "### "} and not re.fullmatch(r"(#+|-|\|)\s*", text):
            self.lines.append(text)
        self.line = ""

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "title":
            self._in_title = True
        if tag in self.HIDDEN:
            self.hidden += 1
            return
        if tag in self.BLOCK or re.fullmatch(r"h[1-6]|li|td|th", tag):
            if tag in {"td", "th"}:
                self.line += " | "
            else:
                self._flush()
        if re.fullmatch(r"h[1-3]", tag):
            self.line = "## "
        elif re.fullmatch(r"h[4-6]", tag):
            self.line = "### "
        elif tag == "li":
            self.line = "- "
        elif tag == "a":
            self.href, self.anchor = dict(attrs).get("href"), ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag in self.HIDDEN:
            self.hidden = max(0, self.hidden - 1)
            return
        if tag == "a" and self.href:
            self.links.append((urljoin(self.base, self.href.strip()), re.sub(r"\s+", " ", self.anchor).strip()))
            self.href = None
        if tag in self.BLOCK or re.fullmatch(r"h[1-6]|li", tag):
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self.hidden:
            return
        self.line += data
        if self.href is not None:
            self.anchor += data


def read(html: str, url: str) -> tuple[str, str, list[tuple[str, str]]]:
    """(title, markdown lines, links) of a page."""
    parser = _Markdown(url)
    parser.feed(html)
    parser.close()
    parser._flush()
    lines = []
    for line in parser.lines:
        if lines and re.fullmatch(r"\d{1,2}", lines[-1]):
            lines[-1] = f"**{lines[-1]}.** {line}"  # a numbered item whose number sits in a block of its own: 'item 2' can be quoted
            continue
        lines.append(line)
        for k in range(1, 9):  # Tilda repeats a block (of up to a few lines) for phones: the second copy goes
            if len(lines) >= 2 * k and lines[-k:] == lines[-2 * k:-k]:
                del lines[-k:]
                break
    title = re.sub(r"\s+", " ", parser.title).strip() or next((line.lstrip("# ") for line in lines if line.startswith("## ")), url)
    return title, "\n".join(lines), parser.links


def _taken(site: Site, url: str) -> bool:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or parts.netloc != urlsplit(site.base).netloc or DOC.search(parts.path):
        return False
    return not re.search(site.skip, unquote(parts.path).lstrip("/"), re.I)


def load(name: str) -> dict:
    path = ROOT / name / "index.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"pages": {}, "docs": {}}


def save(name: str, index: dict) -> None:
    (ROOT / name).mkdir(parents=True, exist_ok=True)
    (ROOT / name / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def fetch_site(name: str, site: Site, client: httpx.Client) -> int:
    """Read every page of a site (from its sitemap and the links of its pages); keep the text of the new and changed ones
    and the documents they link. The number of pages that are new, changed or gone."""
    index = load(name)
    todo: list[str] = [site.base]
    if site.sitemap:
        try:
            todo += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", client.get(urljoin(site.base, "sitemap.xml")).text)
        except httpx.HTTPError as e:
            print(f"  {name}: no sitemap ({e})")
        time.sleep(PAUSE)
    seen, read_ok, changed, docs = set(), 0, 0, {}
    while todo and len(seen) < MAX_PAGES:
        url = canonical(todo.pop(0))
        if url in seen or not _taken(site, url):
            continue
        seen.add(url)
        slug = slug_of(site, url)
        try:
            resp = client.get(url)
            time.sleep(PAUSE)
        except httpx.HTTPError as e:
            print(f"  FAILED {url}: {e}")
            continue
        old = index["pages"].get(slug, {})
        if resp.status_code == 404 or "text/html" not in resp.headers.get("content-type", ""):
            if old and not old.get("gone"):
                index["pages"][slug] = {**old, "gone": True}
                changed += 1
            continue
        if resp.status_code != 200:
            print(f"  {url}: {resp.status_code}")
            continue
        read_ok += 1
        title, text, links = read(resp.text, str(resp.url))
        for link, anchor in links:
            if DOC.search(urlsplit(link).path) and urlsplit(link).netloc == urlsplit(site.base).netloc:
                doc = canonical(link)
                docs[doc] = max(docs.get(doc, ""), anchor, key=len)  # the fullest of the link texts: 'Правила проживания', not 'Правила'
            elif _taken(site, link):
                todo.append(link)
        sha = hashlib.sha256(text.encode()).hexdigest()
        if old.get("sha256") == sha and not old.get("gone"):
            continue
        (ROOT / name).mkdir(parents=True, exist_ok=True)
        (ROOT / name / f"{slug}.md").write_text(text, encoding="utf-8")
        index["pages"][slug] = {"url": url, "title": title, "sha256": sha, "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                "last_modified": resp.headers.get("last-modified", "")}
        changed += 1
        print(f"  {slug}: {'changed' if old else 'new'}, {len(text)} chars")
    for slug, page in index["pages"].items():  # a page no link leads to any more has left the site
        if read_ok and page["url"] not in seen and not page.get("gone") and len(seen) < MAX_PAGES:  # (not when the site did not answer)
            index["pages"][slug] = {**page, "gone": True}
            changed += 1
    if read_ok:
        index["docs"] = docs
    save(name, index)
    return changed


def fetch() -> int:
    total = 0
    with httpx.Client(headers=regulations.HEADERS, timeout=60, follow_redirects=True) as client:
        for name, site in SITES.items():
            print(f"== {name}: {site.base}")
            total += fetch_site(name, site, client)
    return total


def docs() -> dict[str, dict]:
    """The documents the sites link, as regulations.all_docs wants them."""
    out = {}
    for name in SITES:
        for url, anchor in load(name)["docs"].items():
            file = unquote(url.rsplit("/", 1)[-1])
            stem = re.sub(r"[_]+", " ", file.rsplit(".", 1)[0]).strip()
            title = anchor if len(anchor) >= 12 and not re.fullmatch(r"(?i)(скачать|здесь|тут|download|here|подробнее|ссылк\w*)", anchor) else stem
            title = re.sub(r"\s+", " ", re.sub(r"\s*\(\d\)$", "", title)).strip()  # ('… 2025 год (2)': the second copy of a file)
            key = f"site-{name}-" + hashlib.sha1(url.encode()).hexdigest()[:8] + "-" + (latin(stem)[:40].strip("-") or "doc")
            out[key] = {"title": title, "url": url, "root": ROOT / name / "docs", "section": f"site/{name}", "ext": file.rsplit(".", 1)[-1].lower()}
    return out


def boilerplate(texts: list[str]) -> set[str]:
    """Lines that most pages of a site repeat: its menu, its footer, its contacts block."""
    if len(texts) < 3:
        return set()
    counts = Counter(line for text in texts for line in set(text.splitlines()))
    return {line for line, n in counts.items() if n >= max(3, 0.5 * len(texts))}


def compile_all() -> None:
    """Every page read -> wiki/sites/<site>-<slug>.md. The model writes only the description, tags and audience, once per
    version of the text; a page gone from its site loses its page."""
    out = BUNDLE / FOLDER
    out.mkdir(parents=True, exist_ok=True)
    keep, written = set(), 0
    for name, site in SITES.items():
        pages = {slug: p for slug, p in load(name)["pages"].items() if not p.get("gone") and (ROOT / name / f"{slug}.md").exists()}
        texts = {slug: (ROOT / name / f"{slug}.md").read_text(encoding="utf-8") for slug in pages}
        common = boilerplate(list(texts.values()))
        for slug, p in sorted(pages.items()):
            key = f"{name}-{slug}"
            lines = [line for line in texts[slug].splitlines() if line not in common]
            title = re.sub(r"\s*[|—–-]\s*(Campus Life|Кампус.*)$", "", p["title"]).strip() or p["title"]
            if lines and lines[0].lstrip("# ").lower() == title.lower():
                lines = lines[1:]  # (the page's own heading: the title says it)
            body = "\n\n".join(lines)
            if len(re.findall(r"[^\W\d_]{3,}", body)) < 30:
                continue  # a page of pictures and buttons
            keep.add(key)
            target = out / f"{key}.md"
            old = target.read_text(encoding="utf-8") if target.exists() else ""
            fm = front_of(old) if old else {}
            if f"id: {yaml_value(p['sha256'][:12])}" in old and fm.get("description") and fm.get("audience"):
                desc, tags, audience = str(fm["description"]), [str(t) for t in fm.get("tags") or []], [str(a) for a in fm["audience"]]
                by = (fm.get("generated") or {}).get("by")
            else:
                desc, tags, audience = regulations.describe(title, body, kind=f"page of the site {urlsplit(site.base).netloc} ({site.about})")
                by = f"{PRODUCER} sites ({regulations.model_name()}: description, tags and audience only)"
            front = ["---", "type: page", f"title: {yaml_value(title)}", f"description: {yaml_value(desc)}", f"resource: {yaml_value(p['url'])}",
                     f"tags: {yaml_value(tags)}", f"audience: {yaml_value(audience)}", "source_kind: website", f"language: {site.language}",
                     f"section: {yaml_value(f'site/{name}')}",
                     "sources:", f"  - resource: {yaml_value(p['url'])}", f"    id: {yaml_value(p['sha256'][:12])}", f"    title: {yaml_value(title)}",
                     f"    last_modified: {yaml_value(p['fetched_at'])}",
                     "generated:", f"  by: {yaml_value(by)}", f"  at: {yaml_value(p['fetched_at'])}", "status: draft", "---"]
            page = "\n".join(front) + f"\n\n# {title}\n\n{body}\n\n# Citations\n\n1. [{title}]({p['url']}), read {p['fetched_at'][:10]}\n"
            if page != old:
                target.write_text(page, encoding="utf-8")
                written += 1
    for page in out.glob("*.md"):
        if page.stem not in keep and page.name != "index.md":
            page.unlink()
            print(f"{page.stem}: no longer on its site, page removed")
    print(f"{written} pages written, {len(keep)} pages of the sites in the bundle")


def status() -> None:
    for name, site in SITES.items():
        index = load(name)
        pages = index["pages"].values()
        print(f"{name} ({site.base}): {sum(not p.get('gone') for p in pages)} pages, {sum(bool(p.get('gone')) for p in pages)} gone, "
              f"{len(index['docs'])} documents linked")


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
