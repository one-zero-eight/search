"""Source citations built in code, because small models do not reliably name their sources.

The sources of a conversation live in the graph state (`sources`, next to `messages`): a tool that finds a chat message
registers it and puts the ref it gets (m0, m1, ... in the order the messages reach the model, over the whole
conversation) next to the message; the registry is saved with the history and dropped with it (`/clear`). The model copies
refs next to the facts it uses; `cite` replaces them by [1], [2], ... and appends the source list. Only refs of this
conversation's registry are honoured, so a made-up or injected ref can neither leak a message nor produce a fake source.
A source is described by its fields, not by a database row, so a message found live in Telegram can be cited too.
"""

import logging
import re
import threading
import time
from datetime import datetime
from urllib.parse import urlsplit

from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from catix.db import store
from catix.settings import settings

log = logging.getLogger("catix.sources")

# [m0], [m0, m1], [ m0 ; m1 ]
GROUP_RE = re.compile(r"\[\s*(m\d+(?:\s*[,;]\s*m\d+)*)\s*\]")
RUN_RE = re.compile(rf"{GROUP_RE.pattern}(?:[ \t]*{GROUP_RE.pattern})*")  # [m6][m11] [m12]: refs at one place of the answer
MAX_RUN = 5  # Sources at one place: a claim needs a few, and of 28 in a row ("что такое пчз?") none would be opened.
FORWARDER_RE = re.compile(r"\s*\(forwarded by .*\)$")
MAX_SOURCES = 300  # A very long conversation forgets its oldest sources (their refs are then dropped as unknown).


def merge_sources(left: dict | None, right: dict | None) -> dict:
    """The state reducer: sources are only ever added (the newest MAX_SOURCES are kept)."""
    merged = {**(left or {}), **(right or {})}
    if len(merged) > MAX_SOURCES:
        newest = sorted(merged, key=lambda ref: int(ref[1:]))[-MAX_SOURCES:]
        merged = {ref: merged[ref] for ref in newest}
    return merged


# Refs given out in the last seconds but not yet merged into the state: tools of one step run in parallel and each of
# them sees the state as it was before the step.
_PENDING: dict[str, tuple[float, int]] = {}
_LOCK = threading.Lock()
PENDING_SECONDS = 60


def _next_index(thread: str, known: dict) -> int:
    base = max((int(ref[1:]) for ref in known), default=-1) + 1
    with _LOCK:
        stamp, pending = _PENDING.get(thread, (0.0, 0))
        n = max(base, pending) if time.monotonic() - stamp < PENDING_SECONDS else base
        _PENDING[thread] = (time.monotonic(), n + 1)
        if len(_PENDING) > 2000:  # Threads of inline questions come and go.
            for old in sorted(_PENDING, key=lambda k: _PENDING[k][0])[:1000]:
                del _PENDING[old]
        return n


class Collector:
    """The sources one tool call finds: hands out refs now, builds the state update to return with the result."""

    def __init__(self, runtime: ToolRuntime) -> None:
        self.runtime = runtime
        self.known: dict[str, dict] = dict(runtime.state.get("sources") or {})
        self.thread = str((runtime.config.get("configurable") or {}).get("thread_id", "")) if runtime.config else ""
        self.by_key = {source["key"]: ref for ref, source in self.known.items()}
        self.new: dict[str, dict] = {}

    def _add(self, key: str, fields: dict) -> str:
        if key not in self.by_key:  # The same message found again keeps its ref.
            ref = f"m{_next_index(self.thread, {**self.known, **self.new})}"
            self.by_key[key] = ref
            self.new[ref] = {"key": key, **fields}
        return self.by_key[key]

    def add_db(self, message_id: int | None) -> str | None:
        return self._add(f"db:{message_id}", {"message_id": message_id}) if message_id else None

    def add_live(self, chat_id: int, msg_id: int, *, chat_title: str, link: str | None, date: datetime, author: str | None, sender_link: str | None = None) -> str:
        fields = {"chat_title": chat_title, "link": link, "date": date.isoformat(), "author": author, "sender_link": sender_link}
        return self._add(f"live:{chat_id}:{msg_id}", fields)

    def add_wiki(self, hit) -> str:
        """A piece of the wiki (db/wiki.py WikiHit): the document, the clause and the original, so that the source line
        points to the university's own document; a guide's piece names the documents it rests on."""
        fields = {"wiki": True, "title": hit.title, "clause": hit.clause, "link": hit.resource, "trust": hit.trust,
                  "site": hit.path.startswith("/raw/sites/"),
                  "based_on": [{"title": b["title"], "link": b["link"]} for b in hit.based_on if b.get("link")][:2]}
        return self._add(f"wiki:{hit.id}", fields)

    def result(self, payload: dict, tool_name: str, artifact: dict | None = None) -> Command:
        """The tool's result for the model, and the new sources for the state; `artifact` goes with it, unseen by the model."""
        import json

        message = ToolMessage(content=json.dumps(payload, ensure_ascii=False, default=str), tool_call_id=self.runtime.tool_call_id,
                              name=tool_name, artifact=artifact)
        return Command(update={"messages": [message], "sources": self.new})


def _identity(ref: str, source: dict) -> object:
    """What one number of the source list stands for: a chat message, or a whole document of the wiki (its clauses are listed
    in its one line, so that twelve clauses of one regulation do not make twelve lines)."""
    return ("wiki", source.get("title"), source.get("link")) if source.get("wiki") else ref


def _capped(run: re.Match, registry: dict[str, dict]) -> str:
    """A run of refs with at most MAX_RUN sources, the first ones written. Such runs came of a helper that cited every message
    of a channel for one sentence, and of final_answer, which puts all refs of the reports under an answer that lost them."""
    refs = re.findall(r"m\d+", run.group(0))
    keys = list(dict.fromkeys(_identity(ref, registry[ref]) for ref in refs if ref in registry))
    if len(keys) <= MAX_RUN:
        return run.group(0)
    log.info("a run of %d sources is cut to %d", len(keys), MAX_RUN)
    kept = set(keys[:MAX_RUN])
    return "".join(f"[{ref}]" for ref in dict.fromkeys(refs) if ref in registry and _identity(ref, registry[ref]) in kept)


def cite(answer: str, registry: dict[str, dict]) -> str:
    """Replace refs in the answer by numbers and append the numbered source list."""
    numbers: dict[object, int] = {}
    first: dict[object, str] = {}  # identity -> the first ref of it (its source fields)
    clauses: dict[object, list[str]] = {}

    def renumber(match: re.Match) -> str:
        used: set[int] = set()
        for item in re.findall(r"m\d+", match.group(1)):
            if item in registry:
                key = _identity(item, registry[item])
                used.add(numbers.setdefault(key, len(numbers) + 1))
                first.setdefault(key, item)
                clause = registry[item].get("clause")
                if clause and clause not in clauses.setdefault(key, []):
                    clauses[key].append(clause)
            else:
                log.warning("dropping unknown source ref %s", item)
        return f"[{', '.join(map(str, sorted(used)))}]" if used else ""

    answer = GROUP_RE.sub(renumber, RUN_RE.sub(lambda run: _capped(run, registry), answer))
    answer = re.sub(r"(\[\d+(?:, \d+)*\])(?:\s*\1)+", r"\1", answer)  # [1][1]: two clauses of one document became one number
    answer = re.sub(r"[ \t]+([.,;:!?])", r"\1", answer)  # Where a dropped ref left a gap.
    if not numbers:
        return answer.strip()

    stored = store.message_sources([s["message_id"] for key in numbers if (s := registry[first[key]]).get("message_id")])
    lines = []
    for key, number in numbers.items():
        source = registry[first[key]]
        if source.get("wiki"):
            source = {**source, "clause": ", ".join(clauses.get(key, []))}
        if source.get("message_id"):
            row = stored.get(source["message_id"])
            if not row:
                continue
            source = {
                "chat_title": row.chat_title, "link": row.link or row.chat_link,  # The chat's own link when the message has none.
                "date": row.date, "author": row.sender_name, "sender_link": row.sender_link, "official": row.chat_official,
            }
        lines.append(_line(number, source))
    if not lines:
        return answer.strip()
    title = "Источники" if re.search(r"[а-яё]", answer.lower()) else "Sources"
    return f"{answer.strip()}\n\n{title}:\n" + "\n".join(lines)


def _link(title: str, link: str | None) -> str:
    title = f"«{title}»"
    return f"[{title.replace('[', '(').replace(']', ')')}]({link})" if link else title


def _wiki_line(number: int, source: dict) -> str:
    """[n] «Положение о …», п. 5.3 (документ университета) — or a guide with the documents it rests on, a page of a site
    (its host: media.innopolis.university) or an eduwiki page."""
    line = f"[{number}] {_link(source['title'], source.get('link'))}" + (f", п. {source['clause']}" if source.get("clause") else "")
    if source.get("trust") == "official":
        return line + " (документ университета)"
    if source.get("trust") == "guide":
        based = ", ".join(_link(b["title"], b["link"]) for b in source.get("based_on") or [])
        return line + " (сводка cAtIx" + (f" по документам: {based})" if based else ")")
    if source.get("site"):
        return line + (f" ({host})" if (host := urlsplit(source.get("link") or "").hostname) else " (сайт)")
    return line + " (eduwiki)"


def _line(number: int, source: dict) -> str:
    if source.get("wiki"):
        return _wiki_line(number, source)
    date = source.get("date")
    when = (datetime.fromisoformat(date) if isinstance(date, str) else date).astimezone(settings.tz) if date else None
    author = FORWARDER_RE.sub("", source.get("author") or "")
    title = f"«{source['chat_title']}»"
    if link := source.get("link"):
        title = f"[{title.replace('[', '(').replace(']', ')')}]({link})"
    line = f"[{number}] {title}" + (" (официальный чат)" if source.get("official") else "") + (f", {when:%d.%m.%Y}" if when else "")
    if author and source.get("sender_link"):
        line += f", [{author.replace('[', '(').replace(']', ')')}]({source['sender_link']})"
    elif author:
        line += f", {author}"
    return line
