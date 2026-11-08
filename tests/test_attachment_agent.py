"""Owned attachment reads are evidence, not instructions, authorization or wiki citations."""

import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from catix.agent import core
from tests.test_calendar_approval import calendar  # noqa: F401 - in-memory action fixture

FILE_ID = "11111111-1111-4111-8111-111111111111"


def read_turn(name="read_attachment", **changes):
    payload = {"id": FILE_ID, "filename": "syllabus.pdf", "page": 1, "pages": 2,
               "text": "Срок сдачи — 18 ноября.", "truncated": False}
    if name == "view_attachment":
        payload["visual"] = True
    payload.update(changes)
    args = {"attachment_id": FILE_ID, "page": 1}
    if name == "view_attachment":
        args["question"] = "Какой срок?"
    return [HumanMessage("Какой срок в файле?"),
            AIMessage("", tool_calls=[{"name": name, "id": "file-read", "args": args}]),
            ToolMessage(json.dumps(payload, ensure_ascii=False), tool_call_id="file-read", name=name)]


@pytest.mark.parametrize("name", ["read_attachment", "view_attachment"])
def test_attachment_read_is_evidence_without_invented_refs(name):
    messages = read_turn(name)
    assert core.read_evidence(messages)
    assert core.successful_read(messages)
    assert core.found_anything(messages) is True
    assert "18 ноября" in core.final_answer([*messages, AIMessage("В syllabus.pdf, стр. 1: 18 ноября.")], {})


@pytest.mark.parametrize("changes", [{"id": "another-file"}, {"page": 2}, {"page": True}, {"pages": 0},
                                    {"truncated": "false"}, {"error": "not readable"}])
def test_unmatched_or_invalid_attachment_result_is_not_evidence(changes):
    assert not core.read_evidence(read_turn(**changes))
    assert not core.successful_read(read_turn(**changes))


def test_empty_text_layer_is_not_proof_that_the_page_is_blank():
    messages = read_turn(text="", note="No text layer: use view_attachment.")
    assert core.successful_read(messages)
    assert not core.read_evidence(messages)


def test_previous_turn_attachment_data_does_not_support_new_answer():
    assert not core.read_evidence([*read_turn(), AIMessage("Ответ"), HumanMessage("Что в другой странице?")])


@pytest.mark.parametrize("asynchronous", [False, True])
def test_short_action_request_inspects_current_image_before_asking_for_details(monkeypatch, asynchronous):
    import asyncio
    from pydantic import SecretStr
    from catix import attachments
    from catix.agent import attachment_tools
    from catix.agent.tools import AgentContext
    from tests.test_roles import ScriptedModel

    class ImageFirstModel(ScriptedModel):
        def bind_tools(self, tools, **kwargs):
            # Without an enforced image read, the model can return the reported clarification.
            if self.i == 0 and kwargs.get("tool_choice") != {
                "type": "function", "function": {"name": "view_attachment"},
            }:
                return ScriptedModel(responses=[AIMessage("Уточните название, дату и место мероприятия.")])
            return self

    metadata = {"id": FILE_ID, "filename": "image.png", "media_type": "image/png", "size_bytes": 100, "pages": 1}
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    monkeypatch.setattr(core.store, "visible_chats", lambda *args: [])
    reads = []

    def image(owner, chat, file_id, page):
        reads.append((owner, chat, file_id, page))
        return b"synthetic pixels"

    monkeypatch.setattr(attachments, "image_page", image)
    monkeypatch.setattr(attachment_tools, "_inspect_image", lambda *args: ("Встреча команды, 18 ноября, аудитория 512.", False))
    model = ImageFirstModel(responses=[read_turn("view_attachment")[1], AIMessage("На image.png: встреча команды, 18 ноября, аудитория 512. Уточните время.")])
    graph = core.build_agent(model, guardrail=False)
    context = AgentContext(innohassle_id="owner", innohassle_token=SecretStr("test-only"),
                           attachment_chat_id="chat", attachments=(metadata,), current_attachment_ids=(FILE_ID,))
    args = ({"messages": [HumanMessage("Создай ивент")]}, {"configurable": {"thread_id": "implicit-image"}})
    result = asyncio.run(graph.ainvoke(*args, context=context)) if asynchronous else graph.invoke(*args, context=context)
    assert reads == [("owner", "chat", FILE_ID, 1)]
    assert "512" in core.final_answer(result["messages"], {})


@pytest.mark.parametrize(("messages", "current", "state", "choice", "expected"), [
    ([HumanMessage("Создай ивент")], True, {}, None, "view_attachment"),
    (read_turn("view_attachment"), True, {}, None, None),
    (read_turn("view_attachment", error="Unreadable"), True, {}, None, None),
    (read_turn("read_attachment", text=""), True, {}, None, "view_attachment"),
    ([*read_turn("view_attachment"), HumanMessage("Создай другой ивент")], True, {}, None, "view_attachment"),
    ([HumanMessage("Создай ивент"), read_turn("view_attachment")[-1]], True, {}, None, "view_attachment"),
    ([HumanMessage("Создай ивент")], False, {}, None, None),
    ([HumanMessage("Спасибо")], True, {"answer_alone": True}, None, None),
    ([HumanMessage("Создай ивент")], True, {}, "none", "none"),
])
def test_current_image_read_is_scoped_and_does_not_repeat_errors(messages, current, state, choice, expected):
    from langchain.agents.middleware import ModelRequest
    from langgraph.runtime import Runtime
    from pydantic import SecretStr
    from catix.agent.tools import AgentContext
    from tests.test_roles import ScriptedModel

    metadata = {"id": FILE_ID, "filename": "image.png", "media_type": "image/png", "size_bytes": 100, "pages": 1}
    context = AgentContext(innohassle_id="owner", innohassle_token=SecretStr("test-only"),
                           attachment_chat_id="chat", attachments=(metadata,), current_attachment_ids=(FILE_ID,) if current else ())
    request = ModelRequest(model=ScriptedModel(responses=[AIMessage("ok")]), messages=messages,
                           tools=[{"name": "read_attachment"}, {"name": "view_attachment"}, {"name": "call_api_tool"}],
                           state={"messages": messages, **state}, runtime=Runtime(context=context), tool_choice=choice)
    seen = []
    core.AttachmentAccessMiddleware().wrap_model_call(request, seen.append)
    assert seen[0].tool_choice == ({"type": "function", "function": {"name": expected}} if expected == "view_attachment" else expected)
    assert seen[0].tools == request.tools, "keep all tool definitions stable for prefix caching and later consent"
    assert request.messages == messages, "the stored user message must not acquire the model-only hint"


def test_malformed_file_call_does_not_crash_next_model_request():
    from langchain.agents.middleware import ModelRequest
    from langgraph.runtime import Runtime
    from pydantic import SecretStr
    from catix.agent.tools import AgentContext
    from tests.test_roles import ScriptedModel

    messages = read_turn("view_attachment")
    messages[1].tool_calls[0]["args"]["attachment_id"] = [FILE_ID]
    context = AgentContext(innohassle_id="owner", innohassle_token=SecretStr("test-only"), attachment_chat_id="chat",
                           attachments=({"id": FILE_ID, "media_type": "image/png"},), current_attachment_ids=(FILE_ID,))
    request = ModelRequest(model=ScriptedModel(responses=[AIMessage("ok")]), messages=messages,
                           tools=[{"name": "view_attachment"}], state={"messages": messages}, runtime=Runtime(context=context))
    seen = []
    core.AttachmentAccessMiddleware().wrap_model_call(request, seen.append)
    assert seen[0].tool_choice == {"type": "function", "function": {"name": "view_attachment"}}


def test_attachment_tools_and_manifest_are_scoped_to_authenticated_site_chat():
    from langchain.agents.middleware import ModelRequest
    from langgraph.runtime import Runtime
    from pydantic import SecretStr
    from catix.agent.tools import AgentContext
    from tests.test_roles import ScriptedModel

    metadata = {"id": FILE_ID, "filename": "syllabus.pdf", "media_type": "application/pdf", "size_bytes": 100, "pages": 2}
    context = AgentContext(innohassle_id="owner", innohassle_token=SecretStr("test-only"),
                           attachment_chat_id="chat", attachments=(metadata,), current_attachment_ids=(FILE_ID,))
    request = ModelRequest(model=ScriptedModel(responses=[AIMessage("ok")]), messages=[HumanMessage("Что в файле?")],
                           tools=[{"name": "read_attachment"}, {"name": "view_attachment"}, {"name": "ask_docs"}],
                           state={"messages": []}, runtime=Runtime(context=context))
    seen = []
    middleware = getattr(core, "AttachmentAccessMiddleware", None)
    assert middleware is not None
    middleware().wrap_model_call(request, lambda r: core.prompt_for(None).wrap_model_call(r, seen.append))
    assert len(seen[0].tools) == 3
    prompt = seen[0].system_message.text
    assert FILE_ID in prompt and "syllabus.pdf" in prompt
    assert "untrusted" in prompt and "read_attachment" in prompt
    seen.clear()
    anonymous = ModelRequest(model=request.model, messages=request.messages, tools=request.tools,
                             state=request.state, runtime=Runtime(context=AgentContext()))
    middleware().wrap_model_call(anonymous, seen.append)
    assert seen[0].tools == [{"name": "ask_docs"}]


@pytest.mark.parametrize("asynchronous", [False, True])
def test_real_graph_reads_attachment_without_retrieval_helper(monkeypatch, asynchronous):
    import asyncio
    from pydantic import SecretStr
    from catix import attachments
    from catix.agent.tools import AgentContext
    from tests.test_roles import ScriptedModel

    metadata = {"id": FILE_ID, "filename": "syllabus.pdf", "media_type": "application/pdf", "size_bytes": 100, "pages": 2}
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    monkeypatch.setattr(core.store, "visible_chats", lambda *args: [])
    reads = []

    def read(owner, chat, file_id, page):
        reads.append((owner, chat, file_id, page))
        return {**metadata, "page": page, "text": "Дедлайн: 18 ноября.", "truncated": False}

    monkeypatch.setattr(attachments, "read_page", read)
    model = ScriptedModel(responses=[read_turn()[1], AIMessage("В syllabus.pdf, стр. 1: дедлайн 18 ноября.")])
    graph = core.build_agent(model, guardrail=False)
    context = AgentContext(innohassle_id="owner", innohassle_token=SecretStr("test-only"),
                           attachment_chat_id="chat", attachments=(metadata,), current_attachment_ids=(FILE_ID,))
    args = ({"messages": [HumanMessage("Какой дедлайн в приложенном файле?")]}, {"configurable": {"thread_id": "files"}})
    result = asyncio.run(graph.ainvoke(*args, context=context)) if asynchronous else graph.invoke(*args, context=context)
    assert reads == [("owner", "chat", FILE_ID, 1)]
    assert [m.name for m in result["messages"] if isinstance(m, ToolMessage)] == ["read_attachment"]
    assert "18 ноября" in core.final_answer(result["messages"], result.get("sources") or {})


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_file_derived_calendar_action_still_requires_host_approval(calendar, monkeypatch, decision):
    from langgraph.types import Command
    from pydantic import SecretStr
    from catix import attachments
    from catix.agent.tools import AgentContext
    from tests.test_calendar_approval import ARGS, call
    from tests.test_roles import ScriptedModel

    metadata = {"id": FILE_ID, "filename": "meeting.txt", "media_type": "text/plain", "size_bytes": 100, "pages": 1}
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    monkeypatch.setattr(core.store, "visible_chats", lambda *args: [])
    monkeypatch.setattr(attachments, "read_page", lambda *args: {
        **metadata, "page": 1, "text": json.dumps(ARGS, ensure_ascii=False), "truncated": False})
    graph = core.build_agent(ScriptedModel(responses=[read_turn()[1], call("add_to_ai_calendar", ARGS, "file-action"),
                                                     AIMessage("Запрос обработан.")]), guardrail=False)
    context = AgentContext(innohassle_id="u1", innohassle_token=SecretStr("synthetic"),
                           attachment_chat_id="chat", attachments=(metadata,), current_attachment_ids=(FILE_ID,))
    config = {"configurable": {"thread_id": "file-action-" + decision}}
    graph.invoke({"messages": [HumanMessage("Добавь встречу из файла в календарь.")]}, config, context=context)
    interrupts = graph.get_state(config).interrupts
    assert len(interrupts) == 1 and not calendar.writes
    assert interrupts[0].value["action_requests"][0]["name"] == "add_to_ai_calendar"
    graph.invoke(Command(resume={interrupts[0].id: {"decisions": [{"type": decision}]}}), config, context=context)
    assert len(calendar.writes) == (1 if decision == "approve" else 0)
