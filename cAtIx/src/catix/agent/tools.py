"""LangChain tools for the agent.

Tools return dicts; LangChain serialises them to JSON for the model. Results are
kept compact because they go straight into the model context.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Literal

import icalendar
import recurring_ical_events
from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from langgraph.types import Command
from pydantic import BaseModel, Field, field_validator

from catix import official
from catix.agent import sqlquery
from catix.agent.sources import Collector
from catix.common import courses, dates
from catix.db import store
from catix.db import wiki as wiki_store
from catix.innohassle import client as innohassle
from catix.settings import settings

MAX_CLUBS = 10
MAX_CLUBS_LISTING = 40
MAX_EVENTS = 30
MAX_AREAS = 8
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


DEFAULT_EVENTS_WINDOW_DAYS = 14


def _doc_to_text(raw: str) -> str:
    """Club descriptions are stored as a ProseMirror JSON document; flatten it to plain text."""
    try:
        doc = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw or ""

    lines: list[str] = []

    def walk(node: dict, buf: list[str]) -> None:
        match node.get("type"):
            case "text":
                buf.append(node.get("text", ""))
            case "hardBreak":
                buf.append("\n")
            case _:
                for child in node.get("content", []):
                    walk(child, buf)

    for block in doc.get("content", []):
        buf: list[str] = []
        walk(block, buf)
        if text := "".join(buf).strip():
            lines.append(text)
    return "\n".join(lines)


def _matches(query: str, *fields: str | None) -> bool:
    haystack = " ".join(f for f in fields if f).lower()
    return all(word in haystack for word in query.lower().split())


def _fmt(dt: date | datetime) -> str:
    if isinstance(dt, datetime):
        return dt.astimezone(settings.tz).strftime("%Y-%m-%d %H:%M %a")
    return dt.isoformat()


class GetClubsArgs(BaseModel):
    query: str | None = Field(
        None,
        description="Keywords in English, e.g. 'chess', 'dance', 'robotics'. Club data is in English.",
    )
    type: Literal["tech", "sport", "hobby", "art"] | None = None
    include_inactive: bool = Field(False, description="Also return closed clubs.")


@tool(args_schema=GetClubsArgs)
def get_clubs(query: str | None = None, type: str | None = None, include_inactive: bool = False) -> dict:
    """Student clubs of Innopolis University. With `query`: full description, schedule, location,
    leader contacts and links. Without `query`: a short list of titles; call again with a query for details."""
    leaders = innohassle.club_leaders()
    found = []
    for club in innohassle.clubs():
        if not include_inactive and not club["is_active"]:
            continue
        if type and club["type"] != type:
            continue
        description = _doc_to_text(club["description"])
        if query and not _matches(query, club["title"], club["short_description"], description):
            continue
        if not query:
            # Listing mode: many clubs, so only the essentials to save context.
            found.append(
                {
                    "title": club["title"],
                    "type": club["type"],
                    "short_description": club["short_description"][:200],
                }
            )
            continue
        leader = leaders.get(club["leader_innohassle_id"] or "")
        found.append(
            {
                "title": club["title"],
                "type": club["type"],
                "active": club["is_active"],
                "short_description": club["short_description"],
                "description": description[:1200],
                "leader": leader and {"name": leader["name"], "telegram": leader["telegram_alias"]},
                "links": [{"label": l.get("label"), "url": l["link"]} for l in club["links"]],
            }
        )
    limit = MAX_CLUBS if query else MAX_CLUBS_LISTING
    result = {"total": len(found), "clubs": found[:limit]}
    if len(found) > limit:
        result["note"] = f"Only the first {limit} of {len(found)} are shown; narrow the query or filter by type."
    return result


class GetUniversityEventsArgs(BaseModel):
    date_from: date | None = Field(None, description="YYYY-MM-DD, default today.")
    date_to: date | None = Field(
        None,
        description=f"YYYY-MM-DD inclusive, default date_from + {DEFAULT_EVENTS_WINDOW_DAYS} days.",
    )
    query: str | None = Field(None, description="Optional keywords to filter by.")


@tool(args_schema=GetUniversityEventsArgs)
def get_university_events(date_from: date | None = None, date_to: date | None = None, query: str | None = None) -> dict:
    """University-wide events (talks, workshops, celebrations) from InNoHassle.
    Does NOT contain class schedules, exams or deadlines."""
    start = date_from or datetime.now(settings.tz).date()
    end = date_to or start + timedelta(days=DEFAULT_EVENTS_WINDOW_DAYS)
    calendar = icalendar.Calendar.from_ical(innohassle.events_ics())
    # Expands RRULE so recurring events show up as individual occurrences.
    occurrences = recurring_ical_events.of(calendar).between(start, end + timedelta(days=1))

    events = []
    for ev in occurrences:
        title = str(ev.get("SUMMARY", ""))
        description = str(ev.get("DESCRIPTION", ""))
        location = str(ev.get("LOCATION", ""))
        if query and not _matches(query, title, description, location):
            continue
        event = {
            "title": title,
            "start": _fmt(ev.decoded("DTSTART")),
            "end": _fmt(ev.decoded("DTEND")) if "DTEND" in ev else None,
            "location": location or None,
            "description": description[:500] or None,
        }
        if "URL" in ev:
            event["url"] = str(ev.get("URL"))
        events.append(event)
    events.sort(key=lambda e: e["start"])
    result = {
        "range": [start.isoformat(), end.isoformat()],
        "total": len(events),
        "events": events[:MAX_EVENTS],
    }
    if not calendar.walk("VEVENT"):
        result["note"] = "The InNoHassle events calendar is empty right now, so absence of events here proves nothing."
    return result


class FindRoomArgs(BaseModel):
    query: str = Field(description="Room number ('319'), place ('canteen', 'printer') or person surname.")


@tool(args_schema=FindRoomArgs)
def find_room(query: str) -> dict:
    """Search the campus map: room numbers, offices (e.g. 'Student Affairs'), canteens, printers,
    and which staff member sits in which room. Returns floor/building, description and working hours."""
    scene_titles = {s["scene_id"]: s["title"] for s in innohassle.scenes()}
    seen: set[tuple[str, str]] = set()
    areas = []
    for hit in innohassle.search_areas(query):
        area = hit["area"]
        key = (hit["scene_id"], area["svg_polygon_id"])
        if key in seen:
            continue
        seen.add(key)
        areas.append(
            {
                "title": area["title"],
                "ru_title": area["ru_title"],
                "where": scene_titles.get(hit["scene_id"], hit["scene_id"]),
                "description": area["description"],
                "people": area["people"] or None,
                "bookable": area["room_booking_id"] is not None,
            }
        )
    return {"total": len(areas), "areas": areas[:MAX_AREAS]}


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
    rows = store.search(
        queries,
        chat=chat,
        chat_ids=allowed,
        date_from=date_from and date_from.isoformat(),
        date_to=date_to and date_to.isoformat(),
        # A period of events needs a wider pool: the filter below is applied after the ranking.
        limit=EVENT_POOL if event_from or event_to else MAX_MESSAGES if settings.reranker_route is None else MAX_MESSAGES_RERANKED,
        original=_question(runtime),
    )
    collector = Collector(runtime)
    asked = _asked_courses(runtime)
    messages = []
    now = datetime.now(settings.tz)
    if event_from or event_to:
        start, end = event_from or date.min, event_to or date.max
        # Written in the period, or speaking of a day in it ("23 October" in a post of 5 October).
        rows = [
            r
            for r in rows
            if start <= r.date.astimezone(settings.tz).date() <= end or dates.mentions_between(r.text, r.date, now, start, end)
        ][: MAX_MESSAGES if settings.reranker_route is None else MAX_MESSAGES_RERANKED]
    for row in rows:
        item = {
            "ref": collector.add_db(row.ref_id),
            "chat": row.chat_title,
            "official": row.chat_official,  # true only for chats an admin marked official
            "group": row.chat_group,  # `all` (for everybody) or the study group of the chat
            "date": _fmt(row.date),
            "from": row.sender_name,
            # The stamp is in the text itself, so "завтра" is read next to the day it was written on.
            "text": row.text[:600],
        }
        _subject_fields(item, row.text, row.chat_title, asked)
        if row.edit_date:
            item["edited"] = _fmt(row.edit_date)
        if settings.annotate_dates and (resolved := dates.resolve(row.text, row.date, now)):
            item["dates_in_text"] = resolved
        if row.parent_text:
            item["in_reply_to"] = f"{row.parent_sender}: {row.parent_text[:200]}"
        messages.append(item)
    result = {"total": len(messages), "messages": messages}
    return collector.result(result, "search_chats")


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
    hits, problem = live_search.search(
        queries, sorted(chats), date_from and date_from.isoformat(), date_to and date_to.isoformat()
    )
    now = datetime.now(settings.tz)
    asked = _asked_courses(runtime)
    messages = []
    for hit in hits:
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
    if problem:
        result["note"] = f"Telegram search gave no usable answer for some chats: {problem}."
    return collector.result(result, "search_userbot_chats")


def _own_group(runtime: ToolRuntime[AgentContext]) -> dict | None:
    """The schedule group of the asker's study group, if InNoHassle has exactly one by that name."""
    group = runtime.context.study_group if runtime.context else None
    if not group:
        return None
    matches = _find_group(group)
    return matches[0] if len(matches) == 1 else None


MAX_CLASSES = 40
DEFAULT_SCHEDULE_DAYS = 7


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


def _instructor(description: str) -> str | None:
    match = re.search(r"Instructors?:\s*([^\n]+?)(?:\s+Groups?:|\n|$)", description)
    return match.group(1).strip() if match else None


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


@tool(args_schema=GetScheduleArgs)
def get_schedule(
    runtime: ToolRuntime[AgentContext],
    group: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    query: str | None = None,
) -> dict:
    """Official university timetable from InNoHassle: lectures, tutorials and labs with times, rooms and
    instructors. Use for "what classes / where is the lab / which room" questions. Exams and reschedules
    announced in chats are found with search_chats instead."""
    start = date_from or datetime.now(settings.tz).date()
    end = date_to or start + timedelta(days=DEFAULT_SCHEDULE_DAYS - 1)

    if group:
        matches = _find_group(group)
        if not matches:
            return {
                "error": f"No schedule group matches {group!r}. Ask the user for the exact group, e.g. B26-DSAI-04."
            }
        if len(matches) > 1:
            return {
                "error": "Several groups match, ask the user which one.",
                "candidates": [g["name"] for g in matches[:15]],
            }
        source = matches[0]["name"]
        ics = innohassle.group_schedule_ics(matches[0]["alias"])
    elif (own := _own_group(runtime)) is not None:
        source = own["name"]
        ics = innohassle.group_schedule_ics(own["alias"])
    else:
        return {"error": "The asker's group is not known. Ask for their group, e.g. B26-DSAI-04."}

    calendar = icalendar.Calendar.from_ical(ics)
    now = datetime.now(settings.tz)
    classes, seen = [], set()
    for ev in recurring_ical_events.of(calendar).between(start, end + timedelta(days=1)):
        title = str(ev.get("SUMMARY", ""))
        if query and not _matches(query, title):
            continue
        begin = ev.decoded("DTSTART")
        if not isinstance(begin, datetime):
            continue  # All-day entries are markers, not classes.
        key = (begin, title, str(ev.get("LOCATION", "")))
        if key in seen:
            continue  # A calendar may repeat an event once per source group.
        seen.add(key)
        local = begin.astimezone(settings.tz)
        finish = ev.decoded("DTEND") if "DTEND" in ev else begin
        # Computed here: the model is unreliable at comparing clock times with "now".
        status = "finished" if finish <= now else "now" if begin <= now else "upcoming"
        item = {
            "date": local.strftime("%Y-%m-%d %a"),
            "time": f"{local:%H:%M}-{ev.decoded('DTEND').astimezone(settings.tz):%H:%M}"
            if "DTEND" in ev
            else f"{local:%H:%M}",
            "title": title,
            "room": str(ev.get("LOCATION", "")) or None,
            "instructor": _instructor(str(ev.get("DESCRIPTION", ""))),
            "status": status,
        }
        classes.append({k: v for k, v in item.items() if v})
    classes.sort(key=lambda c: (c["date"], c["time"]))
    result = {
        "schedule": source,
        "now": now.strftime("%Y-%m-%d %H:%M"),
        "range": [start.isoformat(), end.isoformat()],
        "total": len(classes),
        "classes": classes[:MAX_CLASSES],
    }
    if len(classes) > MAX_CLASSES:
        result["note"] = f"Only the first {MAX_CLASSES} are shown; narrow the dates."
    return result


class QueryDbArgs(BaseModel):
    sql: str = Field(description="One SQLite SELECT statement with LIMIT.")


@tool(args_schema=QueryDbArgs, description=sqlquery.DESCRIPTION)
def query_db(sql: str, runtime: ToolRuntime[AgentContext]) -> Command:
    result = sqlquery.run(sql, runtime.context.allowed_chat_ids if runtime.context else None)
    # The views name messages by database id ("m5127"): the model gets this conversation's refs instead.
    collector = Collector(runtime)
    return collector.result(collector.rewrite(result), "query_db")


# ---- the wiki: documents of the university, guides, eduwiki ------------------------------------------------------

MAX_WIKI = 8
WIKI_TEXT = 1000  # characters of a piece in the search results
READ_BUDGET = 5000  # characters read_wiki returns at most
KINDS = {
    "official": "official document of the university",
    "guide": "guide: a summary that cAtIx wrote from the documents it names (check the clause in the document)",
    "wiki": "eduwiki page (the university's teaching wiki, edited by staff; may be outdated)",
}


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
    item = {"ref": collector.add_wiki(hit), "document": hit.title, "kind": KINDS[hit.trust]}
    if hit.issued:
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
        None, description="Only these kinds of pages: official (documents of the university), guide (summaries), wiki (eduwiki). Default: all."
    )

    @field_validator("queries", mode="before")
    @classmethod
    def _one_query(cls, value):
        return [value] if isinstance(value, str) else value


@tool(args_schema=SearchWikiArgs)
def search_wiki(queries: list[str], runtime: ToolRuntime[AgentContext], kinds: list[str] | None = None) -> Command:
    """Search the university's knowledge base: its official documents (regulations, orders, rules of admission, study plans,
    programmes, reports), guides that summarise them, and the eduwiki (courses, teachers, procedures). Returns pieces of
    pages with the document, the clause number and a ref to cite. For rules, rights, deadlines, procedures, programmes,
    courses, admission, structure of the university."""
    hits = wiki_store.search(queries, trust=kinds, limit=MAX_WIKI, original=_question(runtime))
    collector = Collector(runtime)
    result = {"total": len(hits), "pieces": [_wiki_item(h, collector) for h in hits]}
    if not hits:
        result["note"] = "Nothing found: try other words, in Russian and in English."
    return collector.result(result, "search_wiki")


MAX_READS = 2  # read_wiki calls per question


def _calls_this_turn(runtime: ToolRuntime[AgentContext], name: str) -> int:
    """How many results of tool `name` came back since the last question (the helper's run)."""
    count = 0
    for message in reversed(runtime.state.get("messages", [])):
        if getattr(message, "type", "") == "human":
            break
        count += getattr(message, "type", "") == "tool" and getattr(message, "name", "") == name
    return count


class ReadWikiArgs(BaseModel):
    page: str = Field(description="The `page` of a search result ('/regulations/attestation-regulation.md'), or words of a document's title.")
    clause: str | None = Field(None, description="A clause number to read ('5.3'; '5' reads chapter 5).")
    section: str | None = Field(None, description="Words of a section heading to read.")


@tool(args_schema=ReadWikiArgs)
def read_wiki(page: str, runtime: ToolRuntime[AgentContext], clause: str | None = None, section: str | None = None) -> Command:
    """Read more of one page of the knowledge base: a clause cut off in the search results, the clauses around it, or a
    section. Without clause and section: the start of the page and its list of sections."""
    collector = Collector(runtime)
    if _calls_this_turn(runtime, "read_wiki") >= MAX_READS:
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
        # From the first piece whose heading or text has the words on: a section is read on, as a person would read it
        # ("Приложение 1" is often a line in the text, not a heading).
        want = section.lower()
        start = next((i for i, p in enumerate(pieces) if want in p.heading.lower() or want in p.text.lower()), None)
        chosen = pieces[start:] if start is not None else []
    else:
        chosen = pieces
    first = pieces[0] if pieces else None
    result: dict = {"document": first.title if first else page, "kind": KINDS[first.trust] if first else None, "page": path}
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
    get_schedule,
    search_chats,
    query_db,
    get_clubs,
    get_university_events,
    find_room,
    search_userbot_chats,
    search_wiki,
    read_wiki,
]
