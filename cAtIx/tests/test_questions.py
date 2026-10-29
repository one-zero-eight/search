"""The queue of questions in front of the agent (agent/questions.py), without a model or a messenger."""

import asyncio

from catix.agent.questions import QuestionQueue
from catix.tgbot import stream


def _run(coro):
    return asyncio.run(coro)


async def _ask(queue: QuestionQueue, user: str, name: str, log: list, release: asyncio.Event, waits: list | None = None):
    async def on_wait(ahead: int) -> None:
        if waits is not None:
            waits.append((name, ahead))

    async with queue.turn(user, on_wait):
        log.append(f"start {name}")
        await release.wait()
        log.append(f"end {name}")


async def _settle():
    for _ in range(20):
        await asyncio.sleep(0)


def test_one_question_at_a_time_in_the_order_they_came():
    async def scenario():
        queue, log, release = QuestionQueue(1), [], asyncio.Event()
        tasks = [asyncio.create_task(_ask(queue, f"u{i}", f"q{i}", log, release)) for i in range(3)]
        await _settle()
        assert log == ["start q0"]  # the others wait
        release.set()
        await asyncio.gather(*tasks)
        return log

    assert _run(scenario()) == ["start q0", "end q0", "start q1", "end q1", "start q2", "end q2"]


def test_two_places_let_two_questions_run_together():
    async def scenario():
        queue, log, release = QuestionQueue(2), [], asyncio.Event()
        tasks = [asyncio.create_task(_ask(queue, f"u{i}", f"q{i}", log, release)) for i in range(3)]
        await _settle()
        started = list(log)
        release.set()
        await asyncio.gather(*tasks)
        return started

    assert _run(scenario()) == ["start q0", "start q1"]


def test_a_users_second_question_waits_behind_the_first_questions_of_others():
    async def scenario():
        queue, log, release = QuestionQueue(1), [], asyncio.Event()
        tasks = [asyncio.create_task(_ask(queue, "spammer", f"s{i}", log, release)) for i in range(3)]
        await _settle()
        tasks.append(asyncio.create_task(_ask(queue, "other", "o0", log, release)))
        await _settle()
        release.set()
        await asyncio.gather(*tasks)
        return [entry.removeprefix("start ") for entry in log if entry.startswith("start")]

    assert _run(scenario()) == ["s0", "o0", "s1", "s2"]  # s0 was already being answered when o0 came


def test_a_waiting_question_hears_how_many_are_ahead_and_one_without_a_wait_hears_nothing():
    async def scenario():
        queue, log, waits = QuestionQueue(1), [], []
        first, second = asyncio.Event(), asyncio.Event()
        a = asyncio.create_task(_ask(queue, "a", "a", log, first, waits))
        await _settle()
        b = asyncio.create_task(_ask(queue, "b", "b", log, second, waits))
        c = asyncio.create_task(_ask(queue, "c", "c", log, second, waits))
        await _settle()
        first.set()
        await a
        await _settle()
        second.set()
        await asyncio.gather(b, c)
        return waits

    assert _run(scenario()) == [("b", 1), ("c", 2), ("c", 1)]


def test_the_status_is_repeated_while_the_place_stays_the_same():
    async def scenario():
        queue, seen, release = QuestionQueue(1), [], asyncio.Event()

        async def holder():
            async with queue.turn("a"):
                await release.wait()

        async def waiter():
            async def on_wait(ahead):
                seen.append(ahead)

            async with queue.turn("b", on_wait, repeat=0.05):
                pass

        tasks = [asyncio.create_task(holder())]
        await _settle()
        tasks.append(asyncio.create_task(waiter()))
        await asyncio.sleep(0.18)
        release.set()
        await asyncio.gather(*tasks)
        return seen

    seen = _run(scenario())
    assert seen[0] == 1 and len(seen) >= 3, seen


def test_a_question_that_gives_up_leaves_the_queue():
    async def scenario():
        queue, log, release = QuestionQueue(1), [], asyncio.Event()
        a = asyncio.create_task(_ask(queue, "a", "a", log, release))
        await _settle()
        b = asyncio.create_task(_ask(queue, "b", "b", log, release))
        c = asyncio.create_task(_ask(queue, "c", "c", log, release))
        await _settle()
        b.cancel()
        release.set()
        await asyncio.gather(a, c)
        return log, b.cancelled()

    log, cancelled = _run(scenario())
    assert cancelled and log == ["start a", "end a", "start c", "end c"]


def test_the_draft_shows_the_queue_and_sends_it_again_to_keep_it_alive():
    class Recorder(stream.DraftStreamer):
        def __init__(self):
            super().__init__(None, 1, None, lambda text: text)
            self.sent: list[str] = []

        async def _send(self, text, *, html):
            self.sent.append(text)

    drafts = Recorder()
    _run(drafts.queued(2))
    _run(drafts.queued(2))
    _run(drafts.start())
    assert drafts.sent == [stream.QUEUED.format(ahead=2)] * 2 + [stream.CHECKING]
    assert "2" in drafts.sent[0]
