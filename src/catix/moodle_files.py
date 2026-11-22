"""The course files the InNoHassle browser extension uploaded (api/moodle.py), their text and their search.

A file is stored once per distinct content (`moodle_blobs`, keyed by the sha256 of its bytes) however many students have it,
and is reachable only through the user's own `moodle_files` rows. The `moodle-files` thread of `catix-worker`
(worker/moodle_reader.py) claims a blob, reads its text in a sandboxed subprocess (moodle_file_reader.py: PDF text
layer, LibreOffice to PDF, LightOnOCR for scans and images), and cuts it into `moodle_blob_chunks` one piece-run per page; it also
cuts the course texts (`chunk_texts`) into the same table. The embeddings worker (`embed_batch`) embeds them. `search` looks
in the pieces of the user's course files and texts and of those their study group shares."""

import logging
import os
import signal
import subprocess
import sys
import tempfile
import uuid
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Literal

from catix import moodle_sync
from catix.db import pg
from catix.db.store import MAX_QUERIES, _combine, _embed_all, _rrf, _words
from catix.docs import chunks
from catix.docs import store as docs_store
from catix.settings import settings

log = logging.getLogger("catix.moodle_files")

MAX_BYTES = 100 * 1024 * 1024
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
TEXT_BATCH = 50
AWAY_EXIT = 75  # moodle_file_reader: the OCR server did not answer


class OcrAway(RuntimeError):
    """The OCR server did not answer: the file is retried later and the attempt does not count."""


class ReadFailed(RuntimeError):
    pass


@dataclass
class Extracted:
    page_texts: list[tuple[int | None, str]] | None
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
    pages = result["page_texts"]
    return Extracted(None if pages is None else [(p, t) for p, t in pages], result["method"], result["pages"], result.get("skipped"))


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
        blank = not any(t.strip() for _, t in found.page_texts or [])
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
            rows = []
            for page, text in found.page_texts or []:  # a piece never spans two pages: one slide is one piece
                base = len(rows)
                rows.extend((job["sha256"], base + c.seq, page, c.heading, c.text, c.search_text(title)) for c in chunks.cut(text))
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO moodle_blob_chunks (sha256, seq, page, heading, text, search_text) VALUES (%s, %s, %s, %s, %s, %s)",
                    rows,
                )
        return True


def chunk_texts(limit: int = TEXT_BATCH) -> int:
    """Cut up to `limit` course texts (module texts, section summaries, announcements) that are not yet pieces into
    `moodle_blob_chunks`; the number handled, 0 = none waited. One transaction."""
    with pg.connection() as conn:
        texts = conn.execute(
            """SELECT t.sha256, t.text, COALESCE(
                 (SELECT name FROM moodle_modules WHERE text_sha256 = t.sha256 LIMIT 1),
                 (SELECT name FROM moodle_sections WHERE summary_sha256 = t.sha256 LIMIT 1),
                 (SELECT title FROM moodle_announcements WHERE text_sha256 = t.sha256 LIMIT 1), '') AS title
               FROM moodle_texts t WHERE NOT t.chunked ORDER BY t.sha256 LIMIT %s FOR UPDATE OF t SKIP LOCKED""",
            (limit,),
        ).fetchall()
        if not texts:
            return 0
        rows = [
            (t["sha256"], i, c.heading, c.text, c.search_text(t["title"]))
            for t in texts
            for i, c in enumerate(chunks.cut(t["text"]))
        ]
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO moodle_blob_chunks (text_sha256, seq, page, heading, text, search_text) VALUES (%s, %s, NULL, %s, %s, %s)",
                rows,
            )
        conn.execute("UPDATE moodle_texts SET chunked = true WHERE sha256 = ANY(%s::text[])", ([t["sha256"] for t in texts],))
        return len(texts)


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
class MoodleHit:
    chunk_id: int
    kind: Literal["file", "module", "section", "announcement"]
    course_id: int
    course: str
    path: str  # Course › Section › Module › file
    title: str
    url: str
    page: int | None
    heading: str
    text: str
    sha256: str | None  # the file's; none for course text
    shared: bool  # from the course of a member of the asker's study group
    relevance: float | None = None


_FILE_PIECES = moodle_sync.SCOPE_CTE + """
    SELECT c.id AS chunk_id, c.page, c.heading, c.text, c.sha256, x.course_id, x.own, x.course, x.section, x.module,
           x.filename, x.url
    FROM moodle_blob_chunks c
    JOIN LATERAL (
        SELECT s.course_id, s.own, mc.fullname AS course, sec.name AS section, m.name AS module, f.filename, f.url
        FROM s JOIN moodle_files f USING (innohassle_id, course_id)
        JOIN moodle_modules m USING (innohassle_id, course_id, module_id)
        JOIN moodle_sections sec ON sec.innohassle_id = s.innohassle_id AND sec.course_id = s.course_id AND sec.section_id = m.section_id
        JOIN moodle_courses mc ON mc.innohassle_id = s.innohassle_id AND mc.course_id = s.course_id
        WHERE f.sha256 = c.sha256 AND (s.own OR m.shareable)
        ORDER BY s.own DESC, s.course_id, f.module_id, f.position LIMIT 1
    ) x ON true
    WHERE c.id = ANY(%(ids)s::bigint[])"""

_TEXT_PIECES = moodle_sync.SCOPE_CTE + """
    SELECT c.id AS chunk_id, c.heading, c.text, x.kind, x.course_id, x.own, mc.fullname AS course, x.section, x.title, x.url,
           x.section_pos, x.discussion_id
    FROM moodle_blob_chunks c
    JOIN LATERAL (
        SELECT * FROM (
            SELECT 'module' AS kind, 0 AS prio, s.innohassle_id AS owner, s.own, s.course_id, sec.name AS section, m.name AS title,
                   m.url, sec.position AS section_pos, NULL::bigint AS discussion_id, m.position AS pos
            FROM s JOIN moodle_modules m USING (innohassle_id, course_id)
            JOIN moodle_sections sec ON sec.innohassle_id = s.innohassle_id AND sec.course_id = s.course_id AND sec.section_id = m.section_id
            WHERE m.text_sha256 = c.text_sha256 AND (s.own OR m.shareable)
            UNION ALL
            SELECT 'section', 1, s.innohassle_id, s.own, s.course_id, sec.name, sec.name, NULL, sec.position, NULL, 0
            FROM s JOIN moodle_sections sec USING (innohassle_id, course_id)
            WHERE sec.summary_sha256 = c.text_sha256 AND (s.own OR sec.shareable)
            UNION ALL
            SELECT 'announcement', 2, s.innohassle_id, s.own, s.course_id, '', a.title, NULL, 0, a.discussion_id, a.position
            FROM s JOIN moodle_announcements a USING (innohassle_id, course_id)
            WHERE a.text_sha256 = c.text_sha256
        ) u ORDER BY u.own DESC, u.prio, u.course_id, u.pos LIMIT 1
    ) x ON true
    JOIN moodle_courses mc ON mc.innohassle_id = x.owner AND mc.course_id = x.course_id
    WHERE c.id = ANY(%(ids)s::bigint[])"""


def _file_hit(r: dict) -> MoodleHit:
    path = " › ".join(p for p in (r["course"], r["section"], r["module"], r["filename"]) if p)
    return MoodleHit(r["chunk_id"], "file", r["course_id"], r["course"], path, r["filename"], r["url"], r["page"], r["heading"],
                     r["text"], r["sha256"], not r["own"])


def _text_hit(r: dict) -> MoodleHit:
    course_url = f"{moodle_sync.MOODLE_URL}course/view.php?id={r['course_id']}"
    if r["kind"] == "module":
        parts, url = (r["course"], r["section"], r["title"]), r["url"] or course_url
    elif r["kind"] == "section":
        parts, url = (r["course"], r["section"]), f"{course_url}#section-{r['section_pos']}"
    else:
        parts, url = (r["course"], "Announcements", r["title"]), f"{moodle_sync.MOODLE_URL}mod/forum/discuss.php?d={r['discussion_id']}"
    return MoodleHit(r["chunk_id"], r["kind"], r["course_id"], r["course"], " › ".join(p for p in parts if p), r["title"], url, None,
                     r["heading"], r["text"], None, not r["own"])


def search(
    innohassle_id: str | None, queries: list[str], *, study_groups: Sequence[str] = (), course_ids: list[int] | None = None,
    limit: int = 8, rerank: bool = True,
) -> list[MoodleHit]:
    """The `limit` pieces of the asker's course files and course texts, and of those their study groups share, that answer
    the queries best (hybrid BM25 + vector, reranked). `course_ids`: only these courses. `rerank=False` returns the whole
    pool of candidates unscored, for a rerank over several sources together (db/rerank.py)."""
    queries = [q for q in dict.fromkeys(q.strip() for q in queries if q.strip()) if _words(q)][:MAX_QUERIES]
    if not queries or limit <= 0:
        return []
    found = moodle_sync.scopes(innohassle_id, study_groups, course_ids)
    if not found:
        return []
    arrays = moodle_sync.scope_arrays(found)
    with pg.connection() as conn:
        shas = pg.column(
            conn,
            moodle_sync.SCOPE_CTE + """ SELECT DISTINCT f.sha256 FROM s JOIN moodle_files f USING (innohassle_id, course_id)
               JOIN moodle_modules m USING (innohassle_id, course_id, module_id)
               WHERE f.sha256 IS NOT NULL AND (s.own OR m.shareable)""",
            arrays,
        )
        text_shas = pg.column(
            conn,
            moodle_sync.SCOPE_CTE + """ SELECT x.summary_sha256 FROM s JOIN moodle_sections x USING (innohassle_id, course_id)
               WHERE x.summary_sha256 IS NOT NULL AND (s.own OR x.shareable)
               UNION SELECT x.text_sha256 FROM s JOIN moodle_modules x USING (innohassle_id, course_id)
               WHERE x.text_sha256 IS NOT NULL AND (s.own OR x.shareable)
               UNION SELECT x.text_sha256 FROM s JOIN moodle_announcements x USING (innohassle_id, course_id)
               WHERE x.text_sha256 IS NOT NULL""",
            arrays,
        )
    if not shas and not text_shas:
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
                   WHERE (search_text ||| %(q)s OR search_text::pdb.alias('search_text_en') ||| %(q)s)
                     AND (sha256 = ANY(%(s)s::text[]) OR text_sha256 = ANY(%(t)s::text[]))
                   ORDER BY pdb.score(id) DESC LIMIT %(n)s""",
                {"q": _words(query), "s": shas, "t": text_shas, "n": n},
            )
            nearest: list[int] = []
            if use_vectors:
                with conn.transaction():
                    conn.execute("SET LOCAL hnsw.iterative_scan = strict_order")
                    conn.execute("SELECT set_config('hnsw.ef_search', %s, true)", (str(settings.search_ef),))
                    nearest = pg.column(
                        conn,
                        """SELECT e.chunk_id FROM moodle_blob_chunk_embeddings e JOIN moodle_blob_chunks c ON c.id = e.chunk_id
                           WHERE (c.sha256 = ANY(%(s)s::text[]) OR c.text_sha256 = ANY(%(t)s::text[]))
                           ORDER BY e.embedding <=> %(v)s::vector LIMIT %(n)s""",
                        {"s": shas, "t": text_shas, "v": vectors[i], "n": n},
                    )
            per_query.append(_rrf(bm25, nearest))
    per_query = [scores for scores in per_query if scores]
    reranking = settings.reranker_route is not None and rerank
    fused = _combine(per_query, max(limit, settings.docs_rerank_candidates) if reranking or not rerank else limit, reserve=1)
    if not fused:
        return []
    with pg.connection() as conn:
        params = {**arrays, "ids": fused}
        found_hits = {r["chunk_id"]: _file_hit(r) for r in conn.execute(_FILE_PIECES, params).fetchall()}
        found_hits |= {r["chunk_id"]: _text_hit(r) for r in conn.execute(_TEXT_PIECES, params).fetchall()}
    hits = [found_hits[i] for i in fused if i in found_hits]
    if not rerank:
        return hits
    return _rerank(queries, hits, limit) if reranking else hits[:limit]


def rerank_document(h: MoodleHit) -> str:
    return f"{h.path}\n{h.heading}\n{h.text[:settings.rerank_max_chars]}"


def _rerank(queries: list[str], hits: list[MoodleHit], limit: int) -> list[MoodleHit]:
    """As db.docs._rerank: the best score over the queries orders the hits, the second best is their `relevance`."""
    if not hits:
        return hits
    documents = [rerank_document(h) for h in hits]
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
