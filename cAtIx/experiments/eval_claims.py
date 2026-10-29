"""Can a claim of a knowledge card be checked against the clause it cites: the embedder (cosine), the reranker and an LLM judge.

experiments/claims.jsonl has the triples (claim, paragraph, label), from the cards' own sentences that cite one clause:
  supported        the agent's sentence and the clause it cites (read by hand: the clause says it)
  contradicted     the same sentence with one fact changed by hand (`kind`: negation, number, entity, condition, ...)
  wrong_paragraph  the agent's sentence and the next clause of the same document (`kind: neighbour`), or a clause the
                   agent itself cited wrongly (`kind: agent`)
  added_detail     the supported sentence with one plausible detail its clause does not give, added by hand
                   (`kind: edit`), or the agent's own (`kind: agent`)
A paragraph is a clause with its lists and tables, up to the next clause.

For each method: ROC AUC of supported against each other label (1 = always ranks the true pair higher, 0.5 = chance), and
the paired win rate (how often the original sentence scores higher than its edited one on the same clause, by kind).

With the judge, a sentence its cited clause does not back is looked for in the rest of the document (as WikiChat checks a
claim against what it retrieves, not one citation): the reranker picks the --candidates best clauses, the judge reads them
in that order, and the first that backs it is the new citation. Wanted: a wrong paragraph moved to the clause the sentence
came from (or its copy in the document's other language), a contradicted sentence moved nowhere.

--prompt strict: the judge is told that a detail the paragraph does not give (who, when, how, a name, a system) makes the
sentence not_in_text, so a true sentence with a guessed detail does not pass. --prompt details: the same, and the judge
first lists the sentence's details the paragraph does not give, then answers.

--atomic: the judge's model first splits the sentence into the facts it states, and each fact is judged on its own (and
looked for on its own); the sentence is supported when all its facts are. A clause that backs a part of a sentence then
cannot pass the whole of it.

Usage: uv run python experiments/eval_claims.py [--judge agent|wiki|none] [--atomic] [--prompt plain|strict|details] [--candidates K] [--output scores.jsonl]
"""

import argparse
import json
import math
import re
import statistics
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from catix.settings import settings
from catix.wiki.paths import BUNDLE

DATASET = Path(__file__).with_name("claims.jsonl")
JUDGE_PROMPT = """You check one sentence of a wiki card against the paragraph of the source document it cites.
- "supported": the paragraph states everything the sentence says (other words or another language are fine).
- "contradicted": the paragraph says otherwise on any point: a negation, another number, term or date, another person or
  body, a condition added or dropped, "may" for "must".
- "not_in_text": the paragraph is about something else and does not say it.
Answer with JSON only: {"verdict": "supported" | "contradicted" | "not_in_text"}"""
STRICT_JUDGE_PROMPT = JUDGE_PROMPT.replace(
    '- "not_in_text": the paragraph is about something else and does not say it.',
    '- "not_in_text": the paragraph is about something else and does not say it, or it does not give some detail of the\n'
    "  sentence: who does it, when, how, where, in what system, a name, a number, a condition. A detail that is likely true\n"
    "  but not in the paragraph is not_in_text.")
DETAILS_JUDGE_PROMPT = STRICT_JUDGE_PROMPT.replace(
    'Answer with JSON only: {"verdict"',
    "First list every detail of the sentence that the paragraph does not give (an empty list if there is none), then the\n"
    "verdict. Only the sentence's details count: what the paragraph says and the sentence leaves out is fine, and a term the\n"
    'paragraph defines or uses (a title, a capitalised name) may be spelled out in the sentence. Answer with JSON only: {"absent": ["..."], "verdict"')
MISSING_JUDGE_PROMPT = STRICT_JUDGE_PROMPT.replace(
    'Answer with JSON only: {"verdict"',
    "First list the facts of the sentence that the paragraph does not give anywhere (an empty list if there is none). List\n"
    "only what is missing: not what matches or means the same (a translation, a short name such as \"the University\" for the\n"
    "organisation's full name, a term the paragraph defines, a value in a table's cell), and not what the paragraph says\n"
    "and the sentence leaves out. The verdict is not_in_text when the list is not empty.\n"
    'Answer with JSON only: {"missing": ["..."], "verdict"')
PROMPTS = {"plain": JUDGE_PROMPT, "strict": STRICT_JUDGE_PROMPT, "details": DETAILS_JUDGE_PROMPT, "missing": MISSING_JUDGE_PROMPT}
LISTS = (DETAILS_JUDGE_PROMPT, MISSING_JUDGE_PROMPT)  # the prompts whose answer lists details before the verdict
SPLIT_PROMPT = """Split the sentence of a wiki card into the separate facts it states, one short sentence each, in the
sentence's language. Each fact must be understood alone: name what it is about instead of "it", "the Centre", "this".
Keep every detail of the sentence in some fact: numbers, terms, dates, who decides, conditions, "may" or "must",
negations. Add nothing. A sentence that states one fact stays one fact.
Answer with JSON only: {"facts": ["...", "..."]}"""
VERDICTS = ("supported", "contradicted", "not_in_text")
CLAUSE = re.compile(r"^\*\*([\d.]+?)\.?\*\*.*?(?=\n\*\*\d|\n#|\Z)", re.M | re.S)  # a clause with its lists and tables


def cosine(x: list[float], y: list[float]) -> float:
    return sum(a * b for a, b in zip(x, y, strict=True)) / (math.sqrt(sum(a * a for a in x)) * math.sqrt(sum(b * b for b in y)))


def auc(positives: list[float], negatives: list[float]) -> float:
    """The chance that a random positive scores higher than a random negative (ties count half)."""
    pairs = [(p > n) + 0.5 * (p == n) for p in positives for n in negatives]
    return sum(pairs) / len(pairs) if pairs else float("nan")


def ask(system: str, user: str, wiki: bool, max_tokens: int, thinking: bool = False) -> str:
    route = settings.wiki_llm_route if wiki and settings.wiki_llm_route else settings.llm_route
    body = {
        "model": (settings.wiki_llm_model if wiki else None) or settings.llm_model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    if not (wiki and settings.wiki_llm_route):  # llama.cpp's switch for Qwen's thinking
        body["chat_template_kwargs"] = {"enable_thinking": thinking}
    key = settings.wiki_llm_api_key.get_secret_value() if wiki and settings.wiki_llm_api_key else None
    response = httpx.post(f"{str(route).rstrip('/')}/chat/completions", json=body,
                          headers={"Authorization": f"Bearer {key}"} if key else None, timeout=300)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def judge(claim: str, paragraph: str, wiki: bool, prompt: str = JUDGE_PROMPT) -> str:
    answer = ask(prompt, f"Sentence: {claim}\n\nParagraph:\n{paragraph}", wiki, 400 if prompt in LISTS else 30)
    answer = answer[answer.rfind('"verdict"'):]  # the list of absent details may name a verdict
    return next((verdict for verdict in VERDICTS if verdict in answer), "unparsed")


def split(claim: str, wiki: bool) -> list[str]:
    """The facts of a sentence; the sentence itself if the answer is not a list of them."""
    answer = ask(SPLIT_PROMPT, claim, wiki, 1000)
    try:
        facts = json.loads(answer[answer.find("{"):answer.rfind("}") + 1])["facts"]
    except (ValueError, KeyError, TypeError):
        facts = []
    return [fact for fact in facts if isinstance(fact, str) and fact.strip()] or [claim]


def check(row: dict, atomic: bool, wiki: bool, prompt: str) -> None:
    """The verdict on a sentence: supported if all its facts are, contradicted if any is."""
    row["facts"] = split(row["claim"], wiki) if atomic else [row["claim"]]
    row["fact_verdicts"] = [judge(fact, row["paragraph"], wiki, prompt) for fact in row["facts"]]
    verdicts = set(row["fact_verdicts"])
    row["verdict"] = next(verdict for verdict in ("contradicted", "unparsed", "not_in_text", "supported") if verdict in verdicts)


def clauses(source: str) -> list[tuple[str, str]]:
    """(number, text) of every clause of a document of the wiki, as claims.jsonl cuts them."""
    return [(m.group(1), m.group(0).strip()[:4000]) for m in CLAUSE.finditer((BUNDLE / source.lstrip("/")).read_text(encoding="utf-8"))]


def relocate(row: dict, k: int, wiki: bool, rerank, prompt: str) -> None:
    """For every fact the cited clause does not back, the clause that does among the document's others: the reranker's k
    best, judged in order. The sentence is moved if every such fact found one."""
    others = [clause for clause in clauses(row["source"]) if clause[1] != row["paragraph"]]
    row["candidates"], row["relocated"] = [], []
    for fact, verdict in zip(row["facts"], row["fact_verdicts"], strict=True):
        if verdict == "supported":
            continue
        scores = [score for start in range(0, len(others), 32) for score in rerank(fact, [text for _, text in others[start:start + 32]])]
        top = sorted(range(len(others)), key=scores.__getitem__, reverse=True)[:k]
        row["candidates"].append([others[i][0] for i in top])
        row["relocated"].append(next((others[i][0] for i in top if judge(fact, others[i][1], wiki, prompt) == "supported"), None))
    row["moved"] = None not in row["relocated"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--judge", choices=["agent", "wiki", "none"], default="agent", help="the agent's model, the wiki's, or no judge")
    parser.add_argument("--atomic", action="store_true", help="split every sentence into its facts and judge each")
    parser.add_argument("--prompt", choices=PROMPTS, default="plain", help="the judge's prompt")
    parser.add_argument("--candidates", type=int, default=3, help="clauses of the document to judge when the cited one fails (0: off)")
    parser.add_argument("--output", type=Path, help="every row with its scores, as JSON lines")
    args = parser.parse_args()
    settings.phoenix_endpoint = None
    prompt = PROMPTS[args.prompt]
    from catix.db import pg

    rows = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]
    texts = sorted({text for row in rows for text in (row["claim"], row["paragraph"])})
    vectors = dict(zip(texts, (vector for start in range(0, len(texts), 32) for vector in pg.embed(texts[start:start + 32])), strict=True))
    for row in rows:
        row["cosine"] = cosine(vectors[row["claim"]], vectors[row["paragraph"]])
        row["reranker"] = pg.rerank(row["claim"], [row["paragraph"]])[0]
    methods = ["cosine", "reranker"]
    if args.judge != "none":
        with ThreadPoolExecutor(4) as pool:
            list(pool.map(lambda row: check(row, args.atomic, args.judge == "wiki", prompt), rows))
        for row in rows:
            row["judge"] = float(row["verdict"] == "supported")
        methods.append("judge")
        if args.atomic:
            print(f"facts a sentence: median {statistics.median(len(row['facts']) for row in rows)}, max {max(len(row['facts']) for row in rows)}")

    by_label = defaultdict(list)
    for row in rows:
        by_label[row["label"]].append(row)
    print(f"{len(rows)} rows: " + ", ".join(f"{label} {len(group)}" for label, group in by_label.items()))
    print("\nmedian score by label")
    print(f"{'':10}" + "".join(f"{label:>18}" for label in by_label))
    for method in methods:
        print(f"{method:10}" + "".join(f"{statistics.median(row[method] for row in group):18.3f}" for group in by_label.values()))

    print("\nROC AUC, supported against")
    others = [label for label in by_label if label != "supported"]
    print(f"{'':10}" + "".join(f"{label:>18}" for label in others))
    for method in methods:
        positives = [row[method] for row in by_label["supported"]]
        print(f"{method:10}" + "".join(f"{auc(positives, [row[method] for row in by_label[label]]):18.3f}" for label in others))

    # The original sentence against its edit (same clause) and against the neighbour clause, card by card.
    original = {row["card"]: row for row in by_label["supported"]}
    pairs = [(f"{row['label']}/{row['kind']}", original[row["card"]], row) for row in rows
             if row["label"] != "supported" and row["card"] in original]
    kinds = sorted({kind for kind, _, _ in pairs})
    print("\npaired win rate: the original sentence on its clause scores higher than")
    print(f"{'':10}" + "".join(f"{kind.replace('contradicted/', 'contr/').replace('wrong_paragraph/', 'wrong/'):>17}" for kind in kinds))
    print(f"{'(pairs)':10}" + "".join(f"{sum(k == kind for k, _, _ in pairs):>17}" for kind in kinds))
    for method in methods:
        rates = [statistics.mean((a[method] > b[method]) + 0.5 * (a[method] == b[method]) for k, a, b in pairs if k == kind) for kind in kinds]
        print(f"{method:10}" + "".join(f"{rate:17.2f}" for rate in rates))

    if args.judge != "none":
        print("\njudge verdicts by label")
        print(f"{'':18}" + "".join(f"{verdict:>14}" for verdict in (*VERDICTS, "unparsed")))
        for label, group in by_label.items():
            print(f"{label:18}" + "".join(f"{sum(row['verdict'] == verdict for row in group):14}" for verdict in (*VERDICTS, "unparsed")))

    # The best single threshold for "the sentence is backed by its clause" (supported against everything else).
    # Balanced: the mean of the shares of each side it gets right, as "never supported" alone is right on two rows of three.
    print("\nbest threshold, supported against the rest (balanced accuracy)")
    for method in methods[:2]:
        def balanced(t: float) -> float:
            return statistics.mean(statistics.mean((row[method] >= t) == (row["label"] == "supported") for row in group)
                                   for group in (by_label["supported"], [row for row in rows if row["label"] != "supported"]))
        threshold = max(sorted({row[method] for row in rows}), key=balanced)
        print(f"{method:10} >= {threshold:.3f}: {balanced(threshold):.2f}")
    if args.judge != "none" and args.candidates > 0:
        failed = [row for row in rows if row["verdict"] != "supported"]
        with ThreadPoolExecutor(4) as pool:
            list(pool.map(lambda row: relocate(row, args.candidates, args.judge == "wiki", pg.rerank, prompt), failed))
        # Where a sentence belongs: the clause of its supported row (the same card), by text or by number (the other language).
        home = {row["card"]: row["clause"] for row in by_label["supported"]}
        print(f"\nlooked for in the document, top {args.candidates} clauses by the reranker, when the cited one did not back it")
        print(f"{'':18}{'not backed':>12}{'home in top':>13}{'moved':>8}{'moved home':>12}{'moved elsewhere':>17}")
        for label, group in by_label.items():
            group = [row for row in group if row["verdict"] != "supported"]
            moved = [row for row in group if row["moved"]]
            at_home = [row for row in moved if all(clause == home.get(row["card"]) for clause in row["relocated"])]
            in_top = sum(all(home.get(row["card"]) in top for top in row["candidates"]) for row in group)
            print(f"{label:18}{len(group):12}{in_top:13}{len(moved):8}{len(at_home):12}{len(moved) - len(at_home):17}")
        for row in failed:
            if row["moved"] and not all(clause == home.get(row["card"]) for clause in row["relocated"]):
                print(f"  {row['label']}/{row['kind']}: clause {row['clause']} -> {', '.join(row['relocated'])}: {row['claim'][:100]}")
    if args.output:
        args.output.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


if __name__ == "__main__":
    main()
