"""Compare message search methods on a small labelled query set.

Methods: (B) BM25 (pg_search), (C) vector (pgvector), (D) the production hybrid, store.search (B + C by RRF).
Queries are worded differently from the messages on purpose; relevant messages are defined by a regex on the
message text, picked by reading the data. Small sample: look at the per-query table, not only the averages.

Usage: uv run python experiments/eval_search.py
"""

import statistics
import time

from catix.common import courses
from catix.db import pg
from catix.db import store

TOP = 10
RRF_K = 60

# (query, regex of the relevant messages)
QUERIES = [
    ("когда мидтерм по компарху", r"midterm по компарч"),
    ("где можно поесть в университете", r"^🍽"),
    ("документы для военкомата", r"военкомат|воинск\w+ уч[её]т|воинской обязанности"),
    ("когда меняют постельное бельё", r"смен\w+ белья|график смены белья"),
    ("настроить интернет на линуксе", r"\mwifi\M"),
    ("хакатон с призовым фондом", r"(hackathon|хакатон).*(prize|призов)|(prize|призов).*(hackathon|хакатон)"),
    ("когда была контрольная по дискретной математике", r"тест по дискретк"),
    ("защита первой ассигны по итп", r"защит\w* ассиг|defen[cs]es? of A1"),
    ("во сколько рекап по линейной алгебре", r"рекап.*агле"),
    ("что делать с физкультурой первокурсникам", r"физическ\w+ культур|спортивных занятий"),
    ("где найти карту университета", r"карта университета"),
]  # fmt: skip

# Exact terms: names, codes, file names. Here lexical search should shine.
LEXICAL_QUERIES = [
    ("GA1", r"GA1"),
    ("Innoglobalhack", r"Innoglobalhack"),
    ("PIN_C10", r"PIN_C10"),
    ("Quizlet графы", r"Quizlet"),
    ("справки Приложение 4", r"Приложение 4"),
    ("Tender Hack Казань", r"Tender ?Hack"),
]  # fmt: skip


def main() -> None:
    import sys

    queries = QUERIES + LEXICAL_QUERIES if "--all" in sys.argv else QUERIES
    conn = pg.connect()
    pg.embed(["warm-up"])

    # The production code paths of store.py: words only, meaning only, and the real hybrid search.
    methods = {
        "B bm25 (words)": lambda q: store._bm25(store._words(q), None, None, None)[:TOP],
        "C vector (meaning)": lambda q: store._vector(pg.embed([q], query=True)[0], None, None, None)[:TOP],
        "D hybrid (store.search)": lambda q: [r.ref_id for r in store.search([q], limit=TOP)],
    }
    ranks = {m: [] for m in methods}
    recalls = {m: [] for m in methods}
    times = {m: [] for m in methods}
    print(f"{'query':<52} relevant | first relevant rank (B / C / D)")
    for query, pattern in queries:
        relevant = {r["id"] for r in conn.execute("SELECT id FROM messages WHERE text ~* %s", (pattern,))}
        if not relevant:
            print(f"{query:<52} NO RELEVANT MESSAGES FOR {pattern!r}, skipped")
            continue
        cells = []
        for name, fn in methods.items():
            started = time.perf_counter()
            result = fn(query)
            times[name].append((time.perf_counter() - started) * 1000)
            first = next((i for i, x in enumerate(result, 1) if x in relevant), None)
            ranks[name].append(first)
            recalls[name].append(len(relevant & set(result)) / min(len(relevant), TOP))
            cells.append(str(first) if first else "-")
        print(f"{query:<52} {len(relevant):>8} | " + " / ".join(f"{c:>2}" for c in cells))

    print(f"\n{'method':<24} {'hit@5':>6} {'MRR@10':>8} {'recall@10':>10} {'median ms':>10}")
    for name in methods:
        n = len(ranks[name])
        hit5 = sum(1 for r in ranks[name] if r and r <= 5) / n
        mrr = sum(1 / r for r in ranks[name] if r) / n
        print(f"{name:<24} {hit5:>6.0%} {mrr:>8.2f} {statistics.mean(recalls[name]):>10.0%} {statistics.median(times[name]):>10.1f}")
    print("(vector and hybrid times include embedding the query on the GPU server)")
    pg.close()


if __name__ == "__main__":
    main()
