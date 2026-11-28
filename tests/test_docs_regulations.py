import pytest
from catix.docs.sources.regulations import to_markdown


def test_numbered_clauses_and_chapters():
    md = to_markdown("1. Общие положения\n\n1.1. Первый пункт\nпродолжение строки.\n\n1.2. Второй пункт.")
    assert md.split("\n\n") == ["## 1. Общие положения", "**1.1.** Первый пункт продолжение строки.", "**1.2.** Второй пункт."]


def test_flat_numbering_has_clauses_not_chapters():
    md = to_markdown("1. Настоящее Положение определяет порядок\nперехода обучающихся.\n\n2. Положение обязательно для всех.")
    assert md.split("\n\n") == ["**1.** Настоящее Положение определяет порядок перехода обучающихся.", "**2.** Положение обязательно для всех."]


def test_table_rows_from_layout_gaps_and_page_numbers():
    md = to_markdown("Буква        Оценка\nA            отлично\n\n12\n")
    assert md == "| Буква | Оценка |\n| --- | --- |\n| A | отлично |"


def test_the_date_of_a_document_is_its_own_not_that_of_a_law_it_cites():
    from catix.docs.sources.regulations import issued_of

    text = "ПРИКАЗ\n\n30 июня 2025 г.\n\nВ соответствии с Федеральным законом от 29 декабря 2012 года № 273-ФЗ ..."
    assert issued_of(text, "fallback") == "2025-06-30T00:00:00+03:00"
    assert issued_of("Утверждено приказом от 01.09.2024 № 5, закон от 29 декабря 2012 года", "f").startswith("2024-09-01")
    assert issued_of("Без дат.", "fallback") == "fallback"


def test_a_table_found_in_the_pdf_keeps_its_rows_and_merged_cells_take_the_value_above():
    from catix.docs.sources.regulations import table_markdown, to_markdown

    rows = [["Код", "Профиль", "Испытание", None], ["09.04.01", "Робототехника", "Тестирование", None], [None, None, "Собеседование", None]]
    md = table_markdown(rows)
    assert md.splitlines() == ["| Код | Профиль | Испытание |", "| --- | --- | --- |",
                               "| 09.04.01 | Робототехника | Тестирование |", "| 09.04.01 | Робототехника | Собеседование |"]
    text = f"**1.1.** До таблицы.\n\n{md}\n\n{md}\nПосле таблицы."
    blocks = to_markdown(text).split("\n\n")
    assert blocks[1] == md and blocks[2] == md and blocks[3] == "После таблицы."  # two tables stay two, the text after stays after


def test_a_cell_merged_across_columns_heads_a_group_of_rows_and_is_not_the_row_above_again():
    from catix.docs.sources.regulations import table_markdown

    rows = [["№", "Услуга", "Периодичность"], ["Расходные материалы", None, None], ["4", "Мыло", "при заезде"]]
    wide = [[False] * 3, [False, True, True], [False] * 3]
    assert table_markdown(rows, wide).splitlines()[2:] == ["| Расходные материалы |  |  |", "| 4 | Мыло | при заезде |"]


def test_a_table_of_one_column_is_text_and_its_clauses_are_clauses():
    # a regulation in a frame came out as a table of one column, and its clauses as rows: '| 1.1. Колледж ... |'
    from catix.docs.sources.regulations import table_markdown, to_markdown

    rows = [["1.1. Колледж является структурным"], ["подразделением Университета."], [None], ["1.2. Настоящее Положение регулирует"], ["деятельность Колледжа."]]
    assert to_markdown(table_markdown(rows)).split("\n\n") == ["**1.1.** Колледж является структурным подразделением Университета.",
                                                             "**1.2.** Настоящее Положение регулирует деятельность Колледжа."]


def odl_item(content: str, *more: str) -> dict:
    return {"type": "list item", "content": content, "kids": [{"type": "paragraph", "content": m} for m in more]}


def test_opendataloader_text_keeps_a_clause_on_its_own_line_and_its_item_whole():
    # joining lines itself, opendataloader glued '6.1.' to its chapter's heading and '10.13.' to the clause before it
    from catix.docs.sources.opendataloader import text_of
    from catix.docs.sources.regulations import to_markdown

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
    from catix.docs.sources.opendataloader import join_broken, joined

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
    from catix.docs.sources.opendataloader import text_of

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
    from catix.docs.sources.opendataloader import text_of

    doc = {"kids": [{"type": "paragraph", "content": "Работник обязан соблюдать"}, {"type": "paragraph", "content": "правила охраны труда."},
                    {"type": "paragraph", "content": "а) иное."}]}
    assert text_of(doc, set()).split("\n\n") == ["Работник обязан соблюдать\nправила охраны труда.", "а) иное."]


def test_marked_pages_keep_a_paragraph_on_its_own_page():
    from catix.docs.sources.opendataloader import split_pages, text_of

    doc = {"kids": [{"type": "paragraph", "content": "Работник обязан соблюдать", "page number": 1},
                    {"type": "paragraph", "content": "правила охраны труда.", "page number": 2}]}
    assert split_pages(text_of(doc, set(), marked=True)) == [(1, "Работник обязан соблюдать"), (2, "правила охраны труда.")]


def test_lighton_pages_are_marked():
    from catix.docs.sources import lighton
    from catix.docs.sources.opendataloader import split_pages

    pages = split_pages(lighton.text_of_pages(["# Intro\n\nfirst", "", "third"], marked=True))
    assert [page for page, _ in pages] == [1, 3]


def test_the_paragraphs_of_a_list_item_stay_where_they_stand_beside_its_inner_list():
    # the laundry's rules: '✓ Две стиральные машины' follows 1.4 on the page, a paragraph of item 1 after its inner list
    from catix.docs.sources.opendataloader import text_of

    inner = {"type": "list", "list items": [odl_item("1.1. Прачечная работает в режиме самообслуживания."),
                                            odl_item("1.4. В каждой прачечной комнате имеются:")]}
    item = {"type": "list item", "content": "1. Доступ в прачечную круглосуточно.",
            "kids": [inner, {"type": "paragraph", "content": "✓ Две стиральные машины"}]}
    assert text_of({"kids": [{"type": "list", "list items": [item]}]}, set()).split("\n\n") == [
        "1. Доступ в прачечную круглосуточно.", "1.1. Прачечная работает в режиме самообслуживания.",
        "1.4. В каждой прачечной комнате имеются:", "✓ Две стиральные машины"]


def test_a_page_head_stands_once_and_a_page_number_not_at_all():
    from catix.docs.sources.opendataloader import text_of

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
    from catix.docs.sources import opendataloader, regulations

    monkeypatch.setattr(regulations, "pages_of", lambda pdf: 1)
    monkeypatch.setattr(opendataloader, "text_of_pdf", lambda pdf, converted=None, marked=False: None)
    monkeypatch.setattr(regulations, "text_layer", lambda pdf: "1.1. Текст " * 50)
    text, method, ocr_pages = regulations.extract(tmp_path / "x.pdf", 0)
    assert method == regulations.PDFPLUMBER and ocr_pages == 0 and text.startswith("1.1.")


def test_scans_are_read_several_at_once(monkeypatch):
    """Short scans side by side fill the OCR server's slots: three are open at once, not one after another."""
    import threading
    from pathlib import Path
    from catix.docs.sources import regulations

    monkeypatch.setattr(regulations.settings, "ocr_parallel", 3)
    together = threading.Barrier(3, timeout=10)  # (one at a time, the first would wait here for ever: BrokenBarrierError)
    monkeypatch.setattr(regulations, "ocr_text", lambda pdf: (together.wait(), (pdf.stem, "ocr"))[1])
    done = {scan: future.result() for scan, future in regulations.read_scans(["a", "b", "c"], lambda s: Path(f"{s}.pdf"))}
    assert done == {"a": ("a", "ocr"), "b": ("b", "ocr"), "c": ("c", "ocr")}


def test_the_pages_of_two_short_scans_are_read_side_by_side(monkeypatch, tmp_path):
    """tesseract reads the pages of every scan in one queue (page_pool): two scans of 2 pages have 4 pages in flight."""
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from pathlib import Path
    from catix.docs.sources import tesseract, opendataloader

    monkeypatch.setattr(opendataloader, "corpus_words", lambda: frozenset())  # (the words of the stored documents: the database)

    def pdftoppm(args, check):  # 2 pages of each scan, as pdftoppm names them
        for n in (1, 2):
            Path(f"{args[-1]}-{n}.png").write_bytes(b"")

    monkeypatch.setattr(tesseract.settings, "ocr_parallel", 4)
    monkeypatch.setattr(tesseract, "_pages", None)
    together = threading.Barrier(4, timeout=10)
    monkeypatch.setattr(tesseract, "available", lambda: True)
    monkeypatch.setattr(tesseract.subprocess, "run", pdftoppm)
    monkeypatch.setattr(tesseract, "read_page", lambda png: (together.wait(), png.stem)[1])
    with ThreadPoolExecutor(2) as scans:
        texts = list(scans.map(tesseract.text_of_pdf, [tmp_path / "a.pdf", tmp_path / "b.pdf"]))
    assert [t.split() for t in texts] == [["p-1", "p-2"], ["p-1", "p-2"]]


def test_a_stopped_reading_of_scans_starts_none_of_those_waiting(monkeypatch):
    """Ctrl-C (the reading given up): the scans not started are not read, the one being read ends."""
    import threading
    from pathlib import Path
    from catix.docs.sources import regulations

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


def test_a_short_document_is_worth_a_page_and_one_with_no_letter_or_digit_is_not():
    from catix.docs.sources.regulations import readable

    assert readable("Информация о наличии общежития(ий)\n\nУниверситет предоставляет размещение.")
    assert readable("| № | оценка |\n| --- | --- |\n| 1 | 45 |")
    assert not readable("")
    assert not readable("  \n\n")
    assert not readable("____ | | ---- ||\n\n| --- | --- |\n_ _")


def test_a_scan_as_lighton_reads_it_is_text_as_a_text_layer_is():
    from catix.docs.sources.lighton import nodes_of
    from catix.docs.sources.opendataloader import text_of

    page1 = ("# 1. Общие положения\n\n"
             '<table border="1"><tr><th rowspan="2">Вид</th><th colspan="2">Сроки</th></tr>'
             "<tr><td>начало</td><td>конец</td></tr><tr><td>учебная</td><td>1 июля</td><td>14 июля</td></tr></table>\n\n"
             "| Вид | Срок |\n| --- | --- |\n| итоговая | 1 августа |\n\n"
             "1.1. Студент проходит практику в\n\n![image](image_1.png)")
    page2 = "организации.\n\n- отчёт;\n- дневник.\n\nДиректор\n\n![image](image_2.png)\n\nК.В. Семенихин"
    text = text_of({"kids": nodes_of(page1) + nodes_of(page2)}, set())
    assert text.split("\n\n") == [
        "1. Общие положения",
        "| Вид | Сроки |  |\n| --- | --- | --- |\n| Вид | начало | конец |\n| учебная | 1 июля | 14 июля |",
        "| Вид | Срок |\n| --- | --- |\n| итоговая | 1 августа |",
        "1.1. Студент проходит практику в\nорганизации.", "- отчёт;\n- дневник.", "Директор", "К.В. Семенихин"]


def test_a_login_page_given_for_a_document_is_not_the_document_and_the_document_waits(monkeypatch, docs_db):
    import contextlib

    import httpx

    from catix.docs import notes
    from catix.docs.sources import opendataloader, regulations

    url = "https://help.university.innopolis.ru/documents/reglament.pdf"
    monkeypatch.setattr(regulations, "all_docs", lambda: {"site-help-1-reglament": {"title": "Регламент", "url": url, "section": "site/help", "ext": "pdf"}})
    login = httpx.Response(200, html="<!DOCTYPE html><html><body>Sign in</body></html>", request=httpx.Request("GET", "https://sso.university.innopolis.ru/adfs/ls"))
    monkeypatch.setattr(regulations.httpx, "get", lambda *a, **k: login)
    monkeypatch.setattr(regulations, "PAUSE", 0)
    monkeypatch.setattr(opendataloader, "converted", lambda pdfs: contextlib.nullcontext({}))
    assert regulations.fetch() == 0
    assert [r["key"] for r in docs_db.execute("SELECT key FROM document_files").fetchall()] == ["site-help-1-reglament"]  # no file; a note that it waits, not that it is skipped
    note = notes.note("site-help-1-reglament")
    assert "skipped" not in note and note["failed"] == "sent to the login of sso.university.innopolis.ru" and not notes.has_text("site-help-1-reglament")
    monkeypatch.setattr(regulations.httpx, "get", lambda *a, **k: pytest.fail("asked again before RETRY"))
    assert regulations.fetch() == 0


def test_a_broken_link_the_site_answers_with_its_page_is_skipped(monkeypatch, docs_db):
    import contextlib

    import httpx

    from catix.docs import notes
    from catix.docs.sources import opendataloader, regulations

    url = "https://innopolis.university/sveden/upload/iblock/e9e/x/10.pdf"
    monkeypatch.setattr(regulations, "all_docs", lambda: {"site-university-1-10": {"title": "Результаты опроса", "url": url, "section": "site/university", "ext": "pdf"}})
    page = httpx.Response(200, html="<!DOCTYPE html><html><title>Сведения</title></html>", request=httpx.Request("GET", url))
    monkeypatch.setattr(regulations.httpx, "get", lambda *a, **k: page)
    monkeypatch.setattr(regulations, "PAUSE", 0)
    monkeypatch.setattr(opendataloader, "converted", lambda pdfs: contextlib.nullcontext({}))
    assert regulations.fetch() == 0
    assert [r["key"] for r in docs_db.execute("SELECT key FROM document_files").fetchall()] == ["site-university-1-10"]
    assert "skipped" in notes.note("site-university-1-10")


def test_every_download_ends_in_a_note_and_a_dead_host_stops_only_its_own_documents(monkeypatch, docs_db):
    """olymp.innopolis.ru has no address any more and university.innopolis.ru/files/ sends to the start page of
    innopolis.university: without a note every run asked them again, and five failures in a row stopped the whole run."""
    import contextlib
    from datetime import timedelta

    import httpx

    from catix.docs import notes
    from catix.docs.sources import opendataloader, regulations, sites

    docs = {f"site-dead-{n}": {"title": f"Dead {n}", "url": f"https://dead.example/{n}.pdf", "section": "site/dead", "ext": "pdf"}
            for n in range(regulations.MAX_FAILURES + 1)}
    docs["site-media-1-free"] = {"title": "Free", "url": "https://old.example/files/FREE.pdf", "section": "site/media", "ext": "pdf"}
    monkeypatch.setattr(regulations, "all_docs", lambda: docs)
    asked = []

    def get(url, **kwargs):
        asked.append(url)
        if url.startswith("https://dead.example/"):
            raise httpx.ConnectError("[Errno -5] No address associated with hostname", request=httpx.Request("GET", url))
        return httpx.Response(200, html="<!DOCTYPE html><html><title>Университет</title><a href='/news/'>Новости</a></html>",
                              request=httpx.Request("GET", "https://new.example/"))  # (the start page of the other host, no login)

    monkeypatch.setattr(regulations.httpx, "get", get)
    monkeypatch.setattr(regulations, "PAUSE", 0)
    monkeypatch.setattr(regulations.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(opendataloader, "converted", lambda pdfs: contextlib.nullcontext({}))
    assert regulations.fetch() == 0
    dead = [f"https://dead.example/{n}.pdf" for n in range(regulations.MAX_FAILURES)]
    assert asked == [*dead, "https://old.example/files/FREE.pdf"]  # (the dead host let be after MAX_FAILURES; the other host read)
    written = {key: notes.note(key) for key in docs if notes.note(key)}
    assert all(written[f"site-dead-{n}"]["failed"].startswith("ConnectError") for n in range(regulations.MAX_FAILURES))
    assert f"site-dead-{regulations.MAX_FAILURES}" not in written  # (not asked: the next run asks it)
    assert written["site-media-1-free"]["skipped"] == "a page, not the file"
    asked.clear()
    assert regulations.fetch() == 0
    assert asked == [f"https://dead.example/{regulations.MAX_FAILURES}.pdf"]  # (the others wait RETRY; the skipped one stays skipped)
    monkeypatch.setattr(sites, "RETRY", timedelta(0))  # (RETRY has passed)
    asked.clear()
    regulations.fetch()
    assert asked == dead


def test_the_headings_lighton_found_are_the_headings_of_the_page_and_none_is_guessed_from_a_number():
    """The regulation of IT help: its chapter '4 Процесс …' has no dot, so the guess missed it, and took the items of a list
    '1. Начало процесса:' for chapters; the '#' lines of the model say which is which. A section of a chapter stays a clause,
    by its number, as the cards cite it."""
    from catix.docs.sources.lighton import nodes_of
    from catix.docs.sources.opendataloader import text_of
    from catix.docs.sources.regulations import to_markdown

    page = ("3.3.2 Списание техники.\n\n# 4 Процесс получения технической поддержки\n\n## 4.1 Описание процесса\n\n"
            "1. Начало процесса: возникшая необходимость в ИТ-поддержке.\n\n3. Результат процесса:\n\n– заявка закрыта.\n\n# Приложение 1")
    md = to_markdown(text_of({"kids": nodes_of(page)}, set(), headings=True))
    assert md.split("\n\n") == ["**3.3.2** Списание техники.", "## 4 Процесс получения технической поддержки", "**4.1** Описание процесса",
                                "1. Начало процесса: возникшая необходимость в ИТ-поддержке.", "3. Результат процесса:", "- – заявка закрыта.",
                                "## Приложение 1"]
    assert to_markdown("1. Общие положения\n\n1.1. Текст") == "## 1. Общие положения\n\n**1.1.** Текст"  # (the text layer: guessed, as before)


def test_a_flat_numbering_past_99_keeps_its_clauses():
    from catix.docs.sources.regulations import to_markdown

    assert to_markdown("99. Зачисление проводится в 2 этапа.\n\n100. На каждом этапе определяется приоритет.") == (
        "**99.** Зачисление проводится в 2 этапа.\n\n**100.** На каждом этапе определяется приоритет.")


def test_a_scan_is_queued_by_a_run_without_ocr_and_read_by_a_run_with_it_which_downloads_it_again(monkeypatch, tmp_path, docs_db):
    import contextlib
    import tempfile

    import httpx

    from catix.docs import notes
    from catix.docs.sources import opendataloader, regulations

    url, key = "https://hotel.innopolis.university/upload/rules.pdf", "site-hotel-1-rules"
    monkeypatch.setattr(regulations, "all_docs", lambda: {key: {"title": "Правила", "url": url, "section": "site/hotel", "ext": "pdf"}})
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    asked, layers, read = [], [], []
    monkeypatch.setattr(regulations.httpx, "get", lambda u, **k: asked.append(u) or httpx.Response(200, content=b"%PDF-1.4 a scan", headers={"etag": "v1"},
                                                                                                  request=httpx.Request("GET", u)))
    monkeypatch.setattr(regulations, "PAUSE", 0)
    monkeypatch.setattr(regulations, "pages_of", lambda pdf: 3)
    monkeypatch.setattr(opendataloader, "converted", lambda pdfs: contextlib.nullcontext({}))
    monkeypatch.setattr(regulations, "layer_text", lambda pdf, converted=None: layers.append(pdf.name))  # (None: too little text, a scan)
    monkeypatch.setattr(regulations, "ocr_text", lambda pdf: read.append(pdf.name) or ("1. Общие положения " * 50, "ocr (LightOnOCR)"))

    assert regulations.read_new(ocr=False) == []
    meta = notes.note(key)
    assert meta["ocr"] == "queued" and meta["pages"] == 3 and meta["remote"]["etag"] == "v1" and not read and not notes.has_text(key)
    assert regulations.read_new(ocr=False) == [] and asked == [url] and layers == [f"{key}.pdf"]  # (it waits: not downloaded, its text layer not asked again)
    assert not list(tmp_path.iterdir())  # (the original lived only in the run's temporary folder)
    assert regulations.read_new() == [key] and read == [f"{key}.pdf"] and layers == [f"{key}.pdf"] and asked == [url, url]  # (the run with OCR downloads it again)
    meta = notes.note(key)
    assert "ocr" not in meta and meta["method"] == "ocr (LightOnOCR)" and meta["remote"]["etag"] == "v1" and "sha256" in meta
    assert notes.text(key).startswith("1. Общие положения") and not list(tmp_path.iterdir())
    assert regulations.read_new() == [] and asked == [url, url]  # (read: nothing more)


def test_a_recheck_asks_a_read_document_with_what_the_site_said_and_reads_it_again_only_when_it_changed(monkeypatch, tmp_path, docs_db):
    import contextlib
    import tempfile
    from datetime import datetime, timedelta, timezone

    import httpx

    from catix.docs import frontier, notes
    from catix.docs.sources import opendataloader, regulations
    from tests.helpers import link_document

    url, key = "https://hotel.innopolis.university/upload/rules.pdf", "site-hotel-1-rules"
    assert link_document("hotel", url, "Правила проживания", key=key) == key
    monkeypatch.setattr(regulations, "all_docs", lambda: {key: {"title": "Правила", "url": url, "section": "site/hotel", "ext": "pdf"}})
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    answer = {"status": 200, "body": b"%PDF-1.4 one", "etag": "v1"}
    sent = []

    def get(u, **kwargs):
        sent.append(kwargs.get("headers", {}))
        return httpx.Response(answer["status"], content=b"" if answer["status"] == 304 else answer["body"], headers={"etag": answer["etag"]}, request=httpx.Request("GET", u))

    layers = []
    monkeypatch.setattr(regulations.httpx, "get", get)
    monkeypatch.setattr(regulations, "PAUSE", 0)
    monkeypatch.setattr(regulations, "pages_of", lambda pdf: 1)
    monkeypatch.setattr(regulations, "pdf_created", lambda pdf: None)
    monkeypatch.setattr(opendataloader, "converted", lambda pdfs: contextlib.nullcontext({}))
    monkeypatch.setattr(regulations, "layer_text", lambda pdf, converted=None: layers.append(pdf.name) or (f"{pdf.read_bytes().decode()} " * 70, "text layer"))

    assert regulations.recheck(["not-a-document"]) == [] and not sent  # (a key that is no document any more is passed by)
    assert regulations.recheck([key]) == [key]  # (never read: read as new, asked for with nothing)
    assert "If-None-Match" not in sent[-1] and notes.text(key).startswith("%PDF-1.4 one") and notes.note(key)["remote"]["etag"] == "v1"
    row = docs_db.execute("SELECT state, why, priority, next_at FROM crawl_urls WHERE doc_key = %s", (key,)).fetchone()
    assert row["state"] == "ok" and row["why"] is None and row["priority"] == frontier.RECHECK  # (frontier.documents_read noted the row)
    assert row["next_at"] > datetime.now(timezone.utc) + frontier.DOCUMENT_EVERY - timedelta(minutes=5)

    before = notes.note(key)
    answer["status"] = 304  # (the site: not modified)
    assert regulations.recheck([key]) == []
    assert sent[-1]["If-None-Match"] == "v1" and len(layers) == 1  # (what the site said of the file is what is asked: no download, no extraction)
    after = notes.note(key)
    assert notes.text(key).startswith("%PDF-1.4 one") and "refetch" not in after
    assert {k: v for k, v in after.items() if k != "checked_at"} == before and after["checked_at"]  # (only the check is noted)

    answer.update(status=200, body=b"%PDF-1.4 two", etag="v2")  # (the site: a new version)
    assert regulations.recheck([key]) == [key]
    assert sent[-1]["If-None-Match"] == "v1" and notes.text(key).startswith("%PDF-1.4 two") and notes.note(key)["remote"]["etag"] == "v2"
    assert notes.note(key)["sha256"] != before["sha256"] and len(layers) == 2

    answer.update(body=b"%PDF-1.4 two", etag="v3")  # (the site says a new ETag, the bytes are the same: the text stays, nothing is extracted)
    assert regulations.recheck([key]) == []
    assert notes.note(key)["remote"]["etag"] == "v3" and notes.text(key).startswith("%PDF-1.4 two") and len(layers) == 2
    assert not list(tmp_path.iterdir())


def test_a_file_of_the_bundle_a_site_links_with_its_spaces_is_one_document(monkeypatch, docs_db):
    from catix.docs.sources import regulations, sites
    from tests.helpers import link_document

    monkeypatch.setattr(regulations, "DOCS", {"attestation-regulation": ("Положение об аттестации", "bd2/Положение%20о%20формах.pdf")})
    url = sites.canonical(regulations.BASE + "bd2/Положение о формах.pdf")
    link_document("university", url, "Положение о формах, периодичности и порядке контроля")
    assert [d["url"] for d in sites.docs().values()] == [url]  # (the site links it: a row of the frontier)
    assert [key for key in regulations.all_docs() if key.startswith(("attestation", "site-"))] == ["attestation-regulation"]


F = "F"
GIA_URL = "https://help.university.innopolis.ru/documents/%D0%BF%D1%80%D0%B8%D0%BA%D0%B0%D0%B7_%D0%BE%D1%82_01.02.2023___%D0%9E%D0%94_%D0%90%D0%94-03.pdf"


@pytest.mark.parametrize("text, title, url, member, created, expected", [
    ("Утверждено от 01.09.2024", "Положение 2026", "https://x.example/a.pdf", None, None, ("2024-09-01T00:00:00+03:00", "text", "day")),
    ("Без дат.", "Положение о ГИА 2026", "https://x.example/a.pdf", None, None, ("2026-01-01T00:00:00+03:00", "title", "year")),
    ("Без дат.", "Правила", GIA_URL, None, None, ("2023-02-01T00:00:00+03:00", "filename", "day")),
    ("Без дат.", "Правила на 2026/2027 учебный год", "https://x.example/a.pdf", None, None, ("2026-01-01T00:00:00+03:00", "title", "year")),
    ("Без дат.", "fgos 09.02.07 izm1", "https://x.example/x.pdf", None, "2021-03-04", ("2021-03-04T00:00:00+03:00", "pdf", "day")),
    ("Без дат.", "Правила", "https://x.example/x.pdf", None, None, ("F", "", "")),
    ("Без дат.", "Правила", "https://x.example/x.pdf", "orders/приказ 21-08-2025.pdf", None, ("2025-08-21T00:00:00+03:00", "filename", "day")),
])
def test_a_document_without_a_date_in_its_text_takes_it_from_its_title_its_file_or_its_pdf(text, title, url, member, created, expected):
    from catix.docs.sources.regulations import dated

    assert dated(text, title, url, member, created, F) == expected


def _archive(status):
    from catix.docs.sources import archive_documents

    return lambda key, revision: archive_documents.save(key, {"url": "https://x.example/a.zip", "status": status, "sha256": "a" * 64})


def _read(remote, **more):
    from catix.docs import notes

    def put(key, revision):
        notes.put_text(key, revision, "1. Текст документа")
        notes.put_note(key, revision, {"sha256": "a" * 64, "method": "text layer", "remote": remote, **more})

    return put


def _note(**fields):
    from catix.docs import notes

    return lambda key, revision: notes.put_note(key, revision, fields)


ZIP, FILE = {"ext": "zip"}, {"ext": "pdf"}


@pytest.mark.parametrize("document, put, expected", [
    pytest.param(ZIP, _archive("ready"), ("ok", None, "DOCUMENT_EVERY"), id="an archive whose manifest is ready"),
    pytest.param({"archived": True, "revision": "a" * 64, **FILE}, _archive("ready"), ("ok", None, "DOCUMENT_EVERY"), id="a PDF an archive URL served"),
    pytest.param(ZIP, _archive("unsafe"), ("tried", "unsafe", "RETRY"), id="an archive whose manifest is another status"),
    pytest.param(ZIP, lambda key, revision: None, ("new", None, "SOON"), id="an archive with no manifest"),
    pytest.param(FILE, _read({"etag": "v1"}), ("ok", None, "DOCUMENT_EVERY"), id="a text read of a file the site signs"),
    pytest.param(FILE, _read({}), ("ok", None, "UNSIGNED_EVERY"), id="a text read of a file the site says nothing of"),
    pytest.param(FILE, _read({"etag": "v1"}, ocr="queued", pages=3), ("ok", None, "DOCUMENT_EVERY"), id="a text read wins over a queued scan"),
    pytest.param(FILE, _note(ocr="queued", pages=3), ("ok", "queued", "DOCUMENT_EVERY"), id="a scan queued for OCR"),
    pytest.param(FILE, _note(ocr="too long", pages=90), ("ok", "too long", "DOCUMENT_EVERY"), id="a scan put aside as too long"),
    pytest.param(FILE, _note(skipped="a page, not the file"), ("gone", "a page, not the file", None), id="skipped"),
    pytest.param(FILE, _note(failed="ConnectError: no address"), ("tried", "ConnectError: no address", "RETRY"), id="no file came lately"),
    pytest.param(FILE, lambda key, revision: None, ("new", None, "SOON"), id="no note"),
    pytest.param(FILE, _note(sha256="a" * 64), ("new", None, "SOON"), id="a hash with no text is not a read document"),
])
def test_the_row_of_a_document_has_the_state_its_notes_say(docs_db, document, put, expected):
    from catix.docs import frontier
    from catix.docs.sources import regulations

    state, why, delay = expected
    put("doc", document.get("revision", ""))
    assert regulations.note_state("doc", document) == (state, why, getattr(frontier, delay) if delay else None)


def test_the_state_of_a_document_is_that_of_its_revision(docs_db):
    from catix.docs import notes
    from catix.docs.sources import regulations

    notes.put_note("member", "old", {"skipped": "too big"})
    assert regulations.note_state("member", {"ext": "pdf", "revision": "new"})[0] == "new"  # (the new revision of a member is not read: its old one says nothing)
    assert regulations.note_state("member", {"ext": "pdf", "revision": "old"}) == ("gone", "too big", None)
    assert regulations.note_state("member", {"ext": "pdf"})[0] == "new"


def test_a_document_is_a_page_when_its_text_is_read_and_readable_and_of_the_revision_now(monkeypatch, docs_db):
    from catix.docs import notes
    from catix.docs.sources import regulations

    def read(key, revision, text, **more):
        notes.put_text(key, revision, text)
        notes.put_note(key, revision, {"title": key, "url": f"https://x.example/{key}.pdf", "sha256": "b" * 64, "method": "text layer", "section": "site/x",
                                       "fetched_at": "2026-11-01T10:00:00+00:00", **more})

    read("read", "", "1. Общие положения\n\n1.1. Текст пункта.")
    read("member", "new", "1. Текст нового издания.")
    read("member", "old", "1. Текст старого издания.")
    read("blank", "", "____ | | ----")
    notes.put_note("queued", "", {"ocr": "queued", "pages": 3})
    read("gone", "", "1. Положение, на которое ссылок больше нет.")
    docs = {key: {"title": f"Документ {key}", "url": f"https://x.example/{key}.pdf", "section": "site/x", "ext": "pdf"} for key in ("read", "blank", "queued", "gone", "unread")}
    docs["member"] = {"title": "Документ member", "url": "https://x.example/member.pdf", "section": "site/x", "ext": "pdf", "revision": "new"}
    docs["gone"]["unlisted"] = "2026-10-01"
    monkeypatch.setattr(regulations, "all_docs", lambda: docs)
    made = {d.path: d for d in regulations.compile_all()}
    assert sorted(made) == ["regulations/gone", "regulations/member", "regulations/read"]  # (not the blank, the queued scan, the unread; of a member, its revision now)
    assert "1.1." in made["regulations/read"].body and made["regulations/read"].meta["title"] == "Документ read"
    assert "нового издания" in made["regulations/member"].body and "старого" not in made["regulations/member"].body
    assert made["regulations/gone"].meta["stale_after"] == "2026-10-01T00:00:00+00:00" and "Ни одна видимая страница" in made["regulations/gone"].body
