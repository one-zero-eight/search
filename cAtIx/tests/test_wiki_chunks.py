from catix.wiki import chunks
from catix.wiki.chunks import MAX, cut

FRONT = '---\ntype: regulation\ntitle: "Положение"\naudience: ["student"]\n---\n\n# Положение\n\n'


def test_clauses_are_numbered_and_their_lists_stay_with_them():
    long = "Текст пункта положения. " * 15  # sections above the size a piece is packed at
    body = f"## 1. Общие положения\n\n**1.1.** {long}\n\n**1.2.** Разработано в соответствии с:\n\n- законом;\n- уставом.\n\n## 2. Порядок\n\n**2.1.** {long}\n"
    meta, cs = cut(FRONT + body)
    assert meta["type"] == "regulation"
    assert [(c.heading, c.clause) for c in cs] == [("1. Общие положения", "1.1–1.2"), ("2. Порядок", "2.1")]
    assert "- законом;" in cs[0].text


def test_a_continued_clause_says_which_clause_it_continues(monkeypatch):
    monkeypatch.setattr(chunks, "MAX", 60)
    monkeypatch.setattr(chunks, "MIN", 10)
    body = "## 1. Общие\n\n**1.2.** Разработано в соответствии с законами.\n\n- федеральным законом об образовании;\n"
    _, cs = cut(FRONT + body)
    assert cs[1].text.startswith("(1.2) - федеральным")
    assert cs[1].clause == "1.2"


def test_a_big_table_is_cut_by_rows_with_the_header_repeated():
    rows = "\n".join(f"| {i} | {'тема ' * 30} |" for i in range(40))
    _, cs = cut(FRONT + "## Темы\n\n| № | Тема |\n| --- | --- |\n" + rows + "\n")
    assert len(cs) > 3
    assert all(c.text.startswith("| № | Тема |\n| --- | --- |") for c in cs)
    assert all(len(c.text) <= MAX for c in cs)
    assert sum(c.text.count("| тема") for c in cs) == 40  # every row once


def test_a_tiny_section_is_packed_with_the_next_one_under_its_heading():
    _, cs = cut(FRONT + "## Контакты\n\nОфис 101.\n\n## Сроки\n\nДо 1 сентября.\n")
    assert len(cs) == 1
    assert cs[0].heading == "Контакты" and "### Сроки\n\nДо 1 сентября." in cs[0].text


def test_a_guide_cites_the_pages_its_numbers_point_to():
    text = ('---\ntype: guide\ntitle: "Retakes"\n---\n\n# Retakes\n\n## Limits\n\nTwo retakes are allowed [5].\n\n'
            "# Citations\n\n5. [Положение о контроле](/regulations/attestation-regulation.md)\n")
    _, cs = cut(text)
    assert len(cs) == 1 and "Citations" not in cs[0].text
    assert cs[0].cites == [{"n": 5, "title": "Положение о контроле", "href": "/regulations/attestation-regulation.md"}]


def test_the_fingerprint_follows_the_text_not_the_position():
    a = cut(FRONT + "## A\n\n**1.1.** Текст пункта.\n")[1][0]
    b = cut(FRONT + "## Вступление\n\n" + "Длинное вступление. " * 80 + "\n\n## A\n\n**1.1.** Текст пункта.\n")[1][-1]
    assert a.seq != b.seq and a.sha == b.sha


def test_an_update_keeps_the_rows_of_unchanged_pieces():
    from catix.wiki.chunks import Chunk
    from catix.wiki.search_index import plan

    a, b, c = (Chunk(i, "H", [], t) for i, t in enumerate(["one", "two", "two"]))
    stored = [(10, a.sha), (11, b.sha), (12, c.sha), (13, Chunk(0, "H", [], "gone").sha)]
    new = [Chunk(0, "H", [], "new"), Chunk(1, "H", [], "two"), Chunk(2, "H", [], "one"), Chunk(3, "H", [], "two")]
    kept, insert, delete = plan(stored, new)
    assert [(i, ch.text) for i, ch in kept] == [(11, "two"), (10, "one"), (12, "two")]  # moved pieces keep their rows (and vectors)
    assert [ch.text for ch in insert] == ["new"] and delete == [13]
