from catix.docs import chunks
from catix.docs.chunks import MAX, cut

FRONT = "# Положение\n\n"


def test_clauses_are_numbered_and_their_lists_stay_with_them():
    long = "Текст пункта положения. " * 15  # sections above the size a piece is packed at
    body = f"## 1. Общие положения\n\n**1.1.** {long}\n\n**1.2.** Разработано в соответствии с:\n\n- законом;\n- уставом.\n\n## 2. Порядок\n\n**2.1.** {long}\n"
    cs = cut(FRONT + body)
    assert [(c.heading, c.clause) for c in cs] == [("1. Общие положения", "1.1–1.2"), ("2. Порядок", "2.1")]
    assert "- законом;" in cs[0].text


def test_a_continued_clause_says_which_clause_it_continues(monkeypatch):
    monkeypatch.setattr(chunks, "MAX", 60)
    monkeypatch.setattr(chunks, "MIN", 10)
    body = "## 1. Общие\n\n**1.2.** Разработано в соответствии с законами.\n\n- федеральным законом об образовании;\n"
    cs = cut(FRONT + body)
    assert cs[1].text.startswith("(1.2) - федеральным")
    assert cs[1].clause == "1.2"


def test_a_big_table_is_cut_by_rows_with_the_header_repeated():
    rows = "\n".join(f"| {i} | {'тема ' * 30} |" for i in range(40))
    cs = cut(FRONT + "## Темы\n\n| № | Тема |\n| --- | --- |\n" + rows + "\n")
    assert len(cs) > 3
    assert all(c.text.startswith("| № | Тема |\n| --- | --- |") for c in cs)
    assert all(len(c.text) <= MAX for c in cs)
    assert sum(c.text.count("| тема") for c in cs) == 40  # every row once


def test_a_tiny_section_is_packed_with_the_next_one_under_its_heading():
    cs = cut(FRONT + "## Контакты\n\nОфис 101.\n\n## Сроки\n\nДо 1 сентября.\n")
    assert len(cs) == 1
    assert cs[0].heading == "Контакты" and "### Сроки\n\nДо 1 сентября." in cs[0].text


def test_the_fingerprint_follows_the_text_not_the_position():
    a = cut(FRONT + "## A\n\n**1.1.** Текст пункта.\n")[0]
    b = cut(FRONT + "## Вступление\n\n" + "Длинное вступление. " * 80 + "\n\n## A\n\n**1.1.** Текст пункта.\n")[-1]
    assert a.seq != b.seq and a.sha == b.sha


def test_an_update_keeps_the_rows_of_unchanged_pieces():
    from catix.docs.chunks import Chunk
    from catix.docs.store import plan

    a, b, c = (Chunk(i, "H", [], t) for i, t in enumerate(["one", "two", "two"]))
    stored = [(10, a.sha), (11, b.sha), (12, c.sha), (13, Chunk(0, "H", [], "gone").sha)]
    new = [Chunk(0, "H", [], "new"), Chunk(1, "H", [], "two"), Chunk(2, "H", [], "one"), Chunk(3, "H", [], "two")]
    kept, insert, delete = plan(stored, new)
    assert [(i, ch.text) for i, ch in kept] == [(11, "two"), (10, "one"), (12, "two")]  # moved pieces keep their rows (and vectors)
    assert [ch.text for ch in insert] == ["new"] and delete == [13]


def test_a_text_that_stands_on_several_pages_is_searched_once_on_the_latest_intakes(monkeypatch):
    """The course programme of each intake repeats the last one: the copies are not searched, the latest intake's piece is.
    The same paragraph in another course stays searched, unless copies are marked across courses:
    then a question that names that course gets its piece."""
    from contextlib import nullcontext

    from catix.db import docs as doc_store, pg
    from catix.docs.chunks import Chunk
    from catix.docs.store import Document, mark_copies, write_page

    title = "Рабочая программа «Тестовый {}» (Б1.О.01) — бакалавриат 09.03.01, набор {}, 3 семестр"
    made = [("Альфакурс", 2024), ("Альфакурс", 2026), ("Альфакурс", 2025), ("Бетакурс", 2023)]
    pages = {f"course-programmes/test-copies-{i}": title.format(course, intake) for i, (course, intake) in enumerate(made)}
    texts = ["Объём дисциплины 72 часа.", "Объём  дисциплины 72 ЧАСА.", "Объём дисциплины 72 часа.", "Объём дисциплины 72 часа."]
    with pg.connection() as conn, conn.transaction(force_rollback=True):
        for (rel, name), text in zip(pages.items(), texts):
            write_page(conn, Document(rel, {"title": name, "source_kind": "official-document"}, ""), "x", [Chunk(0, "Объём", [], text)])
        monkeypatch.setattr(pg, "connection", lambda: nullcontext(conn))  # (the rows are in this transaction only)

        def found(question: str, across: bool) -> doc_store.DocHit:
            mark_copies(conn, across_courses=across)
            searched = conn.execute("SELECT path, id FROM document_chunks WHERE path = ANY(%s) AND copy_of IS NULL", (list(pages),)).fetchall()
            ids = {r["path"]: r["id"] for r in searched}
            assert set(ids) == ({"course-programmes/test-copies-1"} if across else {"course-programmes/test-copies-1", "course-programmes/test-copies-3"})
            return doc_store._hits([ids["course-programmes/test-copies-1"]], [question])[0]

        hit = found("сколько часов", across=False)
        assert hit.path == "course-programmes/test-copies-1"
        hit = found("сколько часов у курса Бетакурс", across=True)
        assert hit.path == "course-programmes/test-copies-3"  # the course asked about, not the latest intake of another
