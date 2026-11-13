"""Real Sage text/vision on a synthetic poster; storage is isolated, external services disabled."""
import io
import json
import uuid

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from PIL import Image, ImageDraw, ImageFont
from pydantic import SecretStr

from catix import attachments
from catix.agent import api_tools, core, guardrail, tracing
from catix.agent.tools import AgentContext
from catix.settings import settings

pytestmark = pytest.mark.model


def test_short_event_request_reads_image_with_real_model(monkeypatch):
    question = "Создай ивент"
    verdict = guardrail._screen_chain().invoke({"text": question, "history": "[]"})
    assert verdict.category == "ok", "check the classifier, not its fail-open wrapper"
    monkeypatch.setattr(guardrail, "screen", lambda *args, **kwargs: guardrail.Verdict(category=verdict.category))
    monkeypatch.setattr(core.store, "visible_chats", lambda *args: [])
    monkeypatch.setattr(settings, "agent_plan_thinking", False)
    monkeypatch.setattr(settings, "agent_max_model_calls", 5)

    image = Image.new("RGB", (1000, 350), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("/usr/share/fonts/liberation/LiberationSans-Regular.ttf", 38)
    for y, text in [(40, "Встреча студенческой команды"), (130, "Аудитория 512"), (220, "Начало: 17:35")]:
        draw.text((30, y), text, fill="black", font=font)
    output = io.BytesIO()
    image.save(output, format="PNG")
    file_id = str(uuid.uuid4())
    info = {"id": file_id, "filename": "image.png", "media_type": "image/png", "size_bytes": len(output.getvalue()), "pages": 1}
    reads = []

    def image_page(owner, chat, attachment_id, page):
        assert (owner, chat, attachment_id, page) == ("synthetic-owner", "synthetic-chat", file_id, 1)
        reads.append(attachment_id)
        return output.getvalue()

    monkeypatch.setattr(attachments, "image_page", image_page)

    def no_service(*args, **kwargs):
        return {"error": "External services are disabled in this synthetic image test. No action was performed."}

    async def no_async_service(*args, **kwargs):
        return no_service(*args, **kwargs)

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", no_service)
    monkeypatch.setattr(api_tools.mcp_client, "request", no_async_service)
    context = AgentContext(innohassle_id="synthetic-owner", innohassle_token=SecretStr("synthetic-not-a-real-token"),
                           attachment_chat_id="synthetic-chat", attachments=(info,), current_attachment_ids=(file_id,))
    thread = "test-image-" + uuid.uuid4().hex
    with tracing.private(), tracing.question(thread, "synthetic-owner", question) as traced:
        graph = core.build_agent()
        result = graph.invoke({"messages": [HumanMessage(question)]}, tracing.run_config(thread), context=context)
        answer = core.final_answer(result["messages"], result.get("sources") or {}).answer
        traced.answer(answer)
    tracing.flush()
    calls = [call for message in result["messages"] if isinstance(message, AIMessage) for call in message.tool_calls]
    assert calls and calls[0]["name"] == "view_attachment"
    assert reads == [file_id]
    visual = [json.loads(message.text) for message in result["messages"]
              if isinstance(message, ToolMessage) and message.name == "view_attachment"]
    assert len(visual) == 1 and visual[0].get("visual") is True, visual
    assert "512" in visual[0]["text"] and "17:35" in visual[0]["text"], visual
    assert "512" in answer and "17:35" in answer, answer
    print(json.dumps({"trace_id": traced.trace_id, "span_id": traced.id, "answer": answer}, ensure_ascii=False))
