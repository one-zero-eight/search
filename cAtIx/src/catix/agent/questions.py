"""A queue of questions in front of the agent: at most AGENT_PARALLEL_QUESTIONS are answered at once, the rest wait their turn.

The model server gains little from several questions at once: the agent's work is mostly reading long prompts (prefill),
which takes the whole GPU, and the MoE model gains little from decoding several answers together. On llama.cpp 6
questions at once took 134 s, one after another 136 s (experiments/load_agent.py). On 1Cat-vLLM 12 at once were done in
106-111 s 4 at a time and in 136 s one at a time, with about the same mean wait (71 s, 74 s); answered all at once,
everybody waits for the slowest. While a question runs, its model calls carry its priority (PRIORITY): vLLM serves the
calls of a question that started earlier first.

Turns go round the users: a user's second question waits behind the first questions of everybody else, so one person
sending many messages does not hold the others up. The queue lives in one process: the Telegram and the Max bot keep one each.
"""

import asyncio
import contextlib
import contextvars
import itertools
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field

log = logging.getLogger("catix.questions")

# The priority of the model calls of the question being answered (LLM_PRIORITY, agent/core.py PriorityMiddleware): the
# moment it got its turn, in ms and below zero. vLLM serves the lowest first and gives 0 to a call without one, so the
# calls of a question that started earlier go first, and those of every question before other work (the wiki agent).
PRIORITY: contextvars.ContextVar[int | None] = contextvars.ContextVar("question_priority", default=None)


def priority_now() -> int:
    return int(time.time() * 1000) - 10**13


@dataclass
class _Ticket:
    user: str
    rank: int  # How many questions of the same user were ahead of it when it came: the round it belongs to.
    no: int = field(default_factory=itertools.count().__next__)


class QuestionQueue:
    def __init__(self, parallel: int) -> None:
        self.parallel = parallel
        self._waiting: list[_Ticket] = []  # in the order they will be answered
        self._running: list[_Ticket] = []
        self._changed = asyncio.Condition()

    def ahead(self, ticket: _Ticket) -> int:
        """Questions that will be answered or are being answered before this one."""
        return len(self._running) + self._waiting.index(ticket)

    def _enqueue(self, user: str) -> _Ticket:
        rank = sum(t.user == user for t in self._running + self._waiting)
        ticket = _Ticket(user, rank)
        # After every waiting question of the same round or an earlier one: round robin over the users.
        at = next((i for i, t in enumerate(self._waiting) if t.rank > rank), len(self._waiting))
        self._waiting.insert(at, ticket)
        return ticket

    @contextlib.asynccontextmanager
    async def turn(
        self, user: str, on_wait: Callable[[int], Awaitable[None]] | None = None, repeat: float | None = None
    ) -> AsyncIterator[None]:
        """Waits for the turn of a question of `user`, then holds a place while the block runs.

        While it waits (not when there is no wait at all), `on_wait(n)` is called with the number of questions ahead
        whenever it changes, and again every `repeat` seconds if it does not (a Telegram draft disappears after 30 s)."""
        async with self._changed:
            ticket = self._enqueue(user)
            self._changed.notify_all()  # those it was put ahead of are one place further back
        try:
            shown, shown_at = None, 0.0
            while True:
                async with self._changed:
                    if len(self._running) < self.parallel and self._waiting[0] is ticket:
                        self._waiting.remove(ticket)
                        self._running.append(ticket)
                        self._changed.notify_all()  # with more than one place, the next one may start too
                        break
                    ahead = self.ahead(ticket)
                    if on_wait is None or (ahead == shown and repeat is None):
                        await self._changed.wait()
                        continue
                    left = shown_at + repeat - time.monotonic() if ahead == shown else 0
                    if left > 0:
                        with contextlib.suppress(TimeoutError):
                            await asyncio.wait_for(self._changed.wait(), left)
                        continue
                if shown is None:
                    log.info("question of %s waits, %d ahead", user, ahead)
                shown, shown_at = ahead, time.monotonic()
                await on_wait(ahead)  # outside the lock: it talks to the messenger
        except BaseException:
            async with self._changed:  # left the queue while waiting (cancelled, or on_wait failed)
                if ticket in self._waiting:
                    self._waiting.remove(ticket)
                    self._changed.notify_all()
            raise
        priority = PRIORITY.set(priority_now())
        try:
            yield
        finally:
            PRIORITY.reset(priority)
            async with self._changed:
                self._running.remove(ticket)
                self._changed.notify_all()
