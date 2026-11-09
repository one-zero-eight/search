"""Source citations built in code, because small models do not reliably name their sources.

The sources of a conversation live in the graph state (`sources`, next to `messages`): a tool that finds a chat message
registers it and puts the ref it gets (m0, m1, ... in the order the messages reach the model, over the whole
conversation) next to the message; the registry is saved with the history and dropped with it (`/clear`). The model copies
refs next to the facts it uses; `cite` replaces them by [1], [2], ... and returns structured sources. Only refs of this
conversation's registry are honoured, so a made-up or injected ref can neither leak a message nor produce a fake source.
A source is described by its fields, not by a database row, so a message found live in Telegram can be cited too.
"""

import logging
import re
import threading
import time
from datetime import datetime

from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from catix.common.citations import AnswerSource, CitationLink, CitedAnswer
from catix.db import store
from catix.wiki import previews

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
        fields = {"wiki": True, "title": hit.title, "clause": hit.clause, "section": hit.heading, "link": hit.resource, "trust": hit.trust,
                  "site": hit.path.startswith("/raw/sites/"),
                  "based_on": [{"title": b["title"], "link": b["link"]} for b in hit.based_on if b.get("link")][:2]}
        if document := previews.describe(hit.path, hit.page_sha, hit.resource or ""):
            fields["archive_document"] = document
            return self._add(f"wiki:{hit.id}:{hit.page_sha}", fields)
        return self._add(f"wiki:{hit.id}", fields)

    def add_web(self, title: str, url: str, official: bool) -> str:
        """A page found on the web (agent/web_tools.py): one source per page, whatever was quoted from it."""
        return self._add(f"web:{url}", {"web": True, "title": title, "link": url, "official_site": official})

    def result(self, payload: dict, tool_name: str, artifact: dict | None = None) -> Command:
        """The tool's result for the model, and the new sources for the state; `artifact` goes with it, unseen by the model."""
        import json

        message = ToolMessage(content=json.dumps(payload, ensure_ascii=False, default=str), tool_call_id=self.runtime.tool_call_id,
                              name=tool_name, artifact=artifact)
        return Command(update={"messages": [message], "sources": self.new})


def _identity(ref: str, source: dict) -> object:
    """What one number of the source list stands for: a chat message, or a whole document of the wiki (its clauses are listed
    in its one line, so that twelve clauses of one regulation do not make twelve lines)."""
    if source.get("web"):
        return ("web", source.get("link"))
    if document := source.get("archive_document"):
        return ("archive", document["page"], document["revision"], document["member"])
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


def cite(answer: str, registry: dict[str, dict]) -> CitedAnswer:
    """Number only cited, resolvable sources and return their structured provenance."""
    # Resolve before capping and numbering: a deleted database row must neither leave
    # a dangling citation nor consume one of the MAX_RUN slots.
    referenced = {ref for group in GROUP_RE.findall(answer) for ref in re.findall(r"m\d+", group)}
    cited = {ref: source for ref, source in registry.items() if ref in referenced}
    message_ids = list(dict.fromkeys(source["message_id"] for source in cited.values() if source.get("message_id")))
    stored = store.message_sources(message_ids) if message_ids else {}
    resolved = {}
    for ref, source in cited.items():
        if source.get("message_id"):
            row = stored.get(source["message_id"])
            if not row:
                continue
            source = {
                "chat_title": row.chat_title, "link": row.link or row.chat_link,
                "date": row.date, "author": row.sender_name, "sender_link": row.sender_link, "official": row.chat_official,
            }
        resolved[ref] = source

    numbers: dict[object, int] = {}
    entries: dict[object, AnswerSource] = {}

    def renumber(match: re.Match) -> str:
        used: set[int] = set()
        for ref in re.findall(r"m\d+", match.group(1)):
            if ref not in resolved:
                log.warning("dropping unknown or unavailable source ref %s", ref)
                continue
            source = resolved[ref]
            key = _identity(ref, source)
            number = numbers.setdefault(key, len(numbers) + 1)
            used.add(number)
            if key not in entries:
                entries[key] = _source(number, source)
            entry = entries[key]
            clause, section = source.get("clause"), source.get("section")
            if clause and clause not in entry.clauses:
                entry.clauses.append(clause)
            if section and not clause and section not in entry.sections:
                entry.sections.append(section)
            for based in source.get("based_on") or []:
                if based.get("link") and not any(item.title == based["title"] and item.url == based["link"] for item in entry.based_on):
                    entry.based_on.append(CitationLink(title=based["title"], url=based["link"]))
        return f"[{', '.join(map(str, sorted(used)))}]" if used else ""

    answer = GROUP_RE.sub(renumber, RUN_RE.sub(lambda run: _capped(run, resolved), answer))
    answer = re.sub(r"(\[\d+(?:, \d+)*\])(?:\s*\1)+", r"\1", answer)
    answer = re.sub(r"[ \t]+([.,;:!?])", r"\1", answer)
    return CitedAnswer(answer=answer.strip(), sources=list(entries.values()))


def _source(number: int, source: dict) -> AnswerSource:
    if source.get("web"):
        return AnswerSource(number=number, title=source.get("title") or source.get("link") or "", url=source.get("link"),
                            kind="web", official=bool(source.get("official_site")))
    if source.get("wiki"):
        trust = source.get("trust")
        kind = "official_document" if trust == "official" else "guide" if trust == "guide" else "website" if source.get("site") else "eduwiki"
        return AnswerSource(number=number, title=source["title"], url=source.get("link"), kind=kind,
                            archive_document=source.get("archive_document"), official=trust == "official")
    return AnswerSource(number=number, title=source["chat_title"], url=source.get("link"), kind="chat",
                        date=source.get("date"), author=FORWARDER_RE.sub("", source.get("author") or "") or None,
                        author_url=source.get("sender_link"), official=bool(source.get("official")))
