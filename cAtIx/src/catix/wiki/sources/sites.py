"""The sites of the university and its services as a source of the bundle: innopolis.university (the university's own
site, every page in Russian and English; of its disclosure section /sveden/ sveden.py reads the documents, this the text of
the pages: the staff, the structure), apply.innopolis.university (for applicants: programmes, admission, grants, olympiads;
Russian), campuslife.innopolis.ru
(student life: the handbook, the FAQ, scholarships, clubs; English), hotel.innopolis.university (the campus and its
dormitories; Russian), new.innopolis.university/en/ (international applicants; English), media.innopolis.university (the
news and events), stc.innopolis.university (IT courses), edu.innopolis.university (programmes for schools and teachers),
innopolis.com (the city and its special economic zone; Russian and English), and the sites of the university's units and
projects the pages link most (career, corporate, dovuz, progmatica, the college, the dissertation council, ...; see SITES).

    catix-wiki sites fetch [SITE ...]   # the pages of every site (or of those named) -> raw/sites/<site>/ (one request every Site.pause seconds); the number that changed
    catix-wiki sites compile    # raw/sites -> wiki/raw/sites/<site>/<slug>.md
    catix-wiki sites status     # pages and documents found on every site

A page's text is kept as the site shows it: the program turns the markup into markdown and drops what every page of the
site repeats (menus, footers); no model is asked: the description is the page's first sentence. The documents a site
links (PDF, DOCX: the rules of the dormitories, their prices) go the way of the regulations (regulations.py, which asks
`docs()`): wiki/raw/regulations/, quoted by clause, `source_kind: official-document`. The pages themselves are `website`.
Every run reads all pages again and compares their text: these sites say nothing reliable about changes.
"""

import asyncio
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
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from http.cookiejar import CookieJar, DefaultCookiePolicy
from urllib.parse import parse_qs, quote, unquote, urldefrag, urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx
import websockets

from catix.wiki.compile import AUDIENCES, PRODUCER, yaml_value
from catix.wiki.paths import DOCS, RAW
from catix.wiki.sources import regulations
from catix.wiki.sources.rpd import latin

ROOT = RAW / "sites"
FOLDER = "sites"
PAUSE = 2  # seconds between requests
MAX_PAGES = 60  # per site: the crawl follows the links of the site, this stops a calendar or a catalogue from running away
DOC = re.compile(r"\.(pdf|docx?|rtf)$", re.I)
MIN_WORDS = 10  # a page with fewer words (after the shared lines) is a page of pictures and buttons; a heading and a few links to its sections is a page


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
    render: bool = False  # the site is an app: its HTML is an empty shell, the text comes from scripts (a headless browser runs them)
    robots: bool = False  # the pages its robots.txt disallows are not taken (Tilda lists there the pages it does not publish: tests, old webinars)
    pause: float | None = None  # seconds between requests, PAUSE when None (innopolis.com asks for 10: Crawl-delay)
    headings: str | None = None  # the classes of a block that is a heading on a site that writes no <h2> (innopolis.com: <div class="article__title">)
    bare: bool = False  # a link without a language is the page in the language of the page it is on (innopolis.com writes '/media/news/x', '/services')
    listing: str | None = None  # the query that turns the pages of a list (innopolis.com: '?page=2'): they are read for their links, not kept
    end: str | None = None  # where the text of a page ends and the site's blocks of the day it was read begin (media: 'Новости по теме')
    drop: str | None = None  # the lines of a page that lead to the next post, not its text (robotics: 'Дальше', the next post's name)
    profile: str | None = None  # the environment variable that names a Chromium profile a person logged in to: the site is behind a login, its pages are read as that person sees them
    private: str | None = None  # what the pages show of the person who is logged in (name, mail, balance, notifications): cut from every page before anything is kept
    aliases: tuple[str, ...] = ()  # other hosts of the site, an old name or a mirror: a link to one leads to the site's page of the same path, when there is one


TILDA = r"^(tilda|members)/|(^|/)((\w+[-_])?form|thank_?you\w*|test\w*|\w+_test)$"  # (the forms, their thank-you pages and the tests of a Tilda site: no text; a 'page123.html' is a page: the defences of dissovet)
BITRIX = r"(^|/)(search|personal|auth|login|bitrix|upload|local|include)(/|$)|print"


def only(*sections: str) -> str:
    """The skip of a site that is a corner of innopolis.university's Bitrix (career, corporate): every path but its own sections."""
    return rf"^(?!({'|'.join(sections)})(/|$))[^/]+"


SITES = {
    "university": Site("https://innopolis.university/", "ru", "the university's own site: its units, centres, programmes, campus, science, contacts",
                       r"^(en/)?(search|lk|form|personal|auth|login|bitrix|upload|filespublic|files|local|include)(/|$)|print",
                       sitemap=False, max_pages=3000, english="en", aliases=("university.innopolis.ru",)),  # (its old name: the pages link it)
    "apply": Site("https://apply.innopolis.university/", "ru", "admission to Innopolis University: programmes, the rules and dates of admission, grants, olympiads, quotas",
                  r"^(en/)?(search|personal|auth|login|bitrix|upload|local|include)(/|$)|print", max_pages=1500, aliases=("apply.innopolis.ru",)),  # (its /en/ is the Russian text again)
    "campuslife": Site("https://campuslife.innopolis.ru/", "en", "student life at Innopolis University: handbook, FAQ, scholarships, clubs, services",
                       r"_old\b|^page\d+\.html$|^tilda/", dated=True),  # (past events are taken: the wiki is their record; an old copy of a page is not)
    "innohassle": Site("https://innohassle.ru/", "en", "InNoHassle, the student ecosystem of Innopolis University made by the one-zero-eight community: clubs and their leaders, scholarship, room-booking rules, sport, maps, music room",
                       r"(^|/)(admin|account|auth|forms|drafts|submissions|profile|trainer|print|scan)(/|$)|^guard/(create|copy|files)|^when2meet/new"
                       r"|^$|^(start|schedule|maps|workshops|timetable|tabletennis|events)(/|$)|^clubs($|/(?!(league|new)(/|$)))|^music-room($|/(?!instructions(/|$)))"
                       r"|^(calendar|search|when2meet|student-affairs|board-games|timer)($|/)|^sport($|/(?!faq(/|$)))|^room-booking($|/(?!rules(/|$)))",  # (login walls: 'Use your Innopolis account to access InNoHassle services'; board-games and timer: no text)
                       max_pages=300, render=True),  # (an app: the browser runs its scripts; the pages behind a login show 'Sign in' and are dropped as pages of no words)
    "hotel": Site("https://hotel.innopolis.university/", "ru", "the campus of Innopolis University: dormitories, their rules, prices and documents",
                  r"zayavka|bitrix|upload/", sitemap=False, english="en"),
    "international": Site("https://new.innopolis.university/en/", "en", "admission of international applicants to Innopolis University (in English): bachelor's, master's and PhD programmes, grants, olympiad bonuses, applicants from the CIS, FAQ",
                          r"^(?!en(/|$))|(^|/)(search|personal|auth|login|bitrix|upload|local|include)(/|$)", sitemap=False, max_pages=200),  # (only /en/ is there: / is a 404, and its sitemap is apply's)
    "media": Site("https://media.innopolis.university/", "ru", "the news and events of Innopolis University",
                  r"^(?!(news|events)(/|$))[^/]+|^(news|events)/[^/]+/.", max_pages=5000, dated=True, end=r"(?m)^(\[Читать далее\]\([^)]*\)\n)?Новости по теме$"),  # (the rest of it is innopolis.university again: about, sveden, success-stories; its /en/ lists the Russian news;
                  # an address below a news item is a link written without 'https://' ('news/x/www.kuka.ru'): the site answers it with its list of news)
    "stc": Site("https://stc.innopolis.university/", "ru", "IT courses of Innopolis University for adults and children: professions, programmes, their prices and the blog",
                r"^(tilda|members)/|^page\d+\.html$", max_pages=300, robots=True),
    "edu": Site("https://edu.innopolis.university/", "ru", "programmes of Innopolis University for schools, colleges, universities and teachers: short courses, internships, strategy sessions, staff assessment",
                r"^(tilda|members)/|^page\d+\.html$", max_pages=200, robots=True),
    "city": Site("https://innopolis.com/ru/", "ru", "the city of Innopolis and its special economic zone: living and housing, transport, services, schools, business, news and events",
                 r"^(?!(ru|en)(/|$))", sitemap=False, max_pages=800, english="en", dated=True, pause=10,  # (an address without ru/ or en/ is a redirect to /ru/site/typicle?slug=..., a page that fails)
                 headings=r"\b(section_head|section_text|article|history)__title\b", bare=True, listing="page", aliases=("innopolis.ru",)),  # (innopolis.ru: the same site)
    "my": Site("https://my.innopolis.university/", "ru", "My University, the student portal of Innopolis University: the events (volunteering, innopoints) and the store of merch",
               r"^(?!(store|event)(/|$))[^/]+|^store/(purchases|transactions)|^event/(my|history)", sitemap=False, max_pages=100, profile="CATIX_CHROMIUM_PROFILE",
               private=r"^RU\n### .+\n\S+@\S+\n|^Баланс:\n\d+\n|^## Уведомления\n(?s:.*)\Z"),  # (a login; the pages of the person: purchases, transactions, my events, history of participation)
    # the sites the pages link most that were not read (experiments/link_stats.py --group university, 2026-10-31)
    "career": Site("https://career.innopolis.university/", "ru", "careers at Innopolis University: vacancies, the competition for teaching posts, relocation to Innopolis",
                   only("job", "konkursnyezayavkiprofessorskoprepodavatelskogosostava", "relocation"), sitemap=False, max_pages=300),  # (its sitemap and the rest of it: innopolis.university again)
    "corporate": Site("https://corporate.innopolis.university/", "ru", "Innopolis University for business: corporate education, training of staff, strategy sessions, technology audit",
                      only("education", "podgotovkakadrov", "stratsession", "technologicalaudit"), sitemap=False, max_pages=100),
    "ai": Site("https://ai.innopolis.university/", "ru", "artificial intelligence at Innopolis University: its projects and science",
               only("projects", "science"), sitemap=False, max_pages=100),
    "alumni": Site("https://alumni.innopolis.university/", "en", "the alumni of Innopolis University: the community, its events and how to join", r".", sitemap=False, max_pages=5),
    "dovuz": Site("https://dovuz.innopolis.university/", "ru", "pre-university education at Innopolis University: courses, olympiad preparation, camps, webinars and olympiads for schoolchildren",
                  TILDA, max_pages=300, robots=True),
    "progmatica": Site("https://progmatica.innopolis.university/", "ru", "Progmatica, the IT school of Innopolis University for children: courses, intensives, webinars, master classes, articles for parents",
                       TILDA, max_pages=200, robots=True),
    "spec": Site("https://spec.innopolis.university/", "ru", "science, technology and education at Innopolis University: webinars, cases of industrial robotics and AI, digests, its scientists",
                 TILDA, max_pages=100, robots=True),
    "ido": Site("https://ido.innopolis.university/", "ru", "further education at Innopolis University: online courses in programming, IT and management, further training of teachers",
                TILDA, max_pages=100, robots=True),
    "college": Site("https://innopolis.college/", "ru", "Innopolis College, after the 9th grade: admission and its results, programmes, student life, partners, news",
                    TILDA, max_pages=100, robots=True),
    "events": Site("https://events.innopolis.university/", "ru", "the events of Innopolis University: webinars, master classes, conferences, the products it shows at exhibitions",
                   TILDA, max_pages=60, robots=True, dated=True),
    "trud": Site("https://trud.innopolis.university/", "ru", "free training in digital professions in the federal project of employment (earlier 'Содействие занятости'): its professions and how to enrol",
                 TILDA, max_pages=50, robots=True),
    "engineerschool": Site("https://engineerschool.innopolis.university/", "ru", "the Advanced Engineering School of Innopolis University: its programmes for IT engineers, its industry projects, news",
                           TILDA, max_pages=50, robots=True),
    "itbm": Site("https://itbm.innopolis.university/", "ru", "the centre of corporate training of Innopolis University: soft skills, technology and management programmes, strategy sessions",
                 TILDA, max_pages=20, robots=True),
    "olymp": Site("https://olymp.innopolis.university/", "ru", "the Republican team olympiad in programming for schoolchildren of grades 7–11, held by Innopolis University",
                  TILDA, max_pages=20, robots=True, dated=True),
    "msonline": Site("https://msonline.innopolis.university/", "ru", "the online master's programmes of Innopolis University",
                     TILDA, max_pages=30, robots=True),
    "research": Site("https://research.innopolis.university/", "ru", "the sector of analytical research of Innopolis University: research in IT, business and education for companies and the state",
                     TILDA, max_pages=30, robots=True),
    "dissovet": Site("https://dissovet.innopolis.university/", "ru", "the dissertation council of Innopolis University: defences of theses, its members, its documents",
                     TILDA + r"|^page(135641906|136990946)\.html$", max_pages=60, robots=True),  # (the templates of a defence its sitemap lists: 'Иванов Иван Николаевич', 'Название работы')
    "globalhack": Site("https://globalhack.innopolis.university/", "ru", "INNOGLOBALHACK, the all-Russian hackathon of Innopolis University for students of technical universities",
                       TILDA, max_pages=10, robots=True, dated=True),
    "aiconf": Site("https://aiconf.innopolis.ru/", "ru", "AI IN 2023, a conference on artificial intelligence in Innopolis, and its drone race",
                   TILDA, max_pages=20, robots=True, dated=True),
    "fmp": Site("https://fmp.innopolis.university/", "ru", "'Физмат прорыв' (the physics and mathematics breakthrough): classes, clubs and lectures for gifted schoolchildren, its teachers, useful resources",
                TILDA, max_pages=60, robots=True),
    "llc": Site("https://llc.innopolis.university/", "ru", "the centre of continuous learning of Innopolis University: courses of soft skills for business, career and life",
                TILDA, max_pages=20, robots=True),
    "iustore": Site("https://iustore.innopolis.ru/", "ru", "the merchandise store of Innopolis University: clothes, sizes, delivery, returns",
                    TILDA, max_pages=30, robots=True),
    "onboarding": Site("https://onboarding.innopolis.ru/", "ru", "the onboarding of a new resident of the city of Innopolis",
                       TILDA, max_pages=20, robots=True),
    "teamproject": Site("https://team-project.university.innopolis.ru/", "ru", "the events of the pre-university centre of Innopolis University: team projects, the spring school of bachelors, partnership",
                        TILDA, max_pages=20, robots=True),
    "sez": Site("https://sezinnopolis.ru/", "ru", "the special economic zone Innopolis: its residents, support for companies and startups, industrial sites, rent and services, news and events",
                BITRIX + r"|(^|/)(startup-lk|lk)(/|$)", sitemap=False, max_pages=600, robots=True),  # (its robots.txt forbids the pages of its lists: the news of the first page)
    "robotics": Site("https://robotics.innopolis.university/", "ru", "the centre of technologies of robotics and mechatronics components at Innopolis University: projects, labs, team, publications, patents, education, news",
                     r"^(en|team|public)(/|$)|(^|/)(feed|wp-json|wp-admin|wp-content|xmlrpc\.php|comments|sample-page|author|tag|category)(/|$)", sitemap="wp-sitemap.xml", max_pages=900,
                     drop=r"\[(Дальше|Перейти к следующей теме в этом разделе|\(:ru\)[^\]]*)\]\([^)]*\)"),  # (its English is mostly the Russian text marked '(Русский)'; a person's page is a name and
                     # a post, a publication's its title: /science/ lists them with their authors; the language is a cookie, see fetch)
}


CHROMIUM = shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
RENDER_BUDGET = 15000  # milliseconds of the page's own time the browser lets its scripts run


def render_page(url: str) -> str | None:
    """The page as the browser shows it after its scripts ran (headless Chromium, the page's own address): for a site that is
    an app, whose HTML is an empty shell ('You need to enable JavaScript'). None when the browser gave nothing."""
    if not CHROMIUM:
        raise RuntimeError("a site with render=True needs Chromium (chromium, chromium-browser or google-chrome on the PATH)")
    with tempfile.TemporaryDirectory() as profile:
        run = subprocess.run([CHROMIUM, "--headless=new", "--disable-gpu", "--no-sandbox", f"--user-data-dir={profile}",
                              f"--virtual-time-budget={RENDER_BUDGET}", "--dump-dom", url], capture_output=True, text=True, timeout=180)
    return run.stdout if run.returncode == 0 and run.stdout.strip() else None


LIVE_WAIT = 30  # seconds: the longest a page of an app behind a login is given to finish loading
LOGIN_FORM = re.compile(r"""<input[^>]+type=["']?password""", re.I)


def render_live(url: str, profile: str) -> str:
    """The page as a person logged in to the Chromium profile sees it: the browser (with the profile) opens the page and the DOM is
    taken when it stops changing. Not the virtual-time budget of render_page: an app behind a login polls, and the budget never ends.
    Raises when the profile is not logged in (the page asks for a password) or the page did not load (its title is still '{eventName}')."""
    if not CHROMIUM:
        raise RuntimeError("a site with a profile needs Chromium (chromium, chromium-browser or google-chrome on the PATH)")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    browser = subprocess.Popen([CHROMIUM, "--headless=new", "--disable-gpu", "--no-sandbox", f"--user-data-dir={profile}", f"--remote-debugging-port={port}", "about:blank"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                tab = next(t for t in httpx.get(f"http://127.0.0.1:{port}/json").json() if t["type"] == "page")
                break
            except (httpx.HTTPError, StopIteration):
                time.sleep(0.2)
        else:
            raise httpx.TransportError("the browser did not start")

        async def ask() -> str:
            async with websockets.connect(tab["webSocketDebuggerUrl"], max_size=None) as ws:
                ids = iter(range(1, 10**6))

                async def call(method: str, **params) -> dict:
                    n = next(ids)
                    await ws.send(json.dumps({"id": n, "method": method, "params": params}))
                    while (answer := json.loads(await ws.recv())).get("id") != n:
                        pass
                    return answer

                await call("Page.navigate", url=url)
                last, still = "", 0
                for second in range(LIVE_WAIT):
                    await asyncio.sleep(1)
                    html = (await call("Runtime.evaluate", expression="document.documentElement.outerHTML", returnByValue=True))["result"]["result"]["value"]
                    still = still + 1 if html == last else 0
                    last = html
                    if still >= 3 and second >= 4:  # (unchanged for three seconds, and not the empty shell of the first ones)
                        break
                return last

        html = asyncio.run(ask())
    finally:
        browser.terminate()
        browser.wait()
    if LOGIN_FORM.search(html):
        raise RuntimeError(f"the profile {profile} is not logged in: {url} asks for a password")
    if re.search(r"<title>[^<]*\{\w+\}", html):
        raise httpx.TransportError(f"{url} did not finish loading")
    return html


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


def get_page(client: httpx.Client, site: "Site", url: str) -> httpx.Response:
    """The answer for a page: the site's own, or (for an app) what the browser made of it, as if it were the answer."""
    if site.profile:
        if not (profile := os.environ.get(site.profile)):
            raise RuntimeError(f"a site with a login needs {site.profile}: the Chromium profile a person logged in to")
        html = render_live(url, os.path.expanduser(profile))
        return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, text=html, request=httpx.Request("GET", url))
    if not site.render:
        return client.get(url)
    html = render_page(url)
    return httpx.Response(200 if html else 404, headers={"content-type": "text/html; charset=utf-8"}, text=html or "",
                          request=httpx.Request("GET", url))


def keep_by_hand(name: str, slug: str, old: dict) -> bool:
    """Whether the file of a page was edited after the crawl wrote it (a page behind a login, which a person put in by hand): its
    hash is no longer the one the crawl noted. A page marked `manual` in the index stays so; the crawl does not write over it."""
    path = ROOT / name / f"{slug}.md"
    if not path.exists() or not old:
        return False
    return bool(old.get("manual")) or bool(old.get("file_sha")) and hashlib.sha256(path.read_bytes()).hexdigest() != old["file_sha"]


def put_cache(name: str, slug: str, text: str) -> str:
    """The text of a page into the cache; the hash of the file as written (to tell later whether a person changed it)."""
    path = ROOT / name / f"{slug}.md"
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(url: str) -> str:
    """One spelling of a link: the site writes the same file with spaces, Cyrillic or %-escapes."""
    parts = urlsplit(url)
    return f"https://{parts.netloc}{quote(unquote(parts.path), safe='/')}"


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


class _Markdown(HTMLParser):
    """HTML -> markdown lines: headings, paragraphs, list items, tables; links, pictures and videos where the page has them
    (`[text](url)`, `![alt](url)`, `[▶ video](url)`), and the links on the side too (the crawl follows them). A table row
    is one line, whatever breaks its cells hold (a teacher's two degrees in one cell), and the first row of a table is
    followed by the markdown separator, so that the row is its header."""

    HIDDEN = {"script", "style", "noscript", "svg", "form", "select", "button", "template", "iframe", "head"}
    BLOCK = {"p", "div", "section", "article", "br", "ul", "ol", "blockquote", "dd", "dt"}

    def __init__(self, base: str, headings: str | None = None) -> None:
        super().__init__(convert_charrefs=True)
        self.base, self.lines, self.line, self.hidden = base, [], "", 0
        self.headings = headings  # (Site.headings)
        self.links: list[tuple[str, str]] = []  # (url, text)
        self.href: str | None = None
        self.anchor = ""
        self.url: str | None = None  # where the open link leads, when it is worth writing in the text
        self.mark: tuple[str, int] | None = None  # (line or cell, where the text of the open link starts in it)
        self.video = False  # inside <video> with no source written yet
        self.title = ""
        self._in_title = False
        self.tables: list[int] = []  # rows written of each open table (a table may sit in a cell of another)
        self.row: list[str] | None = None
        self.cell: str | None = None

    def _put(self, text: str) -> None:
        if self.cell is not None:
            self.cell += text
        else:
            self.line += text

    def _wrap(self, reopen: bool = False) -> None:
        """What was written since the open link began becomes its text: [text](url). A block ending inside the link closes
        the text there and opens it again on the next line (`reopen`)."""
        kind = "cell" if self.cell is not None else "line"
        if self.url and self.mark and self.mark[0] == kind:
            buf = self.cell if self.cell is not None else self.line
            seg = buf[self.mark[1]:]
            text = re.sub(r"\s+", " ", re.sub(r"</?[a-z][^>]*>", " ", seg, flags=re.I)).strip()  # (a site that writes <p> as text: not in a link)
            head = re.match(r"(#{2,3} |- )", text)  # (a link around a heading or an item: the mark of the line stays outside)
            if head:
                text = text[head.end():]
            if text:
                if "![" not in text:
                    text = text.replace("[", "(").replace("]", ")")
                done = buf[:self.mark[1]] + seg[:len(seg) - len(seg.lstrip())] + (head.group(1) if head else "") + f"[{text}]({md_url(self.url)})" + seg[len(seg.rstrip()):]
                if self.cell is not None:
                    self.cell = done
                else:
                    self.line = done
        self.mark = (kind, 0) if reopen and self.url else None

    def _image(self, attrs: dict) -> None:
        srcset = (attrs.get("srcset") or attrs.get("data-srcset") or "").split(",")[-1].split()
        src = attrs.get("data-original") or attrs.get("data-src") or attrs.get("data-lazy-src") or (srcset[0] if srcset else "") or attrs.get("src") or ""
        if not src.strip():
            return  # (a picture a script fills in later: urljoin would make of it the address of the page)
        url = urljoin(self.base, src.strip())  # (Tilda keeps a 20-pixel preview in src, the picture in data-original)
        url = re.sub(r"^(https://)thb(\.tildacdn\.com/tild[\w-]+)/-/[^/]+/[^/]+/(.+)$", r"\1static\2/\3", url)  # (a preview with no original beside it: the file itself)
        small = any((attrs.get(k) or "").isdigit() and int(attrs[k]) <= 64 for k in ("width", "height"))
        if urlsplit(url).scheme not in {"http", "https"} or small or IMAGE_SKIP.search(urlsplit(url).path) or TRACKER.search(url):
            return
        alt = re.sub(r"[\[\]]", "", re.sub(r"\s+", " ", attrs.get("alt") or attrs.get("title") or "")).strip()
        self._put(f" ![{alt}]({md_url(url)}) ")

    def _watch(self, url: str | None, title: str = "") -> None:
        if url:
            self._put(f" [▶ {re.sub(r'[\[\]]', '', title).strip() or 'video'}]({md_url(url)}) ")

    def _flush(self) -> None:
        self._wrap(reopen=True)
        text = re.sub(r"\s+", " ", self.line).strip()
        if text and text not in {"-", "|", "## ", "### "} and not re.fullmatch(r"(#+|-|\|)\s*", text):
            self.lines.append(text)
        self.line = ""

    def _end_row(self) -> None:
        if self.cell is not None:
            self._end_cell()
        if self.row and any(self.row):
            self._flush()
            self.lines.append("| " + " | ".join(self.row) + " |")
            if self.tables:
                if self.tables[-1] == 0:
                    self.lines.append("|" + " --- |" * len(self.row))
                self.tables[-1] += 1
        self.row = None

    def _end_cell(self) -> None:
        self._wrap()
        if self.row is None:
            self.row = []
        self.row.append(re.sub(r"\s+", " ", self.cell or "").replace("|", "/").strip())
        self.cell = None

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "title":
            self._in_title = True
        a = {k: v or "" for k, v in attrs}
        if not self.hidden:
            if tag == "img":
                self._image(a)
            elif tag == "iframe":
                self._watch(video_url(urljoin(self.base, (a.get("src") or a.get("data-src") or "").strip())), a.get("title", ""))
            elif tag == "video":
                self.video = not a.get("src")
                self._watch(urljoin(self.base, a["src"]) if a.get("src") else None, a.get("title", ""))
            elif tag == "source" and self.video and a.get("src"):
                self.video = False
                self._watch(urljoin(self.base, a["src"]))
            elif a.get("data-videolazy-id") and a.get("data-videolazy-type") in {"youtube", "vimeo"}:  # (Tilda's video block)
                vid = a["data-videolazy-id"]
                self._watch(f"https://www.youtube.com/watch?v={vid}" if a["data-videolazy-type"] == "youtube" else f"https://vimeo.com/{vid}")
            elif tag not in self.HIDDEN:  # (Bitrix keeps a video in the data-source / data-src of a div)
                self._watch(next(filter(None, (video_url(urljoin(self.base, a[k].strip())) for k in ("data-source", "data-src", "data-video-src") if a.get(k))), None))
            if "background-image" in a.get("style", "") and tag not in self.HIDDEN:  # (a banner: the first address, not the 2x copies)
                found = re.search(r"background-image:\s*(?:-webkit-)?(?:image-set\()?\s*url\(\s*['\"]?([^'\")]+)", a["style"])
                if found:
                    self._image({"src": found.group(1), "data-original": a.get("data-original", "")})  # (Tilda: the 20-pixel preview in the style, the picture in data-original)
            elif a.get("data-original") and tag not in self.HIDDEN | {"img"}:
                self._image({"src": a["data-original"]})
        if tag in self.HIDDEN:
            self.hidden += 1
            return
        if tag == "a":
            self.href, self.anchor, self.url, self.mark = a.get("href"), "", None, None
            if re.match(r"(?i)javascript:", re.sub(r"[\s*]", "", self.href or "")):  # (a script, not a link; media writes it 'jav * ascript:void(0)', an address of every page)
                self.href = None
            if self.href and not self.hidden:
                url = urljoin(self.base, self.href.strip())
                if urlsplit(url).scheme in {"http", "https"} and urldefrag(url)[0] != urldefrag(self.base)[0]:
                    self.url, self.mark = url, ("cell" if self.cell is not None else "line", len(self.cell if self.cell is not None else self.line))
        if tag == "table":
            self._flush()
            self.tables.append(0)
        elif tag == "tr":
            self._end_row()
            self.row = []
        elif tag in {"td", "th"}:
            if self.cell is not None:
                self._end_cell()
            self.cell = ""
        elif self.cell is not None:
            if tag in self.BLOCK or re.fullmatch(r"h[1-6]|li", tag):
                self.cell += " "  # (a break inside a cell is a space: the row stays one line)
        elif tag in self.BLOCK or re.fullmatch(r"h[1-6]|li", tag):
            self._flush()
            if re.fullmatch(r"h[1-3]", tag):
                self.line = "## "
            elif re.fullmatch(r"h[4-6]", tag):
                self.line = "### "
            elif tag == "li":
                self.line = "- "
            elif self.headings and re.search(self.headings, a.get("class", "")):
                self.line = "## "

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag in self.HIDDEN:
            self.hidden = max(0, self.hidden - 1)
            return
        if tag == "a":
            self._wrap()
            if self.href:
                self.links.append((urljoin(self.base, self.href.strip()), re.sub(r"\s+", " ", self.anchor).strip()))
            self.href, self.url = None, None
        if tag == "video":
            self.video = False
        if tag in {"td", "th"} and self.cell is not None:
            self._end_cell()
        elif tag == "tr":
            self._end_row()
        elif tag == "table":
            self._end_row()
            if self.tables:
                self.tables.pop()
        elif self.cell is None and (tag in self.BLOCK or re.fullmatch(r"h[1-6]|li", tag)):
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self.hidden:
            return
        if self.cell is not None:
            self.cell += data
        else:
            self.line += data
        if self.href is not None:
            self.anchor += data


def read(html: str, url: str, headings: str | None = None) -> tuple[str, str, list[tuple[str, str]]]:
    """(title, markdown lines, links) of a page; `headings`: Site.headings."""
    parser = _Markdown(url, headings)
    parser.feed(html)
    parser.close()
    parser._flush()
    lines, item = [], 0
    for line in parser.lines:
        if lines and re.fullmatch(r"\d{1,2}", lines[-1]) and int(lines[-1]) in (1, item + 1):  # (not a counter: '110 places', '50 places')
            item = int(lines[-1])
            hashes, words = re.match(r"(#+ )?(.*)", line).groups()  # (a step whose words are a heading: '### **1.** Submit an application')
            lines[-1] = f"{hashes or ''}**{lines[-1]}.** {words}"  # a numbered item whose number sits in a block of its own: 'item 2' can be quoted
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
        rules.parse(client.get(urljoin(site.base, "/robots.txt")).text.splitlines())
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


def fetch_site(name: str, site: Site, client: httpx.Client) -> int:
    """Read every page of a site (from its sitemap and the links of its pages); keep the text of the new and changed ones
    and the documents they link. The number of pages that are new, changed or gone."""
    index = load(name)
    todo: list[str] = [site.base]
    if site.sitemap:
        try:
            path = site.sitemap if isinstance(site.sitemap, str) else "sitemap.xml"
            maps = [urljoin(site.base, path)] + ([urljoin(site.base, f"{site.english}/{path}")] if site.english else [])
            for _ in range(100):  # (a sitemap may list sitemaps: Bitrix keeps one per block of the site)
                if not maps:
                    break
                for loc in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", client.get(maps.pop(0)).text):
                    (maps if loc.endswith(".xml") else todo).append(repaired(site, loc))
                time.sleep(PAUSE if site.pause is None else site.pause)
        except httpx.HTTPError as e:
            print(f"  {name}: no sitemap ({e})")
        time.sleep(PAUSE if site.pause is None else site.pause)
    rules = robots_of(site, client)
    seen, read_slugs, read_ok, changed, docs = set(), set(), 0, 0, {}
    first: dict[str, str] = {}  # the words of a page (their hash) -> the page read with them first in this run
    while todo and len(seen) < site.max_pages:
        link = todo.pop(0)
        number = re.search(rf"[?&]{site.listing}=(\d+)", link) if site.listing else None
        url = canonical(link) + (f"?{site.listing}={number.group(1)}" if number and number.group(1) != "1" else "")  # (a page of a list, after its first)
        if url in seen or not _taken(site, url) or rules and not rules.can_fetch(regulations.HEADERS["User-Agent"], url):
            continue
        seen.add(url)
        slug = slug_of(site, url)
        if index["pages"].get(slug, {}).get("url", url).rstrip("/") != url.rstrip("/"):  # (two paths, one slug: a Cyrillic path leaves nothing of itself, 'home' is taken)
            slug = f"{slug[:50]}-{hashlib.sha1(url.encode()).hexdigest()[:6]}"
        try:
            resp = get_page(client, site, url)
            time.sleep(PAUSE if site.pause is None else site.pause)
        except (httpx.HTTPError, subprocess.TimeoutExpired) as e:
            print(f"  FAILED {url}: {e}")
            continue
        old = index["pages"].get(slug, {})
        if resp.status_code == 404 or "text/html" not in resp.headers.get("content-type", ""):
            if old and not old.get("gone") and slug not in read_slugs:  # (not for the other spelling of an address that was read: /x/ and /x)
                index["pages"][slug] = {**old, "gone": True}
                changed += 1
            continue
        if resp.status_code != 200:
            print(f"  {url}: {resp.status_code}")
            continue
        read_ok += 1
        read_slugs.add(slug)
        title, text, links = read(resp.text, str(resp.url), site.headings)
        if site.private:
            text = re.sub(site.private, "", text, flags=re.M).rstrip() + "\n"  # (the person who is logged in is not the page's)
        if site.bare:
            links = [(languaged(site, link, str(resp.url)), anchor) for link, anchor in links]
            text = re.sub(r"(!\[[^\]]*\]\([^)\s]*\))|(?<=\]\()https?://[^)\s]+", lambda m: m.group(1) or languaged(site, m.group(), str(resp.url)), text)  # (not a picture)
        if (extra := EXTRAS.get((name, slug))):
            text = extra(client, resp.text, str(resp.url), text)
        for link, anchor in links:
            if DOC.search(urlsplit(link).path) and urlsplit(link).netloc == urlsplit(site.base).netloc:
                doc = canonical(link)
                docs[doc] = max(docs.get(doc, ""), anchor, key=len)  # the fullest of the link texts: 'Правила проживания', not 'Правила'
            elif _taken(site, link):
                todo.append(link)
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
            if not (ROOT / name / f"{slug}.md").exists() or (ROOT / name / f"{slug}.md").read_text(encoding="utf-8") != text:
                index["pages"][slug] = {**old, "file_sha": put_cache(name, slug, text)}  # (the same words, other links and pictures)
            continue
        index["pages"][slug] = {"url": url, "title": title, "sha256": sha, "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                "last_modified": resp.headers.get("last-modified", ""), "file_sha": put_cache(name, slug, text)}
        changed += 1
        print(f"  {slug}: {'changed' if old else 'new'}, {len(text)} chars", flush=True)
        if changed % 50 == 0:
            save(name, index)  # (a long crawl cut short keeps what it read)
    for slug, page in index["pages"].items():  # a page no link leads to any more has left the site
        if read_ok and page["url"] not in seen and slug not in read_slugs and not page.get("gone") and len(seen) < site.max_pages:  # (not when the site did not answer)
            index["pages"][slug] = {**page, "gone": True}
            changed += 1
    if read_ok:
        index["docs"] = docs
    save(name, index)
    return changed


def fetch(names: list[str] | None = None) -> int:
    """The sites named (every site when none is), one after another; the number of pages that are new, changed or gone."""
    if unknown := [n for n in names or [] if n not in SITES]:
        sys.exit(f"no site {', '.join(unknown)}: the sites are {', '.join(SITES)}")
    total = 0
    no_cookies = CookieJar(policy=DefaultCookiePolicy(allowed_domains=[]))  # every page as a new visitor sees it (robotics keeps the language of the last page in a cookie: its sitemap became English)
    with httpx.Client(headers=regulations.HEADERS, timeout=60, follow_redirects=True, cookies=no_cookies) as client:
        for name, site in SITES.items():
            if names and name not in names:
                continue
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
    """Lines that many pages of a site repeat: its menu, its footer, its contacts block. A small site needs half of its pages
    (at least 3) to repeat a line; a large one a quarter, but no fewer than 10 pages: a section of a site has its own menu and
    footer, which is on a third of the pages, not on a half. They are kept once, in the site's shared page, not lost."""
    if len(texts) < 3:
        return set()
    need = max(3, min(0.5 * len(texts), max(10, 0.25 * len(texts))))
    counts = Counter(line for text in texts for line in set(text.splitlines()))
    return {line for line, n in counts.items() if n >= need}


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
    site = SITES[name]
    host = urlsplit(site.base).netloc
    title = f"Общие блоки сайта {host}: меню, шапка, подвал, контакты" if lang == "ru" else f"Blocks shared by the pages of {host}: menu, header, footer, contacts"
    sha = hashlib.sha256(plain(body).encode()).hexdigest()[:12]
    front = ["---", "type: page", f"title: {yaml_value(title)}",
             f"description: {yaml_value('The menu, header, footer and contact lines that every page of the site repeats, kept once.')}",
             f"resource: {yaml_value(site.base)}", "tags: [\"site\", \"menu\", \"footer\", \"contacts\"]", f"audience: {yaml_value(list(AUDIENCES))}",
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
    out = DOCS / FOLDER
    out.mkdir(parents=True, exist_ok=True)
    entries: dict[tuple[str, str], dict] = {}
    shared: dict[tuple[str, str], list[str]] = {}  # (site, language) -> the lines its pages repeat, in the order they come
    for name, site in SITES.items():
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
    where = {address(e["page"]["url"]): page_path(name, slug) for (name, slug), e in entries.items()}
    for key, doc in docs().items():  # (a document of a site, once it is a page of regulations)
        if (DOCS / "regulations" / f"{key}.md").exists():
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
        audience = [str(a) for a in p.get("audience") or AUDIENCES]  # (everyone, unless a person named its readers: sport/faq is for students)
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
    for page in out.rglob("*.md"):
        if page not in keep and page.name != "index.md":
            page.unlink()
            print(f"{page.relative_to(out)}: no longer on its site (or moved), page removed")
    print(f"{written} pages written, {len(keep)} pages of the sites in the bundle")


def status() -> None:
    for name, site in SITES.items():
        index = load(name)
        pages = index["pages"].values()
        print(f"{name} ({site.base}): {sum(not p.get('gone') for p in pages)} pages, {sum(bool(p.get('gone')) for p in pages)} gone, "
              f"{len(index['docs'])} documents linked")


def main() -> None:
    cmd, *args = sys.argv[2:] or ["status"]
    if cmd == "fetch":
        fetch(args)
    elif cmd == "compile":
        compile_all()
    elif cmd == "status":
        status()
    else:
        sys.exit(__doc__)
