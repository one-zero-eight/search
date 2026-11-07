"""The model server under the agent's kind of load, without the agent: how long users wait when they ask at once.

Every user makes CALLS model calls like the agent does: the same long system prompt for everybody, then a context that grows
by a tool result per call. All users start together. Two kinds of limits can be put in front of the server:

    calls=K      at most K model calls run at once, the rest wait in order (what `-np K` of llama-server does)
    questions=Q  at most Q users are served at once, the next user starts when one finishes (a queue of questions)

    python3 experiments/load_llm.py 6 calls=6 calls=2 questions=1 questions=2

Prints, for every setting, the wait of each user, their mean and the time until the last one is done.
"""
import json
import random
import statistics
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

URL = "http://localhost:8080/v1/chat/completions"
WORDS = ["университет", "расписание", "экзамен", "аудитория", "дедлайн", "клуб", "кампус", "group", "course", "пересдача"]
rng = random.Random(7)
SYSTEM = "Ты помощник университета. " + " ".join(rng.choice(WORDS) for _ in range(1700))  # ~3k tokens, the same for all
CALLS, TOOL_WORDS, OUT = 4, 700, 120
computed, computed_lock = [0], threading.Lock()


class FifoLimit:
    """At most `k` holders; the others are let in strictly in the order they came, as the model server's own queue does.
    (A threading.Semaphore is not fair: a thread that has just released it takes it again before the waiting ones.)"""

    def __init__(self, k):
        self.free, self.waiting, self.lock = k, [], threading.Lock()

    def __enter__(self):
        with self.lock:
            if self.free and not self.waiting:
                self.free -= 1
                return
            turn = threading.Event()
            self.waiting.append(turn)
        turn.wait()

    def __exit__(self, *exc):
        with self.lock:
            if self.waiting:
                self.waiting.pop(0).set()  # the slot passes straight to the first in line
            else:
                self.free += 1


def call(messages, limit):
    body = {"messages": messages, "max_tokens": OUT, "temperature": 0.3, "ignore_eos": True,
            "chat_template_kwargs": {"enable_thinking": False}}
    with limit:
        r = urllib.request.urlopen(urllib.request.Request(URL, json.dumps(body).encode(), {"Content-Type": "application/json"}), timeout=900)
        d = json.load(r)
    with computed_lock:
        computed[0] += d["timings"]["prompt_n"]  # prompt tokens the server had to compute, not taken from its cache
    return d["choices"][0]["message"]["content"]


def user(u, call_limit, question_limit, t0):
    r = random.Random(u)
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"вопрос {u}: " + " ".join(r.choice(WORDS) for _ in range(20))}]
    with question_limit:
        for _ in range(CALLS):
            text = call(messages, call_limit)
            messages += [{"role": "assistant", "content": text},
                         {"role": "user", "content": "результат: " + " ".join(r.choice(WORDS) for _ in range(TOOL_WORDS))}]
    return time.time() - t0


def run(n, setting):
    kind, _, k = setting.partition("=")
    unlimited = threading.BoundedSemaphore(10_000)
    call_limit = FifoLimit(int(k)) if kind == "calls" else unlimited
    question_limit = FifoLimit(int(k)) if kind == "questions" else unlimited
    computed[0] = 0
    seed = random.randrange(10**9)  # new users every run: nothing of theirs is cached yet
    t0 = time.time()
    with ThreadPoolExecutor(n) as ex:
        waits = sorted(ex.map(lambda u: user(seed + u, call_limit, question_limit, t0), range(n)))
    print(f"{setting:12s} mean {statistics.mean(waits):5.1f}s  median {statistics.median(waits):5.1f}s  last {waits[-1]:5.1f}s"
          f"  computed {computed[0]:6d} tokens  | {' '.join(f'{w:.0f}' for w in waits)}", flush=True)


if __name__ == "__main__":
    users = int(sys.argv[1])
    for setting in sys.argv[2:]:
        run(users, setting)
