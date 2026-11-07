"""The wiki's search on the generated test set (experiments/wiki_questions.jsonl, gen_wiki_questions.py), with how sure each
number is: a 95% interval from resampling the questions, and for two methods the share of questions where they differ.

Methods: the search as it is (search_wiki: hybrid, reranked) and variants of it; a variant is a change made for the run
only (see VARIANTS). Compare two with --diff A B: the questions where one finds the answer in the top 5 and the other not.

Usage: uv run python experiments/eval_wiki_large.py [variant ...] [--diff A B]
"""

import json
import random
import sys
from pathlib import Path

from catix.db import pg, wiki

sys.path.insert(0, str(Path(__file__).parent))
from gen_wiki_questions import OUT, relevant  # noqa: E402

TOP = 10


def pools(other: int):
    """The 30 places for the reranker: `other` for pages that are not course programmes, the rest for those (now 15/15)."""
    original = wiki._combine

    def combine(per_query, limit):
        if len(per_query) % 2:
            return original(per_query, limit)
        top = lambda d, k: sorted(d, key=d.get, reverse=True)[:k]  # noqa: E731
        merged = [{}, {}]  # (the queries' scores of each pool, the best of them)
        for i, scores in enumerate(per_query):
            for item, value in scores.items():
                merged[i % 2][item] = max(value, merged[i % 2].get(item, 0.0))
        chosen = top(merged[0], other)
        chosen += [x for x in top(merged[1], limit) if x not in chosen][:limit - len(chosen)]
        return chosen + [x for x in top(merged[0], limit) if x not in chosen][:limit - len(chosen)]

    wiki._combine = combine


def one_pool():
    """No pools: BM25 and the vector search over all pieces and one RRF, as before the course programmes had a pool of their own."""
    bm25, vector = wiki._bm25, wiki._vector
    everything = lambda sql: sql.replace("AND (path LIKE %(c)s) = %(courses)s", "").replace("AND (c.path LIKE %(c)s) = %(courses)s", "")  # noqa: E731
    real = pg.column
    def column(conn, sql, params=()):
        return real(conn, everything(sql), params)
    wiki._bm25 = lambda words, trust, courses=False: [] if courses else bm25(words, trust)
    wiki._vector = lambda v, trust, courses=False: [] if courses else vector(v, trust)
    wiki.pg.column = column


def with_copies():
    """The copies of a piece searched too (search_index.mark_copies), as before they were marked."""
    real = pg.column
    wiki.pg.column = lambda conn, sql, params=(): real(conn, sql.replace(" AND copy_of IS NULL", "").replace(" AND c.copy_of IS NULL", ""), params)


def one_pool_with_copies():
    one_pool()
    inner = wiki.pg.column
    wiki.pg.column = lambda conn, sql, params=(): inner(conn, sql.replace(" AND copy_of IS NULL", "").replace(" AND c.copy_of IS NULL", ""), params)


VARIANTS = {
    "now": lambda: None,
    "with-copies": with_copies,
    "one-pool-with-copies": one_pool_with_copies,
    "one-pool": one_pool,
    "pools-20-10": lambda: pools(20),
    "pools-25-5": lambda: pools(25),
}


def run(name: str, questions: list[dict], conn) -> list[int | None]:
    saved = wiki._combine, wiki._bm25, wiki._vector, wiki.pg.column
    VARIANTS[name]()
    try:
        firsts = []
        for q in questions:
            hits = wiki.search([q["question"]], limit=TOP)
            firsts.append(next((i for i, h in enumerate(hits, 1) if h in q["rel"]), None))
        return firsts
    finally:
        wiki._combine, wiki._bm25, wiki._vector, wiki.pg.column = saved


def interval(values: list[float], draws: int = 2000) -> tuple[float, float]:
    rng = random.Random(0)
    means = sorted(sum(rng.choice(values) for _ in values) / len(values) for _ in range(draws))
    return means[int(draws * 0.025)], means[int(draws * 0.975)]


def line(name: str, firsts: list) -> str:
    out = [f"{name:<21}"]
    for k in (1, 5, 10):
        hits = [1.0 if f and f <= k else 0.0 for f in firsts]
        lo, hi = interval(hits)
        out.append(f"hit@{k} {sum(hits) / len(hits):>4.0%} [{lo:.0%}–{hi:.0%}]")
    mrr = [1 / f if f else 0.0 for f in firsts]
    out.append(f"MRR {sum(mrr) / len(mrr):.3f}")
    return "  ".join(out)


def main() -> None:
    args = sys.argv[1:]
    diff = args[args.index("--diff") + 1: args.index("--diff") + 3] if "--diff" in args else []
    names = list(dict.fromkeys(a for a in args if a in VARIANTS)) or ["now"]  # (the first is the one broken down)
    def stop(*args, **kwargs):  # search keeps going without the reranker: the numbers would be of another method
        raise SystemExit("the reranker does not answer")
    wiki.log.warning = stop
    conn = pg.connect()
    questions = [json.loads(line) for line in Path(OUT).read_text().splitlines()]
    for q in questions:
        q["rel"] = relevant(conn, q["answer"])
    print(f"{len(questions)} questions ({sum(q['language'] == 'English' for q in questions)} in English)\n")
    results = {name: run(name, questions, conn) for name in names}
    for name, firsts in results.items():
        print(line(name, firsts))
    for group in ("language", "reader"):
        print(f"\nby {group} ({names[0]}):")
        for value in sorted({q[group] for q in questions}):
            subset = [f for f, q in zip(results[names[0]], questions) if q[group] == value]
            print(f"  {value:<12} n={len(subset):<4}" + line("", subset)[21:])
    if diff:
        a, b = diff
        only_a = [q["question"] for q, x, y in zip(questions, results[a], results[b]) if (x and x <= 5) and not (y and y <= 5)]
        only_b = [q["question"] for q, x, y in zip(questions, results[a], results[b]) if (y and y <= 5) and not (x and x <= 5)]
        print(f"\ntop 5 only with {a}: {len(only_a)}; only with {b}: {len(only_b)} (the rest the same)")
        for q in only_a[:10]:
            print(f"  {a}: {q}")
        for q in only_b[:10]:
            print(f"  {b}: {q}")
    pg.close()


if __name__ == "__main__":
    main()
