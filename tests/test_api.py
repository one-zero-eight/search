"""The HTTP API (api/): the search service's paths answered by cAtIx. The wiki and the agent are replaced, the token is faked."""

import asyncio
import json
import time
from datetime import datetime, timezone
from types import SimpleNamespace

import httpx

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command
from pydantic import SecretStr

from catix.api import ask, chats, search, state
from catix.api.app import app
from catix.api.schemas import AskAction, AskApproval, AskChat, AskChatHistory, AskDecision, AskResponses
from catix.db.wiki import WikiHit
from catix.innohassle import token

AUTH = {"Authorization": "Bearer good"}


def hit(path: str, title: str, resource: str, trust: str = "wiki", relevance: float | None = 0.9) -> WikiHit:
    return WikiHit(id=1, path=path, seq=0, heading="", clause="", sha="", text="text of " + title, cites=[], title=title, type="page",
                   trust=trust, audience=[], resource=resource, status=None, review=None, source_warning=None, stale_after=None,
                   issued=None, relevance=relevance)


class FakeChats:
    """api/chats.py in memory: these tests run without a database (tests/test_api_chats.py tries the real one)."""

    thread_of = staticmethod(chats.thread_of)

    def __init__(self):
        self.chats: dict[str, dict] = {}  # chat_id -> owner, title, checkpoint, updated
        self.answers: list[dict] = []  # response, span_id, feedback, comment

    def start(self, innohassle_id: str, question: str) -> str:
        chat_id = state.new_id()
        self.chats[chat_id] = {"owner": innohassle_id, "title": question, "title_by": "question", "checkpoint": None,
                               "updated": datetime.now(timezone.utc)}
        return chat_id

    def needs_title(self, chat_id: str) -> bool:
        return self.chats.get(chat_id, {}).get("title_by") == "question"

    def rename(self, chat_id: str, innohassle_id: str, title: str) -> AskChat | None:
        if self.owner(chat_id) != innohassle_id:
            return None
        self.chats[chat_id].update(title=title.strip(), title_by="user")
        return self._chat(chat_id)

    def delete(self, chat_id: str, innohassle_id: str) -> bool:
        if self.owner(chat_id) != innohassle_id:
            return False
        del self.chats[chat_id]
        self.answers = [a for a in self.answers if a["response"].chat_id != chat_id]
        return True

    def owner(self, chat_id: str) -> str | None:
        return self.chats.get(chat_id, {}).get("owner")

    def checkpoint(self, chat_id: str) -> str | None:
        return self.chats.get(chat_id, {}).get("checkpoint")

    def save_answer(self, response: AskResponses, span_id: str | None, checkpoint: str | None, title: str | None = None) -> None:
        self.answers.append({"response": response, "span_id": span_id, "feedback": None, "comment": None})
        chat = self.chats[response.chat_id]
        chat.update(checkpoint=checkpoint, updated=datetime.now(timezone.utc), waiting=None)
        if title and chat["title_by"] == "question":
            chat.update(title=title, title_by="model")

    def save_waiting(self, response: AskResponses, checkpoint: str, interrupts: list[dict]) -> None:
        self.chats[response.chat_id].update(waiting=(checkpoint, interrupts, response), updated=datetime.now(timezone.utc))

    def waiting(self, chat_id: str):
        return self.chats.get(chat_id, {}).get("waiting")

    def take_waiting(self, chat_id: str, checkpoint: str) -> bool:
        found = self.waiting(chat_id)
        if found is None or found[0] != checkpoint:
            return False
        self.chats[chat_id]["waiting"] = None
        return True

    def _chat(self, chat_id: str) -> AskChat:
        chat = self.chats[chat_id]
        return AskChat(chat_id=chat_id, title=chat["title"], created_at=chat["updated"], updated_at=chat["updated"])

    def of_user(self, innohassle_id: str) -> list[AskChat]:
        answered = {a["response"].chat_id for a in self.answers}
        mine = [c for c, chat in self.chats.items() if chat["owner"] == innohassle_id and (c in answered or chat.get("waiting"))]
        return [self._chat(c) for c in sorted(mine, key=lambda c: self.chats[c]["updated"], reverse=True)]

    def history(self, chat_id: str, innohassle_id: str) -> AskChatHistory | None:
        if self.owner(chat_id) != innohassle_id:
            return None
        answers = [a["response"].model_copy(update={"messages": [], "feedback": a["feedback"], "feedback_comment": a["comment"]})
                   for a in self.answers if a["response"].chat_id == chat_id]
        found = self.waiting(chat_id)
        return AskChatHistory(**self._chat(chat_id).model_dump(), answers=answers, waiting=found[2] if found else None)

    def _answer(self, ask_query_id: str) -> dict | None:
        return next((a for a in self.answers if a["response"].ask_query_id == ask_query_id), None)

    def asked(self, ask_query_id: str) -> tuple[str, str] | None:
        answer = self._answer(ask_query_id)
        return None if answer is None else (self.chats[answer["response"].chat_id]["owner"], answer["span_id"])

    def vote(self, ask_query_id: str, feedback: str, comment: str | None) -> None:
        self._answer(ask_query_id).update(feedback=feedback, comment=comment)  # type: ignore[union-attr]


@pytest.fixture(autouse=True)
def kept(monkeypatch) -> FakeChats:
    fake = FakeChats()
    monkeypatch.setattr(ask, "chats", fake)
    monkeypatch.setattr(ask.titles, "name", lambda question: f"Тема: {question}")  # (the model is not asked)
    return fake


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(token, "claims", lambda t: {"uid": "u1", "email": "a@innopolis.university", "telegram_id": 7} if t == "good" else None)
    return TestClient(app)  # (not entered: the app's start, which opens the agent's memory in Postgres, does not run)


def answering(answer="answer", span_id=None, checkpoint="cp-1"):
    """A fake of ask._run: the agent answers `answer` (with `{query}` in it), its trace is `span_id`."""

    async def _run(query, chat_id, user, events=None, decision=None):
        return answer.format(query=query), [], [{"role": "user", "content": query}], span_id, checkpoint

    return _run


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


def test_page_by_url_gives_the_text_of_the_page(client, monkeypatch):
    pieces = [hit("/raw/sites/university/team-rector.md", "Ректор", "https://innopolis.university/team-rector/")] * 2
    monkeypatch.setattr(search.wiki_store, "page_of_resource", lambda url: pieces if url == pieces[0].resource else [])
    found = client.get("/search/page", params={"url": pieces[0].resource}, headers=AUTH).json()
    assert found["title"] == "Ректор" and found["text"] == "text of Ректор\n\ntext of Ректор"
    assert client.get("/search/page", params={"url": "https://x.example/"}, headers=AUTH).status_code == 404


def test_a_table_cut_out_of_a_page_is_text():
    cut = "| a | b |\n\n| --- | --- |\n\n| Гасников | Ректор |"
    assert search.table_as_text(cut).split() == ["a", "·", "b", "Гасников", "·", "Ректор"]


def test_page_pieces_keep_a_table_together():
    pieces = ["text", "| a | b |\n\n### Title\n\n| - | - |", "| 1 | 2 |\n\n| 3 | 4 |", "end"]
    assert search.join_pieces(pieces) == "text\n\n| a | b |\n| - | - |\n| 1 | 2 |\n| 3 | 4 |\n\nend"


def test_ask_keeps_a_chat_for_its_owner(client, monkeypatch, kept):
    monkeypatch.setattr(ask, "_run", answering("answer to {query}"))
    first = client.post("/ask/", json={"query": "hi"}, headers=AUTH).json()
    assert first["answer"] == "answer to hi" and first["chat_id"] and first["messages"]
    assert kept.chats[first["chat_id"]]["title"] == "Тема: hi" and kept.checkpoint(first["chat_id"]) == "cp-1"
    again = client.post("/ask/", json={"query": "more", "chat_id": first["chat_id"]}, headers=AUTH).json()
    assert again["chat_id"] == first["chat_id"]
    assert [a["response"].answer for a in kept.answers] == ["answer to hi", "answer to more"]

    kept.chats[first["chat_id"]]["owner"] = "somebody else"
    assert client.post("/ask/", json={"query": "x", "chat_id": first["chat_id"]}, headers=AUTH).status_code == 404
    unknown = client.post("/ask/", json={"query": "x", "chat_id": "0" * 24}, headers=AUTH).json()
    assert unknown["chat_id"] != "0" * 24  # an unknown chat starts a new one


def test_the_user_comes_back_to_a_chat(client, monkeypatch, kept):
    monkeypatch.setattr(ask, "_run", answering("answer to {query}", span_id="span-1"))
    monkeypatch.setattr(ask.tracing, "score_feedback", lambda *args: None)
    first = client.post("/ask/", json={"query": "first"}, headers=AUTH).json()
    client.post("/ask/", json={"query": "second", "chat_id": first["chat_id"]}, headers=AUTH)
    other = client.post("/ask/", json={"query": "other"}, headers=AUTH).json()
    client.post(f"/ask/{first['ask_query_id']}/feedback", params={"feedback": "like"}, json={"comment": "good"}, headers=AUTH)

    listed = client.get("/ask/chats", headers=AUTH).json()
    assert [(c["chat_id"], c["title"]) for c in listed] == [(other["chat_id"], "Тема: other"), (first["chat_id"], "Тема: first")]
    history = client.get(f"/ask/chats/{first['chat_id']}", headers=AUTH).json()
    assert history["title"] == "Тема: first"
    assert [(a["query"], a["answer"], a["feedback"], a["feedback_comment"]) for a in history["answers"]] == [
        ("first", "answer to first", "like", "good"),
        ("second", "answer to second", None, None),
    ]
    assert all(a["messages"] == [] and a["chat_id"] == first["chat_id"] for a in history["answers"])

    kept.start("somebody else", "theirs")
    assert len(client.get("/ask/chats", headers=AUTH).json()) == 2  # nor a chat without an answer, nor another's
    kept.chats[first["chat_id"]]["owner"] = "somebody else"
    assert client.get(f"/ask/chats/{first['chat_id']}", headers=AUTH).status_code == 404
    assert client.get("/ask/chats/nope", headers=AUTH).status_code == 404
    assert client.get("/ask/chats", headers={"Authorization": "Bearer bad"}).status_code == 401


@pytest.mark.parametrize("path", ["/ask/", "/ask/stream"])
@pytest.mark.parametrize("query", ["", "   \n"])
def test_ask_needs_a_question(client, path, query):
    assert client.post(path, json={"query": query}, headers=AUTH).status_code == 422


def test_feedback_on_an_answer_annotates_its_trace(client, monkeypatch, kept):
    votes = []
    monkeypatch.setattr(ask, "_run", answering(span_id="span-1"))
    monkeypatch.setattr(
        ask.tracing, "score_feedback", lambda span_id, voter, good, comment=None: votes.append((span_id, voter, good, comment))
    )
    ask_id = client.post("/ask/", json={"query": "hi"}, headers=AUTH).json()["ask_query_id"]
    url = f"/ask/{ask_id}/feedback"
    assert client.post(url, params={"feedback": "dislike"}, headers=AUTH).json()["status"] == "success"
    assert client.post(url, params={"feedback": "like"}, headers=AUTH).status_code == 200  # the user changes their mind
    # then says what they liked: the same vote again, with the comment
    assert client.post(url, params={"feedback": "like"}, json={"comment": " Clear and short \n"}, headers=AUTH).status_code == 200
    assert client.post(url, params={"feedback": "like"}, json={"comment": "  "}, headers=AUTH).status_code == 200  # blank is none
    assert votes == [
        ("span-1", "api:u1", False, None),
        ("span-1", "api:u1", True, None),
        ("span-1", "api:u1", True, "Clear and short"),
        ("span-1", "api:u1", True, None),
    ]
    assert client.post(url, params={"feedback": "meh"}, headers=AUTH).status_code == 422
    too_long = {"comment": "x" * (ask.COMMENT_MAX + 1)}
    assert client.post(url, params={"feedback": "like"}, json=too_long, headers=AUTH).status_code == 422
    assert client.post("/ask/nope/feedback", params={"feedback": "like"}, headers=AUTH).status_code == 404

    assert kept.answers[0]["feedback"] == "like" and kept.answers[0]["comment"] is None  # the last vote, for the history

    kept.chats[kept.answers[0]["response"].chat_id]["owner"] = "somebody else"
    assert client.post(url, params={"feedback": "like"}, headers=AUTH).status_code == 404
    assert len(votes) == 4


def test_an_answer_without_a_trace_has_no_feedback(client, monkeypatch):
    monkeypatch.setattr(ask, "_run", answering(span_id=None))  # tracing is off
    assert client.post("/ask/", json={"query": "hi"}, headers=AUTH).json()["ask_query_id"] is None


def test_feedback_that_phoenix_does_not_take_is_a_502(client, monkeypatch, kept):
    def score_feedback(span_id, voter, good, comment=None):
        raise RuntimeError("phoenix is down")

    monkeypatch.setattr(ask.tracing, "score_feedback", score_feedback)
    monkeypatch.setattr(ask, "_run", answering(span_id="span-1"))
    ask_id = client.post("/ask/", json={"query": "hi"}, headers=AUTH).json()["ask_query_id"]
    assert client.post(f"/ask/{ask_id}/feedback", params={"feedback": "like"}, headers=AUTH).status_code == 502
    assert kept.answers[0]["feedback"] is None


def test_ask_failure_is_a_502(client, monkeypatch):
    async def run(query, chat_id, user):
        raise RuntimeError("model is down")

    monkeypatch.setattr(ask, "run", run)
    assert client.post("/ask/", json={"query": "x"}, headers=AUTH).status_code == 502


def test_ask_stream_sends_the_work_and_the_final_answer(client, monkeypatch, kept):
    async def _run(query, chat_id, user, events, decision=None):
        await events.put(("status", {"text": "checking"}))
        await events.put(("answer", {"text": "ans"}))
        return "answer", [], [], "span-1", "cp-1"

    monkeypatch.setattr(ask, "_run", _run)
    response = client.post("/ask/stream", json={"query": "hi"}, headers=AUTH)
    assert response.headers["content-type"].startswith("text/event-stream")
    names = [line.removeprefix("event: ") for line in response.text.splitlines() if line.startswith("event: ")]
    assert names == ["status", "answer", "done"]
    assert '"answer": "answer"' in response.text
    done = json.loads(response.text.split("event: done\ndata: ")[1])
    assert kept.asked(done["ask_query_id"]) == ("u1", "span-1")  # the 👍/👎 on it annotates its trace
    assert kept.checkpoint(done["chat_id"]) == "cp-1"  # kept with the answer: the next question goes on from it


def test_ask_stream_runs_through_the_queue(client, monkeypatch):
    class FakeAgent:
        checkpointer = SimpleNamespace(adelete_thread=lambda thread_id: _state())

        def aget_state(self, config):
            return _state()

    monkeypatch.setattr(ask, "agent", FakeAgent)
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
    return type("S", (), {"values": {}, "config": {"configurable": {"checkpoint_id": "cp"}}})()


def test_ask_stream_failure_is_an_error_event(client, monkeypatch):
    async def run(query, chat_id, user, events, decision=None):
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
    assert client.get("/moodle/courses").status_code == 404
    assert client.post("/moodle/parse", headers=AUTH).status_code == 410


# --- one client's questions in a line, and cancelling ---


def two_users(monkeypatch):
    claims = {"good": {"uid": "u1", "email": "a@innopolis.university", "telegram_id": 7},
              "other": {"uid": "u2", "email": "b@innopolis.university", "telegram_id": 8}}
    monkeypatch.setattr(token, "claims", lambda t: claims.get(t))
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def test_a_clients_questions_are_answered_one_at_a_time_in_order(monkeypatch):
    log = []

    async def fake(query, chat_id, user, events=None, decision=None):
        log.append(("start", query))
        await asyncio.sleep(0.05)
        log.append(("end", query))
        return f"a:{query}", [], [], None, "cp"

    monkeypatch.setattr(ask, "_run", fake)

    async def go():
        async with two_users(monkeypatch) as c:
            async def post(q, after, who="good"):
                # One after another: a question takes its place in the line once its chat is looked up in the database,
                # so of the ones that come at the same instant either may be first.
                await asyncio.sleep(after)
                return await c.post("/ask/", json={"query": q}, headers={"Authorization": f"Bearer {who}"})

            return await asyncio.gather(post("1", 0), post("2", 0.01), post("3", 0.02), post("x", 0.01, "other"))

    responses = asyncio.run(go())
    assert [r.status_code for r in responses] == [200] * 4
    mine = [e for e in log if e[1] != "x"]
    assert mine == [("start", "1"), ("end", "1"), ("start", "2"), ("end", "2"), ("start", "3"), ("end", "3")]
    assert log.index(("start", "x")) < log.index(("end", "1"))  # another client does not wait for them
    assert not ask._gates and not ask.pending


def test_cancel_stops_the_running_and_the_waiting_questions_of_a_chat(monkeypatch, kept):
    started = []

    async def fake(query, chat_id, user, events=None, decision=None):
        started.append(query)
        await asyncio.Event().wait()

    monkeypatch.setattr(ask, "_run", fake)
    kept.chats["c1"] = {"owner": "u1", "title": "1", "checkpoint": None}

    async def go():
        async with two_users(monkeypatch) as c:
            h = {"Authorization": "Bearer good"}
            # Authentication/chat lookup runs concurrently; task creation order alone does not choose the gate winner.
            asks = [asyncio.create_task(c.post("/ask/", json={"query": "1", "chat_id": "c1"}, headers=h))]
            while not started:
                await asyncio.sleep(0.01)
            asks.append(asyncio.create_task(c.post("/ask/", json={"query": "2", "chat_id": "c1"}, headers=h)))
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
    assert not ask._gates and not ask.pending and not kept.answers


def test_a_deleted_chat_goes_with_its_answers_and_the_agents_memory(monkeypatch, kept):
    """A question of the chat still being answered is cancelled first; one sent with the chat's id afterwards starts a new chat."""
    started, deleted = [], []

    async def fake(query, chat_id, user, events=None, decision=None):
        started.append(query)
        if query == "hang":
            await asyncio.Event().wait()
        return f"a:{query}", [], [], None, "cp"

    async def delete_thread(thread_id):
        deleted.append(thread_id)

    monkeypatch.setattr(ask, "_run", fake)
    monkeypatch.setattr(ask, "agent", lambda: SimpleNamespace(checkpointer=SimpleNamespace(adelete_thread=delete_thread)))

    async def go():
        async with two_users(monkeypatch) as c:
            h = {"Authorization": "Bearer good"}
            chat_id = (await c.post("/ask/", json={"query": "first"}, headers=h)).json()["chat_id"]
            other = (await c.post("/ask/", json={"query": "other"}, headers=h)).json()["chat_id"]
            hanging = asyncio.create_task(c.post("/ask/", json={"query": "hang", "chat_id": chat_id}, headers=h))
            while "hang" not in started:
                await asyncio.sleep(0.01)
            stranger = await c.delete(f"/ask/chats/{chat_id}", headers={"Authorization": "Bearer other"})
            deleting = await c.delete(f"/ask/chats/{chat_id}", headers=h)
            again = await c.delete(f"/ask/chats/{chat_id}", headers=h)
            listed = (await c.get("/ask/chats", headers=h)).json()
            history = await c.get(f"/ask/chats/{chat_id}", headers=h)
            after = (await c.post("/ask/", json={"query": "after", "chat_id": chat_id}, headers=h)).json()
            return chat_id, other, stranger, deleting, again, await hanging, listed, history, after

    chat_id, other, stranger, deleting, again, hanging, listed, history, after = asyncio.run(go())
    assert stranger.status_code == 404
    assert deleting.status_code == 200 and deleting.json() == {"status": "success", "chat_id": chat_id}
    assert hanging.status_code == 409  # cancelled before the chat went
    assert again.status_code == 404 and history.status_code == 404
    assert deleted == [f"api:{chat_id}"]
    assert [c["chat_id"] for c in listed] == [other]  # the other chat stays
    assert after["chat_id"] not in (chat_id, other)  # a new chat
    assert not ask._gates and not ask.pending
    assert {a["response"].chat_id for a in kept.answers} == {other, after["chat_id"]}


def test_a_question_goes_on_from_the_last_answer_of_its_chat(monkeypatch, kept):
    """A question cancelled (or failed, or cut by a restart) halfway leaves its messages in the thread: the next one goes on
    from the checkpoint kept with the chat's last answer, and before the first answer the thread is cleared."""
    deleted, configs = [], []
    hang = {"on": False}

    class FakeAgent:
        async def _delete(thread_id):
            deleted.append(thread_id)

        checkpointer = SimpleNamespace(adelete_thread=_delete)

        async def aget_state(self, config):
            return SimpleNamespace(values={}, config={"configurable": {"checkpoint_id": f"after:{config['configurable']['thread_id']}"}})

        async def ainvoke(self, inputs, config, context):
            configs.append(dict(config["configurable"]))
            if hang["on"]:
                await asyncio.Event().wait()
            return {"messages": [HumanMessage(inputs["messages"][0]["content"]), AIMessage("answer")], "sources": {}}

    monkeypatch.setattr(ask, "agent", lambda: FakeAgent())
    monkeypatch.setattr(ask.groups, "scoped_chat_ids", lambda key, telegram_id: set())
    monkeypatch.setattr(ask.groups, "effective_group", lambda key, telegram_id: ask.groups.ALL)
    user = ask.UserTokenData(innohassle_id="u1", email="a@innopolis.university", telegram_id=7)
    chat_id = kept.start("u1", "q")

    async def cancel_after_start():
        task = asyncio.create_task(ask.run("q", chat_id, user))
        while not configs:
            await asyncio.sleep(0.01)
        for pending in list(ask.pending[chat_id]):
            pending.cancel()
        with pytest.raises(ask.AskCancelled):
            await task

    hang["on"] = True
    asyncio.run(cancel_after_start())
    assert deleted == [f"api:{chat_id}"] and "checkpoint_id" not in configs[0]  # no answer yet: from nothing
    assert not kept.answers and kept.checkpoint(chat_id) is None

    hang["on"], configs[:] = False, []
    assert asyncio.run(ask.run("q", chat_id, user)).answer == "answer"
    assert kept.checkpoint(chat_id) == f"after:api:{chat_id}"  # the thread's latest checkpoint, kept with the answer

    hang["on"], configs[:], deleted[:] = True, [], []
    asyncio.run(cancel_after_start())
    hang["on"], configs[:] = False, []
    asyncio.run(ask.run("q", chat_id, user))
    assert configs[0]["checkpoint_id"] == f"after:api:{chat_id}" and not deleted  # past the cancelled one
    assert len(kept.answers) == 2


# --- the name of a chat ---


def test_the_model_names_a_chat_by_its_first_question_and_the_user_renames_it(client, monkeypatch, kept):
    asked = []

    def name(question):
        asked.append(question)
        return f"Тема: {question}"

    monkeypatch.setattr(ask, "_run", answering())
    monkeypatch.setattr(ask.titles, "name", name)
    chat_id = client.post("/ask/", json={"query": "когда пересдача"}, headers=AUTH).json()["chat_id"]
    client.post("/ask/", json={"query": "а по физике", "chat_id": chat_id}, headers=AUTH)
    assert asked == ["когда пересдача"] and kept.chats[chat_id]["title"] == "Тема: когда пересдача"  # named once

    url = f"/ask/chats/{chat_id}"
    renamed = client.patch(url, json={"title": "  Пересдачи  "}, headers=AUTH)
    assert renamed.status_code == 200 and renamed.json()["title"] == "Пересдачи"
    assert client.get("/ask/chats", headers=AUTH).json()[0]["title"] == "Пересдачи"
    assert client.patch(url, json={"title": " "}, headers=AUTH).status_code == 422
    assert client.patch(url, json={"title": "x" * (chats.TITLE_MAX + 1)}, headers=AUTH).status_code == 422
    assert client.patch("/ask/chats/nope", json={"title": "x"}, headers=AUTH).status_code == 404
    kept.chats[chat_id]["owner"] = "somebody else"
    assert client.patch(url, json={"title": "mine"}, headers=AUTH).status_code == 404


def test_a_chat_the_model_could_not_name_keeps_its_question_and_is_named_by_the_next(client, monkeypatch, kept):
    def broken(question):
        raise RuntimeError("the model is down")

    monkeypatch.setattr(ask, "_run", answering())
    monkeypatch.setattr(ask.titles, "name", broken)
    chat_id = client.post("/ask/", json={"query": "когда пересдача"}, headers=AUTH).json()["chat_id"]
    assert kept.chats[chat_id]["title"] == "когда пересдача"  # the answer came all the same
    monkeypatch.setattr(ask.titles, "name", lambda question: f"Тема: {question}")
    client.post("/ask/", json={"query": "а по физике", "chat_id": chat_id}, headers=AUTH)
    assert kept.chats[chat_id]["title"] == "Тема: а по физике"


def test_the_answer_does_not_wait_long_for_the_name(monkeypatch, kept):
    monkeypatch.setattr(ask, "_run", answering())
    monkeypatch.setattr(ask, "TITLE_WAIT", 0.05)
    monkeypatch.setattr(ask.titles, "name", lambda question: time.sleep(0.5) or "late")
    user = ask.UserTokenData(innohassle_id="u1", email="a@innopolis.university", telegram_id=7)
    chat_id = kept.start("u1", "q")

    async def answer() -> float:
        started = time.monotonic()
        await ask.run("q", chat_id, user)
        return time.monotonic() - started

    assert asyncio.run(answer()) < 0.4 and kept.chats[chat_id]["title"] == "q"  # named by the next question


def test_a_user_name_is_never_replaced_by_the_model(client, monkeypatch, kept):
    monkeypatch.setattr(ask, "_run", answering())
    chat_id = kept.start("u1", "q")
    client.patch(f"/ask/chats/{chat_id}", json={"title": "Моё"}, headers=AUTH)
    client.post("/ask/", json={"query": "q", "chat_id": chat_id}, headers=AUTH)
    assert kept.chats[chat_id]["title"] == "Моё"


@pytest.mark.parametrize(("reply", "name"), [
    ("Пересдача по матанализу", "Пересдача по матанализу"),
    ('"Retake of Calculus."\n', "Retake of Calculus"),
    ("«Запись на спорт»\nВот название", "Запись на спорт"),
    ("Название: Общежитие", "Общежитие"),
    ("  \n", None),
])
def test_the_name_is_the_first_line_without_quotes(reply, name):
    assert ask.titles.clean(reply) == name


# --- an answer that waits for the user's decision (HumanInTheLoopMiddleware) ---

APPROVAL = AskApproval(id="cp-paused", actions=[AskAction(name="book_music_room", description="Забронировать музыкальную комнату на пт, 7 ноября, 18:00–19:00.")])


def test_an_action_waits_in_the_chat_until_the_user_decides(client, monkeypatch, kept):
    decided = []

    async def _run(query, chat_id, user, events=None, decision=None):
        if decision is None:
            return ask.Waiting("Нужно ваше подтверждение", [], None, "cp-paused", APPROVAL, [{"id": "i1", "actions": 1}])
        decided.append((query, decision.decision, decision.approval_id, user.token.get_secret_value()))
        return "Забронировано.", [], [], None, "cp-2"

    monkeypatch.setattr(ask, "_run", _run)
    first = client.post("/ask/", json={"query": "забронируй музкомнату"}, headers=AUTH).json()
    chat_id = first["chat_id"]
    assert first["approval"] == APPROVAL.model_dump() and first["ask_query_id"] is None and first["calendar_events"] == []
    assert not kept.answers, "no answer yet: the question waits"
    assert client.get("/ask/chats", headers=AUTH).json()[0]["chat_id"] == chat_id  # it is listed, to come back to it
    history = client.get(f"/ask/chats/{chat_id}", headers=AUTH).json()
    assert history["answers"] == [] and history["waiting"]["approval"]["id"] == "cp-paused"

    done = client.post(f"/ask/{chat_id}/decision", json={"decision": "approve", "approval_id": "cp-paused"}, headers=AUTH)
    assert done.status_code == 200 and done.json()["answer"] == "Забронировано." and done.json()["approval"] is None
    assert decided == [("забронируй музкомнату", "approve", "cp-paused", "good")], "the question that waited, with this request's token"
    assert client.get(f"/ask/chats/{chat_id}", headers=AUTH).json()["waiting"] is None
    assert client.post(f"/ask/{chat_id}/decision", json={"decision": "approve"}, headers=AUTH).status_code == 409
    assert client.post("/ask/nope/decision", json={"decision": "reject"}, headers=AUTH).status_code == 404
    assert client.post(f"/ask/{chat_id}/decision", json={"decision": "maybe"}, headers=AUTH).status_code == 422


def test_the_sites_sport_token_reaches_the_agent_with_the_question_and_the_decision(client, monkeypatch, kept):
    seen = []

    async def _run(query, chat_id, user, events=None, decision=None):
        seen.append(user.sport_token and user.sport_token.get_secret_value())
        if decision is None:
            return ask.Waiting("Нужно ваше подтверждение", [], None, "cp-paused", APPROVAL, [{"id": "i1", "actions": 1}])
        return "Записал.", [], [], None, "cp-2"

    monkeypatch.setattr(ask, "_run", _run)
    monkeypatch.setattr(token, "sport_email", {"sport-mine": "a@innopolis.university", "sport-other": "b@innopolis.university"}.get)
    first = client.post("/ask/", json={"query": "запиши меня на волейбол"}, headers=AUTH | {"X-Sport-Token": "sport-mine"}).json()
    client.post(f"/ask/{first['chat_id']}/decision", json={"decision": "approve"}, headers=AUTH | {"X-Sport-Token": "sport-other"})
    client.post("/ask/", json={"query": "сколько у меня часов спорта"}, headers=AUTH)
    assert seen == ["sport-mine", None, None], "only the asker's own, and only from the request it came with"


@pytest.mark.parametrize("streamed", [False, True])
@pytest.mark.parametrize("content_kind", ["text", "blocks", "empty", "whitespace"])
def test_approval_keeps_the_assistants_explanation(client, monkeypatch, kept, streamed, content_kind):
    explanation = (
        "Ваше расписание на завтра (9 ноября): занятия с 09:00 до 15:50.\n\n"
        "- **Воллейбол**, 20:00–22:30, [SC] Big Hall (15 мест свободно)\n\nЗаписать вас на неё?"
    )
    paused = SimpleNamespace(id="i1", value={"action_requests": [
        {"name": "call_api_tool", "description": "Записать вас на тренировку #46767."}
    ]})
    content = {"text": explanation, "blocks": [{"type": "text", "text": explanation}],
               "empty": "", "whitespace": " \n "}[content_kind]
    expected = explanation if content_kind in {"text", "blocks"} else ask.WAITING["Russian"].format(
        actions="- Записать вас на тренировку #46767.")

    class FakeAgent:
        paused = False

        async def _delete(thread_id):
            return None

        checkpointer = SimpleNamespace(adelete_thread=_delete)

        async def aget_state(self, config):
            return SimpleNamespace(values={}, interrupts=[paused] if self.paused else [],
                                   config={"configurable": {"checkpoint_id": "cp-paused"}})

        async def ainvoke(self, inputs, config, context):
            self.paused = True
            return {"messages": [HumanMessage("предыдущий вопрос"), AIMessage("Старый ответ: бассейн в 10:00."),
                                 HumanMessage("подбери тренировку"), AIMessage(
                content=content,
                tool_calls=[{"id": "checkin", "name": "call_api_tool", "args": {
                    "name": "sport_sport_checkin", "arguments": {"training_id": 46767},
                }}],
            )], "sources": {}}

        async def astream(self, inputs, config, context, stream_mode):
            yield "values", await self.ainvoke(inputs, config, context)

    agent = FakeAgent()
    monkeypatch.setattr(ask, "agent", lambda: agent)
    monkeypatch.setattr(ask.groups, "scoped_chat_ids", lambda key, telegram_id: set())
    monkeypatch.setattr(ask.groups, "effective_group", lambda key, telegram_id: ask.groups.ALL)
    response = client.post("/ask/stream" if streamed else "/ask/", json={"query": "подбери тренировку"}, headers=AUTH)
    assert response.status_code == 200
    if streamed:
        block = next(block for block in response.text.split("\n\n") if block.startswith("event: done\n"))
        body = json.loads(block.split("data: ", 1)[1])
    else:
        body = response.json()
    assert body["answer"] == expected
    assert body["approval"]["actions"] == paused.value["action_requests"]
    history = client.get(f"/ask/chats/{body['chat_id']}", headers=AUTH).json()
    assert history["waiting"]["answer"] == expected
    assert not kept.answers, "the explanation is not a completed action"


def test_a_decision_resumes_the_paused_checkpoint_once(monkeypatch, kept):
    calls = []
    paused = SimpleNamespace(id="i1", value={"action_requests": [{"name": "book_music_room", "description": "Забронировать музкомнату."}]})
    state_of = {"paused": False}

    class FakeAgent:
        async def _delete(thread_id):
            return None

        checkpointer = SimpleNamespace(adelete_thread=_delete)

        async def aget_state(self, config):
            now = state_of["paused"]
            return SimpleNamespace(values={}, interrupts=[paused] if now else [],
                                   config={"configurable": {"checkpoint_id": "cp-paused" if now else "cp-done"}})

        async def ainvoke(self, inputs, config, context):
            calls.append((inputs, dict(config["configurable"]), context.innohassle_token.get_secret_value()))
            resumed = isinstance(inputs, Command)
            state_of["paused"] = not resumed
            return {"messages": [HumanMessage("q"), AIMessage("Забронировано." if resumed else "")], "sources": {}}

    monkeypatch.setattr(ask, "agent", lambda: FakeAgent())
    monkeypatch.setattr(ask.groups, "scoped_chat_ids", lambda key, telegram_id: set())
    monkeypatch.setattr(ask.groups, "effective_group", lambda key, telegram_id: ask.groups.ALL)
    user = ask.UserTokenData(innohassle_id="u1", email="a@innopolis.university", telegram_id=7, token=SecretStr("tok"))
    chat_id = kept.start("u1", "забронируй музкомнату")

    waiting = asyncio.run(ask.run("забронируй музкомнату", chat_id, user))
    assert waiting.approval.actions[0].name == "book_music_room" and "- Забронировать музкомнату." in waiting.answer
    assert kept.waiting(chat_id)[0] == "cp-paused" and kept.checkpoint(chat_id) is None

    wrong = AskDecision(decision="approve", approval_id="cp-other")
    with pytest.raises(ask.NothingToDecide):
        asyncio.run(ask.run("забронируй музкомнату", chat_id, user, decision=wrong))
    answered = asyncio.run(ask.run("забронируй музкомнату", chat_id, user, decision=AskDecision(decision="approve", approval_id="cp-paused")))
    inputs, configurable, token = calls[-1]
    assert isinstance(inputs, Command) and inputs.resume == {"i1": {"decisions": [{"type": "approve"}]}}
    assert configurable["checkpoint_id"] == "cp-paused" and token == "tok"
    assert answered.answer == "Забронировано." and kept.checkpoint(chat_id) == "cp-done" and kept.waiting(chat_id) is None
    with pytest.raises(ask.NothingToDecide):  # never twice
        asyncio.run(ask.run("забронируй музкомнату", chat_id, user, decision=AskDecision(decision="approve")))
    assert sum(isinstance(c[0], Command) for c in calls) == 1


def test_a_rejection_tells_the_helper_that_nothing_was_done():
    assert ask._decisions([{"id": "i1", "actions": 2}], "reject") == {
        "i1": {"decisions": [{"type": "reject", "message": ask.DECLINED}] * 2}}
