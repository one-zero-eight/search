"""The sites of the university and its services as a source of the bundle: innopolis.university (the university's own
site, every page in Russian and English; of its disclosure section /sveden/ sveden.py reads the documents, this the text of
the pages: the staff, the structure), apply.innopolis.university (for applicants: programmes, admission, grants, olympiads;
Russian), campuslife.innopolis.ru
(student life: the handbook, the FAQ, scholarships, clubs; English), hotel.innopolis.university (the campus and its
dormitories; Russian), new.innopolis.university/en/ (international applicants; English), media.innopolis.university (the
news and events), stc.innopolis.university (IT courses), edu.innopolis.university (programmes for schools and teachers),
innopolis.com (the city and its special economic zone; Russian and English), and the sites of the university's units and
projects the pages link most (career, corporate, dovuz, progmatica, the college, the dissertation council, ...; see SITES).

    catix-wiki sites fetch [SITE ...]   # the pages of every site (or of those named) -> raw/sites/<site>/ (one request every Site.pause seconds); trusted-provider page links are followed recursively,
                                        # through the documents too: their text layers (scans queued for manual OCR), the pages their text names, their documents, ...
    catix-wiki sites new [SITE ...]     # only the pages that appeared: the new links of each site's feed (or start page), and the new pages they link on any trusted site,
                                        # through the documents they link, read by their text layer alone (a scan waits for a manual OCR run)
    catix-wiki sites compile    # raw/sites -> wiki/raw/sites/<site>/<slug>.md
    catix-wiki sites status     # pages and documents found on every site
    catix-wiki sites docs       # the documents of trusted sites that the pages link and no site has yet: to be downloaded by `regs fetch`
    catix-wiki sites discover | explore | add | review | approve | reject   # new sites of the university in the links of the pages and documents (discover.py);
                                # their name/config wait in raw/sites-discovered.json, read but not trusted, until `approve` moves them to raw/sites.yaml

A page's text is kept as the site shows it: html_to_markdown turns the markup into markdown (a page that needs its scripts,
an app's empty shell, is read in the browser first: get_page), the program drops what every page of the site repeats (menus,
footers); no model is asked: the description is the page's first sentence. The documents a site
links (PDF, DOCX: the rules of the dormitories, their prices) go the way of the regulations (regulations.py, which asks
`docs()`): wiki/raw/regulations/, quoted by clause, `source_kind: official-document`. The pages themselves are `website`.
Every week a run reads all pages again and compares their text: these sites say nothing reliable about changes (678 of 4476
pages sent Last-Modified, the sitemaps of media and apply stopped in 2024 and 2025); the new pages are fetch_new's. A page that comes
back with less than half of its own words (SHORT_READ: a stub, an app's empty shell, half a page), answers 404 or is no
longer linked is kept as it was until the next run finds it so too: written over or dropped at once, it would take with it
what the cards citing it say. The sites are read once a week, so a page that really went is gone a week later.
"""

import asyncio
import contextlib
import functools
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from argparse import Namespace
from collections import Counter
from dataclasses import dataclass, fields
from datetime import datetime, timezone
from html import escape, unescape
from http.cookiejar import CookieJar, DefaultCookiePolicy
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, quote, unquote, urldefrag, urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx
import websockets
import yaml
from html_to_markdown import ConversionOptions, NodeContext, PreprocessingOptions, convert
from html_to_markdown.exceptions import ConversionError

from catix.wiki.compile import AUDIENCES, PRODUCER, yaml_value
from catix.wiki.paths import DOCS, RAW
from catix.wiki.sources import regulations
from catix.wiki.sources.rpd import latin

ROOT = RAW / "sites"
FOLDER = "sites"
PAUSE = 2  # seconds between requests
MAX_PAGES = 60  # per site: the crawl follows the links of the site, this stops a calendar or a catalogue from running away
DOC = re.compile(r"\.(pdf|docx?|rtf|zip|7z)$", re.I)
ARCHIVE = re.compile(r"\.(zip|7z)$", re.I)
DOWNLOAD = re.compile(r"/(?:download(?:\.php)?|file)/?$", re.I)
NOT_PAGE = re.compile(r"\.(xml|rss|atom|json|webmanifest|txt|csv|ics|ya?ml|css|m?js|map|woff2?|ttf|otf|eot|jpe?g|png|gif|webp|avif|svg|ico|bmp"
                      r"|tiff?|heic|mp4|webm|mov|m4v|ogv|avi|mkv|mp3|wav|ogg|oga|m4a|flac|aac|xlsx?|pptx?|od[tsp]|rar|t?gz|tar|exe|apk|dmg|iso)$", re.I)
# ^ a file a page links, not a page (a sitemap, a picture, a video, a font): not asked for (a video would be downloaded whole to be
#   dropped), and the browser of Site.render would show it as a page of its own (lyceuminnopolis.ru's sitemap.xml became a page)
ARCHIVE_TYPES = {"application/zip": "zip", "application/x-zip-compressed": "zip", "application/x-7z-compressed": "7z"}
UNIVERSITY = ("innopolis.university", "innopolis.ru", "innopolis.edu.ru", "innopolis.com", "innopolis.college")  # the hosts of the university and of the city
MIN_WORDS = 10  # a page with fewer words (after the shared lines) is a page of pictures and buttons; a heading and a few links to its sections is a page
NEW_PAGES = 50  # new pages a run of new pages (fetch_new) reads on one site besides its start pages: a feed shows tens, a calendar would run away
NEW_DEPTH = 3  # waves of fetch_new: the new pages of other trusted sites that new pages link, and those that these link
SHORT_READ = 0.5  # a page read with less than this share of its own words is kept as it was until the next run reads it as short (fetch_site)


@dataclass(frozen=True)
class Site:
    base: str
    language: str
    about: str
    skip: str  # paths not taken: past events, old copies, forms, the other language
    sitemap: bool | str = True  # a path: its sitemap is not /sitemap.xml (WordPress: 'wp-sitemap.xml')
    max_pages: int = MAX_PAGES
    english: str | None = None  # the path of the English copy of a Russian site: its pages are `language: en`
    dated: bool = False  # a year in the title or the address of a page is the year it is about (events: 'Spring Ball 2022')
    render: bool = False  # the site is an app: every page is read in the browser (a page of another site that needs its scripts is read there too: get_page)
    robots: bool = False  # the pages its robots.txt disallows are not taken (Tilda lists there the pages it does not publish: tests, old webinars)
    pause: float | None = None  # seconds between requests, PAUSE when None (innopolis.com asks for 10: Crawl-delay)
    headings: str | None = None  # the classes of a block that is a heading on a site that writes no <h2> (innopolis.com: <div class="article__title">)
    bare: bool = False  # a link without a language is the page in the language of the page it is on (innopolis.com writes '/media/news/x', '/services')
    listing: str | None = None  # the query that turns the pages of a list (innopolis.com: '?page=2'): they are read for their links, not kept
    end: str | None = None  # where the text of a page ends and the site's blocks of the day it was read begin (media: 'Новости по теме')
    drop: str | None = None  # the lines of a page that lead to the next post, not its text (robotics: 'Дальше', the next post's name)
    profile: str | None = None  # the environment variable that names a Chromium profile a person logged in to: the site is behind a login, its pages are read as that person sees them
    audience: tuple[str, ...] | None = None  # who the pages of the site are for, when it is not everyone (the IT instructions of help are for the staff); a page's own `audience` in the index is stronger
    discover: str | None = None  # a script the logged-in browser runs on the site's start page; it returns the JSON list of the pages' addresses (Wiki.js: the pages its GraphQL lists; the menu is drawn by scripts, no link leads to them)
    missing: str | None = None  # what a page that does not exist looks like, when the site answers it with 200 (Wiki.js: 'Эта страница не существует')
    signin: str | None = None  # what the page of the login looks like in the DOM (the session ended: the portal shows 'Авторизация' in place of the page): the crawl stops, the form is not a page
    private: str | None = None  # what the pages show of the person who is logged in (name, mail, balance, notifications): cut from every page before anything is kept
    feeds: tuple[str, ...] = ()  # the paths where the site shows its new pages (a list of news or events): fetch_new reads them every few hours in place of the start page
    aliases: tuple[str, ...] = ()  # other hosts of the site, an old name or a mirror: a link to one leads to the site's page of the same path, when there is one


CONFIG = RAW / "sites.yaml"
DISCOVERED_SKIP = r"^(tilda|members)/|(^|/)((\w+[-_])?form|thank_?you\w*|test\w*|\w+_test)$"


def load_config(path: Path | None = None) -> tuple[dict[str, dict[str, Any]], frozenset[str]]:
    path = CONFIG if path is None else path
    raw = cast(dict[str, Any], yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    return cast(dict[str, dict[str, Any]], raw.get("sites", raw)), frozenset(raw.get("blocked", ()))


def load_sites(path: Path | None = None) -> dict[str, Site]:
    """Load the trusted site catalog from the wiki data."""
    raw, _ = load_config(path)
    return {name: make_site(values) for name, values in raw.items()}


def make_site(values: dict[str, Any]) -> Site:
    """The same typed settings in the approved YAML and a pending JSON record."""
    names = {field.name for field in fields(Site)}
    tuple_fields = {"audience", "aliases", "feeds"}
    kwargs: dict[str, Any] = {key: tuple(value) if key in tuple_fields and isinstance(value, list) else value
                              for key, value in values.items() if key in names}
    return Site(**kwargs)


def load_blocked(path: Path | None = None) -> frozenset[str]:
    return load_config(path)[1]





SITES: dict[str, Site] = {}
BLOCKED: frozenset[str] = frozenset()
_catalog_version: tuple | None = None


def reload_catalog() -> None:
    """Refresh the approved snapshot when its data file changes, including a git checkout or another process's approval.
    Imports never read or create data. Parsing is cached; readers check the file's identity before each operation."""
    global BLOCKED, _catalog_version
    try:
        stamp = CONFIG.stat()
    except FileNotFoundError:
        raise FileNotFoundError(f"site catalog missing: {CONFIG}; run catix-wiki sites migrate --from PATH_TO_SITES_YAML") from None
    version = (CONFIG, stamp.st_dev, stamp.st_ino, stamp.st_mtime_ns, stamp.st_size)
    if version != _catalog_version:
        raw, blocked = load_config()
        loaded = {name: make_site(values) for name, values in raw.items()}
        SITES.clear()
        SITES.update(loaded)
        BLOCKED, _catalog_version = blocked, version


DISCOVERED = RAW / "sites-discovered.json"  # what discover.py's probes found: {"sites": {host: {"status": "pending" | "failed" | "closed", ...}}}
DISCOVERED_PAGES = 30  # pages a found site may have until a person has read what it gave and raised its limits in the discovery record's config
DISCOVERED_PAUSE = 3


def site_name(host: str) -> str:
    """The name of a found site (its folder in raw/sites/): 'dovuz' for dovuz.innopolis.university, 'innopolis-college' for innopolis.college."""
    return host.removesuffix(".innopolis.university") if host.endswith(".innopolis.university") else host.replace(".", "-")


def discovered() -> dict[str, dict]:
    return json.loads(DISCOVERED.read_text(encoding="utf-8")).get("sites", {}) if DISCOVERED.exists() else {}


def load_discovered() -> int:
    """Compatibility hook: discovered sites never become configuration automatically."""
    return 0


def site_values(site: Site) -> dict[str, Any]:
    return {field.name: list(value) if isinstance(value := getattr(site, field.name), tuple) else value for field in fields(Site)}


def found_site(host: str, entry: dict) -> Site:
    defaults = Site(f"https://{host}/", entry.get("language", "ru"), f"{host}, found by the wiki's run: {entry.get('title') or host}",
                    DISCOVERED_SKIP, max_pages=DISCOVERED_PAGES, robots=True, pause=DISCOVERED_PAUSE,
                    render=bool(entry.get("render")))
    return make_site(site_values(defaults) | entry.get("config", {}))


def discovered_name(host: str, entry: dict) -> str:
    return entry.get("name") or site_name(host)


def pending_sites() -> dict[str, Site]:
    """Readable but not trusted; settings live in the discovery record, never a second pending file."""
    from catix.wiki import autopilot

    reload_catalog()
    rejected = set(autopilot.load_state().get("rejected_sites", []))
    pending: dict[str, Site] = {}
    for host, entry in discovered().items():
        if entry.get("status") != "pending" or host in rejected:
            continue
        name = discovered_name(host, entry)
        if name in SITES:
            approved = SITES[name]
            own = (urlsplit(approved.base).hostname or "").lower().rstrip(".").removeprefix("www.")
            if host != own and host not in approved.aliases:
                raise ValueError(f"site name {name} belongs to another approved host")
            continue
        if name in pending:
            raise ValueError(f"multiple pending hosts use site name {name}")
        pending[name] = found_site(host, entry)
    return pending


def every_site() -> dict[str, Site]:
    return {**pending_sites(), **SITES}


_UMASK = os.umask(0o022)
os.umask(_UMASK)  # (read once, at import: os.umask sets it as it tells it)


def atomic_write(path: Path, text: str) -> None:
    """Readers see a complete file; an unchanged write leaves its timestamp alone. The file is readable as one open() makes
    (0666 less the umask): NamedTemporaryFile makes it 0600, and the catalogue in the checkout of the wiki was then closed to
    the containers that mount it (their user is not the checkout's owner)."""
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False) as out:
        temporary = Path(out.name)
        try:
            out.write(text)
            out.flush()
            os.fsync(out.fileno())
            os.chmod(temporary, 0o666 & ~_UMASK)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def write_discovered(found: dict) -> None:
    atomic_write(DISCOVERED, json.dumps({"sites": found}, ensure_ascii=False, indent=1, sort_keys=True))


def approve_discovered(host: str, entry: dict) -> str:
    """Move settings into the wiki's approved catalog; the caller removes the discovery record afterwards."""
    reload_catalog()
    name = discovered_name(host, entry)
    if name not in SITES:
        values = site_values(found_site(host, entry)) | entry.get("config", {})
        text = CONFIG.read_text(encoding="utf-8")
        tops = [line for line in text.splitlines() if re.match(r"[^\s#]", line)]
        if tops and tops[-1] == "sites:":
            # Append beneath the final top-level key, preserving comments and hand-written settings.
            block = yaml.safe_dump({name: values}, allow_unicode=True, sort_keys=False, width=137)
            atomic_write(CONFIG, text.rstrip("\n") + "\n" + "".join(f"  {line}\n" for line in block.splitlines()))
        else:
            raw = yaml.safe_load(text) or {}
            if "sites" not in raw:
                raw = {"sites": raw}
            raw["sites"][name] = values
            atomic_write(CONFIG, yaml.safe_dump(raw, allow_unicode=True, sort_keys=False, width=139))
        reload_catalog()
    return name


def migrate_catalog(source: Path | None = None) -> None:
    """Explicit, repeatable migration; an existing data catalog wins over the old code copy.
    Pending YAML overrides move into JSON, and its original is retained as .yaml.bak. No crawl or approval is performed;
    only records already marked accepted are moved to the approved catalog."""
    origin = CONFIG if CONFIG.exists() else source
    if origin is None:
        raise FileNotFoundError(f"site catalog missing: {CONFIG}; provide sites migrate --from PATH_TO_SITES_YAML")
    load_sites(origin)  # validate everything before writing any migration output
    text = origin.read_text(encoding="utf-8")
    raw = yaml.safe_load(text) or {}
    if "sites" not in raw:
        raw = {"sites": raw}
    approved = raw["sites"]
    found = discovered()
    pending_file = DISCOVERED.with_name("sites-pending.yaml")
    backup = pending_file.with_suffix(".yaml.bak")
    if pending_file.exists():
        if backup.exists() and backup.read_bytes() != pending_file.read_bytes():
            raise ValueError(f"migration backup already exists with different contents: {backup}")
        for name, values in load_config(pending_file)[0].items():
            site = make_site(values)
            host = (urlsplit(site.base).hostname or "").lower().rstrip(".").removeprefix("www.")
            entry = found.get(host, {})
            if entry.get("status", "pending") not in ("pending", "accepted"):
                raise ValueError(f"pending YAML conflicts with {entry['status']} record for {host}")
            found[host] = {**entry, "status": entry.get("status", "pending"), "name": name, "config": values}
    approved_hosts = {(urlsplit(values["base"]).hostname or "").lower().rstrip(".").removeprefix("www."): name
                      for name, values in approved.items()}
    changed_catalog = False
    for host, entry in list(found.items()):
        if entry.get("status") not in ("pending", "accepted"):
            continue
        if host in approved_hosts:
            del found[host]
            continue
        name = discovered_name(host, entry)
        if name in approved:
            raise ValueError(f"site name {name} belongs to another approved host")
        values = site_values(found_site(host, entry)) | entry.get("config", {})
        if entry["status"] == "accepted":
            approved[name] = values
            approved_hosts[host] = name
            changed_catalog = True
            del found[host]
        else:
            found[host] = {**entry, "name": name, "config": values}
    atomic_write(CONFIG, yaml.safe_dump(raw, allow_unicode=True, sort_keys=False, width=139) if changed_catalog else text)
    if found or DISCOVERED.exists() or pending_file.exists():
        write_discovered(found)
    if pending_file.exists():
        pending_file.replace(backup)
    reload_catalog()


CHROMIUM = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
RENDER_WAIT = 15  # seconds: the longest the browser gives a page's scripts to fill it
RENDER_IDLE = 5  # seconds of it the browser waits for the page's requests to end (an app asks for its data after it loaded; Tilda's counters never end)
RENDER_STILL = 1.5  # seconds the text of the page stays the same: the scripts have filled it


class NotAPage(httpx.TransportError):
    """The browser was given a file, not a page (a feed, a video): it shows any answer as a page of its own."""

    def __init__(self, url: str, kind: str):
        super().__init__(f"{url} is {kind}, not a page")
        self.kind = kind


def render_page(url: str) -> str:
    """The page as the browser shows it after its scripts ran (headless Chromium through Playwright): for a page whose HTML is
    an empty shell ('You need to enable JavaScript to run this app'). The page is taken once its requests ended and its text
    stopped changing (when its HTML is read, lyceuminnopolis.ru shows 68 of its 502 words; the 'load' of a page of Tilda may not
    come in 30 seconds, its text is there in 3). The browser of the system when there is one, else Playwright's own. Raises
    httpx.TransportError, as a site that does not answer, when the browser cannot start or read the page, and when the page's
    scripts took it to another host (Tilda's redirect block, a login of SSO): the page there is not this one, and this one is
    not gone either (the link of a redirect block is in the page's <noscript>, which the crawl follows). Raises NotAPage when
    the answer is not HTML (an address with no extension that gives a feed or a file): the browser would show it as a page."""
    from playwright.sync_api import Error, sync_playwright

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=CHROMIUM, headless=True, args=["--no-sandbox"])
            try:
                page = browser.new_page()
                answer = page.goto(url, wait_until="domcontentloaded", timeout=2 * RENDER_WAIT * 1000)
                kind = (answer.headers.get("content-type", "") if answer else "").split(";", 1)[0].strip().lower()
                if kind and "html" not in kind:
                    raise NotAPage(url, kind)
                end = time.monotonic() + RENDER_WAIT
                try:
                    page.wait_for_load_state("networkidle", timeout=RENDER_IDLE * 1000)
                except Error:
                    pass  # (a page that never stops asking: its text says when it is done)
                last, since = None, time.monotonic()
                while time.monotonic() < end:
                    text = page.evaluate("document.body ? document.body.innerText : ''")
                    if text != last:
                        last, since = text, time.monotonic()
                    elif text.strip() and time.monotonic() - since >= RENDER_STILL:
                        break  # (an empty page is not done: an app shows nothing until its data comes)
                    page.wait_for_timeout(250)
                if (urlsplit(page.url).hostname or "").removeprefix("www.") != (urlsplit(url).hostname or "").removeprefix("www."):
                    raise httpx.TransportError(f"its scripts lead to {page.url}")
                return page.content()
            finally:
                browser.close()
    except Error as e:
        raise httpx.TransportError(f"the browser did not read {url}: {str(e).splitlines()[0]}") from e


WALL = re.compile(r"""(?i)вы не робот|just a moment|attention required|checking your browser|проверка браузера|smart-?captcha|captcha_smart|cf-chl|ddos-guard""")
WALL_TITLE = re.compile(r"""(?i)вы не робот|just a moment|attention required|checking your browser|проверка браузера""")
BOT_TRIES = 8  # a bot check comes and goes (timepad behind Yandex answered seven requests of a burst, then let one through)
BOT_PAUSE = 5  # seconds between the asks


def get_through(client: httpx.Client, url: str) -> httpx.Response:
    """The answer for the url, asked again while a bot check answers in its place ('Вы не робот?' of Yandex on timepad, 'Just a
    moment' of Cloudflare): the wall is not the site, and it lets a request through now and then. The last answer is kept
    whatever it is, so a page that names a bot check in its own words is only asked for again, never refused for them."""
    page = client.get(url)
    for _ in range(BOT_TRIES - 1):
        if not WALL.search(page.text):
            break
        time.sleep(BOT_PAUSE)
        page = client.get(url)
    return page


LIVE_WAIT = 30  # seconds: the longest a page of an app behind a login is given to finish loading
LOGIN_FORM = re.compile(r"""<input[^>]+type=["']?password""", re.I)


class LiveBrowser:
    """One Chromium with the profile of a person who logged in, kept for the whole crawl: a portal that gives a session a few minutes
    lives longer in one browser than in a new one for every page (the pages are opened in one tab, one after another)."""

    def __init__(self, profile: str):
        if not CHROMIUM:
            raise RuntimeError("a site with a profile needs Chromium (chromium, chromium-browser or google-chrome on the PATH)")
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        self.profile = profile
        self.process = subprocess.Popen([CHROMIUM, "--headless=new", "--disable-gpu", "--no-sandbox", f"--user-data-dir={profile}", f"--remote-debugging-port={port}", "about:blank"],
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.loop = asyncio.new_event_loop()
        try:
            for _ in range(100):
                try:
                    tab = next(t for t in httpx.get(f"http://127.0.0.1:{port}/json").json() if t["type"] == "page")
                    break
                except (httpx.HTTPError, StopIteration):
                    time.sleep(0.2)
            else:
                raise httpx.TransportError("the browser did not start")
            self.ws = self.loop.run_until_complete(websockets.connect(tab["webSocketDebuggerUrl"], max_size=None))
        except BaseException:
            self.close()
            raise
        self.ids = iter(range(1, 10**9))

    async def call(self, method: str, **params) -> dict:
        n = next(self.ids)
        await self.ws.send(json.dumps({"id": n, "method": method, "params": params}))
        while (answer := json.loads(await self.ws.recv())).get("id") != n:
            pass
        return answer

    async def load(self, url: str) -> str:
        await self.call("Page.navigate", url=url)
        last, still = "", 0
        for second in range(LIVE_WAIT):
            await asyncio.sleep(1)
            html = (await self.call("Runtime.evaluate", expression="document.documentElement.outerHTML", returnByValue=True))["result"]["result"]["value"]
            still = still + 1 if html == last else 0
            last = html
            if still >= 3 and second >= 4:  # (unchanged for three seconds, and not the empty shell of the first ones)
                break
        return last

    def evaluate(self, script: str) -> str:
        """What a script returns in the page that is open (a promise is waited for)."""
        answer = self.loop.run_until_complete(self.call("Runtime.evaluate", expression=script, awaitPromise=True, returnByValue=True))
        return answer["result"]["result"]["value"]

    def get(self, url: str) -> str:
        """The page after it stopped changing. Raises when the page asks for a password or did not finish loading (its title is still '{eventName}')."""
        html = self.loop.run_until_complete(self.load(url))
        if re.search(r"<title>[^<]*\{\w+\}", html):  # (the page asked for its data and had no answer yet: once more)
            html = self.loop.run_until_complete(self.load(url))
        if LOGIN_FORM.search(html):
            raise RuntimeError(f"the profile {self.profile} is not logged in: {url} asks for a password")
        if re.search(r"<title>[^<]*\{\w+\}", html):
            raise httpx.TransportError(f"{url} did not finish loading")
        return html

    def close(self) -> None:
        if hasattr(self, "ws"):
            self.loop.run_until_complete(self.ws.close())
        self.process.terminate()
        self.process.wait()
        self.loop.close()


LIVE: dict[str, LiveBrowser] = {}  # profile -> its browser, open during a crawl


def render_live(url: str, profile: str) -> str:
    """The page as the person logged in to the profile sees it (the browser is opened on the first page and kept: close_live)."""
    if profile not in LIVE:
        LIVE[profile] = LiveBrowser(profile)
    return LIVE[profile].get(url)


def profile_of(site: Site) -> str:
    if not (profile := os.environ.get(site.profile or "")):
        raise RuntimeError(f"a site with a login needs {site.profile}: the Chromium profile a person logged in to")
    return os.path.expanduser(profile)


def close_live() -> None:
    while LIVE:
        LIVE.popitem()[1].close()


def service_catalog(js: str) -> list[dict]:
    """The services InNoHassle's dashboard lists, from the objects in its script ({url, resource, title, description, category, ...}):
    the page shows six of them and a 'Show all' button, the script holds them all, in two languages."""
    out = []
    for m in re.finditer(r"\{url:`([^`]*)`.*?category:`([^`]*)`", js, flags=re.S):
        chunk = m.group(0)
        field = lambda key: (lambda f: f.group(1) if f and f.group(1) is not None else "")(re.search(rf"\b{key}:(?:`([^`]*)`|null)", chunk))
        out.append({"url": m.group(1), "category": m.group(2), "name": field("resource"), "name_ru": field("resourceRu"), "title": field("title"),
                    "title_ru": field("titleRu"), "text": field("description"), "text_ru": field("descriptionRu")})
    return out


def catalog_markdown(services: list[dict]) -> str:
    """The catalog as the page's lines: a heading per category, a line per service with its words in both languages."""
    lines = []
    for category in dict.fromkeys(sv["category"] for sv in services):
        lines += [f"### {category}", ""]
        for sv in (sv for sv in services if sv["category"] == category):
            name = sv["name"] + (f": {sv['title']}" if sv["title"] else "")
            name_ru = sv["name_ru"] + (f": {sv['title_ru']}" if sv["title_ru"] else "")
            lines.append(f"- [{name}]({md_url(sv['url'])})" + (f" ({name_ru})" if name_ru and name_ru != name else "") + f": {sv['text']}"
                         + (f" / {sv['text_ru']}" if sv["text_ru"] else ""))
        lines.append("")
    return "\n".join(lines).strip()


def dashboard_with_catalog(client: httpx.Client, html: str, url: str, text: str) -> str:
    """The text of InNoHassle's dashboard with the whole catalog of services in place of the six the page shows."""
    src = re.search(r'<script[^>]+type="module"[^>]+src="([^"]+)"', html)
    if not src:
        return text
    try:
        services = service_catalog(client.get(urljoin(url, src.group(1))).text)
    except httpx.HTTPError:
        return text
    return text.split("## Filter")[0] + catalog_markdown(services) + "\n" if services else text


EXTRAS = {("innohassle", "dashboard"): dashboard_with_catalog}  # (site, page) -> what the page needs besides what the browser shows


def needs_script(page: httpx.Response, headings: str | None = None) -> bool:
    """Whether the browser is to read a page the site sent: its <noscript> asks for JavaScript, or it has next to no words (the
    empty shell of an app, a page of Tilda whose blocks its scripts draw). Not a bot check: the browser does not pass it either."""
    return (page.status_code == 200 and "text/html" in page.headers.get("content-type", "") and not WALL.search(page.text)
            and convert_page(page.text, str(page.url), headings)[3])


def get_page(client: httpx.Client, site: "Site", url: str) -> httpx.Response:
    """The answer for a page: the site's own, or what the browser made of it, as if it were the answer: for every page of an app
    (Site.render), for a page that needs its scripts (needs_script) on any other site."""
    if site.profile:
        profile = profile_of(site)
        html = render_live(url, profile)
        if site.signin and re.search(site.signin, html):
            raise RuntimeError(f"the session of the profile {profile} has ended: {url} shows the login")
        return httpx.Response(404 if site.missing and re.search(site.missing, html) else 200, headers={"content-type": "text/html; charset=utf-8"}, text=html, request=httpx.Request("GET", url))
    headers = {"content-type": "text/html; charset=utf-8"}
    if not site.render:
        page = get_through(client, url)
        if not needs_script(page, site.headings):
            return page
        url = str(page.url)
        try:
            html = render_page(url)
        except httpx.TransportError as e:
            print(f"  {url}: needs its scripts, and {e}: read as the site sent it", flush=True)
            return page
        if not html:
            return page
        print(f"  {url}: needs its scripts, read in the browser", flush=True)
        if "last-modified" in page.headers:
            headers["last-modified"] = page.headers["last-modified"]
    else:
        try:
            html = render_page(url)
        except NotAPage as e:  # (the site's file as the site sent it: fetch_site leaves what is not a page)
            return httpx.Response(200, headers={"content-type": e.kind}, request=httpx.Request("GET", url))
    return httpx.Response(200 if html else 404, headers=headers, text=html or "", request=httpx.Request("GET", url))


def keep_by_hand(name: str, slug: str, old: dict) -> bool:
    """Whether the file of a page was edited after the crawl wrote it (a page behind a login, which a person put in by hand): its
    hash is no longer the one the crawl noted. A page marked `manual` in the index stays so; the crawl does not write over it."""
    path = ROOT / name / f"{slug}.md"
    if not path.exists() or not old:
        return False
    return bool(old.get("manual")) or bool(old.get("file_sha")) and hashlib.sha256(path.read_bytes()).hexdigest() != old["file_sha"]


def missed(pages: dict, slug: str, why: str, run: str) -> int:
    """A page the run did not find (a 404, no link to it): gone once a second run finds it so, kept until then (a site down
    for an hour, a menu its scripts did not draw). 1 when it is gone now."""
    page = pages[slug]
    if (mark := page.get("missing")) and mark["run"] != run:
        pages[slug] = {key: value for key, value in page.items() if key not in ("missing", "short")} | {"gone": True}
        return 1
    if not mark:
        pages[slug] = {**page, "missing": {"why": why, "run": run}}
        print(f"  {slug}: {why}, kept until the next run finds it so", flush=True)
    return 0


def put_cache(name: str, slug: str, text: str) -> str:
    """The text of a page into the cache; the hash of the file as written (to tell later whether a person changed it)."""
    path = ROOT / name / f"{slug}.md"
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(url: str) -> str:
    """One spelling of a link: the site writes the same file with spaces, Cyrillic or %-escapes."""
    parts = urlsplit(url)
    query = f"?{parts.query}" if parts.query and (ARCHIVE.search(parts.path) or DOWNLOAD.search(parts.path)) else ""
    return f"https://{parts.netloc}{quote(unquote(parts.path), safe='/')}{query}"


def slug_of(site: Site, url: str) -> str:
    path = unquote(urlsplit(url).path).strip("/")
    return re.sub(r"[^a-z0-9]+", "-", path.lower()).strip("-")[:60] or "home"


IMAGE_SKIP = re.compile(r"icon|sprite|pixel|spacer|blank|favicon|tracking|counter|emoji|arrow|\.(svg|ico)(\?|$)", re.I)  # (not 'logo': a partner's logo is content, the site's own is in every page, so in the shared blocks)
TRACKER = re.compile(r"img\.youtube\.com|mc\.yandex|counter\.|google-analytics|doubleclick|facebook\.com/tr|top-fwz|vk\.com/rtrg", re.I)
MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)\s]*\)")
MD_LINK = re.compile(r"\[([^\]]*)\]\([^)\s]*\)")
VIDEO_FILE = re.compile(r"\.(mp4|webm|mov|m4v|ogv)(\?|$)", re.I)


def md_url(url: str) -> str:
    """A link target that survives markdown: no spaces, no brackets."""
    return re.sub(r"\s", lambda m: quote(m.group()), url).replace("(", "%28").replace(")", "%29")  # (a no-break space in an address too)


def video_url(src: str) -> str | None:
    """The page where a video of an embed can be watched (YouTube, Rutube, VK, Vimeo), a video file as it is; None for
    any other frame (a map, a form, a widget)."""
    parts = urlsplit(src)
    host, path, query = parts.netloc.lower().removeprefix("www."), parts.path, parse_qs(parts.query)
    if host.endswith(("youtube.com", "youtube-nocookie.com")) and path.startswith("/embed/"):
        return f"https://www.youtube.com/watch?v={path.split('/')[2]}"
    if host == "rutube.ru" and path.startswith("/play/embed/"):
        return f"https://rutube.ru/video/{path.split('/')[3]}/"
    if host in {"vk.com", "vkvideo.ru"} and "video_ext" in path and "oid" in query and "id" in query:
        return f"https://vk.com/video{query['oid'][0]}_{query['id'][0]}"
    if host == "player.vimeo.com" and path.startswith("/video/"):
        return f"https://vimeo.com/{path.split('/')[2]}"
    if host == "youtu.be" and path.strip("/"):
        return f"https://www.youtube.com/watch?v={path.strip('/')}"
    if host.endswith("youtube.com") and path == "/watch" and "v" in query:
        return f"https://www.youtube.com/watch?v={query['v'][0]}"
    return src if VIDEO_FILE.search(path) else None


def plain(text: str) -> str:
    """A page's words without its links and pictures: what its hash is made of, so that a new link does not make a new version."""
    lines = [MD_LINK.sub(lambda m: "" if m.group(1).startswith("▶") else m.group(1), MD_IMAGE.sub("", line)) for line in text.splitlines()]  # (a video is no words)
    lines = [line.strip() if line.startswith("|") else re.sub(r" {2,}", " ", line).strip() for line in lines]  # (a table row keeps its empty cells)
    return "\n".join(line for line in lines if line and not re.fullmatch(r"(#+|-|\|)", line))


LAZY_SOURCES = ("data-original", "data-src", "data-lazy-src")  # where a lazy picture keeps its file (Tilda: a 20-pixel preview in src, the picture in data-original)
SMALL = 64  # pixels: a picture this wide or high is an icon, a pixel of a counter
VIDEO_SOURCES = ("data-source", "data-src", "data-video-src")  # where a block keeps the video it plays (Bitrix: a div with data-source)
BANNER = re.compile(r"background-image:\s*(?:-webkit-)?(?:image-set\()?\s*url\(\s*['\"]?([^'\")]+)")  # (a banner: the first address, not the 2x copies)
TILDA_PREVIEW = re.compile(r"^(https://)thb(\.tildacdn\.com/tild[\w-]+)/-/[^/]+/[^/]+/(.+)$")  # (a preview with no original beside it: the file itself)
_W = "\t\n\f\r "  # (the spaces of HTML: a no-break space is a letter of a name)
_NAME = rf"[^{_W}/>=][^{_W}/>=]*+"  # (as a browser reads a tag: a quote in a name is a letter of it)
_VALUE = rf"""[{_W}]*+=[{_W}]*+(?:"[^"]*+"|'[^']*+'|[^{_W}>]++)"""
ATTRIBUTE = re.compile(rf"""({_NAME})(?:[{_W}]*+=[{_W}]*+(?:"([^"]*+)"|'([^']*+)'|([^{_W}>]++)))?""")
TAG = re.compile(  # (what is inside a script, a style, a comment is not tags)
    rf"<!--.*?-->|<(script|style|textarea|title)\b[^>]*>.*?</\1[{_W}]*>"
    rf"|<(?P<end>/?)(?P<name>[a-zA-Z][^{_W}/>]*+)(?P<attrs>(?:[{_W}/]++|{_NAME}(?:{_VALUE})?|=[^{_W}/>=]*+)*+)>",
    re.S | re.I)
HEADINGS = ["h1", "h2", "h3", "h4", "h5", "h6"]
BLOCKS = ["p", "div", "section", "article", "ul", "ol", "li", "table", "blockquote", "dl", "figure", *HEADINGS]
SCRIPT_HREF = re.compile(r"(?i)javascript:")
FRONT = re.compile(r"\A---\n.*?\n---\n", re.S)  # (the converter writes the <head> it read as front matter: the title is taken from its metadata)
UNLISTED = re.compile(r"^ *(?:-|\d+\.) ")  # (the mark of an item of a list)
UNWRITTEN = {"noscript", "template", "form"}  # not the page's text, their links are the crawl's: what a reader does not see (a <noscript>
# is read for what it says of scripts), a form (its fields, its consent, its button; not a <button> elsewhere: a question of a FAQ)
CONTINUE, SKIP = {"type": "continue"}, {"type": "skip"}


def readable(url: str) -> str:
    """An address with the letters the site wrote in it, not their %-codes (the converter writes 'Правила' as '%D0%9F%D1%80…', six
    times as long for the reader); a space and a bracket stay coded, as md_url codes them."""
    def letters(m: re.Match) -> str:
        try:
            return bytes.fromhex(m.group().replace("%", "")).decode("utf-8")
        except UnicodeDecodeError:  # (not UTF-8: a site in cp1251)
            return m.group()
    return md_url(re.sub(r"(?:%[89a-fA-F][0-9a-fA-F])+", letters, url))


def _custom(output: str) -> dict:
    return {"type": "custom", "output": output}


def _attributes(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for name, quoted, single, bare in ATTRIBUTE.findall(text):
        found.setdefault(name.lower(), unescape(quoted or single or bare))  # (the first of two of a name, as a browser takes)
    return found


def _tag(name: str, attributes: dict[str, str]) -> str:
    return f"<{name}" + "".join(f' {k}="{escape(v)}"' for k, v in attributes.items()) + ">"


def _watch(src: str | None, title: str = "") -> str:
    """A link to where a video is watched, `▶ title`: plain() knows it is no words."""
    return f'<a href="{escape(src)}">▶ {escape(re.sub(r"[\[\]]", "", title).strip() or "video")}</a>' if src else ""


def _prepared(html: str, url: str, headings: str | None) -> str:
    """The page with what the converter cannot see written as tags it reads. Its visitor (_Page) is given no attributes of
    the elements (NodeContext.attributes() is empty in html-to-markdown 3.19, DocumentNode.attributes too; those of an <img>
    and an <a> come only in the metadata of the result, after the visitor ran), so what lives in them is moved here, tag by tag
    (no tree: each step reads one opening tag and writes beside it). The file of a lazy picture whose src is a preview
    (data-original, data-src; the converter takes data-src or a srcset itself only for a missing or a data: src) into its src,
    a picture of 64 pixels or less out; a banner of a style and the picture of a Tilda block (data-original of a div) as an
    <img>; a video (a frame, a <video> whose file is in data-src, the video block of Tilda or Bitrix) as a link to where it is
    watched, with its title; a block the site names a heading (Site.headings, a class) as an <h2>. A frame that is not a video
    (a map, a form) is gone. All the rest is _Page's."""
    out: list[str] = []
    pos = 0
    renamed: list[list] = []  # [tag, depth] of a block made an <h2>: its own closing tag closes the <h2>
    while m := TAG.search(html, pos):
        out.append(html[pos:m.start()])
        pos = m.end()
        name = (m.group("name") or "").lower()
        if not name:  # (a comment, a script, a style: as they are)
            out.append(m.group())
            continue
        if m.group("end"):
            for block in (b for b in renamed if b[0] == name):
                block[1] -= 1
            out.append("</h2>" if renamed and renamed[-1][1] == 0 and renamed.pop() else m.group())
            continue
        a = _attributes(m.group("attrs"))
        if name == "img":
            if any(a.get(k, "").isdigit() and int(a[k]) <= SMALL for k in ("width", "height")):
                continue  # (a pixel, an icon: the converter knows the size only in its metadata, after the visitor ran)
            if src := next(filter(None, (a.get(k, "").strip() for k in LAZY_SOURCES)), ""):
                out.append(_tag("img", {**a, "src": src}))
            else:
                out.append(m.group())
            continue
        if name in {"iframe", "video"}:  # (the whole element: a frame's words are for a browser that has none)
            close = re.compile(rf"</{name}\s*>", re.I).search(html, pos)
            inner, pos = (html[pos:close.start()], close.end()) if close else ("", pos)
            if name == "iframe":
                out.append(_watch(video_url(urljoin(url, (a.get("src") or a.get("data-src") or "").strip())), a.get("title", "")))
            else:
                parts = [a, *(_attributes(t.group("attrs")) for t in TAG.finditer(inner) if (t.group("name") or "").lower() == "source")]
                source = next(filter(None, (part.get(k, "").strip() for part in parts for k in ("src", "data-src"))), "")  # (a lazy one: data-src)
                out.append(_watch(urljoin(url, source) if source else None, a.get("title", "")))
            continue
        for block in (b for b in renamed if b[0] == name):
            block[1] += 1
        if headings and re.search(headings, a.get("class", "")):
            renamed.append([name, 1])
            out.append("<h2>")
        else:
            out.append(m.group())
        if a.get("data-videolazy-id") and a.get("data-videolazy-type") in {"youtube", "vimeo"}:  # (Tilda's video block)
            vid = a["data-videolazy-id"]
            out.append(_watch(f"https://www.youtube.com/watch?v={vid}" if a["data-videolazy-type"] == "youtube" else f"https://vimeo.com/{vid}"))
        else:
            out.append(_watch(next(filter(None, (video_url(urljoin(url, a[k].strip())) for k in VIDEO_SOURCES if a.get(k))), None)))
        banner = a.get("data-original") or (found.group(1) if (found := BANNER.search(a.get("style", ""))) else "")
        if banner.strip():  # (Tilda: the 20-pixel preview in the style, the picture in data-original)
            out.append(_tag("img", {"src": banner.strip()}))
    out.append(html[pos:])
    return "".join(out)


@dataclass
class _Link:
    """What _Page learns of an open <a> while the converter goes through what is inside it."""
    words: str = ""  # its text as the page has it, with the spaces at its ends (the converter hands visit_link the text without them)
    picture: bool = False  # a picture that is content
    block: bool = False  # a block inside: a card, a line of its own
    heading: tuple[int, str] | None = None  # (level, words) of a heading inside


class _Page:
    """What html_to_markdown is told besides its options, element by element, and what it learns of the page: its links (the
    crawl follows them) and whether a <noscript> asks for JavaScript (the page is its scripts: get_page has the browser read it).
    The links stay in the text where the page has them, `[text](url)`, the pictures too, `![alt](url)` (not the decorations:
    icons, pixels, counters); a heading of the page is `## ` (h1-h3) or `### `: the wiki's page is the `# `. A link is read with
    what is inside it (`open`): one with no words and no picture (an icon, a burger) is none, where the converter would write
    its address for its words; a link around a heading is the heading's words, the heading stays one; a card (blocks in a link)
    is a line of its own, not one with the next cards."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.links: list[tuple[str, str]] = []  # (url, text), those of a <noscript> and a form too (Tilda's redirect block: 'Redirect to
        # URL'; the policy a consent links)
        self.script = False
        self.open: list[_Link] = []  # the <a> the converter is inside

    def visit_element_start(self, ctx: NodeContext) -> dict:
        if ctx.tag_name == "a":
            self.open.append(_Link())
        elif self.open and ctx.tag_name in BLOCKS:
            self.open[-1].block = True
        return CONTINUE

    def visit_element_end(self, ctx: NodeContext, output: str) -> dict:
        if ctx.tag_name == "a" and self.open:
            self.open.pop()
        if ctx.tag_name not in UNWRITTEN:
            return CONTINUE
        if ctx.tag_name == "noscript" and "javascript" in output.lower():
            self.script = True  # ('You need to enable JavaScript to run this app.', 'У вас отключено исполнение JavaScript')
        return _custom("")

    def visit_text(self, ctx: NodeContext, text: str) -> dict:
        if self.open:
            self.open[-1].words += text
        return CONTINUE

    def visit_link(self, ctx: NodeContext, href: str, text: str, title: str | None = None) -> dict:
        href = urljoin(self.url, href.strip())  # (the converter resolves `href=" /a "`, not `href=" https://… "`: the browser does both)
        link = self.open[-1] if self.open else _Link(words=text, picture=True)
        words = re.sub(r"\s+", " ", re.sub(r"</?[a-z][^>]*>", " ", text, flags=re.I)).strip()  # (a site that writes <p> as text: not in a link)
        if SCRIPT_HREF.search(re.sub(r"[\s*]", "", unquote(href))):  # (a script, not a link; media writes it 'jav * ascript:void(0)')
            return _custom(words)
        self.links.append((href, re.sub(r"\s+", " ", re.sub(r"\*\*|__", "", MD_IMAGE.sub("", words))).strip()))
        if not link.words.strip() and not link.picture:
            return _custom("")  # (an icon, a burger, an svg: the converter's words for it are its address)
        if urlsplit(href).scheme not in {"http", "https"} or urldefrag(unquote(href))[0] == urldefrag(unquote(self.url))[0]:
            out = words  # (a fragment of the page, a mailto: are words)
        elif link.heading and link.heading[1] in words:
            level, head = link.heading
            rest = words.replace(head, "", 1).strip()
            out = f"\n\n{'#' * level} [{head.replace('[', '(').replace(']', ')')}]({readable(href)})\n\n{rest}"
        else:
            out = f"[{words if '![' in words else words.replace('[', '(').replace(']', ')')}]({readable(href)})"
        if link.block:
            out = f"\n\n{out}\n\n"
        return _custom((" " if link.words[:1].isspace() else "") + out + (" " if link.words[-1:].isspace() else ""))

    def visit_image(self, ctx: NodeContext, src: str, alt: str, title: str | None = None) -> dict:
        alt = re.sub(r"[\[\]]", "", re.sub(r"\s+", " ", alt or title or "")).strip()
        if src.startswith("data:"):
            if self.open and alt:
                self.open[-1].picture = True  # (its alt, the words of the link: inline_data_media)
            return CONTINUE
        url = TILDA_PREVIEW.sub(r"\1static\2/\3", src.strip())  # (Tilda: the file, not its 20-pixel preview)
        parts = urlsplit(url)
        if (parts.scheme not in {"http", "https"} or IMAGE_SKIP.search(parts.path) or TRACKER.search(url)
                or urldefrag(url)[0] == urldefrag(self.url)[0]):  # (a decoration; no address: a script fills it in later)
            return _custom("")
        if self.open:
            self.open[-1].picture = True
        return _custom(f" ![{alt}]({readable(url)}) ")

    def visit_heading(self, ctx: NodeContext, level: int, text: str, id: str | None = None) -> dict:
        words = re.sub(r"\s+", " ", text).strip()
        mark = "##" if level <= 3 else "###"
        if self.open:  # (inside a link: visit_link writes it, the converter would write '[## words](…)')
            if words and not self.open[-1].heading:
                self.open[-1].heading = (len(mark), words)
            return CONTINUE
        return _custom(f"\n\n{mark} {words}\n\n") if words else SKIP  # (a block: the converter writes a custom one as it is, the words after it would join it)


def _options(url: str) -> ConversionOptions:
    return ConversionOptions(
        base_url=url,  # (every link and picture with its whole address)
        extract_images=False,
        inline_data_media="alt_text_only",
        hidden_content="all",  # (the text of a closed tab or a menu is the page's; the <noscript> is read by _Page, not written)
        preprocessing=PreprocessingOptions(enabled=False),  # (the menu stays: the crawl follows its links, boilerplate() keeps it once)
        exclude_selectors=["select", "svg"],  # (the options of a list: a language, a city; an icon drawn)
        bullets="-",
        compact_tables=True,
        autolinks=False,
    )


@functools.lru_cache(maxsize=2)  # (get_page reads a page to tell whether it needs its scripts, fetch_site reads it again)
def convert_page(html: str, url: str, headings: str | None = None) -> tuple[str, str, tuple[tuple[str, str], ...], bool]:
    """(title, markdown lines, links, whether it needs its scripts) of a page; `headings`: Site.headings. A page needs its scripts
    when its <noscript> asks for JavaScript or it has fewer than MIN_WORDS words: the HTML is an empty shell."""
    page = _Page(url)
    try:
        result = convert(_prepared(html, url, headings), _options(url), visitor=page)
    except ConversionError as e:
        print(f"  {url}: not read as HTML ({e})", flush=True)
        return url, "", (), False
    lines, item, base = [], 0, None
    for raw in FRONT.sub("", result.content or "", count=1).splitlines():
        line = re.sub(r"\s+", " ", raw).strip()
        if not line or re.fullmatch(r"(#+|-|\||([-*_] ?){3,})", line):
            continue  # (an empty heading or item, a rule)
        if listed := re.match(r"( *)((?:- )*)(-|\d+\.) (.*)", raw):  # an item of a list in an item keeps its place, counted from the first item
            pad, outer, mark, rest = listed.groups()
            if outer and mark != "-":  # ('- 2. Правила': the item's own words)
                outer, mark, rest = outer[:-2], "-", f"{mark} {rest}"
            column = len(pad) + len(outer)  # (an item that opens with a list, '- - x': the inner item is the line)
            base = column if base is None else min(base, column)  # (whose own item was empty: no code block of 4 spaces)
            line = " " * (column - base) + f"{mark} " + re.sub(r"\s+", " ", rest).strip()
        else:
            base = None
        if lines and re.fullmatch(r"\d{1,2}", lines[-1]) and int(lines[-1]) in (1, item + 1):  # (not a counter: '110 places', '50 places')
            item = int(lines[-1])
            hashes, words = re.match(r"(#+ )?(.*)", line).groups()  # (a step whose words are a heading: '### **1.** Submit an application')
            lines[-1] = f"{hashes or ''}**{lines[-1]}.** {words}"  # a numbered item whose number sits in a block of its own: 'item 2' can be quoted
            continue
        lines.append(line)
        for k in range(1, 9):  # Tilda repeats a block (of up to a few lines) for phones: the second copy goes
            if len(lines) >= 2 * k and [UNLISTED.sub("", x) for x in lines[-k:]] == [UNLISTED.sub("", x) for x in lines[-2 * k:-k]]:
                del lines[-k:]  # (the first copy may open an item of a list: '- ![](a.jpg)', then '![](a.jpg)')
                break
    text = "\n".join(lines)
    meta = result.metadata.document
    title = re.sub(r"\s+", " ", meta.title if meta and meta.title else "").strip() or next((re.sub(r"\*\*|__", "", plain(line.lstrip("# "))) for line in lines if line.startswith("## ")), url)
    script = page.script or len(re.findall(r"[^\W\d_]{3,}", plain(text))) < MIN_WORDS
    return title, text, tuple(page.links), script


def read(html: str, url: str, headings: str | None = None) -> tuple[str, str, list[tuple[str, str]]]:
    """(title, markdown lines, links) of a page; `headings`: Site.headings."""
    title, text, links, _ = convert_page(html, url, headings)
    return title, text, list(links)


def _taken(site: Site, url: str) -> bool:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or parts.netloc != urlsplit(site.base).netloc or DOC.search(parts.path) or NOT_PAGE.search(parts.path):
        return False
    return not re.search(site.skip, unquote(parts.path).lstrip("/"), re.I)


def repaired(site: Site, loc: str) -> str:
    """An address of a sitemap with the host written twice, as media's lists its news
    ('http://media.innopolis.universitymedia.innopolis.university/news/...'): the host once."""
    host = re.escape(urlsplit(site.base).netloc)
    return re.sub(rf"^(https?://){host}(?={host}/)", r"\1", loc)


def languaged(site: Site, url: str, page: str) -> str:
    """A link of the site written without a language (Site.bare): the page in the language of the page it is on;
    a file is not in a language ('/uploads/x.jpg')."""
    parts, lang = urlsplit(url), re.match(r"/([a-z]{2})(/|$)", urlsplit(page).path)
    if not site.bare or not lang or parts.netloc != urlsplit(site.base).netloc or re.match(r"/[a-z]{2}(/|$)", parts.path) or re.search(r"\.\w+$", parts.path):
        return url
    return url.replace(parts.netloc, f"{parts.netloc}/{lang.group(1)}", 1)


def robots_of(site: Site, client: httpx.Client) -> RobotFileParser | None:
    """The rules of the site's robots.txt, for a site that asks to follow them (Site.robots); None: every page may be read."""
    if not site.robots:
        return None
    rules = RobotFileParser()
    try:
        rules.parse(get_through(client, urljoin(site.base, "/robots.txt")).text.splitlines())
    except httpx.HTTPError as e:
        print(f"  no robots.txt ({e}): every page is read")
        return None
    return rules


def load(name: str) -> dict:
    path = ROOT / name / "index.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"pages": {}, "docs": {}}


def save(name: str, index: dict) -> None:
    (ROOT / name).mkdir(parents=True, exist_ok=True)
    (ROOT / name / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def new_linked_pages(names: list[str] | None = None) -> dict[str, set[str]]:
    """Trusted-provider page links in cached pages whose target is not cached yet."""
    from catix.wiki.sources import crawl

    readable = every_site()
    selected = names or list(readable)
    known = {name: {canonical(page["url"]) for page in load(name)["pages"].values() if page.get("url")} for name in readable}
    found: dict[str, set[str]] = {}
    for source in selected:
        folder = ROOT / source
        if not folder.is_dir() or source not in readable:
            continue
        index = load(source)
        for path in folder.glob("*.md"):
            url = index["pages"].get(path.stem, {}).get("url", readable[source].base)
            for target in crawl.page_links(path.read_text(encoding="utf-8"), url):
                provider = crawl.provider(target)
                if provider and target not in known.setdefault(provider, set()):
                    found.setdefault(provider, set()).add(target)
    return found


def known_urls(index: dict) -> set[str]:
    """The addresses of a site's index, gone ones too (a page that went, a copy of another under a second address: not new)."""
    return {page["url"].rstrip("/") for page in index["pages"].values() if page.get("url")}


def fetch_site(name: str, site: Site, client: httpx.Client, start: list[str] | None = None,
               linked: dict[str, set[str]] | None = None, visited: set[str] | None = None, run: str | None = None,
               only_new: bool = False) -> int:
    """Read every page of a site (from its sitemap and the links of its pages); keep the text of the new and changed ones
    and the documents they link. The number of pages that are new, changed or gone. `run` names the run (`fetch` reads a
    page again in the waves of linked pages): a page read short or not found is taken so only when another run finds it so.

    An address the index does not have is read before the known ones: a new item of a feed does not wait for 2000 old news
    (media's sitemap stopped in July 2024: its new pages are in the links of its start page), nor miss max_pages. With
    `only_new` the pages of `start` are read and then only the new addresses they link (fetch_new), at most NEW_PAGES of them.
    A few pages (`start`: a wave) do not read again a page this run read (`visited`): its site's run read it, and its links."""
    from catix.wiki.sources import crawl

    run = run or datetime.now(timezone.utc).isoformat()
    index = load(name)
    known = known_urls(index)
    fresh: list[str] = []  # the new addresses: read first
    kept = {slug: (ROOT / name / f"{slug}.md").read_text(encoding="utf-8") for slug, page in index["pages"].items()
            if not page.get("gone") and (ROOT / name / f"{slug}.md").exists()}  # the pages as the last runs kept them
    common = {lang: boilerplate([t for slug, t in kept.items() if language_of(site, slug) == lang]) for lang in ("ru", "en")}
    partial = start is not None
    todo: list[str] = list(start) if start is not None else [site.base]

    def url_of(link: str) -> str:
        number = re.search(rf"[?&]{site.listing}=(\d+)", link) if site.listing else None
        return canonical(link) + (f"?{site.listing}={number.group(1)}" if number and number.group(1) != "1" else "")  # (a page of a list, after its first)

    def put(link: str) -> None:
        url = url_of(link)
        if ("?" not in url or DOWNLOAD.search(urlsplit(url).path)) and url.rstrip("/") not in known:  # listing queries are not new pages; download IDs are distinct files
            fresh.append(link)
        elif not only_new:
            todo.append(link)

    if site.sitemap and not partial:
        try:
            path = site.sitemap if isinstance(site.sitemap, str) else "sitemap.xml"
            maps = [urljoin(site.base, path)] + ([urljoin(site.base, f"{site.english}/{path}")] if site.english else [])
            for _ in range(100):  # (a sitemap may list sitemaps: Bitrix keeps one per block of the site)
                if not maps:
                    break
                for loc in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", get_through(client, maps.pop(0)).text):
                    if loc.endswith(".xml"):
                        maps.append(loc)
                    else:
                        put(repaired(site, loc))
                time.sleep(PAUSE if site.pause is None else site.pause)
        except httpx.HTTPError as e:
            print(f"  {name}: no sitemap ({e})")
        time.sleep(PAUSE if site.pause is None else site.pause)
    if site.discover and not partial:  # (the pages no link leads to: the browser lists them)
        render_live(site.base, profile_of(site))
        for path in json.loads(LIVE[profile_of(site)].evaluate(site.discover)):
            put(urljoin(site.base, path))
        print(f"  {name}: {len(todo) + len(fresh)} pages listed, {len(fresh)} of them new")
    rules = robots_of(site, client)
    seen, read_slugs, read_ok, changed, docs = set(), set(), 0, 0, {}
    first: dict[str, str] = {}  # the words of a page (their hash) -> the page read with them first in this run
    limit = min(site.max_pages, len(todo) + NEW_PAGES) if only_new else site.max_pages


    while (fresh or todo) and len(seen) < limit:
        link = (fresh or todo).pop(0)
        url = url_of(link)
        if (url in seen or (partial and visited is not None and url in visited) or not _taken(site, url)
                or rules and not rules.can_fetch(regulations.HEADERS["User-Agent"], url)):
            continue
        seen.add(url)
        if visited is not None:
            visited.add(url)
        slug = slug_of(site, url)
        if index["pages"].get(slug, {}).get("url", url).rstrip("/") != url.rstrip("/"):  # (two paths, one slug: a Cyrillic path leaves nothing of itself, 'home' is taken)
            slug = f"{slug[:50]}-{hashlib.sha1(url.encode()).hexdigest()[:6]}"
        try:
            if DOWNLOAD.search(urlsplit(url).path):
                # Do not GET a potentially large binary just to classify it as an archive.
                head = client.head(url)
                kind = ARCHIVE_TYPES.get(head.headers.get("content-type", "").split(";", 1)[0].lower())
                if head.status_code == 200 and kind and crawl.provider(url):
                    docs[url] = index["docs"].get(url, urlsplit(url).path.rsplit("/", 1)[-1])
                    index.setdefault("archive_types", {})[url] = kind
                    changed += url not in index["docs"]
                    read_ok += 1
                    time.sleep(PAUSE if site.pause is None else site.pause)
                    continue
            resp = get_page(client, site, url)
            time.sleep(PAUSE if site.pause is None else site.pause)
        except httpx.HTTPError as e:
            print(f"  FAILED {url}: {e}")
            continue
        old = index["pages"].get(slug, {})
        if resp.status_code == 404 or "text/html" not in resp.headers.get("content-type", ""):
            if old and not old.get("gone") and slug not in read_slugs:  # (not for the other spelling of an address that was read: /x/ and /x)
                changed += missed(index["pages"], slug, "404" if resp.status_code == 404 else f"not a page ({resp.headers.get('content-type', 'no type')})", run)
            continue
        if resp.status_code != 200:
            print(f"  {url}: {resp.status_code}")
            continue
        title, text, links = read(resp.text, str(resp.url), site.headings)
        if WALL_TITLE.search(title):  # (a bot check that let none of the asks of get_page through, not the site's page)
            print(f"  {url}: a bot check answers in its place", flush=True)
            continue
        read_ok += 1
        read_slugs.add(slug)
        if "missing" in old:  # (it is there: the 404 or the missing link before was the wrong one)
            old = index["pages"][slug] = {key: value for key, value in old.items() if key != "missing"}
        if site.private:
            text = re.sub(site.private, "", text, flags=re.M).rstrip() + "\n"  # (the person who is logged in is not the page's)
        if site.bare:
            links = [(languaged(site, link, str(resp.url)), anchor) for link, anchor in links]
            text = re.sub(r"(!\[[^\]]*\]\([^)\s]*\))|(?<=\]\()https?://[^)\s]+", lambda m: m.group(1) or languaged(site, m.group(), str(resp.url)), text)  # (not a picture)
        if (extra := EXTRAS.get((name, slug))):
            text = extra(client, resp.text, str(resp.url), text)
        for link, anchor in links:
            if (DOC.search(urlsplit(link).path) or canonical(link) in index.get("archive_types", {})) and crawl.provider(link):
                doc = canonical(link)
                docs[doc] = max(docs.get(doc, ""), anchor, key=len)  # the fullest of the link texts: 'Правила проживания', not 'Правила'
            elif _taken(site, link) or crawl.provider(link) == name:
                put(link)
            elif linked is not None and (other := crawl.provider(link)):
                target = canonical(link)
                if target not in (visited or set()) and target not in linked.setdefault(other, set()):
                    linked[other].add(target)
        if "?" in url:  # (a page of a list: its links are taken, it is not kept)
            continue
        sha = hashlib.sha256(plain(text).encode()).hexdigest()  # (the words: a new link or picture is not a new version)
        if first.setdefault(sha, slug) != slug:  # the page read before under another address (Tilda: '/Vue-js-framework' is '/vue-js-framework')
            if old and not old.get("gone"):
                index["pages"][slug] = {**old, "gone": True}
                changed += 1
            continue
        (ROOT / name).mkdir(parents=True, exist_ok=True)
        if keep_by_hand(name, slug, old):  # (a person wrote this page: the crawl does not write over it; its words are the page's words now)
            mine = ROOT / name / f"{slug}.md"
            index["pages"][slug] = {**old, "manual": True, "sha256": hashlib.sha256(plain(mine.read_text(encoding="utf-8")).encode()).hexdigest(),
                                    "file_sha": hashlib.sha256(mine.read_bytes()).hexdigest()}
            print(f"  {slug}: edited by hand, kept")
            continue
        if old.get("sha256") == sha and not old.get("gone"):
            index["pages"][slug] = {key: value for key, value in old.items() if key != "short"}  # (the short read was the wrong one)
            if not (ROOT / name / f"{slug}.md").exists() or (ROOT / name / f"{slug}.md").read_text(encoding="utf-8") != text:
                index["pages"][slug]["file_sha"] = put_cache(name, slug, text)  # (the same words, other links and pictures)
            continue
        mark = old.get("short")
        if slug in kept and not old.get("gone") and not (mark and mark["run"] != run):  # a read that went wrong (a stub, an app's empty shell, half a page)
            lang = language_of(site, slug)  # writes over the page and the cards drop what it said: the next run has to read it so too
            before, after = own_words(site, kept[slug], common[lang]), own_words(site, text, common[lang])
            if before >= MIN_WORDS and after < SHORT_READ * before:
                index["pages"][slug] = {**old, "short": mark or {"words": after, "run": run}}
                if not mark:
                    print(f"  {slug}: {after} words of its {before}, kept as it was until the next run reads it so", flush=True)
                continue
        index["pages"][slug] = {"url": url, "title": title, "sha256": sha, "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                "last_modified": resp.headers.get("last-modified", ""), "file_sha": put_cache(name, slug, text)}
        changed += 1
        print(f"  {slug}: {'changed' if old else 'new'}, {len(text)} chars", flush=True)
        if changed % 50 == 0:
            save(name, index)  # (a long crawl cut short keeps what it read)
    for slug, page in list(index["pages"].items()):  # a page no link leads to any more has left the site
        if (read_ok and not partial and page["url"] not in seen and slug not in read_slugs and not page.get("gone")
                and len(seen) < site.max_pages):  # (not when the site did not answer; not from a few pages: they do not lead everywhere)
            changed += missed(index["pages"], slug, "no link leads to it", run)
    if read_ok and not partial:
        index["docs"] = docs
    elif docs:  # (a few pages: their documents join the site's, the whole site's run says which are linked no more)
        index["docs"] = docs | index["docs"]
    save(name, index)
    return changed


def fetch(names: list[str] | None = None, only_new: bool = False, documents: bool = False, ocr: bool = False) -> int:
    """The sites named (every site when none is, the pending ones too), one after another, then the pages of other trusted
    sites their pages link, wave after wave; the number of pages that are new, changed or gone. In a site this run read whole
    a wave reads the pages the run has not read yet (a page only another site leads to: its own run did not reach it, and
    without the wave it would be gone a week later). In any other site it reads only the addresses its index does not have,
    then the new addresses these link (fetch_site, only_new), NEW_DEPTH waves at most, as fetch_new does: its known pages are
    the weekly run's, which reads them all again (the approval of a site that links one page of innopolis.university read
    hundreds of the university's pages). A site never read and a site behind a login are left to the weekly run, which reads
    them whole. `only_new` reads no site whole: the links of their cached pages that the sites they lead to do not have
    (new_linked_pages), wave after wave.

    With `documents` (the weekly run) the waves go on through the documents: once the pages settle, the documents they link
    are read (regulations.read_new, which follows the documents those link; text layers only by default, scans queued for
    a later manual run with OCR), and the pages of trusted sites
    their text names are the next wave, whose documents are read in turn, until a wave brings nothing new (document -> site
    -> document -> site). The first such wave takes the pages every document read so far names, not only the new ones': a
    page only a document leads to is not reached by its own site's run, and without the wave it would be gone a week later
    ('no link leads to it'). A run of a few sites takes their documents and the pages of what it read. The number counts
    the documents read too."""
    every = every_site()
    if unknown := [n for n in names or [] if n not in every]:
        sys.exit(f"no site {', '.join(unknown)}: the sites are {', '.join(every)}")
    total, run = 0, datetime.now(timezone.utc).isoformat(timespec="seconds")
    weekly = not names and not only_new  # (every site read whole: its waves have no end but what they bring)
    no_cookies = CookieJar(policy=DefaultCookiePolicy(allowed_domains=[]))  # every page as a new visitor sees it (robotics keeps the language of the last page in a cookie: its sitemap became English)
    with httpx.Client(headers=regulations.HEADERS, timeout=60, follow_redirects=True, cookies=no_cookies) as client:
        linked: dict[str, set[str]] = new_linked_pages(names) if only_new else {}
        visited: set[str] = set()
        whole = set() if only_new else {name for name in every if not names or name in names}
        for name, site in every.items():
            if name not in whole:
                continue
            print(f"== {name}: {site.base}")
            try:
                total += fetch_site(name, site, client, linked=linked, visited=visited, run=run)
            finally:
                close_live()

        def unread(name: str, urls: set[str]) -> list[str]:
            """The linked pages of a site a wave reads: those the run has not read, and of a site it did not read whole
            only those its index does not have."""
            urls = urls - visited  # (read since the link was found: by its site's run)
            if name in whole:
                return sorted(urls)
            if SITES[name].profile or not (ROOT / name / "index.json").exists():
                return []
            known = known_urls(load(name))
            return sorted(url for url in urls if url.rstrip("/") not in known)

        prefixes = tuple(f"site-{name}-" for name in names) if names else None
        first = True
        while True:
            depth = 0
            while linked and (weekly or depth < NEW_DEPTH):
                wave, linked, depth = linked, {}, depth + 1
                for name, urls in wave.items():
                    if name not in SITES or not (start := unread(name, urls)):
                        continue
                    print(f"== {name}: {len(start)} linked pages" + ("" if name in whole else " it does not have"))
                    try:
                        total += fetch_site(name, SITES[name], client, start=start, linked=linked, visited=visited, run=run,
                                            only_new=name not in whole)
                    finally:
                        close_live()
            if not documents:
                break
            print("== the documents the pages link", flush=True)
            read = regulations.read_new(prefixes=prefixes, ocr=ocr)
            total += len(read)
            found = regulations.page_links_of(None if first and not names else read)
            first = False
            linked = {other: urls - visited for other, urls in found.items() if urls - visited}
            if linked:
                print(f"== the pages of trusted sites the documents name: {sum(map(len, linked.values()))}", flush=True)
            else:
                break
    return total


def entries(site: Site) -> list[str]:
    """The pages a site shows its new pages on: its feeds (Site.feeds), its start page (in each language) when it names none."""
    if site.feeds:
        return list(dict.fromkeys(urljoin(site.base, path) for path in site.feeds))
    return [site.base, *([urljoin(site.base, f"{site.english}/")] if site.english else [])]


def fetch_new(names: list[str] | None = None, client: httpx.Client | None = None, documents: bool = False) -> int:
    """The pages that appeared since the last run, read now and not at the weekly run: the feed of each site (its start page
    when it names none: entries), the new addresses it links (fetch_site, only_new) and, wave after wave (NEW_DEPTH), the new
    pages of other trusted sites that the new pages link. No sitemap: a known address is not read, but its file is (84 of
    them, 5 minutes of a run), and a new page is in the feed first. The pages a site had are the weekly `fetch`'s: it reads
    them all again for changes, and its sitemap. So is a site behind a login (Site.profile: the person's browser once a week,
    not every few hours) and a site the weekly run has not read yet (the whole of it, not 50 pages). The number of pages new
    or changed.

    With `documents` (the 6-hourly run) the documents a wave's new pages link are read after it by their text layer alone
    (regulations.read_new without OCR: a scan is queued for a manual OCR run, so no OCR model needs to be up), and the new pages
    of trusted sites their text names join the next wave (site -> site -> document -> site). The number counts them too."""
    reload_catalog()
    if unknown := [n for n in names or [] if n not in SITES]:
        sys.exit(f"no site {', '.join(unknown)}: the sites are {', '.join(SITES)}")
    run = datetime.now(timezone.utc).isoformat(timespec="seconds")
    readable = {name for name, site in SITES.items() if not site.profile and (ROOT / name / "index.json").exists()}
    wave = {name: entries(SITES[name]) for name in SITES if name in readable and (not names or name in names)}
    total, visited = 0, set()
    with contextlib.ExitStack() as stack:
        if client is None:
            no_cookies = CookieJar(policy=DefaultCookiePolicy(allowed_domains=[]))
            client = stack.enter_context(httpx.Client(headers=regulations.HEADERS, timeout=60, follow_redirects=True, cookies=no_cookies))
        for depth in range(NEW_DEPTH + 1):
            linked: dict[str, set[str]] = {}
            changed = 0
            for name, start in wave.items():
                print(f"== {name}: {'its start pages' if depth == 0 else f'{len(start)} new pages linked'}", flush=True)
                try:
                    changed += fetch_site(name, SITES[name], client, start=start, linked=linked, visited=visited, run=run, only_new=True)
                except Exception as e:  # noqa: BLE001 - one site failing (its browser, its server) leaves the others to read; the weekly run reads it whole
                    print(f"  {name}: {type(e).__name__}: {str(e)[:300]}", flush=True)
                finally:
                    close_live()
            total += changed
            if documents and changed:  # (the documents of the pages read, by their text layer; the pages their text names)
                read = regulations.read_new(prefixes=("site-",), ocr=False)
                total += len(read)
                for other, urls in regulations.page_links_of(read).items():
                    linked.setdefault(other, set()).update(urls - visited)
            wave = {}
            for name, urls in linked.items():
                known = known_urls(load(name)) if name in readable else set()
                if name in readable and (new := sorted(u for u in urls if u.rstrip("/") not in known)):
                    wave[name] = new
            if not wave:
                break
    return total


LINKED_DOC = re.compile(r"\[([^\]]*)\]\((https?://[^)\s]+)\)")
PICTURE = re.compile(r"!\[([^\]]*)\]\([^)\s]*\)")


def links_of(text: str) -> list[tuple[str, str]]:
    """(text, address) of the links of a page of the bundle. A picture that is a link (`[![](cover.png)](rules.pdf)`: Tilda's
    covers of the collections of edu) is a link whose text is the picture's alt: LINKED_DOC alone took the picture's address
    for the link's and lost the document."""
    return LINKED_DOC.findall(PICTURE.sub(lambda m: m.group(1), text))


def collect_linked_docs() -> int:
    """The documents of trusted providers (crawl.provider: a site of SITES, not a pending one) that the pages of the bundle
    link and no site has among its documents yet (a page of `apply` or `dovuz` linking a PDF of innopolis.university: fetch_site
    took only the documents of the site's own host before): added to the documents of the site whose page links them, to be
    downloaded by `regs fetch`. The links are read from the pages as they are in the bundle, so the sites need not be read
    again. The number added."""
    from catix.wiki.sources import crawl

    names = list(every_site())
    have = {canonical(u) for name in names for u in load(name)["docs"]}
    added = 0
    for name in names:
        folder = DOCS / FOLDER / name
        if not folder.is_dir() or not (ROOT / name / "index.json").exists():
            continue
        index, found = load(name), {}
        for page in sorted(folder.glob("*.md")):
            for label, link in links_of(page.read_text(encoding="utf-8")):
                url = canonical(link)  # (https: a link the site wrote with http:// is the same file)
                if DOC.search(urlsplit(link).path) and url not in have and crawl.provider(url):
                    found[url] = max(found.get(url, ""), label, key=len)
        if found:
            index["docs"].update(found)
            save(name, index)
            have |= set(found)
            added += len(found)
            print(f"  {name}: {len(found)} documents of trusted sites added")
    return added


def docs() -> dict[str, dict]:
    """The documents the sites link, as regulations.all_docs wants them (those a pending site links too: they are of trusted
    providers, as every document of a site's index)."""
    out = {}
    for name, site in every_site().items():
        index = load(name)
        for url, anchor in index["docs"].items():
            file = unquote(urlsplit(url).path.rsplit("/", 1)[-1])
            stem = re.sub(r"[_]+", " ", file.rsplit(".", 1)[0]).strip()
            if re.search(r"(?i)\.(pdf|docx?|xlsx?|pptx?|rtf|odt)$", anchor):  # the link says the file's name (help: 'Приказ ад-01.2019.12.23 регламент_процесса_….pdf')
                anchor = re.sub(r"_+", " ", anchor.rsplit(".", 1)[0]).strip()
            title = anchor if len(anchor) >= 12 and not re.fullmatch(r"(?i)(скачать|здесь|тут|download|here|подробнее|ссылк\w*)", anchor) else stem
            title = re.sub(r"\s+", " ", re.sub(r"\s*\(\d\)$", "", title)).strip()  # ('… 2025 год (2)': the second copy of a file)
            key = f"site-{name}-" + hashlib.sha1(url.encode()).hexdigest()[:8] + "-" + (latin(stem)[:40].strip("-") or "doc")
            out[key] = {"title": title, "url": url, "root": ROOT / name / "docs", "section": f"site/{name}", "ext": index.get("archive_types", {}).get(url, file.rsplit(".", 1)[-1].lower()),
                        **({"audience": list(site.audience)} if site.audience else {})}  # (the regulations of help are for the staff, as its pages)
    return out


def boilerplate(texts: list[str]) -> set[str]:
    """Lines that many pages of a site repeat: its menu, its footer, its contacts block. A small site needs half of its pages
    (at least 3) to repeat a line; a large one a quarter, but no fewer than 10 pages: a section of a site has its own menu and
    footer, which is on a third of the pages, not on a half. They are kept once, in the site's shared page, not lost."""
    if len(texts) < 3:
        return set()
    need = max(3, min(0.5 * len(texts), max(10, 0.25 * len(texts))))
    counts = Counter(line for text in texts for line in set(text.splitlines()))
    return {line for line, n in counts.items() if n >= need}


def own_words(site: Site, text: str, common: set[str]) -> int:
    """The words of a page that are its own: not the lines its site repeats (the menu, the footer: on sez.innopolis.ru 80% of a
    page), not what comes after Site.end (the related news). What a read that went wrong loses, and a menu would hide it."""
    own = re.split(site.end, text, maxsplit=1)[0] if site.end else text
    return len(re.findall(r"[^\W\d_]{3,}", plain("\n".join(line for line in own.splitlines() if line not in common))))


def year_of(site: Site, slug: str, title: str, body: str) -> int | None:
    """The year a page is about, on a site whose pages have one: the latest year of its title, its address and the start of its
    text ('InnoBootCamp 2018', 'springball2022'). A page of this year, or of none, is not dated."""
    if not site.dated:
        return None
    years = [int(y) for y in re.findall(r"(?<!\d)(20\d\d)(?!\d)", f"{slug} {title} {plain(body)[:300]}")]
    return max(years) if years else None


PAST_NOTE = {"ru": "> Страница относится к {} году: сведения на ней могли устареть.", "en": "> This page is from {}: what it says may be out of date."}


def language_of(site: Site, slug: str) -> str:
    return "en" if site.english and (slug == site.english or slug.startswith(site.english + "-")) else site.language


def page_path(name: str, slug: str) -> str:
    """Where a page of a site is in the bundle."""
    return f"/{DOCS.name}/{FOLDER}/{name}/{slug}.md"


def address(url: str) -> str:
    """The spelling under which the pages and the links to them are compared; a link to another host of a site (Site.aliases)
    is compared as a link to the site ('university.innopolis.ru/en/about/' is 'innopolis.university/en/about/')."""
    reload_catalog()
    spelled = canonical(urldefrag(url)[0]).rstrip("/")
    host = urlsplit(spelled).netloc
    own = next((urlsplit(site.base).netloc for site in SITES.values() if host.removeprefix("www.") in site.aliases), None)
    return spelled.replace(host, own, 1) if own else spelled


def resolve(body: str, where: dict[str, str]) -> str:
    """The links of a page that lead to a page or a document of the bundle lead there; the others stay as the site wrote
    them. A picture is not touched (its link is the picture's own)."""
    def one(m: re.Match) -> str:
        if m.group(1):
            return m.group(1)
        url = m.group(2)
        return f"]({where.get(address(url), url)})"
    return re.sub(r"(!\[[^\]]*\]\([^)\s]*\))|\]\(((?:https?://)[^)\s]*)\)", one, body)


SHARED_NOTE = {"ru": "_Меню, подвал и другие блоки, которые повторяются на страницах сайта, собраны в одном месте: [{0}]({0})._",
               "en": "_The menu, footer and other blocks that the pages of the site repeat are kept in one place: [{0}]({0})._"}


def first_sentence(title: str, words: str) -> str:
    """The description of a page: the first sentence of its text, what the page begins with, not a guess; its title when it has none."""
    for line in words.splitlines():
        line = line.strip()
        if len(line) > 40 and not line.startswith(("#", "|", "-", ">", "!", "[")) and len(re.findall(r"[^\W\d_]{3,}", line)) >= 6 \
                and not re.search(r"(?i)\bsign in\b|\blog ?in\b|account to access", line):  # (not the invitation to sign in)
            return (re.split(r"(?<=[.!?])\s", line)[0])[:200]
    return title[:200]


def shared_file(site: Site, lang: str) -> str:
    return "_shared.md" if lang == site.language else f"_shared-{lang}.md"


def write_shared(out, name: str, lang: str, body: str, at: str, keep: set) -> int:
    """The lines every page of a site repeats (menu, footer, contacts), once, as a page of its own: the pages lose them, the wiki
    keeps them, and search finds them in one place instead of in a copy per page."""
    site = every_site()[name]
    host = urlsplit(site.base).netloc
    title = f"Общие блоки сайта {host}: меню, шапка, подвал, контакты" if lang == "ru" else f"Blocks shared by the pages of {host}: menu, header, footer, contacts"
    sha = hashlib.sha256(plain(body).encode()).hexdigest()[:12]
    front = ["---", "type: page", f"title: {yaml_value(title)}",
             f"description: {yaml_value('The menu, header, footer and contact lines that every page of the site repeats, kept once.')}",
             f"resource: {yaml_value(site.base)}", "tags: [\"site\", \"menu\", \"footer\", \"contacts\"]", f"audience: {yaml_value(list(site.audience or AUDIENCES))}",
             "source_kind: website", f"language: {lang}", f"section: {yaml_value(f'site/{name}')}",
             "sources:", f"  - resource: {yaml_value(site.base)}", f"    id: {yaml_value(sha)}", f"    title: {yaml_value(title)}", f"    last_modified: {yaml_value(at)}",
             "generated:", f"  by: {yaml_value(PRODUCER + ' sites (code: the lines the pages repeat)')}", f"  at: {yaml_value(at)}", "status: draft", "---"]
    page = "\n".join(front) + f"\n\n# {title}\n\n{body}\n\n# Citations\n\n1. [{host}]({site.base}), read {at[:10]}\n"
    target = out / name / shared_file(site, lang)
    keep.add(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if page == (target.read_text(encoding="utf-8") if target.exists() else ""):
        return 0
    target.write_text(page, encoding="utf-8")
    return 1


def compile_all() -> None:
    """Every page read -> wiki/raw/sites/<site>/<slug>.md, by code alone (its description: its first sentence); a page gone
    from its site loses its page. The links of a page lead to the pages and documents of the
    bundle that they name (all the sites together: a page of one may link a page of another), to the site itself otherwise."""
    readable = every_site()
    out = DOCS / FOLDER
    out.mkdir(parents=True, exist_ok=True)
    entries: dict[tuple[str, str], dict] = {}
    shared: dict[tuple[str, str], list[str]] = {}  # (site, language) -> the lines its pages repeat, in the order they come
    kept: dict[str, str] = {}  # the address of a page of a site not read here -> its page, as it is
    untouched: set = set()  # the files of those sites
    for name, site in readable.items():  # (the pending sites' too: a person reviews them, explore looks in them for hosts)
        if not (ROOT / name / "index.json").exists():  # (read elsewhere: a site behind a login, by the person's browser) its pages stay as they are
            files = [f for f in sorted((out / name).glob("*.md")) if f.name != "index.md"] if (out / name).is_dir() else []
            untouched |= set(files)
            for page in files:
                if not page.name.startswith("_") and (url := re.search(r'^resource: "?([^"\n]+?)"?$', page.read_text(encoding="utf-8"), re.M)):
                    kept[address(url.group(1))] = page_path(name, page.stem)  # (not the shared blocks: their address is the site's)
            if files:
                print(f"{name}: not read here (no {ROOT.name}/{name}/index.json), its {len(files)} pages kept as they are")
            continue
        pages = {slug: p for slug, p in load(name)["pages"].items() if not p.get("gone") and (ROOT / name / f"{slug}.md").exists()}
        texts = {slug: (ROOT / name / f"{slug}.md").read_text(encoding="utf-8") for slug in pages}
        common = {lang: boilerplate([t for slug, t in texts.items() if language_of(site, slug) == lang]) for lang in {"ru", "en"}}  # (each language has its menu)
        same = Counter(p["title"] for p in pages.values())  # (a title that five pages share names none of them: the template's, 'Шапка')
        ends = Counter(m.group() for p in pages.values() if (m := re.search(r"\s[|—–-]\s[^|—–]{3,}$", p["title"])))
        suffix = next((end for end, n in ends.most_common(1) if n >= max(5, len(pages) / 2)), None)  # (the name of the site after the page's: ' — Центр технологий ... мехатроники')
        for slug, p in sorted(pages.items()):
            if p["title"].startswith("Copy of "):
                continue  # (Tilda's copy of a page, left unpublished: 'Copy of Гасников Александр Владимирович')
            lang = language_of(site, slug)
            for line in texts[slug].splitlines():
                if line in common[lang] and line not in shared.setdefault((name, lang), []):
                    shared[name, lang].append(line)
            own = re.split(site.end, texts[slug], maxsplit=1)[0] if site.end else texts[slug]  # (the related and popular news are not the page's: they change by the day)
            lines = [line for line in own.splitlines() if line not in common[lang] and not (site.drop and re.fullmatch(site.drop, line))]
            title = re.sub(r"\s*[|—–-]\s*(Campus Life|Кампус.*|Университет Иннополис|Innopolis University|Иннополис|Innopolis)$", "", p["title"]).strip() or p["title"]  # (innopolis.com: 'Аренда жилья - Иннополис')
            if suffix and title.endswith(suffix) and title != suffix.strip(" |—–-"):
                title = title[:-len(suffix)].strip()
            if same[p["title"]] >= 5 and len(pages) >= 10:
                title = next((h for h in (plain(line).lstrip("# ").strip() for line in lines if re.match(r"#{2,3} ", line)) if h), title)  # its first heading names the page
            head = next((i for i, line in enumerate(lines[:3]) if plain(line).lstrip("# ").lower() == title.lower()), None)
            if head is not None:  # (the page's own heading: the title says it)
                del lines[head]
                if 0 < head < len(lines) and lines[head - 1] == lines[head]:
                    del lines[head]  # (the date of a news item before its heading and after it)
            if len(re.findall(r"[^\W\d_]{3,}", plain("\n".join(lines)))) < MIN_WORDS:
                continue  # a page of pictures and buttons
            entries[name, slug] = {"site": site, "page": p, "title": title, "lang": lang, "lines": lines}
    where = kept | {address(e["page"]["url"]): page_path(name, slug) for (name, slug), e in entries.items()}
    for key, doc in regulations.all_docs().items():  # a document, once it is a page of regulations, under the key it has there: the
        if (DOCS / "regulations" / f"{key}.md").exists():  # file sveden lists too is `sveden-…`, not the site's (its link stayed the site's)
            where[address(doc["url"])] = f"/{DOCS.name}/regulations/{key}.md"
    keep, written = set(), 0
    for (name, lang), lines in sorted(shared.items()):
        pages = [e["page"] for (n, _), e in entries.items() if n == name and e["lang"] == lang]
        if lines and pages:
            written += write_shared(out, name, lang, resolve("\n\n".join(lines), where), max(p["fetched_at"] for p in pages), keep)
    for (name, slug), e in sorted(entries.items()):
        site, p, title, lang = e["site"], e["page"], e["title"], e["lang"]
        body = resolve("\n\n".join(e["lines"]), where)
        year = year_of(site, slug, title, body)
        past = year if year and year < datetime.now(timezone.utc).year else None  # (the year it is about is over)
        target = out / name / f"{slug}.md"
        keep.add(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        audience = [str(a) for a in p.get("audience") or site.audience or AUDIENCES]  # (everyone, unless a person named the readers of the page (sport/faq: students) or of the site)
        front = ["---", "type: page", f"title: {yaml_value(title)}", f"description: {yaml_value(first_sentence(title, plain(body)))}", f"resource: {yaml_value(p['url'])}",
                 f"audience: {yaml_value(audience)}", "source_kind: website", f"language: {lang}",
                 f"section: {yaml_value(f'site/{name}')}",
                 "sources:", f"  - resource: {yaml_value(p['url'])}", f"    id: {yaml_value(p['sha256'][:12])}", f"    title: {yaml_value(title)}",
                 f"    last_modified: {yaml_value(f'{past}-01-01T00:00:00+00:00' if past else p['fetched_at'])}",  # (the day of the page, not of the crawl: the search says 'date' of it)
                 "generated:", f"  by: {yaml_value(PRODUCER + ' sites')}", f"  at: {yaml_value(p['fetched_at'])}", "status: draft"]
        if past:
            front.append(f"stale_after: {yaml_value(f'{past + 1}-01-01T00:00:00+00:00')}")  # (the search warns: may be outdated)
            body = PAST_NOTE[lang].format(past) + "\n\n" + body
        front.append("---")
        if shared.get((name, lang)):
            body += "\n\n" + SHARED_NOTE[lang].format(page_path(name, shared_file(site, lang)[:-3]))
        page = "\n".join(front) + f"\n\n# {title}\n\n{body}\n\n# Citations\n\n1. [{title}]({p['url']}), read {p['fetched_at'][:10]}\n"
        if page != (target.read_text(encoding="utf-8") if target.exists() else ""):
            target.write_text(page, encoding="utf-8")
            written += 1
    keep |= untouched
    for page in out.rglob("*.md"):
        if page not in keep and page.name != "index.md":
            page.unlink()
            print(f"{page.relative_to(out)}: no longer on its site (or moved), page removed")
    print(f"{written} pages written, {len(keep)} pages of the sites in the bundle")


def status() -> None:
    for name, site in every_site().items():
        index = load(name)
        pages = index["pages"].values()
        print(f"{name} ({site.base}{', pending a look' if name not in SITES else ''}): {sum(not p.get('gone') for p in pages)} pages, "
              f"{sum(bool(p.get('gone')) for p in pages)} gone, {len(index['docs'])} documents linked")


def main(args: Namespace) -> None:
    cmd = args.action
    if cmd == "migrate":
        migrate_catalog(args.source)
        print(f"site catalog: {CONFIG}; pending settings: {DISCOVERED}")
    elif cmd == "fetch":
        only_new = getattr(args, "only_new", False)
        print(f"{fetch(args.names, only_new=only_new, documents=not only_new)} pages new, changed or gone" + ("" if only_new else " and documents read"))
    elif cmd == "new":
        print(f"{fetch_new(args.names, documents=True)} pages new or changed and documents read")
    elif cmd == "compile":
        compile_all()
    elif cmd == "status":
        status()
    elif cmd == "docs":
        print(f"{collect_linked_docs()} documents added; `catix-wiki regs fetch` downloads and reads them")
    elif cmd in ("discover", "explore", "add", "review", "accept", "approve", "reject"):
        from catix.wiki.sources import discover

        discover.main(args)
