"""The queue of questions in front of the agent (agent/questions.py), without a model or a messenger."""

import asyncio

from catix.agent.questions import QuestionQueue


def _run(coro):
    return asyncio.run(coro)


async def _ask(queue: QuestionQueue, user: str, name: str, log: list, release: asyncio.Event):
    async with queue.turn(user):
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


def test_a_question_that_got_its_turn_earlier_has_the_lower_priority():
    """vLLM serves the lowest priority first and gives 0 to a call without one: the calls of every question go before
    those, and of two questions the one that started first goes first. Outside a turn there is none."""
    from catix.agent.questions import PRIORITY

    async def scenario():
        queue, seen, release = QuestionQueue(2), {}, asyncio.Event()

        async def ask(name):
            async with queue.turn(name):
                seen[name] = PRIORITY.get()
                await release.wait()

        first = asyncio.create_task(ask("u0"))
        await _settle()
        await asyncio.sleep(0.01)  # the priority is in ms
        second = asyncio.create_task(ask("u1"))
        await _settle()
        release.set()
        await asyncio.gather(first, second)
        return seen, PRIORITY.get()

    seen, after = _run(scenario())
    assert seen["u0"] < seen["u1"] < 0 and after is None
