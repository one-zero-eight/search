"""The userbot stays up when Telegram cannot be reached (tguserbot/userbot.py, `listen`): it tries again after pauses that
grow, instead of exiting into docker's immediate restart. And the bot does not wait for a userbot that is not connected
(live_search.py, `request`). Nothing connects: the client and Redis are stand-ins."""

import asyncio
import types

import pytest
from python_socks import ProxyError

from catix import live_search
from catix.settings import settings
from catix.tguserbot import userbot


class _Stop(Exception):
    pass


def _run_listen(monkeypatch, rounds: list, lasted: list[float] | None = None) -> list[float]:
    """listen() over `rounds` (an exception to raise, or None for a round that ends in a disconnect), each lasting the
    seconds in `lasted` (a moment if not given): the pauses taken."""
    pauses: list[float] = []
    now = [0.0]

    async def once() -> None:
        if not rounds:
            raise _Stop
        now[0] += lasted.pop(0) if lasted else 1
        if (outcome := rounds.pop(0)) is not None:
            raise outcome

    async def sleep(seconds: float) -> None:
        pauses.append(seconds)

    monkeypatch.setattr(userbot, "_listen_once", once)
    monkeypatch.setattr(userbot.asyncio, "sleep", sleep)
    monkeypatch.setattr(userbot.random, "uniform", lambda a, b: 1.0)
    monkeypatch.setattr(userbot, "time", types.SimpleNamespace(monotonic=lambda: now[0]))
    with pytest.raises(_Stop):
        asyncio.run(userbot.listen())
    return pauses


def test_the_pauses_grow_while_telegram_is_away(monkeypatch):
    rounds = [ConnectionError("Connection to Telegram failed 2 time(s)")] * 7
    assert _run_listen(monkeypatch, rounds) == [10, 30, 60, 120, 300, 300, 300]


def test_a_proxy_that_refuses_is_tried_again_not_a_crash(monkeypatch):
    assert _run_listen(monkeypatch, [ProxyError("refused"), TimeoutError(), None]) == [10, 30, 60]


def test_a_connection_that_worked_a_while_starts_the_pauses_over(monkeypatch):
    rounds = [ConnectionError(), ConnectionError(), None, ConnectionError()]
    assert _run_listen(monkeypatch, rounds, lasted=[5, 5, userbot.STABLE_SECONDS + 1, 5]) == [10, 30, 10, 30]


def test_an_unexpected_error_still_stops_the_userbot(monkeypatch):
    async def once() -> None:
        raise EOFError  # e.g. no session: the login asks for a phone number, and there is nobody to type it

    monkeypatch.setattr(userbot, "_listen_once", once)
    with pytest.raises(EOFError):
        asyncio.run(userbot.listen())


class _Redis:
    def __init__(self, online: bool) -> None:
        self.online, self.pushed = online, []

    def exists(self, key: str) -> int:
        return int(self.online and key == live_search.ONLINE)

    def rpush(self, key: str, value: str) -> None:
        self.pushed.append(key)

    def blpop(self, keys: list[str], timeout: int) -> None:
        return None


def test_the_bot_does_not_wait_for_a_userbot_that_is_not_connected(monkeypatch):
    fake = _Redis(online=False)
    monkeypatch.setattr(settings, "redis_url", "redis://stand-in")
    monkeypatch.setattr(live_search.redis, "from_url", lambda *a, **k: fake)
    hits, problem = live_search.request([-100], ["экзамен"])
    assert hits == [] and "not connected" in problem and fake.pushed == []


def test_a_connected_userbot_is_asked(monkeypatch):
    fake = _Redis(online=True)
    monkeypatch.setattr(settings, "redis_url", "redis://stand-in")
    monkeypatch.setattr(live_search.redis, "from_url", lambda *a, **k: fake)
    monkeypatch.setattr(settings, "live_search_timeout", 1.0)
    _, problem = live_search.request([-100], ["экзамен"])
    assert fake.pushed == [live_search.REQUESTS] and "did not answer" in problem
