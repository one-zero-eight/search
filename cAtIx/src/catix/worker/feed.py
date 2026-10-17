"""Serves the approved schedule changes as an iCalendar feed and links it to the InNoHassle calendar.

The feed is at /feed/<FEED_TOKEN>.ics (everything) and /feed/<FEED_TOKEN>/<GROUP>.ics (one study group). InNoHassle fetches it from its own servers, so the address must be public
HTTPS: put a tunnel or reverse proxy in front of FEED_PORT. The token in the path is the only protection, as for
any calendar subscription link.
Commands: `catix-feed url <public base url>` prints the link, `catix-feed link <public base url>` adds it to the
calendar of the INNOHASSLE_TOKEN owner (the token lives one day; the link stays).
"""

import asyncio
import hmac
import logging
import sys

from aiohttp import web

from catix.worker import changes
from catix import groups
from catix.settings import settings

log = logging.getLogger("catix.feed")

ALIAS = "ctx-schedule-changes"


async def _handle(request: web.Request) -> web.Response:
    log.info("feed requested by %s (%s)", request.headers.get("CF-Connecting-IP", request.remote), request.headers.get("User-Agent", "?")[:80])
    token = settings.feed_token.get_secret_value() if settings.feed_token else ""
    if not token or not hmac.compare_digest(request.match_info["token"], token):
        raise web.HTTPNotFound
    group = request.match_info.get("group")
    if group is not None and (group := groups.normalize(group)) is None:
        raise web.HTTPNotFound
    body = await asyncio.to_thread(changes.feed_ics, None if group in (None, groups.ALL) else group)
    return web.Response(text=body, content_type="text/calendar", charset="utf-8")


async def serve() -> web.AppRunner | None:
    if not settings.feed_token:
        return None
    app = web.Application()
    app.router.add_get("/feed/{token}.ics", _handle)  # Everything.
    app.router.add_get("/feed/{token}/{group}.ics", _handle)  # One study group (and the chats for everybody).
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", settings.feed_port).start()  # A tunnel or proxy exposes it.
    return runner


def feed_url(base: str) -> str:
    if not settings.feed_token:
        sys.exit("Set FEED_TOKEN in .env first.")
    return f"{base.rstrip('/')}/feed/{settings.feed_token.get_secret_value()}.ics"


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] not in ("url", "link"):
        sys.exit("usage: catix-feed url|link <public base url, e.g. https://name.ru.tuna.am>")
    url = feed_url(sys.argv[2])
    if sys.argv[1] == "url":
        print(url)
        return
    from catix.innohassle import client as innohassle

    resp = innohassle._client.post(
        "schedule/v0/users/me/linked",
        json={"alias": ALIAS, "url": url, "name": "Изменения расписания (из чатов)", "is_active": True},
    )
    print(resp.status_code, resp.text[:300])
