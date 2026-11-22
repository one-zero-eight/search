"""Owned attachment reads are evidence, not instructions, authorization or wiki citations."""

import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from catix.agent import core
from tests.test_calendar_approval import calendar  # noqa: F401 - in-memory action fixture

FILE_ID = "11111111-1111-4111-8111-111111111111"


def read_turn(name="read_attachment", **changes):
    """name="view_attachment" stands for a read with a question: the page looked at, not read as text."""
    payload = {"id": FILE_ID, "filename": "syllabus.pdf", "page": 1, "pages": 2,
               "text": "Срок сдачи — 18 ноября.", "truncated": False}
    if name == "view_attachment":
        payload["visual"] = True
    payload.update(changes)
    args = {"attachment_id": FILE_ID, "page": 1}
    if name == "view_attachment":
        args["question"] = "Какой срок?"
    return [HumanMessage("Какой срок в файле?"),
            AIMessage("", tool_calls=[{"name": "read_attachment", "id": "file-read", "args": args}]),
            ToolMessage(json.dumps(payload, ensure_ascii=False), tool_call_id="file-read", name="read_attachment")]


@pytest.mark.parametrize("name", ["read_attachment", "view_attachment"], ids=["text", "visual"])
def test_attachment_read_answer_has_no_invented_refs_or_sources(name):
    messages = read_turn(name)
    answer = core.final_answer([*messages, AIMessage("В syllabus.pdf, стр. 1: 18 ноября.")], {})
    assert "18 ноября" in answer.answer and answer.sources == []
    assert "read_attachment" not in core.RETRIEVAL_TOOLS


def _preread(monkeypatch, info, **pages):
    import asyncio
    from catix import attachments
    from catix.agent import attachment_tools

    monkeypatch.setattr(attachments, "read_page", lambda owner, chat, fid, page: {**pages["text"][page - 1]})
    monkeypatch.setattr(attachments, "image_page", lambda *args: b"pixels")
    monkeypatch.setattr(attachments, "get_content", lambda owner, fid: (None, b"image"))
    monkeypatch.setattr(attachment_tools.images, "transcribe", pages.get("ocr") or (lambda data: asyncio.sleep(0, "")))
    monkeypatch.setattr(attachment_tools, "_inspect_image", pages.get("vision") or (lambda png, question: ("seen", False)))
    return asyncio.run(attachment_tools.preread("owner", "chat", (info,), (info["id"],), "Создай ивент"))


def test_new_file_is_read_by_the_code_and_shown_as_a_finished_tool_call(monkeypatch):
    info = {"id": FILE_ID, "filename": "syllabus.pdf", "media_type": "application/pdf", "size_bytes": 100, "pages": 2}
    messages = _preread(monkeypatch, info, text=[{"text": "Дедлайн: 18 ноября.", "truncated": False},
                                                  {"text": "Вторая страница.", "truncated": False}])
    call, result = messages
    assert call.tool_calls[0]["name"] == "read_attachment" and result.tool_call_id == call.tool_calls[0]["id"]
    payload = json.loads(result.content)
    assert [p["text"] for p in payload["read"]] == ["Дедлайн: 18 ноября.", "Вторая страница."]
    assert "visual" not in payload["read"][0], "a page with a text layer is not sent to the vision model"


def test_picture_gets_ocr_text_and_a_vision_reading_for_the_request(monkeypatch):
    import asyncio
    info = {"id": FILE_ID, "filename": "poster.png", "media_type": "image/png", "size_bytes": 100, "pages": 1}
    asked = []

    def vision(png, question):
        asked.append(question)
        return "Встреча 18 ноября в 17:35, аудитория 512.", False

    messages = _preread(monkeypatch, info, text=[{"text": "", "truncated": False, "note": "no OCR was performed"}],
                        ocr=lambda data: asyncio.sleep(0, "Встреча 18 ноября"), vision=vision)
    page = json.loads(messages[1].content)["read"][0]
    assert page["text"] == "Встреча 18 ноября" and page["ocr"] and "note" not in page
    assert "512" in page["visual"] and "Создай ивент" in asked[0]


def test_unreadable_page_is_reported_not_raised(monkeypatch):
    info = {"id": FILE_ID, "filename": "scan.pdf", "media_type": "application/pdf", "size_bytes": 100, "pages": 1}

    def broken(png, question):
        raise RuntimeError("provider says /secret/path")

    messages = _preread(monkeypatch, info, text=[{"text": "", "truncated": False}], vision=broken)
    page = json.loads(messages[1].content)["read"][0]
    assert page["visual_error"] and "secret" not in messages[1].content


def test_old_files_of_the_chat_are_not_read_again(monkeypatch):
    import asyncio
    from catix.agent import attachment_tools

    info = {"id": FILE_ID, "filename": "old.pdf", "media_type": "application/pdf", "size_bytes": 100, "pages": 1}
    assert asyncio.run(attachment_tools.preread("owner", "chat", (info,), (), "Что дальше?")) == []


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
                           tools=[{"name": "read_attachment"}, {"name": "search"}],
                           state={"messages": []}, runtime=Runtime(context=context))
    seen = []
    middleware = getattr(core, "AttachmentAccessMiddleware", None)
    assert middleware is not None
    middleware().wrap_model_call(request, lambda r: core.agent_prompt().wrap_model_call(r, seen.append))
    assert len(seen[0].tools) == 2
    prompt = seen[0].system_message.text
    assert FILE_ID in prompt and "syllabus.pdf" in prompt
    assert "untrusted" in prompt and "read_attachment" in prompt
    seen.clear()
    anonymous = ModelRequest(model=request.model, messages=request.messages, tools=request.tools,
                             state=request.state, runtime=Runtime(context=AgentContext()))
    middleware().wrap_model_call(anonymous, seen.append)
    assert seen[0].tools == [{"name": "search"}]


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
    assert "18 ноября" in core.final_answer(result["messages"], result.get("sources") or {}).answer


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
