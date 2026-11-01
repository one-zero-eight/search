"""The HTTP API (api/): the search service's paths answered by cAtIx. The wiki and the agent are replaced, the token is faked."""

import asyncio
from types import SimpleNamespace

import httpx
import asyncio

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from catix.api import ask, search, state
from catix.api.app import app
from catix.db.wiki import WikiHit
from catix.innohassle import token

AUTH = {"Authorization": "Bearer good"}


def hit(path: str, title: str, resource: str, trust: str = "wiki", relevance: float | None = 0.9) -> WikiHit:
    return WikiHit(id=1, path=path, seq=0, heading="", clause="", sha="", text="text of " + title, cites=[], title=title, type="page",
                   trust=trust, audience=[], resource=resource, status=None, review=None, source_warning=None, stale_after=None,
                   issued=None, relevance=relevance)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(token, "claims", lambda t: {"uid": "u1", "email": "a@innopolis.university", "telegram_id": 7} if t == "good" else None)
    return TestClient(app)


def test_token_is_required(client):
    assert client.get("/search/search", params={"query": "x", "response_types": "link_to_source"}).status_code == 401
    bad = client.post("/ask/", json={"query": "x"}, headers={"Authorization": "Bearer bad"})
    assert bad.status_code == 401


def test_search_cards(client, monkeypatch):
    hits = [
        hit("/raw/eduwiki/a.md", "Retake", "https://eduwiki.innopolis.university/a"),
        hit("/raw/eduwiki/a.md", "Retake", "https://eduwiki.innopolis.university/a", relevance=0.5),
        hit("/raw/sites/hotel/x.md", "Rooms", "https://hotel.innopolis.university/x"),
        hit("/raw/regulations/r.md", "Regulation", "https://example.org/r.pdf", trust="official", relevance=None),
    ]
    monkeypatch.setattr(search.wiki_store, "search", lambda query, limit: hits)
    body = client.get("/search/search", params={"query": "retake", "response_types": "link_to_source"}, headers=AUTH).json()
    assert body["searched_for"] == "retake"
    assert [(r["source"]["type"], r["source"]["display_name"]) for r in body["responses"]] == [
        ("eduwiki", "Retake"), ("hotel", "Rooms"), ("eduwiki", "Regulation")]
    assert body["responses"][0]["score"] == [0.9, 0.5]
    assert body["responses"][2]["source"]["breadcrumbs"] == ["Документы университета"]

    only_hotel = client.get("/search/search", params={"query": "q", "sources": "hotel", "response_types": "pdf"}, headers=AUTH).json()
    assert [r["source"]["type"] for r in only_hotel["responses"]] == ["hotel"]


def test_search_feedback(client, monkeypatch):
    monkeypatch.setattr(search.wiki_store, "search", lambda query, limit: [hit("/raw/eduwiki/a.md", "A", "https://e/a")])
    search_id = client.get("/search/search", params={"query": "q", "response_types": "pdf"}, headers=AUTH).json()["search_query_id"]
    url = f"/search/search/{search_id}/feedback"
    assert client.post(url, params={"response_index": 0, "feedback": "like"}, headers=AUTH).json()["status"] == "success"
    assert state.searches[search_id] == ["like"]
    assert client.post(url, params={"response_index": 5, "feedback": "like"}, headers=AUTH).status_code == 400
    assert client.post("/search/search/nope/feedback", params={"response_index": 0, "feedback": "like"}, headers=AUTH).status_code == 404


def test_ask_keeps_a_chat_for_its_owner(client, monkeypatch):
    async def run(query, chat_id, user):
        return f"answer to {query}", [], [{"role": "user", "content": query}]

    monkeypatch.setattr(ask, "run", run)
    first = client.post("/ask/", json={"query": "hi"}, headers=AUTH).json()
    assert first["answer"] == "answer to hi" and first["chat_id"] and first["messages"]
    again = client.post("/ask/", json={"query": "more", "chat_id": first["chat_id"]}, headers=AUTH).json()
    assert again["chat_id"] == first["chat_id"]

    state.chats[first["chat_id"]] = "somebody else"
    assert client.post("/ask/", json={"query": "x", "chat_id": first["chat_id"]}, headers=AUTH).status_code == 404
    unknown = client.post("/ask/", json={"query": "x", "chat_id": "0" * 24}, headers=AUTH).json()
    assert unknown["chat_id"] != "0" * 24  # a forgotten chat starts a new one


@pytest.mark.parametrize("path", ["/ask/", "/ask/stream"])
@pytest.mark.parametrize("query", ["", "   \n"])
def test_ask_needs_a_question(client, path, query):
    assert client.post(path, json={"query": query}, headers=AUTH).status_code == 422


def test_ask_failure_is_a_502(client, monkeypatch):
    async def run(query, chat_id, user):
        raise RuntimeError("model is down")

    monkeypatch.setattr(ask, "run", run)
    assert client.post("/ask/", json={"query": "x"}, headers=AUTH).status_code == 502


def test_ask_stream_sends_the_work_and_the_final_answer(client, monkeypatch):
    async def run(query, chat_id, user, events):
        await events.put(("status", {"text": "checking"}))
        await events.put(("answer", {"text": "ans"}))
        return "answer", [], []

    monkeypatch.setattr(ask, "run", run)
    response = client.post("/ask/stream", json={"query": "hi"}, headers=AUTH)
    assert response.headers["content-type"].startswith("text/event-stream")
    names = [line.removeprefix("event: ") for line in response.text.splitlines() if line.startswith("event: ")]
    assert names == ["status", "answer", "done"]
    assert '"answer": "answer"' in response.text


def test_ask_stream_runs_through_the_queue(client, monkeypatch):
    monkeypatch.setattr(ask, "agent", lambda: type("A", (), {"aget_state": lambda self, c: _state()})())
    monkeypatch.setattr(ask, "questions", ask.QuestionQueue(1))

    async def stream_agent(inputs, config, context, events):
        return {"messages": [AIMessage("a")], "sources": {}}

    monkeypatch.setattr(ask, "stream_agent", stream_agent)
    monkeypatch.setattr(ask.groups, "scoped_chat_ids", lambda *a: [])
    monkeypatch.setattr(ask.groups, "effective_group", lambda *a: ask.groups.ALL)
    response = client.post("/ask/stream", json={"query": "hi"}, headers=AUTH)
    assert "event: done" in response.text


def test_stream_agent_shows_what_the_bot_shows(monkeypatch):
    from langchain_core.messages import AIMessageChunk, ToolMessage

    from catix.agent.core import SUPERVISOR_NAME
    from catix.common.status import CHECKING, STATUS, WRITING

    model = {"langgraph_node": "model", "lc_agent_name": SUPERVISOR_NAME}

    class FakeAgent:
        async def astream(self, *args, **kwargs):
            yield "custom", {"tool": "search_chats"}
            yield "messages", (ToolMessage("report", name="ask_chats", tool_call_id="1"), {})
            yield "messages", (AIMessageChunk(content="Ответ [m1]", id="a"), model)
            yield "values", {"messages": [AIMessage("Ответ")]}

    monkeypatch.setattr(ask, "agent", lambda: FakeAgent())
    events: asyncio.Queue = asyncio.Queue()
    result = asyncio.run(ask.stream_agent({}, {}, None, events))
    sent = [events.get_nowait() for _ in range(events.qsize())]
    assert sent == [
        ("status", {"text": CHECKING}),
        ("status", {"text": STATUS["search_chats"]}),
        ("status", {"text": WRITING}),
        ("answer", {"text": "Ответ"}),
    ]
    assert result["messages"][0].text == "Ответ"


async def _state():
    return type("S", (), {"values": {}, "config": {"configurable": {}}})()


def test_ask_stream_failure_is_an_error_event(client, monkeypatch):
    async def run(query, chat_id, user, events):
        raise RuntimeError("model is down")

    monkeypatch.setattr(ask, "run", run)
    response = client.post("/ask/stream", json={"query": "x"}, headers=AUTH)
    assert "event: error" in response.text and "model is down" in response.text


def test_history_has_only_questions_and_answers():
    messages = [HumanMessage("q"), AIMessage("", tool_calls=[{"name": "ask_docs", "args": {}, "id": "1"}]), AIMessage("a")]
    assert ask._history(messages) == [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]


def test_cards_of_the_sources_found_in_this_turn():
    registry = {
        "m0": {"wiki": True, "title": "Old", "link": "https://o", "trust": "official"},
        "m1": {"wiki": True, "title": "News", "link": "https://media.innopolis.university/n", "site": True, "trust": "wiki"},
        "m2": {"message_id": 5},
    }
    cards = ask._cards(registry, before={"m0"})
    assert [c.source.display_name for c in cards] == ["News"]


def test_mocks(client):
    act = client.post("/act/", json={"query": "book a room"}, headers=AUTH).json()
    assert act["tool_calls"] == [] and act["answer"]
    assert client.get("/moodle/courses/grouped-by-semester").json() == {}
    assert client.get("/moodle/courses", headers=AUTH).json() == []
    assert client.post("/moodle/batch-courses", json={"courses": []}, headers=AUTH).status_code == 200
    assert client.post("/hotel/parse", headers=AUTH).status_code == 410


# --- one client's questions in a line, and cancelling ---


def two_users(monkeypatch):
    claims = {"good": {"uid": "u1", "email": "a@innopolis.university", "telegram_id": 7},
              "other": {"uid": "u2", "email": "b@innopolis.university", "telegram_id": 8}}
    monkeypatch.setattr(token, "claims", lambda t: claims.get(t))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def test_a_clients_questions_are_answered_one_at_a_time_in_order(monkeypatch):
    log = []

    async def fake(query, chat_id, user, events=None):
        log.append(("start", query))
        await asyncio.sleep(0.05)
        log.append(("end", query))
        return f"a:{query}", [], []

    monkeypatch.setattr(ask, "_run", fake)

    async def go():
        async with two_users(monkeypatch) as c:
            post = lambda q, who="good": c.post("/ask/", json={"query": q}, headers={"Authorization": f"Bearer {who}"})  # noqa: E731
            return await asyncio.gather(post("1"), post("2"), post("3"), post("x", "other"))

    responses = asyncio.run(go())
    assert [r.status_code for r in responses] == [200] * 4
    mine = [e for e in log if e[1] != "x"]
    assert mine == [("start", "1"), ("end", "1"), ("start", "2"), ("end", "2"), ("start", "3"), ("end", "3")]
    assert log.index(("start", "x")) < log.index(("end", "1"))  # another client does not wait for them
    assert not ask._gates and not ask.pending


def test_cancel_stops_the_running_and_the_waiting_questions_of_a_chat(monkeypatch):
    started = []

    async def fake(query, chat_id, user, events=None):
        started.append(query)
        await asyncio.Event().wait()

    monkeypatch.setattr(ask, "_run", fake)
    state.chats["c1"] = "u1"

    async def go():
        async with two_users(monkeypatch) as c:
            h = {"Authorization": "Bearer good"}
            asks = [asyncio.create_task(c.post("/ask/", json={"query": q, "chat_id": "c1"}, headers=h)) for q in ("1", "2")]
            while len(ask.pending.get("c1", ())) < 2 or not started:
                await asyncio.sleep(0.01)
            stranger = await c.post("/ask/c1/cancel", headers={"Authorization": "Bearer other"})
            cancelled = await c.post("/ask/c1/cancel", headers=h)
            return stranger, cancelled, await asyncio.gather(*asks)

    stranger, cancelled, asks = asyncio.run(go())
    assert stranger.status_code == 404
    assert cancelled.json()["cancelled"] == 2
    assert [r.status_code for r in asks] == [409, 409]
    assert started == ["1"]  # the second never got its turn
    assert not ask._gates and not ask.pending


def test_a_cancelled_question_leaves_the_thread_as_it_found_it(monkeypatch):
    deleted = []
    checkpoint = {"id": None}

    class FakeAgent:
        checkpointer = SimpleNamespace(delete_thread=deleted.append)

        async def aget_state(self, config):
            return SimpleNamespace(values={}, config={"configurable": {"checkpoint_id": checkpoint["id"]}})

        async def ainvoke(self, *args, **kwargs):
            await asyncio.Event().wait()

    monkeypatch.setattr(ask, "agent", lambda: FakeAgent())
    monkeypatch.setattr(ask.groups, "scoped_chat_ids", lambda key, telegram_id: set())
    monkeypatch.setattr(ask.groups, "effective_group", lambda key, telegram_id: ask.groups.ALL)
    user = ask.UserTokenData(innohassle_id="u1", email="a@innopolis.university", telegram_id=7)

    async def cancel_after_start(chat_id):
        task = asyncio.create_task(ask.run("q", chat_id, user))
        while chat_id not in ask.pending:
            await asyncio.sleep(0.01)
        await asyncio.sleep(0.05)
        for pending in list(ask.pending[chat_id]):
            pending.cancel()
        with pytest.raises(ask.AskCancelled):
            await task

    asyncio.run(cancel_after_start("fresh"))
    assert deleted == ["api:fresh"] and "fresh" not in state.resume_from  # no history: nothing to keep

    checkpoint["id"] = "cp-1"
    asyncio.run(cancel_after_start("old"))
    assert state.resume_from["old"] == "cp-1"  # the next question forks from the last finished one
