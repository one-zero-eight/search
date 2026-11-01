"""The HTTP API (api/): the search service's paths answered by cAtIx. The wiki and the agent are replaced, the token is faked."""

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


def test_ask_failure_is_a_502(client, monkeypatch):
    async def run(query, chat_id, user):
        raise RuntimeError("model is down")

    monkeypatch.setattr(ask, "run", run)
    assert client.post("/ask/", json={"query": "x"}, headers=AUTH).status_code == 502


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
