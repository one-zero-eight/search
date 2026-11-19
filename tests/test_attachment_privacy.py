"""File conversations have full Phoenix traces, but redact ordinary application logs."""

from types import SimpleNamespace

import pytest

from catix.agent import tracing


def test_private_scope_keeps_tracing_enabled_and_marks_private_context(monkeypatch):
    from opentelemetry import context
    from opentelemetry.context import _SUPPRESS_INSTRUMENTATION_KEY

    provider = SimpleNamespace(get_tracer=lambda *args: None)
    monkeypatch.setattr(tracing, "_provider", provider)
    private = getattr(tracing, "private", None)
    assert private is not None, "file conversations need a private-log redaction scope"
    assert not tracing.is_private()
    assert tracing.enabled()
    with private(True):
        assert tracing.is_private()
        assert tracing.enabled(), "private file conversations should still export Phoenix traces"
        assert not context.get_value(_SUPPRESS_INSTRUMENTATION_KEY)
        with private(False):
            assert tracing.is_private(), "nested nonprivate code must not clear its parent's privacy marker"
    assert not tracing.is_private()
    assert not context.get_value(_SUPPRESS_INSTRUMENTATION_KEY)


@pytest.fixture
def traced_files(monkeypatch):
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from openinference.instrumentation.langchain import LangChainInstrumentor
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    instrumentor = LangChainInstrumentor()
    original_provider = tracing._provider
    was_instrumented = instrumentor.is_instrumented_by_opentelemetry
    if was_instrumented:
        instrumentor.uninstrument()
    try:
        instrumentor.instrument(tracer_provider=provider)
        monkeypatch.setattr(tracing, "_provider", provider)
        yield exporter
    finally:
        instrumentor.uninstrument()
        if was_instrumented:
            instrumentor.instrument(tracer_provider=original_provider)
        provider.shutdown()


def test_private_question_exports_manual_and_langchain_spans(traced_files):
    from langchain_core.runnables import RunnableLambda

    with tracing.private():
        session = "file-chat-test"
        with tracing.question(session, "owner-test", "private question sentinel") as question:
            RunnableLambda(lambda text: str(text).upper()).invoke(
                "private tool input", tracing.run_config(session, "owner-test")  # pyright: ignore[reportArgumentType]
            )
            with tracing.span("file-read", "TOOL", input="private file data") as done:
                done("private answer sentinel")
            question.answer("private answer sentinel")

    spans = traced_files.get_finished_spans()
    root = next(item for item in spans if item.name == "question")
    assert question.id == f"{root.context.span_id:016x}"
    assert root.attributes["session.id"] == session
    assert root.attributes["user.id"] == "owner-test"
    assert root.attributes["input.value"] == "private question sentinel"
    assert root.attributes["output.value"] == "private answer sentinel"
    children = [item for item in spans if item.context.trace_id == root.context.trace_id and item.parent]
    assert any(item.name == "file-read" and item.parent.span_id == root.context.span_id for item in children)
    assert any(item.name == "RunnableLambda" and item.parent.span_id == root.context.span_id for item in children), \
        "LangChain run was not exported under the question"
    assert not tracing.is_private()


def test_file_tool_arguments_do_not_reach_application_logs(caplog):
    import logging
    import time
    from catix.agent.core import LoggingMiddleware
    from langchain_core.messages import ToolMessage

    request = SimpleNamespace(tool_call={"name": "ask_docs", "args": {"question": "PRIVATE_ATTACHMENT_SENTINEL"}})
    with caplog.at_level(logging.INFO), tracing.private():
        LoggingMiddleware()._log_tool(request, ToolMessage("data", tool_call_id="read"), time.monotonic())
    assert "PRIVATE_ATTACHMENT_SENTINEL" not in caplog.text
    assert "ask_docs" in caplog.text
