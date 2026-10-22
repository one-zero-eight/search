"""The wiki tools without a database: which clauses a piece holds, how a piece is shown to the model and in the source list."""

import types
from datetime import date

from catix.agent import sources, tools
from catix.db.wiki import WikiHit, holds


def hit(**kw) -> WikiHit:
    base = dict(id=7, path="/regulations/att.md", seq=3, heading="6. Пересдача", clause="6.1–6.3", sha="s", text="**6.1.** Пересдача ...",
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
    assert "[1] [«Положение о контроле»](https://innopolis.university/x.pdf), п. 6.1–6.3 (документ университета)" in answer


def test_a_guide_is_cited_with_the_documents_it_rests_on_and_never_called_official():
    guide = hit(trust="guide", title="Retakes", resource=None, clause="", path="/guides/retakes.md",
                based_on=[{"page": "/regulations/att.md", "title": "Положение о контроле", "link": "https://innopolis.university/x.pdf", "trust": "official"}])
    collector = tools.Collector(runtime())
    item = tools._wiki_item(guide, collector)
    assert "official" not in item and item["based_on"] == [{"document": "Положение о контроле", "page": "/regulations/att.md"}]
    line = sources.cite(f"Две пересдачи [{item['ref']}].", collector.new).splitlines()[-1]
    assert line == "[1] «Retakes» (сводка cAtIx по документам: [«Положение о контроле»](https://innopolis.university/x.pdf))"


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
    assert "Не более двух раз [1], потом отчисление [1]." in answer
    assert answer.splitlines()[-1].endswith("п. 5.3, 5.18 (документ университета)") and "[2]" not in answer


def test_a_field_of_study_code_is_not_a_clause():
    from catix.wiki.chunks import cut

    _, cs = cut('---\ntype: regulation\ntitle: "Правила"\n---\n\n## Испытания\n\n**09.04.01** Информатика: тестирование.\n')
    assert cs[0].clause == ""


def test_two_clauses_of_one_document_side_by_side_become_one_mark():
    collector = tools.Collector(runtime())
    a, b = tools._wiki_item(hit(id=1, clause="5.3"), collector), tools._wiki_item(hit(id=2, clause="5.4"), collector)
    assert sources.cite(f"Компьютерное тестирование [{a['ref']}][{b['ref']}].", collector.new).startswith("Компьютерное тестирование [1].")
