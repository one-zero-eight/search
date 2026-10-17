"""Is the code that resolves "завтра", "в пятницу", "через неделю" needed when the model already sees the message date?

Real chats are too easy to tell (the model is already right nearly every time), so this builds announcements with
relative dates and known answers in a throwaway chat, asks about each, and removes the chat afterwards. The chat is
private and not one of the bot's, so Telegram users never see it. Needs the embedding workers (catix-worker) to be running.

Configs: N date only as a JSON field (the original), K resolved dates (current). (Two more were tried and dropped:
the date stamped into the message text, with and without the resolved dates: it added nothing.)
Usage: uv run python experiments/eval_relative_dates.py [N K] [--reps N]
"""

import re
import statistics
import sys
import time
import uuid
from datetime import datetime

from catix.db import pg
from catix.db import store
from catix.agent.core import build_agent, final_answer
from catix.settings import settings

sys.path.insert(0, "experiments")
from eval_dates import PAST, body, judge, reason  # noqa: E402

CHAT_ID = -999000222
FUTURE_ONLY = PAST  # for events after "today" (2026-10-15 by the clock of the run) a past-tense word is wrong

# (sent at, text, question, regexes that must match, forbid)
CASES = [
    ((2026, 10, 9, 18), "Напоминаю: завтра в 14:00 в аудитории 301 собираемся на репетицию хора", "Когда была репетиция хора?", [r"10 октября|10\.10"], None),
    ((2026, 10, 7, 12), "В пятницу у нас контрольная по ботанике, не забудьте", "Когда была контрольная по ботанике?", [r"9 октября|09\.10"], None),
    ((2026, 10, 12, 12), "Сдача проектов по кулинарии — через неделю", "Когда сдача проектов по кулинарии?", [r"19 октября|19\.10"], FUTURE_ONLY),
    ((2026, 10, 14, 9), "Сегодня вечером в 19:00 лекция гостя по астрономии в 108", "Когда была лекция по астрономии?", [r"14 октября|14\.10"], None),
    ((2026, 10, 13, 12), "Послезавтра экскурсия на птицефабрику, сбор в 8:00 у входа", "Когда экскурсия на птицефабрику?", [r"15 октября|15\.10|сегодня"], None),
    ((2026, 10, 14, 12), "В следующий вторник конкурс по лепке пельменей", "Когда конкурс по лепке пельменей?", [r"20 октября|20\.10"], FUTURE_ONLY),
    ((2026, 10, 2, 12), "Вчера опубликовали результаты олимпиады по шахматам", "Когда опубликовали результаты олимпиады по шахматам?", [r"1 октября|01\.10"], None),
    ((2026, 10, 10, 12), "На следующей неделе во вторник будет мастер-класс по керамике", "Когда был мастер-класс по керамике?", [r"13 октября|13\.10"], None),
    ((2026, 10, 5, 12), "Дедлайн по эссе про пингвинов — 20 октября", "До какого числа сдать эссе про пингвинов?", [r"20 октября|20\.10"], FUTURE_ONLY),
    ((2026, 10, 1, 12), "Завтра в 10:00 в 214 хакатон по робототехнике, послезавтра финал", "Когда был финал хакатона по робототехнике?", [r"3 октября|03\.10"], None),
]  # fmt: skip

CONFIGS = {
    "N": dict(annotate_dates=False),  # the date only as a JSON field (the original)
    "K": dict(annotate_dates=True),   # dates resolved in code (current)
}  # fmt: skip


def setup() -> None:
    chat = store.ChatInfo(CHAT_ID, "synthetic relative dates", None, via_bot=False)
    messages = [
        store.Message(CHAT_ID, i + 1, None, datetime(*sent, tzinfo=settings.tz), None, 1, "Test", None, text, None)
        for i, (sent, text, *_rest) in enumerate(CASES)
    ]
    store.write_batch([chat], messages)
    deadline = time.time() + 60
    while time.time() < deadline:  # wait until the embedding workers have processed them
        with pg.connection() as conn:
            waiting = conn.execute(
                "SELECT count(*) AS n FROM embedding_queue q JOIN messages m ON m.id = q.message_id WHERE m.chat_id = %s", (CHAT_ID,)
            ).fetchone()["n"]
        if waiting == 0:
            return
        time.sleep(0.5)
    sys.exit("the embedding workers did not process the test messages: is the bot (or catix-embed) running?")


def cleanup() -> None:
    with pg.connection() as conn:
        for table in ("messages", "members"):
            conn.execute(f"DELETE FROM {table} WHERE chat_id = %s", (CHAT_ID,))
        conn.execute("DELETE FROM chats WHERE chat_id = %s", (CHAT_ID,))


def main() -> None:
    reps = int(sys.argv[sys.argv.index("--reps") + 1]) if "--reps" in sys.argv else 3
    names = [a for a in sys.argv[1:] if a in CONFIGS] or list(CONFIGS)
    try:  # The cleanup must run even if setup fails half way.
        setup()
        cases = CASES
        if "--pick" in sys.argv:  # 1-based case numbers
            cases = [CASES[int(i) - 1] for i in sys.argv[sys.argv.index("--pick") + 1].split(",")]
        summary = {}
        for name in names:
            for key, value in CONFIGS[name].items():
                setattr(settings, key, value)
            agent = build_agent()
            passed, times, lines = 0, [], []
            for sent, text, question, must, forbid in cases:
                marks = []
                for _ in range(reps):
                    started = time.monotonic()
                    try:
                        out = agent.invoke(
                            {"messages": [{"role": "user", "content": question}]}, {"configurable": {"thread_id": uuid.uuid4().hex}}
                        )
                        answer = final_answer(out["messages"])
                    except Exception as e:  # noqa: BLE001
                        answer = ""
                        print(f"   error: {type(e).__name__}", flush=True)
                    times.append(time.monotonic() - started)
                    ok = judge(answer, must, forbid)
                    passed += ok
                    marks.append("✓" if ok else "✗")
                    if not ok:
                        lines.append(f"    ✗ {question}\n        {reason(answer, must, forbid)} | {body(answer)[:150]!r}")
                print(f"[{name}] {''.join(marks)}  {question}", flush=True)
            total = len(cases) * reps
            summary[name] = (passed, total, statistics.median(times))
            print(f"[{name}] correct {passed}/{total}, median {summary[name][2]:.0f}s\n", flush=True)
            if lines:
                print("\n".join(lines[:8]), "\n", flush=True)
        print("== summary")
        for name, (passed, total, med) in summary.items():
            print(f"{name} {CONFIGS[name]}: {passed}/{total} correct ({passed / total:.0%}), median {med:.0f}s")
    finally:
        cleanup()
        pg.close()


if __name__ == "__main__":
    main()
