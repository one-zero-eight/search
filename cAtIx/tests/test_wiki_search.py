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
