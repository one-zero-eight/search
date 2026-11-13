"""The text layers of the regulations read again by opendataloader (regulations.extract) against the text they have now, before
`regs reextract` replaces it: the reading must not lose the documents' clauses or words.

For every document read from its text layer, both texts through to_markdown, and:
  clauses  the clauses of the document
  words    of the words (4+ letters) of the text now, the share in the new one: a word broken at a line's end now
           ('консор- циума') is not one, and one found among the new text's letters is kept (a half of a word broken with
           no hyphen, 'магист ратуры'; words read with no spaces, 'obtainedfromtheresults')
  breaks   words broken by a hyphen and a space ('научно- технической'), one-column tables ('| 1.1. ... |' frames)
A document the new reading loses more than WORDS of the words of is listed with what it lost, and
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

from catix.wiki.sources import opendataloader
from catix.wiki.sources.regulations import all_docs, pages_of, to_markdown

WORDS = 0.97
CLAUSE = re.compile(r"^\*\*(\d{1,2}(?:\.\d{1,2}){0,4})\.?\*\*", re.M)
BREAK = re.compile(r"[^\W\d_]+- (?!и |или |либо )[^\W\d_]+")
ONE_COLUMN = re.compile(r"^\|\s*-{3}\s*\|$", re.M)
LONG = re.compile(r"[^\W\d_]{4,}")


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
    print(f"{len(todo)} documents read from their text layer", flush=True)
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
            wo, wn = words(old), words(new)
            letters = re.sub(r"[\W\d_]+", "", new.lower())
            gone = [w for w in wo if w not in wn and w not in letters]
            share = 1 - len(gone) / (len(wo) or 1)
            total.update({"docs": 1, "clauses old": len(old_cl), "clauses new": len(new_cl),
                          "breaks old": len(BREAK.findall(old)), "breaks new": len(BREAK.findall(new)),
                          "one-column old": len(ONE_COLUMN.findall(old)), "one-column new": len(ONE_COLUMN.findall(new)),
                          "chars old": len(old), "chars new": len(new)})
            if share < WORDS or new_cl < old_cl:
                missing = sorted(gone, key=lambda w: -wo[w])[:12]
                worse.append((key, sorted(old_cl - new_cl), share, len(old_cl), len(new_cl), missing))
    t = total
    print(f"\n{t['docs']} documents compared ({time.time() - start:.0f}s); {len(short)} read too little of by opendataloader "
          f"(pdfplumber reads them): {', '.join(short[:10])}{' ...' if len(short) > 10 else ''}")
    print(f"clauses {t['clauses old']} -> {t['clauses new']}, broken words {t['breaks old']} -> {t['breaks new']}, "
          f"one-column tables {t['one-column old']} -> {t['one-column new']}, characters {t['chars old']} -> {t['chars new']}")
    print(f"\n{len(worse)} documents lose something:")
    for key, lost, share, n_old, n_new, missing in sorted(worse, key=lambda w: (-len(w[1]), w[2])):
        print(f"  {key}: words {100 * share:.1f}%, clauses {n_old} -> {n_new}"
              + (f", clauses lost {lost[:8]}" if lost else "")
              + (f"\n      words gone: {' '.join(missing)}" if share < WORDS else ""))


if __name__ == "__main__":
    sys.exit(main())
