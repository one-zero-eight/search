"""How the agent's answers slow down when several users ask at once.

Asks the real agent N questions at once, for each setting:

    all          every question goes to the agent at once (as the bot does now)
    questions=Q  at most Q questions are answered at once, the next one starts when one is done (a queue of questions)

and prints, for every question, its total time, the number of model calls and the largest context of a call (from the
agent's own log). Run it where the bot runs, against the same model server:

    PHOENIX_PROJECT=catix-loadtest python experiments/load_agent.py 6 all questions=2 questions=3
"""

import asyncio
import contextvars
import logging
import statistics
import sys
import time
import uuid
from collections import defaultdict

from catix.agent.core import build_agent, final_answer
from catix.agent.tools import AgentContext

QUESTIONS = [
    "Сколько раз можно пересдавать экзамен, если я его завалил?",
    "На какой срок можно взять академический отпуск?",
    "Где находится спортзал и как туда записаться?",
    "Когда дедлайн по домашке по матанализу?",
    "How long can academic leave last?",
    "Какие клубы есть в университете?",
    "Как получить справку об обучении?",
    "Какая стипендия у бакалавров и от чего она зависит?",
]

question_no = contextvars.ContextVar("question_no", default=None)
calls: dict[int, list[tuple[int, float]]] = defaultdict(list)  # question -> (approximate tokens in context, seconds) per model call


class CallRecorder(logging.Handler):
    """Collects the "model call" lines of LoggingMiddleware (agent/core.py) by the question they belong to."""

    def emit(self, record: logging.LogRecord) -> None:
        no = question_no.get()
        if no is not None and record.msg.startswith("model call"):
            _, tokens, seconds = record.args
            calls[no].append((tokens, seconds))


logging.basicConfig(level=logging.WARNING)
logging.getLogger("catix.agent").setLevel(logging.INFO)
logging.getLogger("catix.agent").addHandler(CallRecorder())
logging.getLogger("catix.agent").propagate = False

agent = build_agent()


async def ask(no: int, question: str, limit: asyncio.Semaphore, t0: float) -> float:
    async with limit:
        question_no.set(no)  # the helpers' threads get a copy of the context, so their log lines carry it too
        config = {"configurable": {"thread_id": f"load-{uuid.uuid4().hex}"}}
        state = await agent.ainvoke({"messages": [{"role": "user", "content": question}]}, config, context=AgentContext())
        final_answer(state["messages"], state.get("sources") or {})
    return time.monotonic() - t0


async def run(n: int, setting: str) -> None:
    kind, _, k = setting.partition("=")
    limit = asyncio.Semaphore(int(k) if kind == "questions" else n)
    calls.clear()
    t0 = time.monotonic()
    waits = await asyncio.gather(*(ask(i, QUESTIONS[i % len(QUESTIONS)], limit, t0) for i in range(n)))
    print(f"{setting:12s} mean {statistics.mean(waits):5.1f}s  median {statistics.median(waits):5.1f}s  last {max(waits):5.1f}s"
          f"  | {' '.join(f'{w:.0f}' for w in sorted(waits))}", flush=True)
    for i in range(n):
        own = calls[i]
        print(f"    q{i} {waits[i]:5.1f}s  {len(own)} model calls, {sum(s for _, s in own):5.1f}s in them,"
              f" largest context ~{max((t for t, _ in own), default=0)} tokens", flush=True)


async def main(n: int, settings: list[str]) -> None:
    for setting in settings:
        await run(n, setting)


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]), sys.argv[2:] or ["all"]))
