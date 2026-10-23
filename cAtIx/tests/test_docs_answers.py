"""Answers of the real agent from the university's documents (the docs helper and the wiki search).

The facts are read from the documents themselves (wiki/regulations): the regulation on interim assessment, п. 5.3 (at most two
retakes within one year), the regulation on academic leave, п. 2.2 (12 months, two years for military service or medical
reasons), the admission rules (master's 09.04.01: computer testing, at least 40 of 100). Deterministic checks only: the number,
the clause, the source line, the language. A changed document changes these tests: read the document before the test.
"""

import re

from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from tests.helpers import Answer, ContainsAll, LatinShare, MatchesAny, NoMatch, ask

OFFICIAL_SOURCE = r"\(документ университета\)|\(university document\)"


def case(question: str, answer: Answer) -> LLMTestCase:
    return LLMTestCase(input=question, actual_output=answer.body, retrieval_context=answer.tool_results)


def sources(answer: Answer) -> str:
    """The source list under the answer."""
    parts = re.split(r"\n\n(?:Источники|Sources):", answer.text)
    return parts[1] if len(parts) > 1 else ""


def test_retakes_give_the_number_and_the_period_of_the_regulation(agent):
    question = "Сколько раз можно пересдавать экзамен, если я его завалил?"
    answer = ask(agent, question)
    assert "ask_docs" in answer.helpers, answer.helpers
    assert_test(case(question, answer), [
        MatchesAny([r"\b2\b|\bдва\b|\bдвух\b|дважды"], name="TwoRetakes"),
        MatchesAny([r"\b1\b\s*\(?одного\)?\s*год|одного\s+года|\bгод\w*\b"], name="WithinAYear"),
    ])


def test_an_official_rule_is_cited_with_the_document_and_its_clause(agent):
    answer = ask(agent, "Сколько раз можно пересдавать экзамен, если я его завалил?")
    listed = sources(answer)
    assert re.search(OFFICIAL_SOURCE, listed), f"no university document among the sources: {listed!r}"
    assert re.search(r"п\.\s*\d+(\.\d+)+", listed), f"no clause in the source list: {listed!r}"
    assert "innopolis.university" in listed, listed


def test_academic_leave_gives_twelve_months_and_the_exception(agent):
    question = "На какой срок можно взять академический отпуск?"
    answer = ask(agent, question)
    assert "ask_docs" in answer.helpers, answer.helpers
    assert_test(case(question, answer), [MatchesAny([r"\b12\b|двенадцат"], name="TwelveMonths")])


def test_an_english_question_about_a_russian_document_gets_an_english_answer(agent):
    question = "How long can academic leave last?"
    answer = ask(agent, question)
    assert_test(case(question, answer), [
        MatchesAny([r"\b12\b|twelve"], name="TwelveMonths"),
        LatinShare(at_least=0.8, name="EnglishAnswer"),
    ])


def test_master_admission_gives_the_master_exam_not_the_bachelor_ones(agent):
    """Regression: the jumbled tables of pdftotext made the agent give the bachelor's exams (ЕГЭ, olympiads) to a master's question."""
    question = "Какое вступительное испытание и минимальный балл при поступлении в магистратуру по направлению 09.04.01?"
    answer = ask(agent, question)
    assert_test(case(question, answer), [
        ContainsAll(["40"], name="MinimumScore"),
        MatchesAny([r"тестирован"], name="Testing"),
        NoMatch([r"\bЕГЭ\b"], name="NoBachelorExams"),
    ])
    listed = sources(answer)
    assert listed, "no sources under the answer"
    assert "2024/2025" not in listed, f"the rules of an earlier year: {listed!r}"


def test_a_rule_the_documents_do_not_have_is_not_made_up(agent):
    """No document gives days off for a hackathon: the answer says it was not found and invents no number of days."""
    question = "Сколько дополнительных дней каникул положено студенту за победу в хакатоне?"
    answer = ask(agent, question)
    assert answer.helpers, "answered without a helper"
    assert_test(case(question, answer), [NoMatch([r"\b\d+\s*(?:дн|день|недел)"], name="NoInventedDays")])
