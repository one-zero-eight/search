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


def test_surveys_and_curricula_are_not_queued_rules_are():
    assert agent.worth_reading({"type": "regulation", "section": "sveden/document"})
    assert agent.worth_reading({"type": "regulation", "section": "sveden/apply"})
    assert not agent.worth_reading({"type": "regulation", "section": "sveden/rating-system"})
    assert not agent.worth_reading({"type": "regulation", "section": "sveden/education"})
    assert agent.worth_reading({"type": "course"})  # the teaching wiki: no section
    assert not agent.worth_reading({"type": "course-programme"}) and not agent.worth_reading({"type": "guide"})


def test_refusals_are_counted_by_kind():
    from collections import Counter

    counts = Counter({"attempts": 5, "refused": 2, agent.kind_of("number 24 is not in what the sentence cites: x"): 1,
                      agent.kind_of("no citation of a source page: x"): 2})
    assert agent.describe(counts) == "5 attempts, 2 refused (no citation 2, number not in what it cites 1)"


def test_numbers_written_as_russian_words_count():
    assert {"4", "7", "18"} <= agent.numbers_in("до четырёх месяцев, в течение семи дней, старше восемнадцати лет")
    assert agent.numbers_in("в течение семестра в пятницу") == set()  # whole words only


def test_a_card_too_long_is_split():
    long = "\n\n".join(f"Leave lasts up to 12 months [п. 2.2]({REG}#2.2)." for _ in range(200))
    assert "too long" in agent.write("academic-leave", "Academic leave", "d", long, [], [], bundle())[0]


def test_ordinals_and_clause_numbers_in_the_text():
    assert {"2", "3"} <= agent.numbers_in("по итогам второго этапа; третий этап")
    found = agent.problems(f"Stage 2 ends by August 1, see clause 3.1.2 [п. 2.2]({REG}#2.2).", bundle())
    assert any("number 1" in p or "number 2" in p for p in found)  # (2.2 says neither 2 stages nor August 1)
    assert not any("number 3" in p for p in found)  # "clause 3.1.2" is a reference, not a claim


def test_the_items_of_a_list_rest_on_the_line_that_opens_it():
    body = f"Leave is granted for [п. 2.2]({REG}#2.2):\n\n- up to 12 months;\n- 24 months."
    found = agent.problems(body, bundle())
    assert len(found) == 1 and "number 24" in found[0]  # the first item rests on 2.2, the second states what 2.2 does not


def test_a_link_to_a_card_not_written_yet_becomes_its_name(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "BUNDLE", tmp_path)
    body = f"Up to 12 months [п. 2.2]({REG}#2.2).\n\n## See also\n\n- [Appeals](/knowledge/appeals.md)"
    assert agent.write("academic-leave", "Academic leave", "d", body, [], [], bundle()) == []
    text = (tmp_path / "knowledge" / "academic-leave.md").read_text()
    assert "- Appeals" in text and "/knowledge/appeals.md" not in text
