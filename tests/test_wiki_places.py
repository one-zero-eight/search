"""The model points at the place a sentence rests on (wiki/agent.py place_quotes): the lines of the file read_page numbers
('#L8-L9') or a short clause ('#2.2'), and code copies the words there into the link as its quote; the checks go on as for a
quote the model wrote. No model here: the cards' texts are given."""

from types import SimpleNamespace

import pytest

from catix.wiki import agent

REG = "/raw/regulations/leave.md"
SITE = "/raw/sites/managers.md"
LONG = " ".join(["the student writes an application and attaches the documents that show the reason for the leave"] * 6)
FILES = {
    REG: ("---\ntype: regulation\ntitle: \"Положение об академическом отпуске\"\n---\n\n# Положение об академическом отпуске\n\n"
          "**2.2.** Academic leave is granted for up to 12 months.\n\n"
          f"**2.3.** A student may take academic leave twice at most;\n{LONG}.\n"),
    SITE: ("---\ntype: page\ntitle: \"Руководство\"\n---\n\n# Руководство\n\n## Директор института\n\n"
           "Вандюков Дмитрий Владимирович\nДиректор Института информационных технологий\n"),
}
# lines of REG: 8 is clause 2.2, 10–11 are clause 2.3; lines of SITE: 10 and 11 are the director


@pytest.fixture(autouse=True)
def _bundle(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "BUNDLE", tmp_path)
    monkeypatch.setattr(agent.settings, "wiki_agent_quotes", True)
    monkeypatch.setattr(agent.settings, "wiki_agent_two_sources", False)
    for page, text in FILES.items():
        (tmp_path / page.lstrip("/")).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / page.lstrip("/")).write_text(text, encoding="utf-8")
    return tmp_path


def index() -> SimpleNamespace:
    page = lambda text: {"meta": {"type": "regulation" if "regulation" in text else "page", "title": text.split('title: "')[1].split('"')[0],
                                  "sources": [{"id": "a1", "last_modified": "2024-03-01"}]}, "body": text.split("\n---\n", 1)[1]}
    return SimpleNamespace(meta={p: page(t) for p, t in FILES.items()})


def test_lines_become_the_clause_they_are_in_and_its_words():
    body, found = agent.place_quotes(f"Academic leave lasts up to 12 months [source]({REG}#L8).", index())
    assert found == []
    assert body == f'Academic leave lasts up to 12 months [п. 2.2]({REG}#2.2 "Academic leave is granted for up to 12 months.").'


def test_a_short_clause_is_its_own_quote_a_long_one_asks_for_lines():
    body, found = agent.place_quotes(f"Leave lasts up to 12 months [п. 2.2]({REG}#2.2).", index())
    assert found == [] and '#2.2 "Academic leave is granted for up to 12 months.")' in body
    body, found = agent.place_quotes(f"Leave is taken twice at most [п. 2.3]({REG}#2.3).", index())
    assert found == [] and body.endswith(f'[п. 2.3]({REG}#2.3 "A student may take academic leave twice at most;").')  # (code found the line)
    _, found = agent.place_quotes(f"Leave is paid by the state [п. 2.3]({REG}#2.3).", index())  # (no line of it says so)
    assert len(found) == 1 and "clause 2.3" in found[0] and "(lines 10–11)" in found[0] and f"[source]({REG}#L10-L11)" in found[0]


def test_code_finds_the_place_a_sentence_rests_on_when_the_quote_is_not_on_the_page():
    # the model wrote its own sentence as the quote, the name in another order: code finds the lines of the page
    body = f'Директор Института — Вандюков Дмитрий Владимирович [source]({SITE} "Вандюков Дмитрий — директор Института").'
    fixed, found = agent.place_quotes(body, index())
    assert found == [] and fixed.endswith(f'[source]({SITE} "Директор института Вандюков Дмитрий Владимирович").')
    assert agent.problems(fixed, index(), quotes=True) == []
    _, found = agent.place_quotes(f'Ректор — Иванов Пётр [source]({SITE} "Иванов Пётр").', index())  # (the page does not say it)
    assert found == [] and agent.problems(f'Ректор — Иванов Пётр [source]({SITE} "Иванов Пётр").', index(), quotes=True) != []


def test_a_page_without_clauses_is_cited_by_its_lines():
    body, found = agent.place_quotes(f"The institute is headed by its director [source]({SITE}#L10-L11).", index())
    assert found == []
    assert body.endswith(f'[source]({SITE} "Вандюков Дмитрий Владимирович Директор Института информационных технологий").')


def test_lines_across_clauses_rest_on_the_page_and_lines_past_the_text_are_refused():
    body, found = agent.place_quotes(f"Leave lasts 12 months, twice at most [source]({REG}#L8-L10).", index())
    assert found == [] and body.startswith(f'Leave lasts 12 months, twice at most [source]({REG} "Academic leave is granted for up to 12 months.')
    _, found = agent.place_quotes(f"Leave [source]({REG}#L2-L3).", index())  # (the front matter is not the text)
    assert "has no lines 2–3: its text is lines 5–11" in found[0]
    _, found = agent.place_quotes(f"Leave [source]({REG}#L5-L60).", index())
    assert "has no lines" in found[0]


def test_the_sentence_is_checked_against_the_words_it_points_at(_bundle):
    found = agent.write("academic-leave", "Academic leave", "How long leave lasts.",
                        f"Academic leave lasts up to 24 months [source]({REG}#L8).", [], ["student"], index())
    assert any("24" in p for p in found)
    assert agent.write("academic-leave", "Academic leave", "How long leave lasts.",
                       f"Academic leave lasts up to 12 months [source]({REG}#L8).", [], ["student"], index()) == []
    card = agent.read_file_card("academic-leave")
    assert card["body"] == f'Academic leave lasts up to 12 months [п. 2.2]({REG}#2.2 "Academic leave is granted for up to 12 months.").'


def test_a_quote_the_model_wrote_still_holds():
    body = f'Leave lasts up to 12 months [п. 2.2]({REG}#2.2 "is granted for up to 12 months").'
    assert agent.place_quotes(body, index()) == (body, [])
    assert agent.problems(body, index(), quotes=True) == []


def test_read_page_numbers_the_lines_a_link_points_at():
    text = agent.read_document(index(), REG)
    assert "8| **2.2.** Academic leave is granted for up to 12 months." in text and "2| type:" not in text
    assert agent.read_document(index(), REG, clause="2.3").splitlines()[2].startswith("10| **2.3.**")
    assert "no clause 9.9" in agent.read_document(index(), REG, clause="9.9")
    assert "10| Вандюков Дмитрий Владимирович" in agent.read_document(index(), SITE)


def test_a_page_without_clauses_says_so_and_asking_the_same_again_ends_the_task():
    assert "has no numbered clauses: read it with read_page(page)" in agent.read_document(index(), SITE, clause="1")
    from langchain_core.messages import ToolMessage

    guard = agent._guard()
    agent.TASK.set({"refused": 0})
    answers = []
    for n in range(1, 2 * agent.SAME_ANSWERS + 1):  # clause 1, 2, 3...: each call new, the answer the same
        call = {"name": "read_page", "args": {"page": SITE, "clause": str(n)}, "id": f"c{n}"}
        answers.append(guard.wrap_tool_call(SimpleNamespace(tool_call=call), lambda r: ToolMessage(f"{SITE} has no clause {n}", tool_call_id=f"c{n}")))
    assert "STOP: read_page answered the same" in answers[agent.SAME_ANSWERS - 1].content  # told first, ended the second time
    model = SimpleNamespace(tools=[], override=lambda tools: None)
    assert guard.wrap_model_call(model, lambda r: "called").content.startswith("DONE: gave up: read_page answered the same")


def test_read_file_of_a_document_has_its_lines_numbered():
    guard = agent._guard(lambda page, line: agent.read_document(index(), page, offset=line))
    agent.TASK.set({"refused": 0})
    call = {"name": "read_file", "args": {"file_path": SITE, "offset": 9}, "id": "c1"}
    out = guard.wrap_tool_call(SimpleNamespace(tool_call=call), lambda r: "the raw file")
    assert "10| Вандюков Дмитрий Владимирович" in out.content and "9| " not in out.content
    other = {"name": "read_file", "args": {"file_path": "/large_tool_results/x"}, "id": "c2"}
    assert guard.wrap_tool_call(SimpleNamespace(tool_call=other), lambda r: "the raw file") == "the raw file"


def test_a_page_that_is_not_there_names_the_pages_near_it():
    assert agent.read_document(index(), "/raw/sites/manager.md").endswith(f"the pages near it are {SITE}")
    assert agent.read_document(index(), "/raw/x/y.md").endswith("find pages with search_wiki")


def test_a_long_page_is_cut_and_lists_what_follows_in_few_lines(_bundle, monkeypatch):
    lines = "".join(f"## Подразделение {n}\n\nРуководитель подразделения {n}\n\n" for n in range(1, 2001))
    (_bundle / "raw" / "sites" / "struct.md").write_text(f"---\ntype: page\ntitle: \"Структура\"\n---\n\n{lines}", encoding="utf-8")
    idx = index()
    idx.meta["/raw/sites/struct.md"] = {"meta": {"type": "page", "title": "Структура"}, "body": lines}
    text = agent.read_document(idx, "/raw/sites/struct.md")
    cut = int(text.split("[...cut at line ")[1].split(":")[0])
    listing = text.split("[Headings of the page")[1]
    assert len(listing) < agent.CONTENTS_LIMIT + 200 and "more: read on with offset" in listing
    assert f"line {cut}: " in listing or f"line {cut + 1}: " in listing or f"line {cut + 2}: " in listing  # what follows the cut, not the start
    assert len(text) < agent.READ_LIMIT + agent.CONTENTS_LIMIT + 400


def test_the_end_of_a_page_is_said():
    assert agent.read_document(index(), SITE).endswith("[end of the page: line 11, nothing after it]")
    assert agent.read_document(index(), SITE, offset=40) == f"{SITE} ends at line 11: there is nothing after it"


def test_a_row_of_a_table_numbered_as_a_clause_is_that_clause(_bundle):
    # a plan converted again into a table kept its numbers in the first cell: the cards citing '#1.2' hold again
    plan = "/raw/regulations/plan.md"
    text = ("---\ntype: regulation\ntitle: \"План-график\"\n---\n\n# План-график\n\n| № | Мероприятие | Сроки |\n| --- | --- | --- |\n"
            "| 1. Направление – качество образования |  |  |\n| 1.1 | Аудит личных достижений обучающихся | Февраль |\n"
            "| 1.2 | Аудит данных промежуточной аттестации | Август |\n")
    (_bundle / "raw" / "regulations" / "plan.md").write_text(text, encoding="utf-8")
    idx = index()
    idx.meta[plan] = {"meta": {"type": "regulation", "title": "План-график"}, "body": text.split("\n---\n", 1)[1]}
    assert agent.clauses_of(idx, plan) == {"1.1": "Аудит личных достижений обучающихся Февраль", "1.2": "Аудит данных промежуточной аттестации Август"}
    body, found = agent.place_quotes(f"The interim assessment data are audited in August [п. 1.2]({plan}#1.2).", idx)
    assert found == [] and body.endswith(f'[п. 1.2]({plan}#1.2 "Аудит данных промежуточной аттестации Август").')
    assert agent.problems(body, idx, quotes=True) == []


def test_a_clause_the_page_does_not_have_is_found_again_on_the_page():
    # the clauses of a PDF converted again went away, and a card kept citing them: code finds the place of the sentence
    body, found = agent.place_quotes(f"Academic leave is granted for up to 12 months [п. 5.1]({REG}#5.1).", index())
    assert found == [] and body.endswith(f'[п. 2.2]({REG}#2.2 "Academic leave is granted for up to 12 months.").')


def test_lines_across_many_clauses_are_cut_to_a_quote_of_the_page():
    # a sentence pointed at a whole page of numbered rules: its 132 words, without their numbers, were nowhere on the page
    lines = "\n\n".join(f"**{n}.** Правило номер {n}: проживающие соблюдают тишину и порядок в комнате и на этаже." for n in range(1, 16))
    rules = "/raw/regulations/rules.md"
    text = f"---\ntype: regulation\ntitle: \"Правила\"\n---\n\n# Правила\n\n{lines}\n"
    agent.BUNDLE.joinpath("raw/regulations/rules.md").write_text(text, encoding="utf-8")
    idx = index()
    idx.meta[rules] = {"meta": {"type": "regulation", "title": "Правила"}, "body": text.split("\n---\n", 1)[1]}
    body, found = agent.place_quotes(f"The residents keep quiet [source]({rules}#L8-L36).", idx)
    assert found == [] and "**" not in body and agent.problems(body, idx, quotes=True) == []


def test_lines_that_begin_before_a_clause_rest_on_the_page():
    # the heading of an order and its clause 1: the quote is the page's words, not the clause's (it was looked for in the
    # clause, not found, and not cut: 111 words the model had not written and could not fix)
    c, words, problem = agent.place_quote(REG, "L6-L8", "Academic leave lasts up to 12 months", index())
    assert (c, problem) == ("", "") and words.startswith("Положение об академическом отпуске")


def test_a_long_quote_is_cut_to_the_window_with_the_most_of_its_numbers():
    # the tariffs of four buildings in a row: a window centred on the middle number lost the first and the last
    filler = lambda n: " ".join(["корпус"] * n)  # noqa: E731
    where = f"{filler(20)} тариф 1800 рублей {filler(60)} тариф 2200 рублей {filler(100)} тариф 3100 рублей {filler(30)}"
    cut = agent.fit_quote(where, where, "Two-room costs 1 800 and 2 200 roubles")
    assert len(agent.words_of(cut)) == agent.QUOTE_WORDS[1] and "1800" in cut and "2200" in cut


def test_the_place_of_a_sentences_numbers_is_added_when_its_quote_lacks_them():
    # the model quoted the line that names the director, and the year was in the line above: code adds that place
    body = f'The institute has been headed by its director since 12 months ago [source]({SITE} "Вандюков Дмитрий Владимирович").'
    assert agent.place_quotes(body, index())[0] == body  # (no line of the page has 12: the check refuses it, as before)
    body = f'Academic leave is granted for up to 12 months [source]({REG} "A student may take academic leave twice at most").'
    placed, found = agent.place_quotes(body, index())
    assert found == [] and f'[п. 2.2]({REG}#2.2 "Academic leave is granted for up to 12 months.")' in placed
    assert agent.problems(placed, index(), quotes=True) == []


def test_short_lines_across_clauses_are_a_quote_of_the_page():
    # clauses 1–3 of a list of documents, three lines: without the numbers between them the words were "not in the page"
    lines = "\n\n".join(f"**{n}.** {doc};" for n, doc in enumerate(["Паспорт", "Регистрационная карта", "Согласие на обработку данных"], 1))
    docs = "/raw/regulations/docs.md"
    text = f"---\ntype: regulation\ntitle: \"Документы\"\n---\n\n# Документы\n\n{lines}\n"
    agent.BUNDLE.joinpath("raw/regulations/docs.md").write_text(text, encoding="utf-8")
    idx = index()
    idx.meta[docs] = {"meta": {"type": "regulation", "title": "Документы"}, "body": text.split("\n---\n", 1)[1]}
    body, found = agent.place_quotes(f"A guest brings a passport, a registration card and a consent [source]({docs}#L8-L12).", idx)
    assert found == [] and '"Паспорт; 2. Регистрационная карта; 3. Согласие' in body and agent.problems(body, idx, quotes=True) == []


def test_an_english_sentence_is_found_on_a_russian_page_by_its_numbers():
    # "the order of 21 January 2026": none of its words is on the page, its numbers are, on one line
    order = "/raw/regulations/order.md"
    text = ("---\ntype: regulation\ntitle: \"Приказ\"\n---\n\n# Приказ\n\nПРИКАЗ № 01/2026/01/21 от 21 января 2026 г.\n\n"
            "Стоимость с 1 февраля 2026 года: 3 600 руб.\n\nСтоимость с 1 июня 2026 года: 4 200 руб.\n")
    agent.BUNDLE.joinpath("raw/regulations/order.md").write_text(text, encoding="utf-8")
    idx = index()
    idx.meta[order] = {"meta": {"type": "regulation", "title": "Приказ"}, "body": text.split("\n---\n", 1)[1]}
    assert agent.locate(order, "", "The order of 21 January 2026 sets the prices", idx) == ("", "ПРИКАЗ № 01/2026/01/21 от 21 января 2026 г.")
    assert agent.locate(order, "", "The price is 3,600 rubles", idx)[1].startswith("Стоимость с 1 февраля")
    assert agent.locate(order, "", "The prices of 2026", idx) == ("", "")  # (three lines say 2026: code does not guess)
    assert agent.locate(order, "", "Two rooms", idx) == ("", "")  # ('2' alone is not a place)
    assert agent.locate(order, "", "From 1 June 2026", idx) == ("", "")  # (two lines say "1 ... 2026")
    agent.BUNDLE.joinpath("raw/regulations/order.md").write_text(text + "\nПриложение к приказу № 01/2026/01/21 от 21 января 2026 г.\n", encoding="utf-8")
    assert agent.locate(order, "", "Order No. 01/2026/01/21 of 21 January 2026", idx)[1].startswith("ПРИКАЗ")  # (its annex repeats it)


def test_lines_of_a_numbered_list_are_a_quote_of_the_page():
    # "1. — Утвердить перечень ... 2. — Утвердить формы": without the list's "2." the two lines were "not in the page"
    order = "/raw/regulations/forms.md"
    text = ("---\ntype: regulation\ntitle: \"Приказ о формах\"\n---\n\n# Приказ о формах\n\n"
            "1. — Утвердить перечень документов для размещения гостей.\n\n2. — Утвердить формы документов для размещения гостей.\n")
    agent.BUNDLE.joinpath("raw/regulations/forms.md").write_text(text, encoding="utf-8")
    idx = index()
    idx.meta[order] = {"meta": {"type": "regulation", "title": "Приказ о формах"}, "body": text.split("\n---\n", 1)[1]}
    body, found = agent.place_quotes(f"The order approves the list and the forms of the documents [source]({order}#L8-L10).", idx)
    assert found == [] and "размещения гостей. 2. — Утвердить формы" in body and agent.problems(body, idx, quotes=True) == []


def test_a_quote_in_another_clause_is_linked_to_it():
    # the model quoted clauses 2 and 3 and linked "п. 2–3" to #2: the quote is the page's, its clause is found by code
    body, found = agent.place_quotes(f'Leave is taken twice at most [п. 2.2]({REG}#2.2 "A student may take academic leave twice at most").', index())
    assert found == [] and f'[п. 2.3]({REG}#2.3 "A student may take academic leave twice at most")' in body
    body, _ = agent.place_quotes(f'Up to 12 months, twice [п. 2.2]({REG}#2.2 "for up to 12 months. 2.3. A student may take academic leave twice").', index())
    assert f'[source]({REG} "for up to 12 months.' in body and agent.problems(body, index(), quotes=True) == []  # (across two: the page)


def test_the_lines_that_hold_are_written_and_the_rest_go_back(_bundle):
    # a model sent a card four times over, unchanged, for the numbers of a few lines: nothing was written
    good = [f"Leave lasts up to 12 months [п. 2.2]({REG}#2.2).", f"A student may take it twice [п. 2.3]({REG}#2.3 \"A student may take academic leave twice at most\")."]
    bad = f"Leave lasts 18 months [п. 2.2]({REG}#2.2)."
    notes: list = []
    assert agent.write("leave", "Academic leave", "How long it lasts.", "\n\n".join([*good, bad]), [], [], index(), notes=notes) == []
    text = (_bundle / "knowledge" / "leave.md").read_text(encoding="utf-8")
    assert "twice" in text and "18 months" not in text
    assert notes[0].startswith("without the lines that do not hold (1)") and "number 18 is not in what the sentence cites" in notes[0]
    found = agent.write("leave", "Academic leave", "How long it lasts.", "\n\n".join([bad, bad.replace("18", "19")]), [], [], index())
    assert found and "number 18" in found[0]  # (a card of lines that do not hold is not written: it is sent back whole)


def test_a_tables_own_numbering_is_not_a_claim():
    # "| 1. | Loss of a key | 300 |": the row's number is the table's, not what the row says
    body = f"| № | Violation | Fine |\n| --- | --- | --- |\n| 1. | Taking leave for 12 months [п. 2.2]({REG}#2.2) | none |"
    body, _ = agent.place_quotes(body, index())
    assert agent.problems(body, index(), quotes=True) == []
