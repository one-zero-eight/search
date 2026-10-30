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


def test_a_cell_merged_across_columns_heads_a_group_of_rows_and_is_not_the_row_above_again():
    from catix.wiki.sources.regulations import table_markdown

    rows = [["№", "Услуга", "Периодичность"], ["Расходные материалы", None, None], ["4", "Мыло", "при заезде"]]
    wide = [[False] * 3, [False, True, True], [False] * 3]
    assert table_markdown(rows, wide).splitlines()[2:] == ["| Расходные материалы |  |  |", "| 4 | Мыло | при заезде |"]


def test_a_table_of_one_column_is_text_and_its_clauses_are_clauses():
    # a regulation in a frame came out as a table of one column, and its clauses as rows: '| 1.1. Колледж ... |'
    from catix.wiki.sources.regulations import table_markdown, to_markdown

    rows = [["1.1. Колледж является структурным"], ["подразделением Университета."], [None], ["1.2. Настоящее Положение регулирует"], ["деятельность Колледжа."]]
    assert to_markdown(table_markdown(rows)).split("\n\n") == ["**1.1.** Колледж является структурным подразделением Университета.",
                                                             "**1.2.** Настоящее Положение регулирует деятельность Колледжа."]


def odl_item(content: str, *more: str) -> dict:
    return {"type": "list item", "content": content, "kids": [{"type": "paragraph", "content": m} for m in more]}


def test_opendataloader_text_keeps_a_clause_on_its_own_line_and_its_item_whole():
    # joining lines itself, opendataloader glued '6.1.' to its chapter's heading and '10.13.' to the clause before it
    from catix.wiki.sources.opendataloader import text_of
    from catix.wiki.sources.regulations import to_markdown

    doc = {"kids": [
        {"type": "heading", "content": "6. Основные права и обязанности Работников\n6.1. Работник имеет право на:"},
        {"type": "list", "list items": [odl_item("– заключение трудового договора;"), odl_item("– отдых.")]},
        {"type": "list", "list items": [odl_item("10.12. Время простоя по вине Работника не", "оплачивается.\n10.13. Обеспечение повышения уровня")]},
    ]}
    blocks = to_markdown(text_of(doc, set())).split("\n\n")
    assert blocks[0] == "## 6. Основные права и обязанности Работников"
    assert blocks[1] == "**6.1.** Работник имеет право на:"
    assert "**10.12.** Время простоя по вине Работника не оплачивается." in blocks
    assert "**10.13.** Обеспечение повышения уровня" in blocks


def test_a_word_broken_at_the_end_of_a_line_is_whole_as_the_documents_write_it():
    from catix.wiki.sources.opendataloader import join_broken, joined

    words = {"консорциума", "научно-технической", "научно", "технической", "организации", "программы", "про", "граммы", "социально", "культурной"}
    assert join_broken("консор", "циума,", words) == "консорциума,"
    assert join_broken("научно", "технической", words) == "научно-технической"  # the compound the documents write
    assert join_broken("органи", "зации", words) == "организации"
    assert join_broken("про", "граммы", words) == "программы"  # both halves are words, but the documents write it whole
    assert join_broken("социально", "культурной", words) == "социально-культурной"  # neither form known: two words keep it
    assert join_broken("Папуа", "Новая", words) == "Папуа-Новая"
    assert joined(["в рамках консор-", "циума, что помогает"], words) == ["в рамках консорциума, что помогает"]
    assert joined(["список -", "пункт"], words) == ["список -", "пункт"]  # a dash, not a broken word


def test_an_opendataloader_table_keeps_merged_cells_and_a_frame_is_text():
    from catix.wiki.sources.opendataloader import text_of

    def cell(r, c, text, rs=1, cs=1):
        return {"type": "table cell", "row number": r, "column number": c, "row span": rs, "column span": cs,
                "kids": [{"type": "paragraph", "content": text}]}

    table = {"type": "table", "number of rows": 3, "number of columns": 3, "rows": [
        {"cells": [cell(1, 1, "Код"), cell(1, 2, "Испытание"), cell(1, 3, "Баллы")]},
        {"cells": [cell(2, 1, "09.04.01", rs=2), cell(2, 2, "Тестирование"), cell(2, 3, "60")]},
        {"cells": [cell(3, 2, "Собеседование", cs=2)]},
    ]}
    frame = {"type": "table", "number of rows": 2, "number of columns": 1, "rows": [
        {"cells": [cell(1, 1, "1.1. Колледж является структурным")]}, {"cells": [cell(2, 1, "подразделением Университета.")]}]}
    text = text_of({"kids": [table, frame]}, set())
    assert text.split("\n\n")[0].splitlines()[2:] == ["| 09.04.01 | Тестирование | 60 |", "| 09.04.01 | Собеседование |  |"]
    assert text.split("\n\n")[1] == "1.1. Колледж является структурным\nподразделением Университета."


def test_a_paragraph_going_on_after_a_page_break_is_one_paragraph():
    from catix.wiki.sources.opendataloader import text_of

    doc = {"kids": [{"type": "paragraph", "content": "Работник обязан соблюдать"}, {"type": "paragraph", "content": "правила охраны труда."},
                    {"type": "paragraph", "content": "а) иное."}]}
    assert text_of(doc, set()).split("\n\n") == ["Работник обязан соблюдать\nправила охраны труда.", "а) иное."]


def test_the_paragraphs_of_a_list_item_stay_where_they_stand_beside_its_inner_list():
    # the laundry's rules: '✓ Две стиральные машины' follows 1.4 on the page, a paragraph of item 1 after its inner list
    from catix.wiki.sources.opendataloader import text_of

    inner = {"type": "list", "list items": [odl_item("1.1. Прачечная работает в режиме самообслуживания."),
                                            odl_item("1.4. В каждой прачечной комнате имеются:")]}
    item = {"type": "list item", "content": "1. Доступ в прачечную круглосуточно.",
            "kids": [inner, {"type": "paragraph", "content": "✓ Две стиральные машины"}]}
    assert text_of({"kids": [{"type": "list", "list items": [item]}]}, set()).split("\n\n") == [
        "1. Доступ в прачечную круглосуточно.", "1.1. Прачечная работает в режиме самообслуживания.",
        "1.4. В каждой прачечной комнате имеются:", "✓ Две стиральные машины"]


def test_a_page_head_stands_once_and_a_page_number_not_at_all():
    from catix.wiki.sources.opendataloader import text_of

    def page(kind: str, content: str) -> dict:
        return {"type": kind, "kids": [{"type": "paragraph", "content": content}]}

    doc = {"kids": [page("header", "Положение о практике"), {"type": "paragraph", "content": "Студент проходит практику в"},
                    page("footer", "Стр. 1 из 2"), page("header", "Положение о практике"),
                    {"type": "paragraph", "content": "организации."}, page("footer", "2"),
                    page("header", "Приложение 2\nк Положению о практике"), {"type": "paragraph", "content": "Форма отчёта"},
                    page("footer", "КонсультантПлюс Страница 3 из 4"), page("footer", "КонсультантПлюс Страница 4 из 4")]}
    assert text_of(doc, set()).split("\n\n") == ["Положение о практике", "Студент проходит практику в\nорганизации.",
                                                 "Приложение 2\nк Положению о практике", "Форма отчёта", "КонсультантПлюс"]


def test_a_clause_number_glued_to_its_words_is_a_clause():
    md = to_markdown("3.1. Аспирант обязан.\n3.2.Аспирант осваивает программу.\n2.14.«Содействие» оказывается.\nк 2.3.2026 году")
    assert "**3.2.** Аспирант осваивает программу." in md and "**2.14.** «Содействие» оказывается." in md


def test_a_pdf_opendataloader_cannot_read_is_read_by_pdfplumber(monkeypatch, tmp_path):
    from catix.wiki.sources import opendataloader, regulations

    monkeypatch.setattr(regulations, "pages_of", lambda pdf: 1)
    monkeypatch.setattr(opendataloader, "text_of_pdf", lambda pdf, converted=None: None)
    monkeypatch.setattr(regulations, "text_layer", lambda pdf: "1.1. Текст " * 50)
    text, method, ocr_pages = regulations.extract(tmp_path / "x.pdf", 0)
    assert method == regulations.PDFPLUMBER and ocr_pages == 0 and text.startswith("1.1.")


def test_a_short_table_of_data_is_worth_a_page_and_a_form_of_lines_is_not():
    from catix.wiki.sources.regulations import readable

    results = ("Автономная некоммерческая организация высшего образования «Университет Иннополис»\n\nРезультаты вступительного испытания по программе магистратуры Управление цифровым продуктом, проводимого "
               "АНО ВО «Университет Иннополис» самостоятельно, дата проведения 08.08.2024\n\n"
               "| № | СНИЛС/Уникальный код | оценка | оценка (прописью) |\n| --- | --- | --- | --- |\n"
               "| 1 | 12253778149 | 45 | Сорок пять |\n| 2 | 15472870485 | 42 | Сорок два |\n| 3 | 16898160835 | 40 | Сорок |")
    assert readable(results)
    assert not readable("Заявление\n\nФамилия ____ Имя ____ Отчество ____\n\nПодпись ____ Дата ____")


def test_a_scan_as_chandra_reads_it_is_text_as_a_text_layer_is():
    from catix.wiki.sources.chandra import nodes_of
    from catix.wiki.sources.opendataloader import text_of

    page1 = ('<div data-bbox="1 1 9 9" data-label="Page-Header"><p>Положение о практике</p></div>'
             '<div data-label="Section-Header"><h2><b>1. Общие положения</b></h2></div>'
             '<div data-label="Table"><table border="1"><tr><th rowspan="2">Вид</th><th colspan="2">Сроки</th></tr>'
             '<tr><td>начало</td><td>конец</td></tr><tr><td>учебная</td><td>1 июля</td><td>14 июля</td></tr></table></div>'
             '<div data-label="Text"><p>1.1. Студент проходит практику в</p></div>'
             '<div data-label="Image"><img alt="Official seal"/>Round seal of the university.</div>')
    page2 = ('<div data-label="Page-Header">2</div><div data-label="Page-Header"><p>Положение о практике</p></div>'
             '<div data-label="Text"><p>организации.</p></div>'
             '<div data-label="List-Group"><ul><li>– отчёт;</li><li>– дневник.</li></ul></div>'
             '<div data-label="Text"><p>Директор</p><img alt="Signature"/>A handwritten signature in black ink.<p>К.В. Семенихин</p></div>')
    text = text_of({"kids": nodes_of(page1) + nodes_of(page2)}, set())
    assert text.split("\n\n") == [
        "Положение о практике", "1. Общие положения",
        "| Вид | Сроки |  |\n| --- | --- | --- |\n| Вид | начало | конец |\n| учебная | 1 июля | 14 июля |",
        "1.1. Студент проходит практику в\nорганизации.", "– отчёт;", "– дневник.", "Директор", "К.В. Семенихин"]
