"""Tells the admins in Telegram when something the bot depends on stops working, and when it works again.

Every ALERT_CHECK_SECONDS it asks the llama.cpp servers (chat model, embeddings, reranker if configured) for /health,
looks at the embedding queue and, where the userbot is set up (TG_API_ID), whether it is connected to Telegram. A problem
is reported after two failed checks in a row (a restart or a hiccup does not wake anybody), once, and again every
REMIND_HOURS while it lasts; the recovery is reported too. Runs inside `catix-worker`.
"""

import asyncio
import contextlib
import logging
import time
from collections.abc import Awaitable, Callable

import httpx
import redis.asyncio as aioredis
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from catix import live_search
from catix.settings import settings
from catix.worker import changes, embedder

log = logging.getLogger("catix.health")

FAILS_BEFORE_ALERT = 2
QUEUE_CHECKS_BEFORE_ALERT = 3  # The queue is long for this many checks in a row: the embedders do not keep up.
REMIND_HOURS = 6
QUEUE = "очередь эмбеддингов"
USERBOT = "userbot (поиск в Telegram)"


def _health_url(route: object) -> str:
    base = str(route).rstrip("/")
    return f"{base.removesuffix('/v1')}/health"


def targets() -> dict[str, str]:
    found = {
        "языковая модель (чат)": _health_url(settings.llm_route),
        "эмбеддинги": _health_url(settings.embeddings_route),
    }
    if settings.reranker_route:
        found["реранкер"] = _health_url(settings.reranker_route)
    return found


async def probe(client: httpx.AsyncClient, url: str) -> bool:
    try:
        return (await client.get(url)).status_code == 200
    except httpx.HTTPError:
        return False


class Monitor:
    """The state machine: feed it the results of a check, it sends what has to be said."""

    def __init__(self, notify: Callable[[str], Awaitable[None]], clock: Callable[[], float] = time.monotonic) -> None:
        self.notify, self.clock = notify, clock
        self.fails: dict[str, int] = {}
        self.alerted_at: dict[str, float] = {}

    async def step(self, name: str, ok: bool, detail: str = "") -> None:
        if ok:
            self.fails[name] = 0
            if name in self.alerted_at:
                del self.alerted_at[name]
                await self.notify(f"✅ {name}: снова в порядке.")
            return
        self.fails[name] = self.fails.get(name, 0) + 1
        threshold = QUEUE_CHECKS_BEFORE_ALERT if name == QUEUE else FAILS_BEFORE_ALERT
        if self.fails[name] < threshold:
            return
        now = self.clock()
        last = self.alerted_at.get(name)
        if last is None or now - last >= REMIND_HOURS * 3600:
            self.alerted_at[name] = now
            prefix = "⚠️" if last is None else "⚠️ Всё ещё:"
            await self.notify(f"{prefix} {name}: {detail or 'не отвечает'}.")


async def _notifier(bot: Bot) -> Callable[[str], Awaitable[None]]:
    async def notify(text: str) -> None:
        log.warning("alert: %s", text)
        for admin in await asyncio.to_thread(changes.admins):
            with contextlib.suppress(TelegramAPIError):
                await bot.send_message(admin, text)

    return notify


async def run() -> None:
    if not settings.alerts or not settings.tg_bot_token:
        log.info("alerts are off (ALERTS=false or no TG_BOT_TOKEN)")
        return
    bot = Bot(settings.tg_bot_token.get_secret_value())  # Only sends; the bot app polls.
    monitor = Monitor(await _notifier(bot))
    # The userbot runs where it has an account to run with; it says it is connected through Redis (live_search.ONLINE).
    userbot = aioredis.from_url(settings.redis_url, socket_timeout=10) if settings.tg_api_id and settings.redis_url else None
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            while True:
                try:
                    for name, url in targets().items():
                        await monitor.step(name, await probe(client, url), "не отвечает на /health")
                    backlog = await asyncio.to_thread(embedder.backlog)
                    await monitor.step(QUEUE, backlog <= settings.alert_queue_max, f"{backlog} сообщений ждут вектора, эмбеддеры не успевают")
                    if userbot:
                        await monitor.step(USERBOT, bool(await userbot.exists(live_search.ONLINE)), "нет связи с Telegram")
                except asyncio.CancelledError:
                    raise
                except Exception:  # noqa: BLE001 - a failing check must not stop the monitoring
                    log.exception("health check failed")
                await asyncio.sleep(settings.alert_check_seconds)
    finally:
        await bot.session.close()
        if userbot:
            await userbot.aclose()
