"""Do the answers get dates right? Compares: A as at the start, C dates resolved in code (dates.py).

Each question has a known correct date (checked by hand against the messages) and, where the event is in the
future, words that would be wrong ("был"). Today is taken from the clock, so the future ones must stay in the future.

Usage: uv run python experiments/eval_dates.py [configs, e.g. A C] [--reps N] [--hard | --only-hard]
"""

import json
import re
import statistics
import sys
import time
import uuid

from langchain_core.messages import AIMessage

from catix.db import pg
from catix.agent.core import build_agent, final_answer
from catix.settings import settings

PAST = r"\bбыл[аио]?\b|прошел|прошёл|состоялся|состоялась"
# (question, regexes that must all match the answer body, regex that must not match)
QUESTIONS = [
    ("Когда был тест по дискретке?", [r"5 октября|05\.10|2026-10-05"], r"4 октября|04\.10|13 октября"),
    ("До какого числа можно пройти социально-психологическое тестирование?", [r"15 октября|15\.10|2026-10-15"], None),
    ("Когда у английского был GA1 module test?", [r"14 октября|14\.10|2026-10-14"], r"15 октября"),
    ("Когда тьюторы ждали всех желающих в 313 аудитории?", [r"27 сентября|27\.09|2026-09-27"], None),
    ("Когда был тест GT1 по английскому?", [r"23 сентября|23\.09|2026-09-23"], None),
    ("Когда дедлайн подачи заявки кандидатом в старосты?", [r"6 октября|06\.10|2026-10-06"], None),
    ("Когда мидтерм по компарху?", [r"23 октября|23\.10|2026-10-23"], PAST),
    ("Когда review session по Test 1 по аналитической геометрии и в какой аудитории?", [r"16 октября|16\.10|2026-10-16", r"106"], PAST),
    ("Когда тест по матану?", [r"17 октября|17\.10|2026-10-17"], PAST),
    ("Когда был Единый день банков?", [r"4 сентября|04\.09|2026-09-04"], None),
]  # fmt: skip

# Several events in one answer; a future date must not be called past. FUTURE(d) is "<date> ... был/прошёл" nearby.
def _past_near(date_pattern: str) -> str:
    return rf"(?:{date_pattern})[^.\n]{{0,45}}(?:{PAST})|(?:{PAST})[^.\n]{{0,25}}(?:{date_pattern})"


HARD = [
    ("Когда и какие будут у меня мидтермы?",
     [r"23 октября|23\.10|2026-10-23", r"17 октября|17\.10|2026-10-17"],
     _past_near(r"23 октября|23\.10|17 октября|17\.10")),
    ("Какие тесты и контрольные ещё впереди?",
     [r"23 октября|23\.10|2026-10-23", r"17 октября|17\.10|2026-10-17"],
     _past_near(r"23 октября|23\.10|17 октября|17\.10")),
    ("Какие тесты уже прошли с начала сентября?",
     [r"5 октября|05\.10|2026-10-05", r"14 октября|14\.10|23 сентября|23\.09"],
     None),
]  # fmt: skip

CONFIGS = {
    "A": dict(annotate_dates=False),  # as at the start
    "C": dict(annotate_dates=True),   # dates resolved in code
}  # fmt: skip
# Model reasoning (thinking mode) was tried too and dropped: about 4x slower (~25 s instead of ~6 s per answer)
# with no visible gain on these questions.


def body(answer: str) -> str:
    """The answer without its source list, whose dates would match by accident."""
    return re.split(r"\n\n(?:Источники|Sources):", answer)[0]


def judge(answer: str, must: list[str], forbid: str | None) -> bool:
    text = body(answer)
    return bool(answer.strip()) and all(re.search(p, text, re.I) for p in must) and not (forbid and re.search(forbid, text, re.I))


def reason(answer: str, must: list[str], forbid: str | None) -> str:
    """Why an answer was judged wrong: what is missing, or which wrong wording matched."""
    text = body(answer)
    if not answer.strip():
        return "empty answer"
    if forbid and (m := re.search(forbid, text, re.I)):
        return f"wrong wording: {m.group(0)!r}"
    missing = [p for p in must if not re.search(p, text, re.I)]
    return f"missing: {missing}" if missing else "ok"


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    reps = int(sys.argv[sys.argv.index("--reps") + 1]) if "--reps" in sys.argv else 2
    names = [a for a in args if a in CONFIGS] or ["A", "C"]
    questions = HARD if "--only-hard" in sys.argv else QUESTIONS + HARD if "--hard" in sys.argv else QUESTIONS
    if "--pick" in sys.argv:  # 1-based numbers of the questions of the chosen list
        questions = [questions[int(i) - 1] for i in sys.argv[sys.argv.index("--pick") + 1].split(",")]
    summary = {}
    for name in names:
        for key, value in CONFIGS[name].items():
            setattr(settings, key, value)
        agent = build_agent()
        passed, times, empty, lines = 0, [], 0, []
        for question, must, forbid in questions:
            marks = []
            for _ in range(reps):
                config = {"configurable": {"thread_id": uuid.uuid4().hex}}
                started = time.monotonic()
                try:
                    out = agent.invoke({"messages": [{"role": "user", "content": question}]}, config)
                    answer = final_answer(out["messages"], out.get("sources") or {})
                except Exception as e:  # noqa: BLE001
                    answer = ""
                    print(f"   error: {type(e).__name__}: {str(e)[:100]}", flush=True)
                times.append(time.monotonic() - started)
                ok = judge(answer, must, forbid)
                empty += not answer.strip()
                passed += ok
                marks.append("✓" if ok else "✗")
                if not ok:
                    lines.append(f"    ✗ {question}\n        {reason(answer, must, forbid)}")
                with open("/tmp/eval_answers.jsonl", "a") as f:
                    f.write(json.dumps({"config": name, "question": question, "ok": ok, "answer": answer}, ensure_ascii=False) + "\n")
            print(f"[{name}] {''.join(marks)}  {question}", flush=True)
        total = len(questions) * reps
        summary[name] = (passed, total, statistics.median(times), max(times), empty)
        print(f"[{name}] correct {passed}/{total}, median {summary[name][2]:.0f}s, slowest {summary[name][3]:.0f}s, empty answers {empty}\n", flush=True)
        if lines:
            print("\n".join(lines[:16]), "\n", flush=True)
    print("== summary")
    for name, (passed, total, med, slow, empty) in summary.items():
        print(f"{name} {CONFIGS[name]}: {passed}/{total} correct ({passed / total:.0%}), median {med:.0f}s, slowest {slow:.0f}s, empty {empty}")
    pg.close()


if __name__ == "__main__":
    main()
