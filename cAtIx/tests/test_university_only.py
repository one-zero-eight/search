"""The agent speaks for the university only: a question about a term or a name is looked up, not answered from memory.

Regression: "что такое did?" was answered with an expansion the model made up ("Diploma Individual Project"), and "что такое git"
with a textbook definition, without a single tool call. The chats only say that DID is something the university hosts. Needs the
model; each question is asked once, because the small model does not answer the same way every time.
"""

import re

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from tests.helpers import MatchesAny, NoMatch, ask

GENERAL = [
    "что такое did?",
    "что такое git",
    "what is polymorphism",
    "кто такой Эйнштейн",
    "что такое ci/cd",
    "объясни что такое рекурсия",
    "what is a database index",
    "что такое docker",
]
NOT_FOUND = [r"не\s+нашёл|не\s+нашел|не\s+найден|нет\s+(?:информации|упоминаний|объяснени)", r"\bfound\s+no\b|no\s+information|not\s+mentioned|no\s+mention"]
# what the model made up for DID, and what it would say from memory about the other terms
INVENTED_DID = re.compile(r"digital|decentral|diploma|innovation days|innopolis days|цифров|дипломн|децентрализ", re.I)


@pytest.mark.parametrize("question", GENERAL)
def test_a_general_question_is_looked_up_in_a_tool(agent, question):
    answer = ask(agent, question)
    assert answer.tool_names, f"answered without a tool: {answer.body[:200]!r}"


def test_an_abbreviation_is_not_expanded_from_memory(agent):
    for _ in range(3):
        answer = ask(agent, "что такое did?")
        evidence = " ".join(answer.tool_results).lower()
        invented = [m.group(0) for m in INVENTED_DID.finditer(answer.body) if m.group(0).lower() not in evidence]
        assert not invented, f"an expansion that no message has: {invented} in {answer.body[:200]!r}"


def test_a_term_the_university_does_not_discuss_is_reported_as_not_found(agent):
    for question in ("кто такой Эйнштейн", "что такое docker", "what is polymorphism"):
        answer = ask(agent, question)
        evidence = " ".join(answer.tool_results).lower()
        term = {"кто такой Эйнштейн": "эйнштейн", "что такое docker": "docker", "what is polymorphism": "polymorphism"}[question]
        if term not in evidence:  # the chats say nothing about it: that is the whole answer
            assert_test(LLMTestCase(input=question, actual_output=answer.body), [MatchesAny(NOT_FOUND, name="SaysNothingFound")])


def test_nothing_found_is_not_followed_by_a_textbook_definition(agent):
    """Soft: the model sometimes still adds 'Git is a distributed version control system…'. At most 2 of the 8 may."""
    leaks = []
    for question in GENERAL:
        answer = ask(agent, question)
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", answer.body.strip()) if s]
        definition = re.search(r"\b(это|—|is a|is an|refers to|представляет собой)\b", answer.body, re.I) and len(sentences) > 2
        if definition and any(re.search(p, answer.body, re.I) for p in NOT_FOUND):
            leaks.append(question)
    assert len(leaks) <= 2, f"explained from memory after 'not found': {leaks}"
