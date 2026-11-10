"""The documents maintain themselves: the sources are asked on their schedule, and what changed becomes documents in Postgres.

    catix-docs run [--loop] [--source NAME ...] [--site NAME ...] [--build]

One run:
  1. the sources that are due (sources/, each with its own interval; `--source` asks the named ones now; `--site` reads only
     the named sites in place of every site), and those the requests waiting in the queue name (POST /{section}/parse of the
     API, parse_requests.py: its requests are served here, and the run says in the queue what it did);
  2. if one brought something, or an earlier run was cut off before it built: build.rebuild(): changed documents are
     rewritten, gone ones removed; the search finds them at once, the vectors of new pieces come from the queue.
`--build`: no source is asked; the documents are rebuilt from the data the sources hold.
OCR: the sources queue scans for a manual run with OCR and put aside those too long for it (sources/ocr_queue.py); when
either grows, the admins are told in Telegram, of each scan once.
Runs one at a time (an advisory lock of Postgres). Its state (when each source was asked, the scans the admins were told of,
whether a rebuild is owed) is in docs_meta, key 'runner'. `--loop` wakes up for a request (REQUEST_POLL) without waiting for the schedule.
"""

import json
import sys
import time
import traceback
from argparse import Namespace
from datetime import datetime, timedelta, timezone

from catix import admins
from catix.db import pg
from catix.docs import build, parse_requests, sources, store
from catix.settings import settings

LOCK_ID = 7_301_001  # pg_try_advisory_lock key of catix-docs run
IDLE = timedelta(minutes=15)  # the longest sleep of --loop between two looks at the schedule
REQUEST_POLL = 30  # seconds between two looks of the sleeping --loop at the queue of requests


class Outcome(str):
    """What a run did, in a line, and of which kind: changed (the documents moved) or unchanged; `failed`: the sources that
    raised (the others went on). The queue of requests keeps them (parse_requests.finish)."""

    kind: str
    failed: tuple[str, ...] = ()

    def __new__(cls, kind: str, text: str) -> "Outcome":
        line = super().__new__(cls, text)
        line.kind = kind
        return line


def load_state() -> dict:
    with pg.connection() as conn:
        row = conn.execute("SELECT value FROM docs_meta WHERE key = 'runner'").fetchone()
    return json.loads(row["value"]) if row else {}


def save_state(state: dict) -> None:
    with pg.connection() as conn:
        conn.execute("INSERT INTO docs_meta (key, value) VALUES ('runner', %s) ON CONFLICT (key) DO UPDATE SET value = excluded.value",
                     (json.dumps(state, ensure_ascii=False),))


def due(state: dict, now: datetime) -> list[sources.Source]:
    """The sources whose interval has passed."""
    asked = state.get("asked", {})
    return [s for s in sources.SOURCES if s.name not in asked or now - datetime.fromisoformat(asked[s.name]) >= s.every]


def run_once(names: list[str] | None = None, sites: list[str] | None = None) -> Outcome:
    """One run; what it did, in a line. `sites`: the `sites` source reads only these sites (sources.sites_of)."""
    state, now = load_state(), datetime.now(timezone.utc)
    asked = [s for s in sources.SOURCES if s.name in names] if names else due(state, now)
    if sites:
        asked = [sources.sites_of(sites) if s.name == "sites" else s for s in asked]
    changed: dict[str, int] = {}
    failed: list[str] = []

    def outcome(kind: str, text: str) -> Outcome:
        line = Outcome(kind, text + (f" (failed: {', '.join(failed)}; see the log)" if failed else ""))
        line.failed = tuple(failed)
        return line

    for source in asked:
        print(f"== source {source.name}: {source.about}", flush=True)
        try:
            changed[source.name] = source.update()
        except Exception:  # noqa: BLE001 - one source failing must not stop the others; it is asked again next time
            traceback.print_exc()
            failed.append(source.name)
            continue
        if source in sources.SOURCES:  # (a few sites read do not move the schedule of all of them)
            state.setdefault("asked", {})[source.name] = now.isoformat(timespec="seconds")
            save_state(state)
    try:
        tell_ocr_queue(state)
    except Exception:  # noqa: BLE001 - the queue's report must not stop the run
        traceback.print_exc()
    build_only = names == ["build-only"]
    if not build_only and not any(changed.values()) and not state.get("rebuild"):
        return outcome("unchanged", f"nothing new ({', '.join(s.name for s in asked) or 'no source due'})")
    state["rebuild"] = True
    save_state(state)
    counts = build.rebuild()
    state.pop("rebuild")
    save_state(state)
    new, changed_n, removed = (counts.get(k, 0) for k in ("pages new", "pages changed", "pages removed"))
    if new + changed_n + removed:
        return outcome("changed", f"documents: {new} new, {changed_n} changed, {removed} removed; {store.queued()} pieces wait for a vector")
    return outcome("unchanged", "sources changed, the documents did not")


def tell_ocr_queue(state: dict) -> None:
    """The admins told when the OCR queue grows, or the scans put aside as too long for it (sources/ocr_queue.py): of each scan
    once. The state keeps the scans told that are still there (`ocr_told`): one read by OCR leaves it, one that comes back,
    or moves between the queue and the long ones, is told again."""
    from catix.docs.sources import ocr_queue

    found = ocr_queue.scans()
    now = {(s.source, s.key, s.too_long) for s in found}
    told = {tuple(t) for t in state.get("ocr_told", [])}
    if text := ocr_queue.message(found, {(source, key) for source, key, _ in now - told}):
        tell_admins(text)
    if now != told:
        state["ocr_told"] = [list(t) for t in sorted(now)]
        save_state(state)


def tell_admins(text: str) -> None:
    """A message to the admins of the bot (they set up the alerts too); the run goes on if it cannot be sent."""
    if not settings.tg_bot_token:
        print(f"(no TG_BOT_TOKEN: the admins are not told) {text}", flush=True)
        return
    import asyncio

    from aiogram import Bot

    async def send() -> None:
        ids = list(dict.fromkeys([*settings.admin_telegram_ids, *(admins.added() if settings.database_url else [])]))
        async with Bot(settings.tg_bot_token.get_secret_value()) as bot:
            for admin in ids:
                try:
                    await bot.send_message(admin, text, parse_mode=None)
                except Exception as e:  # noqa: BLE001 - blocked the bot, never started it, ...
                    print(f"admin {admin} was not told: {e}", flush=True)

    try:
        asyncio.run(send())
    except Exception:  # noqa: BLE001
        traceback.print_exc()


def with_requests(names: list[str] | None, sites: list[str] | None, requests: list[parse_requests.Request], state: dict,
                  now: datetime) -> tuple[list[str] | None, list[str] | None]:
    """The sources a run asks and the sites `sites` reads (None: every site), with the requests it serves: the sources of the
    command line (or the due ones) and those the requests name. A request that asks no source (parsing false) adds nothing:
    the run rebuilds what the data holds anyway. `sites` asked for every site (the schedule, `--source sites`) reads
    every site; asked only for some (`--site`, the requests), it reads the union of them."""
    if not requests:
        return names, sites
    base = list(names) if names else [s.name for s in due(state, now)]
    asked = list(dict.fromkeys([*base, *(r.source for r in requests if r.parsing)])) or ["build-only"]
    if "sites" not in asked:
        return asked, None
    limits = ([sites or None] if "sites" in base else []) + [r.sites or None for r in requests if r.parsing and r.source == "sites"]
    return asked, None if None in limits else list(dict.fromkeys(name for limit in limits for name in limit))


def served(requests: list[parse_requests.Request], line: Outcome) -> None:
    """The queue learns what the run did; a request whose source raised failed (the run's other sources may have gone on)."""
    if not requests:
        return
    broken = [r for r in requests if r.parsing and any(name.split(" (")[0] == r.source for name in line.failed)]
    parse_requests.finish([r for r in requests if r not in broken], line.kind, str(line))
    parse_requests.finish(broken, "error", str(line), failed=True)


def pause(seconds: float) -> None:
    """The sleep of --loop, cut short by a request in the queue."""
    end = time.monotonic() + seconds
    while (left := end - time.monotonic()) > 0 and not parse_requests.waiting():
        time.sleep(min(REQUEST_POLL, left))


def main(args: Namespace) -> None:
    names, sites = args.source, getattr(args, "site", None)
    if sites and "sites" not in (names or []):
        names = [*(names or []), "sites"]  # (--site is the source `sites`, limited to these sites)
    if args.build:
        names = names or ["build-only"]  # no source is asked (a name that is none): the documents are rebuilt from the data
    lock = pg.connect()
    lock.autocommit = True
    if not lock.execute("SELECT pg_try_advisory_lock(%s) AS got", (LOCK_ID,)).fetchone()["got"]:
        sys.exit("another run of catix-docs is going on")
    while True:
        started = datetime.now(timezone.utc)
        requests = parse_requests.take()
        asked, limited = with_requests(names, sites, requests, load_state(), started)
        if requests:
            print(f"[{started:%Y-%m-%d %H:%M}] requests: {', '.join(r.describe() for r in requests)}", flush=True)
        try:
            line = run_once(asked, sites=limited)
            print(f"[{started:%Y-%m-%d %H:%M}] {line}", flush=True)
            served(requests, line)
        except Exception as e:  # noqa: BLE001 - the loop keeps going; the next run tries again
            traceback.print_exc()
            parse_requests.finish(requests, "error", f"the run failed: {type(e).__name__}: {e}", failed=True)
        if not args.loop:
            return
        names, sites = None, None  # (--source and --site ask now; the loop then follows the schedule)
        state = load_state()
        waits = [datetime.fromisoformat(state["asked"][s.name]) + s.every - datetime.now(timezone.utc) for s in sources.SOURCES if s.name in state.get("asked", {})]
        pause(max(60.0, min([IDLE, *waits]).total_seconds()))
