"""The sites of the university's services (sources/sites.py): what code reads from a page, which links it follows, which documents it hands on."""

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


def test_one_file_written_three_ways_is_one_document_with_its_fullest_name():
    _, _, links = read(PAGE, "https://hotel.innopolis.university/studentaccommodation/")
    files = {canonical(url) for url, _ in links if url.endswith(".pdf")}
    assert len(files) == 1
    assert max((a for u, a in links if u.endswith(".pdf")), key=len) == "Правила проживания"


def test_past_events_old_copies_and_the_other_language_are_not_followed():
    campus, hotel = SITES["campuslife"], SITES["hotel"]
    assert sites._taken(campus, "https://campuslife.innopolis.ru/handbook")
    assert not sites._taken(campus, "https://campuslife.innopolis.ru/springball2022")
    assert not sites._taken(campus, "https://campuslife.innopolis.ru/handbook_old")
    assert not sites._taken(hotel, "https://hotel.innopolis.university/en/contacts/")
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
