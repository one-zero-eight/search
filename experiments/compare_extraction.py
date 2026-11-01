"""The text layers of the regulations read again by opendataloader (regulations.extract) against the text they have now, before
`regs reextract` replaces it: what the cards rest on must stay, and the reading must not lose the documents' words.

For every document read from its text layer, both texts through to_markdown, and:
  cited    the clauses the cards cite (', clause 5.3' / ', п. 5.3' in their Citations) that stand as a clause (**5.3.**)
  quotes   the cards' quotes of the document («...» in their Citations) found in it (agent.find_quote: word for word, or near)
  clauses  the clauses of the document
  words    of the words (4+ letters) of the text now, the share in the new one: a word broken at a line's end now
           ('консор- циума') is not one, and one found among the new text's letters is kept (a half of a word broken with
           no hyphen, 'магист ратуры'; words read with no spaces, 'obtainedfromtheresults')
  breaks   words broken by a hyphen and a space ('научно- технической'), one-column tables ('| 1.1. ... |' frames)
A document the new reading loses a cited clause, a quote or more than WORDS of the words of is listed with what it lost, and
one opendataloader read too little of (regulations.extract reads it by pdfplumber then) is counted apart.

Usage: uv run python experiments/compare_extraction.py [--save DIR] [--only REGEX]   (--save: the new markdown, for reading)
"""

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

from catix.wiki.agent import find_quote
from catix.wiki.paths import BUNDLE, card_folders
from catix.wiki.sources import opendataloader
from catix.wiki.sources.regulations import all_docs, pages_of, to_markdown

WORDS = 0.97
CLAUSE = re.compile(r"^\*\*(\d{1,2}(?:\.\d{1,2}){0,4})\.?\*\*", re.M)
CITED = re.compile(r"^\d+\. \[.*?\]\(/raw/regulations/([^ )#]+)\.md\), (?:clause|п\.) (\d+(?:\.\d+)*)", re.M)
QUOTE = re.compile(r"^\d+\. \[.*?\]\(/raw/regulations/([^ )#]+)\.md\)[^\n«]*?: «(.+)»\s*$", re.M)
BREAK = re.compile(r"[^\W\d_]+- (?!и |или |либо )[^\W\d_]+")
ONE_COLUMN = re.compile(r"^\|\s*-{3}\s*\|$", re.M)
LONG = re.compile(r"[^\W\d_]{4,}")


def card_refs() -> tuple[dict[str, set[str]], dict[str, list[str]]]:
    """Document -> the clauses the cards cite of it, and the quotes they hold of it."""
    clauses: dict[str, set[str]] = {}
    quotes: dict[str, list[str]] = {}
    for folder in card_folders(BUNDLE):
        for card in (BUNDLE / folder).glob("*.md"):
            text = card.read_text(encoding="utf-8")
            for key, number in CITED.findall(text):
                clauses.setdefault(key, set()).add(number)
            for key, quote in QUOTE.findall(text):
                quotes.setdefault(key, []).append(quote)
    return clauses, quotes


def words(md: str) -> Counter:
    return Counter(w.lower() for w in LONG.findall(re.sub(r"[^\W\d_]+- [^\W\d_]+", " ", md)))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", type=Path)
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    docs = {k: d for k, d in all_docs().items() if re.search(args.only, k)}
    todo = []
    for key, d in docs.items():
        meta_path, pdf, txt = d["root"] / f"{key}.json", d["root"] / f"{key}.pdf", d["root"] / f"{key}.txt"
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        if str(meta.get("method", "")).startswith("text layer") and pdf.exists() and txt.exists():
            todo.append((key, pdf, txt))
    cited, quoted = card_refs()
    print(f"{len(todo)} documents read from their text layer; cards cite {sum(map(len, cited.values()))} clauses and hold "
          f"{sum(map(len, quoted.values()))} quotes of them", flush=True)
    start = time.time()
    total, short, worse = Counter(), [], []
    with opendataloader.converted([pdf for _, pdf, _ in todo]) as jsons:
        print(f"converted in {time.time() - start:.0f}s", flush=True)
        for key, pdf, txt in todo:
            new_text = opendataloader.text_of_pdf(pdf, jsons[pdf]) if pdf in jsons else None
            if new_text is None or len(new_text.strip()) <= 300 * pages_of(pdf):
                short.append(key)
                continue
            old, new = to_markdown(txt.read_text(encoding="utf-8")), to_markdown(new_text)
            if args.save:
                args.save.mkdir(parents=True, exist_ok=True)
                (args.save / f"{key}.md").write_text(new, encoding="utf-8")
            old_cl, new_cl = set(CLAUSE.findall(old)), set(CLAUSE.findall(new))
            cites = cited.get(key, set())
            lost_cited = sorted(c for c in cites if c in old_cl and c not in new_cl)
            qs = quoted.get(key, [])
            lost_quotes = [q for q in qs if find_quote(q, old) is not None and find_quote(q, new) is None]
            wo, wn = words(old), words(new)
            letters = re.sub(r"[\W\d_]+", "", new.lower())
            gone = [w for w in wo if w not in wn and w not in letters]
            share = 1 - len(gone) / (len(wo) or 1)
            total.update({"docs": 1, "cited": len([c for c in cites if c in old_cl]), "lost cited": len(lost_cited),
                          "quotes": len(qs), "lost quotes": len(lost_quotes), "clauses old": len(old_cl), "clauses new": len(new_cl),
                          "breaks old": len(BREAK.findall(old)), "breaks new": len(BREAK.findall(new)),
                          "one-column old": len(ONE_COLUMN.findall(old)), "one-column new": len(ONE_COLUMN.findall(new)),
                          "chars old": len(old), "chars new": len(new)})
            if lost_cited or lost_quotes or share < WORDS:
                missing = sorted(gone, key=lambda w: -wo[w])[:12]
                worse.append((key, lost_cited, lost_quotes, share, len(old_cl), len(new_cl), missing))
    t = total
    print(f"\n{t['docs']} documents compared ({time.time() - start:.0f}s); {len(short)} read too little of by opendataloader "
          f"(pdfplumber reads them): {', '.join(short[:10])}{' ...' if len(short) > 10 else ''}")
    print(f"cited clauses kept {t['cited'] - t['lost cited']}/{t['cited']}, quotes kept {t['quotes'] - t['lost quotes']}/{t['quotes']}")
    print(f"clauses {t['clauses old']} -> {t['clauses new']}, broken words {t['breaks old']} -> {t['breaks new']}, "
          f"one-column tables {t['one-column old']} -> {t['one-column new']}, characters {t['chars old']} -> {t['chars new']}")
    print(f"\n{len(worse)} documents lose something:")
    for key, lost_cited, lost_quotes, share, n_old, n_new, missing in sorted(worse, key=lambda w: (-len(w[1]) - len(w[2]), w[3])):
        print(f"  {key}: words {100 * share:.1f}%, clauses {n_old} -> {n_new}"
              + (f", cited clauses lost {lost_cited[:8]}" if lost_cited else "") + (f", quotes lost {len(lost_quotes)}: «{lost_quotes[0][:80]}»" if lost_quotes else "")
              + (f"\n      words gone: {' '.join(missing)}" if share < WORDS else ""))


if __name__ == "__main__":
    sys.exit(main())
