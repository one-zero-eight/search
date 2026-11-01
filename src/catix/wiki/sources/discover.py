"""New sites of the university, found by the wiki's run in the links of the pages it already reads.

    catix-wiki sites discover [--dry-run] [--all]   # the hosts the pages link that no source reads yet, and what the probe says of them
                                                    # (--dry-run keeps nothing; --all: every candidate, however many, failed ones again)
    catix-wiki sites explore [--rounds 10] [--max-sites 60]   # discover --all, read what was found, look in its pages for more, again, until a round finds nothing
    catix-wiki sites review                                   # what the pending sites gave: pages read, titles, who links them
    catix-wiki sites accept HOST_OR_NAME ... | --all          # worth keeping: read from now on (then `autopilot --build` makes the pages, the index, the review)
    catix-wiki sites reject HOST_OR_NAME ... | --all          # not worth it: forgotten for good, with the pages read

A host is a candidate when
  - it is a host of the university (innopolis.university, innopolis.ru, innopolis.edu.ru, innopolis.com, innopolis.college,
    and their subdomains) that one page of the bundle links, or another host with the word `inno` in its name
    (innopolis, innohassle, inno-..., not `innovation`) that three pages link;
  - it is not read yet (no site of SITES, no alias of one), is not one a person rejected, and did not fail a probe lately.
The links come from the pages of the bundle, never from what people write in the chats: anyone can write a link there.

A candidate is probed before anything is kept: its name must resolve to public addresses only, https, its robots.txt must not
close the start page, the start page (and where it redirects, which must be a host of the same kind) must have words of its
own, not a login or an empty shell. A host that passes becomes a *pending* site in raw/sites-discovered.json and is read like
the others, but with the safe settings of sites.load_discovered (30 pages, robots.txt, a slow pace). A pending site never
reaches the `wiki` branch by itself: the run sends everything it brought to a review branch and tells the admins (autopilot.py);
`autopilot accept` makes it accepted, `autopilot discard` makes the run forget it. At most MAX_NEW sites a run.
"""

import ipaddress
import json
import re
import socket
import sys
import time
from datetime import datetime, timedelta, timezone
from http.cookiejar import CookieJar, DefaultCookiePolicy
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from catix.wiki.paths import DOCS
from catix.settings import settings
from catix.wiki.sources import eduwiki, regulations, sites, sveden

UNIVERSITY = ("innopolis.university", "innopolis.ru", "innopolis.edu.ru", "innopolis.com", "innopolis.college")
INNO = re.compile(r"(^|[.-])inno(polis|hassle)?([.-]|$)|innopolis|innohassle")
MIN_PAGES = {"university": 1, "inno": 3}  # pages of the bundle that must link the host
MAX_NEW = 3  # sites found in one run
MAX_PROBES = 8  # hosts probed in one run
MIN_WORDS = 30  # words of the start page without the lines every page of the site repeats
RETRY_DAYS = 30  # a host that failed its probe is probed again after this long
RETRY_UNREACHABLE_DAYS = 7  # ... and one that did not answer (an outage, a name that did not resolve), sooner
UNREACHABLE = ("no answer", "the name does not resolve")
LINK = re.compile(r"\]\((https?://[^)\s]+)\)")
LOGIN_TITLE = re.compile(r"(?i)авториз|личный кабинет|вход\b|регистрац|sign.?in|log.?in|account")
PASSWORD_FIELD = re.compile(r"""(?i)<input[^>]+type=["']?password""")


def host_of(url: str) -> str:
    return (urlsplit(url).hostname or "").lower().removeprefix("www.")


def kind_of(host: str) -> str | None:
    """'university' for a host of the university, 'inno' for another with the word in its name, else None."""
    if any(host == s or host.endswith("." + s) for s in UNIVERSITY):
        return "university"
    return "inno" if INNO.search(host) else None


def read_by_code() -> set[str]:
    """The hosts the code reads without a line in SITES: a source of its own (the eduwiki's API, the disclosure section and the
    documents of the university) or the agent's tools (the InNoHassle API: clubs, events, maps). They come from the constants the
    code reads them by; tests/test_wiki_discover.py fails when the code names a host that is not here."""
    return {host_of(url) for url in (eduwiki.API, sveden.BASE, regulations.BASE, str(settings.innohassle_api))}


def known_hosts() -> set[str]:
    """The hosts that are read already or must not be asked: what the code reads, every site of SITES with its aliases, and the found ones."""
    known = read_by_code()
    for site in sites.SITES.values():
        known |= {host_of(site.base), *site.aliases}
    return known | {host for host, entry in sites.discovered().items() if entry.get("status") != "failed"}  # (a failed one is asked again later: retry_later)


def links_by_host() -> dict[str, set[str]]:
    """host -> the pages of the bundle's sites that link it."""
    found: dict[str, set[str]] = {}
    for path in sorted((DOCS / sites.FOLDER).rglob("*.md")):
        for url in LINK.findall(path.read_text(encoding="utf-8")):
            if host := host_of(url):
                found.setdefault(host, set()).add("/" + path.relative_to(DOCS.parent).as_posix())
    return found


def candidates(rejected: set[str]) -> list[tuple[str, str, list[str]]]:
    """(host, kind, the pages that link it), the hosts of the university first, then the most linked."""
    known = known_hosts()
    out = []
    for host, pages in links_by_host().items():
        kind = kind_of(host)
        if not kind or host in known or host in rejected or len(pages) < MIN_PAGES[kind]:
            continue
        out.append((host, kind, sorted(pages)))
    out.sort(key=lambda c: (c[1] != "university", -len(c[2]), c[0]))
    return out


def retry_later(found: dict, host: str, now: datetime) -> bool:
    entry = found.get(host)
    if not entry or entry.get("status") != "failed":
        return False
    days = RETRY_UNREACHABLE_DAYS if entry.get("reason", "").startswith(UNREACHABLE) else RETRY_DAYS
    return now - datetime.fromisoformat(entry["tried"]) < timedelta(days=days)


def public(host: str) -> bool:
    """Whether the name resolves, and only to addresses of the internet (not 127.0.0.1, 10.x, a link-local or a metadata address)."""
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)}
    except OSError:
        return False
    return bool(addresses) and all(ipaddress.ip_address(a).is_global for a in addresses)


def probe(host: str, client: httpx.Client) -> dict | str:
    """What the start page of the host says ({title, words, language}), or why the host is not taken."""
    if not public(host):
        return "the name does not resolve to public addresses"
    try:
        robots = client.get(f"https://{host}/robots.txt")
        if robots.status_code == 200:
            rules = RobotFileParser()
            rules.parse(robots.text.splitlines())
            if not rules.can_fetch(regulations.HEADERS["User-Agent"], f"https://{host}/"):
                return "robots.txt closes the start page"
        page = client.get(f"https://{host}/")
    except httpx.HTTPError as e:
        return f"no answer ({type(e).__name__})"
    final = host_of(str(page.url))
    if page.url.scheme != "https":
        return "redirects away from https"
    if final != host:
        if final in known_hosts():
            return f"is {final} (a site read already)"
        if not kind_of(final) or not public(final):
            return f"redirects to {final}"
    if page.status_code != 200 or "text/html" not in page.headers.get("content-type", ""):
        return f"HTTP {page.status_code}, not a page"
    title, text, _ = sites.read(page.text, str(page.url))
    if PASSWORD_FIELD.search(page.text) or LOGIN_TITLE.search(title):
        return f"a login page ('{title[:60]}')"
    words = len(text.split())
    if words < MIN_WORDS:
        return f"the start page has {words} words (a login, or an empty shell)"
    return {"title": re.sub(r"\s+", " ", title)[:120], "words": words, "language": "ru" if re.search("[а-яё]", text.lower()) else "en"}


def write(found: dict) -> None:
    text = json.dumps({"sites": found}, ensure_ascii=False, indent=1, sort_keys=True)
    if not sites.DISCOVERED.exists() or sites.DISCOVERED.read_text(encoding="utf-8") != text:
        sites.DISCOVERED.parent.mkdir(parents=True, exist_ok=True)
        sites.DISCOVERED.write_text(text, encoding="utf-8")


def discover(rejected: set[str] = frozenset(), client: httpx.Client | None = None, dry_run: bool = False, pause: float = sites.PAUSE,
             everything: bool = False, since: datetime | None = None) -> int:
    """Probe the candidates, keep the ones that pass as pending sites; how many were found. `dry_run` probes and says what it
    would do, but keeps nothing (the file of found sites is not written, SITES does not change). `everything`: no limit of hosts or
    of sites for the run, and the hosts that failed a probe lately are probed again (a night's run by hand), except those that
    failed since `since` (the earlier rounds of `explore`)."""
    now = datetime.now(timezone.utc)
    found = sites.discovered()
    own = client or httpx.Client(headers=regulations.HEADERS, timeout=20, follow_redirects=True,
                                 cookies=CookieJar(policy=DefaultCookiePolicy(allowed_domains=[])))
    added = probes = 0
    try:
        for host, kind, pages in candidates(set(rejected)):
            if not everything and (added >= MAX_NEW or probes >= MAX_PROBES):
                break
            if not everything and retry_later(found, host, now):
                continue
            if since and found.get(host, {}).get("tried", "") >= since.isoformat(timespec="seconds"):
                continue  # (this run of explore asked it already)
            probes += 1
            result = probe(host, own)
            if isinstance(result, str):
                print(f"  {host}: not taken: {result}")
                found[host] = {"status": "failed", "kind": kind, "reason": result, "tried": now.isoformat(timespec="seconds")}
            else:
                print(f"  {host}: {'would be found' if dry_run else 'found'}, '{result['title']}', {result['words']} words, linked from {len(pages)} pages")
                found[host] = {"status": "pending", "kind": kind, "found": now.date().isoformat(), "pages": len(pages), "examples": pages[:3], **result}
                added += 1
            time.sleep(pause)
    finally:
        if client is None:
            own.close()
    if not dry_run:
        write(found)
        sites.load_discovered()
    return added


def pending_hosts() -> list[str]:
    return sorted(host for host, entry in sites.discovered().items() if entry.get("status") == "pending")


def accept_pending(hosts: list[str] | None = None) -> list[str]:
    """A person read what the pending sites gave: they are accepted (and need no look again). `hosts`: only these."""
    found, hosts = sites.discovered(), [h for h in pending_hosts() if hosts is None or h in hosts]
    for host in hosts:
        found[host]["status"] = "accepted"
    if hosts:
        write(found)
    return hosts


def explore(rejected: set[str], max_rounds: int = 10, max_sites: int = 60, client: httpx.Client | None = None, pause: float = sites.PAUSE) -> list[str]:
    """Rounds, until a round finds nothing new: probe every candidate, read the sites that passed, make their pages (the links
    of a page are read from the made pages, not from the database: no search index is needed between rounds), look in them for
    hosts again. The sites found, all of them pending a person's look (`sites review`, `sites accept`, `sites reject`)."""
    started, total = datetime.now(timezone.utc), []
    for number in range(1, max_rounds + 1):
        before = set(pending_hosts())
        print(f"== round {number}", flush=True)
        discover(rejected, client=client, pause=pause, everything=True, since=started)
        new = sorted(set(pending_hosts()) - before)
        if not new:
            print("nothing new: the search is over", flush=True)
            break
        total += new
        names = [sites.site_name(host) for host in new]
        print(f"== reading {', '.join(names)}", flush=True)
        try:
            sites.fetch(names)
        except Exception as e:  # noqa: BLE001 - one site down must not end the night's run; its pages are what was read
            print(f"  reading stopped: {type(e).__name__}: {e}", flush=True)
        sites.compile_all()
        if len(total) >= max_sites:
            print(f"{len(total)} sites found, the limit of this run ({max_sites}): enough for now", flush=True)
            break
    else:
        print(f"{max_rounds} rounds: there may be more, run it again", flush=True)
    return total


def resolve(names: list[str]) -> list[str]:
    """Pending hosts by a host or a name of a site ('lab' for lab.innopolis.university)."""
    pending = pending_hosts()
    by_name = {sites.site_name(h): h for h in pending}
    unknown = [n for n in names if n not in pending and n not in by_name]
    if unknown:
        sys.exit(f"not pending: {', '.join(unknown)}; pending are {', '.join(by_name) or 'none'}")
    return [n if n in pending else by_name[n] for n in names]


def reject(hosts: list[str]) -> list[str]:
    """A person looked and the sites are not worth it: forgotten for good, with what was read of them."""
    import shutil

    from catix.wiki import autopilot

    state = autopilot.load_state()
    state["rejected_sites"] = sorted({*state.get("rejected_sites", []), *hosts})
    autopilot.save_state(state)
    found = sites.discovered()
    for host in hosts:
        found.pop(host, None)
        name = sites.site_name(host)
        sites.SITES.pop(name, None)
        for folder in (sites.ROOT / name, DOCS / sites.FOLDER / name):
            shutil.rmtree(folder, ignore_errors=True)
    write(found)
    return hosts


def review() -> None:
    """What the pending sites gave, to decide which are worth keeping."""
    found = sites.discovered()
    for host in pending_hosts():
        entry, name = found[host], sites.site_name(host)
        index = sites.load(name)
        pages = [p for p in index["pages"].values() if not p.get("gone")]
        titles = "; ".join(p["title"][:50] for p in pages[:4])
        print(f"{name}   {host}   [{entry.get('kind')}] linked from {entry.get('pages')} pages, e.g. {(entry.get('examples') or ['?'])[0]}")
        print(f"   '{entry.get('title')}': {len(pages)} pages read, {len(index['docs'])} documents linked")
        print(f"   {titles or 'no page read yet (sites fetch ' + name + ')'}")
    if not pending_hosts():
        print("nothing waits for a look")


def main(args: list[str]) -> None:
    from catix.wiki import autopilot

    rejected = set(autopilot.load_state().get("rejected_sites", []))
    option = lambda name, default: int(args[args.index(name) + 1]) if name in args else default  # noqa: E731
    if args[:1] == ["explore"]:
        total = explore(rejected, option("--rounds", 10), option("--max-sites", 60))
        print(f"{len(total)} sites found; `catix-wiki sites review` shows what they gave")
        return
    if args[:1] == ["review"]:
        return review()
    if args[:1] in (["accept"], ["reject"]):
        names = [a for a in args[1:] if not a.startswith("--")]
        hosts = pending_hosts() if "--all" in args else resolve(names)
        done = accept_pending(hosts) if args[0] == "accept" else reject(hosts)
        print(f"{'accepted' if args[0] == 'accept' else 'rejected'}: {', '.join(done) or 'none'}")
        return
    dry = "--dry-run" in args
    found = discover(rejected, dry_run=dry, everything="--all" in args)
    print(f"{found} new sites" + (" would be kept (dry run: nothing was written)" if dry else ""))
    if pending := pending_hosts():
        print("pending a person's look: " + ", ".join(pending), file=sys.stderr)
