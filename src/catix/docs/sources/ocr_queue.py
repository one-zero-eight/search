"""The OCR queue: the scans every source keeps for tesseract, and, apart from it, the scans too long for OCR.

    catix-docs regs queue

The scheduled runs read documents by their text layer only: a scan (a PDF whose text layer gives too little) is queued
for the OCR thread of `catix-docs run --loop` (and a manual run: `catix-docs regs fetch`), which reads it by Tesseract.
A scan longer than the limit (regulations.MAX_OCR_PAGES) is not queued: it
would wait there for ever, so it is put aside (`"ocr": "too long"`) and listed apart, for a person to decide.

The run tells the admins in Telegram when the queue or the scans put aside grow (runner.tell_ocr_queue, with
`message`): once for each new scan, not at every run. On the server a manual run is
`docker compose -f docker-compose.prod.yml run --rm docs catix-docs regs fetch`.
"""

from dataclasses import dataclass

from catix.docs.sources import regulations

MAX_NAMED = 5  # new scans a message names; the others are counted
MAX_TITLE = 90


@dataclass(frozen=True)
class Scan:
    source: str  # "regs": a document of the regulations, sites, archives
    key: str
    title: str
    url: str
    pages: int
    too_long: bool  # put aside, not in the queue
    since: str = ""  # when it was queued or put aside (ISO), "" when not known
    failed: int = 0  # times tesseract could not read it


def scans() -> list[Scan]:
    """Every scan queued for OCR or put aside as too long, of every source."""
    out = [Scan("regs", key, d.get("title") or note.get("title", ""), d.get("url") or note.get("url", ""), note.get("pages", 0),
                regulations.ocr_state(note) == regulations.TOO_LONG, note.get("queued_at", ""), note.get("ocr_failed", 0))
           for key, d, note in regulations.scan_notes()]
    return sorted(out, key=lambda s: (s.too_long, s.source, s.since, s.key))


def _pages(found: list[Scan]) -> int:
    return sum(s.pages for s in found)


def _count(found: list[Scan]) -> str:
    return f"{len(found)} {'scan' if len(found) == 1 else 'scans'}, {_pages(found)} pages"


RUN = {"regs": ("documents", f"catix-docs regs fetch, up to {regulations.OCR_BUDGET} pages a run")}


def _lines(found: list[Scan]) -> None:
    for s in found:
        print(f"  {s.pages:>4} p  {s.since[:10] or '?':<10}  {s.source:<6}  {s.key}" + (f"  (tesseract failed {s.failed}x)" if s.failed else ""))
        print(f"{'':>8}{s.title[:120]}  {s.url}")


def show(found: list[Scan] | None = None) -> None:
    """The queue and, apart, the scans put aside, printed: what waits for OCR and which run reads it, what no run reads."""
    found = scans() if found is None else found
    queue, apart = [s for s in found if not s.too_long], [s for s in found if s.too_long]
    print(f"OCR queue: {_count(queue)}" + (" (read by Tesseract: the OCR thread of catix-docs run --loop, or a manual run)" if queue else ""))
    for source, (what, run) in RUN.items():
        if mine := [s for s in queue if s.source == source]:
            print(f"  {what}: {_count(mine)} ({run})")
    _lines(queue)
    print(f"Too long for OCR, put aside, not queued: {_count(apart)} (over {regulations.MAX_OCR_PAGES} pages a document; no run reads them)")
    _lines(apart)


def _scans_ru(n: int) -> str:
    return f"{n} " + ("скан" if n % 10 == 1 and n % 100 != 11 else "скана" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else "сканов")


def _named(found: list[Scan]) -> str:
    names = [f"• {s.title[:MAX_TITLE]}{'…' if len(s.title) > MAX_TITLE else ''} ({s.pages} стр.)" for s in found[:MAX_NAMED]]
    return "\n".join(names + ([f"• и ещё {len(found) - MAX_NAMED}"] if len(found) > MAX_NAMED else []))


def message(found: list[Scan], new: set[tuple[str, str]]) -> str | None:
    """What the admins are told of the scans `new` ((source, key) not told yet) among all `found`; None when none is new."""
    queue, apart = [s for s in found if not s.too_long], [s for s in found if s.too_long]
    new_queue, new_apart = [s for s in queue if (s.source, s.key) in new], [s for s in apart if (s.source, s.key) in new]
    if not new_queue and not new_apart:
        return None
    parts = []
    if new_queue:
        runs = ["catix-docs regs fetch"]
        more = f" (новые: {_scans_ru(len(new_queue))}, {_pages(new_queue)} стр.)" if len(new_queue) < len(queue) else ""
        parts.append(f"🖨 Очередь OCR выросла: {_scans_ru(len(queue))}, {_pages(queue)} стр.{more}:\n"
                     f"{_named(new_queue)}\nИх читает OCR-поток catix-docs run --loop (Tesseract) по мере поступления; вручную: {' и '.join(runs)} "
                     f"(за прогон до {regulations.OCR_BUDGET} стр.); на проде: docker compose -f docker-compose.prod.yml run --rm docs <команда>.")
    if new_apart:
        more = f" (новые: {_scans_ru(len(new_apart))}, {_pages(new_apart)} стр.)" if len(new_apart) < len(apart) else ""
        parts.append(f"📕 Слишком длинные для OCR сканы отложены, в очереди их нет: {_scans_ru(len(apart))}, {_pages(apart)} стр.{more}:\n"
                     f"{_named(new_apart)}\nИх не прочитает ни один прогон: лимит — {regulations.MAX_OCR_PAGES} стр. на документ.")
    return "\n\n".join(parts) + "\nСписок: catix-docs regs queue"
