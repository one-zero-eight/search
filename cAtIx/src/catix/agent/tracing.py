"""Tracing in Arize Phoenix (docker-compose.yml, one container): `run_config` is the config for every agent call, `question` is
the root span of one question, and the users' 👍/👎 on an answer are annotations on that span (`score_feedback`).

The LangChain/LangGraph runs are traced by the OpenInference instrumentation, which sees every run in the process: model calls,
tools, middleware. The root span groups them under one entry with the question, the answer, the session and the user. `span`
adds the steps inside a tool (BM25, vectors, the reranker), so that a trace shows where a search spends its time. Without
PHOENIX_ENDPOINT everything here does nothing.
"""

import contextlib
import contextvars
import json
import logging
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

from catix.settings import settings

log = logging.getLogger("catix.tracing")

_provider = None
_client = None
if settings.phoenix_endpoint:
    from openinference.instrumentation.langchain import LangChainInstrumentor
    from phoenix.otel import register

    _provider = register(
        project_name=settings.phoenix_project,
        endpoint=f"{str(settings.phoenix_endpoint).rstrip('/')}/v1/traces",
        batch=True,
        auto_instrument=False,
        set_global_tracer_provider=False,
    )
    LangChainInstrumentor().instrument(tracer_provider=_provider)


def enabled() -> bool:
    return _provider is not None


def run_config(thread_id: str, user_id: str | None = None, name: str | None = None) -> dict:
    """Config for one LLM run: the conversation thread and, when tracing is on, the session and user of the trace and its name."""
    config: dict = {"configurable": {"thread_id": thread_id}}
    if name:
        config["run_name"] = name
    if enabled():  # OpenInference reads `session_id` and `user_id` from the run metadata
        config["metadata"] = {"session_id": thread_id, **({"user_id": user_id} if user_id else {})}
    return config


@dataclass
class Question:
    """The root span of one question. `id` is what a 👍/👎 refers to (None when tracing is off)."""

    id: str | None = None
    trace_id: str | None = None  # The whole trace in Phoenix (the tests print it for a failed test)
    _span: object | None = field(default=None, repr=False)

    def answer(self, text: str) -> None:
        if self._span is not None:
            self._span.set_attribute("output.value", text)  # type: ignore[attr-defined]


@contextlib.contextmanager
def question(thread_id: str, user_id: str | None, text: str) -> Iterator[Question]:
    """`with tracing.question(thread, user, text) as q:` around the agent call. The spans of the run nest under it."""
    if _provider is None:
        yield Question()
        return
    attributes = {"openinference.span.kind": "AGENT", "session.id": thread_id, "input.value": text}
    if user_id:
        attributes["user.id"] = user_id
    with _provider.get_tracer("catix").start_as_current_span("question", attributes=attributes) as span:
        context = span.get_span_context()
        yield Question(id=format(context.span_id, "016x"), trace_id=format(context.trace_id, "032x"), _span=span)


_step: contextvars.ContextVar = contextvars.ContextVar("catix_step", default=None)


def _parent():
    """The span a step belongs to: the step it is inside of, else the LangChain run (a tool) it is called from. The
    OpenInference spans of LangChain runs are not the current OpenTelemetry span, so a step would hang off the question."""
    if _provider is None:
        return None
    import langchain_core.runnables.config  # noqa: F401 - get_current_span reads it as an attribute, which needs the import
    from openinference.instrumentation.langchain import get_current_span
    from opentelemetry import trace

    for candidate in (_step.get(), get_current_span(), trace.get_current_span()):
        if candidate is not None and candidate.is_recording():
            return candidate
    return None


@contextlib.contextmanager
def span(name: str, kind: str = "CHAIN", input: object = None, **attributes) -> Iterator[Callable[[object], None]]:
    """`with tracing.span("bm25", "RETRIEVER", input=words) as done: ...; done(result)`: one step of a search as a child of
    the tool that runs it, with its time. `done` records what the step gave (a count or a short value).

    Only inside a traced question: the worker's embeddings and the experiments make no traces of their own."""
    parent = _parent()
    if parent is None:
        yield lambda _: None
        return
    from opentelemetry import trace

    attrs = {"openinference.span.kind": kind, **{k: v for k, v in attributes.items() if v is not None}}
    if input is not None:
        attrs["input.value"] = input if isinstance(input, str) else json.dumps(input, ensure_ascii=False, default=str)
    with _provider.get_tracer("catix").start_as_current_span(name, context=trace.set_span_in_context(parent), attributes=attrs) as current:
        token = _step.set(current)
        try:
            yield lambda output: current.set_attribute(
                "output.value", output if isinstance(output, str) else json.dumps(output, ensure_ascii=False, default=str)
            )
        finally:
            _step.reset(token)


def carry(fn: Callable) -> Callable:
    """`fn` that runs inside the current step in another thread: a thread pool does not carry the context, and the steps
    run there would hang off nothing."""
    parent = _parent()

    def run(*args, **kwargs):
        token = _step.set(parent)
        try:
            return fn(*args, **kwargs)
        finally:
            _step.reset(token)

    return run


def log_status() -> None:
    """Say at startup (after logging is configured) whether and where traces go."""
    if enabled():
        log.info("phoenix tracing on (%s, project %s)", settings.phoenix_endpoint, settings.phoenix_project)
    else:
        log.warning("tracing is off: set PHOENIX_ENDPOINT (docker compose up -d phoenix, http://localhost:6006)")


def flush() -> None:
    if _provider is not None:
        _provider.force_flush()


MODELS = "{ generativeModels(first: 1000) { edges { node { id name kind } } } }"
CREATE = "mutation($input: CreateModelMutationInput!) { createModel(input: $input) { model { id } } }"
UPDATE = "mutation($input: UpdateModelMutationInput!) { updateModel(input: $input) { model { id } } }"


def price_model(name: str, prices: dict[str, float]) -> None:
    """The model's prices (USD per 1M tokens: input, cache_read, output) in Phoenix, which then shows the cost of each call
    and trace. A model Phoenix has no price for (a new one, a local one) shows none."""
    if not enabled() or not prices:
        return
    import re

    import httpx

    def gql(query: str, variables: dict | None = None) -> dict:
        r = httpx.post(f"{str(settings.phoenix_endpoint).rstrip('/')}/graphql", json={"query": query, "variables": variables or {}}, timeout=10)
        r.raise_for_status()
        if r.json().get("errors"):
            raise RuntimeError(r.json()["errors"][0]["message"])
        return r.json()["data"]

    costs = [{"tokenType": t, "kind": "COMPLETION" if t == "output" else "PROMPT", "costPerMillionTokens": float(v)} for t, v in prices.items()]
    model = {"name": name, "namePattern": re.escape(name), "costs": costs}
    try:
        mine = [e["node"] for e in gql(MODELS)["generativeModels"]["edges"] if e["node"]["name"] == name and e["node"]["kind"] == "CUSTOM"]
        if mine:
            gql(UPDATE, {"input": {"id": mine[0]["id"], **model}})
        else:
            gql(CREATE, {"input": model})
    except Exception as e:  # noqa: BLE001 - the costs are a convenience: the run goes on without them
        log.warning("could not set the prices of %s in Phoenix: %s", name, e)


def _phoenix_client():
    global _client
    if _client is None:
        from phoenix.client import Client

        _client = Client(base_url=str(settings.phoenix_endpoint).rstrip("/"))
    return _client


def score_feedback(span_id: str, user_id: int, good: bool) -> None:
    """A user's thumbs up (1) or down (0) on the answer whose root span is `span_id`; the same user changing their mind replaces
    the earlier vote (same `identifier`). The span reaches Phoenix a few seconds after the answer, so an early vote waits a bit."""
    if not enabled():
        return
    last: Exception | None = None
    for attempt in range(3):
        try:
            _phoenix_client().spans.add_span_annotation(
                annotation_name="user-feedback",
                annotator_kind="HUMAN",
                span_id=span_id,
                label="👍" if good else "👎",
                score=1.0 if good else 0.0,
                identifier=f"tg:{user_id}",
                sync=True,
            )
            return
        except Exception as e:  # noqa: BLE001 - usually "the span is not there yet"
            last = e
            time.sleep(3)
    raise last  # type: ignore[misc]
