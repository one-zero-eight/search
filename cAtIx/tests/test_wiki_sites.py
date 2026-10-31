"""The sites of the university's services (sources/sites.py): what code reads from a page, which links it follows, which documents it hands on."""

import dataclasses
import hashlib

import httpx
import pytest

from catix.wiki.sources import sites
from catix.wiki.sources.sites import SITES, boilerplate, canonical, read

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
    lines = read(html, "https://innopolis.com/ru/life/housing/rental", SITES["city"].headings)[1].splitlines()
    assert lines == ["## Стоимость квартир", "от 17 000 ₽ в месяц", "3 минуты"]  # (a fact's title is no heading)
    assert read(html, "https://innopolis.com/ru/life/housing/rental")[1].splitlines()[0] == "Стоимость квартир"  # (another site: a div)


def test_one_file_written_three_ways_is_one_document_with_its_fullest_name():
    _, _, links = read(PAGE, "https://hotel.innopolis.university/studentaccommodation/")
    files = {canonical(url) for url, _ in links if url.endswith(".pdf")}
    assert len(files) == 1
    assert max((a for u, a in links if u.endswith(".pdf")), key=len) == "Правила проживания"


def test_past_events_old_copies_and_the_other_language_are_not_followed():
    campus, hotel = SITES["campuslife"], SITES["hotel"]
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


def test_the_documents_of_a_site_go_to_the_regulations_with_a_readable_key(tmp_path, monkeypatch):
    monkeypatch.setattr(sites, "ROOT", tmp_path)
    url = canonical("https://hotel.innopolis.university/upload/docs-hotel/Приложение к приказу_Правила _размещения 2025 год (2).pdf")
    sites.save("hotel", {"pages": {}, "docs": {url: "Правила"}})
    (key, doc), = sites.docs().items()
    assert key.startswith("site-hotel-") and "-prilozhenie-k-prikazu-pravila" in key
    assert doc["title"] == "Приложение к приказу Правила размещения 2025 год"  # the link text says too little: the file's name
    assert doc["section"] == "site/hotel" and doc["ext"] == "pdf"


def test_the_university_site_reads_the_pages_of_its_disclosure_section_too_and_has_an_english_copy():
    uni = SITES["university"]
    assert sites._taken(uni, "https://innopolis.university/campus")
    assert sites._taken(uni, "https://innopolis.university/en/about/")
    assert sites._taken(uni, "https://innopolis.university/sveden/employees/")  # (its text: sveden.py reads only the documents)
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


def test_a_link_leads_into_the_bundle_when_the_page_is_there_and_stays_live_otherwise():
    where = {sites.address("https://hotel.innopolis.university/rooms"): "/raw/sites/hotel/rooms.md"}
    body = ("[Номера](https://hotel.innopolis.university/rooms/#prices) [нет](https://hotel.innopolis.university/zayavka/) "
            "[![Номер](https://hotel.innopolis.university/rooms)](https://hotel.innopolis.university/rooms/)")
    assert sites.resolve(body, where) == ("[Номера](/raw/sites/hotel/rooms.md) [нет](https://hotel.innopolis.university/zayavka/) "
                                         "[![Номер](https://hotel.innopolis.university/rooms)](/raw/sites/hotel/rooms.md)")  # (a picture keeps its own address)


WORDS = " ".join(f"слово{chr(1072 + i % 26)}{chr(1072 + i // 26)}ы" for i in range(40))


def _site_root(tmp_path, monkeypatch, pages):
    monkeypatch.setattr(sites, "ROOT", tmp_path / "cache")
    monkeypatch.setattr(sites, "DOCS", tmp_path / "wiki" / "raw")
    monkeypatch.setattr(sites, "SITES", {"hotel": sites.SITES["hotel"]})
    index = {"pages": {}, "docs": {}}
    for slug, (url, text) in pages.items():
        (tmp_path / "cache" / "hotel").mkdir(parents=True, exist_ok=True)
        (tmp_path / "cache" / "hotel" / f"{slug}.md").write_text(text, encoding="utf-8")
        index["pages"][slug] = {"url": url, "title": slug.title(), "sha256": "a" * 64, "fetched_at": "2026-10-30T00:00:00+00:00"}
    sites.save("hotel", index)
    return tmp_path / "wiki" / "raw" / "sites"


def test_the_pages_of_a_site_go_to_a_folder_of_their_own_and_link_each_other(tmp_path, monkeypatch):
    out = _site_root(tmp_path, monkeypatch, {
        "home": ("https://hotel.innopolis.university/", f"{WORDS} [Номера](https://hotel.innopolis.university/rooms/) ![Фото](https://cdn.example/a.jpg)"),
        "rooms": ("https://hotel.innopolis.university/rooms/", f"{WORDS} [На главную](https://hotel.innopolis.university/) [Скрытая](https://hotel.innopolis.university/gone/)"),
    })
    sites.compile_all()
    home, rooms = (out / "hotel" / "home.md").read_text(encoding="utf-8"), (out / "hotel" / "rooms.md").read_text(encoding="utf-8")
    assert "[Номера](/raw/sites/hotel/rooms.md)" in home and "![Фото](https://cdn.example/a.jpg)" in home
    assert "[На главную](/raw/sites/hotel/home.md)" in rooms and "[Скрытая](https://hotel.innopolis.university/gone/)" in rooms


def test_a_link_to_the_old_name_of_a_site_leads_to_its_page_when_there_is_one(tmp_path, monkeypatch):
    out = _site_root(tmp_path, monkeypatch, {
        "home": ("https://hotel.innopolis.university/", f"{WORDS} [Номера](https://hotel.innopolis.ru/rooms/) [Старое](https://hotel.innopolis.ru/old/)"),
        "rooms": ("https://hotel.innopolis.university/rooms/", WORDS),
    })
    monkeypatch.setattr(sites, "SITES", {"hotel": dataclasses.replace(SITES["hotel"], aliases=("hotel.innopolis.ru",))})
    sites.compile_all()
    home = (out / "hotel" / "home.md").read_text(encoding="utf-8")
    assert "[Номера](/raw/sites/hotel/rooms.md)" in home and "[Старое](https://hotel.innopolis.ru/old/)" in home  # (no page: the link as written)


def test_the_name_of_the_site_leaves_the_titles_and_the_way_to_the_next_post_leaves_the_text(tmp_path, monkeypatch):
    centre = " — Центр робототехники"
    out = _site_root(tmp_path, monkeypatch, {f"p{i}": (f"https://hotel.innopolis.university/p{i}/", f"{WORDS} {i}\n[Дальше](https://hotel.innopolis.university/p{i + 1}/)") for i in range(6)})
    index = sites.load("hotel")
    for i, page in enumerate(index["pages"].values()):
        page["title"] = f"Новость {i}{centre}"
    sites.save("hotel", index)
    monkeypatch.setattr(sites, "SITES", {"hotel": dataclasses.replace(SITES["hotel"], drop=SITES["robotics"].drop)})
    sites.compile_all()
    page = (out / "hotel" / "p0.md").read_text(encoding="utf-8")
    assert 'title: "Новость 0"' in page and "Дальше" not in page


def test_a_site_may_keep_its_sitemap_elsewhere(tmp_path, monkeypatch):
    monkeypatch.setattr(sites, "ROOT", tmp_path)
    monkeypatch.setattr(sites, "PAUSE", 0)
    site = sites.Site("https://wp.example/", "ru", "a centre", r"^nothing$", sitemap="wp-sitemap.xml", max_pages=10)
    maps = {"/wp-sitemap.xml": "<sitemapindex><sitemap><loc>https://wp.example/wp-sitemap-posts-team-1.xml</loc></sitemap></sitemapindex>",
            "/wp-sitemap-posts-team-1.xml": "<urlset><url><loc>https://wp.example/team/ivanov/</loc></url></urlset>"}

    class Client:
        def get(self, url):
            path = httpx.URL(url).path
            if path in maps:
                return httpx.Response(200, headers={"content-type": "application/xml"}, text=maps[path], request=httpx.Request("GET", url))
            return httpx.Response(200, headers={"content-type": "text/html"}, text=f"<html><p>{WORDS} {path}</p></html>", request=httpx.Request("GET", url))

    sites.fetch_site("wp", site, Client())
    assert "team-ivanov" in sites.load("wp")["pages"]  # (no link leads there: the sitemap does)


def test_a_news_item_ends_where_the_related_news_begin_and_says_its_heading_and_date_once(tmp_path, monkeypatch):
    out = _site_root(tmp_path, monkeypatch, {
        "rooms": ("https://hotel.innopolis.university/rooms/", f"29 октября 2026\n## Rooms\n29 октября 2026\n{WORDS}\n[Читать далее](https://hotel.innopolis.university/next/)\n"
                                                                "Новости по теме\n[Другая новость дня](https://hotel.innopolis.university/other/)"),
    })
    monkeypatch.setattr(sites, "SITES", {"hotel": dataclasses.replace(SITES["hotel"], end=SITES["media"].end)})
    sites.compile_all()
    body = (out / "hotel" / "rooms.md").read_text(encoding="utf-8").split("---\n", 2)[2]
    assert body.count("29 октября 2026") == 1 and "## Rooms" not in body and WORDS in body
    assert "Читать далее" not in body and "Другая новость дня" not in body


def test_a_page_moved_into_its_folder_leaves_no_old_file(tmp_path, monkeypatch):
    out = _site_root(tmp_path, monkeypatch, {"home": ("https://hotel.innopolis.university/", WORDS)})
    sites.compile_all()
    (out / "hotel-home.md").write_text((out / "hotel" / "home.md").read_text(encoding="utf-8"), encoding="utf-8")
    sites.compile_all()
    assert (out / "hotel" / "home.md").exists() and not (out / "hotel-home.md").exists()


def test_a_link_to_a_document_of_a_site_leads_to_its_page_of_regulations_once_there_is_one(tmp_path, monkeypatch):
    url = "https://hotel.innopolis.university/upload/docs-hotel/Правила проживания.pdf"
    out = _site_root(tmp_path, monkeypatch, {"home": ("https://hotel.innopolis.university/", f"{WORDS} [Правила]({url.replace(' ', '%20')})")})
    index = sites.load("hotel")
    index["docs"] = {sites.canonical(url): "Правила проживания"}
    sites.save("hotel", index)
    sites.compile_all()
    assert f"({url.replace(' ', '%20')})" in (out / "hotel" / "home.md").read_text(encoding="utf-8")  # (not converted yet: the site's own file)
    (key,) = sites.docs()
    (tmp_path / "wiki" / "raw" / "regulations").mkdir(parents=True)
    (tmp_path / "wiki" / "raw" / "regulations" / f"{key}.md").write_text("x", encoding="utf-8")
    sites.compile_all()
    assert f"[Правила](/raw/regulations/{key}.md)" in (out / "hotel" / "home.md").read_text(encoding="utf-8")


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


def test_the_lines_every_page_repeats_are_a_page_of_their_own_which_each_page_names(tmp_path, monkeypatch):
    menu = "- [Меню](https://hotel.innopolis.university/menu/)\nТелефон: +7 967 462 82 39"
    pages = {slug: (f"https://hotel.innopolis.university/{slug}/", f"{WORDS} {slug}\n{menu}") for slug in ("a", "b", "c", "d")}
    out = _site_root(tmp_path, monkeypatch, pages)
    sites.compile_all()
    shared = (out / "hotel" / "_shared.md").read_text(encoding="utf-8")
    assert "Телефон: +7 967 462 82 39" in shared and "- [Меню](https://hotel.innopolis.university/menu/)" in shared
    page = (out / "hotel" / "a.md").read_text(encoding="utf-8")
    assert "Телефон" not in page and "[/raw/sites/hotel/_shared.md](/raw/sites/hotel/_shared.md)" in page
    assert "type: page" in shared and "source_kind: website" in shared


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
    campus, hotel = SITES["campuslife"], SITES["hotel"]
    assert sites.year_of(campus, "springball2022", "Spring Ball", "text") == 2022
    assert sites.year_of(campus, "ibc", "InnoBootCamp 2018", "text") == 2018
    assert sites.year_of(campus, "ibc", "IBC", "05.08-18.08 #InnoBootCamp2018 - Bachelors") == 2018  # (its first lines)
    assert sites.year_of(campus, "faq", "FAQ", "no year here" + " word" * 100 + " 2019") is None  # (not a year far into the text)
    assert sites.year_of(hotel, "prikaz-2021", "Приказ 2021", "text") is None  # (a site where a year says nothing of the page)


def test_a_page_of_a_past_year_says_so_and_the_search_gets_its_date_and_its_review_date(tmp_path, monkeypatch):
    out = _site_root(tmp_path, monkeypatch, {"ball2022": ("https://hotel.innopolis.university/ball2022/", WORDS),
                                             "now": ("https://hotel.innopolis.university/now/", WORDS + " now")})
    monkeypatch.setitem(sites.SITES, "hotel", dataclasses.replace(sites.SITES["hotel"], dated=True))
    sites.compile_all()
    past, current = (out / "hotel" / "ball2022.md").read_text(encoding="utf-8"), (out / "hotel" / "now.md").read_text(encoding="utf-8")
    assert "stale_after: \"2023-01-01T00:00:00+00:00\"" in past and "last_modified: \"2022-01-01T00:00:00+00:00\"" in past
    assert "> Страница относится к 2022 году" in past
    assert "stale_after" not in current and "Страница относится" not in current and "last_modified: \"2026" in current


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


def test_a_title_that_many_pages_share_is_the_templates_and_the_first_heading_names_the_page(tmp_path, monkeypatch):
    pages = {f"p{i}": (f"https://hotel.innopolis.university/p{i}/", f"![](https://x.org/{i}.jpg)\n### Имя {i}\n{WORDS} {i}") for i in range(10)}
    out = _site_root(tmp_path, monkeypatch, pages)
    index = sites.load("hotel")
    for p in index["pages"].values():
        p["title"] = "Шапка"
    sites.save("hotel", index)
    sites.compile_all()
    assert 'title: "Имя 3"' in (out / "hotel" / "p3.md").read_text(encoding="utf-8")


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


def test_innohassle_keeps_the_pages_of_text_and_leaves_the_lists_of_data():
    app = SITES["innohassle"]
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


def test_a_page_a_person_wrote_is_not_written_over_by_the_crawl(tmp_path, monkeypatch):
    monkeypatch.setattr(sites, "ROOT", tmp_path)
    monkeypatch.setattr(sites, "PAUSE", 0)
    site = sites.Site("https://app.example/", "en", "an app", "^nothing$", sitemap=False, max_pages=3)
    shell = "<html><title>My bookings</title><h1>Bookings</h1><h2>Sign in to get access</h2><p>Use your account.</p></html>"
    sites.fetch_site("app", site, _Site(shell))
    cache = next((tmp_path / "app").glob("*.md"))
    assert sites.load("app")["pages"][cache.stem]["file_sha"]
    cache.write_text("## Booking rules\nStudents can book rooms up to 3 hours.\n", encoding="utf-8")  # (a person put the page behind the login in)
    sites.fetch_site("app", site, _Site(shell.replace("Bookings", "Bookings today")))  # (the page changed, the crawl sees the shell)
    assert cache.read_text(encoding="utf-8") == "## Booking rules\nStudents can book rooms up to 3 hours.\n"
    page = sites.load("app")["pages"][cache.stem]
    assert page["manual"] and page["sha256"] == hashlib.sha256(sites.plain(cache.read_text(encoding="utf-8")).encode()).hexdigest()
    sites.fetch_site("app", site, _Site(shell))  # (and the next time too: the mark stays)
    assert "Booking rules" in cache.read_text(encoding="utf-8")


def test_a_page_under_two_addresses_is_kept_once(tmp_path, monkeypatch):
    monkeypatch.setattr(sites, "ROOT", tmp_path)
    monkeypatch.setattr(sites, "PAUSE", 0)
    site = sites.Site("https://courses.example/", "ru", "courses", "^nothing$", sitemap=False, max_pages=10)
    home = '<html><title>Курсы</title><p>Курсы для взрослых и детей.</p><a href="/vue">Vue</a> <a href="/Vue">Vue</a></html>'
    vue = "<html><title>Vue</title><p>Курс по фреймворку Vue для тех, кто пишет интерфейсы.</p></html>"

    class Client:
        def get(self, url):
            html = home if url.rstrip("/").endswith("example") else vue
            return httpx.Response(200, headers={"content-type": "text/html"}, text=html, request=httpx.Request("GET", url))

    sites.fetch_site("courses", site, Client())
    assert sorted(sites.load("courses")["pages"]) == ["home", "vue"]  # (Tilda answers '/Vue' with '/vue')


def test_the_pages_of_a_list_lead_to_its_news_and_a_link_without_a_language_is_in_the_page_s_one(tmp_path, monkeypatch):
    monkeypatch.setattr(sites, "ROOT", tmp_path)
    monkeypatch.setattr(sites, "PAUSE", 0)
    site = sites.Site("https://city.example/ru/", "ru", "the city", r"^(?!(ru|en)(/|$))", sitemap=False, max_pages=20, bare=True, listing="page")
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

    sites.fetch_site("city", site, Client())
    assert sorted(sites.load("city")["pages"]) == ["ru", "ru-news", "ru-news-a", "ru-news-b", "ru-services"]  # (the second page of the list is not a page)
    assert asked.count("/ru/news") == 1 and "/services" not in asked  # (its first page is the list itself)
    assert "[Услуги](https://city.example/ru/services)" in (tmp_path / "city" / "ru-news-a.md").read_text(encoding="utf-8")


def test_the_description_of_a_page_is_its_first_sentence_and_no_model_is_asked(tmp_path, monkeypatch):
    sentence = "Students settle in the rooms of the campus and pay for the room every month."
    out = _site_root(tmp_path, monkeypatch, {"home": ("https://hotel.innopolis.university/", f"{sentence} {WORDS}")})
    monkeypatch.setattr(sites.httpx, "post", lambda *a, **k: pytest.fail("a model is asked"))
    sites.compile_all()
    home = (out / "hotel" / "home.md").read_text(encoding="utf-8")
    assert f'description: "{sentence}"' in home and "tags:" not in home and "pending" not in home


def test_the_first_sentence_of_a_page_is_not_the_invitation_to_sign_in():
    words = "Use your Innopolis account to access InNoHassle services.\nAll university services of the student in one place, found by what they are for."
    assert sites.first_sentence("Dashboard", words) == "All university services of the student in one place, found by what they are for."


def test_the_index_of_the_sites_lists_the_pages_of_every_site_folder(tmp_path):
    from catix.wiki import compile as wc

    for site, slug in (("hotel", "home"), ("campuslife", "faq")):
        page = tmp_path / "raw" / "sites" / site / f"{slug}.md"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(f'---\ntype: page\ntitle: "{slug} of {site}"\ndescription: "d"\nsection: "site/{site}"\n---\n\n# {slug}\n', encoding="utf-8")
    wc.write_index(wc.concepts(tmp_path), tmp_path)
    listing = (tmp_path / "raw" / "sites" / "index.md").read_text(encoding="utf-8")
    assert "(/raw/sites/hotel/home.md)" in listing and "(/raw/sites/campuslife/faq.md)" in listing
    assert "## site/hotel" in listing and "## site/campuslife" in listing  # (a section for every site)
    assert "(/raw/sites/index.md): " in (tmp_path / "index.md").read_text(encoding="utf-8")


def test_a_person_can_name_the_readers_of_a_page(tmp_path, monkeypatch):
    out = _site_root(tmp_path, monkeypatch, {"faq": ("https://hotel.innopolis.university/faq/", WORDS)})
    index = sites.load("hotel")
    index["pages"]["faq"]["audience"] = ["student"]
    sites.save("hotel", index)
    sites.compile_all()
    assert 'audience: ["student"]' in (out / "hotel" / "faq.md").read_text(encoding="utf-8")  # (not everyone: the person's word stands)
