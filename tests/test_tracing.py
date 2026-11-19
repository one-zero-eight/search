"""Tracing in Phoenix (agent/tracing.py), without the agent or the model: a LangChain run inside `tracing.question` becomes a
trace with the question span as its root, the session and the user on it, and a user's 👍/👎 is an annotation on that span
that a second vote of the same user replaces. Needs the Phoenix container (`docker compose up -d phoenix`)."""

import time
import uuid

import httpx
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from langchain_core.runnables import RunnableLambda
from phoenix.client import Client

from catix.agent import tracing
from catix.settings import settings
from tests.helpers import ContainsAll


@pytest.fixture(scope="module")
def phoenix():
    if not tracing.enabled():
        pytest.skip("PHOENIX_ENDPOINT is not set")
    base = str(settings.phoenix_endpoint).rstrip("/")
    try:
        httpx.get(f"{base}/healthz", timeout=3).raise_for_status()
    except httpx.HTTPError:
        pytest.skip(f"Phoenix does not answer at {base} (docker compose up -d phoenix)")
    return Client(base_url=base)


def traced_run(user: str = "4242") -> tuple[str, str]:
    """One fake question: a LangChain run inside the question span. Returns the span id and the session."""
    session = "test-" + uuid.uuid4().hex[:8]
    with tracing.question(session, user, "когда мидтерм?") as traced:
        RunnableLambda(lambda x: x.upper()).invoke("ответ", tracing.run_config(session, user, name="fake-agent"))
        traced.answer("Мидтерм в среду")
    assert traced.id
    tracing.flush()
    return traced.id, session


def spans_of(client: Client, span_id: str, wait: float = 20) -> list[dict]:
    """The spans of the trace of `span_id`, once Phoenix has them."""
    deadline = time.monotonic() + wait
    while time.monotonic() < deadline:
        try:
            spans = client.spans.get_spans(project_identifier=settings.phoenix_project, limit=1000)
        except httpx.HTTPStatusError:  # 404 until the first span of a new project has arrived
            time.sleep(1)
            continue
        trace = next((s["context"]["trace_id"] for s in spans if s["context"]["span_id"] == span_id), None)
        if trace:
            return [s for s in spans if s["context"]["trace_id"] == trace]
        time.sleep(1)
    pytest.fail("the trace did not reach Phoenix")


def test_a_question_is_one_trace_with_session_user_and_text(phoenix):
    span_id, session = traced_run()
    spans = spans_of(phoenix, span_id)
    root = next(s for s in spans if s["context"]["span_id"] == span_id)
    attributes = root["attributes"]
    assert root["name"] == "question" and root.get("parent_id") in (None, "")
    assert attributes["session.id"] == session and attributes["user.id"] == "4242"
    assert_test(
        LLMTestCase(input=attributes["input.value"], actual_output=attributes["output.value"]),
        [ContainsAll(["Мидтерм в среду"], name="AnswerRecorded")],
    )
    assert any(s.get("parent_id") == span_id for s in spans), "the LangChain run is not under the question span"


def test_private_file_question_reaches_phoenix_with_nested_runs(phoenix):
    session = "private-test-" + uuid.uuid4().hex[:8]
    with tracing.private():
        with tracing.question(session, "synthetic-private-user", "synthetic private document question") as traced:
            RunnableLambda(lambda x: str(x).upper()).invoke(
                "synthetic private tool text", tracing.run_config(session, "synthetic-private-user")  # pyright: ignore[reportArgumentType]
            )
            with tracing.span("synthetic-file-read", "TOOL", input="synthetic file text") as output:
                output("synthetic extracted answer")
            traced.answer("synthetic file answer")
    assert traced.id
    tracing.flush()
    spans = spans_of(phoenix, traced.id)
    root = next(s for s in spans if s["context"]["span_id"] == traced.id)
    assert root["attributes"]["session.id"] == session
    assert root["attributes"]["user.id"] == "synthetic-private-user"
    assert root["attributes"]["input.value"] == "synthetic private document question"
    assert root["attributes"]["output.value"] == "synthetic file answer"
    assert any(s["name"] == "synthetic-file-read" and s.get("parent_id") == traced.id for s in spans)
    assert any(s.get("parent_id") == traced.id and s["name"] != "synthetic-file-read" for s in spans)
    tracing.score_feedback(traced.id, "api:synthetic-private-user", False, "Synthetic file feedback")
    annotations = phoenix.spans.get_span_annotations(span_ids=[traced.id], project_identifier=settings.phoenix_project)
    assert [(a["identifier"], a["result"]["score"], a["result"].get("explanation")) for a in annotations] == [
        ("api:synthetic-private-user", 0.0, "Synthetic file feedback")]


def test_feedback_is_an_annotation_and_a_second_vote_replaces_the_first(phoenix):
    span_id, _ = traced_run()
    spans_of(phoenix, span_id)
    tracing.score_feedback(span_id, "tg:4242", True)
    tracing.score_feedback(span_id, "tg:4242", False)  # the same user changes their mind
    tracing.score_feedback(span_id, "tg:4343", True)  # someone else keeps theirs
    tracing.score_feedback(span_id, "api:u1", False)
    tracing.score_feedback(span_id, "api:u1", False, "Не тот корпус")  # then says what was wrong with the answer
    annotations = phoenix.spans.get_span_annotations(span_ids=[span_id], project_identifier=settings.phoenix_project)
    votes = {a["identifier"]: (a["result"]["label"], a["result"]["score"], a["result"].get("explanation")) for a in annotations}
    assert votes == {"tg:4242": ("👎", 0.0, None), "tg:4343": ("👍", 1.0, None), "api:u1": ("👎", 0.0, "Не тот корпус")}


def test_without_tracing_nothing_breaks(monkeypatch):
    monkeypatch.setattr(tracing, "_provider", None)
    with tracing.question("t", "1", "q") as traced:
        traced.answer("a")
    assert traced.id is None and tracing.run_config("t", "1") == {"configurable": {"thread_id": "t"}}
    tracing.score_feedback("abc", "tg:1", True)  # off: does nothing
