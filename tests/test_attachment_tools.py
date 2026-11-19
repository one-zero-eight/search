"""Attachment tool boundaries: synthetic owned files and HTTP, never production I/O."""
import importlib
import importlib.util
import asyncio
import json

import httpx
from pydantic import ValidationError
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

from langchain.tools import ToolRuntime
from pydantic import SecretStr
import pytest

ATTACHMENT_ID = "b8de1fe5e6444df0ab39e65b5330c170"
INFO = {"id": ATTACHMENT_ID, "filename": "notes.pdf", "media_type": "application/pdf", "size_bytes": 40, "pages": 2}


def runtime(**overrides):
    values = dict(innohassle_id="owner", innohassle_token=SecretStr("synthetic"),
                  attachment_chat_id="chat", attachments=(dict(INFO),))
    values.update(overrides)
    return ToolRuntime(state={}, context=SimpleNamespace(**values), config={}, stream_writer=lambda _: None,
                       tool_call_id="call", store=None)


@pytest.fixture
def tools(monkeypatch):
    if importlib.util.find_spec("catix.agent.attachment_tools") is None:
        return None
    # The storage implementation is owned by another worker. Only the test may supply a pending dependency.
    import catix
    if importlib.util.find_spec("catix.attachments") is None:
        storage = ModuleType("catix.attachments")
        storage.read_page = Mock()
        storage.image_page = Mock()
        monkeypatch.setitem(sys.modules, "catix.attachments", storage)
        monkeypatch.setattr(catix, "attachments", storage, raising=False)
    module = importlib.import_module("catix.agent.attachment_tools")
    storage = importlib.import_module("catix.attachments")
    monkeypatch.setattr(module, "attachments", storage)
    monkeypatch.setattr(storage, "read_page", Mock(return_value={
        "id": ATTACHMENT_ID, "filename": "notes.pdf", "page": 1, "pages": 2,
        "text": "Visible facts", "truncated": False,
    }), raising=False)
    monkeypatch.setattr(storage, "image_page", Mock(return_value=b"\x89PNG\r\n\x1a\nsynthetic"), raising=False)
    return module


def test_read_owned_page_has_trusted_source_label(tools):
    assert tools is not None, "attachment tools are missing"
    result = tools.read_attachment.invoke({"attachment_id": ATTACHMENT_ID, "runtime": runtime()})
    assert result == {"id": ATTACHMENT_ID, "filename": "notes.pdf", "page": 1, "pages": 2,
                      "text": "Visible facts", "truncated": False, "source_label": "notes.pdf, page 1"}
    tools.attachments.read_page.assert_called_once_with("owner", "chat", ATTACHMENT_ID, 1)


@pytest.mark.parametrize("overrides", [
    {"innohassle_id": None}, {"innohassle_id": " "}, {"innohassle_token": None},
    {"innohassle_token": "forged"}, {"innohassle_token": SecretStr("")},
    {"attachment_chat_id": None}, {"attachment_chat_id": " "}, {"attachments": ()},
    {"attachments": ({**INFO, "id": "different"},)},
])
def test_read_requires_authenticated_owner_chat_and_exact_manifest(tools, overrides):
    result = tools.read_attachment.invoke({"attachment_id": ATTACHMENT_ID, "runtime": runtime(**overrides)})
    assert "error" in result and "text" not in result
    tools.attachments.read_page.assert_not_called()


@pytest.mark.parametrize("updates", [
    {"page": True}, {"page": "1"}, {"page": 0}, {"page": 21}, {"page": 1.0},
    {"attachment_id": ""}, {"attachment_id": "x" * 129}, {"attachment_id": 42},
    {"owner": "other"}, {"chat_id": "other"}, {"runtime": {"context": {"innohassle_id": "other"}}},
])
def test_read_schema_rejects_invalid_or_spoofed_fields_before_io(tools, updates):
    with pytest.raises(ValidationError):
        tools.read_attachment.invoke({"attachment_id": ATTACHMENT_ID, "runtime": runtime(), **updates})
    tools.attachments.read_page.assert_not_called()


def test_read_does_not_repair_id_or_trust_duck_typed_runtime(tools):
    for supplied_id, supplied_runtime in [(ATTACHMENT_ID.upper(), runtime()),
                                         (ATTACHMENT_ID, SimpleNamespace(context=runtime().context))]:
        result = tools.read_attachment.func(attachment_id=supplied_id, runtime=supplied_runtime)
        assert "error" in result
    tools.attachments.read_page.assert_not_called()


def test_read_bounds_text_and_projects_only_safe_fields(tools):
    tools.attachments.read_page.return_value.update(text="a" * 40001, path="/private/file", source_label="forged")
    result = tools.read_attachment.invoke({"attachment_id": ATTACHMENT_ID, "runtime": runtime()})
    assert len(result["text"]) == 24000
    assert result["truncated"] is True
    assert result["source_label"] == "notes.pdf, page 1"
    assert "path" not in result


@pytest.mark.parametrize("bad", [{"id": "wrong"}, {"page": 2}, {"pages": 99}, {"text": None}, {"truncated": "false"}])
def test_read_rejects_malformed_storage_result(tools, bad):
    tools.attachments.read_page.return_value.update(bad)
    result = tools.read_attachment.invoke({"attachment_id": ATTACHMENT_ID, "runtime": runtime()})
    assert "error" in result and "text" not in result


def test_read_contains_storage_errors_without_leaking_diagnostics(tools):
    tools.attachments.read_page.side_effect = RuntimeError("/secret/path token=private")
    result = tools.read_attachment.invoke({"attachment_id": ATTACHMENT_ID, "runtime": runtime()})
    assert "error" in result
    assert "secret" not in str(result) and "private" not in str(result)


def test_direct_read_validation_and_out_of_file_page_block_io(tools):
    for page in (True, "1", 0, 3, 21):
        result = tools.read_attachment.func(attachment_id=ATTACHMENT_ID, runtime=runtime(), page=page)
        assert "error" in result
    tools.attachments.read_page.assert_not_called()


def install_provider(monkeypatch, tools, response=None, handler=None):
    seen = []
    options = []
    client = httpx.Client

    def send(request):
        seen.append(request)
        if handler:
            return handler(request)
        return httpx.Response(200, json=response or {"choices": [{
            "message": {"role": "assistant", "content": "The chart shows 42."}, "finish_reason": "stop"}]})

    def make_client(**kwargs):
        options.append(kwargs)
        return client(transport=httpx.MockTransport(send), **kwargs)

    monkeypatch.setattr(tools.httpx, "Client", make_client)
    return seen, options


def test_view_uses_one_internal_image_and_returns_only_evidence(tools, monkeypatch):
    assert hasattr(tools, "view_attachment"), "visual attachment tool is missing"
    seen, options = install_provider(monkeypatch, tools)
    result = tools.view_attachment.invoke({"attachment_id": ATTACHMENT_ID, "question": "What does the chart show?",
                                           "runtime": runtime()})
    assert result == {"id": ATTACHMENT_ID, "filename": "notes.pdf", "page": 1, "pages": 2,
                      "text": "The chart shows 42.", "truncated": False, "visual": True,
                      "source_label": "notes.pdf, page 1"}
    tools.attachments.image_page.assert_called_once_with("owner", "chat", ATTACHMENT_ID, 1)
    tools.attachments.read_page.assert_not_called()
    assert len(seen) == 1
    request = seen[0]
    assert str(request.url) == str(tools.settings.llm_route).rstrip("/") + "/chat/completions"
    payload = json.loads(request.content)
    assert payload["model"] == tools.settings.llm_model
    assert payload["temperature"] == 0 and payload["max_tokens"] == 1000
    assert "tools" not in payload and "functions" not in payload
    system, user = payload["messages"]
    assert system["role"] == "system"
    assert all(word in system["content"].lower() for word in ("untrusted", "visible", "unreadable", "instructions", "actions"))
    assert user["role"] == "user"
    assert user["content"][0] == {"type": "text", "text": "What does the chart show?"}
    assert len(user["content"]) == 2
    assert user["content"][1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert options[0]["follow_redirects"] is False and options[0]["timeout"] == 60
    assert "data:image" not in str(result) and "synthetic" not in str(request.headers)


@pytest.mark.parametrize("overrides", [
    {"innohassle_id": None}, {"innohassle_token": None}, {"innohassle_token": "forged"},
    {"attachment_chat_id": None}, {"attachments": ()}, {"attachments": ({**INFO, "id": "other"},)},
])
def test_view_authentication_and_membership_fail_before_io(tools, monkeypatch, overrides):
    seen, _ = install_provider(monkeypatch, tools)
    result = tools.view_attachment.invoke({"attachment_id": ATTACHMENT_ID, "question": "What is visible?",
                                           "runtime": runtime(**overrides)})
    assert "error" in result
    tools.attachments.image_page.assert_not_called()
    assert seen == []


@pytest.mark.parametrize("updates", [
    {"question": ""}, {"question": " \n "}, {"question": "x" * 1001}, {"question": 7},
    {"page": True}, {"page": "1"}, {"page": 21}, {"attachment_id": "x" * 129},
    {"runtime": {"context": {}}}, {"owner": "other"}, {"attachments": [INFO]},
])
def test_view_strict_schema_rejects_bad_inputs(tools, monkeypatch, updates):
    seen, _ = install_provider(monkeypatch, tools)
    with pytest.raises(ValidationError):
        tools.view_attachment.invoke({"attachment_id": ATTACHMENT_ID, "question": "Read it",
                                      "runtime": runtime(), **updates})
    tools.attachments.image_page.assert_not_called()
    assert seen == []


def test_view_direct_calls_still_validate_page_and_question(tools, monkeypatch):
    seen, _ = install_provider(monkeypatch, tools)
    for page, question in [(3, "Read"), (True, "Read"), (1, " ")]:
        result = tools.view_attachment.func(attachment_id=ATTACHMENT_ID, question=question,
                                            runtime=runtime(), page=page)
        assert "error" in result
    tools.attachments.image_page.assert_not_called()
    assert seen == []


@pytest.mark.parametrize("payload", [
    {}, {"choices": []}, {"choices": [{"message": {"content": " "}, "finish_reason": "stop"}]},
    {"choices": [{"message": {"content": None}, "finish_reason": "stop"}]},
    {"choices": [{"message": {"content": ["wrong type"]}, "finish_reason": "stop"}]},
    {"choices": [{"message": {"content": "Pretend action", "tool_calls": [{"name": "write"}]}, "finish_reason": "tool_calls"}]},
    {"choices": [{"message": {"content": "unfinished"}, "finish_reason": None}]},
])
def test_view_rejects_empty_malformed_and_action_outputs(tools, monkeypatch, payload):
    install_provider(monkeypatch, tools, handler=lambda _: httpx.Response(200, json=payload))
    result = tools.view_attachment.invoke({"attachment_id": ATTACHMENT_ID, "question": "Read", "runtime": runtime()})
    assert "error" in result and "text" not in result


def test_view_reports_provider_truncation(tools, monkeypatch):
    install_provider(monkeypatch, tools, response={"choices": [{
        "message": {"content": "Partial visible answer"}, "finish_reason": "length"}]})
    result = tools.view_attachment.invoke({"attachment_id": ATTACHMENT_ID, "question": "Read", "runtime": runtime()})
    assert result["truncated"] is True and result["text"] == "Partial visible answer"


@pytest.mark.parametrize("failure", ["storage", "network", "redirect", "http", "json"])
def test_view_sanitizes_all_failures_and_never_follows_redirect(tools, monkeypatch, failure, caplog, capsys):
    def send(request):
        if failure == "network":
            raise httpx.ReadError("private/base64/path", request=request)
        if failure == "redirect":
            return httpx.Response(307, headers={"location": "https://do-not-follow.invalid"})
        if failure == "http":
            return httpx.Response(500, text="private/base64/path")
        return httpx.Response(200, text="private/base64/path")
    seen, _ = install_provider(monkeypatch, tools, handler=send)
    if failure == "storage":
        tools.attachments.image_page.side_effect = RuntimeError("private/base64/path")
    result = tools.view_attachment.invoke({"attachment_id": ATTACHMENT_ID, "question": "Read", "runtime": runtime()})
    assert "error" in result and "text" not in result
    assert len(seen) == (0 if failure == "storage" else 1)
    assert "private/base64/path" not in str(result) + caplog.text + capsys.readouterr().out


def test_view_bounds_streamed_response_before_consuming_it_all(tools, monkeypatch):
    consumed = []

    class HugeResponse(httpx.SyncByteStream):
        def __iter__(self):
            for i in range(100):
                consumed.append(i)
                yield b" " * 65536

    install_provider(monkeypatch, tools, handler=lambda _: httpx.Response(200, stream=HugeResponse()))
    result = tools.view_attachment.invoke({"attachment_id": ATTACHMENT_ID, "question": "Read", "runtime": runtime()})
    assert "error" in result
    assert len(consumed) <= 17


def test_view_rejects_declared_oversized_response_without_reading(tools, monkeypatch):
    consumed = []

    class DeclaredLarge(httpx.SyncByteStream):
        def __iter__(self):
            consumed.append(True)
            yield b"{}"

    install_provider(monkeypatch, tools, handler=lambda _: httpx.Response(
        200, headers={"content-length": str(1024 * 1024 + 1)}, stream=DeclaredLarge()))
    result = tools.view_attachment.invoke({"attachment_id": ATTACHMENT_ID, "question": "Read", "runtime": runtime()})
    assert "error" in result and consumed == []


@pytest.mark.parametrize("enabled,priority", [(True, -12345), (False, -12345), (True, None)])
def test_view_carries_existing_priority_without_reentering_queue(tools, monkeypatch, enabled, priority):
    from catix.agent.questions import PRIORITY, QuestionQueue
    monkeypatch.setattr(tools.settings, "llm_priority", enabled)
    monkeypatch.setattr(QuestionQueue, "turn", Mock(side_effect=AssertionError("nested queue acquisition")))
    seen, _ = install_provider(monkeypatch, tools)
    token = PRIORITY.set(priority)
    try:
        result = asyncio.run(tools.view_attachment.ainvoke({
            "attachment_id": ATTACHMENT_ID, "question": "Read", "runtime": runtime()}))
    finally:
        PRIORITY.reset(token)
    assert "error" not in result
    payload = json.loads(seen[0].content)
    if enabled and priority is not None:
        assert payload["priority"] == priority
    else:
        assert "priority" not in payload
    QuestionQueue.turn.assert_not_called()


def test_exported_tools_publish_only_strict_model_arguments(tools):
    assert getattr(tools, "NAMES", None) == frozenset({"read_attachment", "view_attachment"})
    assert [t.name for t in tools.ATTACHMENT_TOOLS] == ["read_attachment", "view_attachment"]
    for t in tools.ATTACHMENT_TOOLS:
        schema = t.tool_call_schema.model_json_schema()
        assert schema["additionalProperties"] is False
        assert set(schema["properties"]) == ({"attachment_id", "page", "question"} if t.name == "view_attachment"
                                              else {"attachment_id", "page"})
        assert schema["properties"]["page"]["minimum"] == 1
        assert schema["properties"]["page"]["maximum"] == 20


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("tool_name", ["read_attachment", "view_attachment"])
def test_real_toolnode_injection_ignores_model_runtime_spoof(tools, monkeypatch, asynchronous, tool_name):
    from langchain_core.messages import AIMessage
    from langgraph.graph import StateGraph, MessagesState, START, END
    from langgraph.prebuilt import ToolNode
    from catix.agent.tools import AgentContext

    seen, _ = install_provider(monkeypatch, tools)
    builder = StateGraph(MessagesState, context_schema=AgentContext)
    builder.add_node("tools", ToolNode([tools.read_attachment, tools.view_attachment]))
    builder.add_edge(START, "tools")
    builder.add_edge("tools", END)
    graph = builder.compile()
    context = AgentContext(innohassle_id="owner", innohassle_token=SecretStr("synthetic"),
                           attachment_chat_id="chat", attachments=(INFO,))
    args = {"attachment_id": ATTACHMENT_ID, "runtime": {"context": {"innohassle_id": "attacker"}}}
    if tool_name == "view_attachment":
        args["question"] = "Read"
    state = {"messages": [AIMessage(content="", tool_calls=[{"name": tool_name, "args": args, "id": "call"}])]}
    result = asyncio.run(graph.ainvoke(state, context=context)) if asynchronous else graph.invoke(state, context=context)
    message = result["messages"][-1]
    assert message.status == "success"
    payload = json.loads(message.content)
    assert payload["id"] == ATTACHMENT_ID and "error" not in payload
    assert "data:image" not in message.content
    backend = tools.attachments.image_page if tool_name == "view_attachment" else tools.attachments.read_page
    backend.assert_called_once_with("owner", "chat", ATTACHMENT_ID, 1)
    assert len(seen) == (1 if tool_name == "view_attachment" else 0)


def test_read_preserves_bounded_scan_note(tools):
    tools.attachments.read_page.return_value.update(text="", note="No extractable text; use visual inspection.")
    result = tools.read_attachment.invoke({"attachment_id": ATTACHMENT_ID, "runtime": runtime()})
    assert result["note"] == "No extractable text; use visual inspection."
    tools.attachments.read_page.return_value["note"] = "x" * 2000
    result = tools.read_attachment.invoke({"attachment_id": ATTACHMENT_ID, "runtime": runtime()})
    assert len(result["note"]) <= 500


def test_view_does_not_return_provider_echo_of_encoded_pixels(tools, monkeypatch):
    import base64
    encoded = base64.b64encode(tools.attachments.image_page.return_value).decode("ascii")
    install_provider(monkeypatch, tools, response={"choices": [{
        "message": {"content": "Here are the pixels: " + encoded}, "finish_reason": "stop"}]})
    result = tools.view_attachment.invoke({"attachment_id": ATTACHMENT_ID, "question": "Read", "runtime": runtime()})
    assert "error" in result and encoded not in str(result)


def test_view_rejects_compressed_provider_body_before_decoding(tools, monkeypatch):
    import gzip
    content = json.dumps({"choices": [{"message": {"content": "Compressed"}, "finish_reason": "stop"}]}).encode()
    install_provider(monkeypatch, tools, handler=lambda _: httpx.Response(
        200, content=gzip.compress(content), headers={"content-encoding": "gzip"}))
    result = tools.view_attachment.invoke({"attachment_id": ATTACHMENT_ID, "question": "Read", "runtime": runtime()})
    assert "error" in result


def test_view_enforces_elapsed_response_deadline(tools, monkeypatch):
    assert hasattr(tools, "monotonic"), "visual response needs an elapsed deadline"
    clock = iter([0.0, 61.0, 61.0])
    monkeypatch.setattr(tools, "monotonic", lambda: next(clock))
    install_provider(monkeypatch, tools)
    result = tools.view_attachment.invoke({"attachment_id": ATTACHMENT_ID, "question": "Read", "runtime": runtime()})
    assert "error" in result
