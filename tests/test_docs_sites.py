"""The sites of the university's services (sources/sites.py): what code reads from a page, which links it follows, which documents it hands on."""

import dataclasses
import re
from argparse import Namespace
from datetime import timedelta

import httpx
import pytest
import yaml

from catix.docs import frontier, notes
from catix.docs.sources import crawl, regulations, sites
from catix.docs.sources.sites import boilerplate, canonical, read
from tests import crawl_helpers as h
from tests.crawl_helpers import WORDS


@pytest.fixture(autouse=True)
def fresh_caches(monkeypatch):
    """What sites.py remembers of a site (the lines its pages repeat, its robots.txt) is not carried from a test to the next."""
    monkeypatch.setattr(sites, "_common", {})
    monkeypatch.setattr(sites, "_robots", {})


PAGE = """<html><head><title>Проживание студентов</title><script>var x = "<p>not text</p>";</script></head><body>
<nav><a href="/roomfund/">Номерной фонд</a></nav>
<h1>Проживание студентов</h1>
<div class="t-text">Студенты размещаются в номерах кампуса.<br>Заселение в корпусе №5.</div>
<div class="t-text">Студенты размещаются в номерах кампуса.<br>Заселение в корпусе №5.</div>
<div>1</div><div>Final exams are scheduled within the exam period.</div>
<ul><li>WiFi zone</li><li>24-hour laundry room</li></ul>
<a href="/upload/docs-hotel/Правила проживания.pdf">Правила</a>
<a href="https://hotel.innopolis.university/upload/docs-hotel/%D0%9F%D1%80%D0%B0%D0%B2%D0%B8%D0%BB%D0%B0%20%D0%BF%D1%80%D0%BE%D0%B6%D0%B8%D0%B2%D0%B0%D0%BD%D0%B8%D1%8F.pdf">Правила проживания</a>
</body></html>"""


def test_a_page_becomes_markdown_without_its_scripts_and_repeats():
    title, text, _ = read(PAGE, "https://hotel.innopolis.university/studentaccommodation/")
    assert title == "Проживание студентов"
    assert "not text" not in text
    assert text.count("Студенты размещаются в номерах кампуса.") == 1  # (Tilda repeats a block for phones)
    assert "## Проживание студентов" in text.splitlines()
    assert "- WiFi zone" in text.splitlines()


def test_a_number_in_a_block_of_its_own_opens_its_item():
    _, text, _ = read(PAGE, "https://hotel.innopolis.university/")
    assert "**1.** Final exams are scheduled within the exam period." in text.splitlines()


def test_a_counter_is_not_an_item():
    html = ("<html><body><p>110</p><p>бюджетных мест в бакалавриате</p><p>50</p><p>бюджетных мест в магистратуре</p>"
            "<p>1</p><p>Apply online.</p><p>2</p><h2>Pass the exams</h2></body></html>")
    lines = read(html, "https://new.innopolis.university/en/grant/")[1].splitlines()
    assert "50" in lines and "бюджетных мест в магистратуре" in lines  # (new.innopolis.university: a count of places, not item 50)
    assert "**1.** Apply online." in lines and "## **2.** Pass the exams" in lines


def test_a_script_written_as_a_link_is_no_link():
    html = '<html><body><p><a href="jav * ascript:void(0)">Скачать PDF, содержащий материалы страницы</a></p></body></html>'
    _, text, links = read(html, "https://media.innopolis.university/news/x/")
    assert text == "Скачать PDF, содержащий материалы страницы" and links == []


def test_a_block_a_site_names_a_heading_is_one():
    html = ('<html><body><div class="article__title">Стоимость квартир</div><div class="article__text">от 17 000 ₽ в месяц</div>'
            '<div class="facts_item__title">3 минуты</div></body></html>')
    lines = read(html, "https://innopolis.com/ru/life/housing/rental", sites.SITES["city"].headings)[1].splitlines()
    assert lines == ["## Стоимость квартир", "от 17 000 ₽ в месяц", "3 минуты"]  # (a fact's title is no heading)
    assert read(html, "https://innopolis.com/ru/life/housing/rental")[1].splitlines()[0] == "Стоимость квартир"  # (another site: a div)


def test_one_file_written_three_ways_is_one_document_with_its_fullest_name():
    _, _, links = read(PAGE, "https://hotel.innopolis.university/studentaccommodation/")
    files = {canonical(url) for url, _ in links if url.endswith(".pdf")}
    assert len(files) == 1
    assert max((a for u, a in links if u.endswith(".pdf")), key=len) == "Правила проживания"


def test_past_events_old_copies_and_the_other_language_are_not_followed():
    campus, hotel = sites.SITES["campuslife"], sites.SITES["hotel"]
    assert sites._taken(campus, "https://campuslife.innopolis.ru/handbook")
    assert sites._taken(campus, "https://campuslife.innopolis.ru/springball2022")  # (past events are the wiki's record)
    assert sites._taken(campus, "https://campuslife.innopolis.ru/innobootcamp2022") and sites._taken(campus, "https://campuslife.innopolis.ru/ibc")
    assert not sites._taken(campus, "https://campuslife.innopolis.ru/handbook_old")
    assert sites._taken(hotel, "https://hotel.innopolis.university/en/contacts/")  # (its English copy is a text of its own)
    assert sites.language_of(hotel, "en-contacts") == "en" and sites.language_of(hotel, "contacts") == "ru"
    assert not sites._taken(hotel, "https://hotel.innopolis.university/zayavkanabronirovanie/")
    assert not sites._taken(hotel, "https://example.com/")
    assert not sites._taken(hotel, "https://hotel.innopolis.university/upload/docs-hotel/x.pdf")  # (a document, not a page)


def test_the_lines_most_pages_repeat_are_the_sites_own():
    pages = ["Menu\nHandbook\nFooter", "Menu\nFAQ\nFooter", "Menu\nClubs\nFooter", "Menu\nEvents"]
    assert boilerplate(pages) == {"Menu", "Footer"}
    assert boilerplate(pages[:2]) == set()  # too few pages to tell


def test_the_documents_of_a_site_go_to_the_regulations_with_a_readable_key(docs_db):
    url = canonical("https://hotel.innopolis.university/upload/docs-hotel/Приложение к приказу_Правила _размещения 2025 год (2).pdf")
    h.document(url, "hotel", "Правила", linked_by="hotel")
    (key, doc), = sites.docs().items()
    assert key.startswith("site-hotel-") and "-prilozhenie-k-prikazu-pravila" in key
    assert doc["title"] == "Приложение к приказу Правила размещения 2025 год"  # the link text says too little: the file's name
    assert doc["section"] == "site/hotel" and doc["ext"] == "pdf" and "audience" not in doc  # (the hotel names no readers: everyone)


def test_the_university_site_reads_the_pages_of_its_disclosure_section_too_and_has_an_english_copy():
    uni = sites.SITES["university"]
    assert sites._taken(uni, "https://innopolis.university/campus")
    assert sites._taken(uni, "https://innopolis.university/en/about/")
    assert sites._taken(uni, "https://innopolis.university/sveden/employees/")  # (the disclosure section: a page as any other, its documents too)
    assert not sites._taken(uni, "https://innopolis.university/lk/")
    assert not sites._taken(uni, "https://apply.innopolis.university/")  # (another site)
    assert sites.language_of(uni, "en-about") == "en" and sites.language_of(uni, "about") == "ru" and sites.language_of(uni, "entrance") == "ru"


def test_a_table_row_is_one_line_with_its_header_marked_whatever_breaks_its_cells_hold():
    html = ("<table><tr><th>ФИО</th><th>Образование</th></tr>"
            "<tr><td>Бегишева А. А.</td><td><p>Высшее: учитель географии</p><p>Высшее: инженер</p></td></tr></table><p>После</p>")
    _, text, _ = read(html, "https://innopolis.university/sveden/employees")
    assert text.splitlines() == ["| ФИО | Образование |", "| --- | --- |", "| Бегишева А. А. | Высшее: учитель географии Высшее: инженер |", "После"]


MEDIA = """<html><head><title>Бакалавриат</title></head><body>
<h1>Бакалавриат</h1>
<p>Подробнее о <a href="/bachelors/ds-ai/">Data Science</a> и <a href="https://example.org/a b(1)">внешней странице</a>, <a href="#top">наверх</a>, <a href="mailto:a@b.ru">почта</a>.</p>
<a href="/grant/"><div>Подать заявку на грант</div></a>
<a href="/photo/"><img src="/i/small.jpg" data-original="https://cdn.example/big/campus.jpg" alt="Кампус [летом]"></a>
<img src="data:image/gif;base64,AAAA"><img src="/img/logo.png" alt="logo"><img src="/i/px.jpg" width="1" height="1"><img src="/a/menu.svg">
<iframe src="https://www.youtube.com/embed/abc123"></iframe><iframe src="https://maps.example/embed?x=1"></iframe>
<video><source src="/media/tour.mp4"></video>
<div data-videolazy-id="xyz" data-videolazy-type="youtube"></div>
<table><tr><th>Программа</th></tr><tr><td><a href="/p/1/">Магистратура</a></td></tr></table>
</body></html>"""


def test_links_stay_in_the_text_where_the_page_has_them():
    lines = read(MEDIA, "https://apply.innopolis.university/bachelors/")[1].splitlines()
    assert ("Подробнее о [Data Science](https://apply.innopolis.university/bachelors/ds-ai/) и "
            "[внешней странице](https://example.org/a%20b%281%29), наверх, почта.") in lines  # (a fragment and a mailto: are words)
    assert "[Подать заявку на грант](https://apply.innopolis.university/grant/)" in lines  # (a block inside the link)
    assert "| [Магистратура](https://apply.innopolis.university/p/1/) |" in lines  # (a link in a table cell)


def test_pictures_and_videos_are_links_and_the_decorations_are_not():
    text = read(MEDIA, "https://apply.innopolis.university/bachelors/")[1]
    assert "[![Кампус летом](https://cdn.example/big/campus.jpg)](https://apply.innopolis.university/photo/)" in text  # (the picture of Tilda, in a link)
    assert text.count("![") == 2 and "![logo](https://apply.innopolis.university/img/logo.png)" in text  # (a data: picture, a pixel and an svg are not content; a logo is: a partner's)
    assert "[▶ video](https://www.youtube.com/watch?v=abc123)" in text and "maps.example" not in text
    assert "[▶ video](https://apply.innopolis.university/media/tour.mp4)" in text
    assert "[▶ video](https://www.youtube.com/watch?v=xyz)" in text


def test_the_hash_of_a_page_is_of_its_words_not_of_its_links_and_pictures():
    bare = "## Бакалавриат\nПодробнее о Data Science и внешней странице\n| Магистратура |"
    marked = ("## Бакалавриат\nПодробнее о [Data Science](https://x.org/a) и ![](https://x.org/i.jpg) внешней странице\n"
              "![alt](https://x.org/only.jpg)\n| [Магистратура](https://x.org/m) |")
    assert sites.plain(marked) == bare


def _site_root(monkeypatch, pages):
    monkeypatch.setattr(sites, "SITES", {"hotel": sites.SITES["hotel"]})
    for slug, (url, text) in pages.items():
        h.page(url, "hotel", slug, text, sha256="a" * 64)


def _documents() -> dict:
    """The documents compile_all makes, by path."""
    docs, _ = sites.compile_all()
    return {d.path: d for d in docs}


def test_the_pages_of_a_site_go_to_a_folder_of_their_own_and_keep_the_addresses_of_the_site(monkeypatch, docs_db):
    _site_root(monkeypatch, {
        "home": ("https://hotel.innopolis.university/", f"{WORDS} [Номера](https://hotel.innopolis.university/rooms/) ![Фото](https://cdn.example/a.jpg)"),
        "rooms": ("https://hotel.innopolis.university/rooms/", f"{WORDS} [На главную](https://hotel.innopolis.university/) [Скрытая](https://hotel.innopolis.university/gone/)"),
    })
    docs = _documents()
    assert sorted(docs) == ["sites/hotel/home", "sites/hotel/rooms"]
    home, rooms = docs["sites/hotel/home"].body, docs["sites/hotel/rooms"].body
    assert "[Номера](https://hotel.innopolis.university/rooms/)" in home and "![Фото](https://cdn.example/a.jpg)" in home
    assert "[На главную](https://hotel.innopolis.university/)" in rooms and "[Скрытая](https://hotel.innopolis.university/gone/)" in rooms


def test_the_name_of_the_site_leaves_the_titles_and_the_way_to_the_next_post_leaves_the_text(monkeypatch, docs_db):
    centre = " — Центр робототехники"
    _site_root(monkeypatch, {f"p{i}": (f"https://hotel.innopolis.university/p{i}/", f"{WORDS} {i}\n[Дальше](https://hotel.innopolis.university/p{i + 1}/)") for i in range(6)})
    for i in range(6):
        docs_db.execute("UPDATE crawl_urls SET title = %s WHERE slug = %s", (f"Новость {i}{centre}", f"p{i}"))
    monkeypatch.setattr(sites, "SITES", {"hotel": dataclasses.replace(_fixture_site("hotel"), drop=_fixture_site("robotics").drop)})
    page = _documents()["sites/hotel/p0"]
    assert page.meta["title"] == "Новость 0" and "Дальше" not in page.body


def test_the_pages_of_a_site_read_elsewhere_are_kept(monkeypatch, docs_db):
    _site_root(monkeypatch, {"home": ("https://hotel.innopolis.university/", f"{WORDS} [VPN](https://help.example/ru/vpn)")})
    monkeypatch.setattr(sites, "SITES", {"hotel": sites.SITES["hotel"], "help": dataclasses.replace(sites.SITES["hotel"], base="https://help.example/")})
    docs, keep = sites.compile_all()  # (no cache of help here: its browser read it on another machine)
    assert [d.path for d in docs] == ["sites/hotel/home"] and keep == ("sites/help/",)
    assert "[VPN](https://help.example/ru/vpn)" in docs[0].body


def test_a_site_may_keep_its_sitemap_elsewhere(monkeypatch, docs_db):
    site = sites.Site("https://wp.example/", "ru", "a centre", r"^nothing$", sitemap="wp-sitemap.xml", max_pages=10)
    monkeypatch.setitem(sites.SITES, "wp", site)
    maps = {"/wp-sitemap.xml": "<sitemapindex><sitemap><loc>https://wp.example/wp-sitemap-posts-team-1.xml</loc></sitemap></sitemapindex>",
            "/wp-sitemap-posts-team-1.xml": "<urlset><url><loc>https://wp.example/team/ivanov/</loc></url></urlset>"}

    class Client:
        def get(self, url):
            path = httpx.URL(url).path
            if path in maps:
                return httpx.Response(200, headers={"content-type": "application/xml"}, text=maps[path], request=httpx.Request("GET", url))
            return httpx.Response(200, headers={"content-type": "text/html"}, text=f"<html><p>{WORDS} {path}</p></html>", request=httpx.Request("GET", url))

    listing = h.put("https://wp.example/wp-sitemap.xml", "wp", kind="listing")
    assert h.crawl(Client()) == 2
    assert "team-ivanov" in h.by_slug("wp")  # (no link leads there: the sitemap does)
    assert (h.row_of(listing.url).state, h.row_of(listing.url).text) == ("ok", None)  # (the listing is read for its links, it is no page)
    assert [r["dst"] for r in docs_db.execute("SELECT dst FROM crawl_links WHERE src = %s", (listing.address,)).fetchall()] == ["https://wp.example/team/ivanov"]


def test_the_sitemaps_robots_txt_names_are_read_and_each_is_asked_once(monkeypatch, docs_db):
    site = sites.Site("https://shop.example/", "ru", "a shop", r"^nothing$", max_pages=10)
    monkeypatch.setitem(sites.SITES, "shop", site)
    ns = 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'
    maps = {"/robots.txt": ("text/plain", "User-agent: *\nSitemap: https://shop.example/sitemap.xml\nSitemap: https://shop.example/sitemap-store.xml\n"),
            "/sitemap.xml": ("application/xml", f"<urlset {ns}><url><loc>https://shop.example/a/</loc></url></urlset>"),
            "/sitemap-store.xml": ("application/xml", f"<urlset {ns}><url><loc>https://shop.example/tproduct/1-card</loc></url></urlset>")}
    asked = []

    class Client:
        def get(self, url):
            path = httpx.URL(url).path
            asked.append(path)
            kind, text = maps.get(path, ("text/html", f"<html><p>{WORDS} {path}</p></html>"))
            return httpx.Response(200, headers={"content-type": kind}, text=text, request=httpx.Request("GET", url))

    h.put("https://shop.example/sitemap.xml", "shop", kind="listing")
    h.crawl(Client())
    assert {"a", "tproduct-1-card"} <= set(h.by_slug("shop"))
    assert asked.count("/sitemap.xml") == 1


WALLED = '<html><head><title>Вы не робот?</title></head><body><div class="smart-captcha">Подтвердите, что вы не робот</div></body></html>'


def test_a_page_a_bot_check_answers_for_is_asked_again_and_never_kept(monkeypatch, docs_db):
    monkeypatch.setattr(sites, "BOT_PAUSE", 0)
    site = sites.Site("https://club.timepad.example/", "ru", "a club", r"^nothing$", sitemap=False, max_pages=10)
    monkeypatch.setitem(sites.SITES, "club", site)
    start = h.put("https://club.timepad.example/", "club", pinned=True)

    class Wall:
        asks = 0

        def get(self, url):
            Wall.asks += 1
            body = WALLED if Wall.asks <= 2 else f"<html><head><title>Club</title></head><body><p>{WORDS}</p></body></html>"
            return httpx.Response(200, headers={"content-type": "text/html"}, text=body, request=httpx.Request("GET", url))

    assert sites.read_page(Wall(), start) is True
    assert Wall.asks == 3 and (start.state, start.slug) == ("ok", "home")  # (the wall let the third ask through, the page was read)

    class NeverLets:
        def get(self, url):
            return httpx.Response(200, headers={"content-type": "text/html"}, text=WALLED, request=httpx.Request("GET", url))

    sites.read_page(NeverLets(), h.row_of(start.url))
    home = h.row_of(start.url)  # (a read that met only the wall keeps the page it read before)
    assert home.state == "ok" and "Вы не робот" not in home.text and WORDS in home.text
    new = h.put("https://club.timepad.example/other", "club")
    sites.read_page(NeverLets(), new)
    assert (new.state, new.why, new.text) == ("tried", "a bot check", None)


MENU = " ".join(f"раздел{chr(1072 + i % 26)}{chr(1072 + i // 26)}" for i in range(60))


def test_a_page_read_with_half_its_words_gone_waits_for_the_next_read_to_read_it_so(monkeypatch, docs_db):
    site = sites.Site("https://unit.example/", "ru", "a unit", r"^nothing$", sitemap=False, max_pages=10)
    monkeypatch.setitem(sites.SITES, "unit", site)
    labels = {"/": "Главная", "/a/": "Первая", "/b/": "Вторая"}
    shown = {path: f"{label} {WORDS}" for path, label in labels.items()}

    class Client:
        def get(self, url):
            path = httpx.URL(url).path
            html = (f"<html><head><title>{labels[path]}</title></head><body><div><a href='/'>Главная</a> <a href='/a/'>Первая</a> "
                    f"<a href='/b/'>Вторая</a></div><p>{MENU}</p><h1>{labels[path]}</h1><p>{shown[path]}</p></body></html>")
            return httpx.Response(200, headers={"content-type": "text/html"}, text=html, request=httpx.Request("GET", url))

    def read_a() -> tuple[bool, frontier.Row]:
        row = h.row_of("https://unit.example/a/")
        changed = sites.read_page(Client(), row)
        return changed, h.row_of(row.url)

    h.put("https://unit.example/", "unit", pinned=True)
    assert h.crawl(Client()) == 3
    shown["/a/"] = "Ведутся работы"  # (the menu is most of the page still: its own words are what went)
    changed, row = read_a()
    assert not changed and WORDS in row.text and row.short_words < 10 and row.state == "ok"
    shown["/a/"] = f"Первая {WORDS}"  # (it was the read)
    changed, row = read_a()
    assert not changed and WORDS in row.text and row.short_words is None
    shown["/a/"] = "Ведутся работы"
    changed, row = read_a()
    assert not changed and WORDS in row.text and row.short_words is not None
    changed, row = read_a()  # (two reads in a row found it so: it is the page now)
    assert changed and "Ведутся работы" in row.text and WORDS not in row.text and row.short_words is None


def _unit(monkeypatch, **fields) -> sites.Site:
    """The site of a few pages at unit.example the tests of the reading crawl, its start page the row they begin with."""
    site = sites.Site("https://unit.example/", "ru", "a unit", r"^nothing$", **{"sitemap": False, "max_pages": 10, **fields})
    monkeypatch.setitem(sites.SITES, "unit", site)
    h.put("https://unit.example/", "unit", pinned=True)
    return site


def _linked_pages(links: dict[str, list[str]], status: dict[str, int]):
    labels = {"/": "Главная", "/a/": "Первая", "/b/": "Вторая"}

    class Client:
        def get(self, url):
            path = httpx.URL(url).path
            menu = " ".join(f"<a href='{link}'>{labels[link]}</a>" for link in links[path])
            html = f"<html><head><title>{labels[path]}</title></head><body><div>{menu}</div><h1>{labels[path]}</h1><p>{labels[path]} {WORDS}</p></body></html>"
            return httpx.Response(status.get(path, 200), headers={"content-type": "text/html"}, text=html, request=httpx.Request("GET", url))

    return Client()


def test_a_page_not_found_is_missing_and_gone_when_the_next_read_finds_it_so_too(monkeypatch, docs_db):
    _unit(monkeypatch)
    status: dict[str, int] = {}
    client = _linked_pages({"/": ["/a/", "/b/"], "/a/": [], "/b/": []}, status)
    assert h.crawl(client) == 3
    a = "https://unit.example/a/"
    status["/a/"] = 404
    row = h.row_of(a)
    assert sites.read_page(client, row) is False and (row.state, row.why) == ("missing", "404") and WORDS in row.text  # (kept until the next read finds it so)
    assert h.by_slug("unit")["a"].state == "missing" and "a" in {r.slug for r in frontier.live_pages("unit")}
    del status["/a/"]  # (the site was down)
    row = h.row_of(a)
    assert sites.read_page(client, row) is False and (row.state, row.why) == ("ok", None)
    status["/a/"] = 404
    row = h.row_of(a)
    sites.read_page(client, row)
    assert row.state == "missing"
    assert sites.read_page(client, row) is True  # (the documents of the site may change: the page left the search)
    assert (row.state, row.why, row.text) == ("gone", "404", None) and "a" not in {r.slug for r in frontier.live_pages("unit")}


def test_a_page_no_live_page_links_any_more_leaves_the_search_when_the_sweep_finds_it_so_for_a_week(monkeypatch, docs_db):
    _unit(monkeypatch)
    links = {"/": ["/a/", "/b/"], "/a/": [], "/b/": []}
    client = _linked_pages(links, {})
    assert h.crawl(client) == 3
    links["/"] = ["/a/"]  # (the one change is the start page: its menu lost the link)
    sites.read_page(client, h.row_of("https://unit.example/"))
    assert frontier.sweep()["pages unlinked"] == 0  # (unlinked since today: kept for the week)
    b = h.row_of("https://unit.example/b/")
    assert b.state == "ok" and b.unlinked_since is not None and h.row_of("https://unit.example/a/").unlinked_since is None
    monkeypatch.setattr(frontier, "UNLINKED_GRACE", timedelta(0))
    assert frontier.sweep()["pages unlinked"] == 1
    assert sorted(r.slug for r in frontier.live_pages("unit")) == ["a", "home"]
    assert h.row_of("https://unit.example/b/") is None  # (gone and linked by nothing: dropped)


def test_a_document_no_page_links_any_more_is_kept_marked_as_no_longer_on_the_site_when_it_was_read(monkeypatch, docs_db):
    monkeypatch.setattr(regulations, "DOCS", {})
    monkeypatch.setattr(sites, "SITES", {"hotel": sites.Site("https://hotel.innopolis.university/", "ru", "the hotel", r"^nothing$", sitemap=False, max_pages=10)})
    files = {"/upload/a.pdf": "Правила проживания в гостинице", "/upload/b.pdf": "Положение об оплате проживания", "/upload/c.pdf": "Памятка гостю гостиницы"}

    class Client:
        def get(self, url):
            links = " ".join(f"<a href='{path}'>{name}</a>" for path, name in files.items())
            html = f"<html><head><title>Гостиница</title></head><body><h1>Гостиница</h1><p>{WORDS}</p><p>Документы</p><p>{links}</p></body></html>"
            return httpx.Response(200, headers={"content-type": "text/html"}, text=html, request=httpx.Request("GET", url))

    start = h.put("https://hotel.innopolis.university/", "hotel", pinned=True)
    assert sites.read_page(Client(), start)
    urls = {name: canonical(f"https://hotel.innopolis.university/upload/{name}.pdf") for name in "abc"}
    keys = {name: sites.doc_key("hotel", url) for name, url in urls.items()}
    assert set(sites.docs()) == set(keys.values())
    notes.put_text(keys["b"], "", "Положение об оплате проживания. " + WORDS * 3)  # (b was read, c never)
    notes.put_note(keys["b"], "", {"url": urls["b"], "sha256": "ab" * 32, "method": "text layer (opendataloader)",
                                    "fetched_at": "2026-10-01T00:00:00+00:00", "section": "site/hotel"})
    del files["/upload/b.pdf"], files["/upload/c.pdf"]  # (removed from the page, or hidden in a comment: no visitor sees them)
    sites.read_page(Client(), h.row_of(start.url))
    assert frontier.sweep()["documents never read dropped"] == 1
    today = docs_db.execute("SELECT current_date AS today").fetchone()["today"].isoformat()
    assert set(sites.docs()) == {keys["a"], keys["b"]}  # (c never read: nothing to keep)
    assert sites.docs()[keys["b"]]["unlisted"] == today
    page = next(d for d in regulations.compile_all() if d.path == f"regulations/{keys['b']}")
    assert page.meta["stale_after"] == f"{today}T00:00:00+00:00" and f"> Ни одна видимая страница сайта не ссылается на этот документ (с {today})" in page.body  # (the agent: 'may be outdated')
    files["/upload/b.pdf"] = "Положение об оплате проживания"
    sites.read_page(Client(), h.row_of(start.url))
    frontier.sweep()
    assert "unlisted" not in sites.docs()[keys["b"]]  # (linked again: as any other)


class Moving(h.Web):
    """Web, where some addresses send to others ({host: {path: address}}), as httpx's client following them does."""

    def __init__(self, links, moved):
        super().__init__(links)
        self.moved = moved

    def get(self, url):
        target = self.moved.get(httpx.URL(url).host, {}).get(httpx.URL(url).path)
        return super().get(target) if target else super().get(url)


class Validated(h.Web):
    """Web that gives every page an ETag and answers 304 to the request that carries it; what was sent, as {path: headers}."""

    def __init__(self, links):
        super().__init__(links)
        self.sent: dict[str, dict | None] = {}

    def get(self, url, headers=None):
        self.sent[httpx.URL(url).path] = headers
        if headers and headers.get("If-None-Match") == '"e1"':
            return httpx.Response(304, headers={"etag": '"e1"'}, request=httpx.Request("GET", url))
        page = super().get(url)
        return httpx.Response(page.status_code, headers={**page.headers, "etag": '"e1"'}, text=page.text, request=page.request)


def test_a_new_address_is_read_before_the_known_ones(monkeypatch, docs_db):
    _unit(monkeypatch)
    web = h.Web({"unit.example": {"/": ["/a/", "/b/"], "/a/": [], "/b/": []}})
    assert h.crawl(web) == 3
    web.links["unit.example"]["/"].append("/c/")  # (last on the page: a new item at the end of a feed)
    web.links["unit.example"]["/c/"] = []
    web.asked.clear()
    h.make_due("https://unit.example/", "https://unit.example/a/", "https://unit.example/b/")
    assert h.crawl(web) == 4
    assert web.asked == [("unit.example", "/"), ("unit.example", "/c/"), ("unit.example", "/a/"), ("unit.example", "/b/")]
    assert h.row_of("https://unit.example/c/").priority == frontier.RECHECK and "c" in h.by_slug("unit")


def test_a_site_takes_no_more_new_pages_than_its_max_pages(monkeypatch, docs_db):
    _unit(monkeypatch, max_pages=3)
    web = h.Web({"unit.example": {"/": ["/a/", "/b/", "/c/"], "/a/": [], "/b/": [], "/c/": []}})
    assert h.crawl(web) == 3
    assert set(h.by_slug("unit")) == {"home", "a", "b"} and h.row_of("https://unit.example/c/") is None
    assert len(h.rows("unit", "page")) == 3


def test_seed_makes_rows_of_the_start_pages_the_feeds_the_listings_and_the_first_regulations(monkeypatch, docs_db):
    unit = sites.Site("https://unit.example/", "ru", "a unit", r"^nothing$", sitemap=True)  # (no feed: its start page is one)
    club = sites.Site("https://club.example/", "ru", "a club", r"^nothing$", sitemap=False, feeds=("events/",))
    login = sites.Site("https://my.example/", "ru", "behind a login", r"^nothing$", sitemap=False, profile="NO_SUCH_PROFILE")
    monkeypatch.setattr(sites, "SITES", {"unit": unit, "club": club, "my": login})
    frontier.seed()
    frontier.seed()  # (again: the same rows)
    seen = {(r.address, r.kind): (r.site, r.pinned, r.every) for r in h.rows().values() if r.kind != "document"}
    assert seen == {
        ("https://unit.example", "page"): ("unit", True, frontier.FEED_EVERY),
        ("https://unit.example/sitemap.xml", "listing"): ("unit", True, frontier.PAGE_EVERY),
        ("https://club.example", "page"): ("club", True, frontier.FEED_EVERY),
        ("https://club.example/events", "page"): ("club", True, frontier.FEED_EVERY),
        ("https://my.example", "page"): ("my", True, frontier.PAGE_EVERY)}  # (a site behind a login is read as any page: its new pages are not told apart)
    documents = h.rows(kind="document")
    assert len(documents) == len(regulations.DOCS) and all(r.pinned and r.site == "university" and r.every == frontier.DOCUMENT_EVERY for r in documents.values())


def test_a_new_site_is_read_alone_and_says_what_it_could_not_read(monkeypatch, docs_db):
    name = sites.add_site("https://new.example/x")
    assert name == "new-example" and sites.SITES[name].base == "https://new.example/"
    assert sites.SITES[name].about == "new.example, added by a request"
    frontier.seed()
    frontier.request([name])
    web = h.Web({"new.example": {"/": ["/a/", "/gone/", "https://hotel.innopolis.university/rules/"], "/a/": []}})
    while frontier.requested([name]):  # (what the runner does for a request: its rows, nothing of the others)
        h.read(web, frontier.next_due(documents=False))
    assert {host for host, _ in web.asked} == {"new.example"}
    assert h.row_of("https://hotel.innopolis.university/rules/").priority == frontier.NEW  # (hotel's page waits for the crawl)
    found = sites.new_site_report(name)
    assert found.name == "new-example" and found.pages == 2
    assert "404" in found.report() and "0 documents" in found.report()
    assert sites.SITES[name].about == "new.example, added by a request: new.example/"  # (and the title of its start page)
    with pytest.raises(ValueError, match="in the catalog already: new-example"):
        sites.new_site_record("https://new.example/")


def test_a_new_address_the_site_sends_elsewhere_is_no_page_of_its_own_and_the_page_it_is_sent_to_is_read(monkeypatch, docs_db):
    """innopolis.university/news/x sends to media.innopolis.university/news/x: it was kept as a page of the university, a copy
    of media's. '/bachelor/' sends to '/bachelors/': the page under its own address."""
    unit = sites.Site("https://unit.example/", "ru", "a unit", r"^nothing$", sitemap=False)
    media = sites.Site("https://media.example/", "ru", "the news", r"^nothing$", sitemap=False)
    monkeypatch.setattr(sites, "SITES", {"unit": unit, "media": media})
    web = Moving({"unit.example": {"/": ["/news/x/", "/bachelor/"], "/bachelors/": []}, "media.example": {"/news/x/": []}},
                 {"unit.example": {"/news/x/": "https://media.example/news/x/", "/bachelor/": "https://unit.example/bachelors/"}})
    h.put("https://unit.example/", "unit", pinned=True)
    h.crawl(web, ("unit",))
    assert {a: (r.site, r.state, r.why) for a, r in h.rows("unit").items()} == {
        "https://unit.example": ("unit", "ok", None), "https://unit.example/bachelors": ("unit", "ok", None),
        "https://unit.example/news/x": ("unit", "tried", "sent to https://media.example/news/x/"),
        "https://unit.example/bachelor": ("unit", "tried", "sent to https://unit.example/bachelors/")}
    assert {a: (r.state, r.priority) for a, r in h.rows("media").items()} == {"https://media.example/news/x": ("new", frontier.NEW)}  # (media's crawl reads it)


def test_a_known_page_the_site_now_sends_elsewhere_stays_the_page_it_was(monkeypatch, docs_db):
    _unit(monkeypatch)
    web = Moving({"unit.example": {"/": ["/a/"], "/a/": [], "/b/": []}}, {})
    h.crawl(web)
    web.moved = {"unit.example": {"/a/": "https://unit.example/b/"}}
    h.make_due("https://unit.example/a/")
    h.crawl(web)
    page = h.row_of("https://unit.example/a/")
    assert page.url == "https://unit.example/a/" and (page.state, page.why, page.slug) == ("ok", None, "a") and h.row_of("https://unit.example/b/") is None


def test_a_page_answered_304_keeps_its_text_and_its_links_and_only_its_read_time_changes(monkeypatch, docs_db):
    _unit(monkeypatch)
    web = Validated({"unit.example": {"/": ["/a/", "/doc.pdf"], "/a/": []}})
    assert h.crawl(web) == 2  # (the document is no page: the documents' read takes it)
    assert web.sent["/"] is None
    home, a = "https://unit.example/", "https://unit.example/a/"
    before = {url: dataclasses.asdict(h.row_of(url)) for url in (home, a)}
    links = docs_db.execute("SELECT src, dst, anchor FROM crawl_links ORDER BY src, dst").fetchall()
    assert {r["dst"] for r in links} == {"https://unit.example/a", "https://unit.example/doc.pdf"}
    web.sent.clear()
    h.make_due(home, a)
    h.crawl(web)
    assert web.sent["/"] == {"If-None-Match": '"e1"'} and web.sent["/a/"] == {"If-None-Match": '"e1"'}
    for url in (home, a):
        after = dataclasses.asdict(h.row_of(url))
        assert after["read_at"] > before[url]["read_at"] and after["state"] == "ok"
        for column in ("text", "sha256", "title", "slug", "fetched_at", "validators", "why"):
            assert after[column] == before[url][column], column
    assert docs_db.execute("SELECT src, dst, anchor FROM crawl_links ORDER BY src, dst").fetchall() == links  # (not read again: nothing written)
    assert h.row_of("https://unit.example/doc.pdf").kind == "document" and h.row_of(a).unlinked_since is None
    docs_db.execute("UPDATE crawl_urls SET read_at = now() - interval '29 days' WHERE address = %s", (sites.address(a),))  # (REVALIDATE: read whole again)
    h.make_due(home, a)
    web.sent.clear()
    h.crawl(web)
    assert web.sent["/a/"] is None and web.sent["/"] == {"If-None-Match": '"e1"'}


def test_a_news_item_ends_where_the_related_news_begin_and_says_its_heading_and_date_once(monkeypatch, docs_db):
    _site_root(monkeypatch, {
        "rooms": ("https://hotel.innopolis.university/rooms/", f"29 октября 2026\n## Rooms\n29 октября 2026\n{WORDS}\n[Читать далее](https://hotel.innopolis.university/next/)\n"
                                                                "Новости по теме\n[Другая новость дня](https://hotel.innopolis.university/other/)"),
    })
    monkeypatch.setattr(sites, "SITES", {"hotel": dataclasses.replace(_fixture_site("hotel"), end=_fixture_site("media").end)})
    body = _documents()["sites/hotel/rooms"].body
    assert body.count("29 октября 2026") == 1 and "## Rooms" not in body and WORDS in body
    assert "Читать далее" not in body and "Другая новость дня" not in body


def test_a_link_to_a_document_of_a_site_stays_the_link_of_the_site(monkeypatch, docs_db):
    url = "https://hotel.innopolis.university/upload/docs-hotel/Правила проживания.pdf"
    _site_root(monkeypatch, {"home": ("https://hotel.innopolis.university/", f"{WORDS} [Правила]({url.replace(' ', '%20')})")})
    h.document(sites.canonical(url), "hotel", "Правила проживания", linked_by="hotel")
    assert f"[Правила]({url.replace(' ', '%20')})" in _documents()["sites/hotel/home"].body  # (the site's own file, read or not)


def test_a_document_in_a_table_or_under_a_heading_is_told_by_them_not_by_its_own_words(docs_db):
    text = """## Высшее образование
Образовательная программа высшего образования - программа магистратуры: 38.04.05 Бизнес-информатика
| Год | Учебные планы | Рабочие программы дисциплин (модулей) |
| --- | --- | --- |
| 2025 | [Учебный план](https://innopolis.university/upload/x/УП.pdf) | [1 семестр](https://innopolis.university/upload/x/РПД%201.7z) |
Программа бакалавриата 09.03.01
- [Результаты опросов](https://innopolis.university/upload/c/Результаты.pdf)
[Положение](https://innopolis.university/upload/a/Положение.pdf)
*в процессе лицензирования.
Программа дополнительного профессионального образования [«Инженерия искусственного интеллекта»](https://innopolis.university/upload/d/ОП.pdf)
[Учебный план](https://innopolis.university/upload/d/УП.pdf)
—
[Оценочные материалы](https://innopolis.university/upload/d/ОМ.pdf)"""
    contexts = sites.contexts_of(text)
    further = "Программа дополнительного профессионального образования «Инженерия искусственного интеллекта»"
    assert contexts[canonical("https://innopolis.university/upload/d/ОП.pdf")] == "в процессе лицензирования."  # (its own line names it)
    assert contexts[canonical("https://innopolis.university/upload/d/УП.pdf")] == further
    assert contexts[canonical("https://innopolis.university/upload/d/ОМ.pdf")] == further  # (a dash, an empty cell, is no caption)
    caption = "Образовательная программа высшего образования - программа магистратуры: 38.04.05 Бизнес-информатика"
    assert contexts[canonical("https://innopolis.university/upload/x/УП.pdf")] == f"{caption} — 2025 — Учебные планы"
    assert contexts[canonical("https://innopolis.university/upload/x/РПД 1.7z")] == f"{caption} — 2025 — Рабочие программы дисциплин (модулей)"
    assert contexts[canonical("https://innopolis.university/upload/c/Результаты.pdf")] == "Программа бакалавриата 09.03.01"  # (the header of a panel)
    assert contexts[canonical("https://innopolis.university/upload/a/Положение.pdf")] == "Программа бакалавриата 09.03.01"
    url = canonical("https://innopolis.university/upload/x/УП.pdf")
    h.document(url, "university", "Учебный план (документ подписан ПЭП)", context=contexts[url], linked_by="university")
    (doc,) = sites.docs().values()
    assert doc["title"] == f"{caption} — 2025 — Учебные планы — Учебный план" and doc["context"] == contexts[url]


def test_a_link_around_a_heading_keeps_the_heading_a_heading_and_a_picture_without_an_address_is_none():
    html = ('<a href="/s/marina/"><img src="" alt="x"><h2>Marina Ivanova</h2></a>'
            '<a href="/s/ananga/"><p>&lt;p&gt; Though my &lt;b&gt;exchange&lt;/b&gt;&lt;br&gt; &lt;/p&gt;</p></a>')
    text = read(html, "https://innopolis.university/success-stories/x/")[1]
    assert "## [Marina Ivanova](https://innopolis.university/s/marina/)" in text.splitlines()
    assert "![" not in text  # (an empty src is not the page itself)
    assert "[Though my exchange](https://innopolis.university/s/ananga/)" in text


BITRIX = """<html><body>
<div class="landing-block-node-video g-video-preview" data-src="//www.youtube.com/embed/0USWAsrY9uk?autoplay=1&amp;mute=1" data-source="https://youtu.be/0USWAsrY9uk"
 style="background-image: url('//img.youtube.com/vi/0USWAsrY9uk/sddefault.jpg');"></div>
<section style="background-image: url('//innopolis.university/upload/landing/944/7881@1x.jpg'); background-image: -webkit-image-set(url('//innopolis.university/upload/landing/944/7881@1x.jpg') 1x, url('//innopolis.university/upload/landing/c64/7881@2x.jpg') 2x);">
<h2>Кампус</h2><img src="/upload/landing/120/Visa_Inc._logo.svg@1x.png" alt=""></section></body></html>"""


def test_a_video_block_of_bitrix_and_a_banner_in_a_style_are_in_the_text():
    text = read(BITRIX, "https://hotel.innopolis.university/")[1]
    assert text.count("[▶ video](https://www.youtube.com/watch?v=0USWAsrY9uk)") == 1  # (the preview of the video is not a picture)
    assert text.count("![](https://innopolis.university/upload/landing/944/7881@1x.jpg)") == 1  # (the first address of the banner, once)
    assert "![](https://hotel.innopolis.university/upload/landing/120/Visa_Inc._logo.svg@1x.png)" in text  # (a partner's logo is content)
    assert sites.video_url("https://youtu.be/abc") == "https://www.youtube.com/watch?v=abc"
    assert sites.video_url("https://example.org/page") is None


def test_the_lines_every_page_repeats_are_a_page_of_their_own_which_each_page_names(monkeypatch, docs_db):
    menu = "- [Меню](https://hotel.innopolis.university/menu/)\nТелефон: +7 967 462 82 39"
    pages = {slug: (f"https://hotel.innopolis.university/{slug}/", f"{WORDS} {slug}\n{menu}") for slug in ("a", "b", "c", "d")}
    _site_root(monkeypatch, pages)
    docs = _documents()
    shared = docs["sites/hotel/_shared"]
    assert "Телефон: +7 967 462 82 39" in shared.body and "- [Меню](https://hotel.innopolis.university/menu/)" in shared.body
    page = docs["sites/hotel/a"].body
    assert "Телефон" not in page and "[sites/hotel/_shared](sites/hotel/_shared)" in page
    assert shared.meta["type"] == "page" and shared.meta["source_kind"] == "website"


TILDA = """<html><body>
<div class="t-bgimg" data-original="https://static.tildacdn.com/tild6236-6361-4035-b530-623565653634/_.png"
 style="background-image:url('https://thb.tildacdn.com/tild6236-6361-4035-b530-623565653634/-/resizeb/20x/_.png');"></div>
<div style="background-image:url('https://thb.tildacdn.com/tild3064-3161-4639-b230-333438613336/-/resizeb/20x/photo.jpg');"></div>
<img data-original="https://static.tildacdn.com/tild1111-2222-3333-4444-555555555555/a.jpg" src="https://thb.tildacdn.com/tild1111-2222-3333-4444-555555555555/-/resize/20x/a.jpg" alt="A">
</body></html>"""


def test_a_tilda_picture_is_the_file_and_not_its_twenty_pixel_preview():
    text = read(TILDA, "https://campuslife.innopolis.ru/")[1]
    assert "![](https://static.tildacdn.com/tild6236-6361-4035-b530-623565653634/_.png)" in text  # (data-original of the block)
    assert "![](https://static.tildacdn.com/tild3064-3161-4639-b230-333438613336/photo.jpg)" in text  # (no original: the preview's own file)
    assert text.count("![A](https://static.tildacdn.com/tild1111-2222-3333-4444-555555555555/a.jpg)") == 1 and text.count("![") == 3
    assert "thb.tildacdn" not in text


def test_a_page_of_an_events_site_is_about_the_year_its_title_or_address_names():
    campus, hotel = sites.SITES["campuslife"], sites.SITES["hotel"]
    assert sites.year_of(campus, "springball2022", "Spring Ball", "text") == 2022
    assert sites.year_of(campus, "ibc", "InnoBootCamp 2018", "text") == 2018
    assert sites.year_of(campus, "ibc", "IBC", "05.08-18.08 #InnoBootCamp2018 - Bachelors") == 2018  # (its first lines)
    assert sites.year_of(campus, "faq", "FAQ", "no year here" + " word" * 100 + " 2019") is None  # (not a year far into the text)
    assert sites.year_of(hotel, "prikaz-2021", "Приказ 2021", "text") is None  # (a site where a year says nothing of the page)


def test_a_page_of_a_past_year_says_so_and_the_search_gets_its_date_and_its_review_date(monkeypatch, docs_db):
    _site_root(monkeypatch, {"ball2022": ("https://hotel.innopolis.university/ball2022/", WORDS),
                             "now": ("https://hotel.innopolis.university/now/", WORDS + " now")})
    monkeypatch.setitem(sites.SITES, "hotel", dataclasses.replace(sites.SITES["hotel"], dated=True))
    docs = _documents()
    past, current = docs["sites/hotel/ball2022"], docs["sites/hotel/now"]
    assert past.meta["stale_after"] == "2023-01-01T00:00:00+00:00" and past.meta["sources"][0]["last_modified"] == "2022-01-01T00:00:00+00:00"
    assert "> Страница относится к 2022 году" in past.body
    assert "stale_after" not in current.meta and "Страница относится" not in current.body and current.meta["sources"][0]["last_modified"].startswith("2026")


def test_an_address_with_a_no_break_space_is_still_one_link():
    html = '<a href="/upload/Образец данных\u00a0несовершеннолетнего.docx">Образец</a>'
    text = read(html, "https://innopolis.university/sveden/apply/")[1]
    assert text == "[Образец](https://innopolis.university/upload/Образец%20данных%C2%A0несовершеннолетнего.docx)"
    assert sites.plain(text) == "Образец"


def test_a_large_site_shares_what_a_quarter_of_its_pages_repeat_a_small_one_what_half_do():
    section = [f"Menu\nSection menu\nPage {i}" for i in range(12)]  # (12 of 48: a quarter)
    others = [f"Menu\nPage {i}" for i in range(12, 48)]
    assert boilerplate(section + others) == {"Menu", "Section menu"}
    assert boilerplate(section[:6] + others[:6]) == {"Menu", "Section menu"}  # (12 pages: half of them, enough)
    assert boilerplate(section[:5] + others[:7]) == {"Menu"}  # (5 of 12 is less than half)


def test_a_title_that_many_pages_share_is_the_templates_and_the_first_heading_names_the_page(monkeypatch, docs_db):
    pages = {f"p{i}": (f"https://hotel.innopolis.university/p{i}/", f"![](https://x.org/{i}.jpg)\n### Имя {i}\n{WORDS} {i}") for i in range(10)}
    _site_root(monkeypatch, pages)
    docs_db.execute("UPDATE crawl_urls SET title = 'Шапка'")
    assert _documents()["sites/hotel/p3"].meta["title"] == "Имя 3"


def test_a_site_that_is_an_app_is_read_through_the_browser_and_the_others_through_http(monkeypatch):
    seen = []
    monkeypatch.setattr(sites, "render_page", lambda url: seen.append(url) or "<html><title>Clubs</title><h1>Clubs</h1></html>")

    class Client:
        def get(self, url):
            raise AssertionError("an app is not asked over http")

    app = sites.SITES["innohassle"]
    assert app.render and not sites.SITES["hotel"].render
    resp = sites.get_page(Client(), app, "https://innohassle.ru/clubs")
    assert resp.status_code == 200 and "Clubs" in resp.text and resp.headers["content-type"].startswith("text/html") and seen == ["https://innohassle.ru/clubs"]
    monkeypatch.setattr(sites, "render_page", lambda url: None)
    assert sites.get_page(Client(), app, "https://innohassle.ru/nothing").status_code == 404  # (the browser gave nothing: a page that is not there)
    assert not sites._taken(app, "https://innohassle.ru/admin/users") and sites._taken(app, "https://innohassle.ru/clubs/league")


def test_a_file_a_page_links_is_not_read_as_a_page_and_one_kept_as_a_page_leaves(monkeypatch, docs_db):
    """lyceuminnopolis.ru (render: true) links its sitemap.xml and a video: the browser showed them as pages, and the addresses
    of the sitemap reached the wiki as a page. A file is not asked for, an address the browser finds a file at is not kept, and
    a file kept as a page before leaves as a page that is not taken."""
    site = _unit(monkeypatch, render=True)
    links, asked = {"/": ["/a/", "/sitemap.xml", "/media/Promo.MP4", "/feed"], "/a/": []}, []

    def render(url):
        path = httpx.URL(url).path
        asked.append(path)
        if path == "/feed":
            raise sites.NotAPage(url, "application/rss+xml")  # (no extension says so: the answer does)
        menu = " ".join(f"<a href='{link}'>{link}</a>" for link in links[path])
        return f"<html><head><title>{path}</title></head><body><div>{menu}</div><h1>Страница {path}</h1><p>{WORDS}</p></body></html>"

    class Client:
        def get(self, url):
            raise AssertionError("an app is not asked over http")

    monkeypatch.setattr(sites, "render_page", render)
    assert not sites._taken(site, "https://unit.example/sitemap.xml") and not sites._taken(site, "https://unit.example/media/Promo.MP4")
    assert sites._taken(site, "https://unit.example/a/") and sites._taken(site, "https://unit.example/page12.html")
    assert sites.get_page(Client(), site, "https://unit.example/feed").headers["content-type"] == "application/rss+xml"
    asked.clear()
    old = h.page("https://unit.example/sitemap.xml", "unit", "sitemap-xml", f"{WORDS} the sitemap")  # (kept as a page before)
    h.crawl(Client())
    assert asked == ["/", "/a/", "/feed"] and set(h.by_slug("unit")) == {"home", "a", "sitemap-xml"}
    feed = h.row_of("https://unit.example/feed")
    assert (feed.state, feed.why) == ("tried", "not a page (application/rss+xml)")
    h.make_due(old.url)
    assert sites.read_page(Client(), h.row_of(old.url)) is True  # (it leaves: the documents of the site may change)
    assert (h.row_of(old.url).state, h.row_of(old.url).why) == ("gone", "not taken") and asked == ["/", "/a/", "/feed"]


ASKS_FOR_SCRIPTS = (f"<html><head><title>Физмат</title></head><body><noscript>You need to enable JavaScript to run this app.</noscript>"
                    f"<div id='root'><p>{WORDS}</p></div></body></html>")


def _answers(html: str):
    class Client:
        def get(self, url):
            return httpx.Response(200, text=html, headers={"content-type": "text/html; charset=utf-8", "last-modified": "Mon, 02 Nov 2026 10:00:00 GMT"},
                                  request=httpx.Request("GET", url))
    return Client()


def test_a_page_that_asks_for_javascript_or_has_no_words_is_read_in_the_browser_on_any_site(monkeypatch):
    shown = f"<html><head><title>Физмат прорыв</title></head><body><h1>Физмат прорыв</h1><p>{WORDS}</p></body></html>"
    seen = []
    monkeypatch.setattr(sites, "render_page", lambda url: seen.append(url) or shown)
    hotel, url = sites.SITES["hotel"], "https://hotel.innopolis.university/app/"
    assert not hotel.render
    for html in (ASKS_FOR_SCRIPTS, "<html><body><div id='app'></div><script src='/app.js'></script></body></html>"):  # (its <noscript> says so; an empty shell)
        resp = sites.get_page(_answers(html), hotel, url)
        assert resp.text == shown and resp.status_code == 200 and resp.headers["last-modified"] == "Mon, 02 Nov 2026 10:00:00 GMT"
        assert sites.read(resp.text, str(resp.url))[0] == "Физмат прорыв" and "You need to enable" not in sites.read(html, url)[1]
    assert seen == [url, url]
    page = f"<html><body><noscript><img src='https://mc.yandex.ru/watch/1'></noscript><p>{WORDS}</p></body></html>"  # (a counter's <noscript>: no word of scripts)
    assert sites.get_page(_answers(page), hotel, url).text == page and len(seen) == 2
    wall = "<html><head><title>Вы не робот?</title></head><body><noscript>У вас отключено исполнение JavaScript</noscript>smart-captcha</body></html>"
    monkeypatch.setattr(sites, "BOT_TRIES", 1)
    assert sites.get_page(_answers(wall), hotel, url).text == wall and len(seen) == 2  # (the browser does not pass a bot check either)


def test_a_page_the_browser_cannot_read_or_that_its_scripts_take_to_another_site_is_read_as_the_site_sent_it(monkeypatch):
    hotel, url = sites.SITES["hotel"], "https://hotel.innopolis.university/app/"
    for why in ("the browser did not read it", "its scripts lead to https://apply.innopolis.university/"):  # (Tilda's redirect block)
        def broken(url, why=why):
            raise httpx.TransportError(why)

        monkeypatch.setattr(sites, "render_page", broken)
        assert sites.get_page(_answers(ASKS_FOR_SCRIPTS), hotel, url).text == ASKS_FOR_SCRIPTS


def test_a_link_with_no_words_is_none_a_link_keeps_the_spaces_around_it_and_a_list_its_levels():
    html = ('<header><a href="/ru"><svg><use xlink:href="#logo"></use></svg></a><a href="/menu"><i class="icon-burger"></i></a></header>'
            '<p><a href="/hours">Время работы: </a>С 9:00 до 20:00</p>'
            '<ul><li><ul><li><a href="/about/">Об университете</a><ul><li><a href="/board/">Учредители</a></li></ul></li></ul></li></ul>'
            '<noscript>Redirect to URL: <a href="https://apply.innopolis.university/">https://apply.innopolis.university/</a></noscript>')
    _, text, links = read(html, "https://innopolis.university/ru")
    assert text.splitlines() == ["[Время работы:](https://innopolis.university/hours) С 9:00 до 20:00",
                                 "- [Об университете](https://innopolis.university/about/)", "  - [Учредители](https://innopolis.university/board/)"]
    assert "https://apply.innopolis.university/" in {u for u, _ in links}  # (the link of Tilda's redirect block is followed, its words are not the page's)


def test_a_form_is_no_words_of_the_page_but_its_links_are_followed_and_a_button_out_of_a_form_stays():
    html = ('<h2>Частые вопросы</h2><button class="faq__q">Есть ли бюджетные места?</button><p>Да, 300 мест на бакалавриате.</p>'
            '<form action="/send"><label>Ваше ФИО</label><input name="fio"><label><input type="checkbox"> Я согласен с '
            '<a href="/upload/politic.pdf">политикой</a></label><button>Отправить</button></form>')
    _, text, links = read(html, "https://sezinnopolis.ru/rentandservice/")
    assert text.splitlines() == ["## Частые вопросы", "Есть ли бюджетные места?", "Да, 300 мест на бакалавриате."]
    assert ("https://sezinnopolis.ru/upload/politic.pdf", "политикой") in links


def test_innohassle_keeps_the_pages_of_text_and_leaves_the_lists_of_data():
    app = sites.SITES["innohassle"]
    for path in ("", "start", "schedule", "schedule/core-courses", "maps", "workshops", "timetable", "tabletennis/players", "events", "events/p/6ab2",
                 "clubs", "clubs/innopolis-tatars", "music-room", "admin/users", "forms", "account",
                 "calendar", "search/ask", "sport", "sport/history", "when2meet", "student-affairs", "room-booking", "room-booking/rooms", "room-booking/list", "board-games", "timer"):  # (login walls)
        assert not sites._taken(app, f"https://innohassle.ru/{path}"), path
    for path in ("clubs/league", "clubs/new", "music-room/instructions", "sport/faq", "room-booking/rules", "extension", "guard", "dashboard", "about", "dorms", "printers", "scholarship"):
        assert sites._taken(app, f"https://innohassle.ru/{path}"), path


JS = ("x={url:`https://moodle.innopolis.university/my/`,resource:`Moodle`,resourceRu:`Moodle`,title:null,titleRu:null,description:`Access official course "
      "materials and tests.`,descriptionRu:`Материалы курсов.`,icon:`icon-[a]`,category:`Academic`,frequency:9},"
      "{url:`https://telegram.me/hoteluni`,resource:`Dormitory`,resourceRu:`Общежитие`,title:`Administration`,titleRu:`Администрация`,"
      "description:`Contact the hotel administration.`,descriptionRu:`Связь с администрацией.`,category:`Housing`,frequency:2}")  # (no icon in the second)


def test_the_whole_catalog_of_services_is_taken_from_the_script_of_the_dashboard():
    services = sites.service_catalog(JS)
    assert [s["name"] for s in services] == ["Moodle", "Dormitory"]
    text = sites.catalog_markdown(services)
    assert "### Academic" in text and "- [Moodle](https://moodle.innopolis.university/my/): Access official course materials and tests. / Материалы курсов." in text
    assert "- [Dormitory: Administration](https://telegram.me/hoteluni) (Общежитие: Администрация): Contact the hotel administration. / Связь с администрацией." in text

    class Client:
        def get(self, url):
            assert url == "https://innohassle.ru/assets/app.js"
            return type("R", (), {"text": JS})()

    page = '<script type="module" crossorigin src="/assets/app.js"></script>'
    out = sites.dashboard_with_catalog(Client(), page, "https://innohassle.ru/dashboard", "## Dashboard\n\n## All University Services\n\nAll\n\n## Filter\n\n[Sport](u)\n")
    assert out.startswith("## Dashboard") and "### Housing" in out and "[Sport](u)" not in out  # (the six cards the page shows give way to the catalog)


class _Site:
    """A client that answers every page with the same HTML (the page behind a login: the shell)."""

    def __init__(self, html):
        self.html = html

    def get(self, url):
        return httpx.Response(200, headers={"content-type": "text/html"}, text=self.html, request=httpx.Request("GET", url))


def test_a_page_under_two_addresses_is_kept_once(monkeypatch, docs_db):
    monkeypatch.setitem(sites.SITES, "courses", sites.Site("https://courses.example/", "ru", "courses", "^nothing$", sitemap=False, max_pages=10))
    h.put("https://courses.example/", "courses", pinned=True)
    home = '<html><title>Курсы</title><p>Курсы для взрослых и детей.</p><a href="/vue">Vue</a> <a href="/Vue">Vue</a></html>'
    vue = "<html><title>Vue</title><p>Курс по фреймворку Vue для тех, кто пишет интерфейсы.</p></html>"

    class Client:
        def get(self, url):
            html = home if url.rstrip("/").endswith("example") else vue
            return httpx.Response(200, headers={"content-type": "text/html"}, text=html, request=httpx.Request("GET", url))

    assert h.crawl(Client()) == 3
    assert sorted(h.by_slug("courses")) == ["home", "vue"]  # (Tilda answers '/Vue' with '/vue')
    other = h.row_of("https://courses.example/Vue")
    assert (other.state, other.slug) == ("tried", None) and other.why == "the words of https://courses.example/vue"


def test_the_pages_of_a_list_lead_to_its_news_and_a_link_without_a_language_is_in_the_page_s_one(monkeypatch, docs_db):
    site = sites.Site("https://city.example/ru/", "ru", "the city", r"^(?!(ru|en)(/|$))", sitemap=False, max_pages=20, bare=True, listing="page")
    monkeypatch.setitem(sites.SITES, "city", site)
    pages = {"/ru/": '<p>Город.</p><a href="/ru/news">Новости</a>',
             "/ru/news": '<p>Новости города.</p><a href="/news/a">Первая</a> <a href="/ru/news?page=2&per-page=10">2</a>',
             "/ru/news?page=2": '<p>Новости города.</p><a href="/news/b">Вторая</a> <a href="/ru/news?page=1&per-page=10">1</a>',
             "/ru/news/a": '<p>Первая новость.</p><a href="/services">Услуги</a>', "/ru/news/b": "<p>Вторая новость.</p>",
             "/ru/services": "<p>Услуги города.</p>"}
    asked = []

    class Client:
        def get(self, url):
            parts = httpx.URL(url)
            asked.append(path := parts.raw_path.decode())
            found = path in pages
            return httpx.Response(200 if found else 500, headers={"content-type": "text/html"}, text=f"<html>{pages.get(path, '')}</html>", request=httpx.Request("GET", url))

    h.put("https://city.example/ru/", "city", pinned=True)
    h.crawl(Client())
    assert sorted(h.by_slug("city")) == ["ru", "ru-news", "ru-news-a", "ru-news-b", "ru-services"]  # (the second page of the list is not a page)
    assert asked.count("/ru/news") == 1 and "/services" not in asked  # (its first page is the list itself)
    assert "[Услуги](https://city.example/ru/services)" in h.by_slug("city")["ru-news-a"].text
    second = h.row_of("https://city.example/ru/news?page=2")
    assert (second.state, second.text, second.slug) == ("ok", None, None)  # (read for its links, not kept)


def test_the_description_of_a_page_is_its_first_sentence_and_no_model_is_asked(monkeypatch, docs_db):
    sentence = "Students settle in the rooms of the campus and pay for the room every month."
    _site_root(monkeypatch, {"home": ("https://hotel.innopolis.university/", f"{sentence} {WORDS}")})
    monkeypatch.setattr(sites.httpx, "post", lambda *a, **k: pytest.fail("a model is asked"))
    meta = _documents()["sites/hotel/home"].meta
    assert meta["description"] == sentence and "tags" not in meta


def test_the_first_sentence_of_a_page_is_not_the_invitation_to_sign_in():
    words = "Use your Innopolis account to access InNoHassle services.\nAll university services of the student in one place, found by what they are for."
    assert sites.first_sentence("Dashboard", words) == "All university services of the student in one place, found by what they are for."


def test_a_person_can_name_the_readers_of_a_page(monkeypatch, docs_db):
    _site_root(monkeypatch, {"faq": ("https://hotel.innopolis.university/faq/", WORDS)})
    docs_db.execute("UPDATE crawl_urls SET audience = %s WHERE slug = 'faq'", (["student"],))
    assert _documents()["sites/hotel/faq"].meta["audience"] == ["student"]  # (not everyone: the person's word stands)


def test_a_site_behind_a_login_shows_nothing_of_the_person_and_stops_when_the_session_ends(tmp_path, monkeypatch):
    my = sites.SITES["my"]
    shown = "RU\n### Иван Иванов\nivan@innopolis.university\n## Меню\n[Магазин](https://my.innopolis.university/store)\n## Магазин\n## Носки\n200\nБаланс:\n15\n## Привет, Иван Иванов!\n## Уведомления\nУ вас 2 новых\nсообщения\n"
    kept = re.sub(my.private, "", shown, flags=re.M)
    assert "Иван" not in kept and "ivan@" not in kept and "Баланс" not in kept and "сообщения" not in kept
    assert "## Носки\n200" in kept and "## Меню" in kept
    taken = lambda path: sites._taken(my, f"https://my.innopolis.university/{path}")  # noqa: E731
    assert taken("store") and taken("event/details/abc") and not taken("store/purchases") and not taken("event/my") and not taken("event/history") and not taken("personal")
    monkeypatch.setenv(my.profile, str(tmp_path))
    monkeypatch.setattr(sites, "render_live", lambda url, profile: '<h1 class="x"><span>Авторизация</span></h1>')
    with pytest.raises(RuntimeError, match="session"):
        sites.get_page(None, my, "https://my.innopolis.university/store")


def test_a_page_that_does_not_exist_is_a_404_even_when_the_site_answers_200(tmp_path, monkeypatch):
    help_ = sites.SITES["help"]
    monkeypatch.setenv(help_.profile, str(tmp_path))
    monkeypatch.setattr(sites, "render_live", lambda url, profile: "<h1>Не найдено</h1><p>Эта страница не существует.</p>")
    assert sites.get_page(None, help_, "https://help.university.innopolis.ru/ru/VPN/x").status_code == 404
    monkeypatch.setattr(sites, "render_live", lambda url, profile: "<h1>VPN</h1>")
    assert sites.get_page(None, help_, "https://help.university.innopolis.ru/ru/VPN").status_code == 200


def test_a_document_named_by_its_file_is_titled_without_it_and_is_for_the_readers_of_its_site(docs_db):
    url = canonical("https://help.university.innopolis.ru/documents/регламент_процесса_организации_ит.pdf")
    h.document(url, "help", "Приказ ад-01.2019.12.23 регламент_процесса_организации_ит-поддержки.pdf", linked_by="help")
    (doc,) = sites.docs().values()
    assert doc["title"] == "Приказ ад-01.2019.12.23 регламент процесса организации ит-поддержки"
    assert doc["audience"] == ["staff"]


ATTRIBUTES = """<html><body>
<a href="/card/" class="c"><div><div class="t-bgimg" data-original="https://static.tildacdn.com/tild1/a.png"> </div><div><a href="/card/"> </a></div></div></a>
<iframe src="https://vkvideo.ru/video_ext.php?oid=-1&amp;id=2&amp;hash=x"></iframe>
<video controls><source data-src="/media/lazy.mp4?v=1&amp;q=hd" type="video/mp4"><track src="/media/lazy.vtt"></video>
<video controls><source src="/media/own.mp4"></video>
<picture><source data-src="/media/picture.webp"><img src="/media/picture.png" alt="p"></picture>
</body></html>"""


def test_what_lives_in_the_attributes_of_an_element_is_read_as_the_page_writes_it():
    text, links = read(ATTRIBUTES, "https://events.innopolis.university/")[1:]
    assert "[![](https://static.tildacdn.com/tild1/a.png)](https://events.innopolis.university/card/)" in text  # (a card whose link the parser closed before its picture)
    assert "[▶ video](https://vk.com/video-1_2)" in text  # (&amp; in the query of a frame is &)
    assert text.index("lazy.mp4") < text.index("own.mp4")  # (a <source> with a lazy data-src, one with a src: each video its own)
    assert ("https://events.innopolis.university/media/lazy.mp4?v=1&q=hd", "▶ video") in links  # (&amp; in a data-src too)
    assert "picture.webp" not in text  # (a <source> of a <picture> is not a video)
    assert ("https://vk.com/video-1_2", "▶ video") in links


def _fixture_site(name):
    """A site of tests/fixtures/sites.yaml, whatever a test has put in sites.SITES since."""
    from pathlib import Path

    return sites.make_site(sites.read_yaml(Path(__file__).with_name("fixtures") / "sites.yaml")["sites"][name])


def test_catalog_reloads_after_another_process_changes_the_catalog():
    sites.save_catalog({"sites": {}, "blocked": []})
    assert crawl.provider("https://lab.example/") is None
    sites.save_catalog({"sites": {"lab": {"base": "https://lab.example/", "language": "en", "about": "Lab", "skip": ""}}})
    assert crawl.provider("https://lab.example/") == "lab"
    sites.save_catalog({"sites": {}, "blocked": ["lab.example"]})
    assert crawl.provider("https://lab.example/") is None
    assert "lab" not in sites.SITES


def test_a_site_added_while_another_thread_walks_the_catalog_does_not_break_its_loop():
    walking = iter(sites.SITES.items())
    next(walking)
    sites.save_catalog({"sites": {**sites.load_config()["sites"], "lab": {"base": "https://lab.example/", "language": "en", "about": "Lab", "skip": ""}}})
    sites.reload_catalog()
    assert "lab" in sites.SITES
    assert list(walking)  # (the walk goes on over the catalog it started in: no "dictionary changed size during iteration")


def test_a_site_is_added_and_removed_from_the_command_line():
    from argparse import Namespace

    add = Namespace(catalog_action="add", name="lab", fields=["base=https://lab.example/", "language=en", "about=Lab", "aliases=[old.lab.example]"])
    sites.catalog_main(add)
    sites.reload_catalog()
    assert sites.SITES["lab"].aliases == ("old.lab.example",)
    sites.catalog_main(Namespace(catalog_action="remove", name="lab"))
    sites.reload_catalog()
    assert "lab" not in sites.SITES


def test_a_record_that_makes_no_site_is_refused_and_nothing_is_written():
    before = sites.load_config()
    with pytest.raises(ValueError, match="lab"):
        sites.save_catalog({"sites": {"lab": {"base": "https://lab.example/"}}})
    assert sites.load_config() == before


def test_the_export_prints_only_what_differs_from_the_defaults(docs_db, site_catalog, monkeypatch, capsys):
    monkeypatch.setattr(sites, "load_config", site_catalog.load_config)  # (the tables, not the catalog in memory)
    monkeypatch.setattr(sites, "save_catalog", site_catalog.save_catalog)
    record = {"base": "https://lab.example/", "language": "en", "about": "Lab", "skip": "", "sitemap": False, "max_pages": 7, "feeds": ["news/"]}
    sites.save_catalog({"sites": {"lab": record}, "blocked": ["x.example"]})
    sites.catalog_main(Namespace(catalog_action="export"))
    assert yaml.safe_load(capsys.readouterr().out) == {"sites": {"lab": record}, "blocked": ["x.example"]}
