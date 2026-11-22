"""Rerankers compared on the candidates the wiki's search gives its reranker, for quality and for response time.

Two steps, so that the models can be tried on another machine than the database:
  capture  (needs the database and the embedder): for every question of wiki_questions.jsonl the pieces the hybrid search
           hands to the reranker (what docs._rerank builds), and which of them hold the answer -> a JSON file.
  run      (needs only the reranker's HTTP route): scores those candidates with one reranker, times every request ->
           a JSON file per model.
  report   the files of several models side by side: hit@k, MRR, nDCG@10 with intervals, latency percentiles.

Usage:
  uv run python experiments/bench_rerankers.py capture OUT.json
  python experiments/bench_rerankers.py run CANDIDATES.json ROUTE MODEL OUT.json [--workers N] [--max-chars N]
  python experiments/bench_rerankers.py report RESULT.json ...
"""

import json
import math
import random
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

TOP = 10


def capture(out: str) -> None:
    sys.path.insert(0, str(Path(__file__).parent))
    from catix.db import docs as doc_store, pg
    from catix.settings import settings
    from gen_wiki_questions import OUT, relevant

    seen: list[dict] = []

    def record(queries, hits, limit):  # instead of the reranker: keep what it would be given
        seen.append({"documents": [f"{h.title}\n{h.heading}\n{h.text[:settings.rerank_max_chars]}" for h in hits], "ids": [h.id for h in hits], "hits": hits})
        return hits[:limit]

    doc_store._rerank = record
    conn = pg.connect()
    rows = []
    for line in Path(OUT).read_text().splitlines():
        q = json.loads(line)
        rel = relevant(conn, q["answer"])
        seen.clear()
        doc_store.search([q["question"]], limit=TOP)
        if not seen:
            continue
        rows.append({"question": q["question"], "language": q["language"], "reader": q["reader"],
                     "documents": seen[0]["documents"], "ids": seen[0]["ids"], "relevant": [h in rel for h in seen[0]["hits"]]})
    pg.close()
    Path(out).write_text(json.dumps(rows, ensure_ascii=False))
    answered = sum(any(r["relevant"]) for r in rows)
    print(f"{len(rows)} questions, {answered} with a relevant piece among the candidates, "
          f"{statistics.mean(len(r['documents']) for r in rows):.1f} candidates on average -> {out}")


def run(candidates: str, route: str, model: str, out: str, workers: int = 1, max_chars: int | None = None) -> None:
    import httpx

    rows = json.loads(Path(candidates).read_text())
    client = httpx.Client(timeout=300)

    def score(row, documents):
        started = time.perf_counter()
        response = client.post(f"{route.rstrip('/')}/rerank", json={"model": model, "query": row["question"], "documents": documents})
        response.raise_for_status()
        seconds = time.perf_counter() - started
        results = sorted(response.json()["results"], key=lambda item: item["index"])
        assert [r["index"] for r in results] == list(range(len(documents))), "every document must be scored once"
        return [r["relevance_score"] for r in results], seconds

    def one(row):
        documents = [d[:max_chars] for d in row["documents"]] if max_chars else row["documents"]
        return score(row, documents)

    one(rows[0])  # warm-up: kernels, caches
    one(rows[0])
    started = time.perf_counter()
    with ThreadPoolExecutor(workers) as pool:
        done = list(pool.map(one, rows))
    wall = time.perf_counter() - started
    Path(out).write_text(json.dumps({
        "model": __import__("os").environ.get("LABEL", model), "workers": workers, "max_chars": max_chars, "wall": wall,
        "scores": [s for s, _ in done], "seconds": [t for _, t in done],
    }))
    print(f"{model}: {len(rows)} requests, {wall:.1f}s wall, median {statistics.median(t for _, t in done) * 1000:.0f} ms -> {out}")


def first_relevant(scores: list[float], relevant: list[bool]) -> int | None:
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    return next((rank for rank, i in enumerate(order, 1) if relevant[i]), None)


def ndcg(scores: list[float], relevant: list[bool], k: int = TOP) -> float:
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
    gain = sum(1 / math.log2(rank + 1) for rank, i in enumerate(order, 1) if relevant[i])
    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, min(k, sum(relevant)) + 1))
    return gain / ideal if ideal else 0.0


def interval(values: list[float], draws: int = 2000) -> tuple[float, float]:
    rng = random.Random(0)
    means = sorted(sum(rng.choice(values) for _ in values) / len(values) for _ in range(draws))
    return means[int(draws * 0.025)], means[int(draws * 0.975)]


def report(candidates: str, files: list[str]) -> None:
    rows = json.loads(Path(candidates).read_text())
    rows_ok = [i for i, r in enumerate(rows) if any(r["relevant"])]  # a question whose answer is not among the candidates says nothing
    print(f"{len(rows)} questions, {len(rows_ok)} with a relevant piece among the candidates (only these are scored)\n")
    systems = {"hybrid order (no reranker)": [[-i for i in range(len(r["documents"]))] for r in rows]}
    meta = {}
    for f in files:
        data = json.loads(Path(f).read_text())
        systems[data["model"]] = data["scores"]
        meta[data["model"]] = data
    header = f"{'model':<44}" + "".join(f"{c:>17}" for c in ("hit@1", "hit@3", "hit@5", "MRR", "nDCG@10"))
    print(header)
    firsts = {}
    for name, scores in systems.items():
        firsts[name] = [first_relevant(scores[i], rows[i]["relevant"]) for i in rows_ok]
        cells = []
        for k in (1, 3, 5):
            hits = [1.0 if f and f <= k else 0.0 for f in firsts[name]]
            lo, hi = interval(hits)
            cells.append(f"{sum(hits) / len(hits):>5.0%} [{lo:.0%}-{hi:.0%}]")
        mrr = [1 / f if f else 0.0 for f in firsts[name]]
        nd = [ndcg(scores[i], rows[i]["relevant"]) for i in rows_ok]
        cells.append(f"{sum(mrr) / len(mrr):>9.3f}")
        cells.append(f"{sum(nd) / len(nd):>9.3f}")
        print(f"{name:<44}" + "".join(f"{c:>17}" for c in cells))
    print("\nby language, hit@5 / MRR:")
    for language in sorted({r["language"] for r in rows}):
        idx = [n for n, i in enumerate(rows_ok) if rows[i]["language"] == language]
        out = [f"  {language:<10} n={len(idx):<4}"]
        for name in systems:
            f = [firsts[name][n] for n in idx]
            out.append(f"{name.split('/')[-1][:22]}: {sum(1 for x in f if x and x <= 5) / len(f):.0%}/{sum(1 / x if x else 0 for x in f) / len(f):.3f}")
        print("  ".join(out))
    names = list(meta)
    if names:
        print("\nresponse time of one request (one question's candidates):")
        print(f"{'model':<44}{'workers':>8}{'mean':>9}{'p50':>9}{'p95':>9}{'max':>9}{'req/s':>8}   ms")
        for name in names:
            d = meta[name]
            ms = sorted(t * 1000 for t in d["seconds"])
            p95 = ms[min(len(ms) - 1, int(len(ms) * 0.95))]
            print(f"{name:<44}{d['workers']:>8}{statistics.mean(ms):>9.0f}{statistics.median(ms):>9.0f}{p95:>9.0f}{ms[-1]:>9.0f}{len(ms) / d['wall']:>8.1f}")
        print("\npaired: questions where the top 5 differs (A only / B only):")
        for a in range(len(names)):
            for b in range(a + 1, len(names)):
                fa, fb = firsts[names[a]], firsts[names[b]]
                oa = sum(1 for x, y in zip(fa, fb) if (x and x <= 5) and not (y and y <= 5))
                ob = sum(1 for x, y in zip(fa, fb) if (y and y <= 5) and not (x and x <= 5))
                print(f"  {names[a]} vs {names[b]}: {oa} / {ob}")


if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    if cmd == "capture":
        capture(args[0])
    elif cmd == "run":
        opts = {args[i][2:].replace("-", "_"): int(args[i + 1]) for i in range(len(args)) if args[i].startswith("--")}
        pos = [a for i, a in enumerate(args) if not a.startswith("--") and not (i and args[i - 1].startswith("--"))]
        run(*pos, **opts)
    elif cmd == "report":
        report(args[0], args[1:])
