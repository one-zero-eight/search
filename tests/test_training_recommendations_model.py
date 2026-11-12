"""Small real-model checks for the reported date/recommendation failure; no live account I/O."""

from copy import deepcopy
from datetime import datetime

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from catix.agent import api_tools, calendar_tools, core
from catix.innohassle import mcp_server
from catix.settings import settings
from catix.agent.tools import AgentContext

DAY = "2026-11-09"
PERIOD = {"date_from": DAY, "date_to": DAY}
CONTEXT = AgentContext(innohassle_id="synthetic-owner", innohassle_token=SecretStr("synthetic-ih"),
                       sport_token=SecretStr("synthetic-sport"),
                       asked_at=datetime.fromisoformat("2026-11-08T07:20:55+03:00"))


def interval(start, end, **fields):
    return {"starts_at": f"{DAY}T{start}:00+03:00", "ends_at": f"{DAY}T{end}:00+03:00", **fields}


TRAININGS = [
    interval("13:30", "15:00", training_id=49039, name="Functional Training", place="[SC] 3rd floor", checked_in=False, can_check_in=True),
    interval("15:00", "16:30", training_id=47775, name="Functional Training", place="[SC] 3rd floor", checked_in=False, can_check_in=True),
    interval("17:00", "18:30", training_id=46975, name="Basketball", place="[SC] Big Hall", checked_in=False, can_check_in=True),
    interval("19:00", "20:30", training_id=48671, name="Karate", checked_in=False, can_check_in=False),
]


@pytest.mark.model
@pytest.mark.parametrize("question", [
    "What trainings can I sign up for tomorrow?",
    "Предложи мне тренировки на завтра.",
])
def test_generic_sport_requests_do_not_filter_trainings_by_personal_calendar(monkeypatch, question):
    import asyncio
    from fastmcp import Client
    from catix.agent import api_tools
    from catix.innohassle import mcp_server

    requests = []

    async def discover(payload):
        async with mcp_server.adapter() as root, Client(root) as client:
            return {"tools": (await client.call_tool("search_tools", payload)).data,
                    "services": (await client.call_tool("service_status", {})).data}

    def service_read(method, payload, token, credentials):
        assert method == "call_tool" and token == "synthetic-ih"
        assert credentials == {"sport_token": "synthetic-sport"}
        assert payload == {"name": "sport_get_sport_trainings", "arguments": {
            "date_from": "2026-11-09", "date_to": "2026-11-09"}}, "No personal calendar or signup for a service list"
        requests.append(deepcopy(payload))
        return {"range": ["2026-11-09", "2026-11-09"], "trainings": deepcopy(TRAININGS)}

    def request(method, payload, token=None, **credentials):
        if method == "search_tools":
            assert token is None and not credentials
            return asyncio.run(discover(payload))
        return service_read(method, payload, token, credentials)

    async def arequest(method, payload, token=None, **credentials):
        if method == "search_tools":
            assert token is None and not credentials
            return await discover(payload)
        return service_read(method, payload, token, credentials)

    monkeypatch.setattr(api_tools.mcp_client, "request_sync", request)
    monkeypatch.setattr(api_tools.mcp_client, "request", arequest)
    monkeypatch.setattr(calendar_tools, "events_between", lambda *a: pytest.fail("Generic Sport must not read AI Calendar"))
    monkeypatch.setattr(core.store, "visible_chats", lambda *a: [])
    monkeypatch.setattr(core, "tool_call_token", lambda: None)
    model = ChatOpenAI(base_url=str(settings.llm_route), api_key="not-needed", model=settings.llm_model,
                       max_tokens=2000, temperature=0, timeout=60, max_retries=0,
                       extra_body={"chat_template_kwargs": {"enable_thinking": False}})
    graph = core.build_agent(model, guardrail=False)
    config = {"configurable": {"thread_id": "generic-sport-" + str(question.isascii())}}
    result = graph.invoke({"messages": [HumanMessage(question)], "answer_alone": False}, config, context=CONTEXT)
    calls = [call for message in result["messages"] if isinstance(message, AIMessage) for call in message.tool_calls]
    assert calls and all(call["name"] in {"search_api_tools", "call_api_tool"} for call in calls)
    assert all(call["args"].get("name") == "sport_get_sport_trainings" for call in calls if call["name"] == "call_api_tool")
    assert len(requests) == 1 and not graph.get_state(config).interrupts
    answer = core.final_answer(result["messages"], {}).answer
    print({"question": question, "calls": calls, "answer": answer})
    assert "Functional Training" in answer and "13:30" in answer and "Basketball" in answer
    assert "Logic and Discrete Math" not in answer and "English for Scientific Purposes" not in answer
