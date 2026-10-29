"""A queue of questions in front of the agent: at most AGENT_PARALLEL_QUESTIONS are answered at once, the rest wait their turn.

The model server answers several questions at once no faster than one after another: the agent's work is mostly reading
long prompts (prefill), which takes the whole GPU, and the MoE model gains little from decoding several answers together
(experiments/load_agent.py: 6 questions at once took 134 s, one after another 136 s). Answered all at once, everybody
waits for the slowest; in turn, the first ones get their answer early (a mean wait of 72 s instead of 114 s). Questions
that run together also take each other's slots on the model server and lose its cache of their context.

Turns go round the users: a user's second question waits behind the first questions of everybody else, so one person
sending many messages does not hold the others up. The queue lives in one process: the Telegram and the Max bot keep one each.
"""

import asyncio
import contextlib
import itertools
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field

log = logging.getLogger("catix.questions")


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
        try:
            yield
        finally:
            async with self._changed:
                self._running.remove(ticket)
                self._changed.notify_all()
