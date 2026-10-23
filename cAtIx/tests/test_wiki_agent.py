"""The wiki's agent writes cards only through a check by code (wiki/agent.py): every sentence cites a source page and,
for a regulation, a clause that exists; every number is in what it cites; cards and guides are not evidence. No model here."""

from types import SimpleNamespace

from catix.wiki import agent

REG = "/regulations/leave.md"
COURSE = "/course-programmes/calc-2026.md"


def bundle():
    page = lambda typ, body, title: {"meta": {"type": typ, "title": title, "sources": [{"id": "abc", "last_modified": "2026-01-01"}]}, "body": body}
    return SimpleNamespace(meta={
        REG: page("regulation", "**2.2.** Academic leave is granted for up to 12 months.\n\n**2.3.** Twice at most.\n", "Regulation on academic leave"),
        COURSE: page("course-programme", "Calculus, 5 credits, 180 hours, an exam.", "Course programme: Calculus"),
        "/guides/leave.md": page("guide", "Leave lasts 12 months [1].", "Academic leave (guide)"),
        "/knowledge/academic-leave.md": page("card", "", "Academic leave"),
    })


def test_a_card_that_cites_what_it_says_passes():
    body = (f"Academic leave lasts up to 12 months [п. 2.2]({REG}#2.2), at most twice [п. 2.3]({REG}#2.3).\n\n"
            f"- Calculus: 180 hours and an exam [source]({COURSE})\n\n## See also\n\n- [Academic leave](/knowledge/academic-leave.md)")
    assert agent.problems(body, bundle()) == []


def test_a_sentence_without_a_source_a_missing_clause_or_a_number_not_cited_is_refused():
    idx = bundle()
    assert any("no citation" in p for p in agent.problems("Academic leave lasts a year.", idx))
    assert any("no clause 9.9" in p for p in agent.problems(f"Leave lasts 12 months [п. 9.9]({REG}#9.9).", idx))
    assert any("number 24" in p for p in agent.problems(f"Leave lasts 24 months [п. 2.2]({REG}#2.2).", idx))
    assert any("no such page" in p for p in agent.problems("Leave [x](/regulations/none.md).", idx))


def test_a_guide_or_a_card_is_not_evidence():
    found = agent.problems("Leave lasts 12 months [g](/guides/leave.md).", bundle())
    assert any("card or a guide" in p for p in found) and any("no citation" in p for p in found)


def test_the_file_numbers_the_links_and_the_agent_gets_them_back():
    body = f"Up to 12 months [п. 2.2]({REG}#2.2); 180 hours [source]({COURSE}); again [п. 2.2]({REG}#2.2)."
    text, refs = agent.to_file_body(body)
    assert text == "Up to 12 months [1]; 180 hours [2]; again [1]." and refs == [(REG, "2.2"), (COURSE, "")]
    assert agent.to_agent_body(text, refs) == body


def test_a_card_is_written_with_its_front_matter_and_citations_and_read_back(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "BUNDLE", tmp_path)
    body = f"Academic leave lasts up to 12 months [п. 2.2]({REG}#2.2)."
    assert agent.write("academic-leave", "Academic leave", "How long leave lasts.", body, ["leave"], ["student"], bundle()) == []
    text = (tmp_path / "knowledge" / "academic-leave.md").read_text()
    front = text.split("\n---\n")[0]
    assert "type: card" in front and REG in front and "academic-leave" not in front  # its sources are the pages it cites
    assert "# Citations\n\n1. [Regulation on academic leave](/regulations/leave.md), clause 2.2" in text
    assert agent.read_file_card("academic-leave")["body"] == body
    assert agent.write("Bad Slug", "t", "d", body, [], [], bundle()) != []


def test_a_new_text_of_a_card_may_not_lose_what_the_old_one_cited(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "BUNDLE", tmp_path)
    idx = bundle()
    both = f"Up to 12 months [п. 2.2]({REG}#2.2). At most twice [п. 2.3]({REG}#2.3)."
    assert agent.write("academic-leave", "Academic leave", "d", both, [], [], idx) == []
    shorter = f"Up to 12 months [п. 2.2]({REG}#2.2)."
    refused = agent.write("academic-leave", "Academic leave", "d", shorter, [], [], idx)
    assert refused and f"{REG}#2.3" in refused[0]
    assert agent.write("academic-leave", "Academic leave", "d", shorter, [], [], idx, dropped=[f"{REG}#2.3"]) == []
    assert agent.read_file_card("academic-leave")["body"] == shorter


def test_a_citation_whose_clause_went_away_may_go(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "BUNDLE", tmp_path)
    idx = bundle()
    assert agent.write("academic-leave", "Academic leave", "d", f"Up to 12 months [п. 2.2]({REG}#2.2). Twice [п. 2.3]({REG}#2.3).", [], [], idx) == []
    idx.meta[REG]["body"] = "**2.2.** Academic leave is granted for up to 12 months.\n"  # the new version of the regulation has no 2.3
    assert agent.write("academic-leave", "Academic leave", "d", f"Up to 12 months [п. 2.2]({REG}#2.2).", [], [], idx) == []
