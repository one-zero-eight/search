"""The documents of the sources in the database, for the agent's search (catix-docs, src/catix/docs/).

A document is a path, the meta that its front matter used to hold, and a markdown body. Only what changed is done again: a
document with the same fingerprint (the cutting scheme, chunks.SCHEME, the meta and the body) as last time is skipped. A changed
document is cut again and its pieces are matched with the stored ones by the fingerprint of their text: a piece that stayed the
same keeps its row and its vector, a new piece is inserted, a piece that is gone is deleted. A document that a source no longer
makes is deleted with its pieces. Each document is one transaction, so the search sees either the old document or the new one.

A piece whose text stands on other documents too (the course programme of each intake repeats the last one) is searched once:
the others are marked as its copies (mark_copies) and shown as the places it also stands.

New pieces are found by words at once; their vectors come from a queue (document_embedding_queue, filled by a trigger), which
`catix-docs build --embed` drains and the embedding workers drain too (worker/embedder.py). When the embeddings model changes,
every vector is dropped and every piece is queued again.
"""

import hashlib
import json
import time
from collections import defaultdict
from dataclasses import dataclass

from catix.db import pg
from catix.docs.chunks import SCHEME, Chunk, cut
from catix.settings import settings

PRODUCER = "catix-docs"
DOC_FIELDS = 4  # in the fingerprint: change it when the meaning of meta changes
EMBED_BATCH = 32

AUDIENCES = ("student", "postgraduate", "applicant", "teacher", "staff", "management", "public")  # who a document is for


@dataclass(frozen=True)
class Document:
    path: str  # 'regulations/<key>', 'sites/<site>/<slug>', 'course-programmes/<key>', 'past-papers/<subject>', 'eduwiki/<folder>/<slug>'
    meta: dict  # the keys and values the front matter of this page used to have
    body: str  # the markdown after the front matter


def fingerprint(doc: Document) -> str:
    meta = json.dumps(doc.meta, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(f"{SCHEME}\n{DOC_FIELDS}\n{meta}\n{doc.body}".encode()).hexdigest()[:16]


def trust_of(meta: dict) -> str:
    return "official" if meta.get("source_kind") == "official-document" else "wiki"


def plan(old: list[tuple[int, str]], new: list[Chunk]) -> tuple[list[tuple[int, Chunk]], list[Chunk], list[int]]:
    """Match the stored pieces (id, sha) with the new ones: (kept: stored id and its new piece, to insert, ids to delete).
    Pieces with the same text are matched in order, so a text that occurs twice keeps both rows."""
    free: dict[str, list[int]] = defaultdict(list)
    for chunk_id, sha in old:
        free[sha].append(chunk_id)
    kept, insert = [], []
    for c in new:
        if free.get(c.sha):
            kept.append((free[c.sha].pop(0), c))
        else:
            insert.append(c)
    return kept, insert, [i for ids in free.values() for i in ids]


def _text(value) -> str | None:
    if value in (None, "", []):
        return None
    return "; ".join(map(str, value)) if isinstance(value, list) else str(value)


def write_page(conn, doc: Document, sha: str, chunks: list[Chunk]) -> tuple[int, int, int]:
    """Store one document and its pieces (in the caller's transaction); (kept, inserted, deleted) pieces."""
    rel, meta = doc.path, doc.meta
    title = str(meta.get("title") or rel)
    trust = trust_of(meta)
    stale = str(meta.get("stale_after") or "")[:10] or None
    sources = meta.get("sources") or [{}]
    generated = str((meta.get("generated") or {}).get("at", ""))[:10] if isinstance(meta.get("generated"), dict) else ""
    issued = max((str(s.get("last_modified") or "")[:10] for s in sources if isinstance(s, dict)), default="")
    if trust == "official" and issued == generated:
        issued = ""  # no date found in the document: sources/regulations.py put the day it was read there, which says nothing
    conn.execute(
        """INSERT INTO documents (path, sha, title, type, trust, audience, resource, status, review, source_warning, stale_after, issued,
                                  body, meta, indexed_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, now())
           ON CONFLICT (path) DO UPDATE SET sha = excluded.sha, title = excluded.title, type = excluded.type, trust = excluded.trust,
               audience = excluded.audience, resource = excluded.resource, status = excluded.status, review = excluded.review,
               source_warning = excluded.source_warning, stale_after = excluded.stale_after, issued = excluded.issued,
               body = excluded.body, meta = excluded.meta, indexed_at = now()""",
        (rel, sha, title, str(meta.get("type") or ""), trust, [str(a) for a in meta.get("audience") or []], _text(meta.get("resource")),
         _text(meta.get("status")), _text(meta.get("review")), _text(meta.get("source_warning")), stale, issued or None,
         doc.body, json.dumps(meta, ensure_ascii=False, default=str)),
    )
    old = [(r["id"], r["sha"]) for r in conn.execute("SELECT id, sha FROM document_chunks WHERE path = %s", (rel,)).fetchall()]
    kept, insert, delete = plan(old, chunks)
    if delete:
        conn.execute("DELETE FROM document_chunks WHERE id = ANY(%s::bigint[])", (delete,))
    with conn.cursor() as cur:
        # The trigger queues a vector only when search_text really changed (a new title), not for a new position.
        cur.executemany(
            "UPDATE document_chunks SET seq = %s, trust = %s, clause = %s, search_text = %s, cites = %s WHERE id = %s",
            [(c.seq, trust, c.clause, c.search_text(title), json.dumps(c.cites, ensure_ascii=False), chunk_id) for chunk_id, c in kept],
        )
        cur.executemany(
            """INSERT INTO document_chunks (path, trust, seq, heading, clause, sha, text, search_text, cites)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            [(rel, trust, c.seq, c.heading, c.clause, c.sha, c.text, c.search_text(title), json.dumps(c.cites, ensure_ascii=False)) for c in insert],
        )
    return len(kept), len(insert), len(delete)


def check_model(conn) -> None:
    """Vectors of another embeddings model cannot be compared with new ones: drop them all and queue every piece."""
    model = pg.scalar(conn, "SELECT value FROM docs_meta WHERE key = 'embeddings_model'")
    if model == settings.embeddings_model:
        return
    if model is not None:
        conn.execute("DELETE FROM document_chunk_embeddings")
        conn.execute("INSERT INTO document_embedding_queue (chunk_id) SELECT id FROM document_chunks ON CONFLICT DO NOTHING")
        print(f"embeddings model changed ({model} -> {settings.embeddings_model}): every piece is embedded again")
    conn.execute("INSERT INTO docs_meta (key, value) VALUES ('embeddings_model', %s) ON CONFLICT (key) DO UPDATE SET value = excluded.value",
                 (settings.embeddings_model,))


def sync(prefix: str, docs: list[Document], keep: tuple[str, ...] = ()) -> dict[str, int]:
    """Make the documents under `prefix` what `docs` says: changed ones written, gone ones deleted (but not those under a
    prefix of `keep`: sources read on another machine)."""
    seen: set[str] = set()
    for doc in docs:
        if not doc.path.startswith(prefix) or doc.path in seen:
            raise ValueError(doc.path)
        seen.add(doc.path)
    counts = defaultdict(int)
    with pg.connection() as conn:
        check_model(conn)
        stored = {r["path"]: r["sha"] for r in conn.execute("SELECT path, sha FROM documents WHERE starts_with(path, %s)", (prefix,)).fetchall()}
    for doc in docs:
        sha = fingerprint(doc)
        if stored.get(doc.path) == sha:
            counts["pages unchanged"] += 1
            continue
        with pg.connection() as conn:  # one document, one transaction
            kept, inserted, deleted = write_page(conn, doc, sha, cut(doc.body))
        counts["pages changed" if doc.path in stored else "pages new"] += 1
        counts["pieces kept"] += kept
        counts["pieces new"] += inserted
        counts["pieces deleted"] += deleted
    gone = sorted(p for p in set(stored) - seen if not p.startswith(keep))
    if gone:
        with pg.connection() as conn:
            conn.execute("DELETE FROM documents WHERE path = ANY(%s)", (gone,))
        counts["pages removed"] = len(gone)
    return dict(counts)


def prune(prefixes: tuple[str, ...]) -> int:
    """Delete the documents under no prefix: old paths nobody makes any more."""
    with pg.connection() as conn:
        return conn.execute("DELETE FROM documents WHERE NOT (path LIKE ANY(%s))", ([p + "%" for p in prefixes],)).rowcount


# Pieces of one text are one group, among pages of one kind; with ACROSS_COURSES off, a course programme's piece only with
# those of the same course (the same paragraph of two courses may be two facts: "144 hours" of each). The one searched is
# of the latest intake, then of the latest document; the others are named with it, those the question names first.
ACROSS_COURSES = False
COPIES = r"""
WITH keyed AS (
    SELECT c.id, md5(c.trust || '|' || CASE WHEN c.path LIKE 'course-programmes/%%' AND NOT %(across)s
                                          THEN coalesce(substring(p.title FROM '«([^»]+)»'), p.title) ELSE '' END
                     || '|' || regexp_replace(lower(c.text), '\s+', ' ', 'g')) AS key,
           substring(p.title FROM 'набор (\d{4})')::int AS intake, p.issued
    FROM document_chunks c JOIN documents p ON p.path = c.path
), grouped AS (
    SELECT id, first_value(id) OVER (PARTITION BY key ORDER BY intake DESC NULLS LAST, issued DESC NULLS LAST, id) AS main FROM keyed
)
UPDATE document_chunks c SET copy_of = nullif(g.main, g.id) FROM grouped g
WHERE c.id = g.id AND c.copy_of IS DISTINCT FROM nullif(g.main, g.id)
"""


def mark_copies(conn, across_courses: bool = ACROSS_COURSES) -> int:
    """Mark again which pieces are copies of others (all of them: a new page may hold the latest copy); the rows changed."""
    return conn.execute(COPIES, {"across": across_courses}).rowcount


CLAIM = """
SELECT c.id, c.search_text FROM document_chunks c
JOIN (SELECT chunk_id FROM document_embedding_queue ORDER BY chunk_id LIMIT %s FOR UPDATE SKIP LOCKED) q ON q.chunk_id = c.id
"""


def embed_batch(size: int = EMBED_BATCH) -> int:
    """Embed one batch of queued pieces; 0 = the queue is empty. Like the messages' worker: one transaction, a failure leaves them queued."""
    with pg.connection() as conn:
        rows = conn.execute(CLAIM, (size,)).fetchall()
        if not rows:
            return 0
        check_model(conn)
        _embed_rows(conn, rows)
        conn.execute("DELETE FROM document_embedding_queue WHERE chunk_id = ANY(%s::bigint[])", ([r["id"] for r in rows],))
        return len(rows)


def _embed_rows(conn, rows: list[dict]) -> None:
    vectors = pg.embed([record["search_text"] for record in rows])
    with conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO document_chunk_embeddings (chunk_id, embedding) VALUES (%s, %s)
               ON CONFLICT (chunk_id) DO UPDATE SET embedding = excluded.embedding""",
            [(record["id"], vector) for record, vector in zip(rows, vectors, strict=True)],
        )


def embed_all() -> int:
    done, started, last = 0, time.monotonic(), time.monotonic()
    while n := embed_batch():
        done += n
        if time.monotonic() - last > 30:
            print(f"  {done} pieces embedded, {queued()} queued ({done / (time.monotonic() - started):.0f}/s)", flush=True)
            last = time.monotonic()
    return done


def queued() -> int:
    with pg.connection() as conn:
        return pg.scalar(conn, "SELECT count(*) FROM document_embedding_queue")


def status() -> None:
    with pg.connection() as conn:
        for r in conn.execute("""SELECT p.trust, count(DISTINCT p.path) AS pages, count(c.id) AS pieces, count(e.chunk_id) AS vectors
                                 FROM documents p LEFT JOIN document_chunks c ON c.path = p.path
                                 LEFT JOIN document_chunk_embeddings e ON e.chunk_id = c.id GROUP BY p.trust ORDER BY p.trust""").fetchall():
            print(f"{r['trust']:<9} {r['pages']:>5} pages {r['pieces']:>7} pieces {r['vectors']:>7} vectors")
        print(f"queued for a vector: {pg.scalar(conn, 'SELECT count(*) FROM document_embedding_queue')}")
        for r in conn.execute("SELECT split_part(path, '/', 1) AS source, count(*) AS n FROM documents GROUP BY 1 ORDER BY 1").fetchall():
            print(f"{r['source']:<20} {r['n']:>6} documents")

