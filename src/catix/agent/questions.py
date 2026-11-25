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
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

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

    def _enqueue(self, user: str) -> _Ticket:
        rank = sum(t.user == user for t in self._running + self._waiting)
        ticket = _Ticket(user, rank)
        # After every waiting question of the same round or an earlier one: round robin over the users.
        at = next((i for i, t in enumerate(self._waiting) if t.rank > rank), len(self._waiting))
        self._waiting.insert(at, ticket)
        return ticket

    @contextlib.asynccontextmanager
    async def turn(self, user: str) -> AsyncIterator[None]:
        """Waits for the turn of a question of `user`, then holds a place while the block runs."""
        async with self._changed:
            ticket = self._enqueue(user)
            self._changed.notify_all()  # those it was put ahead of are one place further back
        try:
            async with self._changed:
                await self._changed.wait_for(lambda: len(self._running) < self.parallel and self._waiting[0] is ticket)
                self._waiting.remove(ticket)
                self._running.append(ticket)
                self._changed.notify_all()  # with more than one place, the next one may start too
        except BaseException:
            async with self._changed:  # left the queue while waiting (cancelled)
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
