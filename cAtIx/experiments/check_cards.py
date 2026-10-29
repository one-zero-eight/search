"""Every cited sentence of the knowledge cards checked against what it cites: the numbers by code, the meaning by the judge.

A document is cut into parts that cover all its text: its clauses (with their lists and tables; a number the PDF's
conversion bolded inside a sentence goes on with its clause) and the text between them (the head of an order, paragraphs,
tables). A part longer than WINDOW is read in windows, each after the part's first line (a list's intro, a table's header).
A citation points at the parts of its clause, the part holding its quoted line, or (no clause, no quote) the document.
  numbers  every number of the sentence (digits, number words in English and Russian, months, dates split into parts)
           must be in the text cited; a long one (4+ digits) may also stand in it with other separators. "One" and
           "first" are no number here: in English they are as often a pronoun or "for the first time" (впервые)
  judge    (--judge) the sentence, with its context in the card (the section's heading; the intro of a list it is an item
           of, the header of a table it is a row of), against what it cites: read whole up to FULL characters, else the
           reranker's 2 best windows (for a document cited whole: its head and the 3 best). A sentence with one source that this does not
           back is looked for among the document's --candidates best other parts. With --missing the judge is stricter: it
           first lists the facts of the sentence the text does not give (`absent`), and any makes it not_in_text. Without
           it the judge passes a true sentence with an added guess; with it, it flags about 7% of true ones
Not judged: the intro of a list ("The Department's tasks are:"), and remarks of the agent on the document itself (its
OCR, its numbering, what it does not say), which no part of it can back: such a sentence of a cited one is cut out of it.
Results go to --output as JSON lines, one a sentence; a run that stops is continued by running it again.

Usage: uv run python experiments/check_cards.py [--judge agent|wiki] [--missing] [--candidates K] [--cards REGEX] [--output cards.jsonl]
"""

import argparse
import json
import re
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from catix.settings import settings
from catix.wiki.paths import BUNDLE
from eval_claims import CLAUSE, JUDGE_PROMPT, MISSING_JUDGE_PROMPT, VERDICTS, ask

SOURCE = re.compile(r"^(\d+)\. \[.*?\]\((/[^)\s]+\.md)\)(.*)$", re.M)  # a title may hold [brackets]
WORDS = {  # number words, English and Russian (stems with their endings); 1 is left out, see above
    2: r"two|second|два|две|двух|двум|двумя|втор\w*",
    3: r"three|third(?![- ](?:part|person))|thirds|три|тр[её]х|тр[её]м|тремя|трет\w*", 4: r"four|fourth|четыре|четыр[её]х|четырем|четверт\w*",
    5: r"five|fifth|пять|пяти|пят(?:ый|ого|ой|ом|ую|ая)", 6: r"six|sixth|шесть|шести|шест(?:ой|ого|ом|ую|ая)",
    7: r"seven|seventh|семь|семи|седьм\w*", 8: r"eight|eighth|восемь|восьми|восьм(?:ой|ого|ом|ую|ая)",
    9: r"nine|ninth|девять|девяти|девят(?:ый|ого|ом|ую|ая)", 10: r"ten|tenth|десять|десяти|десят(?:ый|ого|ом|ую|ая)",
    11: r"eleven|одиннадцат\w*", 12: r"twelve|двенадцат\w*", 13: r"thirteen|тринадцат\w*", 14: r"fourteen|четырнадцат\w*",
    15: r"fifteen|пятнадцат\w*", 16: r"sixteen|шестнадцат\w*", 17: r"seventeen|семнадцат\w*", 18: r"eighteen|восемнадцат\w*",
    19: r"nineteen|девятнадцат\w*",
    20: r"twenty|двадцат\w*", 30: r"thirty|тридцат\w*", 40: r"forty|сорок\w*", 60: r"sixty|шестьдесят\w*|шестидесят\w*",
    90: r"ninety|девяност\w*", 100: r"hundred|сто|ста|сотн\w*",
}
MONTHS = ["january|январ\\w*", "february|феврал\\w*", "march|март\\w*", "april|апрел\\w*", "ма[йяе]", "june|июн\\w*",  # "may" is the verb
          "july|июл\\w*", "august|август\\w*", "september|сентябр\\w*", "october|октябр\\w*", "november|ноябр\\w*", "december|декабр\\w*"]
NUMBER_WORDS = [(re.compile(rf"\b(?:{pattern})\b", re.I), value) for value, pattern in WORDS.items()]
NUMBER_WORDS += [(re.compile(rf"\b(?:{pattern})\b", re.I), month) for month, pattern in enumerate(MONTHS, 1)]
NUMBER_WORDS += [(re.compile(r"\bMay\s+\d|\d\s+May\b"), 5)]
GROUPS = re.compile(r"(?<=\d)[   ,](?=\d{3}\b)")  # 15 000 and 15,000 are 15000
WINDOW = 2500  # characters of a long part the judge reads at a time, after the part's first line
FULL = 6000  # what a citation points at is read whole up to this length
FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
SEPARATOR = re.compile(r"\|[\s\-:|]+\|")  # the line under a table's header
SENTENCES = re.compile(r"(?<=;)\s+|(?<=[^\d\s.]\.)\s+(?=[А-ЯЁA-Z«\-–—•*])|(?<=:)\s+(?=[-–—•*\d])")
# The agent's remarks on the document rather than on what it says: its reading, its numbering, what it leaves out.
REMARK = re.compile(r"\bOCR\b|text layer|extracted (?:text|table)|[Hh]ow reliable|scanned document|\bscan read|item numbers|"
                    r"(?:is|are) (?:also )?numbered|wiki (?:holds|copy|page is)|cannot be settled|illegible|unreadable|does not say|"
                    r"do not say|not mentioned|gives neither|\bthe page (?:gives|has|shows|holds) no\b|\bthe page does not|"
                    r"do(?:es)? not give|gives the same|is laid out|heading rows? of the table|(?:page|calendar) presents|"
                    r"part of its text is not legible|pages? of the same")
CONTEXT = """
A "Context" line, when given, is what the sentence continues in the card: the section's heading, the intro of a list the
sentence is an item of, or the header of a table it is a row of. Read the sentence with it."""
CARD_JUDGE_PROMPTS = {False: JUDGE_PROMPT + CONTEXT, True: MISSING_JUDGE_PROMPT + CONTEXT}  # by --missing


def numbers(text: str) -> set[int]:
    text = GROUPS.sub("", text)
    found = {int(digits) for digits in re.findall(r"\d+", text)}
    return found | {value for pattern, value in NUMBER_WORDS if pattern.search(text)}


def missing_numbers(claim: str, text: str) -> list[int]:
    """The sentence's numbers that its text does not have."""
    have, digits = numbers(text), re.sub(r"\D", "", text)
    return sorted(value for value in numbers(claim) if value not in have and not (value >= 1000 and str(value) in digits))


def clause_spans(document: str) -> list[tuple[str, int, int]]:
    """The clauses of a document. The PDF's conversion bolds a number that a line of a sentence starts with ("(с учетом
    пункта" / "**4.13** настоящего Положения)"): such a number, without the clause's dot, after a sentence that has not
    ended goes on with the last clause."""
    found = []
    for m in CLAUSE.finditer(document):
        # A date or a programme's code set in bold is no clause: "от" / "**27.07.2006** «О персональных данных»", "**09.03.01**"
        date = re.fullmatch(r"\d{1,2}\.\d{1,2}\.\d{4}|\d{2}\.\d{2}\.\d{2}", m.group(1))
        continues = date or not m.group(0).startswith(f"**{m.group(1)}.**")  # "**4.13**", not "**4.13.**"
        before = document[found[-1][1]:m.start()] if found else ""
        ended = re.search(r"[.;:!?…»)\]|]\s*$", before) and not re.search(r"\b(?:п|пп|ст|ч|абз)\.\s*$", before)  # "с п. **4.18**"
        if found and continues and not ended:
            found[-1] = (found[-1][0], found[-1][1], m.end())
        elif date:  # a date is no clause: its text stays with the text around
            continue
        else:
            found.append((m.group(1), m.start(), m.end()))
    return found


def between(document: str, start: int, end: int) -> list[tuple[str | None, int, int]]:
    """The text between clauses (the head of an order, paragraphs, tables), in pieces that start at its headings; a
    heading that starts with a number ("## 126. Сроки…") is that clause's."""
    cuts = [start] + [start + m.start() + 1 for m in re.finditer(r"\n#", document[start:end])] + [end]
    return [(number.group(1) if (number := re.match(r"#+\s*(\d+(?:\.\d+)*)\.?\s", document[a:b])) else None, a, b)
            for a, b in zip(cuts, cuts[1:]) if document[a:b].strip()]


def pieces(text: str) -> list[tuple[str, str]]:
    """A text as the pieces a window is made of, each with what it needs to be read alone: a table's row (with the line
    before the table, its caption, and its header), or a list item or sentence of the prose (with the last two lines before it that end in ":", what the item is
    of). The PDF breaks lines, and leaves blank ones, inside an item: prose is joined and split at items and sentences."""
    out, prose, header, intros = [], [], "", []
    lines = text.split("\n")

    def flush() -> None:
        for piece in SENTENCES.split(" ".join(" ".join(prose).split())):
            if piece:
                out.append((piece, "\n".join(intros)))
                if piece.endswith(":"):
                    intros[:] = [*intros[-1:], piece[:300]]
        prose.clear()

    for i, line in enumerate(lines):
        line = line.strip()
        if not line.startswith("|"):
            if line:
                header = ""
                prose.append(line)
            continue
        flush()
        if SEPARATOR.fullmatch(line):
            continue
        if i + 1 < len(lines) and SEPARATOR.fullmatch(lines[i + 1].strip()):
            caption = out[-1][0][:300] if out and not out[-1][0].startswith("|") else ""
            header = f"{caption}\n{line}".strip()
            continue
        out.append((line, header))
    flush()
    return out


def windows(text: str) -> list[str]:
    """A long text as windows of up to WINDOW characters: its first line, then what its first piece needs to be read alone
    (see pieces), then whole pieces."""
    if len(text) <= WINDOW:
        return [text]
    found = pieces(text)
    if not found:
        return [text[:WINDOW]]
    head, rest = found[0][0][:500], found[1:]
    out, chunk, context = [], [], ""
    for piece, needs in rest:
        if chunk and len(head) + len(context) + sum(map(len, chunk)) + len(piece) > WINDOW:
            out.append("\n…\n".join(part for part in (head, context, "\n".join(chunk)) if part))
            chunk = []
        if not chunk:
            context = needs if needs != head else ""
        chunk.append(piece[:WINDOW])
    return out + (["\n…\n".join(part for part in (head, context, "\n".join(chunk)) if part)] if chunk else []) or [head]


def parts(document: str) -> list[dict]:
    """Every part of a document's text with its windows: clauses, and the text between them."""
    start = m.end() if (m := FRONTMATTER.match(document)) else 0
    end = document.find("\n# Citations")
    end = len(document) if end < 0 else end
    spans, position = [], start
    for number, a, b in [*clause_spans(document), (None, end, end)]:
        if a >= end and number is not None:
            continue
        if a > position:
            spans += between(document, position, min(a, end))
        if number is not None:
            spans.append((number, a, min(b, end)))
        position = max(position, b)
    return [{"number": number, "start": a, "end": b, "text": window}
            for number, a, b in spans for window in windows(document[a:b].strip()) if window.strip()]


def cited(path: str, tail: str, cache: dict) -> dict | None:
    """What a citation points at: the indices of the document's parts (None: the whole document), and their full text."""
    file = BUNDLE / path.lstrip("/")
    if not file.exists():
        return None
    if path not in cache:
        document = file.read_text(encoding="utf-8")
        cache[path] = (document, parts(document))
    document, units = cache[path]
    chosen = []
    if quote := re.search(r"«(.{12,}?)(?:»|$)", tail):
        words = re.findall(r"\w+", quote.group(1))[:8]
        if at := re.search(r"\W+".join(map(re.escape, words)), document):
            chosen = [i for i, unit in enumerate(units) if unit["start"] <= at.start() < unit["end"]]
    if not chosen and (clause := re.search(r"clauses? ([\d.]*\d)", tail)):
        number = clause.group(1)  # with its subclauses: "4.2. Заполнение бланков дипломов:" says it in 4.2.1, 4.2.2, ...
        chosen = [i for i, unit in enumerate(units) if unit["number"] and (unit["number"] == number or unit["number"].startswith(number + "."))]
    if chosen:
        spans = dict.fromkeys((units[i]["start"], units[i]["end"]) for i in chosen)
        return {"path": path, "parts": chosen, "text": "\n\n".join(document[a:b].strip() for a, b in spans)}
    if not tail.strip():
        return {"path": path, "parts": None, "text": document}
    return None


def sentences(cache: dict) -> list[dict]:
    """The cited sentences of every card with their context in the card and what their citations point at."""
    rows = []
    for card in sorted((BUNDLE / "knowledge").glob("*.md")):
        text = card.read_text(encoding="utf-8")
        sources = {n: (path, tail) for n, path, tail in SOURCE.findall(text)}
        body = text.split("\n---\n", 1)[-1].split("\n# Citations", 1)[0]
        heading = intro = header = ""
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                heading, intro, header = line.lstrip("# "), "", ""
                continue
            item, row = bool(re.match(r"(?:[-*]|\d+\.)\s", line)), line.startswith("|")
            if row and re.fullmatch(r"\|[\s\-:|]+\|", line):
                continue
            if row and not header:
                header = re.sub(r"\s*\[\d+\]", "", line)
                if not re.search(r"\[\d+\]", line):
                    continue
            if not row:
                header = ""
            if not item and not row:
                intro = re.sub(r"\s*\[\d+\]", "", line) if line.rstrip("*").endswith(":") else ""
            context = " — ".join(part for part in (heading, intro if item else "", header if row else "") if part)
            for sentence in re.split(r"(?<=\])\s+(?=[A-ZА-Я«\"(])", re.sub(r"^(?:[-*]|\d+\.)\s+", "", line).strip("| ").replace(" | ", "; ")):
                refs = list(dict.fromkeys(re.findall(r"\[(\d+)\]", sentence)))
                claim = re.sub(r"\s*\[\d+\]", "", sentence).strip()
                if not refs or len(claim) < 15:
                    continue
                cites = [cited(*sources[n], cache) if n in sources else None for n in refs]
                # The agent's remarks on the document are left out of the sentence, or make all of it when nothing else is left.
                whole = claim
                claim = " ".join(part for part in re.split(r"(?<=[.;])\s+(?=[A-Z«(])", whole) if not REMARK.search(part)).strip()
                kind = "intro" if whole.rstrip("* ").endswith(":") else "remark" if not claim else "claim"
                rows.append({"card": card.stem, "claim": claim or whole, "remarks_cut": claim != whole and bool(claim), "context": context, "kind": kind,
                             "refs": [(sources[n][0], sources[n][1].strip(", ")[:60]) if n in sources else (None, n) for n in refs],
                             "resolved": all(cites), "cites": [{"path": c["path"], "parts": c["parts"]} for c in cites if c],
                             "cited_text": "\n\n".join(dict.fromkeys(c["text"] for c in cites if c))})
    return rows


def judge(row: dict, text: str, wiki: bool, missing: bool) -> tuple[str, list[str]]:
    """The verdict, and (with `missing`) the details of the sentence the judge did not find in the text."""
    context = f"Context: {row['context']}\n\n" if row["context"] else ""
    answer = ask(CARD_JUDGE_PROMPTS[missing], f"{context}Sentence: {row['claim']}\n\nParagraph:\n{text}", wiki, 400 if missing else 30)
    try:
        absent = json.loads(answer[answer.find("{"):answer.rfind("}") + 1])["missing"]
    except (ValueError, KeyError, TypeError):
        absent = []
    answer = answer[answer.rfind('"verdict"'):]  # the list of absent details may name a verdict
    return next((verdict for verdict in VERDICTS if verdict in answer), "unparsed"), [str(detail) for detail in absent or []]


def best(rerank, query: str, texts: list[str], k: int) -> list[int]:
    scores = [score for start in range(0, len(texts), 32) for score in rerank(query, texts[start:start + 32])]
    return sorted(range(len(texts)), key=scores.__getitem__, reverse=True)[:k]


def query(row: dict) -> str:
    return f"{row['context']}: {row['claim']}" if row["context"] else row["claim"]


def read(row: dict, cache: dict, rerank) -> set:
    """What the judge reads of what the sentence cites (row["paragraph"]); the (path, text) of the parts it read."""
    texts_read, used = [], set()
    for cite in row["cites"]:
        units = cache[cite["path"]][1]
        indices = cite["parts"] if cite["parts"] is not None else range(len(units))
        texts = list(dict.fromkeys(units[i]["text"] for i in indices))
        if sum(map(len, texts)) > FULL:
            if cite["parts"] is None:  # a document cited whole: its head (the order, its number, date, who signed) and the best
                texts = [texts[0], *(texts[1:][i] for i in best(rerank, query(row), texts[1:], 3))]
            else:
                texts = [texts[i] for i in best(rerank, query(row), texts, 2)]
        texts_read += texts
        used |= {(cite["path"], units[i]["text"]) for i in indices if units[i]["text"] in texts}
    row["paragraph"] = "\n\n".join(dict.fromkeys(texts_read))
    return used


def check(row: dict, cache: dict, candidates: int, wiki: bool, missing: bool, rerank) -> None:
    """The judge's verdict on what the sentence cites; if not backed, on the document's best other parts, in order."""
    used = read(row, cache, rerank)
    row["verdict"], row["absent"] = judge(row, row["paragraph"], wiki, missing)
    paths = {cite["path"] for cite in row["cites"]}
    if row["verdict"] == "supported" or len(paths) != 1 or candidates <= 0:
        return
    path = paths.pop()
    others = [unit for unit in cache[path][1] if (path, unit["text"]) not in used]
    for i in best(rerank, query(row), [unit["text"] for unit in others], candidates):
        if judge(row, others[i]["text"], wiki, missing)[0] == "supported":
            row["moved"] = others[i]["number"] or f"text at {others[i]['start']}"
            row["moved_text"] = others[i]["text"]
            return


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--judge", choices=["agent", "wiki"], help="also judge every resolved sentence with this model")
    parser.add_argument("--missing", action="store_true",
                        help="the stricter judge: it lists the facts of the sentence the text does not give, and any makes it not_in_text")
    parser.add_argument("--candidates", type=int, default=3, help="parts of the document to judge when the cited text fails (0: off)")
    parser.add_argument("--cards", help="only the cards whose name matches this regular expression")
    parser.add_argument("--output", type=Path, default=Path("cards.jsonl"))
    args = parser.parse_args()
    settings.phoenix_endpoint = None

    cache = {}
    rows = [row for row in sentences(cache) if not args.cards or re.match(args.cards, row["card"])]
    for row in rows:
        row["missing_numbers"] = missing_numbers(row["claim"], row["cited_text"]) if row["resolved"] else None
    resolved = [row for row in rows if row["resolved"]]
    kinds = Counter(row["kind"] for row in resolved)
    print(f"{len(rows)} cited sentences in {len({row['card'] for row in rows})} cards; {len(resolved)} with every citation "
          f"found in its document: {kinds['claim']} claims, {kinds['intro']} intros of lists, {kinds['remark']} remarks on the document")
    with_numbers = [row for row in resolved if numbers(row["claim"])]
    flagged = [row for row in resolved if row["missing_numbers"]]
    print(f"numbers: {len(with_numbers)} sentences have some, {len(flagged)} have one their text does not "
          f"({len(flagged) / max(len(with_numbers), 1):.1%})")
    for row in flagged:
        print(f"  {row['card']}: {row['missing_numbers']} | {row['claim'][:120]}")

    done = {}
    if args.output.exists():
        for line in args.output.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row.get("verdict", "error") != "error" and row.get("missing") == args.missing:  # an error, or another judge's verdict, is tried again
                done[(row["card"], row["claim"])] = row
    if args.judge:
        from catix.db import pg

        todo = [row for row in resolved if row["kind"] == "claim" and (row["card"], row["claim"]) not in done]
        print(f"judging {len(todo)} sentences ({len(done)} done before)", flush=True)
        lock = threading.Lock()

        def run(row: dict) -> None:
            try:
                row["missing"] = args.missing
                check(row, cache, args.candidates, args.judge == "wiki", args.missing, pg.rerank)
            except Exception as error:  # noqa: BLE001 - one sentence the servers fail on (too long, a timeout) must not stop the run
                row["verdict"], row["error"] = "error", repr(error)[:300]
            row.pop("cited_text")
            with lock, args.output.open("a", encoding="utf-8") as out:
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
            done[(row["card"], row["claim"])] = row

        with ThreadPoolExecutor(4) as pool:
            for i, _ in enumerate(pool.map(run, todo), 1):
                if i % 250 == 0:
                    print(f"  {i}/{len(todo)}", flush=True)

    judged = [row for row in done.values() if "verdict" in row]
    if not judged:
        return
    verdicts = Counter(row["verdict"] for row in judged)
    print(f"\njudge on {len(judged)} sentences: " + ", ".join(f"{verdict} {count} ({count / len(judged):.1%})" for verdict, count in verdicts.most_common()))
    failed = [row for row in judged if row["verdict"] != "supported"]
    nowhere = [row for row in failed if not row.get("moved")]
    print(f"not backed by what they cite: {len(failed)}; backed by another part of the document: {len(failed) - len(nowhere)}; "
          f"backed nowhere: {len(nowhere)}")
    cite_kind = Counter("document" if any(c["parts"] is None for c in row["cites"]) else "clause or line" for row in nowhere)
    print("  backed nowhere, by what they cite:", dict(cite_kind))
    print(f"  of them flagged by numbers too: {sum(bool(row['missing_numbers']) for row in nowhere)}")
    print("cards with most sentences backed nowhere:", Counter(row["card"] for row in nowhere).most_common(8))


if __name__ == "__main__":
    main()
