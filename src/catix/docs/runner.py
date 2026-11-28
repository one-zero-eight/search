"""The documents maintain themselves: the crawl reads the address that is due next, and what changed becomes documents in Postgres.

    catix-docs run [--loop] [--source NAME ...] [--site NAME ...] [--build]

The crawl (frontier.py) is one table of addresses, each with the time it is read again (pages and documents every week, the feeds
of a site every 6 hours, those it asked for first). Every turn of the loop:
  1. the requests waiting in the queue (POST /{section}/parse of the API, parse_requests.py): `sites` asks for the rows of those
     sites to be read first (frontier.request), a new site is added to the catalog and its rows are read first, the eduwiki is
     read now; the run says in the queue what it did once nothing is asked for any more;
  2. the jobs that are due (sources.JOBS: the eduwiki, the course programmes; each with its own interval);
  3. one step: the row that is due next, a page or a listing (sites.read_page, sites.read_listing), or the documents due (a batch
     of rows: regulations.recheck); the thread of the OCR queue (ocr_worker.py) reads the scans beside it;
  4. the requests whose rows are all read are finished, after the documents they changed are rebuilt;
  5. every FLUSH seconds the groups of documents that changed are rebuilt (build.rebuild(groups)): a changed page reaches the
     search in minutes, and only its site's documents are made again; every day the sweep (frontier.sweep) drops what no page
     links any more, and every document is made again;
  6. nothing due: without `--loop` the run ends; with it, it sleeps until the next row falls due (REQUEST_POLL at most).
`--source NAME ...` runs those jobs now, once; `--site NAME ...` reads those sites' rows first and ends when they are read
(like a request); `--build` rebuilds every document from the tables and ends.
Runs one at a time (an advisory lock of Postgres). Its state (when each job was asked, the scans the admins were told of, when the
sweep was) is in docs_meta, key 'runner'. Under `--loop` the OCR thread (ocr_worker.py) reads the scans queued, and the guide of the
repo (sources/guide.py) is synced once at the start; one request at a time to a host across the threads (sources/hosts.py).
OCR: the sources queue scans for the OCR thread and put aside those too long for it (sources/ocr_queue.py); when either grows,
the admins are told in Telegram, of each scan once.
"""

import json
import sys
import time
import traceback
from argparse import Namespace
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import httpx

from catix import admins
from catix.db import pg
from catix.docs import build, frontier, parse_requests, sources, store
from catix.docs.sources import hosts, regulations, rpd, sites
from catix.settings import settings

LOCK_ID = 7_301_001  # pg_try_advisory_lock key of catix-docs run
REQUEST_POLL = 30  # seconds between two looks of the sleeping --loop at the queue of requests and the due rows
FLUSH = 120  # seconds between two rebuilds of the documents that changed
SESSION_RETELL = timedelta(days=7)  # an ended login is told again this often while it lasts


def load_state() -> dict:
    with pg.connection() as conn:
        row = conn.execute("SELECT value FROM docs_meta WHERE key = 'runner'").fetchone()
    return json.loads(row["value"]) if row else {}


def save_state(state: dict) -> None:
    with pg.connection() as conn:
        conn.execute("INSERT INTO docs_meta (key, value) VALUES ('runner', %s) ON CONFLICT (key) DO UPDATE SET value = excluded.value",
                     (json.dumps(state, ensure_ascii=False),))


def tell_ended_sessions(state: dict) -> None:
    """The admins told of the sites whose login ended (sites.ENDED), each again after SESSION_RETELL while it lasts."""
    ended, sites.ENDED = dict(sites.ENDED), {}
    told, now = state.setdefault("session_told", {}), datetime.now(timezone.utc)
    for name in ended:
        if name in told and now - datetime.fromisoformat(told[name]) < SESSION_RETELL:
            continue
        tell_admins(f"🔑 Сайт {name} ({sites.SITES[name].base}) не прочитан: закончилась сессия входа в его профиле Chromium. "
                    "Остальные сайты прочитаны. Войдите в профиль заново и скопируйте его в /app/data/chromium-profile тома catix_data (DEPLOY.md).")
        told[name] = now.isoformat(timespec="seconds")
    if ended:
        save_state(state)


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
        ids = admins.telegram_ids() if settings.database_url else list(settings.admin_telegram_ids)
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


def pause(seconds: float) -> None:
    """The sleep of --loop, cut short by a request in the queue."""
    end = time.monotonic() + seconds
    while (left := end - time.monotonic()) > 0 and not parse_requests.waiting():
        time.sleep(min(REQUEST_POLL, left))


def sync_guide() -> None:
    """At the start of the loop: the guide of the repo indexed (sources/guide.py); a failure is logged, the loop goes on."""
    try:
        counts = build.sync_guide()
    except Exception:  # noqa: BLE001 - a broken guide must not stop the crawl
        traceback.print_exc()
        return
    print(f"== guide/: {counts}", flush=True)


@dataclass
class Serving:
    """Requests whose rows the crawl reads first: they are finished when no row of `sites` is asked for any more."""

    requests: list[parse_requests.Request]
    sites: list[str]
    new_site: str | None = None  # the name of the site a new-site request added
    counts: Counter = field(default_factory=Counter)  # what the rebuilds since it began did to the documents
    ended: set[str] = field(default_factory=set)  # of its sites, those whose login ended meanwhile


def counts_line(counts: Counter) -> str:
    return (f"documents: {counts['pages new']} new, {counts['pages changed']} changed, {counts['pages removed']} removed; "
            f"{store.queued()} pieces wait for a vector")


class Run:
    """The state of one run of the loop: what changed and is not rebuilt yet, the requests being served."""

    def __init__(self, loop: bool) -> None:
        self.loop = loop
        self.state = load_state()
        self.dirty: set[str] = set()
        self.servings: list[Serving] = []
        self.flushed = time.monotonic()
        self.profile: str | None = None  # the site behind a login the last row was of: its browser stays open for its next rows

    # -- requests

    def serving_ids(self) -> set[str]:
        return {r.id for s in self.servings for r in s.requests}

    def take_requests(self) -> None:
        requests = parse_requests.take(self.serving_ids())
        if not requests:
            return
        print(f"[{datetime.now(timezone.utc):%Y-%m-%d %H:%M}] requests: {', '.join(r.describe() for r in requests)}", flush=True)
        plain = [r for r in requests if r.parsing and r.source == "sites"]
        for request in requests:
            if not request.parsing:  # (nothing is read: the documents are made again from what the tables hold)
                self.finish_with_rebuild(request, None)
            elif request.source == "eduwiki":
                self.finish_with_rebuild(request, "eduwiki")
            elif request.source == "new-site":
                self.add_site(request)
        if plain:
            names = list(dict.fromkeys(n for r in plain for n in (r.sites or list(sites.SITES))))
            sites.reload_catalog()
            known = [n for n in names if n in sites.SITES]
            if gone := [n for n in names if n not in sites.SITES]:
                print(f"  not in the catalog of sites (passed by): {', '.join(gone)}", flush=True)
            frontier.request(known)
            self.servings.append(Serving(plain, known))

    def finish_with_rebuild(self, request: parse_requests.Request, job: str | None) -> None:
        """A request of the eduwiki (the job runs now) or without parsing (nothing is read): the documents are rebuilt, the request told."""
        try:
            if job:
                next(j for j in sources.JOBS if j.name == job).run()
            counts = Counter(build.rebuild({job}) if job else build.rebuild())
        except Exception as e:  # noqa: BLE001 - the loop goes on; the request says why
            traceback.print_exc()
            parse_requests.finish([request], "error", f"the run failed: {type(e).__name__}: {e}", failed=True)
            return
        changed = counts["pages new"] + counts["pages changed"] + counts["pages removed"]
        parse_requests.finish([request], "changed" if changed else "unchanged", counts_line(counts))

    def add_site(self, request: parse_requests.Request) -> None:
        """A request for a new site: the site is added to the catalog and its rows are read first. A name the catalog refuses fails the
        request, and the admins are told."""
        try:
            name = sites.add_site(request.url, request.sites[0] if request.sites else None)
        except Exception as e:  # noqa: BLE001 - the loop goes on; the request says why
            traceback.print_exc()
            text = f"{request.url}: {type(e).__name__}: {str(e)[:300]}"
            parse_requests.finish([request], "error", text, failed=True)
            tell_admins(f"Новый сайт не прочитан: {text}")
            return
        frontier.seed()
        frontier.request([name])
        self.servings.append(Serving([request], [name], new_site=name))

    def finish_servings(self) -> None:
        done = [s for s in self.servings if not frontier.requested(s.sites)]
        if not done:
            return
        self.flush(force=True)
        for serving in done:
            self.servings.remove(serving)
            changed = serving.counts["pages new"] + serving.counts["pages changed"] + serving.counts["pages removed"]
            kind = "error" if serving.ended else "changed" if changed else "unchanged"
            line = counts_line(serving.counts) + (f" (the login ended: {', '.join(sorted(serving.ended))})" if serving.ended else "")
            if serving.new_site:
                self.finish_new_site(serving, kind, line)
            else:
                parse_requests.finish(serving.requests, kind, line, failed=kind == "error")
            print(f"[{datetime.now(timezone.utc):%Y-%m-%d %H:%M}] {line}", flush=True)

    def finish_new_site(self, serving: Serving, kind: str, line: str) -> None:
        report = sites.new_site_report(serving.new_site or "")
        print(report.report(), flush=True)
        if not report.pages:
            parse_requests.finish(serving.requests, "error", report.report(), failed=True)
            tell_admins(f"Новый сайт {report.name} добавлен в каталог, но не прочитан: {report.report()}")
            return
        parse_requests.finish(serving.requests, kind, f"{report.report()}; {line}", failed=kind == "error")
        tell_admins(f"Новый сайт {report.name}: {report.report()}")

    # -- jobs

    def run_jobs(self, only: list[str] | None = None) -> None:
        """The jobs that are due (`only`: those named, now)."""
        now = datetime.now(timezone.utc)
        asked = self.state.setdefault("asked", {})
        for job in sources.JOBS:
            if only is not None:
                if job.name not in only:
                    continue
            elif job.name in asked and now - datetime.fromisoformat(asked[job.name]) < job.every:
                continue
            print(f"== job {job.name}", flush=True)
            try:
                changed = job.run()
            except Exception:  # noqa: BLE001 - one job failing must not stop the others; it is asked again next time
                traceback.print_exc()
                continue
            asked[job.name] = now.isoformat(timespec="seconds")
            save_state(self.state)
            if changed:
                self.dirty.add(job.group)

    # -- the crawl

    def step(self, client: httpx.Client) -> bool:
        """Read the row that is due next; whether there was one. The documents are not read while another thread (the OCR) reads."""
        free = regulations.READ_LOCK.acquire(blocking=False)
        try:
            if (row := frontier.next_due(documents=free)) is None:
                return False
            if self.profile and self.profile != row.site:
                sites.close_live()  # (a browser kept open for one site's pages one after another)
            self.profile = row.site if sites.SITES.get(row.site) and sites.SITES[row.site].profile else None
            rows = [row]
            try:
                if row.kind == "page":
                    if sites.read_page(client, row):
                        self.dirty.add(f"sites/{row.site}")
                elif row.kind == "listing":
                    sites.read_listing(client, row)
                else:
                    rows = [row, *frontier.due_documents(frontier.DOC_BATCH - 1, row.priority, row.address)]
                    self.read_documents(rows)
            except sites.SessionEnded as e:
                sites.ENDED[row.site] = str(e)
                print(f"  {row.site}: {e}; its rows wait, the other sites go on", flush=True)
                frontier.postpone(row.site, frontier.SOON)
            except Exception as e:  # noqa: BLE001 - one address failing (its browser, its server) leaves the others to read
                traceback.print_exc()
                for r in rows:
                    if r.state == "new":
                        frontier.save(r, state="tried", why=f"{type(e).__name__}: {e}"[:200], next_at=frontier.later(frontier.RETRY))
                    else:
                        frontier.save(r, next_at=frontier.later(frontier.SOON))
            return True
        finally:
            if free:
                regulations.READ_LOCK.release()

    def read_documents(self, rows: list[frontier.Row]) -> None:
        """A batch of document rows due: the course archives are the course programmes' (the job `rpd` reads them), the rest is read
        again (regulations.recheck)."""
        courses = {sites.address(a["url"]) for a in rpd.archives()}
        for row in rows:
            if row.address in courses:
                frontier.save(row, state="ok", why=None, next_at=frontier.later(frontier.DOCUMENT_EVERY))
        rest = [row for row in rows if row.address not in courses]
        if not rest:
            return
        done = regulations.recheck([row.doc_key for row in rest if row.doc_key])
        for row in frontier.still_due(rest):  # (a document the bundle does not have, any more: asked again after SOON)
            frontier.save(row, next_at=frontier.later(frontier.SOON))
        if done:
            self.dirty.add("regulations")

    # -- the documents

    def flush(self, force: bool = False) -> None:
        """The documents of the groups that changed made again; the admins told what they should be."""
        if not self.dirty or not (force or time.monotonic() - self.flushed >= FLUSH):
            return
        groups, self.dirty = self.dirty, set()
        try:
            counts = build.rebuild(groups)
        except Exception:  # noqa: BLE001 - the loop goes on; the groups are made again at the next flush
            traceback.print_exc()
            self.dirty |= groups
            return
        self.flushed = time.monotonic()
        for serving in self.servings:
            serving.counts.update(counts)
        print(f"[{datetime.now(timezone.utc):%Y-%m-%d %H:%M}] flush: documents: {counts.get('pages new', 0)} new, {counts.get('pages changed', 0)} changed, "
              f"{counts.get('pages removed', 0)} removed", flush=True)
        self.tell()

    def tell(self) -> None:
        """What the admins should know: the logins that ended, the scans that wait."""
        for serving in self.servings:
            serving.ended |= {name for name in sites.ENDED if name in serving.sites}
        for report in (tell_ended_sessions, tell_ocr_queue):
            try:
                report(self.state)
            except Exception:  # noqa: BLE001 - the report must not stop the run
                traceback.print_exc()

    def sweep(self) -> None:
        """Once a day: what no page links any more is dropped (frontier.sweep), and every document made again."""
        now = datetime.now(timezone.utc)
        swept = self.state.get("swept_at")
        if swept is None:  # (the first run: the clock starts, nothing is dropped before a day of reading)
            self.state["swept_at"] = now.isoformat(timespec="seconds")
            save_state(self.state)
            return
        if now - datetime.fromisoformat(swept) < frontier.SWEEP_EVERY:
            return
        print(f"== sweep: {frontier.sweep()}", flush=True)
        self.state["swept_at"] = now.isoformat(timespec="seconds")
        save_state(self.state)
        build.rebuild()
        self.flushed = time.monotonic()


def run(args: Namespace) -> None:
    """The run without its lock: the tables of the old store imported once, the rows of the catalog seeded, then the loop."""
    frontier.ensure_imported()
    frontier.seed()
    if args.build:
        print(build.rebuild())
        return
    crawl = Run(args.loop)
    if args.loop:
        from catix.docs import ocr_worker

        sync_guide()
        ocr_worker.start()  # (the OCR queue is read as scans arrive, beside the crawl)
        build.rebuild()
    if args.source:
        if unknown := [n for n in args.source if n not in {j.name for j in sources.JOBS}]:
            print(f"no job {', '.join(unknown)}: the jobs are {', '.join(j.name for j in sources.JOBS)}", flush=True)
        crawl.run_jobs(args.source)
    if args.site:
        sites.reload_catalog()
        known = [n for n in args.site if n in sites.SITES]
        if gone := [n for n in args.site if n not in sites.SITES]:
            print(f"no site {', '.join(gone)}: the sites are {', '.join(sites.SITES)}", flush=True)
        frontier.request(known)
        crawl.servings.append(Serving([], known))
    once = bool(args.source or args.site)
    if args.source and not args.site and not args.loop:  # (the jobs named, now, once)
        crawl.flush(force=True)
        return
    with sites.client() as client:
        try:
            while True:
                crawl.take_requests()
                if args.loop or not once:
                    crawl.run_jobs()
                stepped = crawl.step(client)
                crawl.finish_servings()
                crawl.flush()
                crawl.sweep()
                if once and not crawl.servings and not args.loop:
                    crawl.flush(force=True)
                    return
                if not stepped:
                    if not args.loop:
                        crawl.flush(force=True)
                        crawl.tell()
                        return
                    wake = frontier.next_wake()
                    pause(REQUEST_POLL if wake is None else max(1.0, min(REQUEST_POLL, (wake - datetime.now(timezone.utc)).total_seconds())))
        finally:
            sites.close_live()


def main(args: Namespace) -> None:
    lock = pg.connect()
    lock.autocommit = True
    if not lock.execute("SELECT pg_try_advisory_lock(%s) AS got", (LOCK_ID,)).fetchone()["got"]:
        sys.exit("another run of catix-docs is going on")
    hosts.share()  # (the crawl and the OCR thread read the same hosts: one request at a time to each, and the pauses of the sites)
    run(args)
