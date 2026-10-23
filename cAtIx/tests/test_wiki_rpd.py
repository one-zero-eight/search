"""Course programmes (РПД): what code reads from an archive's cell, a file name and the header of a programme (rpd.py)."""

from catix.wiki.rpd import FACILITIES, latin, name_of, programme_label, semester_of

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


def test_a_cohort_whose_links_are_dead_gives_way_to_the_one_before(monkeypatch):
    from catix.wiki import rpd

    cell = "магистратуры: 09.04.01 Информатика; Направленность программы (профиль) – Кибербезопасность* — {} — Рабочие программы дисциплин"
    listed = [{"url": f"https://x/{y}-{s}.7z", "ext": "7z", "title": f"{s} семестр", "context": cell.format(y)} for y, n in ((2025, 3), (2026, 4)) for s in range(1, n + 1)]
    monkeypatch.setattr(rpd.sveden, "load", lambda path: listed)
    assert {a["year"] for a in rpd.archives()} == {2026}
    dead = {f"https://x/2026-{s}.7z" for s in (1, 2, 3)}
    assert {a["year"] for a in rpd.archives(dead=dead)} == {2025}


def test_dates_and_stray_numbers_leave_a_name_from_the_file():
    assert name_of("", "Визуализация_2.1.2_Иностранный язык_2026_ММ_ 21.08.2026.pdf")[2] == "Иностранный язык"
    assert name_of("", "Визуализация_ЕН_02 Дискретная математика с элементами _Программист.pdf")[2] == "Дискретная математика с элементами"


def test_the_name_of_a_college_course_stops_before_its_cycle():
    text = "РАБОЧАЯ ПРОГРАММА ДИСЦИПЛИНЫ (МОДУЛЯ)\nСГ.04 Физическая культура\nсоциально-гуманитарного цикла\nПрограмма подготовки специалистов 15.02.10\n"
    assert name_of(text, "x.pdf")[1:] == ("СГ.04", "Физическая культура")


def test_the_sections_of_a_programme_are_headings():
    from catix.wiki.rpd import to_markdown

    md = to_markdown("Шапка\n1. КРАТКАЯ ХАРАКТЕРИСТИКА ДИСЦИПЛИНЫ\nЦель курса\n2. ПЕРЕЧЕНЬ ПЛАНИРУЕМЫХ РЕЗУЛЬТАТОВ ОБУЧЕНИЯ\n1. Знать методы\n")
    assert "## 1. Краткая характеристика дисциплины" in md and "## 2. Перечень планируемых результатов обучения" in md
    assert "Цель курса" in md.split("## 2.")[0]


def test_a_heading_at_the_top_of_a_page_is_a_heading_too():
    from catix.wiki.rpd import to_markdown

    assert "## 1. Краткая характеристика дисциплины (модуля)" in to_markdown("Тыртышников Е. Е., д.ф.-м.н.\f1. КРАТКАЯ ХАРАКТЕРИСТИКА ДИСЦИПЛИНЫ (МОДУЛЯ)\nЦель")
