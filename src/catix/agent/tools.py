"""LangChain tools for the agent.

Tools return dicts; LangChain serialises them to JSON for the model. Results are
kept compact because they go straight into the model context.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Literal

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from langgraph.types import Command
from pydantic import BaseModel, Field, SecretStr, field_validator

from catix import official
from catix.agent.api_tools import API_TOOLS
from catix.agent.calendar_tools import CALENDAR_TOOLS
from catix.agent.schedule_tools import get_my_schedule
from catix.agent.training_tools import get_my_available_trainings
from catix.agent.web_tools import WEB_TOOLS
from catix.agent.sources import Collector
from catix.common import courses, dates
from catix.db import store
from catix.db import wiki as wiki_store
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
    # The answer goes into an inline-mode card: it must be as short as possible.
    brief: bool = False
    # The asker's study group (from InNoHassle or their own choice); None when unknown (the default `all`).
    study_group: str | None = None
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


def _fmt(dt: date | datetime) -> str:
    if isinstance(dt, datetime):
        return dt.astimezone(settings.tz).strftime("%Y-%m-%d %H:%M %a")
    return dt.isoformat()


class SearchChatsArgs(BaseModel):
    queries: list[str] = Field(
        min_length=1,
        max_length=store.MAX_QUERIES,
        description=(
            "1-8 short searches of the same question from DIFFERENT angles, run together and merged: synonyms, "
            "Russian and English forms ('мидтерм', 'midterm'), with and without the course ('мидтерм матан', "
            "'midterm calculus'). Plain topic words only: no years, no 'when/where', never the same query twice."
        ),
    )
    chat: str | None = Field(None, description="Part of a chat title to restrict the search to.")
    date_from: date | None = Field(
        None, description="YYYY-MM-DD: only messages WRITTEN on or after this day (for 'what was written recently')."
    )
    date_to: date | None = Field(None, description="YYYY-MM-DD inclusive: only messages WRITTEN on or before this day.")
    event_from: date | None = Field(
        None,
        description="YYYY-MM-DD: only messages about a day on or after this one, whenever they were written. A post of "
        "5 October announcing a midterm on 23 October counts for this week of October. Use for 'this week', 'tomorrow', 'upcoming'.",
    )
    event_to: date | None = Field(None, description="YYYY-MM-DD inclusive: the end of the period the messages are about.")

    @field_validator("queries", mode="before")
    @classmethod
    def _one_query(cls, value):
        return [value] if isinstance(value, str) else value


EVENT_POOL = 60


@tool(args_schema=SearchChatsArgs)
def search_chats(
    queries: list[str],
    runtime: ToolRuntime[AgentContext],
    chat: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    event_from: date | None = None,
    event_to: date | None = None,
) -> Command:
    """Search student Telegram chats by words and by meaning: announcements, exam and deadline dates, homework,
    reschedules, campus news, tips. Give several queries from different angles in ONE call: messages found by
    several of them rank first. Messages may be outdated, jokes or contradict each other. Each carries `official`: true only
    for a chat an admin marked as the university's official one; all the rest is students talking.
    Results are ranked by relevance only, not by date: read the dates and prefer the latest information."""
    allowed = runtime.context.allowed_chat_ids if runtime.context else None
    now = datetime.now(settings.tz)
    question = _question(runtime)
    upcoming = asks_upcoming(question)
    if upcoming:  # What is coming starts today: "в ноябре" is from today on, a period wholly over is none.
        event_from = max(event_from or now.date(), now.date())
        event_to = event_to if event_to and event_to >= event_from else None
        # The day a message was written says nothing of what is coming, and drops the announcements made before (the
        # model gave 1 October one time, 1 November the next).
        date_from = date_to = None
    shown = MAX_MESSAGES if settings.reranker_route is None else MAX_MESSAGES_RERANKED
    rows = store.search(
        queries,
        chat=chat,
        chat_ids=allowed,
        date_from=date_from and date_from.isoformat(),
        date_to=date_to and date_to.isoformat(),
        # A period of events needs a wider pool: the filter below is applied after the ranking.
        limit=EVENT_POOL if event_from or event_to or upcoming else shown,
        original=question,
    )
    collector = Collector(runtime)
    asked = _asked_courses(runtime)
    messages = []
    found = len(rows)
    if upcoming:  # One rule whether the model gave a period or not: it gave one a time and not the next.
        rows = [r for r in rows if dates.coming(r.text, r.date, now, event_from, event_to)][:shown]
    elif event_from or event_to:
        start, end = event_from or date.min, event_to or date.max
        # Written in the period, or speaking of a day in it ("23 October" in a post of 5 October).
        rows = [
            r
            for r in rows
            if start <= r.date.astimezone(settings.tz).date() <= end or dates.mentions_between(r.text, r.date, now, start, end)
        ][:shown]
    for row in rows:
        messages.append(_message_item(row, collector, asked, now))
    result = {"total": len(messages), "messages": messages}
    if upcoming and len(rows) < min(found, shown):
        result["note"] = PAST_LEFT_OUT
    # The refs of those about the question, for the guard: two searches in a row with none it had not found before end the
    # searching (core.empty_searches).
    scored = any(row.relevance is not None for row in rows)
    relevant = [item["ref"] for item, row in zip(messages, rows) if row.relevance is not None and row.relevance >= settings.chat_relevant_score]
    return collector.result(result, "search_chats", {"relevant": relevant} if scored else None)


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
        description="YYYY-MM-DD: only messages ABOUT a day on or after this one, whenever written (an olympiad of 15 November "
        "announced on 13 October), the soonest first. With event_to, for 'what is on next week': every message about those "
        "days, whatever its words.",
    )
    event_to: date | None = Field(None, description="YYYY-MM-DD inclusive: the end of the period the messages are about.")
    limit: int = Field(10, description=f"How many of the newest messages to return, 1 to {MAX_READ}.")

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
    """The newest messages of the chats, newest first, and how many pass the filters in all (`total`). For "what is new",
    the latest announcements (official_only), the last messages of one chat or of one person, what was written today, a
    full list of the messages with some words over a period ("all tests since September") and counts ("how many messages
    about deadlines this month"). With event_from/event_to, what is on in a period: every message about its days, the
    soonest first ("какие мероприятия будут на следующей неделе"). Not for a question about a topic: search_chats finds
    messages by meaning, whatever their date."""
    collector = Collector(runtime)
    now = datetime.now(settings.tz)
    if asks_upcoming(_question(runtime)):  # As in search_chats: what is coming starts today, whenever it was written.
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
        result["note"] = "Nothing here: a chat that is not stored is searched with search_userbot_chats, by words."
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


class SearchUserbotArgs(BaseModel):
    queries: list[str] = Field(
        description="1 to 4 short queries of ONE or TWO words each (Telegram's search matches words and their forms, not phrases)."
    )
    chat: str | None = Field(None, description="Only the chat whose title contains this text, or @username.")
    date_from: date | None = Field(None, description="Only messages on or after this day (YYYY-MM-DD).")
    date_to: date | None = Field(None, description="Only messages on or before this day (YYYY-MM-DD).")


@tool(args_schema=SearchUserbotArgs)
def search_userbot_chats(
    queries: list[str],
    runtime: ToolRuntime[AgentContext],
    chat: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> Command:
    """Search chats with Telegram's own search, through the userbot: every chat an admin chose in /listen, official or not,
    whether or not the knowledge base stores it (it also reaches messages the knowledge base does not have). It matches
    whole words and their forms, not meaning, and lists the newest first: give 1-4 queries of one or two words each, never a
    sentence. Read the dates and `official` of each message."""
    from catix import live_search, userbot_config

    collector = Collector(runtime)
    allowed = runtime.context.allowed_chat_ids if runtime.context else None
    chats = userbot_config.searchable_titles(allowed)
    if chat:
        chats = {c: t for c, t in chats.items() if chat.lstrip("@").casefold() in t.casefold()}
    if not chats:
        return collector.result(
            {"total": 0, "messages": [], "note": "No chat to search this way (or none matches `chat`)."},
            "search_userbot_chats",
        )
    official_ids = official.ids()
    chat_group = store.chat_groups([int(c) for c in chats])
    upcoming = asks_upcoming(_question(runtime))
    if upcoming:  # As in search_chats: the day a message was written says nothing of what is coming.
        date_from = date_to = None
    hits, problem = live_search.search(
        queries, sorted(chats), date_from and date_from.isoformat(), date_to and date_to.isoformat()
    )
    now = datetime.now(settings.tz)
    asked = _asked_courses(runtime)
    messages = []
    for hit in hits:
        if upcoming and not dates.coming(hit.text, hit.date, now):
            continue  # The question is about what is coming (asks_upcoming).
        item = {
            "ref": collector.add_live(
                hit.chat_id,
                hit.msg_id,
                chat_title=hit.chat_title,
                link=hit.link,
                date=hit.date,
                author=hit.author,
                sender_link=hit.sender_link,
            ),
            "chat": hit.chat_title,
            "official": hit.chat_id in official_ids,
            "group": chat_group.get(hit.chat_id, "all"),
            "date": _fmt(hit.date),
            "from": hit.author,
            "text": hit.text[:600],
        }
        _subject_fields(item, hit.text, hit.chat_title, asked)
        if settings.annotate_dates and (resolved := dates.resolve(hit.text, hit.date, now)):
            item["dates_in_text"] = resolved
        messages.append(item)
    result: dict = {"total": len(messages), "messages": messages}
    if len(messages) < len(hits):
        result["note"] = PAST_LEFT_OUT
    if problem:
        result["note"] = " ".join(filter(None, [result.get("note"), f"Telegram search gave no usable answer for some chats: {problem}."]))
    return collector.result(result, "search_userbot_chats")


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


# ---- the wiki: documents of the university, guides, eduwiki ------------------------------------------------------

MAX_WIKI = 8
WIKI_TEXT = 1000  # characters of a piece in the search results
READ_BUDGET = 5000  # characters read_wiki returns at most
KINDS = {
    "official": "official document of the university",
    "guide": "guide: a summary that cAtIx wrote from the documents it names (check the clause in the document)",
    "wiki": "eduwiki page (the university's teaching wiki, edited by staff; may be outdated)",
}
# Most pages of the kind `wiki` are not the eduwiki but the pages of the sites (news, olympiads, admission, the city):
# 4061 of 4490 on 2026-11-01. Labelled eduwiki, a news item of media.innopolis.university was cited as an eduwiki page.
SITE_KIND = "a page of a site of the university or of Innopolis (news, events, admission, courses; may be outdated)"
SITES = "/raw/sites/"


def _kind(hit) -> str:
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
        item["date"] = f"{hit.issued:%Y-%m-%d}"  # of the document (or of the guide): a newer one replaces an older one
    if hit.trust == "official":
        item["official"] = True  # a document of the university: "official" may be said of it
    if hit.clause:
        item["clause"] = hit.clause
    if hit.heading:
        item["section"] = hit.heading[:200]
    item["text"] = hit.text if len(hit.text) <= text_limit else hit.text[:text_limit] + " [...cut; read_wiki gives the rest]"
    if hit.audience:
        item["for"] = hit.audience
    if hit.based_on:
        item["based_on"] = [{"document": b["title"], "page": b["page"]} for b in hit.based_on[:3]]
    if also := getattr(hit, "also_in", None):  # the same text in other documents (the programme of other intakes, other courses)
        shown = wiki_store.ALSO_SHOWN
        item["same_text_also_in"] = [{"document": a["title"], "page": a["page"]} for a in also[:shown]] + (
            [f"and {len(also) - shown} more"] if len(also) > shown else [])
    if warnings := _warnings(hit):
        item["warnings"] = warnings
    item["page"] = hit.path
    return item


class SearchWikiArgs(BaseModel):
    queries: list[str] = Field(
        min_length=1,
        max_length=8,
        description="2 to 6 search queries from different angles, in Russian AND English (the documents are Russian, the guides "
        "English): the words a rule would use ('академический отпуск', 'academic leave', 'пересдача', 'retake'). One of them is "
        "a sentence as the document itself would say the answer ('Обучающийся вправе пройти повторную промежуточную аттестацию "
        "не более ...'): its numbers may be guesses, its wording finds the clause.",
    )
    kinds: list[Literal["official", "guide", "wiki"]] | None = Field(
        None, description="Only these kinds of pages: official (documents of the university), guide (summaries), wiki (eduwiki and the "
        "pages of the sites: news, olympiads, admission, the city). Default: all."
    )

    @field_validator("queries", mode="before")
    @classmethod
    def _one_query(cls, value):
        return [value] if isinstance(value, str) else value


@tool(args_schema=SearchWikiArgs)
def search_wiki(queries: list[str], runtime: ToolRuntime[AgentContext], kinds: list[str] | None = None) -> Command:
    """Search the university's knowledge base: its official documents (regulations, orders, rules of admission, study plans,
    programmes, reports), guides that summarise them, the eduwiki (courses, teachers, procedures) and the pages of the
    sites (the news and events of media.innopolis.university, olympiads, admission, courses, campus life, the city of
    Innopolis). Returns pieces of pages with the document, the clause number and a ref to cite. For rules, rights,
    deadlines, procedures, programmes, courses, admission, structure of the university, news."""
    hits = wiki_store.search(queries, trust=kinds, limit=MAX_WIKI, original=_question(runtime))
    collector = Collector(runtime)
    result = {"total": len(hits), "pieces": [_wiki_item(h, collector) for h in hits]}
    # The first piece of each document lists its chapters: asked about IT support, the helper read chapters 1 and 2 of the
    # regulation in order and never reached chapter 4, the procedure and its deadlines.
    contents = wiki_store.chapters({h.path for h in hits}) if hits else {}
    for item in result["pieces"]:
        if len(headings := contents.pop(item["page"], [])) > 1:
            shown = wiki_store.CHAPTERS_SHOWN
            item["chapters"] = [h[:80] for h in headings[:shown]] + ([f"and {len(headings) - shown} more"] if len(headings) > shown else [])
    if not hits:
        result["note"] = "Nothing found: try other words, in Russian and in English."
    # The refs of the pieces about the question, for the guard (as in search_chats).
    scored = any(h.relevance is not None for h in hits)
    relevant = [item["ref"] for item, h in zip(result["pieces"], hits) if h.relevance is not None and h.relevance >= settings.wiki_relevant_score]
    return collector.result(result, "search_wiki", {"relevant": relevant} if scored else None)


MAX_READS = 2  # read_wiki calls that gave text, per question


def _reads_this_turn(runtime: ToolRuntime[AgentContext]) -> int:
    return reads_done(runtime.state.get("messages", []))


def reads_done(messages: list) -> int:
    """How many read_wiki calls gave text since the last question (the helper's run). One that found no such page or section
    costs nothing: the model guesses a heading from a table of contents, and a scan's chapter may be no heading. When they
    are MAX_READS, the helper's next model call is its report (core.RunGuardMiddleware)."""
    count = 0
    for message in reversed(messages):
        if getattr(message, "type", "") == "human":
            break
        if getattr(message, "type", "") == "tool" and getattr(message, "name", "") == "read_wiki":
            try:
                count += bool(json.loads(message.content).get("pieces"))
            except (TypeError, ValueError, AttributeError):
                count += 1
    return count


def _words(text: str) -> str:
    """A heading or a line as its words, to find a section by its name: no markdown, no dots after the numbers ('**4.1.**
    Описание', '4.1 Описание' and '4.1. Описание' are the same words)."""
    return " " + " ".join(re.findall(r"\w+", text.lower())) + " "


class ReadWikiArgs(BaseModel):
    page: str = Field(description="The `page` of a search result ('/raw/regulations/attestation-regulation.md'), or words of a document's title.")
    clause: str | None = Field(None, description="A clause number to read ('5.3'; '5' reads chapter 5).")
    section: str | None = Field(None, description="Words of a section heading to read.")


@tool(args_schema=ReadWikiArgs)
def read_wiki(page: str, runtime: ToolRuntime[AgentContext], clause: str | None = None, section: str | None = None) -> Command:
    """Read more of one page of the knowledge base: a clause cut off in the search results, the clauses around it, or a
    section. Without clause and section: the start of the page and its list of sections."""
    collector = Collector(runtime)
    if _reads_this_turn(runtime) >= MAX_READS:
        # The prompt says so too, but a small model keeps reading and runs out of its budget without a report.
        return collector.result({"error": "No more reading in this question: report now with what you have, and say what is missing."}, "read_wiki")
    path = wiki_store.find_page(page)
    if not path:
        return collector.result({"error": f"No page {page!r}: use the `page` of a search result."}, "read_wiki")
    pieces = wiki_store.page(path)
    if clause:
        # A clause numbered in the text (**5.3.**) or a heading that starts with the number ("32. Вступительные испытания"):
        # documents with flat numbering carry their numbers in headings.
        number = clause.strip().rstrip(".")
        chosen = [p for p in pieces if wiki_store.holds(p.clause, number)
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
    # Said with every read, so the model chooses what to read instead of running into the end of its reading.
    result["reads_left"] = left = MAX_READS - _reads_this_turn(runtime) - bool(out)
    if out and not left:
        result["note"] = "That was the last read in this question: report now with what you have" + (
            " (the page goes on: say what was not read, if it matters)." if "note" in result else ".")
    return collector.result(result, "read_wiki")


TOOLS = [
    search_chats,
    read_chats,
    search_userbot_chats,
    search_wiki,
    read_wiki,
    *API_TOOLS,
    *CALENDAR_TOOLS,
    get_my_schedule,
    get_my_available_trainings,
    *WEB_TOOLS,
]
