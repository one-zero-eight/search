"""LangChain tools for the agent.

Tools return dicts; LangChain serialises them to JSON for the model. Results are
kept compact because they go straight into the model context.
"""

import contextvars
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Literal

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from langgraph.types import Command
from pydantic import BaseModel, Field, SecretStr, field_validator

from catix.agent.api_tools import API_TOOLS
from catix.agent.attachment_tools import ATTACHMENT_TOOLS
from catix.agent.calendar_tools import CALENDAR_TOOLS
from catix.agent import moodle_tools
from catix.agent.moodle_tools import MOODLE_TOOLS
from catix.agent.schedule_tools import get_my_schedule
from catix.agent.web_tools import WEB_TOOLS
from catix.agent.sources import Collector
from catix.common import courses, dates
from catix.common.citations import without_images
from catix import moodle_files
from catix.db import rerank as joint_rerank
from catix.db import store
from catix.db import docs as doc_store
from catix.innohassle import client as innohassle
from catix.settings import settings

MAX_MESSAGES = 15
MAX_MESSAGES_RERANKED = 8  # The reranker picks the best of ~100, so fewer are enough.


@dataclass(frozen=True)
class AgentContext:
    """Per-question context, not visible to the model."""

    # Chats whose messages may be quoted in this answer; None means no restriction (local CLI).
    allowed_chat_ids: frozenset[int] | None = None
    # Telegram id of the asker; None in the local CLI.
    user_telegram_id: int | None = None
    # The asker's study group (from InNoHassle or their own choice); None when unknown (the default `all`).
    study_group: str | None = None
    # All memberships verified by the website; singular study_group is only an unambiguous timetable default.
    verified_study_groups: tuple[str, ...] = ()
    # When the question was asked: the prompts say this time, so that it stays the same for all the model calls of one
    # question (see core.prompt_for).
    asked_at: datetime = field(default_factory=lambda: datetime.now(settings.tz))
    # The asker's InNoHassle token, which only the site has (api/auth.py): shared API tools use it through MCP.
    # Also authorizes local AI Calendar actions. Never kept, never shown; None in the bots and the CLI.
    innohassle_token: SecretStr | None = field(default=None, repr=False)
    # The asker's InNoHassle account on the site: their AI Calendar is kept under it (agent/calendar_tools.py). In the
    # Telegram bot the account linked to `user_telegram_id` is asked for when it is needed.
    innohassle_id: str | None = None
    # The asker's InNoHassle Sport token, which the site sends with a question (api/auth.py verify_asker): shared API tools
    # read their sport and check them in through MCP. Never kept, never shown.
    sport_token: SecretStr | None = field(default=None, repr=False)
    # Private site uploads are bound by the HTTP host, never by model-supplied identity or paths.
    attachment_chat_id: str | None = None
    attachments: tuple[dict, ...] = ()
    current_attachment_ids: tuple[str, ...] = ()


def _fmt(dt: date | datetime) -> str:
    if isinstance(dt, datetime):
        return dt.astimezone(settings.tz).strftime("%Y-%m-%d %H:%M %a")
    return dt.isoformat()


EVENT_POOL = 60


def _message_item(row, collector: Collector, asked: list[str], now: datetime, text_limit: int = 600) -> dict:
    """A chat message as the model sees it, with a ref to cite."""
    item = {
        "ref": collector.add_db(row.ref_id),
        "chat": row.chat_title,
        "official": row.chat_official,  # true only for chats an admin marked official
        "group": row.chat_group,  # `all` (for everybody) or the study group of the chat
        "date": _fmt(row.date),
        "from": row.sender_name,
        # The stamp is in the text itself, so "завтра" is read next to the day it was written on.
        "text": row.text[:text_limit],
    }
    _subject_fields(item, row.text, row.chat_title, asked)
    if row.edit_date:
        item["edited"] = _fmt(row.edit_date)
    if settings.annotate_dates and (resolved := dates.resolve(row.text, row.date, now)):
        item["dates_in_text"] = resolved
    if row.parent_text:
        item["in_reply_to"] = f"{row.parent_sender}: {row.parent_text[:200]}"
    return item


MAX_READ = 50  # messages read_chats returns at most
PERIOD_SCAN = 3000  # messages read_chats reads at most for a period of events, to keep those about its days
READ_TEXT = 300  # characters of a message when it returns more than MAX_MESSAGES: 50 of 600 would fill a third of the context


class ReadChatsArgs(BaseModel):
    chat: str | None = Field(None, description="Part of a chat title or its @username, from the list of chats. Omit for all chats.")
    official_only: bool = Field(False, description="Only the official chats: the announcements of the university.")
    words: list[str] | None = Field(
        None,
        description="Only messages with any of these words, in any form ('тест' also finds 'тесты', 'теста'), Russian and "
        "English ('мидтерм', 'midterm'). Omit to read every message.",
    )
    sender: str | None = Field(None, description="Only messages of the person whose name contains this ('Новиков').")
    date_from: date | None = Field(None, description="YYYY-MM-DD: only messages written on or after this day.")
    date_to: date | None = Field(None, description="YYYY-MM-DD inclusive: only messages written on or before this day.")
    event_from: date | None = Field(
        None,
        description="YYYY-MM-DD: only messages ABOUT an event on or after this day, regardless of publication date "
        "(an olympiad of 15 November announced on 13 October), soonest first. Use for when events happen or work is due; "
        "combine with publication filters only if both axes are explicitly requested.",
    )
    event_to: date | None = Field(None, description="YYYY-MM-DD inclusive: the end of the period the messages are about.")
    limit: int = Field(10, description=f"How many of the newest messages to return, 1 to {MAX_READ}.")

    @field_validator("words", mode="before")
    @classmethod
    def _one_word(cls, value):
        return [value] if isinstance(value, str) else value

    @field_validator("limit", mode="before")
    @classmethod
    def _clamp(cls, value):
        try:
            return min(max(int(value), 1), MAX_READ)
        except (TypeError, ValueError):
            return 10


@tool(args_schema=ReadChatsArgs)
def read_chats(
    runtime: ToolRuntime[AgentContext],
    chat: str | None = None,
    official_only: bool = False,
    words: list[str] | None = None,
    sender: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    event_from: date | None = None,
    event_to: date | None = None,
    limit: int = 10,
) -> Command:
    """List messages of the knowledge-base chats with filters: all of a period, a count, the newest, those of a person or one
    chat. Returns the messages and their `total`; newest first, or soonest event first with event_from/event_to.
    date_from/date_to filter when a message was written; event_from/event_to filter when the event it announces happens or
    work is due (earlier announcements are included). `words` match any form of a word, Russian and English. official_only:
    the university's announcements. `total` counts messages, not events."""
    collector = Collector(runtime)
    now = datetime.now(settings.tz)
    if asks_upcoming(_question(runtime)):  # What is coming starts today, whenever it was written.
        event_from, date_from, date_to = max(event_from or now.date(), now.date()), None, None
        event_to = event_to if event_to and event_to >= event_from else None
    period = (event_from or date.min, event_to or date.max) if event_from or event_to else None
    if period:  # The messages written up to ANNOUNCED_AHEAD_DAYS before it (a few hundred), then those about its days.
        ahead = period[0] - timedelta(days=dates.ANNOUNCED_AHEAD_DAYS) if event_from else None
        date_from = max(filter(None, [date_from, ahead]), default=None)
        date_to = min(filter(None, [date_to, event_to]), default=None)
    found = store.latest(
        chat=chat,
        chat_ids=runtime.context.allowed_chat_ids if runtime.context else None,
        official_only=official_only,
        words=words,
        sender=sender,
        date_from=date_from and date_from.isoformat(),
        date_to=date_to and date_to.isoformat(),
        limit=PERIOD_SCAN if period else limit,
    )
    if found is None:
        return collector.result({"error": f"No chat matches {chat!r}: take a title from the list of chats."}, "read_chats")
    total, rows = found
    if period:
        days = {r.ref_id: dates.first_day_in(r.text, r.date, now, *period) for r in rows}
        rows = sorted((r for r in rows if days[r.ref_id]), key=lambda r: (days[r.ref_id], -r.date.timestamp()))
        total, rows = len(rows), rows[:limit]
    asked = _asked_courses(runtime)
    text_limit = 600 if limit <= MAX_MESSAGES else READ_TEXT
    result = {"total": total, "shown": len(rows), "messages": [_message_item(r, collector, asked, now, text_limit) for r in rows]}
    if total > len(rows):
        which = "soonest" if period else "newest"
        result["note"] = f"The {which} {len(rows)} of {total}: narrow the period or the words, or raise the limit, to see more."
    elif not total and chat:
        result["note"] = "Nothing here: the chat is not stored in the knowledge base."
    return collector.result(result, "read_chats")


# A question about events still to come: "какой ивент будет", "ближайшие дедлайны", "upcoming exams". Its chat searches keep
# only the messages about a day from today on, or naming no day and recent (dates.coming), whatever period the model gives:
# shown "(4 days ago)" next to each date, it still reported events over as coming, and it gave a period one time and not
# the next, so the same question got different answers. A question "what happens if" is not one.
_UPCOMING = re.compile(r"(?<!\w)(?:будет|будут|будем|предстоящ\w*|ближайш\w*|скоро|upcoming|coming|will|next)(?!\w)", re.I)
_EVENT = re.compile(
    r"(?<!\w)(?:ивент|мероприят|событи|фест|концерт|встреч|лекци|семинар|мастер-класс|воркшоп|хакатон|конференц|олимпиад|"
    r"соревновани|турнир|квиз|экзамен|мидтерм|контрольн|тест|зач[её]т|дедлайн|сдач|event|fest|concert|meetup|meeting|"
    r"lecture|seminar|workshop|hackathon|conference|olympiad|contest|competition|tournament|quiz|exam|midterm|test|deadline)",
    re.I,
)
_CONDITIONAL = re.compile(r"(?<!\w)(?:если|if)(?!\w)", re.I)
PAST_LEFT_OUT = (
    "Messages about days already over, and old ones that name no day, were left out: the question is about what is "
    "coming. Do not report past events as coming; if nothing is left, say that nothing coming was found."
)


def asks_upcoming(question: str | None) -> bool:
    """Is it a question about events still to come (and not "what happens if...")?"""
    return bool(question and _UPCOMING.search(question) and _EVENT.search(question) and not _CONDITIONAL.search(question))


def _question(runtime: ToolRuntime[AgentContext]) -> str | None:
    """The user's own question (the last message of theirs), searched as one more angle with double weight."""
    for message in reversed(runtime.state.get("messages", [])):
        if getattr(message, "type", "") == "human":
            return str(message.content)[:300]
    return None


def _asked_courses(runtime: ToolRuntime[AgentContext]) -> list[str]:
    """The courses the user's question names (by any slang or spelling), short names."""
    question = _question(runtime)
    return [c.short for c in courses.hints(question)] if question else []


def _subject_fields(item: dict, text: str, chat_title: str, asked: list[str]) -> None:
    """Say which courses a result is about (its text or the name of its chat) and, when the question names a course,
    whether the result is about it: a small model otherwise takes the midterm of one course for the midterm asked about."""
    found = [c for c in courses.courses() if courses.mentioned(c.short, f"{chat_title}\n{text}")]
    if found:
        item["about"] = [f"{c.short} ({c.name})" for c in found]
    if asked:
        item["matches_question_subject"] = bool({c.short for c in found} & set(asked)) if found else None


def _own_group(runtime: ToolRuntime[AgentContext]) -> dict | None:
    """The schedule group of the asker's study group, if InNoHassle has exactly one by that name."""
    group = runtime.context.study_group if runtime.context else None
    if not group:
        return None
    matches = _find_group(group)
    return matches[0] if len(matches) == 1 else None


DEFAULT_SCHEDULE_DAYS = 7
GROUP_UNKNOWN = "The asker's group is not known: ask them for it (such as B26-DSAI-04)."


def _named(group: str, runtime: ToolRuntime[AgentContext]) -> bool:
    """Is it the asker's own group or one the question names? Told that the asker's group is not known, the campus helper
    took B26-CSE-01 from an example of the prompts and gave its timetable as "the schedule of your group"."""
    own = runtime.context.study_group if runtime.context else None
    return _norm(group) in _norm(_question(runtime) or "") or bool(own and _norm(group) == _norm(own))


def _norm(text: str) -> str:
    return re.sub(r"[\W_]+", "", text.casefold())


def _find_group(query: str) -> list[dict]:
    """Event groups matching a group code ("B26-DSAI-04", "dsai 04") or an elective name."""
    groups = innohassle.event_groups()
    key = _norm(query)
    exact = [g for g in groups if key in (_norm(g["name"]), _norm(g["alias"]))]
    if exact:
        return exact
    by_suffix = [g for g in groups if _norm(g["alias"]).endswith(key)]
    return by_suffix or [g for g in groups if key in _norm(g["name"])]


class GetScheduleArgs(BaseModel):
    group: str | None = Field(
        None,
        description="Academic group like 'B26-DSAI-04' or an elective name. Omit for the asker's own group: it is known, never ask for it.",
    )
    date_from: date | None = Field(None, description="YYYY-MM-DD, default today.")
    date_to: date | None = Field(
        None,
        description=f"YYYY-MM-DD inclusive, default date_from + {DEFAULT_SCHEDULE_DAYS - 1} days.",
    )
    query: str | None = Field(
        None,
        description="Filter by words in the class title, e.g. 'lab', 'Programming'.",
    )


# ---- the wiki: documents of the university, eduwiki ------------------------------------------------------

MAX_WIKI = 8
WIKI_TEXT = 1000  # characters of a piece in the search results
READ_BUDGET = 5000  # characters read_wiki returns at most
KINDS = {
    "official": "official document of the university",
    "wiki": "eduwiki page (the university's teaching wiki, edited by staff; may be outdated)",
}
# Most pages of the kind `wiki` are not the eduwiki but the pages of the sites (news, olympiads, admission, the city):
# 4061 of 4490 on 2026-11-01. Labelled eduwiki, a news item of media.innopolis.university was cited as an eduwiki page.
SITE_KIND = "a page of a site of the university or of Innopolis (news, events, admission, courses; may be outdated)"
SITES = "sites/"
GUIDE_KIND = "catix's own guide: what the assistant, its Telegram bot and the InNoHassle browser extension do and how to use them"
GUIDE = "guide/"


def _kind(hit) -> str:
    if hit.path.startswith(GUIDE):
        return GUIDE_KIND
    return SITE_KIND if hit.trust == "wiki" and hit.path.startswith(SITES) else KINDS[hit.trust]


def _warnings(hit) -> list[str]:
    out = []
    if hit.source_warning or hit.trust == "official" and hit.review and "OCR" in hit.review:
        out.append("read from a scan by OCR: letters and numbers may be misread")
    elif hit.review:
        out.append("not checked: " + hit.review[:200])
    if hit.stale_after and hit.stale_after < date.today():
        out.append(f"may be outdated: due for review since {hit.stale_after:%Y-%m-%d}")
    if getattr(hit, "newer", None):
        out.append(f"an older version: «{hit.newer[:200]}» replaces it; use that one unless the question is about this year")
    return out


def _wiki_item(hit, collector: Collector, text_limit: int = WIKI_TEXT) -> dict:
    item = {"ref": collector.add_wiki(hit), "document": hit.title, "kind": _kind(hit)}
    # (A site page's date is the day it was read, or the 1st of January of a past year it is about: its text has its own.)
    if hit.issued and not hit.path.startswith(SITES):
        item["date"] = f"{hit.issued:%Y-%m-%d}"  # of the document: a newer one replaces an older one
    if hit.trust == "official":
        item["official"] = True  # a document of the university: "official" may be said of it
    if hit.clause:
        item["clause"] = hit.clause
    if hit.heading:
        item["section"] = hit.heading[:200]
    text = without_images(hit.text)  # (the pictures of a piece go to its source, not to the model)
    item["text"] = text if len(text) <= text_limit else text[:text_limit] + " [...cut; read_wiki gives the rest]"
    if hit.based_on:
        item["based_on"] = [{"document": b["title"], "page": b["page"]} for b in hit.based_on[:3]]
    if also := getattr(hit, "also_in", None):  # the same text in other documents (the programme of other intakes, other courses)
        shown = doc_store.ALSO_SHOWN
        item["same_text_also_in"] = [{"document": a["title"], "page": a["page"]} for a in also[:shown]] + (
            [f"and {len(also) - shown} more"] if len(also) > shown else [])
    if warnings := _warnings(hit):
        item["warnings"] = warnings
    item["page"] = hit.path
    return item


SOURCES = ("moodle", "chat", "docs")
log = logging.getLogger("catix.search")


class SearchArgs(BaseModel):
    queries: list[str] = Field(
        min_length=1,
        max_length=store.MAX_QUERIES,
        description=(
            "1-8 short queries of the same question from DIFFERENT angles, run together and merged: synonyms, Russian and "
            "English forms ('мидтерм', 'midterm', 'академический отпуск', 'academic leave'), the words a document or a course "
            "file would use. One of them may be a sentence as a document would state the answer. Plain topic words: no "
            "years, no 'when/where', never the same query twice."
        ),
    )
    sources: list[Literal["moodle", "chat", "docs"]] | None = Field(
        None,
        description="Where to look, one or several: docs (the university's documents, its eduwiki and the pages of its "
        "sites), chat (the university chats), moodle (the asker's Moodle course files and pages). Omit to look in all of them.",
    )

    @field_validator("queries", mode="before")
    @classmethod
    def _one_query(cls, value):
        return [value] if isinstance(value, str) else value

    @field_validator("sources", mode="before")
    @classmethod
    def _sources(cls, value):
        if isinstance(value, str):
            value = [value]
        return value or None


MAX_RESULTS = 16  # results of all sources together when the reranker scores them in one pass (db/rerank.py)


def _fetch_chats(queries: list[str], runtime: ToolRuntime[AgentContext], rerank: bool):
    """(the stored messages of the knowledge base that answer the queries, whether past ones were left out). With
    `rerank` False the pool of candidates, unscored."""
    allowed = runtime.context.allowed_chat_ids if runtime.context else None
    question = _question(runtime)
    upcoming = asks_upcoming(question)
    shown = MAX_MESSAGES if settings.reranker_route is None else MAX_MESSAGES_RERANKED
    # A question about what is coming needs a wider pool: the filter is applied after the ranking.
    rows = store.search(queries, chat_ids=allowed, limit=EVENT_POOL if upcoming else shown, original=question, rerank=rerank)
    found = len(rows)
    if upcoming:  # What is coming starts today, whenever it was written.
        now = datetime.now(settings.tz)
        rows = [r for r in rows if dates.coming(r.text, r.date, now, now.date(), None)]
        if rerank:
            rows = rows[:shown]
    return rows, upcoming and len(rows) < found


def _render_chats(fetched, runtime: ToolRuntime[AgentContext], collector: Collector) -> tuple[dict, list[str], bool]:
    """(the result, the refs about the question, whether the results were scored)."""
    rows, dropped = fetched
    now = datetime.now(settings.tz)
    asked = _asked_courses(runtime)
    messages = [_message_item(row, collector, asked, now) for row in rows]
    result: dict = {"total": len(messages), "messages": messages}
    if dropped:
        result["note"] = PAST_LEFT_OUT
    scored = any(row.relevance is not None for row in rows)
    relevant = [item["ref"] for item, row in zip(messages, rows) if row.relevance is not None and row.relevance >= settings.chat_relevant_score]
    return result, relevant, scored


def _fetch_docs(queries: list[str], runtime: ToolRuntime[AgentContext], rerank: bool):
    return doc_store.search(queries, limit=MAX_WIKI, original=_question(runtime), rerank=rerank)


def _render_docs(hits, collector: Collector) -> tuple[dict, list[str], bool]:
    result = {"total": len(hits), "pieces": [_wiki_item(h, collector) for h in hits]}
    # The first piece of each document lists its chapters, so that a chapter the pieces do not show can be read.
    contents = doc_store.chapters({h.path for h in hits}) if hits else {}
    for item in result["pieces"]:
        if len(headings := contents.pop(item["page"], [])) > 1:
            shown = doc_store.CHAPTERS_SHOWN
            item["chapters"] = [h[:80] for h in headings[:shown]] + ([f"and {len(headings) - shown} more"] if len(headings) > shown else [])
    if not hits:
        result["note"] = "Nothing found: try other words, in Russian and in English."
    scored = any(h.relevance is not None for h in hits)
    relevant = [item["ref"] for item, h in zip(result["pieces"], hits) if h.relevance is not None and h.relevance >= settings.docs_relevant_score]
    return result, relevant, scored


def _rank_queries(queries: list[str], question: str | None) -> list[str]:
    """The queries the reranker scores against: the user's own question first, as in the sources' own searches."""
    given = list(dict.fromkeys(q.strip() for q in queries if q.strip()))[: store.MAX_QUERIES]
    return [question, *[q for q in given if q != question]] if question and question.strip() else given


def _rerank_together(fetched: dict, queries: list[str], runtime: ToolRuntime[AgentContext]) -> dict:
    """Score the candidates of all the sources that answered in one pass, so that the best of all come first (db/rerank.py);
    each source's data keeps the shape its render expects."""
    readers = {"chat": store.rerank_document, "docs": doc_store.rerank_document, "moodle": moodle_files.rerank_document}
    pools = {}
    for source, data in fetched.items():
        if isinstance(data, Exception) or data is None:
            continue
        hits = data[0] if source == "chat" else data
        pools[source] = [(hit, readers[source](hit)) for hit in hits]
    ranked = joint_rerank.mixed(_rank_queries(queries, _question(runtime)), pools, MAX_RESULTS)
    return {source: ((ranked[source], data[1]) if source == "chat" else ranked[source]) if source in ranked else data
            for source, data in fetched.items()}


@tool(args_schema=SearchArgs)
def search(queries: list[str], runtime: ToolRuntime[AgentContext], sources: list[str] | None = None) -> Command:
    """Search the university's information by words and meaning, in several sources at once; each result has a `ref` to cite.
    docs: official documents (regulations, orders, rules of admission, study plans, programmes), the eduwiki (courses,
    teachers, procedures) and the pages of the sites (news and events, olympiads, admission, courses, campus life, the city of
    Innopolis), for rules, rights, deadlines, procedures, programmes, structure and news; chat: what students and staff wrote
    in the university chats, each message with its date, `official` flag and `group`; moodle: the
    text of the asker's Moodle course files and course pages. Without `sources` all of them are searched. Results rank by
    relevance, not by date: read the dates. Matches are not exhaustive lists or counts: use read_chats for those."""
    explicit = bool(sources)
    wanted = list(dict.fromkeys(sources or SOURCES))
    fetchers = {"moodle": moodle_tools.fetch, "chat": _fetch_chats, "docs": _fetch_docs}
    # With a reranker the sources give their candidates unscored and it scores them all in one pass, on one scale.
    together = settings.reranker_route is not None

    def fetch(source: str):
        try:
            return fetchers[source](queries, runtime, not together)
        except Exception as error:  # noqa: BLE001 - one source being down must not take the others with it
            log.warning("search in %s failed: %s", source, type(error).__name__)
            return error

    with ThreadPoolExecutor(len(wanted)) as pool:
        futures = {s: pool.submit(contextvars.copy_context().run, fetch, s) for s in wanted}
        fetched = {s: f.result() for s, f in futures.items()}
    if together:
        fetched = _rerank_together(fetched, queries, runtime)
    collector = Collector(runtime)
    out: dict[str, dict] = {}
    relevant: list[str] = []
    scored = False
    for source in wanted:  # Refs are handed out here, one source after another.
        data = fetched[source]
        if isinstance(data, Exception):
            out[source] = {"error": f"The search in {source} failed ({type(data).__name__}); say that part is unverified."}
        elif source == "moodle":
            if data is not None:
                out[source] = moodle_tools.render(data, collector)
            elif explicit:
                out[source] = {"error": moodle_tools.NOT_ALLOWED}
        else:
            part, refs, was_scored = _render_chats(data, runtime, collector) if source == "chat" else _render_docs(data, collector)
            out[source] = part
            relevant += refs
            scored = scored or was_scored
    result = {"total": sum(part.get("total", 0) for part in out.values()), **out}
    # The refs about the question, for the guard: two searches in a row with none it had not found before end the searching.
    return collector.result(result, "search", {"relevant": relevant} if scored else None)


def _words(text: str) -> str:
    """A heading or a line as its words, to find a section by its name: no markdown, no dots after the numbers ('**4.1.**
    Описание', '4.1 Описание' and '4.1. Описание' are the same words)."""
    return " " + " ".join(re.findall(r"\w+", text.lower())) + " "


class ReadWikiArgs(BaseModel):
    page: str = Field(description="The `page` of a search result ('regulations/attestation-regulation'), or words of a document's title.")
    clause: str | None = Field(None, description="A clause number to read ('5.3'; '5' reads chapter 5).")
    section: str | None = Field(None, description="Words of a section heading to read.")


@tool(args_schema=ReadWikiArgs)
def read_wiki(page: str, runtime: ToolRuntime[AgentContext], clause: str | None = None, section: str | None = None) -> Command:
    """Read more of one page of the knowledge base: a clause cut off in the search results, the clauses around it, or a
    section. Without clause and section: the start of the page and its list of sections."""
    collector = Collector(runtime)
    path = doc_store.find_page(page)
    if not path:
        return collector.result({"error": f"No page {page!r}: use the `page` of a search result."}, "read_wiki")
    pieces = doc_store.page(path)
    if clause:
        # A clause numbered in the text (**5.3.**) or a heading that starts with the number ("32. Вступительные испытания"):
        # documents with flat numbering carry their numbers in headings.
        number = clause.strip().rstrip(".")
        chosen = [p for p in pieces if doc_store.holds(p.clause, number)
                  or any(re.match(rf"{re.escape(number)}(?:\.\d+)*\.?\s", h) for h in p.heading.split(" > "))]
    elif section:
        # From the first piece whose heading has the words, or else a line of its text (not a row of a table first: a table of
        # contents names every section), on: a section is read on, as a person would read it ("Приложение 1" is often a
        # line in the text, not a heading; so is a scan's chapter '4 Процесс получения …' that the model asks as '4. Процесс …').
        want = _words(section)
        found = (lambda p: want in _words(p.heading),
                 lambda p: any(want in _words(line) for line in p.text.splitlines() if not line.startswith("|")),
                 lambda p: want in _words(p.text))
        start = next((i for has in found for i, p in enumerate(pieces) if has(p)), None)
        chosen = pieces[start:] if start is not None else []
    else:
        chosen = pieces
    first = pieces[0] if pieces else None
    result: dict = {"document": first.title if first else page, "kind": _kind(first) if first else None, "page": path}
    if first and first.resource:
        result["original"] = first.resource
    if not chosen:
        result["note"] = f"No {'clause ' + clause if clause else 'section ' + repr(section)} on this page; its sections are listed."
    out, used = [], 0
    for p in chosen:
        if used + len(p.text) > READ_BUDGET and out:
            result["note"] = "More follows: ask for a later clause or section."
            break
        out.append(_wiki_item(p, collector, text_limit=READ_BUDGET))
        used += len(p.text)
    result["pieces"] = out
    if not clause and not section or not chosen:
        result["sections"] = list(dict.fromkeys(p.heading for p in pieces if p.heading))[:60]
    return collector.result(result, "read_wiki")


TOOLS = [
    search,
    read_chats,
    read_wiki,
    *API_TOOLS,
    *CALENDAR_TOOLS,
    *ATTACHMENT_TOOLS,
    *MOODLE_TOOLS,
    get_my_schedule,
    *WEB_TOOLS,
]
