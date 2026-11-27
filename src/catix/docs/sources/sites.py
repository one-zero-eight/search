"""The sites of the university and its services as a source of the documents: innopolis.university (the university's own
site, every page in Russian and English, its disclosure section /sveden/ too: the staff, the structure and the documents
the university discloses, as any other page and its documents), apply.innopolis.university (for applicants: programmes, admission, grants, olympiads;
Russian), campuslife.innopolis.ru
(student life: the handbook, the FAQ, scholarships, clubs; English), hotel.innopolis.university (the campus and its
dormitories; Russian), new.innopolis.university/en/ (international applicants; English), media.innopolis.university (the
news and events), stc.innopolis.university (IT courses), edu.innopolis.university (programmes for schools and teachers),
innopolis.com (the city and its special economic zone; Russian and English), and the sites of the university's units and
projects the pages link most (career, corporate, dovuz, progmatica, the college, the dissertation council, ...; see the catalog).

    catix-docs sites request URL        # a new site: the run adds it to the catalog and reads it
    catix-docs sites status             # the addresses of every site by kind and state (frontier.py)
    catix-docs sites unvisited          # the addresses no run has read, and the hosts the catalog does not have
    catix-docs sites catalog ...        # the catalog of sites (site_catalog): import, export, add, remove, block, unblock

The crawl is the frontier's (docs/frontier.py: one row per address, the links between them) and the runner's (docs/runner.py: it
reads the address that is due next). This module holds the rules of reading one address: read_page (a page: its text, its links,
the same words under two addresses, a 404, a short read) and read_listing (a sitemap, the pages a browser lists), and the
documents the pages make (compile_site).

A page's text is kept as the site shows it: html_to_markdown turns the markup into markdown (a page that needs its scripts,
an app's empty shell, is read in the browser first: get_page), the program drops what every page of the site repeats (menus,
footers); no model is asked: the description is the page's first sentence. The documents a site
links (PDF, DOCX: the rules of the dormitories, their prices) go the way of the regulations (regulations.py, which asks
`docs()`): documents under regulations/, quoted by clause, `source_kind: official-document`. The pages themselves are `website`.
Every page is read again on its own interval and its text compared: these sites say nothing reliable about changes (678 of 4476
pages sent Last-Modified, the sitemaps of media and apply stopped in 2024 and 2025). A page that comes back with less than half
of its own words (SHORT_READ: a stub, an app's empty shell, half a page), answers 404 or is no longer linked is kept as it was
until the next read finds it so too: written over or dropped at once, a bad read would take the page out of the search.
"""

import functools
import hashlib
import json
import logging
import os
import re
import shutil
import time
from argparse import Namespace
from collections import Counter
from dataclasses import MISSING, dataclass, fields
from datetime import datetime, timedelta, timezone
from http.cookiejar import CookieJar, DefaultCookiePolicy
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import parse_qs, quote, unquote, urldefrag, urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx
import yaml
from html_to_markdown import ConversionOptions, NodeContext, PreprocessingOptions, convert
from html_to_markdown.exceptions import ConversionError
from usp.exceptions import SitemapException
from usp.fetch_parse import SitemapFetcher
from usp.web_client.abstract_client import AbstractWebClient, AbstractWebClientResponse, AbstractWebClientSuccessResponse, WebClientErrorResponse

from catix.db import pg
from catix.docs.sources import hosts, regulations
from catix.docs.sources.rpd import latin
from catix.docs.store import AUDIENCES, PRODUCER, Document
from catix.settings import settings

if TYPE_CHECKING:
    from catix.docs.frontier import Row

REVALIDATE = timedelta(days=28)  # a page the site answered 304 is still read whole this often, so a change of the reading code reaches it
ROOT = "sites"  # the prefix of the documents' paths of the sites
PAUSE = 2  # seconds between requests
PROGRESS = 60  # seconds between two lines a crawl says of its progress
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
SHORT_READ = 0.5  # a page read with less than this share of its own words is kept as it was until the next read finds it so too (read_page)
RETRY = timedelta(days=6)  # a link a run asked and got nothing from (a 404, a file, a host down, a login) waits this long before a run of
# new links asks it again: 280 of the 474 links no run had read answered 404, and every 6-hourly run would ask them. Less than the
# week between two runs of every site: the weekly run asks again what the last one could not get (it reads every link of a site anyway).

logging.getLogger("usp").setLevel(logging.CRITICAL)
# (a site without a sitemap is no error: USP logs every 404 and every HTML robots.txt)


def recent(at: str | None, now: datetime | None = None) -> bool:
    """Whether a try noted at `at` (an ISO time) is newer than RETRY: the link waits, no run asks it yet."""
    try:
        when = datetime.fromisoformat(at or "")
    except ValueError:
        return False
    return (now or datetime.now(timezone.utc)) - when < RETRY


# A new field of Site needs the same column of site_catalog: ALTER TABLE site_catalog ADD COLUMN IF NOT EXISTS ... (db/schema.sql).
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
    feeds: tuple[str, ...] = ()  # the paths where the site shows its new pages (a list of news or events): the crawl reads them every few hours in place of the start page (frontier.seed)
    aliases: tuple[str, ...] = ()  # other hosts of the site, an old name or a mirror: a link to one leads to the site's page of the same path, when there is one


CATALOG_COLUMNS = [f.name for f in fields(Site)]  # the columns of site_catalog, from the dataclass so that the two cannot drift
TUPLE_FIELDS = ("audience", "aliases", "feeds")  # text[] in the table
DEFAULT_SITEMAP = "sitemap.xml"
CATALOG_TTL = 15.0  # seconds a process trusts what it read: crawl.provider asks for the catalog for every link


def read_yaml(path: Path) -> dict[str, Any]:
    """A catalog file (sites.yaml of the repository): the records by name, and the blocked hosts."""
    raw = cast(dict[str, Any], yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    return {"sites": raw.get("sites", {}), "blocked": list(raw.get("blocked", ()))}


def load_config() -> dict[str, Any]:
    """The catalog of the database: {"sites": {name: record}, "blocked": [host, ...]}; a record has every field of Site."""
    columns = ", ".join(f'"{column}"' for column in CATALOG_COLUMNS)
    with pg.connection() as conn:
        rows = conn.execute(f"SELECT name, {columns} FROM site_catalog ORDER BY name").fetchall()
        blocked = [row["host"] for row in conn.execute("SELECT host FROM blocked_hosts ORDER BY host").fetchall()]
    if not rows:
        raise FileNotFoundError(f"the site catalog is empty: `catix-docs sites catalog import {settings.sites_file}`")
    records: dict[str, Any] = {}
    for row in rows:
        record = {column: row[column] for column in CATALOG_COLUMNS}
        record["sitemap"] = False if record["sitemap"] is None else True if record["sitemap"] == DEFAULT_SITEMAP else record["sitemap"]
        for name in TUPLE_FIELDS:
            if record[name] is not None:
                record[name] = list(record[name])
        records[row["name"]] = record
    return {"sites": records, "blocked": blocked}


def make_site(values: dict[str, Any]) -> Site:
    """The typed settings of a site from its record."""
    names = {field.name for field in fields(Site)}
    tuple_fields = {"audience", "aliases", "feeds"}
    kwargs: dict[str, Any] = {key: tuple(value) if key in tuple_fields and isinstance(value, list) else value
                              for key, value in values.items() if key in names}
    return Site(**kwargs)


def save_catalog(raw: dict[str, Any]) -> None:
    """The catalog into the database, in one transaction; every record must make a Site (a bad one is refused before anything is
    written), and the table's CHECKs refuse a bad base, language, name or max_pages (nothing is written then either)."""
    made: dict[str, Site] = {}
    for name, values in raw.get("sites", {}).items():
        try:
            made[str(name)] = make_site(dict(values))
        except TypeError as error:
            raise ValueError(f"site {name}: {error}") from None
    columns = ", ".join(f'"{column}"' for column in CATALOG_COLUMNS)
    marks = ", ".join(["%s"] * len(CATALOG_COLUMNS))
    with pg.connection() as conn, conn.transaction():
        conn.execute("DELETE FROM site_catalog")
        conn.execute("DELETE FROM blocked_hosts")
        for name, site in made.items():
            values = {column: getattr(site, column) for column in CATALOG_COLUMNS}
            values["sitemap"] = None if values["sitemap"] is False else DEFAULT_SITEMAP if values["sitemap"] is True else values["sitemap"]
            for field in TUPLE_FIELDS:
                if values[field] is not None:
                    values[field] = list(values[field])
            conn.execute(f"INSERT INTO site_catalog (name, {columns}) VALUES (%s, {marks})", (name, *values.values()))
        for host in sorted(set(raw.get("blocked", ()))):
            conn.execute("INSERT INTO blocked_hosts (host) VALUES (%s)", (host,))
    global _catalog_checked
    _catalog_checked = 0.0


SITES: dict[str, Site] = {}
BLOCKED: frozenset[str] = frozenset()
_catalog_raw: dict[str, Any] | None = None
_catalog_checked = 0.0


def reload_catalog() -> None:
    """Refresh the snapshot when the catalog in the database changed (an edit from another machine); read again at most every
    CATALOG_TTL seconds. Imports never read data."""
    global SITES, BLOCKED, _catalog_raw, _catalog_checked
    if _catalog_raw is not None and time.monotonic() - _catalog_checked < CATALOG_TTL:
        return
    raw = load_config()
    _catalog_checked = time.monotonic()
    if raw != _catalog_raw:
        loaded = {name: make_site(values) for name, values in raw.get("sites", {}).items()}
        SITES = loaded  # (swapped whole: the threads of the run iterate SITES while a request adds a site; clear + update broke their loops)
        BLOCKED, _catalog_raw = frozenset(raw.get("blocked", ())), raw


DEFAULTS = {f.name: f.default for f in fields(Site) if f.default is not MISSING}


def reduced(record: dict[str, Any]) -> dict[str, Any]:
    """A record without the fields that are the defaults of Site: what sites.yaml says."""
    return {key: value for key, value in record.items()
            if key not in DEFAULTS or (tuple(value) if isinstance(value, list) else value) != DEFAULTS[key]}


def catalog_main(args: Namespace) -> None:
    """`catix-docs sites catalog import FILE | export | add NAME KEY=VALUE ... | remove NAME | block HOST | unblock HOST`."""
    action = args.catalog_action
    try:
        raw = load_config()
    except FileNotFoundError:
        raw = {"sites": {}, "blocked": []}
    if action == "import":
        save_catalog(read_yaml(args.file))
        print(f"{len(read_yaml(args.file)['sites'])} sites imported from {args.file}")
        return
    if action == "export":
        print(yaml.safe_dump({"sites": {name: reduced(record) for name, record in raw["sites"].items()}, "blocked": raw["blocked"]},
                             allow_unicode=True, sort_keys=False), end="")
        return
    if action == "add":
        record = {}
        for pair in args.fields:
            key, _, value = pair.partition("=")
            if not _:
                raise SystemExit(f"{pair!r}: write KEY=VALUE (base, language, about, skip, ...; a list or a number as YAML: aliases=[a.example])")
            record[key] = yaml.safe_load(value)
        raw["sites"][args.name] = record
        raw["sites"][args.name].setdefault("skip", "")
    elif action == "remove":
        if raw["sites"].pop(args.name, None) is None:
            raise SystemExit(f"no site {args.name}")
    elif action == "block":
        raw["blocked"] = [*raw.get("blocked", []), args.host]
    elif action == "unblock":
        raw["blocked"] = [h for h in raw.get("blocked", []) if h != args.host]
    save_catalog(raw)
    print(f"{len(raw['sites'])} sites, {len(raw['blocked'])} blocked hosts")


NEW_SITE_SKIP = r"^(tilda|members)/|(^|/)((\w+[-_])?form|thank_?you\w*|test\w*|\w+_test)$"  # (the skip of the sites the wiki's run found)


def new_site_record(url: str, name: str | None = None) -> tuple[str, dict[str, Any]]:
    """The name and the catalog record of a site asked for by a request (POST /sites/new, `catix-docs sites request`): the
    template of the sites the wiki's run found (Tilda's skip, 30 pages, robots.txt, 3 s between requests). The name is the host
    with dashes ('digitalinnopolisdays-ru') unless one is given. Raises ValueError: not an address of a site, a blocked host,
    a host the catalog has (its name: read it again with /sites/parse), a name taken or not of [a-z0-9-]."""
    from catix.docs.sources import crawl

    reload_catalog()
    try:
        parts = urlsplit(url.strip())
        host = (parts.hostname or "").lower().rstrip(".")
    except ValueError:
        host, parts = "", None
    if not parts or parts.scheme not in ("http", "https") or not host or "." not in host:
        raise ValueError(f"{url!r} is not the address of a site: https://host/")
    if any(host == b or host.endswith("." + b) for b in BLOCKED):
        raise ValueError(f"{host} is blocked")
    if known := next((other for other, site in SITES.items() if host in crawl._site_hosts(site)), None):
        raise ValueError(f"{host} is in the catalog already: {known} (POST /sites/parse?sites={known} reads it again)")
    name = name or re.sub(r"^www-", "", host.replace(".", "-"))
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
        raise ValueError(f"{name!r} is not a name of a site: a-z, 0-9 and dashes")
    if name in SITES:
        raise ValueError(f"the name {name} is taken: {SITES[name].base}")
    return name, {"base": f"{parts.scheme}://{host}/", "language": "ru", "about": f"{host}, added by a request",
                  "skip": NEW_SITE_SKIP, "max_pages": 30, "robots": True, "pause": 3}


def request_new_site(url: str, name: str | None = None) -> "parse_requests.Request":
    """Queue a request for a new site (the run adds and reads it). Raises ValueError (new_site_record) or parse_requests.Unavailable."""
    from catix.docs import parse_requests

    name, record = new_site_record(url, name)
    return parse_requests.submit("sites", "new-site", [name], url=record["base"])


@dataclass
class NewSite:
    name: str
    base: str
    pages: int  # read and kept
    documents: int  # the documents its pages link, read
    problems: Counter  # why an address gave no page (the index's `tried`, addresses cut out) -> how many

    def report(self) -> str:
        what = f"{self.name} ({self.base}): {self.pages} pages read, {self.documents} documents"
        return what + (f"; not read: {', '.join(f'{n}× {why}' for why, n in self.problems.most_common())}" if self.problems else "")


def add_site(url: str, name: str | None = None) -> str:
    """Add the site of a request to the catalog (new_site_record's template); its name. The run reads it: its start page is a
    row of the frontier (frontier.seed) and the rest follows the links. It stays in the catalog whatever the read brings: what
    went wrong is the report's (new_site_report), to be handled later (skip, render, profile, ...)."""
    name, record = new_site_record(url, name)
    raw = load_config()
    raw["sites"][name] = record
    save_catalog(raw)
    reload_catalog()
    return name


def new_site_report(name: str) -> NewSite:
    """What the crawl found of a new site: its pages and documents read, and why the addresses that gave no page gave none. The
    start page's title joins the site's `about`."""
    from catix.docs import frontier

    reload_catalog()
    pages, documents, whys, title = frontier.site_counts(name)
    problems = Counter(re.sub(r"https?://\S+", "…", why)[:80] for why in whys)
    if title:
        raw = load_config()
        raw["sites"][name] = {**raw["sites"][name], "about": f"{raw['sites'][name]['about']}: {title}"}  # (as the wiki's run named its sites)
        save_catalog(raw)
        reload_catalog()
    return NewSite(name, SITES[name].base, pages, documents, problems)


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


def get_through(client: httpx.Client, url: str, headers: dict | None = None, pause: float = hosts.PAUSE) -> httpx.Response:
    """The answer for the url, asked again while a bot check answers in its place ('Вы не робот?' of Yandex on timepad, 'Just a
    moment' of Cloudflare): the wall is not the site, and it lets a request through now and then. The last answer is kept
    whatever it is, so a page that names a bot check in its own words is only asked for again, never refused for them. Every
    request waits for its host's turn (hosts.turn: `pause` seconds after the one before)."""
    extra = {"headers": headers} if headers else {}
    hosts.turn(url, pause)
    page = client.get(url, **extra)
    for _ in range(BOT_TRIES - 1):
        if not WALL.search(page.text):
            break
        time.sleep(BOT_PAUSE)
        hosts.turn(url, pause)
        page = client.get(url, **extra)
    return page


class _SitemapAnswer(AbstractWebClientSuccessResponse):
    def __init__(self, page: httpx.Response):
        self.page = page

    def status_code(self) -> int:
        return self.page.status_code

    def status_message(self) -> str:
        return self.page.reason_phrase

    def header(self, case_insensitive_name: str) -> str | None:
        return self.page.headers.get(case_insensitive_name)

    def raw_data(self) -> bytes:
        return self.page.content

    def url(self) -> str:
        return str(self.page.url)


class _SitemapClient(AbstractWebClient):
    """What Ultimate Sitemap Parser asks, through the crawl's client: the bot-check retries of get_through, the site's pause
    after every request, each address once (robots.txt names /sitemap.xml, which is also read as the site's own)."""

    def __init__(self, client: httpx.Client, site: "Site"):
        self.client, self.pause, self.answers = client, PAUSE if site.pause is None else site.pause, {}

    def set_max_response_data_length(self, max_response_data_length: int | None) -> None:
        pass  # (httpx reads the whole answer; USP's own limit bounds what it decompresses)

    def get(self, url: str) -> AbstractWebClientResponse:
        if url not in self.answers:
            try:
                page = get_through(self.client, url)
            except httpx.HTTPError as e:
                self.answers[url] = WebClientErrorResponse(f"{type(e).__name__}: {e}", retryable=False)
            else:
                self.answers[url] = _SitemapAnswer(page) if page.is_success else WebClientErrorResponse(f"{page.status_code} {page.reason_phrase}", retryable=False)
            time.sleep(self.pause)
        return self.answers[url]


def sitemap_pages(site: "Site", client: httpx.Client) -> list[str]:
    """The page addresses a site's sitemaps list, in their order and once each: the sitemaps its robots.txt names (Tilda's
    sitemap-store.xml: the cards of courses and events, that no page links) and its own (Site.sitemap, /sitemap.xml when
    True; the English copy's too), read by Ultimate Sitemap Parser (indexes, gzip, text and RSS sitemaps)."""
    path = site.sitemap if isinstance(site.sitemap, str) else "sitemap.xml"
    roots = [urljoin(site.base, "/robots.txt"), urljoin(site.base, path), *([urljoin(site.base, f"{site.english}/{path}")] if site.english else [])]
    web, found = _SitemapClient(client, site), {}
    for root in roots:
        try:
            tree = SitemapFetcher(url=root, recursion_level=0, web_client=web, quiet_404=True).sitemap()
        except SitemapException as e:
            print(f"  {root}: {e}", flush=True)
            continue
        found.update(dict.fromkeys(page.url for page in tree.all_pages()))
    return list(found)


LIVE_WAIT = 30  # seconds: the longest a page of an app behind a login is given to finish loading
LOGIN_FORM = re.compile(r"""<input[^>]+type=["']?password""", re.I)


class LiveBrowser:
    """One Chromium with the profile of a person who logged in, kept for the whole crawl: a portal that gives a session a few minutes
    lives longer in one browser than in a new one for every page (the pages are opened in one tab, one after another)."""

    def __init__(self, profile: str):
        from playwright.sync_api import Error, sync_playwright

        if not CHROMIUM:
            raise RuntimeError("a site with a profile needs Chromium (chromium, chromium-browser or google-chrome on the PATH)")
        self.profile = profile
        self.playwright = sync_playwright().start()
        try:
            # (Playwright passes --password-store=basic and --use-mock-keychain by default; the plain launch did not, and on a desktop
            #  with a keyring the login cookies of the profile would not decrypt with them)
            self.context = self.playwright.chromium.launch_persistent_context(
                profile, executable_path=CHROMIUM, headless=True, args=["--disable-gpu", "--no-sandbox"],
                ignore_default_args=["--password-store=basic", "--use-mock-keychain"])
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        except Error as e:
            self.playwright.stop()
            raise httpx.TransportError(f"the browser did not start: {str(e).splitlines()[0]}") from e

    def _load(self, url: str) -> str:
        from playwright.sync_api import Error

        try:
            self.page.goto(url, wait_until="commit", timeout=LIVE_WAIT * 1000)
        except Error as e:
            raise httpx.TransportError(f"the browser did not read {url}: {str(e).splitlines()[0]}") from e
        last, still = "", 0
        for second in range(LIVE_WAIT):
            self.page.wait_for_timeout(1000)
            try:
                html = self.page.content()
            except Error:  # (the page is navigating: no document to read yet)
                still = 0
                continue
            still = still + 1 if html == last else 0
            last = html
            if still >= 3 and second >= 4:  # (unchanged for three seconds, and not the empty shell of the first ones)
                break
        return last

    def evaluate(self, script: str) -> str:
        """What a script returns in the page that is open (a promise is waited for)."""
        return self.page.evaluate(script)

    def get(self, url: str) -> str:
        """The page after it stopped changing. Raises when the page asks for a password or did not finish loading (its title is still '{eventName}')."""
        html = self._load(url)
        if re.search(r"<title>[^<]*\{\w+\}", html):  # (the page asked for its data and had no answer yet: once more)
            html = self._load(url)
        if LOGIN_FORM.search(html):
            raise RuntimeError(f"the profile {self.profile} is not logged in: {url} asks for a password")
        if re.search(r"<title>[^<]*\{\w+\}", html):
            raise httpx.TransportError(f"{url} did not finish loading")
        return html

    def close(self) -> None:
        try:
            self.context.close()
        finally:
            self.playwright.stop()


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
        target = urljoin(url, src.group(1))
        hosts.turn(target)
        services = service_catalog(client.get(target).text)
    except httpx.HTTPError:
        return text
    return text.split("## Filter")[0] + catalog_markdown(services) + "\n" if services else text


EXTRAS = {("innohassle", "dashboard"): dashboard_with_catalog}  # (site, page) -> what the page needs besides what the browser shows


def needs_script(page: httpx.Response, headings: str | None = None) -> bool:
    """Whether the browser is to read a page the site sent: its <noscript> asks for JavaScript, or it has next to no words (the
    empty shell of an app, a page of Tilda whose blocks its scripts draw). Not a bot check: the browser does not pass it either."""
    return (page.status_code == 200 and "text/html" in page.headers.get("content-type", "") and not WALL.search(page.text)
            and convert_page(page.text, str(page.url), headings)[3])


class SessionEnded(RuntimeError):
    """The Chromium profile of a site behind a login shows the login: the site is not read until a person logs in again."""


ENDED: dict[str, str] = {}  # site name -> message, for the sites whose session ended in this process since the runner last took them


def conditional_headers(validators: dict) -> dict:
    """The request headers that ask the site to answer 304 when the page is the one read before (ETag, else its date)."""
    if validators.get("etag"):
        return {"If-None-Match": validators["etag"]}
    if validators.get("modified"):
        return {"If-Modified-Since": validators["modified"]}
    return {}


def pause_of(site: "Site") -> float:
    return PAUSE if site.pause is None else site.pause


def get_page(client: httpx.Client, site: "Site", url: str, validators: dict | None = None) -> httpx.Response:
    """The answer for a page: the site's own, or what the browser made of it, as if it were the answer: for every page of an app
    (Site.render), for a page that needs its scripts (needs_script) on any other site. Each request waits for its host's turn."""
    pause = pause_of(site)
    if site.profile:
        profile = profile_of(site)
        hosts.turn(url, pause)
        html = render_live(url, profile)
        if site.signin and re.search(site.signin, html):
            raise SessionEnded(f"the session of the profile {profile} has ended: {url} shows the login")
        return httpx.Response(404 if site.missing and re.search(site.missing, html) else 200, headers={"content-type": "text/html; charset=utf-8", "x-catix-rendered": "1"}, text=html, request=httpx.Request("GET", url))
    headers = {"content-type": "text/html; charset=utf-8", "x-catix-rendered": "1"}
    if not site.render:
        page = get_through(client, url, conditional_headers(validators or {}), pause)
        if page.status_code == 304:
            return page
        if not needs_script(page, site.headings):
            return page
        url = str(page.url)
        try:
            hosts.turn(url, pause)
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
            hosts.turn(url, pause)
            html = render_page(url)
        except NotAPage as e:  # (the site's file as the site sent it: read_page leaves what is not a page)
            return httpx.Response(200, headers={"content-type": e.kind}, request=httpx.Request("GET", url))
    return httpx.Response(200 if html else 404, headers=headers, text=html or "", request=httpx.Request("GET", url))


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

    def __init__(self, url: str, headings: str | None = None) -> None:
        self.url = url
        self.headings = headings  # Site.headings: a class that names a block a heading
        self.video_src = ""  # the file of the <video> the converter is in: its own src, the first <source> with one, else the first data-src of a <source>
        self.depth = 0  # of the element the converter is in
        self.bare: tuple[str, int] | None = None  # (address, depth of its parent) of the last link that wrapped nothing
        self.links: list[tuple[str, str]] = []  # (url, text), those of a <noscript> and a form too (Tilda's redirect block: 'Redirect to
        # URL'; the policy a consent links)
        self.script = False
        self.open: list[_Link] = []  # the <a> the converter is inside

    def visit_element_start(self, ctx: NodeContext) -> dict:
        self.depth += 1
        if ctx.tag_name == "a":
            self.open.append(_Link())
        elif ctx.tag_name == "source" and ctx.parent_tag == "video" and not self.video_src:  # (after visit_video, before the end of the <video>)
            if lazy := ctx.attributes().get("data-src", "").strip():
                self.video_src = urljoin(self.url, lazy)
        elif self.open and ctx.tag_name in BLOCKS:
            self.open[-1].block = True
        return CONTINUE

    def _watch(self, src: str | None, title: str = "") -> str:
        """A link to where a video is watched, `▶ title`: plain() knows it is no words."""
        if not src:
            return ""
        words = re.sub(r"[\[\]]", "", title).strip() or "video"
        self.links.append((src, f"▶ {words}"))
        return f"[▶ {words}]({readable(src)})"

    def _picture(self, src: str, alt: str = "", banner: bool = False) -> str:
        """` ![alt](url) ` of a picture that is content; nothing for a decoration (icons, pixels, counters). A banner after a link that wrapped nothing is in it."""
        url = TILDA_PREVIEW.sub(r"\1static\2/\3", urljoin(self.url, src.strip()))  # (Tilda: the file, not its 20-pixel preview)
        parts = urlsplit(url)
        if (parts.scheme not in {"http", "https"} or IMAGE_SKIP.search(parts.path) or TRACKER.search(url)
                or urldefrag(url)[0] == urldefrag(self.url)[0]):  # (a decoration; no address: a script fills it in later)
            return ""
        if self.open:
            self.open[-1].picture = True
        elif banner and self.bare:  # (a link inside a link: the parser closes the first, an empty one, and wraps the next picture in a copy of it)
            return f" [![{alt}]({readable(url)})]({readable(self.bare[0])}) "
        return f" ![{alt}]({readable(url)}) "

    def _video(self, ctx: NodeContext) -> str:
        """The link a video or a frame is replaced by (a frame that is not a video, a map, a form, is gone): the words of a frame
        are for a browser that has none."""
        a = ctx.attributes()
        if ctx.tag_name == "iframe":
            return self._watch(video_url(urljoin(self.url, (a.get("src") or a.get("data-src") or "").strip())), a.get("title", ""))
        lazy = a.get("data-src", "").strip()  # (a lazy one)
        source, self.video_src = self.video_src or (urljoin(self.url, lazy) if lazy else ""), ""
        return self._watch(source or None, a.get("title", ""))

    def visit_video(self, ctx: NodeContext, src: str | None, *rest) -> dict:
        self.video_src = src or ""  # (its own src or that of its first <source>: a lazy data-src is read in visit_element_start)
        return CONTINUE

    def _lead(self, ctx: NodeContext) -> str:
        """What the converter cannot see in a block, written at its start: the video it plays (Tilda: data-videolazy-id; Bitrix: a div with
        data-source) as a link to where it is watched, a banner of a style and the picture of a Tilda block (data-original of a div) as a picture."""
        a = ctx.attributes()
        if a.get("data-videolazy-id") and a.get("data-videolazy-type") in {"youtube", "vimeo"}:
            vid = a["data-videolazy-id"]
            lead = self._watch(f"https://www.youtube.com/watch?v={vid}" if a["data-videolazy-type"] == "youtube" else f"https://vimeo.com/{vid}")
        else:
            lead = self._watch(next(filter(None, (video_url(urljoin(self.url, a[k].strip())) for k in VIDEO_SOURCES if a.get(k))), None))
        banner = a.get("data-original") or (found.group(1) if (found := BANNER.search(a.get("style", ""))) else "")
        return lead + (self._picture(banner, banner=True) if banner.strip() else "")  # (Tilda: the 20-pixel preview in the style, the picture in data-original)

    def visit_element_end(self, ctx: NodeContext, output: str) -> dict:
        tag = ctx.tag_name
        self.depth -= 1
        if self.bare and self.depth < self.bare[1]:
            self.bare = None  # (the parent of the empty link is closed)
        if tag == "a" and self.open:
            self.open.pop()
        if tag in {"iframe", "video"}:
            return _custom(self._video(ctx))
        if tag in UNWRITTEN:
            if tag == "noscript" and "javascript" in output.lower():
                self.script = True  # ('You need to enable JavaScript to run this app.', 'У вас отключено исполнение JavaScript')
            return _custom("")
        if tag in {"img", "source", "br", "hr", "input", "meta", "link"}:
            return CONTINUE
        lead = self._lead(ctx) if tag != "a" else ""  # (a link has its own in visit_link: the converter has written it by now)
        if lead:
            rest = output.lstrip()
            output = output[:len(output) - len(rest)] + lead + "\n" + rest
        if self.headings and re.search(self.headings, ctx.attributes().get("class", "")):  # (a block the site names a heading)
            result = self.visit_heading(ctx, 2, output)
            if result is not CONTINUE:
                return result
        return _custom(output) if lead else CONTINUE

    def visit_text(self, ctx: NodeContext, text: str) -> dict:
        if self.open:
            self.open[-1].words += text
        return CONTINUE

    def visit_link(self, ctx: NodeContext, href: str, text: str, title: str | None = None) -> dict:
        href = urljoin(self.url, href.strip())  # (the converter resolves `href=" /a "`, not `href=" https://… "`: the browser does both)
        link = self.open[-1] if self.open else _Link(words=text, picture=True)
        if lead := self._lead(ctx):  # (Tilda: a link that is a banner, the picture in its data-original)
            text = f"{lead} {text}"
            link.picture = True
        words = re.sub(r"\s+", " ", re.sub(r"</?[a-z][^>]*>", " ", text, flags=re.I)).strip()  # (a site that writes <p> as text: not in a link)
        if SCRIPT_HREF.search(re.sub(r"[\s*]", "", unquote(href))):  # (a script, not a link; media writes it 'jav * ascript:void(0)')
            return _custom(words)
        self.links.append((href, re.sub(r"\s+", " ", re.sub(r"\*\*|__", "", MD_IMAGE.sub("", words))).strip()))
        if not link.words.strip() and not link.picture:
            if urlsplit(href).scheme in {"http", "https"}:
                self.bare = (href, self.depth - 1)
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
        attributes = ctx.attributes()
        if any(attributes.get(k, "").isdigit() and int(attributes[k]) <= SMALL for k in ("width", "height")):
            return _custom("")  # (a pixel, an icon)
        alt = re.sub(r"[\[\]]", "", re.sub(r"\s+", " ", alt or title or "")).strip()
        # the file of a lazy picture whose src is a preview (the converter takes data-src or a srcset itself only for a missing or a data: src)
        src = next(filter(None, (attributes.get(k, "").strip() for k in LAZY_SOURCES)), "") or src
        if src.startswith("data:"):
            if self.open and alt:
                self.open[-1].picture = True  # (its alt, the words of the link: inline_data_media)
            return CONTINUE
        return _custom(self._picture(src, alt))

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


@functools.lru_cache(maxsize=2)  # (get_page reads a page to tell whether it needs its scripts, read_page reads it again)
def convert_page(html: str, url: str, headings: str | None = None) -> tuple[str, str, tuple[tuple[str, str], ...], bool]:
    """(title, markdown lines, links, whether it needs its scripts) of a page; `headings`: Site.headings. A page needs its scripts
    when its <noscript> asks for JavaScript or it has fewer than MIN_WORDS words: the HTML is an empty shell."""
    page = _Page(url, headings)
    try:
        result = convert(html, _options(url), visitor=page)
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


def page_url(site: Site, url: str) -> str:
    """A page's fetch/cache address: an explicit alias is the same path on the primary host, not a second site.
    An unrelated host (including an unconfigured subdomain) or an unsafe address has no page address here."""
    try:
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"} or parts.port is not None or parts.username or parts.password or not parts.hostname:
            return ""
    except ValueError:
        return ""
    host = parts.hostname.lower().rstrip(".")
    base = urlsplit(site.base)
    if host not in {base.hostname, *(alias.lower().rstrip(".") for alias in site.aliases)}:
        return ""
    if host != base.hostname and any(host == urlsplit(other.base).hostname for other in SITES.values()):
        return ""  # a separately configured primary host is not somebody else's alias
    return canonical(parts._replace(netloc=base.netloc).geturl())


def _taken(site: Site, url: str) -> bool:
    reload_catalog()
    target = page_url(site, url)
    parts = urlsplit(target)
    if not target or DOC.search(parts.path) or NOT_PAGE.search(parts.path):
        return False
    hosts = {(urlsplit(url).hostname or "").lower().rstrip("."), parts.hostname or ""}
    if any(host == blocked or host.endswith("." + blocked) for host in hosts for blocked in BLOCKED):
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


def client() -> httpx.Client:
    """The HTTP client of the crawl: every page as a new visitor sees it (no cookies)."""
    no_cookies = CookieJar(policy=DefaultCookiePolicy(allowed_domains=[]))
    return httpx.Client(headers=regulations.HEADERS, timeout=60, follow_redirects=True, cookies=no_cookies)


def page_target(site: Site, link: str) -> str:
    """The address under which the crawl reads a link of the site (page_url), a page of a list (Site.listing) after its first with its query; '' when it is none."""
    target = page_url(site, link)
    if not target:
        return ""
    number = re.search(rf"[?&]{site.listing}=(\d+)", link) if site.listing else None
    return target + (f"?{site.listing}={number.group(1)}" if number and number.group(1) != "1" else "")


ROBOTS_TTL = timedelta(days=1)
_robots: dict[str, tuple[datetime, RobotFileParser | None]] = {}


def robots(site: Site, client: httpx.Client) -> RobotFileParser | None:
    """robots_of, asked at most once a day for a site."""
    now = datetime.now(timezone.utc)
    if (cached := _robots.get(site.base)) and now - cached[0] < ROBOTS_TTL:
        return cached[1]
    rules = robots_of(site, client)
    _robots[site.base] = (now, rules)
    return rules


COMMON_TTL = 3600  # seconds
_common: dict[str, tuple[float, dict[str, set[str]]]] = {}


def common(name: str) -> dict[str, set[str]]:
    """The lines the pages of a site repeat, per language (boilerplate), from the pages kept; read again every COMMON_TTL seconds
    and when compile_site rebuilds the site."""
    from catix.docs import frontier

    if (cached := _common.get(name)) and time.monotonic() - cached[0] < COMMON_TTL:
        return cached[1]
    site, rows = SITES[name], frontier.live_pages(name)
    found = {lang: boilerplate([row.text for row in rows if row.text and language_of(site, row.slug or "") == lang]) for lang in ("ru", "en")}
    _common[name] = (time.monotonic(), found)
    return found


LIVE_STATES = ("ok", "missing")  # a page kept in the search


def read_page(client: httpx.Client, row: "Row") -> bool:
    """Read the page of one address of the frontier and note what came of it in its row (frontier.save): the text and the hash,
    the links to other addresses (frontier.set_links) and the new ones among them (frontier.add). Whether the documents of the
    site may have changed: a page whose text changed, or that came into the search or left it.

    A new address that gives no page (a 404, a file, the words of another page, robots.txt, a host that does not answer) is
    `tried` and asked again after RETRY. A new address the site sends to another one is no page of its own either: the page it is
    sent to is added in its place. A page the search has (`ok`) that answers 404 is `missing`, kept until the next read finds it
    so too (a site down for an hour, a menu its scripts did not draw), then `gone`. A page that comes back with less than half
    of its own words is kept as it was until the next read finds it so too."""
    from catix.docs import frontier
    from catix.docs.frontier import Found, Link
    from catix.docs.sources import crawl

    site, url, live = SITES[row.site], row.url, row.state in LIVE_STATES
    now = datetime.now(timezone.utc)
    if crawl.provider(url, page=True) != row.site or not _taken(site, url):
        frontier.save(row, state="gone", why="not taken", next_at=None)
        return live
    if (rules := robots(site, client)) and not rules.can_fetch(regulations.HEADERS["User-Agent"], url):
        frontier.save(row, state="tried", why="robots.txt disallows it", next_at=frontier.later(RETRY))
        return live
    slug = row.slug or slug_of(site, url)
    try:
        if DOWNLOAD.search(urlsplit(url).path):
            hosts.turn(url, pause_of(site))  # (do not GET a potentially large binary just to classify it as an archive)
            head = client.head(url)
            kind = ARCHIVE_TYPES.get(head.headers.get("content-type", "").split(";", 1)[0].lower())
            if head.status_code == 200 and kind and crawl.provider(url):
                frontier.save(row, kind="document", doc_key=doc_key(row.site, url), ext=kind, next_at=now, priority=frontier.NEW)
                return False
        conditional = bool(
            row.validators and row.state == "ok" and row.short_words is None and row.text is not None and (row.site, slug) not in EXTRAS
            and "?" not in url and row.read_at and now - row.read_at < REVALIDATE)
        resp = get_page(client, site, url, row.validators if conditional else None)
    except httpx.HTTPError as e:
        print(f"  FAILED {url}: {e}")
        if live:
            frontier.save(row, next_at=frontier.later(frontier.SOON))
        else:
            frontier.save(row, state="tried", why=f"{type(e).__name__}: {str(e)[:200]}", next_at=frontier.later(RETRY))
        return False
    if resp.status_code == 304:
        frontier.save(row, read_at=now)
        return False
    if resp.status_code == 404 or "text/html" not in resp.headers.get("content-type", ""):
        why = "404" if resp.status_code == 404 else f"not a page ({resp.headers.get('content-type', 'no type')})"
        if row.state == "ok":
            print(f"  {slug}: {why}, kept until the next read finds it so", flush=True)
            frontier.save(row, state="missing", why=why, next_at=frontier.later(frontier.SOON))
            return False
        if row.state == "missing":
            frontier.save(row, state="gone", why=why, text=None, next_at=frontier.later(frontier.PAGE_EVERY))
            return True
        frontier.save(row, state="tried", why=why, next_at=frontier.later(RETRY))
        return False
    if resp.status_code != 200:
        print(f"  {url}: {resp.status_code}")
        if live:
            frontier.save(row, next_at=frontier.later(frontier.SOON))
        else:
            frontier.save(row, state="tried", why=str(resp.status_code), next_at=frontier.later(RETRY))
        return False
    moved = str(resp.url)
    if row.state in ("new", "tried") and address(moved) != row.address:  # (a known page that moved stays the page it was)
        print(f"  {url}: sent to {moved}", flush=True)
        frontier.save(row, state="tried", why=f"sent to {moved}", next_at=frontier.later(RETRY))
        if (other := crawl.provider(moved, page=True)) and (target := page_url(SITES[other], moved)):
            frontier.add([Found(target, other, "page")], by=row)
        return False
    title, text, links = read(resp.text, str(resp.url), site.headings)
    if WALL_TITLE.search(title):  # (a bot check that let none of the asks of get_page through, not the site's page)
        print(f"  {url}: a bot check answers in its place", flush=True)
        if live:
            frontier.save(row, next_at=frontier.later(frontier.SOON))
        else:
            frontier.save(row, state="tried", why="a bot check", next_at=frontier.later(RETRY))
        return False
    if site.private:
        text = re.sub(site.private, "", text, flags=re.M).rstrip() + "\n"  # (the person who is logged in is not the page's)
    if site.bare:
        links = [(languaged(site, link, str(resp.url)), anchor) for link, anchor in links]
        text = re.sub(r"(!\[[^\]]*\]\([^)\s]*\))|(?<=\]\()https?://[^)\s]+", lambda m: m.group(1) or languaged(site, m.group(), str(resp.url)), text)  # (not a picture)
    if extra := EXTRAS.get((row.site, slug)):
        text = extra(client, resp.text, str(resp.url), text)
    spelled: dict[str, str] = {}
    contexts = {spelled.setdefault(u, address(u)): c for u, c in contexts_of(text).items()}
    web = [(link, anchor) for link, anchor in links if urlsplit(link).scheme in ("http", "https")]
    dsts = [spelled.get(link) or spelled.setdefault(link, address(link)) for link, _ in web]
    archives = frontier.known_documents(dsts)
    found, written = [], []
    for (link, anchor), dst in zip(web, dsts):
        written.append(Link(dst, anchor, contexts.get(dst, "")))
        if (DOC.search(urlsplit(link).path) or dst in archives) and (other := crawl.provider(link)):
            found.append(Found(canonical(link), other, "document"))
        elif (other := crawl.provider(link, page=True)) and (target := page_target(SITES[other], link)):
            found.append(Found(target, other, "page"))
    frontier.set_links(row.address, written)
    frontier.add(found, by=row)
    if "?" in url and not DOWNLOAD.search(urlsplit(url).path):  # (a page of a list: its links are taken, it is not kept)
        frontier.save(row, state="ok", why=None, text=None, read_at=now)
        return False
    sha = hashlib.sha256(plain(text).encode()).hexdigest()  # (the words: a new link or picture is not a new version)
    if other := frontier.same_words(row.site, sha, row.address):  # the page read under another address (Tilda: '/Vue-js-framework' is '/vue-js-framework')
        print(f"  {slug}: the words of {other}", flush=True)
        if row.state == "ok":
            frontier.save(row, state="gone", why=f"the words of {other}", text=None, next_at=frontier.later(frontier.PAGE_EVERY))
            return True
        frontier.save(row, state="tried", why=f"the words of {other}", next_at=frontier.later(RETRY))
        return live
    validators = {} if "x-catix-rendered" in resp.headers else {k: v for k, v in (("etag", resp.headers.get("etag")), ("modified", resp.headers.get("last-modified"))) if v}
    before = row.text
    if live and row.sha256 == sha:  # (the same words, other links and pictures: the short read was the wrong one)
        frontier.save(row, state="ok", why=None, validators=validators, read_at=now, short_words=None, text=text)
        return text != before
    if row.state == "ok" and before and row.short_words is None:  # a read that went wrong (a stub, an app's empty shell, half a page)
        words = common(row.site)[language_of(site, slug)]  # writes over the page and the cards drop what it said: the next read has to find it so too
        was, now_words = own_words(site, before, words), own_words(site, text, words)
        if was >= MIN_WORDS and now_words < SHORT_READ * was:
            print(f"  {slug}: {now_words} words of its {was}, kept as it was until the next read finds it so", flush=True)
            frontier.save(row, short_words=now_words, next_at=frontier.later(frontier.SOON))
            return False
    if not row.slug and frontier.slug_taken(row.site, slug):  # (two paths, one slug; an alias is the same page, not a collision)
        slug = f"{slug[:50]}-{hashlib.sha1(url.encode()).hexdigest()[:6]}"
    frontier.save(row, state="ok", why=None, slug=slug, title=title, text=text, sha256=sha, fetched_at=now, read_at=now, validators=validators, short_words=None)
    print(f"  {slug}: {'changed' if before else 'new'}, {len(text)} chars", flush=True)
    return True


def read_listing(client: httpx.Client, row: "Row") -> bool:
    """Read the listing of a site: the pages its sitemaps list and the pages its browser lists (Site.discover; no link leads to
    them). They are linked from the listing, so they stay as long as it does. Always False: no text of its own."""
    from catix.docs import frontier
    from catix.docs.frontier import Found, Link

    site = SITES[row.site]
    locs: list[str] = []
    if site.sitemap:
        if not (listed := sitemap_pages(site, client)):
            print(f"  {row.site}: no sitemap")
        locs += [repaired(site, loc) for loc in listed]
    if site.discover:  # (the pages no link leads to: the browser lists them)
        render_live(site.base, profile_of(site))
        locs += [urljoin(site.base, path) for path in json.loads(LIVE[profile_of(site)].evaluate(site.discover))]
        print(f"  {row.site}: {len(locs)} pages listed")
    found, written = [], []
    for loc in dict.fromkeys(locs):
        if (target := page_target(site, loc)) and _taken(site, loc):
            found.append(Found(target, row.site, "page"))
            written.append(Link(address(target)))
    frontier.set_links(row.address, written)
    frontier.add(found, by=row)
    frontier.save(row, state="ok", why=None, read_at=datetime.now(timezone.utc))
    return False


def entries(site: Site) -> list[str]:
    """The pages a site shows its new pages on: its feeds (Site.feeds), its start page (in each language) when it names none."""
    if site.feeds:
        return list(dict.fromkeys(urljoin(site.base, path) for path in site.feeds))
    return [site.base, *([urljoin(site.base, f"{site.english}/")] if site.english else [])]


LINKED_DOC = re.compile(r"\[([^\]]*)\]\((https?://[^)\s]+)\)")
PICTURE = re.compile(r"!\[([^\]]*)\]\([^)\s]*\)")


def links_of(text: str) -> list[tuple[str, str]]:
    """(text, address) of the links of a page of the bundle. A picture that is a link (`[![](cover.png)](rules.pdf)`: Tilda's
    covers of the collections of edu) is a link whose text is the picture's alt: LINKED_DOC alone took the picture's address
    for the link's and lost the document."""
    return LINKED_DOC.findall(PICTURE.sub(lambda m: m.group(1), text))


def _words(markdown: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"^[#*\-\s]+|\*+$|\*\*|__", "", plain(markdown))).strip()  # (and the asterisk of a footnote: 'программ*')


def contexts_of(text: str) -> dict[str, str]:
    """What each document a page links belongs to, read from the page as markdown, not from the markup of one site (a
    regular expression over the HTML of sveden would break with a change of its classes, and it took the links its comments hide):
    a link in a table is '<the line before the table> — <the first cell of its row> — <the header of its column>'
    (sveden/education: 'программа бакалавриата: 09.03.01 … — 2025 — Рабочие программы дисциплин (модулей)': a link
    whose words are '2025' or 'Учебный план' says nothing alone); one in a list or a paragraph, the last line of words
    before it (a heading, the header of a panel: 'программа магистратуры 09.04.01 …'; a line of words with a link in it
    too: the programme of further education its link names). The canonical
    address -> its context; a document the page links twice keeps the first."""
    found: dict[str, str] = {}
    caption, header = "", None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if header is None:
                header = [_words(cell) for cell in cells]
            elif not all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells if cell):
                row = _words(cells[0])
                for i, cell in enumerate(cells):
                    for _, url in links_of(cell):
                        found.setdefault(canonical(url), " — ".join(part for part in (caption, row if i else "", header[i] if i < len(header) else "") if part))
            continue
        header = None
        if links := links_of(line):
            for _, url in links:
                found.setdefault(canonical(url), caption)
            if len(re.findall(r"[^\W\d_]{3,}", re.sub(r"!?\[[^\]]*\]\([^)]*\)", " ", line))) >= 3:  # (words around a link: 'Программа
                caption = _words(line)[:400]  # дополнительного профессионального образования [«Инженерия ИИ»](…)', the caption of the links under it)
        elif re.search(r"[^\W_]", words := _words(line)):  # (not a line of a dash: an empty cell)
            caption = words[:400]
    return {url: context for url, context in found.items() if context}


def docs() -> dict[str, dict]:
    """The documents the sites link, as regulations.all_docs wants them: a file several sites link is one row of the frontier,
    one document (the key of the row, frontier.add / the import), not one a site."""
    from catix.docs import frontier
    from catix.docs.sources import crawl

    reload_catalog()
    found: dict[str, dict] = {}
    for row in frontier.documents():
        if row.doc_key in regulations.DOCS or crawl.provider(row.url) is None:
            continue  # (one of DOCS is read as that; a subdomain or a host blocked since is not the catalog's)
        file = unquote(urlsplit(row.url).path.rsplit("/", 1)[-1])
        stem = re.sub(r"[_]+", " ", file.rsplit(".", 1)[0]).strip()
        anchor = row.anchor
        if re.search(r"(?i)\.(pdf|docx?|xlsx?|pptx?|rtf|odt)$", anchor):  # the link says the file's name (help: 'Приказ ад-01.2019.12.23 регламент_процесса_….pdf')
            anchor = re.sub(r"_+", " ", anchor.rsplit(".", 1)[0]).strip()
        title = anchor if len(anchor) >= 12 and not re.fullmatch(r"(?i)(скачать|здесь|тут|download|here|подробнее|ссылк\w*)", anchor) else stem
        title = re.sub(r"\s+", " ", re.sub(r"\s*\(\d\)$", "", regulations.SIGNED.sub("", title))).strip()  # ('… 2025 год (2)': the second copy of a file)
        context = row.context
        if context and (len(title) < 30 or re.fullmatch(r"[\d\s./()–-]+", title) or title.lower().startswith(("учебный план", "календарный", "рабочая программа"))):
            title = f"{context[:220]} — {title}"  # ('Учебный план', '2025': the programme and the year are the table's, contexts_of)
        linking = [SITES[n] for n in row.linking_sites if n in SITES] or [SITES[row.site]]
        found[row.doc_key] = {
            "title": title, "url": row.url, "section": f"site/{row.site}", "ext": row.ext or file.rsplit(".", 1)[-1].lower(),
            **({"context": context} if context else {}),
            **({"audience": [a for a in AUDIENCES if any(a in s.audience for s in linking)]} if all(s.audience for s in linking) else {}),  # (the regulations of help are for the staff, as its pages)
            **({"unlisted": row.unlinked_since.isoformat()} if row.unlinked_since else {})}
    return found


def doc_key(name: str, url: str) -> str:
    """The key of a document of a site: the site, the address (canonical) and the name of its file."""
    stem = re.sub(r"[_]+", " ", unquote(urlsplit(url).path.rsplit("/", 1)[-1]).rsplit(".", 1)[0]).strip()
    return f"site-{name}-" + hashlib.sha1(url.encode()).hexdigest()[:8] + "-" + (latin(stem)[:40].strip("-") or "doc")


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


def address(url: str) -> str:
    """The spelling under which the pages and the links to them are compared; a link to another host of a site (Site.aliases)
    is compared as a link to the site ('university.innopolis.ru/en/about/' is 'innopolis.university/en/about/'); a page of a list
    after the first (Site.listing: '?page=2') is an address of its own, as page_target reads it."""
    reload_catalog()
    spelled = canonical(urldefrag(url)[0]).rstrip("/")
    owner, target = next(((site, target) for site in SITES.values() if (target := page_url(site, url))), (None, ""))
    found = target.rstrip("/") if target else spelled
    if owner and owner.listing and (number := re.search(rf"[?&]{owner.listing}=(\d+)", url)) and number.group(1) != "1":
        found += f"?{owner.listing}={number.group(1)}"
    return found


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


def shared_path(site: Site, name: str, lang: str) -> str:
    return f"{ROOT}/{name}/_shared" if lang == site.language else f"{ROOT}/{name}/_shared-{lang}"


def shared_document(name: str, lang: str, body: str, at: str) -> Document:
    """The lines every page of a site repeats (menu, footer, contacts), once, as a page of its own: the pages lose them, the search
    keeps them, and finds them in one place instead of in a copy per page."""
    site = SITES[name]
    host = urlsplit(site.base).netloc
    title = f"Общие блоки сайта {host}: меню, шапка, подвал, контакты" if lang == "ru" else f"Blocks shared by the pages of {host}: menu, header, footer, contacts"
    sha = hashlib.sha256(plain(body).encode()).hexdigest()[:12]
    meta = {"type": "page", "title": title,
            "description": "The menu, header, footer and contact lines that every page of the site repeats, kept once.",
            "resource": site.base, "tags": ["site", "menu", "footer", "contacts"], "audience": list(site.audience or AUDIENCES),
            "source_kind": "website", "language": lang, "section": f"site/{name}",
            "sources": [{"resource": site.base, "id": sha, "title": title, "last_modified": at}],
            "generated": {"by": f"{PRODUCER} sites (code: the lines the pages repeat)", "at": at}, "status": "draft"}
    return Document(shared_path(site, name, lang), meta, f"# {title}\n\n{body}\n\n# Citations\n\n1. [{host}]({site.base}), read {at[:10]}\n")


def compile_site(name: str) -> list[Document]:
    """Every page of a site read -> its document, by code alone (its description: its first sentence); a page gone from its site is
    no document. The links of a page stay the addresses of the site."""
    from catix.docs import frontier

    reload_catalog()
    _common.pop(name, None)
    site = SITES[name]
    entries: dict[str, dict] = {}
    shared: dict[str, list[str]] = {}  # language -> the lines its pages repeat, in the order they come
    rows = [row for row in frontier.live_pages(name) if row.slug and row.sha256]
    texts = {row.slug: row.text for row in rows}
    pages = {row.slug: {"url": row.url, "title": row.title or row.url, "sha256": row.sha256, "audience": row.audience,
                        "fetched_at": row.fetched_at.astimezone(timezone.utc).isoformat(timespec="seconds") if row.fetched_at else ""}
             for row in rows}
    common = {lang: boilerplate([t for slug, t in texts.items() if language_of(site, slug) == lang]) for lang in {"ru", "en"}}  # (each language has its menu)
    same = Counter(p["title"] for p in pages.values())  # (a title that five pages share names none of them: the template's, 'Шапка')
    ends = Counter(m.group() for p in pages.values() if (m := re.search(r"\s[|—–-]\s[^|—–]{3,}$", p["title"])))
    suffix = next((end for end, n in ends.most_common(1) if n >= max(5, len(pages) / 2)), None)  # (the name of the site after the page's: ' — Центр технологий ... мехатроники')
    for slug, p in sorted(pages.items()):
        if p["title"].startswith("Copy of "):
            continue  # (Tilda's copy of a page, left unpublished: 'Copy of Гасников Александр Владимирович')
        lang = language_of(site, slug)
        for line in texts[slug].splitlines():
            if line in common[lang] and line not in shared.setdefault(lang, []):
                shared[lang].append(line)
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
        entries[slug] = {"page": p, "title": title, "lang": lang, "lines": lines}
    out: list[Document] = []
    for lang, lines in sorted(shared.items()):
        pages_in = [e["page"] for e in entries.values() if e["lang"] == lang]
        if lines and pages_in:
            out.append(shared_document(name, lang, "\n\n".join(lines), max(p["fetched_at"] for p in pages_in)))
    for slug, e in sorted(entries.items()):
        p, title, lang = e["page"], e["title"], e["lang"]
        body = "\n\n".join(e["lines"])
        year = year_of(site, slug, title, body)
        past = year if year and year < datetime.now(timezone.utc).year else None  # (the year it is about is over)
        audience = [str(a) for a in p.get("audience") or site.audience or AUDIENCES]  # (everyone, unless a person named the readers of the page (sport/faq: students) or of the site)
        meta = {"type": "page", "title": title, "description": first_sentence(title, plain(body)), "resource": p["url"],
                "audience": audience, "source_kind": "website", "language": lang, "section": f"site/{name}",
                "sources": [{"resource": p["url"], "id": p["sha256"][:12], "title": title,
                             "last_modified": f"{past}-01-01T00:00:00+00:00" if past else p["fetched_at"]}],  # (the day of the page, not of the crawl: the search says 'date' of it)
                "generated": {"by": f"{PRODUCER} sites", "at": p["fetched_at"]}, "status": "draft"}
        if past:
            meta["stale_after"] = f"{past + 1}-01-01T00:00:00+00:00"  # (the search warns: may be outdated)
            body = PAST_NOTE[lang].format(past) + "\n\n" + body
        if shared.get(lang):
            body += "\n\n" + SHARED_NOTE[lang].format(shared_path(site, name, lang))
        out.append(Document(f"{ROOT}/{name}/{slug}", meta, f"# {title}\n\n{body}\n\n# Citations\n\n1. [{title}]({p['url']}), read {p['fetched_at'][:10]}\n"))
    print(f"{name}: {len(out)} documents")
    return out


def compile_all() -> tuple[list[Document], tuple[str, ...]]:
    """The documents of every site (compile_site). The second value: the prefixes of the sites with no page read here (a site
    behind a login, read by the person's browser elsewhere): their documents stay as they are."""
    from catix.docs import frontier

    reload_catalog()
    out: list[Document] = []
    keep: list[str] = []
    for name in SITES:
        if not frontier.has_pages(name):
            keep.append(f"{ROOT}/{name}/")
            print(f"{name}: no page read here, its documents kept as they are")
            continue
        out += compile_site(name)
    print(f"{len(out)} documents of the sites")
    return out, tuple(keep)


def main(args: Namespace) -> None:
    cmd = args.action
    if cmd == "request":
        try:
            request = request_new_site(args.url, args.name)
        except ValueError as e:
            raise SystemExit(str(e)) from None
        print(f"request {request.describe()} queued: `catix-docs run` adds and reads it")
    elif cmd == "status":
        from catix.docs import frontier

        frontier.status()
    elif cmd == "unvisited":
        from catix.docs import frontier

        frontier.unvisited(args.names, args.summary, args.only)
    elif cmd == "catalog":
        catalog_main(args)
