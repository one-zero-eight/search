"""Postgres connection pool and the embeddings client."""

import math
import threading
from collections.abc import Mapping, Sequence
from typing import Any, LiteralString, TypeVar, cast

import httpx
from pgvector.psycopg import register_vector
from psycopg import Connection
from psycopg.rows import class_row, dict_row
from psycopg_pool import ConnectionPool

from catix.agent import tracing
from catix.settings import settings

T = TypeVar("T")
Params = Sequence[Any] | Mapping[str, Any] | None

_pool: ConnectionPool | None = None
_lock = threading.Lock()
_http = httpx.Client(timeout=120, limits=httpx.Limits(max_connections=32))


def pool() -> ConnectionPool:
    global _pool
    with _lock:
        if _pool is None:
            if not settings.database_url:
                raise RuntimeError("DATABASE_URL is not set (see docker-compose.yml)")
            _pool = ConnectionPool(
                settings.database_url,
                min_size=1,
                max_size=12,
                kwargs={"row_factory": dict_row},
                configure=register_vector,
                open=False,
            )
            _pool.open(wait=True, timeout=30)
        return _pool


def close() -> None:
    """Close the pool; scripts call this before exiting so its threads stop cleanly."""
    global _pool
    with _lock:
        if _pool is not None:
            _pool.close()
            _pool = None


def connection():
    """`with pg.connection() as conn:` commits on success and rolls back on an exception."""
    return pool().connection()


# SQL passed to these helpers is written in this code (the dynamic parts are fixed fragments); every value goes
# through `params`. psycopg asks for LiteralString to enforce that, which a variable cannot show, hence the cast.
def rows(conn: Connection[Any], model: type[T], sql: str, params: Params = None) -> list[T]:
    """All rows of a query as `model` objects (a dataclass from rows.py), built from the columns by name."""
    with conn.cursor(row_factory=class_row(model)) as cur:
        return cur.execute(cast(LiteralString, sql), params).fetchall()


def row(conn: Connection[Any], model: type[T], sql: str, params: Params = None) -> T | None:
    """The first row as a `model` object, or None."""
    with conn.cursor(row_factory=class_row(model)) as cur:
        return cur.execute(cast(LiteralString, sql), params).fetchone()


def column(conn: Connection[Any], sql: str, params: Params = None) -> list[Any]:
    """The first column of every row."""
    with conn.cursor() as cur:
        return [next(iter(r.values())) for r in cur.execute(cast(LiteralString, sql), params).fetchall()]


def scalar(conn: Connection[Any], sql: str, params: Params = None) -> Any:
    """The first column of the first row, or None."""
    values = column(conn, sql, params)
    return values[0] if values else None


def connect() -> Connection:
    """A standalone connection for scripts."""
    import psycopg

    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set (see docker-compose.yml)")
    conn = psycopg.connect(settings.database_url, row_factory=dict_row)
    register_vector(conn)
    return conn


def embed(texts: list[str], *, query: bool = False, route=None, model: str | None = None) -> list[list[float]]:
    """Vectors for a batch of texts from the embeddings server, in the same order."""
    if not texts:
        return []
    endpoint = str(route or settings.embeddings_route).rstrip('/')
    model = model or settings.embeddings_model
    verify_embedder(endpoint, model)
    prefix = settings.embeddings_query_prefix
    if prefix is None:
        prefix = "Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: " if "harrier" in model.lower() else ""
    texts = [(prefix if query else "") + (text[: settings.embeddings_max_chars].strip() or " ") for text in texts]
    with tracing.span("embed", "EMBEDDING", input=texts, **{"embedding.model_name": model}):
        response = _http.post(
            f"{endpoint}/embeddings",
            json={"input": texts, "model": model},
        )
        response.raise_for_status()
    data = sorted(response.json()["data"], key=lambda item: item["index"])
    if [item["index"] for item in data] != list(range(len(texts))):
        raise ValueError("Embeddings response must contain exactly one vector per input")
    vectors = [item["embedding"] for item in data]
    if any(len(vector) != 1024 or not all(math.isfinite(value) for value in vector) or not any(vector) for vector in vectors):
        raise ValueError("Expected finite, nonzero 1024-dimensional embeddings")
    return vectors


def verify_embedder(route: str, model: str) -> None:
    response = _http.get(f"{route.rstrip('/')}/models")
    response.raise_for_status()
    models = {name for item in response.json()["data"] for name in [item["id"], *item.get("aliases", [])]}
    expected = {model, "ggml-org/bge-m3-Q8_0-GGUF"} if model == "bge-m3" else {model}
    if not expected.intersection(models):
        raise ValueError(f"Configured model {model!r} is not served by {route}: {sorted(models)}")


def rerank(query: str, documents: list[str]) -> list[float]:
    """Relevance of every document to the query from the reranker server (llama.cpp --reranking), in the same order."""
    if not documents:
        return []
    with tracing.span("rerank request", "RERANKER", input=query, **{"reranker.model_name": settings.reranker_model,
                                                                      "reranker.query": query, "documents": len(documents),
                                                                      "document_chars": sum(map(len, documents))}):
        response = _http.post(
            f"{str(settings.reranker_route).rstrip('/')}/rerank",
            json={"model": settings.reranker_model, "query": query, "documents": documents, "raw_scores": True},  # (Infinity: logits, as llama.cpp gives)
        )
        response.raise_for_status()
    results = sorted(response.json()["results"], key=lambda item: item["index"])
    if [item["index"] for item in results] != list(range(len(documents))):
        raise ValueError("Reranker response must score every document exactly once")
    scores = [item["relevance_score"] for item in results]
    if not all(math.isfinite(score) for score in scores):
        raise ValueError("Reranker returned non-finite scores")
    return scores
