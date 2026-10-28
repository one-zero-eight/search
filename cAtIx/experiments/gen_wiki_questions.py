"""A larger test set for the wiki's search, written by the LLM from the wiki itself (experiments/wiki_questions.jsonl).

quality.QUESTIONS has 57 questions: one question is 1.75 points of hit@5, and the methods compared differed by one or two.
Here pieces are drawn at random, by kinds of pages in about the share readers ask of them, and the model writes for each the
question a reader would ask and copies the words of the piece that answer it. The answer is any piece that holds those words
(a document's other versions too), so the set survives a new index. Questions whose words are not in the piece, are in more
than MAX_RELEVANT pieces (too common to be an answer), or repeat another are left out.

Usage: [SEED=n] uv run python experiments/gen_wiki_questions.py [N]   (N questions, 300 by default; appends to what is there)
"""

import json
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from catix.db import pg
from catix.settings import settings

OUT = Path(__import__("os").environ.get("WIKI_QUESTIONS", Path(__file__).with_name("wiki_questions.jsonl")))
SEED = int(__import__("os").environ.get("SEED", 300))  # another seed: other pages, to add questions
MAX_RELEVANT = 20
# (folder, trust, share of the questions, readers who would ask)
STRATA = [
    ("regulations", "official", 0.45, ["student", "applicant", "postgraduate", "staff", "teacher"]),
    ("course-programmes", "official", 0.17, ["student", "teacher", "applicant"]),
    ("courses", "wiki", 0.11, ["student", "teacher"]),
    ("sites", "wiki", 0.16, ["applicant", "public", "student"]),
    ("past-papers", "wiki", 0.03, ["student"]),
    ("people", "wiki", 0.03, ["student", "public"]),
    ("procedures|programs|pages|schedules|calendars", "wiki", 0.05, ["student", "applicant"]),
]
PROMPT = """Below is a piece of a page of the wiki of Innopolis University. Write ONE question that a {reader} could ask a
university assistant and that this piece answers, then copy from the piece the words that answer it.
- The question in {language}, worded as a person would ask in a chat: short, everyday words, not the wording of the
  document; do not name the document or its clause; no "according to this text".
- The fact must be specific to the university (a term, a number, a rule, a person, a procedure, a topic of a course), not
  common knowledge. The question must make sense without the piece and have one answer: name what the fact belongs to
  (the course, the programme and its year, the kind of students, the dormitory, the exam) as a person would ("in the
  Operating Systems course", "for master's applicants"), so that a reader of the whole wiki would find this piece.
- "answer": 3 to 60 words copied from the piece exactly as they stand (its language, its spelling), the ones that answer.
- If the piece answers nothing a reader would ask (a list of names, a form to fill, a table of contents, noise), answer {{"skip": true}}.
Answer with JSON only: {{"question": "...", "answer": "..."}} or {{"skip": true}}.

Page: {title}
Piece:
{text}"""


def words(text: str) -> list[str]:
    return re.findall(r"[^\W_]+", text.lower().replace("ё", "е"))


def span_regex(answer: str) -> str:
    """The answer's words in a row, whatever stands between them (markup, line breaks, punctuation)."""
    return r"[\W_]+".join(re.escape(w) for w in words(answer))


def sample(conn, n: int) -> list[dict]:
    rng = random.Random(SEED)
    chosen = []
    for folder, trust, share, readers in STRATA:
        pages = pg.column(conn, "SELECT path FROM wiki_pages WHERE split_part(path, '/', 2) ~ %s AND trust = %s ORDER BY path",
                          (f"^({folder})$", trust))
        for path in rng.sample(pages, min(len(pages), round(n * share))):  # one piece a page: many documents, not many pieces of one
            rows = conn.execute("SELECT c.id, c.path, c.text, p.title FROM wiki_chunks c JOIN wiki_pages p ON p.path = c.path "
                                "WHERE c.path = %s AND length(c.text) > 300 ORDER BY c.seq", (path,)).fetchall()
            if rows:
                piece = dict(rng.choice(rows))
                chosen.append(piece | {"reader": rng.choice(readers), "language": "English" if rng.random() < 0.3 else "Russian"})
    return chosen


def ask(piece: dict) -> dict | None:
    prompt = PROMPT.format(reader=piece["reader"], language=piece["language"], title=piece["title"], text=piece["text"][:3000])
    try:
        response = httpx.post(f"{str(settings.llm_route).rstrip('/')}/chat/completions", timeout=300, json={
            "model": settings.llm_model, "temperature": 0.7, "max_tokens": 400, "response_format": {"type": "json_object"},
            "chat_template_kwargs": {"enable_thinking": False}, "messages": [{"role": "user", "content": prompt}]})
        data = response.json()
        if "choices" not in data:
            raise RuntimeError(str(data.get("error", data))[:200])
        return json.loads(data["choices"][0]["message"]["content"])
    except Exception as e:  # noqa: BLE001
        print(f"  {piece['path']}: {type(e).__name__}: {str(e)[:100]}", file=sys.stderr)
        return None


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    conn = pg.connect()
    pieces = sample(conn, round(n * 2.5))  # (more than half are skipped or left out)
    seen = {json.loads(line)["question"].lower() for line in OUT.read_text().splitlines()} if OUT.exists() else set()
    kept = 0
    why: dict[str, int] = {}
    with ThreadPoolExecutor(3) as pool, OUT.open("a") as out:
        for piece, made in zip(pieces, pool.map(ask, pieces)):
            if kept >= n:
                break
            reason = ("no answer" if not made else "skipped" if made.get("skip") else "no question" if not made.get("question") or not made.get("answer")
                      else "answer length" if not 3 <= len(words(made["answer"])) <= 60 else "repeated" if made["question"].strip().lower() in seen else "")
            if not reason:
                question, answer = made["question"].strip(), made["answer"].strip()
                regex = span_regex(answer)
                relevant = pg.scalar(conn, "SELECT count(*) FROM wiki_chunks WHERE translate(lower(search_text), 'ё', 'е') ~ %s", (regex,))
                reason = ("not copied" if not re.search(regex, piece["text"].lower().replace("ё", "е"))  # (not in the piece as it stands)
                          else "too common" if not 1 <= relevant <= MAX_RELEVANT else "")
            if reason:
                why[reason] = why.get(reason, 0) + 1
                continue
            seen.add(question.lower())
            kept += 1
            out.write(json.dumps({"reader": piece["reader"], "language": piece["language"], "question": question, "answer": answer,
                                  "source": piece["path"], "relevant": relevant}, ensure_ascii=False) + "\n")
            out.flush()
            print(f"{kept:>3} {piece['reader']:<12} {question[:90]}", flush=True)
    print(f"{kept} questions in {OUT}; left out: {why}")


def relevant(conn, answer: str):
    """The pieces that hold the answer's words in a row (and when a piece the search finds in their place answers: quality.Relevant)."""
    from catix.wiki.quality import Relevant

    return Relevant.of(conn.execute("SELECT c.id, c.path, p.title, c.copy_of FROM wiki_chunks c JOIN wiki_pages p ON p.path = c.path "
                                    "WHERE translate(lower(c.search_text), 'ё', 'е') ~ %s", (span_regex(answer),)).fetchall())


if __name__ == "__main__":
    main()
