"""New sites of the university, found by the wiki's run in the links of the pages it already reads and in the text of the
documents it read.

    catix-wiki sites discover [--dry-run] [--all]   # the hosts the pages link that no source reads yet, and what the probe says of them
                                                    # (--dry-run keeps nothing; --all: every candidate, however many, failed ones again)
    catix-wiki sites explore [--rounds 10] [--max-sites 60]   # discover --all, read what was found, look in its pages for more, again, until a round finds nothing
    catix-wiki sites add HOST_OR_URL ...                      # hosts you found yourself: probed, then pending like the others (no link needed)
    catix-wiki sites review                                   # what the pending sites gave: pages read, titles, who links them; and the hosts that need access
    catix-wiki sites approve HOST_OR_NAME ... | --all         # approve in WIKI_ROOT/raw/sites.yaml, fetch pages and build wiki navigation
    catix-wiki sites accept HOST_OR_NAME ... | --all          # alias for approve
    catix-wiki sites reject HOST_OR_NAME ... | --all          # not worth it: forgotten for good, with the pages read

A host is a candidate when
  - one page of the bundle links it, whatever its name; hosts of the university are probed first;
    hosts of the university mentioned in extracted documents are also collected;
  - it is not read yet (no site of SITES or of the pending ones, no alias of one), is not one a person rejected, and did not
    fail a probe lately.
The links come from the pages of the bundle and the documents of trusted sites, never from what people write in the chats:
anyone can write a link there.

A candidate is probed before anything is kept: its name must resolve to public addresses only, https, its robots.txt must not
close the start page, the start page (and where it redirects, which must also resolve to public addresses) must have words of its
own, not a login or an empty shell. A bot check that answers in place of the start page ('Вы не робот?' of timepad, behind
Yandex) is asked again (sites.get_through: the wall comes and goes), and named when it lets nothing through. A host that
passes becomes a *pending* site in raw/sites-discovered.json and is read like the others, but with the safe settings of
sites.found_site (30 pages, robots.txt, a slow pace). Its settings are in the record's `config`; it is not a trusted provider.
A person reviews it, then `sites approve` moves it to raw/sites.yaml in the same data checkout; `sites reject` forgets it. Failed and closed probes
remain in raw/sites-discovered.json so discover can retry or show that access is needed. At most MAX_NEW sites a run.
"""

import ipaddress
import fcntl
import re
import socket
import sys
import time
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from http.cookiejar import CookieJar, DefaultCookiePolicy
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from catix.wiki.paths import DOCS
from catix.settings import settings
from catix.wiki.sources import eduwiki, regulations, sites, sveden

UNIVERSITY = sites.UNIVERSITY
MIN_PAGES = 1  # pages of the bundle that must link the host: one link is enough (a person decides in `sites review`)
MAX_NEW = 10  # sites found in one run
MAX_PROBES = 60  # hosts probed in one run
MIN_WORDS = 30  # words of the start page without the lines every page of the site repeats
RETRY_DAYS = 30  # a host that failed its probe is probed again after this long
RETRY_UNREACHABLE_DAYS = 7  # ... and one that did not answer (an outage, a name that did not resolve, a bot check that let nothing through), sooner
UNREACHABLE = ("no answer", "the name does not resolve", "a bot check")
CLOSED = "needs access"  # the reason of a host behind a login or answering 401/403: status "closed", listed by `sites review`
LINK = re.compile(r"\]\((https?://[^)\s]+)\)")
HOST = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}")  # (a name: not the end of a word the text of a PDF glued to an address)
LOGIN_TITLE = re.compile(r"(?i)авториз|личный кабинет|вход\b|регистрац|sign.?in|log.?in|account")
APP_SHELL = re.compile(r"""(?i)id=["'](root|app|__next|__nuxt)["']|<script[^>]+type=["']module|enable javascript|<noscript""")  # a page the scripts fill in
PASSWORD_FIELD = re.compile(r"""(?i)<input[^>]+type=["']?password""")


def host_of(url: str) -> str:
    return (urlsplit(url).hostname or "").lower().rstrip(".").removeprefix("www.")  # (a name may end with a dot: 'innopoliscamp.ru.')


def kind_of(host: str) -> str:
    """'university' for a host of the university, 'external' for any other host; a priority, not a filter."""
    if any(host == s or host.endswith("." + s) for s in UNIVERSITY):
        return "university"
    return "external"


def read_by_code() -> set[str]:
    """The hosts the code reads without a line in SITES: a source of its own (the eduwiki's API, the disclosure section and the
    documents of the university) or the agent's tools (the InNoHassle API: clubs, events, maps). They come from the constants the
    code reads them by; tests/test_wiki_discover.py fails when the code names a host that is not here."""
    return {host_of(url) for url in (eduwiki.API, sveden.BASE, regulations.BASE, str(settings.innohassle_api))}


def known_hosts() -> set[str]:
    """The hosts that are read already or must not be asked: what the code reads, every site of SITES with its aliases, and the found ones."""
    sites.reload_catalog()
    known = read_by_code()
    for site in sites.every_site().values():  # (the pending sites too: found already)
        known |= {host_of(site.base), *site.aliases}
    return known | sites.BLOCKED | {host for host, entry in sites.discovered().items() if entry.get("status") not in ("failed", "closed")}  # (a failed or closed one is asked again later: retry_later)


def links_by_host() -> dict[str, set[str]]:
    """host -> the pages of the bundle's sites that link it, and the documents read whose text names it, if it is a host of the
    university (a document by its page of the bundle, /raw/regulations/<key>.md, or by its address before it has one)."""
    from catix.wiki.sources import crawl

    found: dict[str, set[str]] = {}
    for path in sorted((DOCS / sites.FOLDER).rglob("*.md")):
        for url in LINK.findall(path.read_text(encoding="utf-8")):
            if (host := host_of(url)) and HOST.fullmatch(host):
                found.setdefault(host, set()).add("/" + path.relative_to(DOCS.parent).as_posix())
    for key, doc in regulations.all_docs().items():
        if not (text := doc["root"] / f"{key}.txt").exists():
            continue
        page = DOCS / "regulations" / f"{key}.md"
        where = "/" + page.relative_to(DOCS.parent).as_posix() if page.exists() else doc["url"]
        for raw in crawl.URL.findall(text.read_text(encoding="utf-8")):
            if (host := host_of(raw.rstrip(crawl.TRAILING))) and HOST.fullmatch(host) and kind_of(host) == "university":
                found.setdefault(host, set()).add(where)
    return found


def candidates(rejected: set[str]) -> list[tuple[str, str, list[str]]]:
    """(host, kind, the pages that link it), the hosts of the university first, then the most linked."""
    known = known_hosts()
    out = []
    for host, pages in links_by_host().items():
        kind = kind_of(host)
        if host in known or host in rejected or len(pages) < MIN_PAGES:
            continue
        out.append((host, kind, sorted(pages)))
    out.sort(key=lambda c: (c[1] != "university", -len(c[2]), c[0]))
    return out


def retry_later(found: dict, host: str, now: datetime) -> bool:
    entry = found.get(host)
    if not entry or entry.get("status") not in ("failed", "closed"):
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
        robots = sites.get_through(client, f"https://{host}/robots.txt")
        if robots.status_code == 200:
            rules = RobotFileParser()
            rules.parse(robots.text.splitlines())
            if not rules.can_fetch(regulations.HEADERS["User-Agent"], f"https://{host}/"):
                return "robots.txt closes the start page"
        page = sites.get_through(client, f"https://{host}/")
    except httpx.HTTPError as e:
        return f"no answer ({type(e).__name__})"
    final = host_of(str(page.url))
    if page.url.scheme != "https":
        return "redirects away from https"
    if final != host:
        if final in known_hosts():
            return f"is {final} (a site read already)"
        if not public(final):
            return f"redirects to {final}"
    if page.status_code in (401, 403):
        return f"{CLOSED} (HTTP {page.status_code})"
    if page.status_code != 200 or "text/html" not in page.headers.get("content-type", ""):
        return f"HTTP {page.status_code}, not a page"
    html, rendered = page.text, False
    title, text, _ = sites.read(html, str(page.url))
    if sites.needs_script(page) or len(text.split()) < MIN_WORDS and APP_SHELL.search(html):
        # an app: its HTML is an empty shell, the text comes from scripts (a headless browser runs them, as for Site.render)
        try:
            shown = sites.render_page(str(page.url))
        except Exception:  # noqa: BLE001 - a browser that cannot start or time out is "no words" below
            shown = None
        if shown:
            html, rendered = shown, True
            title, text, _ = sites.read(html, str(page.url))
    if PASSWORD_FIELD.search(html) or LOGIN_TITLE.search(title):
        return f"{CLOSED} (a login page: '{title[:60]}')"
    if sites.WALL_TITLE.search(title):  # (a bot check that let none of the asks through: the wall comes and goes, the host is asked again in a week)
        return f"a bot check answers in place of the start page ('{title[:40]}')"
    words = len(text.split())
    if words < MIN_WORDS:
        return f"the start page has {words} words (a login, or an empty shell)"
    return {"title": re.sub(r"\s+", " ", title)[:120], "words": words, "language": "ru" if re.search("[а-яё]", text.lower()) else "en",
            **({"render": True} if rendered else {})}


def write(found: dict) -> None:
    found = {host: {**entry, "name": sites.discovered_name(host, entry),
                    "config": sites.site_values(sites.found_site(host, entry)) | entry.get("config", {})}
             if entry.get("status") == "pending" else entry for host, entry in found.items()}
    sites.write_discovered(found)


def discover(rejected: set[str] = frozenset(), client: httpx.Client | None = None, dry_run: bool = False, pause: float = sites.PAUSE,
             everything: bool = False, since: datetime | None = None) -> int:
    """Probe the candidates, keep the ones that pass as pending sites; how many were found. `dry_run` probes and says what it
    would do, but keeps nothing (raw/sites-discovered.json, which holds the pending sites and their settings, is not written). `everything`: no limit of hosts or
    of sites for the run, and the hosts that failed a probe lately are probed again (a night's run by hand), except those that
    failed since `since` (the earlier rounds of `explore`)."""
    now = datetime.now(timezone.utc)
    found = sites.discovered()
    if not any((DOCS / sites.FOLDER).rglob("*.md")):
        print(f"  no pages of sites in {DOCS / sites.FOLDER}: there is nothing to look in for links (is WIKI_ROOT a checkout of the wiki?)", flush=True)
    own = client or httpx.Client(headers=regulations.HEADERS, timeout=20, follow_redirects=True,
                                 cookies=CookieJar(policy=DefaultCookiePolicy(allowed_domains=[])))
    added = probes = 0
    taken: list[str] = []
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
                closed = result.startswith(CLOSED)  # (kept with who links it: `sites review` lists it for a person to give access)
                found[host] = {"status": "closed" if closed else "failed", "kind": kind, "reason": result, "tried": now.isoformat(timespec="seconds"),
                               **({"pages": len(pages), "examples": pages[:3]} if closed else {})}
            else:
                print(f"  {host}: {'would be found' if dry_run else 'found'}, '{result['title']}', {result['words']} words, linked from {len(pages)} pages")
                found[host] = {"status": "pending", "kind": kind, "found": now.date().isoformat(), "pages": len(pages), "examples": pages[:3], **result}
                taken.append(host)
                added += 1
            time.sleep(pause)
    finally:
        if client is None:
            own.close()
    if not dry_run:
        write(found)

    return added


def pending_hosts() -> list[str]:
    pending = sites.pending_sites()
    return sorted(host for host, entry in sites.discovered().items()
                  if entry.get("status") == "pending" and sites.discovered_name(host, entry) in pending)


def accept_pending(hosts: list[str] | None = None) -> list[str]:
    """Approve pending sites in raw/sites.yaml and remove them from the discovery queue in the same data checkout."""
    found = sites.discovered()
    selected = [h for h in pending_hosts() if hosts is None or h in hosts]
    for host in selected:
        sites.approve_discovered(host, found.pop(host, {}))
    if selected:
        write(found)
    return selected


def build_approved(names: list[str]) -> None:
    """Read the selected sites (and of the trusted sites they link only the pages those do not have yet: sites.fetch) and
    build source pages/navigation, without the agent, documents or a full wiki rebuild."""
    from catix.wiki import compile as compiler

    if not names:
        return
    sites.fetch(names)
    empty = [name for name in names if not any(not page.get("gone") for page in sites.load(name)["pages"].values())]
    if empty:
        raise RuntimeError(f"no pages could be read: {', '.join(empty)}")
    sites.compile_all()
    empty = [name for name in names if not any(p.name != "index.md" for p in (sites.DOCS / sites.FOLDER / name).glob("*.md"))]
    if empty:
        raise RuntimeError(f"no readable wiki pages produced: {', '.join(empty)}")
    compiler.link()


def approve_sites(hosts: list[str]) -> list[str]:
    """The user-facing approval also builds pages. Already approved sites may be named again after a failed build."""
    from catix.wiki import autopilot

    if not hosts:
        return []
    autopilot.LOCK.parent.mkdir(parents=True, exist_ok=True)
    with autopilot.LOCK.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            sys.exit("another wiki update is running; approval was not changed")
        sites.reload_catalog()
        entries = sites.discovered()
        approved = {host_of(site.base): name for name, site in sites.SITES.items()}
        names = [approved[host] if host in approved else sites.discovered_name(host, entries[host]) for host in hosts]
        accept_pending(hosts)
        try:
            build_approved(names)
        except Exception as error:
            sys.exit(f"sites remain approved, but building failed: {error}; retry: catix-wiki sites approve {' '.join(names)}")
    return hosts


def unread_hosts() -> list[str]:
    """Pending runtime sites that have no pages read yet."""
    pending = sites.pending_sites()
    return [host for host, entry in sorted(sites.discovered().items())
            if entry.get("status") == "pending" and (name := sites.discovered_name(host, entry)) in pending
            and not (sites.ROOT / name / "index.json").exists()]


def explore(rejected: set[str], max_rounds: int = 10, max_sites: int = 60, client: httpx.Client | None = None, pause: float = sites.PAUSE) -> list[str]:
    """Rounds, until a round finds nothing new: probe every candidate, read the sites that passed, make their pages (the links
    of a page are read from the made pages, not from the database: no search index is needed between rounds), look in them for
    hosts again. The sites found, all of them pending a person's look (`sites review`, `sites accept`, `sites reject`)."""
    started, total, attempted = datetime.now(timezone.utc), [], set()
    for number in range(1, max_rounds + 1):
        before = set(pending_hosts())
        print(f"== round {number}", flush=True)
        discover(rejected, client=client, pause=pause, everything=True, since=started)
        # (a site nobody has read yet counts too: one a person added with `sites add`, or accepted before it was read)
        unread = [h for h in unread_hosts() if h not in attempted]
        new = sorted(set(pending_hosts()) - before)
        if not new and not unread:
            print("nothing new: the search is over", flush=True)
            break
        total += [h for h in new if h not in total]
        entries = sites.discovered()
        names = [sites.discovered_name(host, entries[host]) for host in dict.fromkeys([*new, *unread])]
        attempted |= {*new, *unread}
        print(f"== reading {', '.join(names)}", flush=True)
        try:
            sites.fetch(names)
            regulations.fetch(prefixes=tuple(f"site-{name}-" for name in names), ocr=False)  # text layers only; scans stay queued
        except Exception as e:  # noqa: BLE001 - one site down must not end the night's run; its pages are what was read
            print(f"  reading stopped: {type(e).__name__}: {e}", flush=True)
        sites.compile_all()
        if len(total) >= max_sites:
            print(f"{len(total)} sites found, the limit of this run ({max_sites}): enough for now", flush=True)
            break
    else:
        print(f"{max_rounds} rounds: there may be more, run it again", flush=True)
    return total


def closed_hosts() -> list[str]:
    return sorted(host for host, entry in sites.discovered().items() if entry.get("status") == "closed")


def resolve(names: list[str], closed: bool = False, approved: bool = False) -> list[str]:
    """Pending hosts (and closed ones when `closed`) by a host or a name of a site ('lab' for lab.innopolis.university)."""
    pending = pending_hosts() + (closed_hosts() if closed else [])
    found = sites.discovered()
    by_name = {sites.discovered_name(h, found[h]): h for h in pending}
    if approved:
        sites.reload_catalog()
        for name, site in sites.SITES.items():
            host = host_of(site.base)
            pending.append(host)
            by_name.update({name: host, **{alias: host for alias in site.aliases}})
    unknown = [n for n in names if n not in pending and n not in by_name]
    if unknown:
        sys.exit(f"not pending{' or closed' if closed else ''}: {', '.join(unknown)}; they are {', '.join(by_name) or 'none'}")
    return list(dict.fromkeys(n if n in pending else by_name[n] for n in names))


def reject(hosts: list[str]) -> list[str]:
    """A person looked and the sites are not worth it: forgotten for good, with what was read of them."""
    import shutil

    from catix.wiki import autopilot

    sites.reload_catalog()
    found = sites.discovered()
    for host in hosts:
        if host not in found:
            raise ValueError(f"not a discovered site: {host}")
        name = sites.discovered_name(host, found[host])
        if name in sites.SITES:
            raise ValueError(f"refusing to delete approved site {name}")
    state = autopilot.load_state()
    state["rejected_sites"] = sorted({*state.get("rejected_sites", []), *hosts})
    autopilot.save_state(state)
    for host in hosts:
        name = sites.discovered_name(host, found.pop(host, {}))
        for folder in (sites.ROOT / name, DOCS / sites.FOLDER / name):
            shutil.rmtree(folder, ignore_errors=True)
    write(found)
    return hosts


def review() -> None:
    """What the pending sites gave, to decide which are worth keeping."""
    found = sites.discovered()
    for host in pending_hosts():
        entry, name = found[host], sites.discovered_name(host, found[host])
        index = sites.load(name)
        pages = [p for p in index["pages"].values() if not p.get("gone")]
        titles = "; ".join(p["title"][:50] for p in pages[:4])
        print(f"{name}   {host}   [{entry.get('kind')}] linked from {entry.get('pages')} pages, e.g. {(entry.get('examples') or ['?'])[0]}")
        print(f"   '{entry.get('title')}': {len(pages)} pages read, {len(index['docs'])} documents linked")
        print(f"   {titles or 'no page read yet (sites fetch ' + name + ')'}")
    if not pending_hosts():
        print("no site waits for a look")
    if closed := closed_hosts():
        print(f"\n== need access ({len(closed)}): behind a login or answering 401/403; not read. To read one, log a Chromium profile in and give it a line in SITES")
        print("   with profile=... (see sites.py: `my`, `help`); `sites reject HOST` forgets it for good")
        for host in closed:
            entry = found[host]
            print(f"{host}   [{entry.get('kind')}] {entry.get('reason', '').removeprefix(CLOSED).strip(' ()')}; linked from {entry.get('pages', '?')} pages, e.g. {(entry.get('examples') or ['?'])[0]}")


def add(addresses: list[str], client: httpx.Client | None = None, pause: float = sites.PAUSE) -> int:
    """Hosts a person found themselves: probed like the others (public addresses, https, robots.txt, a page of words), but no
    link in the bundle is needed, and they may be any host. They become pending sites. How many were kept."""
    now = datetime.now(timezone.utc)
    found = sites.discovered()
    own = client or httpx.Client(headers=regulations.HEADERS, timeout=20, follow_redirects=True,
                                 cookies=CookieJar(policy=DefaultCookiePolicy(allowed_domains=[])))
    kept, taken = 0, []
    try:
        for address in addresses:
            host = host_of(address if "//" in address else f"https://{address}")
            if not host or host in known_hosts() or host in found and found[host].get("status") in ("pending", "accepted"):
                print(f"  {host or address}: read already or waiting for a look")
                continue
            result = probe(host, own)
            if isinstance(result, str):
                print(f"  {host}: not taken: {result}")
                found[host] = {"status": "closed" if result.startswith(CLOSED) else "failed", "kind": "manual", "reason": result, "tried": now.isoformat(timespec="seconds")}
            else:
                print(f"  {host}: kept as pending, '{result['title']}', {result['words']} words")
                found[host] = {"status": "pending", "kind": "manual", "found": now.date().isoformat(), "pages": 0, "examples": [], **result}
                taken.append(host)
                kept += 1
            time.sleep(pause)
    finally:
        if client is None:
            own.close()
    write(found)
    return kept


def main(args: Namespace) -> None:
    from catix.wiki import autopilot

    rejected = set(autopilot.load_state().get("rejected_sites", []))
    cmd = args.action
    if cmd == "explore":
        total = explore(rejected, args.rounds, args.max_sites)
        print(f"{len(total)} sites found; `catix-wiki sites review` shows what they gave")
        return
    if cmd == "add":
        kept = add(args.addresses)
        print(f"{kept} sites kept as pending; `catix-wiki sites explore` reads them and looks in their pages for more")
        return
    if cmd == "review":
        return review()
    if cmd in ("accept", "approve", "reject"):
        cmd = "accept" if cmd == "approve" else cmd
        names = args.names
        if cmd == "accept" and any(n in closed_hosts() for n in names):
            sys.exit("a closed site cannot be read without access: give a Chromium profile a login and a line in SITES (sites.py)")
        hosts = pending_hosts() + (closed_hosts() if cmd == "reject" else []) if args.all else resolve(names, closed=cmd == "reject", approved=cmd == "accept")
        done = approve_sites(hosts) if cmd == "accept" else reject(hosts)
        print(f"{'approved and built' if cmd == 'accept' else 'rejected'}: {', '.join(done) or 'none'}")
        return
    found = discover(rejected, dry_run=args.dry_run, everything=args.all)
    print(f"{found} new sites" + (" would be kept (dry run: nothing was written)" if args.dry_run else ""))
    if pending := pending_hosts():
        print("pending a person's look: " + ", ".join(pending), file=sys.stderr)
