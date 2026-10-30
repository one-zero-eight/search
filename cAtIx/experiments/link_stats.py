"""Statistics of the links in the pages of the bundle: how many go to other pages of the wiki, how many leave it, where to.

    python experiments/link_stats.py                     # wiki/raw/sites of the bundle that settings.wiki_root (or this checkout) holds
    python experiments/link_stats.py --root /path/to/data --folder raw/sites --top 20
    python experiments/link_stats.py --json > stats.json

A page is a markdown file under <root>/wiki/<folder>/. Its front matter and its `# Citations` section are not read (the citation is
the page's own address). In the text: `[text](/raw/..)` is a link inside the wiki, `[text](https://..)` leaves it, `![alt](url)` is a
picture, `[▶ video](url)` a video (a link whose text starts with ▶).
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urlsplit

IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)\)")
LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")
DOCUMENT = re.compile(r"\.(pdf|docx?|xlsx?|pptx?|rtf|zip|rar|7z|csv|txt)$", re.I)
MEDIA_FILE = re.compile(r"\.(jpe?g|png|gif|webp|svg|mp4|webm|mov)$", re.I)


def body_of(text: str) -> str:
    """The text of a page: without the front matter and without `# Citations`."""
    if text.startswith("---\n"):
        text = text.split("---\n", 2)[-1]
    return re.split(r"^# Citations\s*$", text, maxsplit=1, flags=re.M)[0]


def links_of(body: str) -> dict[str, list[tuple[str, str]]]:
    """kind -> [(url, text)]: internal, external, image, video, other (mailto:, tel:, #anchors)."""
    found: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for m in IMAGE.finditer(body):
        found["image"].append((m.group(1), ""))
    rest = IMAGE.sub("", body)  # (a picture inside a link leaves the link with the empty text: `[](url)`)
    for text, url in LINK.findall(rest):
        if text.startswith("▶"):
            found["video"].append((url, text))
        elif url.startswith("/"):
            found["internal"].append((url, text))
        elif url.startswith(("http://", "https://")):
            found["external"].append((url, text))
        else:
            found["other"].append((url, text))
    return found


def host_of(url: str) -> str:
    return urlsplit(url).netloc.lower().removeprefix("www.")


def own(host: str) -> bool:
    """A host of the university itself (its subdomains are other sites, which the wiki may not read)."""
    return host.endswith(("innopolis.university", "innopolis.ru", "innopolis.edu.ru"))


def collect(bundle: Path, folder: Path) -> list[dict]:
    pages = []
    for path in sorted(folder.rglob("*.md")):
        if path.name == "index.md":
            continue
        found = links_of(body_of(path.read_text(encoding="utf-8")))
        rel = path.relative_to(folder).parts
        pages.append({"path": "/" + path.relative_to(bundle).as_posix(), "site": rel[0] if len(rel) > 1 else "",
                      "shared": path.name.startswith("_shared"), "found": found})
    return pages


def summarize(pages: list[dict], top: int) -> dict:
    total = Counter()
    per_site: dict[str, Counter] = defaultdict(Counter)
    hosts, hosts_urls, hosts_pages = Counter(), defaultdict(set), defaultdict(set)
    extensions, anchors = Counter(), Counter()
    external_by_page = []
    for p in pages:
        for kind, items in p["found"].items():
            total[kind] += len(items)
            per_site[p["site"]][kind] += len(items)
        for url, text in p["found"].get("external", []):
            host = host_of(url)
            hosts[host] += 1
            hosts_urls[host].add(url)
            hosts_pages[host].add(p["path"])
            if m := DOCUMENT.search(unquote(urlsplit(url).path)):
                extensions[m.group(1).lower()] += 1
            if text:
                anchors[text.strip().lower()[:40]] += 1
        external_by_page.append((len(p["found"].get("external", [])), p["path"]))
    all_urls = {u for urls in hosts_urls.values() for u in urls}
    outside = sum(n for h, n in hosts.items() if not own(h))
    return {
        "pages": len(pages), "shared_pages": sum(p["shared"] for p in pages),
        "pages_without_external": sum(1 for n, _ in external_by_page if n == 0),
        "links": dict(total), "unique_external": len(all_urls),
        "external_to_university_hosts": sum(hosts.values()) - outside, "external_outside": outside,
        "per_site": {s: dict(c) for s, c in sorted(per_site.items())},
        "top_hosts": [{"host": h, "links": n, "unique": len(hosts_urls[h]), "pages": len(hosts_pages[h]), "university": own(h)}
                      for h, n in hosts.most_common(top)],
        "documents_by_extension": dict(extensions.most_common()),
        "top_link_texts": anchors.most_common(top),
        "pages_with_most_external": [{"page": path, "external": n} for n, path in sorted(external_by_page, reverse=True)[:top]],
    }


def show(s: dict) -> None:
    links = s["links"]
    print(f"pages: {s['pages']} ({s['shared_pages']} of shared blocks), without a link out: {s['pages_without_external']}")
    print(f"links: {links.get('internal', 0)} inside the wiki, {links.get('external', 0)} out of it "
          f"({s['unique_external']} different addresses), {links.get('image', 0)} pictures, {links.get('video', 0)} videos, "
          f"{links.get('other', 0)} others (mail, phone, anchors)")
    print(f"out of the wiki: {s['external_to_university_hosts']} to the university's own hosts (pages the wiki may not read yet), "
          f"{s['external_outside']} to other sites")
    print("\nper site:")
    for site, c in s["per_site"].items():
        print(f"  {site or '(root)':<12} internal {c.get('internal', 0):>5}  external {c.get('external', 0):>5}  pictures {c.get('image', 0):>5}  videos {c.get('video', 0):>3}")
    print("\nhosts the pages link to:")
    for h in s["top_hosts"]:
        print(f"  {h['links']:>5} links  {h['unique']:>4} addresses  {h['pages']:>4} pages  {h['host']}{'  (the university)' if h['university'] else ''}")
    if s["documents_by_extension"]:
        print("\nlinks to files: " + ", ".join(f"{e} {n}" for e, n in s["documents_by_extension"].items()))
    print("\nmost common link texts:")
    for text, n in s["top_link_texts"]:
        print(f"  {n:>5}  {text}")
    print("\npages with most links out:")
    for p in s["pages_with_most_external"]:
        print(f"  {p['external']:>5}  {p['page']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, help="the data root (holds wiki/); default: settings.wiki_root or this checkout")
    ap.add_argument("--folder", default="raw/sites", help="folder of the bundle to read, below wiki/")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.root:
        bundle = args.root / "wiki"
    else:
        from catix.wiki.paths import BUNDLE
        bundle = BUNDLE
    folder = bundle / args.folder
    if not folder.is_dir():
        sys.exit(f"no such folder: {folder}")
    stats = summarize(collect(bundle, folder), args.top)
    print(json.dumps(stats, ensure_ascii=False, indent=1)) if args.json else show(stats)


if __name__ == "__main__":
    main()
