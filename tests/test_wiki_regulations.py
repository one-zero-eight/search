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


def test_scans_are_read_several_at_once(monkeypatch):
    """Short scans side by side fill the OCR server's slots: three are open at once, not one after another."""
    import threading
    from pathlib import Path
    from catix.wiki.sources import regulations

    together = threading.Barrier(3, timeout=10)  # (one at a time, the first would wait here for ever: BrokenBarrierError)
    monkeypatch.setattr(regulations, "ocr_text", lambda pdf: (together.wait(), (pdf.stem, "ocr"))[1])
    done = {scan: future.result() for scan, future in regulations.read_scans(["a", "b", "c"], lambda s: Path(f"{s}.pdf"))}
    assert done == {"a": ("a", "ocr"), "b": ("b", "ocr"), "c": ("c", "ocr")}


def test_the_pages_of_two_short_scans_are_read_side_by_side(monkeypatch, tmp_path):
    """chandra reads the pages of every scan in one queue (page_pool): two scans of 2 pages have 4 pages in flight."""
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from pathlib import Path
    from catix.wiki.sources import chandra

    def pdftoppm(args, check):  # 2 pages of each scan, as pdftoppm names them
        for n in (1, 2):
            Path(f"{args[-1]}-{n}.png").write_bytes(b"")

    together = threading.Barrier(4, timeout=10)
    monkeypatch.setattr(chandra, "available", lambda: True)
    monkeypatch.setattr(chandra.subprocess, "run", pdftoppm)
    monkeypatch.setattr(chandra, "read_page", lambda png: (together.wait(), f'<div data-label="Text"><p>{png.stem}</p></div>')[1])
    with ThreadPoolExecutor(2) as scans:
        texts = list(scans.map(chandra.text_of_pdf, [tmp_path / "a.pdf", tmp_path / "b.pdf"]))
    assert [t.split() for t in texts] == [["p-1", "p-2"], ["p-1", "p-2"]]


def test_a_stopped_reading_of_scans_starts_none_of_those_waiting(monkeypatch):
    """Ctrl-C (the reading given up): the scans not started are not read, the one being read ends."""
    import threading
    from pathlib import Path
    from catix.wiki.sources import regulations

    started, release = [], threading.Event()

    def ocr_text(pdf):
        started.append(pdf.stem)
        if pdf.stem != "a":
            release.wait(10)
        return pdf.stem, "ocr"

    monkeypatch.setattr(regulations.settings, "ocr_parallel", 1)
    monkeypatch.setattr(regulations, "ocr_text", ocr_text)
    reading = regulations.read_scans(["a", "b", "c", "d"], lambda s: Path(f"{s}.pdf"))
    assert next(reading)[0] == "a"
    reading.close()
    release.set()
    assert "c" not in started and "d" not in started


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


def test_a_login_page_given_for_a_document_is_not_the_document_and_the_document_waits(monkeypatch, tmp_path):
    import contextlib

    import httpx

    from catix.wiki.sources import opendataloader, regulations, sites

    url = "https://help.university.innopolis.ru/documents/reglament.pdf"
    monkeypatch.setattr(regulations, "all_docs", lambda: {"site-help-1-reglament": {"title": "Регламент", "url": url, "root": tmp_path, "section": "site/help", "ext": "pdf"}})
    login = httpx.Response(200, html="<!DOCTYPE html><html><body>Sign in</body></html>", request=httpx.Request("GET", "https://sso.university.innopolis.ru/adfs/ls"))
    monkeypatch.setattr(regulations.httpx, "get", lambda *a, **k: login)
    monkeypatch.setattr(regulations, "PAUSE", 0)
    monkeypatch.setattr(opendataloader, "converted", lambda pdfs: contextlib.nullcontext({}))
    monkeypatch.setattr(sites, "collect_linked_docs", lambda: 0)  # (it reads and writes the real bundle's sites)
    assert regulations.fetch() == 0
    assert list(tmp_path.iterdir()) == []  # no file, and no note that would keep it skipped


def test_a_broken_link_the_site_answers_with_its_page_is_skipped(monkeypatch, tmp_path):
    import contextlib
    import json

    import httpx

    from catix.wiki.sources import opendataloader, regulations, sites

    url = "https://innopolis.university/sveden/upload/iblock/e9e/x/10.pdf"
    monkeypatch.setattr(regulations, "all_docs", lambda: {"site-university-1-10": {"title": "Результаты опроса", "url": url, "root": tmp_path, "section": "site/university", "ext": "pdf"}})
    page = httpx.Response(200, html="<!DOCTYPE html><html><title>Сведения</title></html>", request=httpx.Request("GET", url))
    monkeypatch.setattr(regulations.httpx, "get", lambda *a, **k: page)
    monkeypatch.setattr(regulations, "PAUSE", 0)
    monkeypatch.setattr(opendataloader, "converted", lambda pdfs: contextlib.nullcontext({}))
    monkeypatch.setattr(sites, "collect_linked_docs", lambda: 0)  # (it reads and writes the real bundle's sites)
    assert regulations.fetch() == 0
    assert [f.name for f in tmp_path.iterdir()] == ["site-university-1-10.json"] and "skipped" in json.loads((tmp_path / "site-university-1-10.json").read_text())


def test_the_headings_chandra_found_are_the_headings_of_the_page_and_none_is_guessed_from_a_number():
    """The regulation of IT help: its chapter '4 Процесс …' has no dot, so the guess missed it, and took the items of a list
    '1. Начало процесса:' for chapters; chandra's Section-Header blocks say which is which (their h2/h3/h4 do not). A section
    of a chapter stays a clause, by its number, as the cards cite it."""
    from catix.wiki.sources.chandra import nodes_of
    from catix.wiki.sources.opendataloader import text_of
    from catix.wiki.sources.regulations import to_markdown

    page = ('<div data-label="Text"><p>3.3.2 Списание техники.</p></div>'
            '<div data-label="Section-Header"><h2><b>4 Процесс получения технической поддержки</b></h2></div>'
            '<div data-label="Section-Header"><h4>4.1 Описание процесса</h4></div>'
            '<div data-label="Text"><p>1. Начало процесса: возникшая необходимость в ИТ-поддержке.</p></div>'
            '<div data-label="Text"><p>3. Результат процесса:</p></div>'
            '<div data-label="List-Group"><ul><li>– заявка закрыта.</li></ul></div>'
            '<div data-label="Section-Header"><h2>Приложение 1</h2></div>')
    md = to_markdown(text_of({"kids": nodes_of(page)}, set(), headings=True))
    assert md.split("\n\n") == ["**3.3.2** Списание техники.", "## 4 Процесс получения технической поддержки", "**4.1** Описание процесса",
                                "1. Начало процесса: возникшая необходимость в ИТ-поддержке.", "3. Результат процесса:", "- – заявка закрыта.",
                                "## Приложение 1"]
    assert to_markdown("1. Общие положения\n\n1.1. Текст") == "## 1. Общие положения\n\n**1.1.** Текст"  # (the text layer: guessed, as before)


def test_a_flat_numbering_past_99_keeps_its_clauses():
    from catix.wiki.sources.regulations import to_markdown

    assert to_markdown("99. Зачисление проводится в 2 этапа.\n\n100. На каждом этапе определяется приоритет.") == (
        "**99.** Зачисление проводится в 2 этапа.\n\n**100.** На каждом этапе определяется приоритет.")


def test_a_scan_is_queued_by_a_run_without_ocr_and_read_by_the_next_run_with_it(monkeypatch, tmp_path):
    import contextlib
    import json

    import httpx

    from catix.wiki.sources import opendataloader, regulations, sites

    url, key = "https://hotel.innopolis.university/upload/rules.pdf", "site-hotel-1-rules"
    monkeypatch.setattr(regulations, "all_docs", lambda: {key: {"title": "Правила", "url": url, "root": tmp_path, "section": "site/hotel", "ext": "pdf"}})
    monkeypatch.setattr(sites, "collect_linked_docs", lambda: 0)  # (it reads and writes the real bundle's sites)
    monkeypatch.setattr(regulations, "discover_linked_documents", dict)
    asked, layers, read = [], [], []
    monkeypatch.setattr(regulations.httpx, "get", lambda u, **k: asked.append(u) or httpx.Response(200, content=b"%PDF-1.4 a scan", headers={"etag": "v1"},
                                                                                                  request=httpx.Request("GET", u)))
    monkeypatch.setattr(regulations, "PAUSE", 0)
    monkeypatch.setattr(regulations, "pages_of", lambda pdf: 3)
    monkeypatch.setattr(opendataloader, "converted", lambda pdfs: contextlib.nullcontext({}))
    monkeypatch.setattr(regulations, "layer_text", lambda pdf, converted=None: layers.append(pdf.name))  # (None: too little text, a scan)
    monkeypatch.setattr(regulations, "ocr_text", lambda pdf: read.append(pdf.name) or ("1. Общие положения " * 50, "ocr (chandra-ocr-2)"))

    assert regulations.read_new(ocr=False) == []
    meta = json.loads((tmp_path / f"{key}.json").read_text(encoding="utf-8"))
    assert meta["ocr"] == "queued" and meta["pages"] == 3 and meta["remote"]["etag"] == "v1" and not read and not (tmp_path / f"{key}.txt").exists()
    assert regulations.read_new(ocr=False) == [] and asked == [url] and layers == [f"{key}.pdf"]  # (it waits: not downloaded, its text layer not asked again)
    assert regulations.read_new() == [key] and read == [f"{key}.pdf"] and layers == [f"{key}.pdf"]  # (the run with OCR reads it at once)
    meta = json.loads((tmp_path / f"{key}.json").read_text(encoding="utf-8"))
    assert "ocr" not in meta and meta["method"] == "ocr (chandra-ocr-2)" and meta["remote"]["etag"] == "v1" and "sha256" in meta
    assert regulations.read_new() == []  # (read: nothing more)
