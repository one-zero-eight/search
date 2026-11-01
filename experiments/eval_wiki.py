"""How well the agent's wiki search finds the piece that answers a question (catix/db/wiki.py).

Questions of every kind of reader (student, postgraduate, applicant, teacher/staff, management/public), worded as a person
would ask, not as the document says. A piece is relevant when its page (path or title) matches `page` and its text (with the title and headings) matches `text` (both
regexes, case-insensitive), picked by reading the documents. Methods: words only, meaning only, both fused, both fused and
reranked (what search_wiki does). Small sample: read the per-question table, not only the averages.

Usage: uv run python experiments/eval_wiki.py [--check]   (--check: only count the relevant pieces of each question)
"""

import re
import statistics
import sys
import time

from catix.db import pg
from catix.db import store
from catix.db import wiki
from catix.wiki import quality

TOP = 10

QUESTIONS = quality.QUESTIONS  # (reader, question, page regex, text regex): src/catix/wiki/quality.py
relevant = quality.relevant


def main() -> None:
    conn = pg.connect()
    if "--check" in sys.argv:
        for reader, q, page, text in QUESTIONS:
            n = len(relevant(conn, page, text))
            print(f"{n:>4}  {reader:<12} {q}")
        return
    pg.embed(["warm-up"])
    trust = list(wiki.TRUST)
    methods = {
        "words": lambda q: wiki._bm25(store._words(q), trust)[:TOP],
        "meaning": lambda q: wiki._vector(pg.embed([q])[0], trust)[:TOP],
        "fused": lambda q: store._combine([store._rrf(wiki._bm25(store._words(q), trust), wiki._vector(pg.embed([q])[0], trust))], TOP),
        "reranked": lambda q: [h.id for h in wiki.search([q], limit=TOP)],
    }
    ranks = {m: [] for m in methods}
    times = {m: [] for m in methods}
    by_reader: dict[str, dict[str, list]] = {}
    print(f"{'reader':<12} {'question':<70} rel | first relevant rank ({' / '.join(methods)})")
    for reader, q, page, text in QUESTIONS:
        rel = relevant(conn, page, text)
        cells = []
        for name, fn in methods.items():
            started = time.perf_counter()
            result = fn(q)
            times[name].append(time.perf_counter() - started)
            first = next((i for i, x in enumerate(result, 1) if x in rel.ids or x in rel.mains), None)  # (ids: no list of copies to check)
            ranks[name].append(first)
            by_reader.setdefault(reader, {m: [] for m in methods})[name].append(first)
            cells.append(f"{first:>2}" if first else " -")
        print(f"{reader:<12} {q[:70]:<70} {len(rel):>3} | " + " / ".join(cells))

    def stats(firsts: list) -> str:
        n = len(firsts)
        return (f"{sum(1 for f in firsts if f and f <= 5) / n:>6.0%} {sum(1 for f in firsts if f) / n:>7.0%} "
                f"{sum(1 / f for f in firsts if f) / n:>7.2f}")

    print(f"\n{'method':<10} {'hit@5':>6} {'hit@10':>7} {'MRR':>7} {'median s':>9}")
    for name in methods:
        print(f"{name:<10} {stats(ranks[name])} {statistics.median(times[name]):>9.2f}")
    print(f"\n{'reader':<12} {'n':>3}  hit@5 / hit@10 / MRR of 'reranked'")
    for reader, per in by_reader.items():
        print(f"{reader:<12} {len(per['reranked']):>3}  {stats(per['reranked'])}")
    pg.close()


if __name__ == "__main__":
    main()
