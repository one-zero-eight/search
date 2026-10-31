"""Statistics of the links in the pages of the bundle: how many go to other pages of the wiki, how many leave it, where to.

    python experiments/link_stats.py                     # an overview of wiki/raw/sites of the bundle that settings.wiki_root (or this checkout) holds
    python experiments/link_stats.py --root /path/to/data --folder raw/sites --top 20
    python experiments/link_stats.py --group image       # one group, described as exactly as the pages allow
    python experiments/link_stats.py --group files --examples 20 --all     # ... with its examples, and every address with its count
    python experiments/link_stats.py --group internal --json > internal.json

A page is a markdown file under <root>/wiki/<folder>/. Its front matter and its `# Citations` section are not read (the citation is
the page's own address). In the text: `[text](/raw/..)` is a link inside the wiki, `[text](https://..)` leaves it, `![alt](url)` is a
picture, `[▶ video](url)` a video (a link whose text starts with ▶).

The groups of --group (each says in its report how a link comes to be in it):
    internal    links inside the wiki                 external   links out of it (not pictures, not videos)
    university  external, to the university's hosts   outside    external, to other sites
    files       external, to a file (pdf, docx, ...)  image      pictures
    video       videos                                other      mailto:, tel:, #anchors and the like
"""

import argparse
import json
import posixpath
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urlsplit

IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+)\)")
DOCUMENT = re.compile(r"\.(pdf|docx?|xlsx?|pptx?|rtf|zip|rar|7z|csv|txt)$", re.I)
MEDIA_FILE = re.compile(r"\.(jpe?g|png|gif|webp|svg|mp4|webm|mov)$", re.I)

GROUPS = {
    "internal": ("links inside the wiki", "a link [text](/path.md): its target begins with '/', a page of the bundle; a picture that is a link "
                 "([![alt](img)](/path.md)) counts here too, with the empty text"),
    "external": ("links out of the wiki", "a link [text](http(s)://...) that is not a video; a picture that is a link ([![alt](img)](https://...)) "
                 "counts here too, with the empty text"),
    "university": ("external links to the university's own hosts", "external links whose host ends with innopolis.university, innopolis.ru or innopolis.edu.ru "
                   "(its subdomains too: pages of the university that the wiki may not read)"),
    "outside": ("external links to other sites", "external links whose host is not the university's"),
    "files": ("external links to files", "external links whose path ends with pdf, doc(x), xls(x), ppt(x), rtf, zip, rar, 7z, csv or txt"),
    "image": ("pictures", "![alt](url): every picture, also one that is a link itself ([![alt](url)](target))"),
    "video": ("videos", "a link whose text begins with ▶: [▶ video](url)"),
    "other": ("other links", "a link whose target is neither '/...' nor 'http(s)://...': mailto:, tel:, #anchors, relative paths"),
}


def body_start_end(lines: list[str]) -> tuple[int, int]:
    """The first and the last line (0-based, end exclusive) of the text of a page: after the front matter, before `# Citations`."""
    start = 0
    if lines and lines[0] == "---":
        start = next((i for i in range(1, len(lines)) if lines[i] == "---"), -1) + 1
    end = next((i for i in range(start, len(lines)) if re.fullmatch(r"# Citations\s*", lines[i])), len(lines))
    return start, end


def occurrences(text: str) -> list[dict]:
    """Every picture, video and link in the text of a page, with the line of the file it stands on:
    {kind: internal|external|image|video|other, url, text, line, in_link: for a picture, the target of the link around it}."""
    lines = text.splitlines()
    start, end = body_start_end(lines)
    out = []
    for no in range(start, end):
        line = lines[no]
        for m in IMAGE.finditer(line):
            around = re.match(r"\]\(([^)\s]+)\)", line[m.end():]) if line[:m.start()].endswith("[") else None
            out.append({"kind": "image", "url": m.group(2), "text": m.group(1), "line": no + 1, "in_link": around.group(1) if around else ""})
        rest = IMAGE.sub("", line)  # (a picture inside a link leaves the link with the empty text: `[](url)`)
        for label, url in LINK.findall(rest):
            kind = "video" if label.startswith("▶") else "internal" if url.startswith("/") else "external" if url.startswith(("http://", "https://")) else "other"
            out.append({"kind": kind, "url": url, "text": label, "line": no + 1, "in_link": ""})
    return out


def links_of(body: str) -> dict[str, list[tuple[str, str]]]:
    """kind -> [(url, text)]: internal, external, image, video, other (mailto:, tel:, #anchors)."""
    found: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for o in occurrences(body):
        found[o["kind"]].append((o["url"], o["text"] if o["kind"] != "image" else ""))
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
        # (the page text is scanned as a whole file, so that the lines are the lines of the file; front matter and citations are skipped inside)
        occ = occurrences(path.read_text(encoding="utf-8"))
        found: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for o in occ:
            found[o["kind"]].append((o["url"], o["text"] if o["kind"] != "image" else ""))
        rel = path.relative_to(folder).parts
        pages.append({"path": "/" + path.relative_to(bundle).as_posix(), "site": rel[0] if len(rel) > 1 else "",
                      "shared": path.name.startswith("_shared"), "found": found, "occ": occ})
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


# ---- one group, exactly ----

def in_group(group: str, o: dict) -> bool:
    if group in {"internal", "image", "video", "other"}:
        return o["kind"] == group
    if o["kind"] != "external":
        return False
    if group == "external":
        return True
    if group == "university":
        return own(host_of(o["url"]))
    if group == "outside":
        return not own(host_of(o["url"]))
    return bool(DOCUMENT.search(unquote(urlsplit(o["url"]).path)))  # files


def platform_of(url: str) -> str:
    host = host_of(url)
    if host.endswith(("youtube.com", "youtu.be", "youtube-nocookie.com")):
        return "youtube"
    for name in ("rutube.ru", "vk.com", "vimeo.com"):
        if host == name:
            return name.split(".")[0]
    return "file" if re.search(r"\.(mp4|webm|mov|m4v|ogv)$", urlsplit(url).path, re.I) else host or "(no host)"


def spread(values: list[int]) -> dict:
    """min / median / mean / max of a list of counts."""
    if not values:
        return {"min": 0, "median": 0, "mean": 0, "max": 0}
    return {"min": min(values), "median": statistics.median(values), "mean": round(statistics.mean(values), 2), "max": max(values)}


def group_report(pages: list[dict], group: str, bundle: Path, top: int, examples: int) -> dict:
    title, rule = GROUPS[group]
    items = [(p, o) for p in pages for o in p["occ"] if in_group(group, o)]
    by_page = Counter(p["path"] for p, _ in items)
    urls = Counter(o["url"] for _, o in items)
    pages_of_url: dict[str, set] = defaultdict(set)
    for p, o in items:
        pages_of_url[o["url"]].add(p["path"])
    shared_n = sum(1 for p, _ in items if p["shared"])
    r: dict = {"group": group, "title": title, "rule": rule, "occurrences": len(items), "unique_addresses": len(urls),
               "pages_total": len(pages), "pages_with": len(by_page), "pages_without": len(pages) - len(by_page),
               "in_shared_pages": shared_n, "in_content_pages": len(items) - shared_n}
    sites = sorted({p["site"] for p in pages})
    r["per_site"] = {s: {"occurrences": sum(1 for p, _ in items if p["site"] == s), "unique": len({o["url"] for p, o in items if p["site"] == s}),
                         "pages_with": len({p["path"] for p, _ in items if p["site"] == s}), "pages": sum(1 for p in pages if p["site"] == s)} for s in sites}
    r["per_page_with"] = spread(list(by_page.values()))
    r["per_page_all"] = spread([by_page.get(p["path"], 0) for p in pages])
    r["pages_with_most"] = by_page.most_common(top)
    repeated = {u: n for u, n in urls.items() if n > 1}
    same_page = Counter((p["path"], o["url"]) for p, o in items)
    r["repetition"] = {"addresses_used_more_than_once": len(repeated), "occurrences_beyond_the_first": sum(n - 1 for n in urls.values()),
                       "addresses_repeated_inside_one_page": len({u for (_, u), n in same_page.items() if n > 1}),
                       "most_used": [{"url": u, "times": n, "pages": len(pages_of_url[u])} for u, n in urls.most_common(top)]}
    texts = Counter(o["text"].strip().lower()[:60] for _, o in items)
    lengths = [len(o["text"].strip()) for _, o in items]
    if group == "image":
        r["alt"] = {"empty": sum(1 for _, o in items if not o["text"].strip()), "with_text": sum(1 for _, o in items if o["text"].strip()),
                    "pictures_that_are_links": sum(1 for _, o in items if o["in_link"]), "most_common_alt": [t for t in texts.most_common(top) if t[0]]}
    else:
        r["link_text"] = {"empty": sum(1 for n in lengths if n == 0), "distinct": len(texts), "length": spread(lengths),
                          "most_common": texts.most_common(top)}
    if group != "internal":
        hosts, h_urls, h_pages = Counter(), defaultdict(set), defaultdict(set)
        for p, o in items:
            h = host_of(o["url"]) or "(no host)"
            hosts[h] += 1
            h_urls[h].add(o["url"])
            h_pages[h].add(p["path"])
        r["hosts"] = {"distinct": len(hosts), "top": [{"host": h, "occurrences": n, "unique": len(h_urls[h]), "pages": len(h_pages[h]), "university": own(h)}
                                                     for h, n in hosts.most_common(top)]}
        parts = [urlsplit(o["url"]) for _, o in items]
        r["addresses"] = {"https": sum(1 for u in parts if u.scheme == "https"), "http": sum(1 for u in parts if u.scheme == "http"),
                          "with_query": sum(1 for u in parts if u.query), "with_fragment": sum(1 for u in parts if u.fragment),
                          "percent_encoded": sum(1 for _, o in items if "%" in o["url"])}
    if group in {"image", "files", "external", "university", "outside"}:
        ext = Counter((posixpath.splitext(unquote(urlsplit(o["url"]).path))[1].lower().lstrip(".") or "(none)") for _, o in items)
        r["extensions"] = dict(ext.most_common(top))
    if group == "video":
        r["platforms"] = dict(Counter(platform_of(o["url"]) for _, o in items).most_common())
    if group == "internal":
        targets = Counter(urlsplit(o["url"]).path for _, o in items)
        folders = Counter(posixpath.dirname(t) for t in targets.elements())
        dead = {t: n for t, n in targets.items() if not (bundle / t.lstrip("/")).exists()}
        self_links = sum(1 for p, o in items if urlsplit(o["url"]).path == p["path"])
        linked = set(targets)
        folder_pages = [p["path"] for p in pages if not p["shared"]]
        sources_of: dict[str, set] = defaultdict(set)
        for p, o in items:
            sources_of[urlsplit(o["url"]).path].add(p["path"])
        r["internal"] = {"targets_distinct": len(targets), "to_a_folder": dict(folders.most_common(top)), "links_to_pages_that_do_not_exist": sum(dead.values()),
                         "dead_targets": sorted(dead)[:top], "links_to_the_same_page": self_links,
                         "with_fragment": sum(1 for _, o in items if "#" in o["url"]),
                         "most_linked_pages": [{"page": t, "links": n, "from_pages": len(sources_of[t])} for t, n in targets.most_common(top)],
                         "pages_nothing_links_to": [p for p in folder_pages if p not in linked][:top], "count_pages_nothing_links_to": sum(1 for p in folder_pages if p not in linked)}
    first: dict[str, dict] = {}  # the first place of every address, in the order of the pages
    for p, o in items:
        first.setdefault(o["url"], {"page": p["path"], "line": o["line"], "text": o["text"].strip()[:70], "url": o["url"][:140]})
    distinct = list(first.values())
    r["examples"] = distinct[::max(1, len(distinct) // examples)][:examples] if examples else []  # (spread over the group, not its first ones)
    r["all"] = [{"url": u, "times": n, "pages": len(pages_of_url[u])} for u, n in urls.most_common()]
    return r


def pct(a: int, b: int) -> str:
    return f"{100 * a / b:.0f}%" if b else "-"


def show_group(r: dict, everything: bool) -> None:
    print(f"GROUP {r['group']}: {r['title']}")
    print(f"  in the group: {r['rule']}")
    print(f"\n  {r['occurrences']} occurrences, {r['unique_addresses']} different addresses")
    print(f"  on {r['pages_with']} of {r['pages_total']} pages ({pct(r['pages_with'], r['pages_total'])}); {r['pages_without']} pages have none")
    print(f"  in the shared blocks: {r['in_shared_pages']}, in the content of pages: {r['in_content_pages']}")
    rep = r["repetition"]
    print(f"  repeats: {rep['addresses_used_more_than_once']} addresses are used more than once ({rep['occurrences_beyond_the_first']} occurrences beyond the first), "
          f"{rep['addresses_repeated_inside_one_page']} of them twice or more inside one page")
    pw, pa = r["per_page_with"], r["per_page_all"]
    print(f"  per page: among the pages that have it min {pw['min']}, median {pw['median']}, mean {pw['mean']}, max {pw['max']}; "
          f"among all pages median {pa['median']}, mean {pa['mean']}")
    print("\n  per site:")
    for site, c in r["per_site"].items():
        print(f"    {site or '(root)':<12} {c['occurrences']:>6} occurrences  {c['unique']:>5} different  on {c['pages_with']:>3} of {c['pages']:>3} pages ({pct(c['pages_with'], c['pages'])})")
    if "alt" in r:
        a = r["alt"]
        print(f"\n  alt text: {a['with_text']} pictures with it, {a['empty']} without ({pct(a['empty'], r['occurrences'])}); {a['pictures_that_are_links']} pictures are links themselves")
        if a["most_common_alt"]:
            print("  most common alt: " + "; ".join(f"{t} ({n})" for t, n in a["most_common_alt"]))
    if "link_text" in r:
        t = r["link_text"]
        print(f"\n  link text: {t['distinct']} different, {t['empty']} empty, length median {t['length']['median']} (max {t['length']['max']})")
        print("  most common: " + "; ".join(f"{x!r} ({n})" for x, n in t["most_common"]))
    if "hosts" in r:
        print(f"\n  hosts ({r['hosts']['distinct']} different):")
        for h in r["hosts"]["top"]:
            print(f"    {h['occurrences']:>6} occurrences  {h['unique']:>5} addresses  {h['pages']:>4} pages  {h['host']}{'  (the university)' if h['university'] else ''}")
        a = r["addresses"]
        print(f"  addresses: https {a['https']}, http {a['http']}; with a query {a['with_query']}, with a fragment {a['with_fragment']}, percent-encoded {a['percent_encoded']}")
    if "extensions" in r:
        print("\n  file extensions: " + ", ".join(f"{e} {n}" for e, n in r["extensions"].items()))
    if "platforms" in r:
        print("\n  where the videos are: " + ", ".join(f"{e} {n}" for e, n in r["platforms"].items()))
    if "internal" in r:
        i = r["internal"]
        print(f"\n  {i['targets_distinct']} different pages are linked; {i['links_to_the_same_page']} links lead to the page they stand on, {i['with_fragment']} have a #fragment")
        print(f"  links to pages that do not exist in the bundle: {i['links_to_pages_that_do_not_exist']}" + (f" ({', '.join(i['dead_targets'])})" if i["dead_targets"] else ""))
        print("  by folder of the target: " + ", ".join(f"{f} {n}" for f, n in i["to_a_folder"].items()))
        print("  most linked pages:")
        for t in i["most_linked_pages"]:
            print(f"    {t['links']:>5} links from {t['from_pages']:>3} pages  {t['page']}")
        print(f"  pages no page links to: {i['count_pages_nothing_links_to']}" + (": " + ", ".join(i["pages_nothing_links_to"]) if i["pages_nothing_links_to"] else ""))
    print("\n  addresses used most:")
    for u in rep["most_used"]:
        print(f"    {u['times']:>5} times on {u['pages']:>3} pages  {u['url'][:110]}")
    print("\n  pages with most:")
    for path, n in r["pages_with_most"]:
        print(f"    {n:>5}  {path}")
    if r["examples"]:
        print("\n  examples (page:line  text -> address):")
        for e in r["examples"]:
            print(f"    {e['page']}:{e['line']}  {e['text'] or '(no text)'} -> {e['url']}")
    if everything:
        print(f"\n  every address ({len(r['all'])}):")
        for u in r["all"]:
            print(f"    {u['times']:>5} times on {u['pages']:>3} pages  {u['url']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, help="the data root (holds wiki/); default: settings.wiki_root or this checkout")
    ap.add_argument("--folder", default="raw/sites", help="folder of the bundle to read, below wiki/")
    ap.add_argument("--top", type=int, default=15, help="how many rows of a table")
    ap.add_argument("--group", choices=sorted(GROUPS), help="describe one group of links instead of the overview")
    ap.add_argument("--examples", type=int, default=8, help="with --group: how many examples (spread over the group)")
    ap.add_argument("--all", action="store_true", help="with --group: every address of the group with its count")
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
    pages = collect(bundle, folder)
    if args.group:
        report = group_report(pages, args.group, bundle, args.top, args.examples)
        if not args.all:
            report["all"] = []
        print(json.dumps(report, ensure_ascii=False, indent=1)) if args.json else show_group(report, args.all)
        return
    stats = summarize(pages, args.top)
    print(json.dumps(stats, ensure_ascii=False, indent=1)) if args.json else show(stats)


if __name__ == "__main__":
    main()
