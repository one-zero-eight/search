"""The course files the InNoHassle browser extension uploaded (api/moodle.py), their text and their search.

A file is stored once per distinct content (`moodle_blobs`, keyed by the sha256 of its bytes) however many students have it,
and is reachable only through the user's own `moodle_files` rows. The `moodle-files` thread of `catix-docs run --loop`
(docs/moodle_files_worker.py) claims a blob, reads its text in a sandboxed subprocess (moodle_file_reader.py: PDF text
layer, LibreOffice to PDF, LightOnOCR for scans and images), and cuts it into `moodle_blob_chunks`; the embeddings worker
(`embed_batch`) embeds them. `search` looks only in the chunks of the files the user lists."""

import logging
import os
import signal
import subprocess
import sys
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Literal

from catix.db import pg
from catix.db.store import MAX_QUERIES, _combine, _embed_all, _rrf, _words
from catix.docs import chunks
from catix.docs import store as docs_store
from catix.settings import settings

log = logging.getLogger("catix.moodle_files")

MAX_BYTES = 25 * 1024 * 1024
SUFFIXES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".rtf": "application/rtf",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".odp": "application/vnd.oasis.opendocument.presentation",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
INLINE = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".md"}  # shown in the browser; the rest are downloaded
READ_TIMEOUT = 1800  # seconds
LEASE = timedelta(hours=2)
MAX_ATTEMPTS = 3
EMBED_BATCH = 32
AWAY_EXIT = 75  # moodle_file_reader: the OCR server did not answer


class OcrAway(RuntimeError):
    """The OCR server did not answer: the file is retried later and the attempt does not count."""


class ReadFailed(RuntimeError):
    pass


@dataclass
class Extracted:
    text: str | None
    method: str
    pages: int
    skipped: str | None = None


def read_file(data: bytes, suffix: str) -> Extracted:
    """The text of an uploaded file, read by moodle_file_reader.py in a subprocess without credentials (the bytes are
    untrusted); it and its descendants (LibreOffice, the JVM, poppler) are killed when it ends."""
    import json

    process = None
    with tempfile.TemporaryDirectory(prefix="catix-moodle-file-") as work:
        try:
            env = {k: os.environ[k] for k in ("PATH", "LANG") if k in os.environ}
            env["TMPDIR"] = env["HOME"] = work  # LibreOffice needs a writable HOME
            env["DATABASE_URL"] = ""  # the docs modules it imports must not reach the corpus (nor .env: cwd is `work`)
            env["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent)
            if settings.ocr_route:
                env["OCR_ROUTE"] = str(settings.ocr_route)
            env["OCR_MODEL"] = str(settings.ocr_model)
            env["OCR_PARALLEL"] = str(settings.ocr_parallel)
            process = subprocess.Popen(
                [sys.executable, str(Path(__file__).with_name("moodle_file_reader.py")), suffix],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                env=env, cwd=work, start_new_session=True,
            )
            output, _ = process.communicate(data, timeout=READ_TIMEOUT)
        except (subprocess.TimeoutExpired, OSError):
            raise ReadFailed("timed out or could not start") from None
        finally:
            if process is not None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
    if process.returncode == AWAY_EXIT:
        raise OcrAway
    if process.returncode:
        raise ReadFailed(f"reader exited with {process.returncode}")
    result = json.loads(output)
    return Extracted(result["text"], result["method"], result["pages"], result.get("skipped"))


# ---- storage

def put_blob(innohassle_id: str, sha256: str, data: bytes) -> Literal["ok", "not_listed", "type"]:
    """Store a file the user's Moodle content lists (the caller checked that `sha256` is the hash of `data`)."""
    with pg.connection() as conn:
        filename = pg.scalar(
            conn,
            "SELECT filename FROM moodle_files WHERE innohassle_id = %s AND sha256 = %s ORDER BY course_id, module_id, position LIMIT 1",
            (innohassle_id, sha256),
        )
        if filename is None:
            return "not_listed"
        suffix = Path(filename).suffix.lower()
        if suffix not in SUFFIXES:
            return "type"
        conn.execute(
            "INSERT INTO moodle_blobs (sha256, suffix, size_bytes, data) VALUES (%s, %s, %s, %s) ON CONFLICT (sha256) DO NOTHING",
            (sha256, suffix, len(data), data),
        )
        return "ok"


def get_blob(innohassle_id: str, sha256: str) -> tuple[str, str, bytes] | None:
    """(filename, suffix, bytes) of a file the user lists."""
    with pg.connection() as conn:
        row = conn.execute(
            """SELECT f.filename, b.suffix, b.data FROM moodle_blobs b
               JOIN LATERAL (SELECT filename FROM moodle_files WHERE innohassle_id = %s AND sha256 = b.sha256
                             ORDER BY course_id, module_id, position LIMIT 1) f ON true
               WHERE b.sha256 = %s""",
            (innohassle_id, sha256),
        ).fetchone()
    return (row["filename"], row["suffix"], bytes(row["data"])) if row else None


def claim() -> dict | None:
    """The next blob to read (its lease is taken), None when none waits."""
    token = uuid.uuid4().hex
    with pg.connection() as conn:
        row = conn.execute(
            """UPDATE moodle_blobs SET status = 'claimed', token = %(t)s, lease_until = now() + %(lease)s, attempts = attempts + 1
               WHERE sha256 = (SELECT sha256 FROM moodle_blobs
                               WHERE (status = 'pending' OR status = 'claimed' AND lease_until < now()) AND available_at <= now()
                               ORDER BY available_at, uploaded_at LIMIT 1 FOR UPDATE SKIP LOCKED)
               RETURNING sha256, suffix, data, attempts""",
            {"t": token, "lease": LEASE},
        ).fetchone()
    if row is None:
        return None
    return {**row, "data": bytes(row["data"]), "token": token}


def finish(job: dict, found: Extracted) -> bool:
    """Store the text of a claimed blob as pieces; False when the blob was collected or its lease lost meanwhile."""
    with pg.connection() as conn:
        title = pg.scalar(
            conn,
            "SELECT filename FROM moodle_files WHERE sha256 = %s ORDER BY innohassle_id, course_id, module_id, position LIMIT 1",
            (job["sha256"],),
        ) or job["sha256"]
        blank = not (found.text or "").strip()
        status = "skipped" if found.skipped else "done"
        note = found.skipped or ("no text" if blank else None)
        updated = conn.execute(
            """UPDATE moodle_blobs SET status = %s, method = %s, pages = %s, note = %s, extracted_at = now(), token = NULL, lease_until = NULL
               WHERE sha256 = %s AND token = %s RETURNING 1""",
            (status, found.method or None, found.pages, note, job["sha256"], job["token"]),
        ).fetchone()
        if updated is None:
            return False
        conn.execute("DELETE FROM moodle_blob_chunks WHERE sha256 = %s", (job["sha256"],))
        if not blank and not found.skipped:
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO moodle_blob_chunks (sha256, seq, heading, text, search_text) VALUES (%s, %s, %s, %s, %s)",
                    [(job["sha256"], c.seq, c.heading, c.text, c.search_text(title)) for c in chunks.cut(found.text or "")],
                )
        return True


def fail(job: dict, away: bool, note: str) -> None:
    """A claimed blob that could not be read: `away` (the OCR server is down) is asked again soon without counting; else
    again later with a growing pause, and 'failed' after MAX_ATTEMPTS."""
    with pg.connection() as conn:
        if away:
            conn.execute(
                """UPDATE moodle_blobs SET status = 'pending', attempts = attempts - 1, available_at = now() + interval '60 seconds',
                          token = NULL, lease_until = NULL WHERE sha256 = %s AND token = %s""",
                (job["sha256"], job["token"]),
            )
        else:
            conn.execute(
                """UPDATE moodle_blobs SET status = CASE WHEN attempts >= %s THEN 'failed' ELSE 'pending' END,
                          available_at = now() + least(3600, 60 * 2 ^ (attempts - 1)) * interval '1 second',
                          note = %s, token = NULL, lease_until = NULL WHERE sha256 = %s AND token = %s""",
                (MAX_ATTEMPTS, note, job["sha256"], job["token"]),
            )


def embed_batch(size: int = EMBED_BATCH) -> int:
    """Embed one batch of queued pieces; 0 = the queue is empty. One transaction: a failure leaves them queued."""
    with pg.connection() as conn:
        rows = conn.execute(
            """SELECT c.id, c.search_text FROM moodle_blob_chunks c
               JOIN (SELECT chunk_id FROM moodle_blob_embedding_queue ORDER BY chunk_id LIMIT %s FOR UPDATE SKIP LOCKED) q
               ON q.chunk_id = c.id""",
            (size,),
        ).fetchall()
        if not rows:
            return 0
        docs_store.check_model(conn)
        vectors = pg.embed([r["search_text"] for r in rows])
        with conn.cursor() as cur:
            cur.executemany(
                """INSERT INTO moodle_blob_chunk_embeddings (chunk_id, embedding) VALUES (%s, %s)
                   ON CONFLICT (chunk_id) DO UPDATE SET embedding = excluded.embedding""",
                [(r["id"], v) for r, v in zip(rows, vectors, strict=True)],
            )
        conn.execute("DELETE FROM moodle_blob_embedding_queue WHERE chunk_id = ANY(%s::bigint[])", ([r["id"] for r in rows],))
        return len(rows)


# ---- search

@dataclass
class MoodleFileHit:
    chunk_id: int
    sha256: str
    heading: str
    text: str
    course_id: int
    course: str
    module_id: int
    filename: str
    url: str
    relevance: float | None = None


def search(innohassle_id: str, queries: list[str], *, course_ids: list[int] | None = None, limit: int = 8) -> list[MoodleFileHit]:
    """The `limit` pieces of the user's own course files that answer the queries best (hybrid BM25 + vector, reranked)."""
    queries = [q for q in dict.fromkeys(q.strip() for q in queries if q.strip()) if _words(q)][:MAX_QUERIES]
    if not queries or limit <= 0:
        return []
    sql = "SELECT DISTINCT sha256 FROM moodle_files WHERE innohassle_id = %s AND sha256 IS NOT NULL"
    params: list = [innohassle_id]
    if course_ids:
        sql += " AND course_id = ANY(%s)"
        params.append(course_ids)
    with pg.connection() as conn:
        shas = pg.column(conn, sql, params)
    if not shas:
        return []
    vectors = _embed_all(queries)
    n = settings.docs_search_candidates
    per_query = []
    with pg.connection() as conn:
        use_vectors = bool(vectors) and (
            pg.scalar(conn, "SELECT value FROM docs_meta WHERE key = 'embeddings_model'") == settings.embeddings_model)
        for i, query in enumerate(queries):
            bm25 = pg.column(
                conn,
                """SELECT id FROM moodle_blob_chunks
                   WHERE (search_text ||| %(q)s OR search_text::pdb.alias('search_text_en') ||| %(q)s) AND sha256 = ANY(%(s)s)
                   ORDER BY pdb.score(id) DESC LIMIT %(n)s""",
                {"q": _words(query), "s": shas, "n": n},
            )
            nearest: list[int] = []
            if use_vectors:
                with conn.transaction():
                    conn.execute("SET LOCAL hnsw.iterative_scan = strict_order")
                    conn.execute("SELECT set_config('hnsw.ef_search', %s, true)", (str(settings.search_ef),))
                    nearest = pg.column(
                        conn,
                        """SELECT e.chunk_id FROM moodle_blob_chunk_embeddings e JOIN moodle_blob_chunks c ON c.id = e.chunk_id
                           WHERE c.sha256 = ANY(%(s)s) ORDER BY e.embedding <=> %(v)s::vector LIMIT %(n)s""",
                        {"s": shas, "v": vectors[i], "n": n},
                    )
            per_query.append(_rrf(bm25, nearest))
    per_query = [scores for scores in per_query if scores]
    reranking = settings.reranker_route is not None
    fused = _combine(per_query, max(limit, settings.docs_rerank_candidates) if reranking else limit, reserve=1)
    if not fused:
        return []
    with pg.connection() as conn:
        found = {
            r.chunk_id: r
            for r in pg.rows(
                conn,
                MoodleFileHit,
                """SELECT c.id AS chunk_id, c.sha256, c.heading, c.text, f.course_id, mc.fullname AS course, f.module_id, f.filename, f.url
                   FROM moodle_blob_chunks c
                   JOIN LATERAL (SELECT course_id, module_id, filename, url FROM moodle_files
                                 WHERE innohassle_id = %(u)s AND sha256 = c.sha256
                                 ORDER BY course_id, module_id, position LIMIT 1) f ON true
                   JOIN moodle_courses mc ON mc.innohassle_id = %(u)s AND mc.course_id = f.course_id
                   WHERE c.id = ANY(%(ids)s)""",
                {"u": innohassle_id, "ids": fused},
            )
        }
    hits = [found[i] for i in fused if i in found]
    return _rerank(queries, hits, limit) if reranking else hits[:limit]


def _rerank(queries: list[str], hits: list[MoodleFileHit], limit: int) -> list[MoodleFileHit]:
    """As db.docs._rerank: the best score over the queries orders the hits, the second best is their `relevance`."""
    if not hits:
        return hits
    documents = [f"{h.filename}\n{h.heading}\n{h.text[:settings.rerank_max_chars]}" for h in hits]
    queries = queries[:settings.rerank_queries]
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
    for i, column in enumerate(zip(*scores)):
        hits[i].relevance = sorted(column, reverse=True)[1 if len(column) > 1 else 0]
    return [hits[i] for i in order]
