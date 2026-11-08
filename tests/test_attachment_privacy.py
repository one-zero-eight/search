"""File conversations must not export document text to tracing or application logs."""

from types import SimpleNamespace

from catix.agent import tracing


def test_private_scope_suppresses_manual_and_instrumented_traces(monkeypatch):
    from opentelemetry import context
    from opentelemetry.context import _SUPPRESS_INSTRUMENTATION_KEY

    class NoTraces:
        def get_tracer(self, *args):
            raise AssertionError("private content reached the trace provider")

    monkeypatch.setattr(tracing, "_provider", NoTraces())
    private = getattr(tracing, "private", None)
    assert private is not None, "file conversations need a trace-suppression scope"
    assert not tracing.is_private()
    with private(True):
        assert tracing.is_private()
        assert context.get_value(_SUPPRESS_INSTRUMENTATION_KEY)
        with tracing.question("api:chat", "owner", "secret document text") as question:
            assert question.id is None
            question.answer("private extracted data")
        with tracing.span("read", "TOOL", input="private bytes") as output:
            output("private output")
        with private(False):
            assert tracing.is_private(), "nested nonprivate code must not unsuppress its parent"
    assert not tracing.is_private()
    assert not context.get_value(_SUPPRESS_INSTRUMENTATION_KEY)


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
