"""The wiki tools without a database: which clauses a piece holds, how a piece is shown to the model and in the source list."""

import types
from datetime import date

from catix.agent import sources, tools
from catix.db.wiki import WikiHit, holds


def hit(**kw) -> WikiHit:
    base = dict(id=7, path="/raw/regulations/att.md", seq=3, heading="6. Пересдача", clause="6.1–6.3", sha="s", text="**6.1.** Пересдача ...",
                cites=[], title="Положение о контроле", type="regulation", trust="official", audience=["student"],
                resource="https://innopolis.university/x.pdf", status="draft", review=None, source_warning=None,
                stale_after=None, issued=date(2025, 6, 30))
    return WikiHit(**{**base, **kw})


def runtime():
    return types.SimpleNamespace(state={"messages": [], "sources": {}}, config={"configurable": {"thread_id": "t"}}, tool_call_id="x", context=None)


def test_a_piece_holds_the_clauses_of_its_range_and_their_sub_clauses():
    assert holds("5.3–5.5", "5.4") and holds("5.3–5.5", "5.4.1") and holds("5.3", "5.3")
    assert holds("4.9–5.2", "5")  # a chapter that starts in the piece
    assert not holds("5.3–5.5", "5.6") and not holds("5.3–5.5", "6") and not holds("", "5.3")


def test_an_official_piece_is_marked_official_and_cited_with_its_clause():
    collector = tools.Collector(runtime())
    item = tools._wiki_item(hit(), collector)
    assert item["official"] is True and item["clause"] == "6.1–6.3" and item["date"] == "2025-06-30"
    answer = sources.cite(f"Две пересдачи [{item['ref']}].", collector.new)
    assert answer.answer == "Две пересдачи [1]."
    assert len(answer.sources) == 1
    source = answer.sources[0]
    assert (source.number, source.title, source.url, source.kind, source.official) == (1, hit().title, hit().resource, "official_document", True)
    assert source.clauses == ["6.1–6.3"]


def test_a_guide_is_cited_with_the_documents_it_rests_on_and_never_called_official():
    guide = hit(trust="guide", title="Retakes", resource=None, clause="", path="/guides/retakes.md",
                based_on=[{"page": "/raw/regulations/att.md", "title": "Положение о контроле", "link": "https://innopolis.university/x.pdf", "trust": "official"}])
    collector = tools.Collector(runtime())
    item = tools._wiki_item(guide, collector)
    assert "official" not in item and item["based_on"] == [{"document": "Положение о контроле", "page": "/raw/regulations/att.md"}]
    answer = sources.cite(f"Две пересдачи [{item['ref']}].", collector.new)
    source = answer.sources[0]
    assert source.kind == "guide" and not source.official and source.url is None
    assert [(link.title, link.url) for link in source.based_on] == [("Положение о контроле", "https://innopolis.university/x.pdf")]


def test_warnings_say_what_is_not_to_be_trusted():
    old = hit(trust="wiki", review="lost table", stale_after=date(2020, 1, 1))
    assert tools._warnings(old) == ["not checked: lost table", "may be outdated: due for review since 2020-01-01"]
    scan = hit(review="scanned document read by OCR: check numbers")
    assert tools._warnings(scan) == ["read from a scan by OCR: letters and numbers may be misread"]


def test_clauses_of_one_document_share_one_line_of_the_source_list():
    collector = tools.Collector(runtime())
    a = tools._wiki_item(hit(id=1, clause="5.3"), collector)
    b = tools._wiki_item(hit(id=2, clause="5.18"), collector)
    answer = sources.cite(f"Не более двух раз [{a['ref']}], потом отчисление [{b['ref']}].", collector.new)
    assert answer.answer == "Не более двух раз [1], потом отчисление [1]."
    assert len(answer.sources) == 1 and answer.sources[0].clauses == ["5.3", "5.18"]


def test_a_field_of_study_code_is_not_a_clause():
    from catix.wiki.chunks import cut

    _, cs = cut('---\ntype: regulation\ntitle: "Правила"\n---\n\n## Испытания\n\n**09.04.01** Информатика: тестирование.\n')
    assert cs[0].clause == ""


def test_two_clauses_of_one_document_side_by_side_become_one_mark():
    collector = tools.Collector(runtime())
    a, b = tools._wiki_item(hit(id=1, clause="5.3"), collector), tools._wiki_item(hit(id=2, clause="5.4"), collector)
    assert sources.cite(f"Компьютерное тестирование [{a['ref']}][{b['ref']}].", collector.new).answer == "Компьютерное тестирование [1]."


def test_only_a_title_with_an_academic_year_makes_a_series_of_versions():
    from catix.db.wiki import _series

    old = _series("Правила приема на обучение по программам бакалавриата и магистратуры на 2024/2025 учебный год")
    new = _series("ПРАВИЛА ПРИЕМА НА ОБУЧЕНИЕ ПО ПРОГРАММАМ БАКАЛАВРИАТА И МАГИСТРАТУРЫ НА 2026/2027 УЧЕБНЫЙ ГОД (новая редакция)")
    assert old == new and old is not None
    assert _series("Учебный план [Учебный план. Внедрение]") is None


def test_the_section_a_page_of_the_site_names_first_is_not_part_of_the_documents_series():
    """The site's pages of the admission rules of 2026/2027 name their section first, those of 2024/2025 do not: they were
    not of one series, and the rules of 2024/2025 were cited for a master's admission."""
    from catix.db.wiki import _series, _year

    rules = "Правила приема на обучение по образовательным программам высшего образования – программам бакалавриата и программам магистратуры в АНО ВО «Университет Иннополис»"
    old = f"{rules} на 2024/2025 учебный год"
    admission = f"Информация о приеме на 2026/27 учебный год по образовательным программам высшего образования — {rules.upper()} НА 2026/2027 УЧЕБНЫЙ ГОД [Правила_приема_ВО_новая_редакция]"
    acts = f'Локальные нормативные акты(предусмотренные ч. 2 ст. 30 Федеральный закон от 29.12.2012 № 273-ФЗ "Об образовании в Российской Федерации") — {rules} на 2026/2027 учебный год'
    assert _series(old) == _series(admission) == _series(acts) is not None
    assert (_year(old), _year(admission), _year(acts)) == (2024, 2026, 2026)
    assert _series("Информация о приеме на 2026/27 учебный год — Сроки проведения приема") is None, "a section's own year is not a document's"
    staff = "Список научно-педагогических работников с окончанием срока действия трудового договора — В {} учебном году"
    assert _series(staff.format("2024/2025")) == _series(staff.format("2025/2026")) != _series(f"Приказ о стипендиях — В 2025/2026 учебном году")


def test_an_older_version_is_said_to_be_replaced():
    old = hit(newer="Правила приема на 2026/2027 учебный год")
    assert tools._warnings(old) == ["an older version: «Правила приема на 2026/2027 учебный год» replaces it; use that one unless the question is about this year"]


def test_an_older_version_is_found_only_when_its_year_is_asked(monkeypatch):
    from catix.db import wiki

    old = hit(id=1, sha="a", title="Правила приема на 2024/2025 учебный год", newer="Правила приема на 2026/2027 учебный год")
    new = hit(id=2, sha="b", title="Правила приема на 2026/2027 учебный год")
    monkeypatch.setattr(wiki, "_embed_all", lambda queries: [])
    monkeypatch.setattr(wiki, "_bm25", lambda words, kinds, courses=False: [] if courses else [1, 2])
    monkeypatch.setattr(wiki, "_hits", lambda ids, queries=(): [old, new])
    monkeypatch.setattr(wiki.settings, "reranker_route", None)
    assert [h.id for h in wiki.search("правила приема магистратура")] == [2]
    assert [h.id for h in wiki.search("правила приема 2024 года")] == [1, 2]


def test_a_section_asked_as_the_table_of_contents_names_it_is_read_and_a_read_that_finds_nothing_costs_nothing(monkeypatch):
    """The trace of 'регламент организации ИТ-поддержки': a scan's chapter is the line '4 Процесс получения технической
    поддержки', no heading; the model asks for '4. Процесс …' and must get it, not the table of contents, not nothing."""
    import json

    from langchain_core.messages import HumanMessage

    path = "/raw/regulations/site-help-it.md"
    pieces = [hit(id=1, path=path, seq=0, heading="6. Контроль исполнения", clause="", text="| 4 | Процесс получения технической поддержки ..... | 16 |"),
              hit(id=2, path=path, seq=1, heading="6. Контроль исполнения", clause="3.3", text="**3.3.2** Списание техники.\n\n4 Процесс получения технической поддержки\n\n**4.1** Описание процесса"),
              hit(id=3, path=path, seq=2, heading="4. Требования к срокам:", clause="", text="- – в течение 1 (одного) часа")]
    monkeypatch.setattr(tools.wiki_store, "find_page", lambda page: path)
    monkeypatch.setattr(tools.wiki_store, "page", lambda p: pieces)
    rt = runtime()
    rt.state["messages"] = [HumanMessage("регламент организации ИТ-поддержки")]

    def read(**kw) -> dict:
        message = tools.read_wiki.func(page=path, runtime=rt, **kw).update["messages"][0]
        rt.state["messages"].append(message)
        return json.loads(message.content)

    out = read(section="4. Процесс получения технической поддержки")
    assert [p["text"][:9] for p in out["pieces"]] == ["**3.3.2**", "- – в теч"]  # from the chapter's line on, not from the contents
    assert out["reads_left"] == 1
    assert read(section="7. Нет такого раздела")["pieces"] == []
    last = read(section="требования к срокам")  # (the failed read did not count: this is the second)
    assert last["pieces"] and last["reads_left"] == 0 and "last read" in last["note"]
    assert "error" in read(clause="4.1")  # two reads gave text: no more


def test_the_first_piece_of_each_document_found_lists_its_chapters(monkeypatch):
    """Asked about IT support, the helper read chapters 1 and 2 of the regulation in order and never reached chapter 4, the
    procedure and its deadlines: the search names a document's chapters with its first piece, once."""
    import json

    path, other = "/raw/regulations/site-help-it.md", "/raw/regulations/one.md"
    found = [hit(id=1, path=path, heading="1. Общие положения", clause="1.1"), hit(id=2, path=other, heading="Текст", clause=""),
             hit(id=3, path=path, heading="5. Цели и показатели", clause="5.1")]
    contents = {path: ["1. Общие положения", "2. Общее описание процесса", "4. Описание операций процесса", "5. Цели и показатели"], other: ["Текст"]}
    monkeypatch.setattr(tools.wiki_store, "search", lambda *args, **kwargs: found)
    monkeypatch.setattr(tools.wiki_store, "chapters", lambda paths: {p: contents[p] for p in paths})
    pieces = json.loads(tools.search_wiki.func(queries=["регламент ИТ-поддержки"], runtime=runtime()).update["messages"][0].content)["pieces"]
    assert pieces[0]["chapters"] == contents[path] and "chapters" not in pieces[2]  # (once per document)
    assert "chapters" not in pieces[1]  # (one heading is no table of contents)


def test_a_page_without_clauses_is_cited_with_its_section():
    """The rector's phone and mail are one table of the 'Руководство' page: a link to the whole page did not say where to look."""
    page = dict(path="/raw/sites/university/sveden-managers.md", clause="", type="website", trust="wiki", title="Руководство",
                resource="https://innopolis.university/sveden/managers", issued=None)
    heading = "Информация о руководителе образовательной организации, его заместителях:"
    collector = sources.Collector(runtime())
    a = tools._wiki_item(hit(**page, heading=heading), collector)
    b = tools._wiki_item(hit(**page, id=8, seq=4, heading="Информация о руководителях филиалов образовательной организации:"), collector)
    c = tools._wiki_item(hit(**page, id=9, seq=5, heading="Руководство"), collector)  # (the heading of the title itself says nothing)
    answer = sources.cite(f"Ректор: rector@innopolis.ru [{a['ref']}].", collector.new)
    assert answer.sources[0].kind == "website"
    assert answer.sources[0].sections == [heading]
    both = sources.cite(f"Ректор [{a['ref']}], филиалы [{b['ref']}][{c['ref']}].", collector.new)
    assert len(both.sources) == 1
    assert both.sources[0].sections == [heading, "Информация о руководителях филиалов образовательной организации:", "Руководство"]
