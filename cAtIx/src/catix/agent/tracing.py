"""Tracing in Arize Phoenix (docker-compose.yml, one container): `run_config` is the config for every agent call, `question` is
the root span of one question, and the users' 👍/👎 on an answer are annotations on that span (`score_feedback`).

The LangChain/LangGraph runs are traced by the OpenInference instrumentation, which sees every run in the process: model calls,
tools, middleware. The root span groups them under one entry with the question, the answer, the session and the user. Without
PHOENIX_ENDPOINT everything here does nothing.
"""

import contextlib
import logging
import time
from collections.abc import Iterator
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
        yield Question(id=format(span.get_span_context().span_id, "016x"), _span=span)


def log_status() -> None:
    """Say at startup (after logging is configured) whether and where traces go."""
    if enabled():
        log.info("phoenix tracing on (%s, project %s)", settings.phoenix_endpoint, settings.phoenix_project)
    else:
        log.warning("tracing is off: set PHOENIX_ENDPOINT (docker compose up -d phoenix, http://localhost:6006)")


def flush() -> None:
    if _provider is not None:
        _provider.force_flush()


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
