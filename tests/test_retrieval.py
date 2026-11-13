from types import SimpleNamespace

import httpx
import pytest

from catix.db import pg, store, wiki
from catix.settings import settings


def hit(search, text: str):
    """A hit of `search`: a chat message (store) or a piece of the wiki."""
    if search is store:
        from datetime import datetime

        from catix.db.rows import MessageHit

        return MessageHit(ref_id=1, chat_id=1, msg_id=1, date=datetime(2026, 6, 1), edit_date=None, sender_name=None, reply_to=None,
                          text=text, link=None, chat_title="Campus", chat_official=True, chat_group="all", parent_sender=None, parent_text=None)
    return SimpleNamespace(title="Title", heading="Heading", text=text, parent_text=None)


def client(monkeypatch, payload):
    requests = []

    def respond(request):
        import json

        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": settings.embeddings_model}]})
        requests.append(json.loads(request.content))
        return httpx.Response(200, content=json.dumps(payload))

    monkeypatch.setattr(pg, "_http", httpx.Client(transport=httpx.MockTransport(respond)))
    return requests


def test_bge_queries_remain_unprefixed(monkeypatch):
    monkeypatch.setattr(settings, "embeddings_model", "bge-m3")
    monkeypatch.setattr(settings, "embeddings_query_prefix", "")
    requests = client(monkeypatch, {"data": [{"index": 0, "embedding": [1.0] * 1024}]})
    pg.embed(["пересдачи"], query=True)
    assert requests[0]["input"] == ["пересдачи"]


def test_custom_query_prefix_does_not_consume_text_limit(monkeypatch):
    monkeypatch.setattr(settings, "embeddings_query_prefix", "query: ")
    monkeypatch.setattr(settings, "embeddings_max_chars", 5)
    requests = client(monkeypatch, {"data": [{"index": 0, "embedding": [1.0] * 1024}]})
    pg.embed(["abcdef"], query=True)
    pg.embed(["abcdef"])
    assert requests[0]["input"] == ["query: abcde"] and requests[1]["input"] == ["abcde"]


@pytest.mark.parametrize("data", [[], [{"index": 1, "embedding": [1.0] * 1024}],
    [{"index": 0, "embedding": [1.0] * 1024}] * 2, [{"index": 0, "embedding": [1.0]}],
    [{"index": 0, "embedding": [0.0] * 1024}], [{"index": 0, "embedding": [float("nan")] * 1024}]])
def test_invalid_embedding_response_is_rejected(monkeypatch, data):
    client(monkeypatch, {"data": data})
    with pytest.raises(ValueError):
        pg.embed(["document"])


def test_vectors_are_restored_to_input_order(monkeypatch):
    client(monkeypatch, {"data": [{"index": 1, "embedding": [2.0] * 1024}, {"index": 0, "embedding": [1.0] * 1024}]})
    assert pg.embed(["first", "second"]) == [[1.0] * 1024, [2.0] * 1024]


@pytest.mark.parametrize("results", [[], [{"index": 0, "relevance_score": -1.0}],
    [{"index": 0, "relevance_score": 1.0}] * 2,
    [{"index": 0, "relevance_score": 1.0}, {"index": 2, "relevance_score": 1.0}]])
def test_partial_reranker_response_is_not_treated_as_zero_scores(monkeypatch, results):
    client(monkeypatch, {"results": results})
    with pytest.raises(ValueError):
        pg.rerank("question", ["first", "second"])


def test_reranker_restores_order(monkeypatch):
    client(monkeypatch, {"results": [{"index": 1, "relevance_score": 3.0}, {"index": 0, "relevance_score": -4.0}]})
    assert pg.rerank("question", ["first", "second"]) == [-4.0, 3.0]


def test_reranker_rejects_nonfinite_scores(monkeypatch):
    client(monkeypatch, {"results": [{"index": 0, "relevance_score": float("inf")}]})
    with pytest.raises(ValueError, match="non-finite"):
        pg.rerank("question", ["document"])


def test_embedding_checks_the_actual_server_model(monkeypatch):
    monkeypatch.setattr(settings, "embeddings_model", "another-model")
    paths = []

    def respond(request):
        paths.append(request.url.path)
        return httpx.Response(200, json={"data": [{"id": "bge-m3"}]})

    monkeypatch.setattr(pg, "_http", httpx.Client(transport=httpx.MockTransport(respond)))
    with pytest.raises(ValueError, match="not served"):
        pg.embed(["document"])
    assert paths == ["/v1/models"]


@pytest.mark.parametrize("search", [store, wiki])
def test_single_irrelevant_hit_still_passes_through_reranker(monkeypatch, search):
    monkeypatch.setattr(settings, "rerank_min_score", -3.0)
    monkeypatch.setattr(pg, "rerank", lambda query, documents: [-10.0])
    assert search._rerank(["question"], [hit(search, "irrelevant")], 10) == []


@pytest.mark.parametrize("search", [store, wiki])
def test_reranking_keeps_tail_and_fourth_query(monkeypatch, search):
    monkeypatch.setattr(settings, "rerank_queries", 9)
    monkeypatch.setattr(settings, "rerank_max_chars", 4000)
    monkeypatch.setattr(settings, "rerank_min_score", -3.0)
    seen = []

    def rerank(query, documents):
        seen.append((query, documents))
        return [2.0 if query == "fourth" and "answer at the end" in document else -10.0 for document in documents]

    monkeypatch.setattr(pg, "rerank", rerank)
    found = hit(search, "prefix " * 180 + "answer at the end")
    assert [h.text for h in search._rerank(["first", "second", "third", "fourth"], [found], 10)] == [found.text]
    assert len(seen) == 4


def test_each_message_keeps_how_well_two_angles_agree_it_is_about_the_question(monkeypatch):
    """A model's 'администратор университет иннополис' gave 3.09 to a notice on housing contracts, the rest -2.31 at most:
    the cutoff keeps the best, `relevance` is the second best. With one query it is that query's score."""
    scores = {"как получить права администратора": -2.31, "администратор университет иннополис": 3.09, "права на ПК": -6.0}
    monkeypatch.setattr(settings, "rerank_min_score", -3.0)
    monkeypatch.setattr(pg, "rerank", lambda query, documents: [scores[query]])
    notice = hit(store, "договор на услуги размещения в АНО ВО «Университет Иннополис»")
    assert [h.relevance for h in store._rerank(list(scores), [notice], 5)] == [-2.31]
    assert [h.relevance for h in store._rerank(["администратор университет иннополис"], [notice], 5)] == [3.09]


def test_each_wiki_piece_keeps_how_well_two_angles_agree_it_is_about_the_question(monkeypatch):
    """As for the chats: the cutoff keeps the best score, `relevance` is the second best (a misspelt name found the list of
    teachers at -3.24 at best: nothing about the question)."""
    scores = {"кто такой Лисоввкий": -3.24, "Лисоввкий преподаватель": -1.0, "Лисоввкий": -5.0}
    monkeypatch.setattr(settings, "rerank_min_score", -3.0)
    monkeypatch.setattr(pg, "rerank", lambda query, documents: [scores[query]])
    piece = hit(wiki, "| Мелехова Анна Леонидовна | Доцент |")
    assert [h.relevance for h in wiki._rerank(list(scores), [piece], 5)] == [-3.24]


def test_empty_fusion_and_zero_limit():
    assert store._combine([], 10) == []
    assert store._combine([{1: 1.0}], 0) == []
    assert store.search("exam", limit=0) == []
    assert wiki.search("exam", limit=0) == []


@pytest.mark.parametrize("search", [store, wiki])
def test_reranker_failure_keeps_hybrid_ranking(monkeypatch, search):
    def unavailable(*args):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(pg, "rerank", unavailable)
    hits = [hit(search, "first"), hit(search, "second")]
    assert search._rerank(["question"], hits, 1) == hits[:1]
