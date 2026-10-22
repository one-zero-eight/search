"""Search in the wiki (the OKF bundle that `catix-wiki index` puts in the database): the same hybrid search as for chat
messages (store.py), over the pieces of the pages.

Every query is searched by words (BM25, Russian and English stemmers) and by meaning (bge-m3); the rankings are fused,
the queries combined, and the reranker, when there is one, orders the candidates against the queries. The title of the
page and the headings are part of what is searched, so "5.3. The term is ..." is found by the name of its regulation too.
"""

import logging
import re
from collections.abc import Collection
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date

from catix.db import pg
from catix.db.store import CANDIDATES, MAX_QUERIES, RERANK_QUERIES, _combine, _embed_all, _rrf, _words
from catix.settings import settings

log = logging.getLogger("catix.wiki")

TRUST = ("official", "guide", "wiki")


@dataclass
class WikiHit:
    id: int
    path: str
    seq: int
    heading: str
    clause: str
    sha: str
    text: str
    cites: list
    title: str
    type: str
    trust: str
    audience: list[str]
    resource: str | None
    status: str | None
    review: str | None
    source_warning: str | None
    stale_after: date | None
    issued: date | None
    based_on: list[dict] = field(default_factory=list)  # a guide piece: the pages it cites, with their titles and originals


def _bm25(words: str, trust: list[str]) -> list[int]:
    with pg.connection() as conn:
        return pg.column(
            conn,
            """SELECT id FROM wiki_chunks
               WHERE (search_text ||| %(q)s OR search_text::pdb.alias('search_text_en') ||| %(q)s) AND trust = ANY(%(t)s)
               ORDER BY pdb.score(id) DESC LIMIT %(n)s""",
            {"q": words, "t": trust, "n": CANDIDATES},
        )


def _vector(vector: list[float], trust: list[str]) -> list[int]:
    with pg.connection() as conn, conn.transaction():
        conn.execute("SET LOCAL hnsw.iterative_scan = relaxed_order")  # a filter by trust must not leave too few rows
        return pg.column(
            conn,
            """SELECT e.chunk_id FROM wiki_chunk_embeddings e JOIN wiki_chunks c ON c.id = e.chunk_id
               WHERE c.trust = ANY(%(t)s) ORDER BY e.embedding <=> %(v)s::vector LIMIT %(n)s""",
            {"v": vector, "t": trust, "n": CANDIDATES},
        )


HIT = """SELECT c.id, c.path, c.seq, c.heading, c.clause, c.sha, c.text, c.cites, p.title, p.type, p.trust, p.audience, p.resource,
                p.status, p.review, p.source_warning, p.stale_after, p.issued
         FROM wiki_chunks c JOIN wiki_pages p ON p.path = c.path"""


def _hits(ids: list[int]) -> list[WikiHit]:
    with pg.connection() as conn:
        rows = pg.rows(conn, WikiHit, HIT + " WHERE c.id = ANY(%s::bigint[])", (ids,))
    by_id = {r.id: r for r in rows}
    hits, seen = [], set()
    for i in ids:
        # The same document is often published twice (two links to one file): its pieces are the same text, shown once.
        if i in by_id and by_id[i].sha not in seen:
            seen.add(by_id[i].sha)
            hits.append(by_id[i])
    _resolve_cites(hits)
    return hits


def _resolve_cites(hits: list[WikiHit]) -> None:
    """A guide's piece says which pages its [n] point to: give each its title and original, so that the answer can cite them."""
    paths = {c["href"] for h in hits for c in h.cites if str(c.get("href", "")).startswith("/")}
    if not paths:
        return
    with pg.connection() as conn:
        pages = {r["path"]: r for r in conn.execute("SELECT path, title, resource, trust FROM wiki_pages WHERE path = ANY(%s)", (list(paths),)).fetchall()}
    for h in hits:
        seen = set()
        for c in h.cites:
            page = pages.get(c.get("href"))
            if page and page["path"] not in seen:
                seen.add(page["path"])
                h.based_on.append({"page": page["path"], "title": page["title"], "link": page["resource"], "trust": page["trust"]})


def search(queries: str | list[str], *, trust: Collection[str] | None = None, limit: int = 8, original: str | None = None) -> list[WikiHit]:
    """The `limit` pieces that answer the queries best. `trust` keeps only some kinds of pages (official, guide, wiki).
    `original` is the user's own question: one more angle that counts double (as in store.search)."""
    if isinstance(queries, str):
        queries = [queries]
    queries = [q for q in dict.fromkeys(q.strip() for q in queries if q.strip()) if _words(q)][:MAX_QUERIES]
    original = (original or "").strip()
    if original and _words(original):
        queries = [original, *[q for q in queries if q != original]]
    else:
        original = ""
    kinds = [t for t in (trust or TRUST) if t in TRUST]
    if not queries or not kinds:
        return []
    vectors = _embed_all(queries)
    with ThreadPoolExecutor(max_workers=4) as executor:
        jobs = [(executor.submit(_bm25, _words(q), kinds), executor.submit(_vector, vectors[i], kinds) if vectors else None) for i, q in enumerate(queries)]
        per_query = [_rrf(*[job.result() for job in pair if job]) for pair in jobs]
    if original:
        per_query[0] = {item: 2 * value for item, value in per_query[0].items()}
    reranking = settings.reranker_route is not None
    fused = _combine(per_query, max(limit, settings.rerank_candidates) if reranking else limit)
    if not fused:
        return []
    hits = _hits(fused)
    return _rerank(queries, hits, limit) if reranking else hits[:limit]


def _rerank(queries: list[str], hits: list[WikiHit], limit: int) -> list[WikiHit]:
    if len(hits) <= 1:
        return hits[:limit]
    documents = [f"{h.title}\n{h.heading}\n{h.text[:1000]}" for h in hits]
    queries = queries[:RERANK_QUERIES]
    try:
        with ThreadPoolExecutor(max_workers=len(queries)) as executor:
            scores = list(executor.map(lambda q: pg.rerank(q, documents), queries))
    except Exception:  # noqa: BLE001 - search must keep working without the reranker
        log.warning("reranker server unavailable, keeping the hybrid ranking", exc_info=True)
        return hits[:limit]
    best = [max(per_query[i] for per_query in scores) for i in range(len(hits))]
    order = sorted(range(len(hits)), key=lambda i: best[i], reverse=True)[:limit]
    if settings.rerank_min_score is not None:
        order = [i for i in order if best[i] >= settings.rerank_min_score]
    return [hits[i] for i in order]


def _clause_key(number: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", number))


def holds(clause_range: str, number: str) -> bool:
    """Whether a piece with clauses '5.3–5.5' holds clause '5.4' (or its sub-clause '5.4.1')."""
    if not clause_range or not number:
        return False
    first, _, last = clause_range.partition("–")
    want = _clause_key(number)
    lo, hi = _clause_key(first), _clause_key(last or first)
    return lo[: len(want)] <= want <= hi[: len(want)]


def page(path: str) -> list[WikiHit]:
    """All pieces of a page in order; empty if there is no such page."""
    with pg.connection() as conn:
        hits = pg.rows(conn, WikiHit, HIT + " WHERE c.path = %s ORDER BY c.seq", (path,))
    _resolve_cites(hits)
    return hits


def find_page(name: str) -> str | None:
    """A page by its path ('/regulations/x.md', 'regulations/x') or, failing that, by words of its title."""
    path = "/" + name.strip().lstrip("/")
    path = path if path.endswith(".md") else path + ".md"
    with pg.connection() as conn:
        if pg.scalar(conn, "SELECT path FROM wiki_pages WHERE path = %s", (path,)):
            return path
        # The model often drops the folder ('/sveden-f8519483-pdf.md'): the file name alone is unique enough.
        if found := pg.scalar(conn, "SELECT path FROM wiki_pages WHERE path LIKE %s ORDER BY length(path) LIMIT 1", ("%" + path,)):
            return found
        return pg.scalar(conn, "SELECT path FROM wiki_pages WHERE title ILIKE %s ORDER BY trust = 'official' DESC, length(title) LIMIT 1",
                         (f"%{name.strip()}%",))
