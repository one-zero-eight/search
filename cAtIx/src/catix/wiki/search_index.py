"""The wiki in the database, for the agent's search: `catix-wiki index`.

Only what changed is done again. A page whose file (and the cutting scheme, chunks.SCHEME) has the same fingerprint as
last time is skipped. A changed page is cut again and its pieces are matched with the stored ones by the fingerprint of
their text: a piece that stayed the same keeps its row and its vector (only its position or the title in its search
text may be updated), a new piece is inserted, a piece that is gone is deleted. A page whose file is gone is deleted with
its pieces. Each page is one transaction, so the search sees either the old page or the new one.

New pieces are found by words at once; their vectors come from a queue (wiki_embedding_queue, filled by a trigger), which
this command drains at the end and the embedding workers drain too (worker/embedder.py). When the embeddings model
changes, every vector is dropped and every piece is queued again.

    catix-wiki index              # sync the database with wiki/ and compute the missing vectors
    catix-wiki index --no-embed   # sync only; the workers compute the vectors
    catix-wiki index status       # pages, pieces, vectors, queue
    catix-wiki index export FILE  # the wiki's tables, vectors included, into one file
    catix-wiki index import FILE  # replace the wiki's tables with the file's: the server does not compute 88k vectors again

Export and import move only the wiki's tables (not the messages of the chats). The file says which embeddings model made
its vectors and which commit of the `wiki` branch it was made from: after the import, `catix-wiki index` on a checkout of
that commit finds every page unchanged; on a later commit it does only what changed since.
"""

import hashlib
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

from catix.db import pg
from catix.settings import settings
from catix.wiki.chunks import SCHEME, Chunk, cut
from catix.wiki.compile import BUNDLE

SKIP = {"index.md", "log.md", "README.md"}
PAGE_FIELDS = 3  # change it when wiki_pages gets a new field: every page row is written again (its pieces and vectors stay)
EMBED_BATCH = 32


def files(bundle: Path = BUNDLE) -> dict[str, Path]:
    """Bundle path ('/regulations/x.md') -> file, for every concept (not the index, the log, the README, Obsidian's or the claims' folders)."""
    return {"/" + p.relative_to(bundle).as_posix(): p for p in sorted(bundle.rglob("*.md"))
            if p.name not in SKIP and not any(part.startswith(".") for part in p.relative_to(bundle).parts)}


def fingerprint(text: str) -> str:
    return hashlib.sha256(f"{SCHEME}\n{PAGE_FIELDS}\n{text}".encode()).hexdigest()[:16]


def trust_of(meta: dict) -> str:
    if meta.get("source_kind") == "official-document":
        return "official"
    return "guide" if meta.get("type") == "guide" else "wiki"


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


def write_page(conn, rel: str, sha: str, meta: dict, chunks: list[Chunk]) -> tuple[int, int, int]:
    """Store one page and its pieces (in the caller's transaction); (kept, inserted, deleted) pieces."""
    title = str(meta.get("title") or rel)
    trust = trust_of(meta)
    stale = str(meta.get("stale_after") or "")[:10] or None
    sources = meta.get("sources") or [{}]
    generated = str((meta.get("generated") or {}).get("at", ""))[:10] if isinstance(meta.get("generated"), dict) else ""
    issued = generated if trust == "guide" else max((str(s.get("last_modified") or "")[:10] for s in sources if isinstance(s, dict)), default="")
    if trust == "official" and issued == generated:
        issued = ""  # no date found in the document: sources/regulations.py put the day it was downloaded there, which says nothing
    conn.execute(
        """INSERT INTO wiki_pages (path, sha, title, type, trust, audience, resource, status, review, source_warning, stale_after, issued, indexed_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
           ON CONFLICT (path) DO UPDATE SET sha = excluded.sha, title = excluded.title, type = excluded.type, trust = excluded.trust,
               audience = excluded.audience, resource = excluded.resource, status = excluded.status, review = excluded.review,
               source_warning = excluded.source_warning, stale_after = excluded.stale_after, issued = excluded.issued, indexed_at = now()""",
        (rel, sha, title, str(meta.get("type") or ""), trust, [str(a) for a in meta.get("audience") or []], _text(meta.get("resource")),
         _text(meta.get("status")), _text(meta.get("review")), _text(meta.get("source_warning")), stale, issued or None),
    )
    old = [(r["id"], r["sha"]) for r in conn.execute("SELECT id, sha FROM wiki_chunks WHERE path = %s", (rel,)).fetchall()]
    kept, insert, delete = plan(old, chunks)
    if delete:
        conn.execute("DELETE FROM wiki_chunks WHERE id = ANY(%s::bigint[])", (delete,))
    with conn.cursor() as cur:
        # The trigger queues a vector only when search_text really changed (a new title), not for a new position.
        cur.executemany(
            "UPDATE wiki_chunks SET seq = %s, trust = %s, clause = %s, search_text = %s, cites = %s WHERE id = %s",
            [(c.seq, trust, c.clause, c.search_text(title), json.dumps(c.cites, ensure_ascii=False), chunk_id) for chunk_id, c in kept],
        )
        cur.executemany(
            """INSERT INTO wiki_chunks (path, trust, seq, heading, clause, sha, text, search_text, cites)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            [(rel, trust, c.seq, c.heading, c.clause, c.sha, c.text, c.search_text(title), json.dumps(c.cites, ensure_ascii=False)) for c in insert],
        )
    return len(kept), len(insert), len(delete)


def check_model(conn) -> None:
    """Vectors of another embeddings model cannot be compared with new ones: drop them all and queue every piece."""
    model = pg.scalar(conn, "SELECT value FROM wiki_meta WHERE key = 'embeddings_model'")
    if model == settings.embeddings_model:
        return
    if model is not None:
        conn.execute("DELETE FROM wiki_chunk_embeddings")
        conn.execute("INSERT INTO wiki_embedding_queue (chunk_id) SELECT id FROM wiki_chunks ON CONFLICT DO NOTHING")
        print(f"embeddings model changed ({model} -> {settings.embeddings_model}): every piece is embedded again")
    conn.execute("INSERT INTO wiki_meta (key, value) VALUES ('embeddings_model', %s) ON CONFLICT (key) DO UPDATE SET value = excluded.value",
                 (settings.embeddings_model,))


def sync(bundle: Path = BUNDLE) -> dict[str, int]:
    found = files(bundle)
    counts = defaultdict(int)
    with pg.connection() as conn:
        check_model(conn)
        stored = {r["path"]: r["sha"] for r in conn.execute("SELECT path, sha FROM wiki_pages").fetchall()}
    for rel, path in found.items():
        text = path.read_text(encoding="utf-8")
        sha = fingerprint(text)
        if stored.get(rel) == sha:
            counts["pages unchanged"] += 1
            continue
        meta, chunks = cut(text)
        with pg.connection() as conn:  # one page, one transaction
            kept, inserted, deleted = write_page(conn, rel, sha, meta, chunks)
        counts["pages changed" if rel in stored else "pages new"] += 1
        counts["pieces kept"] += kept
        counts["pieces new"] += inserted
        counts["pieces deleted"] += deleted
    gone = sorted(set(stored) - set(found))
    if gone:
        with pg.connection() as conn:
            conn.execute("DELETE FROM wiki_pages WHERE path = ANY(%s)", (gone,))
        counts["pages removed"] = len(gone)
    return dict(counts)


CLAIM = """
SELECT c.id, c.search_text FROM wiki_chunks c
JOIN (SELECT chunk_id FROM wiki_embedding_queue ORDER BY chunk_id LIMIT %s FOR UPDATE SKIP LOCKED) q ON q.chunk_id = c.id
"""


def embed_batch(size: int = EMBED_BATCH) -> int:
    """Embed one batch of queued pieces; 0 = the queue is empty. Like the messages' worker: one transaction, a failure leaves them queued."""
    with pg.connection() as conn:
        rows = conn.execute(CLAIM, (size,)).fetchall()
        if not rows:
            return 0
        vectors = pg.embed([r["search_text"] for r in rows])
        with conn.cursor() as cur:
            cur.executemany(
                """INSERT INTO wiki_chunk_embeddings (chunk_id, embedding) VALUES (%s, %s)
                   ON CONFLICT (chunk_id) DO UPDATE SET embedding = excluded.embedding""",
                [(r["id"], v) for r, v in zip(rows, vectors)],
            )
        conn.execute("DELETE FROM wiki_embedding_queue WHERE chunk_id = ANY(%s::bigint[])", ([r["id"] for r in rows],))
        return len(rows)


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
        return pg.scalar(conn, "SELECT count(*) FROM wiki_embedding_queue")


def status() -> None:
    with pg.connection() as conn:
        for r in conn.execute("""SELECT p.trust, count(DISTINCT p.path) AS pages, count(c.id) AS pieces, count(e.chunk_id) AS vectors
                                 FROM wiki_pages p LEFT JOIN wiki_chunks c ON c.path = p.path
                                 LEFT JOIN wiki_chunk_embeddings e ON e.chunk_id = c.id GROUP BY p.trust ORDER BY p.trust""").fetchall():
            print(f"{r['trust']:<9} {r['pages']:>5} pages {r['pieces']:>7} pieces {r['vectors']:>7} vectors")
        print(f"queued for a vector: {pg.scalar(conn, 'SELECT count(*) FROM wiki_embedding_queue')}")


TABLES = ("wiki_pages", "wiki_chunks", "wiki_chunk_embeddings", "wiki_meta")  # in the order of their references


def _columns(conn, table: str) -> list[str]:
    return pg.column(conn, "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s ORDER BY ordinal_position", (table,))


def export(path: Path) -> None:
    """The wiki's tables as binary COPY streams in one tar file, with a manifest."""
    import io
    import subprocess
    import tarfile

    commit = subprocess.run(["git", "-C", str(BUNDLE.parent), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    with pg.connection() as conn, conn.transaction(), tarfile.open(path, "w:gz") as tar:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")  # (one snapshot of all four tables)
        manifest = {"embeddings_model": pg.scalar(conn, "SELECT value FROM wiki_meta WHERE key = 'embeddings_model'"),
                    "wiki_commit": commit or None, "scheme": SCHEME, "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "columns": {t: _columns(conn, t) for t in TABLES}, "rows": {}}
        for table in TABLES:
            data = io.BytesIO()
            cols = ", ".join(manifest["columns"][table])
            with conn.cursor().copy(f"COPY (SELECT {cols} FROM {table}) TO STDOUT (FORMAT binary)") as copy:  # noqa: S608 - names from the catalog
                for block in copy:
                    data.write(block)
            manifest["rows"][table] = pg.scalar(conn, f"SELECT count(*) FROM {table}")  # noqa: S608
            info = tarfile.TarInfo(f"{table}.bin")
            info.size = data.tell()
            data.seek(0)
            tar.addfile(info, data)
        raw = json.dumps(manifest, ensure_ascii=False, indent=1).encode()
        info = tarfile.TarInfo("manifest.json")
        info.size = len(raw)
        tar.addfile(info, io.BytesIO(raw))
    print(f"{path}: {', '.join(f'{n} {t}' for t, n in manifest['rows'].items())}; wiki commit {commit[:12] or '?'}; {path.stat().st_size // 1_000_000} MB")


def import_(path: Path) -> None:
    """Replace the wiki's tables with those of an export, in one transaction: the search sees the old wiki or the new one.
    Pieces that came with a vector are not queued for one."""
    import tarfile

    with tarfile.open(path, "r:gz") as tar:
        manifest = json.loads(tar.extractfile("manifest.json").read())
        if manifest["embeddings_model"] != settings.embeddings_model:
            sys.exit(f"the vectors of {path} are of {manifest['embeddings_model']}, this database uses {settings.embeddings_model}")
        started = time.monotonic()
        with pg.connection() as conn, conn.transaction():
            for table in TABLES:
                # (by name: COPY names the columns, and a column added later by ALTER stands last in an older database)
                if set(here := _columns(conn, table)) != set(manifest["columns"][table]):
                    sys.exit(f"{table} has other columns here ({here}) than in {path}: apply db/schema.sql of the same version")
            conn.execute("TRUNCATE wiki_pages, wiki_meta CASCADE")  # (pieces, vectors and the queue go with the pages)
            for table in TABLES:
                cols = ", ".join(manifest["columns"][table])
                # The pieces' ids are generated: they come through a staging table, so that the vectors keep their pieces.
                target = "stage" if table == "wiki_chunks" else table
                if target == "stage":
                    conn.execute("CREATE TEMP TABLE stage (LIKE wiki_chunks) ON COMMIT DROP")
                with conn.cursor().copy(f"COPY {target} ({cols}) FROM STDIN (FORMAT binary)") as copy:  # noqa: S608
                    stream = tar.extractfile(f"{table}.bin")
                    while block := stream.read(1 << 20):
                        copy.write(block)
                if target == "stage":
                    conn.execute(f"INSERT INTO wiki_chunks ({cols}) OVERRIDING SYSTEM VALUE SELECT {cols} FROM stage")  # noqa: S608
                    conn.execute("SELECT setval(pg_get_serial_sequence('wiki_chunks', 'id'), coalesce(max(id), 1)) FROM wiki_chunks")
                print(f"  {table}: {manifest['rows'][table]} rows ({time.monotonic() - started:.0f}s)", flush=True)
            conn.execute("DELETE FROM wiki_embedding_queue q USING wiki_chunk_embeddings e WHERE e.chunk_id = q.chunk_id")
            conn.execute("INSERT INTO wiki_meta (key, value) VALUES ('imported_from', %s) ON CONFLICT (key) DO UPDATE SET value = excluded.value",
                         (manifest["wiki_commit"] or "?",))
    print(f"imported {path} (wiki commit {str(manifest['wiki_commit'])[:12]}) in {time.monotonic() - started:.0f}s")


def main() -> None:
    args = sys.argv[2:]
    if not settings.database_url:
        sys.exit("DATABASE_URL is not set: the index lives in the bot's database")
    try:
        if args[:1] == ["status"]:
            status()
            return
        if args[:1] in (["export"], ["import"]) and len(args) == 2:
            (export if args[0] == "export" else import_)(Path(args[1]))
            return
        started = time.monotonic()
        counts = sync()
        print(", ".join(f"{v} {k}" for k, v in counts.items()) or "nothing to do", f"({time.monotonic() - started:.0f}s)")
        if "--no-embed" not in args:
            print(f"{embed_all()} pieces embedded")
        status()
    finally:
        pg.close()
