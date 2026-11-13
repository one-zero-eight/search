"""Course programmes (РПД): what code reads from an archive's cell, a file name and the header of a programme (rpd.py)."""

from catix.wiki.sources.rpd import FACILITIES, latin, name_of, programme_label, semester_of


def test_course_programmes_use_the_shared_safe_archive_reader(tmp_path, monkeypatch):
    import hashlib
    import zipfile
    from catix.wiki.sources import archives, regulations, rpd

    monkeypatch.setattr(rpd, "ROOT", tmp_path)
    monkeypatch.setattr(rpd, "INDEX", tmp_path / "index.json")
    monkeypatch.setattr(rpd, "REMOTE", tmp_path / "archives.json")
    url = "https://innopolis.university/programme.zip"
    monkeypatch.setattr(rpd, "archives", lambda *a: [{"url": url, "ext": "zip", "title": "1 семестр", "year": 2026,
                                                    "programme": "бакалавриата: Информатика"}])
    folder = tmp_path / "archives"
    folder.mkdir()
    name = "Б1.О.18_Численные_методы.pdf"
    with zipfile.ZipFile(folder / f"{hashlib.sha1(url.encode()).hexdigest()[:10]}.zip", "w") as archive:
        archive.writestr(name, b"%PDF course")
    called = []
    unpack = archives.unpack
    monkeypatch.setattr(archives, "unpack", lambda path, dest: called.append(path) or unpack(path, dest))
    monkeypatch.setattr(regulations, "extract", lambda *a: ("1. Цель программы " * 70, "text layer", 0))
    assert rpd.fetch() == 1 and len(called) == 1
    row = next(iter(rpd.load().values()))
    assert row["member"] == name and row["code"] == "Б1.О.18" and row["name"] == "Численные методы"


def test_course_archive_download_is_bounded(tmp_path, monkeypatch):
    import pytest
    from catix.wiki.sources import archive_documents, archives, regulations, rpd

    monkeypatch.setattr(rpd, "ROOT", tmp_path)
    monkeypatch.setattr(rpd, "INDEX", tmp_path / "index.json")
    monkeypatch.setattr(rpd, "REMOTE", tmp_path / "archives.json")
    monkeypatch.setattr(regulations, "PAUSE", 0)
    monkeypatch.setattr(rpd.time, "sleep", lambda _: None)
    monkeypatch.setattr(rpd, "archives", lambda *a: [{"url": "https://innopolis.university/a.zip", "ext": "zip", "title": "Courses"}])
    monkeypatch.setattr(rpd.httpx, "get", lambda *a, **kw: pytest.fail("unbounded archive download"))
    def too_large(url, destination):
        destination.write_bytes(b"partial")
        raise archives.ArchiveError("limit", "too large")
    monkeypatch.setattr(archive_documents, "download", too_large)
    assert rpd.fetch() == 0
    assert not list((tmp_path / "archives").glob("*"))

HEADER = """Председатель Ученого совета
А.В. Гасников
РАБОЧАЯ ПРОГРАММА ДИСЦИПЛИНЫ (МОДУЛЯ)
Б1.О.18 Современные численные методы
оптимизации в обучении
09.03.01 Информатика и вычислительная
Направление подготовки
"""


def test_the_name_comes_from_the_header_not_the_cut_file_name():
    _, code, name = name_of(HEADER, "Визуализация_Б1.О.18_МОИИ_2025_Современные численные методы (5 с.)_25.12.2025.pdf")
    assert (code, name) == ("Б1.О.18", "Современные численные методы оптимизации в обучении")


def test_without_a_header_the_file_name_gives_the_code_and_the_name():
    assert name_of("", "Визуализация_Б1.В.ДВ.03.05_МОИИ_2025_Функциональный анализ (5 с.)_25.12.2025.pdf") == ("Рабочая программа", "Б1.В.ДВ.03.05", "Функциональный анализ")


def test_the_cell_gives_the_level_and_a_short_programme():
    level, label = programme_label("Передовая инженерная школа: бакалавриата: 09.03.01 Информатика и вычислительная техника; "
                                   "Направленность программы (профиль) – Инженерия информационных систем*")
    assert level == "бакалавриат"
    assert label == "ПИШ, бакалавриат 09.03.01 Информатика и вычислительная техника, профиль «Инженерия информационных систем»"
    assert programme_label("подготовки кадров высшей квалификации: 1.2.2. Математическое моделирование")[0] == "аспирантура"
    assert programme_label("Образовательная программа высшего образования - бакалавриата: 09.03.01 Информатика и вычислительная техника; "
                           "Направленность программы (профиль) – AI360: Инженерия данных") == (
        "бакалавриат", "бакалавриат 09.03.01 Информатика и вычислительная техника, профиль «AI360: Инженерия данных»")  # (no 'программа')
    assert programme_label("Образовательная программа среднего профессионального образования - программа подготовки специалистов среднего звена: "
                           "09.02.07 Информационные системы и программирование; Квалификация – Программист; База обучения - 9 классов") == (
        "СПО", "СПО 09.02.07 Информационные системы и программирование, квалификация «Программист», после 9 классов")
    assert programme_label("Образовательная программа среднего профессионального образования - программа подготовки специалистов среднего звена: "
                           "09.02.11 Разработка и управление программным обеспечением; Квалификация – Программист; Направленность - Разработка "
                           "информационных систем; База обучения - 9 классов")[1] == (
        "СПО 09.02.11 Разработка и управление программным обеспечением, квалификация «Программист», направленность «Разработка информационных систем», после 9 классов")


def test_the_semester_comes_from_the_archive_or_the_file():
    assert semester_of("7 семестр (документы подписаны ПЭП)", "x.pdf") == 7
    assert semester_of("Рабочие программы", "Визуализация_Б1.О.15_МОИИ_2025_Вычислительная математика (5 с.)_25.12.2025.pdf") == 5


def test_the_facilities_section_is_cut_up_to_the_next_section():
    text = "5. УЧЕБНО-МЕТОДИЧЕСКОЕ ОБЕСПЕЧЕНИЕ\nкниги\n6. МАТЕРИАЛЬНО-ТЕХНИЧЕСКОЕ ОБЕСПЕЧЕНИЕ\nаудитории\nпроекторы\n7. МЕТОДИЧЕСКИЕ И ОЦЕНОЧНЫЕ МАТЕРИАЛЫ\nкритерии"
    assert FACILITIES.sub("", text) == "5. УЧЕБНО-МЕТОДИЧЕСКОЕ ОБЕСПЕЧЕНИЕ\nкниги\n7. МЕТОДИЧЕСКИЕ И ОЦЕНОЧНЫЕ МАТЕРИАЛЫ\nкритерии"


def test_keys_are_latin():
    assert latin("Б1.О.15 Вычислительная математика") == "b1-o-15-vychislitelnaya-matematika"


def test_assessment_materials_are_named_by_their_own_header():
    text = "Приложение\nк рабочей программе дисциплины\nОПЦ.11 Компьютерные сети\nФОНД ОЦЕНОЧНЫХ СРЕДСТВ ПО ДИСЦИПЛИНЕ\nОПЦ.11 Компьютерные сети\n1. ПАСПОРТ ФОНДА\n"
    assert name_of(text, "ФОС_ОПЦ.11_Компьютерные_сети_Программист.pdf") == ("Фонд оценочных средств", "ОПЦ.11", "Компьютерные сети")
    assert name_of("", "ФОС_ОГСЭ.02_История.pdf") == ("Фонд оценочных средств", "ОГСЭ.02", "История")


def test_a_cut_caption_loses_its_cut_word():
    cell = "Образовательная программа среднего профессионального образования - программа подготовки специалистов среднего звена: 09.02.07 Информационные системы и программирование; К"
    assert programme_label(cell) == ("СПО", "СПО 09.02.07 Информационные системы и программирование")


def _listed(monkeypatch, listed):
    """The archives as the university's site links them: its documents, and the cell of the table each sits in (contexts_of)."""
    from catix.wiki.sources import sites

    monkeypatch.setattr(sites, "every_site", lambda: {"university": None})
    monkeypatch.setattr(sites, "load", lambda name: {"docs": {d["url"]: d["title"] for d in listed}, "contexts": {d["url"]: d["context"] for d in listed}})


def test_an_archive_keeps_the_address_it_was_read_under(monkeypatch):
    from catix.wiki.sources import rpd

    cell = "бакалавриата: 09.03.01 Информатика — 2025 — Рабочие программы дисциплин (модулей)"
    _listed(monkeypatch, [{"url": "https://x/%D0%A0%D0%9F%D0%94%201.7z", "ext": "7z", "title": "1 семестр", "context": cell}])
    monkeypatch.setattr(rpd, "load", lambda: {"rpd-1-x": {"archive": "https://x/РПД 1.7z"}})  # (the old listing wrote the spaces)
    (archive,) = rpd.archives()
    assert archive["url"] == "https://x/РПД 1.7z" and archive["year"] == 2025 and archive["programme"] == "бакалавриата: 09.03.01 Информатика"


def test_the_files_of_an_archive_stay_documents_until_rpd_has_read_it(tmp_path, monkeypatch):
    from catix.wiki.sources import regulations, rpd, sites

    cell = "бакалавриата: 09.03.01 Информатика — 2025 — Рабочие программы дисциплин (модулей)"
    url = "https://innopolis.university/upload/x/РПД%201.7z"
    _listed(monkeypatch, [{"url": url, "title": "1 семестр", "context": cell}])
    monkeypatch.setattr(regulations, "DOCS", {})
    monkeypatch.setattr(regulations, "linked_documents", lambda: {})
    monkeypatch.setattr(sites, "docs", lambda: {"site-university-x-rpd-1": {"title": "1 семестр", "url": url, "root": sites.ROOT, "section": "site/university", "ext": "7z"}})
    monkeypatch.setattr(rpd, "load", lambda: {})
    assert "site-university-x-rpd-1" not in regulations.all_docs()  # (new: rpd reads it, not the documents' reader too)
    monkeypatch.setattr(sites, "ROOT", tmp_path)
    monkeypatch.setattr(sites, "docs", lambda: {"site-university-x-rpd-1": {"title": "1 семестр", "url": url, "root": tmp_path, "section": "site/university", "ext": "7z"}})
    (tmp_path / "site-university-x-rpd-1.archive.json").write_text('{"status": "ready", "members": []}', encoding="utf-8")
    assert "site-university-x-rpd-1" in regulations.all_docs()  # (read as documents before rpd took it: its files are not lost meanwhile)
    monkeypatch.setattr(rpd, "load", lambda: {"rpd-1-x": {"archive": url, "sha256": "ab"}})
    assert "site-university-x-rpd-1" not in regulations.all_docs()  # (its courses are rpd's pages now)


def test_a_cohort_whose_links_are_dead_gives_way_to_the_one_before(monkeypatch):
    from catix.wiki.sources import rpd

    cell = "магистратуры: 09.04.01 Информатика; Направленность программы (профиль) – Кибербезопасность* — {} — Рабочие программы дисциплин"
    listed = [{"url": f"https://x/{y}-{s}.7z", "ext": "7z", "title": f"{s} семестр", "context": cell.format(y)} for y, n in ((2025, 3), (2026, 4)) for s in range(1, n + 1)]
    _listed(monkeypatch, listed)
    assert {a["year"] for a in rpd.archives()} == {2025, 2026}  # every cohort by default (WIKI_RPD_ALL_YEARS)
    assert {a["year"] for a in rpd.archives(all_years=False)} == {2026}
    dead = {f"https://x/2026-{s}.7z" for s in (1, 2, 3)}
    assert {a["year"] for a in rpd.archives(all_years=False, dead=dead)} == {2025}


def test_dates_and_stray_numbers_leave_a_name_from_the_file():
    assert name_of("", "Визуализация_2.1.2_Иностранный язык_2026_ММ_ 21.08.2026.pdf")[2] == "Иностранный язык"
    assert name_of("", "Визуализация_ЕН_02 Дискретная математика с элементами _Программист.pdf")[2] == "Дискретная математика с элементами"


def test_the_name_of_a_college_course_stops_before_its_cycle():
    text = "РАБОЧАЯ ПРОГРАММА ДИСЦИПЛИНЫ (МОДУЛЯ)\nСГ.04 Физическая культура\nсоциально-гуманитарного цикла\nПрограмма подготовки специалистов 15.02.10\n"
    assert name_of(text, "x.pdf")[1:] == ("СГ.04", "Физическая культура")


def test_the_sections_of_a_programme_are_headings():
    from catix.wiki.sources.rpd import to_markdown

    md = to_markdown("Шапка\n1. КРАТКАЯ ХАРАКТЕРИСТИКА ДИСЦИПЛИНЫ\nЦель курса\n2. ПЕРЕЧЕНЬ ПЛАНИРУЕМЫХ РЕЗУЛЬТАТОВ ОБУЧЕНИЯ\n1. Знать методы\n")
    assert "## 1. Краткая характеристика дисциплины" in md and "## 2. Перечень планируемых результатов обучения" in md
    assert "Цель курса" in md.split("## 2.")[0]


def test_a_heading_at_the_top_of_a_page_is_a_heading_too():
    from catix.wiki.sources.rpd import to_markdown

    assert "## 1. Краткая характеристика дисциплины (модуля)" in to_markdown("Тыртышников Е. Е., д.ф.-м.н.\f1. КРАТКАЯ ХАРАКТЕРИСТИКА ДИСЦИПЛИНЫ (МОДУЛЯ)\nЦель")


def test_a_checkout_without_the_downloads_keeps_the_pages(tmp_path, monkeypatch):
    from catix.wiki.sources import rpd

    cell = "магистратуры: 09.04.01 Информатика; Направленность программы (профиль) – Кибербезопасность* — 2026 — Рабочие программы дисциплин"
    _listed(monkeypatch, [{"url": "https://x/a.7z", "ext": "7z", "title": "1 семестр", "context": cell}])
    monkeypatch.setattr(rpd, "ROOT", tmp_path / "raw")
    monkeypatch.setattr(rpd, "DOCS", tmp_path / "wiki" / "raw")
    monkeypatch.setattr(rpd, "load", lambda: {"rpd-1-x": {"archive": "https://x/a.7z", "sha256": "0" * 64}})
    (tmp_path / "wiki" / "raw" / rpd.FOLDER).mkdir(parents=True)
    page = tmp_path / "wiki" / "raw" / rpd.FOLDER / "rpd-1-x.md"
    page.write_text("page")
    rpd.compile_all()
    assert page.read_text() == "page"


def test_a_name_from_a_windows_zip_is_read_as_text():
    import os

    from catix.wiki.sources.rpd import file_name

    windows = os.fsdecode("Программа.pdf".encode("cp866"))  # how Python sees a cp866 name: surrogates
    assert file_name(windows) == "Программа.pdf" and file_name("Программа.pdf") == "Программа.pdf"
