from catix.wiki.sources.regulations import to_markdown


def test_numbered_clauses_and_chapters():
    md = to_markdown("1. Общие положения\n\n1.1. Первый пункт\nпродолжение строки.\n\n1.2. Второй пункт.")
    assert md.split("\n\n") == ["## 1. Общие положения", "**1.1.** Первый пункт продолжение строки.", "**1.2.** Второй пункт."]


def test_flat_numbering_has_clauses_not_chapters():
    md = to_markdown("1. Настоящее Положение определяет порядок\nперехода обучающихся.\n\n2. Положение обязательно для всех.")
    assert md.split("\n\n") == ["**1.** Настоящее Положение определяет порядок перехода обучающихся.", "**2.** Положение обязательно для всех."]


def test_table_rows_from_layout_gaps_and_page_numbers():
    md = to_markdown("Буква        Оценка\nA            отлично\n\n12\n")
    assert md == "| Буква | Оценка |\n| --- | --- |\n| A | отлично |"


def test_audience_is_kept_to_the_closed_set():
    from catix.wiki.compile import AUDIENCES, clean_audience

    assert clean_audience("Students, teachers and the rector") == ["student", "teacher"]
    assert clean_audience("everyone") == list(AUDIENCES)  # nothing usable: the page is for all readers


def test_the_date_of_a_document_is_its_own_not_that_of_a_law_it_cites():
    from catix.wiki.sources.regulations import issued_of

    text = "ПРИКАЗ\n\n30 июня 2025 г.\n\nВ соответствии с Федеральным законом от 29 декабря 2012 года № 273-ФЗ ..."
    assert issued_of(text, "fallback") == "2025-06-30T00:00:00+03:00"
    assert issued_of("Утверждено приказом от 01.09.2024 № 5, закон от 29 декабря 2012 года", "f").startswith("2024-09-01")
    assert issued_of("Без дат.", "fallback") == "fallback"


def test_a_table_found_in_the_pdf_keeps_its_rows_and_merged_cells_take_the_value_above():
    from catix.wiki.sources.regulations import table_markdown, to_markdown

    rows = [["Код", "Профиль", "Испытание", None], ["09.04.01", "Робототехника", "Тестирование", None], [None, None, "Собеседование", None]]
    md = table_markdown(rows)
    assert md.splitlines() == ["| Код | Профиль | Испытание |", "| --- | --- | --- |",
                               "| 09.04.01 | Робототехника | Тестирование |", "| 09.04.01 | Робототехника | Собеседование |"]
    text = f"**1.1.** До таблицы.\n\n{md}\n\n{md}\nПосле таблицы."
    blocks = to_markdown(text).split("\n\n")
    assert blocks[1] == md and blocks[2] == md and blocks[3] == "После таблицы."  # two tables stay two, the text after stays after
