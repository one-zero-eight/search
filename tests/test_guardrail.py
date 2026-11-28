"""Real-model safety labels and their effect on the ordinary agent path.

Classification calls bypass screen()'s fail-open wrapper: a model failure must fail
these checks, not masquerade as acceptance. Middleware then consumes that verdict.
"""

from types import SimpleNamespace

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from langchain_core.messages import AIMessage, HumanMessage

from catix.agent import guardrail
from tests.guardrail_cases import ALLOW, BLOCK, LOOKUP, NONSENSE, OFF_TOPIC, SMALL_TALK
from tests.helpers import SameLabel


def classify_and_route(text, monkeypatch):
    result = guardrail._screen_chain().invoke({"text": text, "history": "[]"})
    verdict = guardrail.Verdict(category=result.category)
    monkeypatch.setattr(guardrail, "screen", lambda text, *, history="[]": verdict)
    state = {"messages": [HumanMessage(text)], "answer_alone": True}
    runtime = SimpleNamespace(context=SimpleNamespace(user_telegram_id=None))
    update = guardrail.GuardrailMiddleware().before_agent(state, runtime)
    if verdict.blocked:
        assert update is not None and update["jump_to"] == "end"
        assert len(update["messages"]) == 1
        assert isinstance(update["messages"][0], AIMessage)
        assert not update["messages"][0].tool_calls
    else:
        assert update == {"answer_alone": verdict.category == "small_talk"}
    return verdict


@pytest.mark.model
@pytest.mark.parametrize("text", ALLOW, ids=[t[:45] for t in ALLOW])
def test_a_normal_question_is_let_through(text, monkeypatch):
    verdict = classify_and_route(text, monkeypatch)
    label = "block" if verdict.blocked else "allow"
    assert_test(LLMTestCase(input=text, actual_output=label, expected_output="allow"), [SameLabel()])


@pytest.mark.model
@pytest.mark.parametrize("text,category", BLOCK, ids=[t[:45] for t, _ in BLOCK])
def test_an_attack_or_spam_is_stopped(text, category, monkeypatch):
    verdict = classify_and_route(text, monkeypatch)
    assert_test(LLMTestCase(input=text, actual_output=verdict.category, expected_output=category), [SameLabel()])
    assert verdict.blocked


@pytest.mark.model
@pytest.mark.parametrize("text", SMALL_TALK, ids=[t[:45] for t in SMALL_TALK])
def test_small_talk_has_nothing_to_look_up(text, monkeypatch):
    verdict = classify_and_route(text, monkeypatch)
    assert_test(LLMTestCase(input=text, actual_output=verdict.category, expected_output="small_talk"), [SameLabel()])


@pytest.mark.model
@pytest.mark.parametrize("text", OFF_TOPIC, ids=[t[:45] for t in OFF_TOPIC])
def test_a_safe_unrelated_task_reaches_the_agent(text, monkeypatch):
    verdict = classify_and_route(text, monkeypatch)
    assert_test(LLMTestCase(input=text, actual_output=verdict.category, expected_output="ok"), [SameLabel()])


@pytest.mark.model
@pytest.mark.parametrize("text", NONSENSE, ids=[t[:45] for t in NONSENSE])
def test_an_unclear_request_reaches_the_agent_for_clarification(text, monkeypatch):
    verdict = classify_and_route(text, monkeypatch)
    assert_test(LLMTestCase(input=text, actual_output=verdict.category, expected_output="ok"), [SameLabel()])


@pytest.mark.model
@pytest.mark.parametrize("text", LOOKUP, ids=[t[:45] for t in LOOKUP])
def test_a_question_keeps_tools_available_even_with_the_words_of_a_task(text, monkeypatch):
    verdict = classify_and_route(text, monkeypatch)
    assert_test(LLMTestCase(input=text, actual_output=verdict.category, expected_output="ok"), [SameLabel()])


@pytest.mark.model
def test_braces_in_a_message_are_classified_as_data(monkeypatch):
    verdict = classify_and_route("что значит {sent} и {{x}} в расписании? {0}", monkeypatch)
    assert not verdict.blocked
