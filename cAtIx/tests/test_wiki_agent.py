"""The wiki's agent writes cards only through a check by code (wiki/agent.py): every sentence cites a source page and,
for a regulation, a clause that exists; every number is in what it cites; cards and guides are not evidence. No model here."""

from collections import Counter
from types import SimpleNamespace

import pytest

from catix.wiki import agent


@pytest.fixture(autouse=True)
def _no_real_wiki(tmp_path, monkeypatch):
    """No test writes into the wiki of WIKI_ROOT (a card that passed the check would land there)."""
    monkeypatch.setattr(agent, "BUNDLE", tmp_path)
    monkeypatch.setattr(agent, "QUEUE", tmp_path / "knowledge-queue.json")
    monkeypatch.setattr(agent.settings, "wiki_agent_quotes", False)  # (the tests of quotes turn them on)

REG = "/regulations/leave.md"
COURSE = "/course-programmes/calc-2026.md"


def bundle():
    page = lambda typ, body, title: {"meta": {"type": typ, "title": title, "sources": [{"id": "abc", "last_modified": "2026-01-01"}]}, "body": body}
    return SimpleNamespace(meta={
        REG: page("regulation", "**2.2.** Academic leave is granted for up to 12 months.\n\n**2.3.** Twice at most.\n", "Regulation on academic leave"),
        COURSE: page("course-programme", "Calculus, 5 credits, 180 hours, an exam.", "Course programme: Calculus"),
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


def test_a_card_is_not_evidence():
    found = agent.problems("Leave lasts 12 months [c](/knowledge/academic-leave.md).", bundle())
    assert any("is a card" in p for p in found) and any("no citation" in p for p in found)


def test_the_file_numbers_the_links_and_the_agent_gets_them_back():
    body = f"Up to 12 months [п. 2.2]({REG}#2.2); 180 hours [source]({COURSE}); again [п. 2.2]({REG}#2.2)."
    text, refs = agent.to_file_body(body)
    assert text == "Up to 12 months [1]; 180 hours [2]; again [1]." and refs == [(REG, "2.2", ""), (COURSE, "", "")]
    assert agent.to_agent_body(text, refs) == body


def test_a_card_is_written_with_its_front_matter_and_citations_and_read_back(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "BUNDLE", tmp_path)
    body = f"Academic leave lasts up to 12 months [п. 2.2]({REG}#2.2)."
    assert agent.write("academic-leave", "Academic leave", "How long leave lasts.", body, ["leave"], ["student"], bundle()) == []
    text = (tmp_path / "knowledge" / "academic-leave.md").read_text()
    front = text.split("\n---\n")[0]
    assert "type: card" in front and REG in front and "academic-leave" not in front  # its sources are the pages it cites
    assert "# Citations\n\n1. [Regulation on academic leave](/regulations/leave.md), п. 2.2" in text
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
    assert agent.worth_reading({"type": "regulation", "section": "sveden/apply", "title": "Вступительное испытание по программе магистратуры «Кибербезопасность» 15.08.2024"})
    assert not agent.worth_reading({"type": "course-programme"}) and not agent.worth_reading({"type": "card"})


def test_refusals_are_counted_by_kind():
    from collections import Counter

    counts = Counter({"attempts": 5, "refused": 2, agent.kind_of("number 24 is not in what the sentence cites: x"): 1,
                      agent.kind_of("no citation of a source page: x"): 2})
    assert agent.describe(counts) == "5 attempts, 2 refused (no citation 2, number not in what it cites 1)"


def test_numbers_written_as_russian_words_count():
    assert {"4", "7", "18"} <= agent.numbers_in("до четырёх месяцев, в течение семи дней, старше восемнадцати лет")
    assert agent.numbers_in("в течение семестра в пятницу") == set()  # whole words only


def test_a_card_too_long_is_split():
    long = "\n\n".join(f"Leave lasts up to 12 months [п. 2.2]({REG}#2.2)." for _ in range(agent.MAX_BODY // 40))
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


def test_groups_of_thousands_are_one_number():
    from catix.wiki.agent import numbers_in

    assert {"16581"} <= numbers_in("16,581 sq. m") and "16" not in numbers_in("16,581 sq. m")
    assert numbers_in("300 thousand rubles") <= numbers_in("стоимость 300 000 рублей")
    assert {"1150000", "1150"} <= numbers_in("1 150 000 руб.") and {"1", "5"} <= numbers_in("1,5 часа")


def test_the_index_of_the_cards_is_not_a_card(tmp_path, monkeypatch):
    from catix.wiki import agent

    monkeypatch.setattr(agent, "BUNDLE", tmp_path)
    (tmp_path / agent.FOLDER).mkdir()
    (tmp_path / agent.FOLDER / "index.md").write_text("# knowledge\n")
    (tmp_path / agent.FOLDER / "a.md").write_text("---\ntype: card\n---\n")
    assert agent.all_cards() == ["a"]


class _Model:
    """An agent whose turns are given: each a list of (text, made tool calls)."""

    def __init__(self, turns):
        self.turns, self.calls = list(turns), 0

    def invoke(self, state, config):
        from langchain_core.messages import AIMessage

        self.calls += 1
        text, called = self.turns.pop(0)
        made = [AIMessage("", tool_calls=[{"name": "list_cards", "args": {}, "id": "1"}])] if called else []
        return {"messages": [*state["messages"], *made, AIMessage(text)]}


def test_done_may_be_bold_or_on_a_later_line():
    assert agent._invoke(_Model([("Wrote two cards.\n\n**DONE:** two cards", True)]), "t").endswith("two cards")


def test_an_agent_sent_back_that_does_nothing_has_finished():
    model = _Model([("Both cards passed the checks.", True), ("Nothing more: the third page is in a card already.", False)])
    assert agent._invoke(model, "t").startswith("DONE (nothing left to do)") and model.calls == 2
    busy = _Model([("Let me restructure.", True)] + [("Let me restructure.", True)] * agent.CONTINUES)
    assert agent._invoke(busy, "t").startswith("NOT FINISHED")


def test_tasks_run_at_once_and_each_leaves_the_queue_when_done(monkeypatch):
    import threading
    import time

    agent.save_queue([f"/regulations/r{i}.md" for i in range(9)])
    seen, at_once, lock = [], [0, 0], threading.Lock()

    def invoke(_agent, task, callbacks=None, name=""):
        with lock:
            at_once[0] += 1
            at_once[1] = max(at_once)
        time.sleep(0.05)
        with lock:
            at_once[0] -= 1
            seen.append(task)
        return "DONE: nothing"

    monkeypatch.setattr(agent, "_invoke", invoke)
    monkeypatch.setattr(agent, "build_agent", lambda *a: None)
    monkeypatch.setattr(agent, "Index", lambda: SimpleNamespace(meta={}))
    monkeypatch.setattr(agent, "check_all", lambda *a: {})
    monkeypatch.setattr(agent.settings, "wiki_agent_parallel", 3)
    stats = agent.run()
    assert at_once[1] == 3 and len(seen) == 3 and agent.load_queue() == [] and stats["unfinished tasks"] == 0
    assert all("The cards there are now:" in t for t in seen)


def test_a_card_written_goes_into_the_search_at_once(monkeypatch):
    from catix.wiki import search_index

    indexed = []
    monkeypatch.setattr(agent.settings, "database_url", "postgresql://test")
    monkeypatch.setattr(search_index, "index_page", lambda rel, bundle: indexed.append(rel))
    monkeypatch.setattr(agent, "write", lambda *a: [])
    write_card = {t.name: t for t in agent._tools([bundle()], [], Counter())}["write_card"]
    assert write_card.invoke({"slug": "academic-leave", "title": "t", "description": "d", "body": "b"}).startswith("written")
    assert indexed == ["/knowledge/academic-leave.md"]


def test_a_bold_date_from_a_line_break_does_not_end_a_clause():
    text = "**1.4.** руководствуется Федеральным законом от\n\n**29.12.2012** №273-ФЗ «Об образовании».\n\n**1.5.** Далее."
    assert dict(agent.CLAUSE.findall(text))["1.4"].rstrip().endswith("«Об образовании».")


def test_a_number_in_the_title_of_the_cited_page_counts():
    idx = bundle()
    idx.meta[REG]["meta"]["title"] = "Положение об академическом отпуске 2022"
    assert not any("number" in p for p in agent.problems(f"The 2022 regulation: leave lasts up to 12 months [п. 2.2]({REG}#2.2).", idx))


def test_a_title_with_brackets_keeps_its_citations():
    idx = bundle()
    idx.meta[REG]["meta"]["title"] = "Администрация — Положение [Положение об Администрации]"
    body = f"Leave lasts up to 12 months [п. 2.2]({REG}#2.2)."
    assert agent.write("academic-leave", "Academic leave", "d", body, [], [], idx) == []
    assert agent.read_file_card("academic-leave")["body"] == body
    text = agent.card_path("academic-leave").read_text().replace("(Положение об Администрации)", "[Положение об Администрации]")
    agent.card_path("academic-leave").write_text(text)  # a card written before the fix
    assert agent.read_file_card("academic-leave")["body"] == body


QUOTE = "Academic leave is granted for up to 12 months"


@pytest.fixture
def quotes(monkeypatch):
    monkeypatch.setattr(agent.settings, "wiki_agent_quotes", True)


def test_a_link_without_a_quote_is_refused_and_a_quote_found_passes(quotes):
    idx = bundle()
    assert any("no quote" in p for p in agent.problems(f"Leave lasts up to 12 months [п. 2.2]({REG}#2.2).", idx, quotes=True))
    assert agent.problems(f'Leave lasts up to 12 months [п. 2.2]({REG}#2.2 "{QUOTE}").', idx, quotes=True) == []


def test_a_quote_is_found_whatever_the_case_the_punctuation_and_a_mended_typo():
    text = "**2.2.** Академический   отпуск предоставляется на срок\nне более 12 (двенадцати) месяцев, — один раз."
    assert agent.find_quote("академический отпуск предоставляется на срок не более 12 (двенадцати) месяцев", text)
    assert agent.find_quote("Академический отпуск предоставлятся на срок не более 12 двенадцати месяцев", text)  # a typo mended or made
    assert agent.find_quote("отпуск по уходу за ребёнком до трёх лет", text) is None


def test_a_quote_not_in_the_page_or_in_another_clause_or_of_a_few_words_not_found_once_is_refused():
    idx = bundle()
    found = lambda body: agent.problems(body, idx, quotes=True)
    assert any("not in /regulations/leave.md#2.2" in p for p in found(f'Up to 12 months [п. 2.2]({REG}#2.2 "students may take it as often as they like").'))
    # a near quote with a number changed is found, and the number is checked against the page's own words there
    assert any("number 24" in p for p in found(f'Up to 24 months [п. 2.2]({REG}#2.2 "leave is granted for up to 24 months").'))
    assert any("but not in its clause 2.3" in p for p in found(f'Up to 12 months [п. 2.3]({REG}#2.3 "{QUOTE}").'))
    assert any("quote is 2 words" in p for p in found(f'Up to 12 months [п. 2.2]({REG}#2.2 "twelve months").'))
    assert found(f'Up to 12 months [п. 2.2]({REG}#2.2 "12 months").') == []  # short, but once in the clause: it can mean only that


def test_a_long_quote_that_is_on_the_page_is_cut_by_code_to_the_words_with_the_numbers():
    words = " ".join(["lorem", "ipsum", "dolor"] * 50)
    where = f"Intro {words} leave is granted for up to 12 months {words} end."
    long = where[:-5]  # 300+ words, all of them on the page
    cut = agent.fit_quote(long, where, "Leave lasts up to 12 months.")
    assert len(agent.words_of(cut)) == agent.QUOTE_WORDS[1] and "12 months" in cut and agent.find_quote(cut, where)
    assert agent.fit_quote("not on the page " * 30, where, "x") == "not on the page " * 30  # (the check says what is wrong)


def test_a_task_that_keeps_being_refused_is_given_up(monkeypatch):
    idx = bundle()
    tools = {t.name: t for t in agent._tools([idx], [])}
    agent.TASK.refused = 0
    answers = [tools["write_card"].invoke({"slug": "academic-leave", "title": "t", "description": "d", "body": "No citation here."})
               for _ in range(agent.MAX_REFUSED + 2)]
    assert answers[0].startswith("NOT written") and answers[agent.MAX_REFUSED - 1] == agent.GIVE_UP == answers[-1]


def test_the_numbers_of_a_quoted_sentence_are_checked_against_its_quote():
    idx = bundle()
    idx.meta[REG]["body"] = "**2.2.** Academic leave is granted for up to 12 months, and a student may take it twice in 6 years.\n"
    quoted = f'Leave lasts up to 6 months [п. 2.2]({REG}#2.2 "{QUOTE}").'
    assert any("number 6" in p for p in agent.problems(quoted, idx, quotes=True))  # 6 is in the clause, not in what it quotes
    assert agent.problems(quoted.replace("6 months", "12 months"), idx, quotes=True) == []


def test_a_quote_goes_into_the_citations_with_its_lines_and_comes_back(quotes, tmp_path):
    (tmp_path / "regulations").mkdir()
    (tmp_path / "regulations" / "leave.md").write_text("---\ntype: regulation\n---\n\n**2.2.** Academic leave is granted\nfor up to 12 months.\n")
    body = f'Leave lasts up to 12 months [п. 2.2]({REG}#2.2 "{QUOTE}").'
    assert agent.write("academic-leave", "Academic leave", "d", body, [], [], bundle()) == []
    assert f"п. 2.2, lines 5–6: «{QUOTE}»" in agent.card_path("academic-leave").read_text()
    assert agent.read_file_card("academic-leave")["body"] == body


def test_identifiers_of_people_are_hidden_and_paths_and_money_are_not():
    line = "Score 40 against 159-606-560 98 and 12547673170, codes 156793 [1]; see [x](/regulations/sveden-35518743-pdf.md); 1150000 rubles, 4.33"
    people = agent.hide_ids(line, people=True)
    assert "159-606-560" not in people and "12547673170" not in people and "156793" not in people
    assert "sveden-35518743" in people and "4.33" in people and "40" in people
    other = agent.hide_ids(line, people=False)
    assert "159-606-560" not in other and "12547673170" in other and "1150000" in other  # only a СНИЛС outside a list of people


def test_a_card_on_a_list_of_people_is_written_without_their_codes(tmp_path):
    idx = bundle()
    idx.meta[REG]["meta"]["title"] = "Вступительное испытание по программе магистратуры «Кибербезопасность» 15.08.2024"
    idx.meta[REG]["body"] = "**2.2.** № 1, 12547673170, 40 (Сорок).\n"
    assert agent.write("exam-results", "Exam results", "d", f"One result: 40 for 12547673170 [п. 2.2]({REG}#2.2).", [], [], idx) == []
    text = agent.card_path("exam-results").read_text()
    assert "12547673170" not in text and "40 for [скрыто]" in text
