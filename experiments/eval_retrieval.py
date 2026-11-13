"""The wiki's search on quality.QUESTIONS or a generated set, optionally against a saved wiki.py implementation."""

import argparse
import importlib.util
import json
import re
import statistics
import sys
import time
from pathlib import Path

from catix.settings import settings


def metrics(rows: list[dict], limit: int) -> dict:
    if not rows:
        return {}
    firsts = [next((rank for rank, match in enumerate(row["relevance"][:limit], 1) if match), None) for row in rows]
    return {
        "questions": len(rows),
        "hit@5": statistics.mean(bool(rank and rank <= 5) for rank in firsts),
        f"hit@{limit}": statistics.mean(bool(rank) for rank in firsts),
        f"precision@{limit}": statistics.mean(sum(row["relevance"][:limit]) / limit for row in rows),
        f"mrr@{limit}": statistics.mean(1 / rank if rank else 0 for rank in firsts),
        "median_seconds": statistics.median(row["seconds"] for row in rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--baseline-source", type=Path)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    if args.limit <= 0:
        parser.error("--limit must be positive")
    settings.phoenix_endpoint = None
    from catix.db import pg, wiki
    from catix.wiki.quality import QUESTIONS, relevant

    baseline = None
    if args.baseline_source:
        spec = importlib.util.spec_from_file_location("catix.db.retrieval_baseline", args.baseline_source)
        baseline = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = baseline
        spec.loader.exec_module(baseline)
    questions = [json.loads(line) for line in args.dataset.read_text(encoding="utf-8").splitlines() if line.strip()] if args.dataset else [
        {"reader": reader, "question": question, "page": page, "text": text} for reader, question, page, text in QUESTIONS
    ]
    results = {mode: [] for mode in (["baseline"] if baseline else []) + ["current"]}
    skipped = []
    try:
        for question in questions:
            if args.dataset:
                words = re.findall(r"[^\W_]+", question["answer"].lower().replace("ё", "е"))
                pattern = re.compile(r"[\W_]+".join(re.escape(word) for word in words))
                with pg.connection() as conn:
                    sources = pg.column(conn, "SELECT search_text FROM wiki_chunks WHERE path = %s", (question["source"],))
                labelled = bool(words) and any(pattern.search(text.lower().replace("ё", "е")) for text in sources)
                matches = lambda hit: bool(pattern.search(f"{hit.title}\n{hit.heading}\n{hit.text}".lower().replace("ё", "е")))
            else:
                with pg.connection() as conn:
                    expected = relevant(conn, question["page"], question["text"])
                labelled = bool(len(expected))
                matches = lambda hit: hit in expected
            if not labelled:
                skipped.append(question["question"])
                continue
            firsts = []
            for mode, rows in results.items():
                started = time.monotonic()
                hits = (baseline if mode == "baseline" else wiki).search(question["question"], limit=args.limit)
                relevance = [matches(hit) for hit in hits]
                rows.append({"query": question["question"], "reader": question.get("reader"), "ids": [hit.id for hit in hits],
                             "relevance": relevance, "seconds": time.monotonic() - started})
                firsts.append(next((rank for rank, match in enumerate(relevance, 1) if match), None))
            print(len(next(iter(results.values()))), firsts, question["question"], flush=True)
            args.output.write_text(json.dumps({"results": results, "skipped": skipped}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({mode: metrics(rows, args.limit) for mode, rows in results.items()}, indent=2))
        print("Questions without relevance labels:", skipped)
    finally:
        pg.close()


if __name__ == "__main__":
    main()
