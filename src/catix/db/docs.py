"""Search in the documents of the store (what `catix-docs` builds from the sources): the same hybrid search as for chat
messages (store.py), over the pieces of the pages.

Every query is searched by words (BM25, Russian and English stemmers) and by meaning (bge-m3); the rankings are fused,
the queries combined, and the reranker, when there is one, orders the candidates against the queries. The title of the
page and the headings are part of what is searched, so "5.3. The term is ..." is found by the name of its regulation too.
"""

import logging
import re
from collections.abc import Collection, Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from datetime import date

from catix.agent import tracing
from catix.db import pg
from catix.db.store import MAX_QUERIES, _combine, _embed_all, _rrf, _words
from catix.settings import settings

log = logging.getLogger("catix.docs")

TRUST = ("official", "wiki")
STATUSES = ("current", "outdated", "unlisted")  # of a document: in force, stale_after has passed, or no page of its site links it any more


def years_between(start: date | None, end: date | None) -> frozenset[int]:
    """The years from `start` to `end` (either may be missing: then the other's year alone); empty without both."""
    if not start and not end:
        return frozenset()
    return frozenset(range((start or end).year, (end or start).year + 1))


@dataclass(frozen=True)
class Filters:
    """What a search keeps of the documents, by what is known of the document itself. `status`: 'current' (not unlisted, not
    past its stale_after), 'outdated' (past it) or 'unlisted'; `issued_from`/`issued_to`: the day the document was issued, a
    document with no date is left out when either is given; `site`: where it comes from ('hotel', 'university', 'eduwiki').
    `cohorts`: the intakes asked for; a course programme of another intake is left out.
    `newest_programmes`: without `cohorts`, only the newest intake's programme of each course is kept.
    `latest_versions`: a version of a document that a later one of its series replaces is left out, unless `asked_years` (the
    years of the dates asked for) holds its year."""

    status: str | None = None
    issued_from: date | None = None
    issued_to: date | None = None
    site: str | None = None
    cohorts: frozenset[int] = frozenset()
    newest_programmes: bool = False
    latest_versions: bool = False
    asked_years: frozenset[int] = frozenset()

    def __post_init__(self) -> None:
        if self.status is not None and self.status not in STATUSES:
            raise ValueError(f"status is one of {', '.join(STATUSES)}")

    def clause(self, column: str = "path") -> tuple[str, dict]:
        """(SQL to append to a WHERE, its parameters): the pieces whose document passes."""
        where = []
        if self.status == "current":
            where.append("status IS DISTINCT FROM 'unlisted' AND (stale_after IS NULL OR stale_after > current_date)")
        elif self.status == "outdated":
            where.append("status IS DISTINCT FROM 'unlisted' AND stale_after <= current_date")
        elif self.status == "unlisted":
            where.append("status = 'unlisted'")
        params: dict = {}
        if self.issued_from or self.issued_to:
            # A course programme has its intake in its meta: the dates choose the intake (`cohorts`), not its `issued`.
            programme = "(path LIKE %(f_courses)s AND meta ? 'cohort')"
            params["f_courses"] = COURSES
        if self.issued_from:
            where.append(f"({programme} OR issued >= %(f_from)s)")
            params["f_from"] = self.issued_from
        if self.issued_to:
            where.append(f"({programme} OR issued <= %(f_to)s)")
            params["f_to"] = self.issued_to
        if self.site:
            where.append("site = %(f_site)s")
            params["f_site"] = self.site
        if self.cohorts:
            where.append("NOT (path LIKE %(f_courses)s AND meta ? 'cohort' AND NOT ((meta->>'cohort')::int = ANY(%(f_cohorts)s)))")
            params["f_cohorts"] = sorted(self.cohorts)
            params["f_courses"] = COURSES
        elif self.newest_programmes:
            where.append("(NOT (path LIKE %(f_courses)s AND meta ? 'cohort') OR substring(title from '«([^»]+)»') IS NULL "
                         "OR (substring(title from '«([^»]+)»'), (meta->>'cohort')::int) IN (SELECT substring(o.title from '«([^»]+)»'), "
                         "max((o.meta->>'cohort')::int) FROM documents o WHERE o.path LIKE %(f_courses)s AND o.meta ? 'cohort' GROUP BY 1))")
            params["f_courses"] = COURSES
        if self.latest_versions:
            where.append("NOT (d.series IS NOT NULL AND NOT (d.academic_year = ANY(%(f_years)s)) "
                         "AND EXISTS (SELECT 1 FROM documents n WHERE n.series = d.series AND n.trust = 'official' AND n.academic_year > d.academic_year))")
            params["f_years"] = sorted(self.asked_years)
        return (f" AND {column} IN (SELECT d.path FROM documents d WHERE {' AND '.join(where)})" if where else ""), params

    def pieces(self, alias: str = "") -> tuple[str, dict]:
        """(SQL to append to a WHERE over document_chunks, its parameters): the pieces searched. A copy of a text (copy_of,
        docs/store.py mark_copies) is searched only when the piece it is a copy of is left out by the filters: the programme of
        an older intake has the same paragraph as the newest one, and a search for that intake must find it."""
        where, params = self.clause(f"{alias}path")
        if not where:
            return f" AND {alias}copy_of IS NULL", params
        main, _ = self.clause("m.path")
        return f"{where} AND NOT EXISTS (SELECT 1 FROM document_chunks m WHERE m.id = {alias}copy_of{main})", params  # (none for a main: no copy_of)


@dataclass
class DocHit:
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
    based_on: list[dict] = field(default_factory=list)  # the pages a piece cites, with their titles and originals (from `cites`)
    newer: str | None = None  # the title of a later version of the document ("на 2026/2027 учебный год" for one of 2024/2025)
    relevance: float | None = None  # its second best score of the reranker over the queries, from _rerank (as store.MessageHit)
    page_sha: str = ""  # the indexed page revision, not the chunk's text hash
    copy_of: int | None = None  # the piece this one is a copy of (docs/store.py mark_copies); set only when its main was filtered out
    archive_member: str | None = None  # the PDF in the archive the page was read from, for the preview
    archive_sha256: str | None = None  # the full digest of that member
    issued_precision: str | None = None  # 'year' when only the year of the date is known (from a title or a file name)


# The course programmes (docs/sources/rpd.py) are 700 pages of the same shape that use every word of study ("курс", "дисциплина",
# "зачет"): searched together with the rest they took the candidates of the regulations (the rules of credit transfer
# fell out of the first ten). They are a pool of their own; both pools give candidates, the reranker orders them together.
COURSES = "course-programmes/%"
POOLS = (False, True)  # (not course programmes, course programmes)
COURSE_PROGRAMMES_SHOWN = 3  # course-programme pieces among the results at most while other candidates remain: 8 programmes of one course from other programmes and intakes pushed out the course's eduwiki page with its grade breakdown (2026-11-27)


def demote_course_programmes(order: list[int], hits: Sequence) -> list[int]:
    """`order` (indexes of `hits`) with the course-programme pieces after the COURSE_PROGRAMMES_SHOWN-th moved to the end."""
    kept, moved, seen = [], [], 0
    for i in order:
        if isinstance(hits[i], DocHit) and hits[i].path.startswith("course-programmes/"):
            seen += 1
            (kept if seen <= COURSE_PROGRAMMES_SHOWN else moved).append(i)
        else:
            kept.append(i)
    return kept + moved


def _bm25(words: str, trust: list[str], courses: bool = False, filters: Filters | None = None) -> list[int]:
    where, more = (filters or Filters()).pieces()
    with tracing.span("bm25 course programmes" if courses else "bm25", "RETRIEVER", input=words) as done, pg.connection() as conn:
        found = pg.column(
            conn,
            f"""SELECT id FROM document_chunks
               WHERE (search_text ||| %(q)s OR search_text::pdb.alias('search_text_en') ||| %(q)s) AND trust = ANY(%(t)s)
                 AND (path LIKE %(c)s) = %(courses)s{where}
               ORDER BY pdb.score(id) DESC LIMIT %(n)s""",
            {"q": words, "t": trust, "n": settings.docs_search_candidates, "c": COURSES, "courses": courses, **more},
        )
        done(len(found))
        return found


def _vector(vector: list[float], trust: list[str], courses: bool = False, filters: Filters | None = None) -> list[int]:
    where, more = (filters or Filters()).pieces("c.")
    with tracing.span("vector course programmes" if courses else "vector", "RETRIEVER") as done, pg.connection() as conn, conn.transaction():
        if pg.scalar(conn, "SELECT value FROM docs_meta WHERE key='embeddings_model'") != settings.embeddings_model:
            log.warning("Skipping wiki vectors whose model does not match EMBEDDINGS_MODEL")
            return []
        conn.execute("SET LOCAL hnsw.iterative_scan = strict_order")
        # The default 40 found 0 to 2 of the true 30 nearest pieces once a filter left out the course programmes (measured
        # against an exact scan, 88k pieces); 200 finds 29-30 of them in under 10 ms.
        conn.execute("SELECT set_config('hnsw.ef_search', %s, true)", (str(settings.search_ef),))
        found = pg.column(
            conn,
            f"""SELECT e.chunk_id FROM document_chunk_embeddings e JOIN document_chunks c ON c.id = e.chunk_id
               WHERE c.trust = ANY(%(t)s) AND (c.path LIKE %(c)s) = %(courses)s{where} ORDER BY e.embedding <=> %(v)s::vector LIMIT %(n)s""",
            {"v": vector, "t": trust, "n": settings.docs_search_candidates, "c": COURSES, "courses": courses, **more},
        )
        done(len(found))
        return found


HIT = """SELECT c.id, c.path, c.seq, c.heading, c.clause, c.sha, c.text, c.cites, c.copy_of, p.title, p.type, p.trust, p.audience, p.resource,
                p.status, p.review, p.source_warning, p.stale_after, p.issued, p.sha AS page_sha,
                p.meta->>'archive_member' AS archive_member, p.meta->>'archive_sha256' AS archive_sha256,
                p.meta->>'issued_precision' AS issued_precision,
                (SELECT n.title FROM documents n WHERE n.series = p.series AND n.trust = 'official' AND n.academic_year > p.academic_year
                 ORDER BY n.academic_year DESC, n.path LIMIT 1) AS newer
         FROM document_chunks c JOIN documents p ON p.path = c.path"""


def _hits(ids: list[int], queries: list[str] = (), filters: Filters | None = None) -> list[DocHit]:
    with pg.connection() as conn:
        rows = pg.rows(conn, DocHit, HIT + " WHERE c.id = ANY(%s::bigint[])", (ids,))
    by_id = {r.id: r for r in rows}
    hits, seen, mains = [], set(), set()
    for i in ids:
        # The same document is often published twice (two links to one file): its pieces are the same text, shown once.
        # So are two copies of one main, found once the main is filtered out.
        if i in by_id and by_id[i].sha not in seen and not (by_id[i].copy_of and by_id[i].copy_of in mains):
            seen.add(by_id[i].sha)
            if by_id[i].copy_of:
                mains.add(by_id[i].copy_of)
            hits.append(by_id[i])
    _resolve_cites(hits)
    return _copies(hits, queries, filters)


def course_of(path: str, title: str) -> str | None:
    """The course a course programme is of ('Операционные системы'), the same for every intake and programme."""
    return (m.group(1) if (m := re.search(r"«([^»]+)»", title)) else title) if path.startswith("course-programmes/") else None


def _copies(hits: list[DocHit], queries: list[str] = (), filters: Filters | None = None) -> list[DocHit]:
    """The search finds one piece of a text that several pages hold. When the title of another of them that passes the
    filters has more of the queries' words (the course asked about), that one is given instead."""
    group = {h.id: h.copy_of or h.id for h in hits}
    more, params = (filters or Filters()).clause("p.path")
    with pg.connection() as conn:
        rows = conn.execute("SELECT DISTINCT ON (p.path, c.copy_of) c.id, c.copy_of, p.title, p.path FROM document_chunks c "
                            f"JOIN documents p ON p.path = c.path WHERE c.copy_of = ANY(%(ids)s::bigint[]){more} "
                            "ORDER BY p.path, c.copy_of, c.seq", {"ids": list(set(group.values())), **params}).fetchall()
    if not rows:
        return hits
    stems = {w[:5] for w in re.findall(r"[^\W\d_]{4,}", " ".join(queries).lower())}
    named = lambda title: sum(w[:5] in stems for w in set(re.findall(r"[^\W\d_]{4,}", title.lower())))  # noqa: E731
    others: dict[int, list[dict]] = {}
    for r in sorted(rows, key=lambda r: (-named(r["title"]), r["title"])):
        others.setdefault(r["copy_of"], []).append(r)
    swap = {h.id: others[group[h.id]][0]["id"] for h in hits if group[h.id] in others
            and others[group[h.id]][0]["id"] != h.id and named(others[group[h.id]][0]["title"]) > named(h.title)}
    if swap:
        with pg.connection() as conn:
            copies = {c.id: c for c in pg.rows(conn, DocHit, HIT + " WHERE c.id = ANY(%s::bigint[])", (list(swap.values()),))}
    out = []
    for h in hits:
        shown = copies[swap[h.id]] if h.id in swap else h
        if h.id in swap:  # (what the found piece carried: the pages it cites, a later version)
            shown.based_on = h.based_on
        out.append(shown)
    return out


ACADEMIC_YEAR = re.compile(r"(\d{4})\s*/\s*\d{4}")


def _own_title(title: str) -> str:
    """The document's own title, the last part with an academic year: a page of the university's site names its section
    first ("Информация о приеме на 2026/27 учебный год … — ПРАВИЛА ПРИЕМА … НА 2026/2027 УЧЕБНЫЙ ГОД"), and the version of
    another year may be in another section or in none. With the section the versions were not of one series, and the rules
    of 2024/2025 were cited for a master's admission as if they were the current ones."""
    parts = [part for part in title.split(" — ") if ACADEMIC_YEAR.search(part)]
    if not parts or len(_words_of(ACADEMIC_YEAR.sub(" ", parts[-1]))) < 4:
        return title  # ("Список работников … — В 2021/2022 учебном году": the part with the year names no document)
    return parts[-1]


def _words_of(text: str) -> list[str]:
    return re.sub(r"[^а-яёa-z0-9.]+", " ", re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", text.lower())).split()


def academic_year_of(title: str) -> int | None:
    """The first year of the academic year a document is for ("на 2026/2027 учебный год": 2026)."""
    found = ACADEMIC_YEAR.search(_own_title(title))
    return int(found.group(1)) if found else None


def series_of(title: str) -> str | None:
    """What stays of a document's own title without its academic year: the admission rules of every year have one. Only
    titles with an academic year make a series; "Учебный план" or "Приказ о зачислении" name different documents of
    different programmes."""
    title = _own_title(title)
    if not ACADEMIC_YEAR.search(title):
        return None
    return " ".join(_words_of(ACADEMIC_YEAR.sub(" ", title)))


def _resolve_cites(hits: list[DocHit]) -> None:
    """A guide's piece says which pages its [n] point to: give each its title and original, so that the answer can cite them."""
    paths = {c["href"] for h in hits for c in h.cites if str(c.get("href", "")).startswith("/")}
    if not paths:
        return
    with pg.connection() as conn:
        pages = {r["path"]: r for r in conn.execute("SELECT path, title, resource, trust FROM documents WHERE path = ANY(%s)", (list(paths),)).fetchall()}
    for h in hits:
        seen = set()
        for c in h.cites:
            page = pages.get(c.get("href"))
            if page and page["path"] not in seen:
                seen.add(page["path"])
                h.based_on.append({"page": page["path"], "title": page["title"], "link": page["resource"], "trust": page["trust"]})


def search(queries: str | list[str], *, trust: Collection[str] | None = None, limit: int = 8, original: str | None = None,
           rerank: bool = True, filters: Filters | None = None) -> list[DocHit]:
    """The `limit` pieces that answer the queries best. `trust` keeps only some kinds of pages (official, wiki); `filters` only
    the documents that pass (Filters: status, date, site).
    `original` is the user's own question: one more angle that counts double (as in store.search). `rerank=False` returns
    the whole pool of candidates unscored, for a rerank over several sources together (db/rerank.py)."""
    if isinstance(queries, str):
        queries = [queries]
    queries = [q for q in dict.fromkeys(q.strip() for q in queries if q.strip()) if _words(q)][:MAX_QUERIES]
    original = (original or "").strip()
    if original and _words(original):
        queries = [original, *[q for q in queries if q != original]]
    else:
        original = ""
    kinds = [t for t in (trust or TRUST) if t in TRUST]
    if not queries or not kinds or limit <= 0:
        return []
    filters = filters or Filters()
    filters = replace(filters, latest_versions=True, asked_years=years_between(filters.issued_from, filters.issued_to))
    vectors = _embed_all(queries)
    with tracing.span("hybrid", "RETRIEVER", input=queries), ThreadPoolExecutor(max_workers=4) as executor:
        jobs = [(i, executor.submit(tracing.carry(_bm25), _words(q), kinds, pool, filters),
                 executor.submit(tracing.carry(_vector), vectors[i], kinds, pool, filters) if vectors else None)
                for i, q in enumerate(queries) for pool in POOLS]
        per_query = [{item: (2 if original and i == 0 else 1) * value for item, value in _rrf(*[job.result() for job in pair if job]).items()}
                     for i, *pair in jobs]
    per_query = [scores for scores in per_query if scores]
    reranking = settings.reranker_route is not None and rerank
    # One reserved hit per query pool (see _combine): an equal share of 30 candidates is the whole list here, because
    # each query comes twice (course programmes and the rest), and the combined score then adds nothing.
    fused = _combine(per_query, max(limit, settings.docs_rerank_candidates) if reranking or not rerank else limit, reserve=1)
    if not fused:
        return []
    with tracing.span("load pieces", input=len(fused)):
        hits = _hits(fused, queries, filters)
    if not rerank:
        return hits
    return _rerank(queries, hits, limit) if reranking else hits[:limit]


def rerank_document(h: DocHit) -> str:
    return f"{h.title}\n{h.heading}\n{h.text[:settings.rerank_max_chars]}"


def freshness(hit) -> float:
    """The factor of a hit's reranker score for its age (settings.docs_freshness_*); 1 for a hit that is not a dated document."""
    issued = getattr(hit, "issued", None)
    if not isinstance(hit, DocHit) or issued is None or hit.path.startswith("sites/"):
        return 1.0
    years = (date.today() - issued).days / 365.25
    return max(settings.docs_freshness_floor, 1 - settings.docs_freshness_rate * max(0.0, years - 1))


def _rerank(queries: list[str], hits: list[DocHit], limit: int) -> list[DocHit]:
    """The `limit` pieces the reranker finds closest to any of the queries (its best score counts), above the cutoff; each
    keeps its second best score as `relevance`, how well two angles agree that it is about the question (see store._rerank)."""
    if not hits or limit <= 0:
        return hits[:limit]
    documents = [rerank_document(h) for h in hits]
    queries = queries[:settings.rerank_queries]
    try:
        with tracing.span("rerank", "RERANKER", input=queries, documents=len(documents)), ThreadPoolExecutor(max_workers=len(queries)) as executor:
            scores = list(executor.map(tracing.carry(lambda q: pg.rerank(q, documents)), queries))
    except Exception:  # noqa: BLE001 - search must keep working without the reranker
        log.warning("reranker server unavailable, keeping the hybrid ranking", exc_info=True)
        return hits[:limit]
    best = [max(per_query[i] for per_query in scores) for i in range(len(hits))]
    ranked = [best[i] * freshness(hits[i]) for i in range(len(hits))]
    order = sorted(range(len(hits)), key=lambda i: ranked[i], reverse=True)
    if settings.rerank_min_score is not None:
        order = [i for i in order if best[i] >= settings.rerank_min_score]
    order = demote_course_programmes(order, hits)[:limit]
    for i, column in enumerate(zip(*scores)):
        hits[i].relevance = sorted(column, reverse=True)[1 if len(column) > 1 else 0]
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


CHAPTERS_SHOWN = 15  # headings of a page given with a search result: the chapters of a regulation fit


def chapters(paths: Iterable[str]) -> dict[str, list[str]]:
    """The headings of each page in their order: its table of contents, as its pieces have it."""
    with pg.connection() as conn:
        rows = conn.execute(
            "SELECT path, heading FROM document_chunks WHERE path = ANY(%s) AND heading <> '' GROUP BY path, heading ORDER BY path, min(seq)",
            (list(paths),),
        ).fetchall()
    out: dict[str, list[str]] = {}
    for row in rows:
        out.setdefault(row["path"], []).append(row["heading"])
    return out


def page(path: str) -> list[DocHit]:
    """All pieces of a page in order; empty if there is no such page."""
    with pg.connection() as conn:
        hits = pg.rows(conn, DocHit, HIT + " WHERE c.path = %s ORDER BY c.seq", (path,))
    _resolve_cites(hits)
    return hits


def has_resource(resource: str) -> bool:
    """Whether a page of the wiki is the copy of the original at `resource`."""
    with pg.connection() as conn:
        return pg.scalar(conn, "SELECT 1 FROM documents WHERE resource = %s LIMIT 1", (resource,)) is not None


def find_page(name: str) -> str | None:
    """A page by its path ('regulations/x', '/raw/regulations/x.md') or, failing that, by words of its title."""
    path = re.sub(r"\.md$", "", name.strip().lstrip("/").removeprefix("raw/"))
    with pg.connection() as conn:
        if pg.scalar(conn, "SELECT path FROM documents WHERE path = %s", (path,)):
            return path
        # The model often drops the folder ('site-university-5f37d92a-pdf'): the last part of the path alone is unique enough.
        if found := pg.scalar(conn, "SELECT path FROM documents WHERE path LIKE %s ORDER BY length(path) LIMIT 1", ("%/" + path,)):
            return found
        return pg.scalar(conn, "SELECT path FROM documents WHERE title ILIKE %s ORDER BY trust = 'official' DESC, length(title) LIMIT 1",
                         (f"%{name.strip()}%",))
