"""Postgres connection pool and the embeddings client."""

import threading
from collections.abc import Mapping, Sequence
from typing import Any, LiteralString, TypeVar, cast

import httpx
from pgvector.psycopg import register_vector
from psycopg import Connection
from psycopg.rows import class_row, dict_row
from psycopg_pool import ConnectionPool

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


def embed(texts: list[str]) -> list[list[float]]:
    """Vectors for a batch of texts from the embeddings server, in the same order."""
    texts = [t[: settings.embeddings_max_chars].strip() or " " for t in texts]
    response = _http.post(
        f"{str(settings.embeddings_route).rstrip('/')}/embeddings",
        json={"input": texts, "model": settings.embeddings_model},
    )
    response.raise_for_status()
    data = sorted(response.json()["data"], key=lambda item: item["index"])
    return [item["embedding"] for item in data]
