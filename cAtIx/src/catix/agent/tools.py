"""LangChain tools for the agent.

Tools return dicts; LangChain serialises them to JSON for the model. Results are
kept compact because they go straight into the model context.
"""

import json
import re
from dataclasses import dataclass
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
    date_from: date | None = Field(None, description="YYYY-MM-DD.")
    date_to: date | None = Field(None, description="YYYY-MM-DD inclusive.")

    @field_validator("queries", mode="before")
    @classmethod
    def _one_query(cls, value):
        return [value] if isinstance(value, str) else value


@tool(args_schema=SearchChatsArgs)
def search_chats(
    queries: list[str],
    runtime: ToolRuntime[AgentContext],
    chat: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
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
        limit=MAX_MESSAGES if settings.reranker_route is None else MAX_MESSAGES_RERANKED,
        original=_question(runtime),
    )
    collector = Collector(runtime)
    asked = _asked_courses(runtime)
    messages = []
    now = datetime.now(settings.tz)
    for row in rows:
        item = {
            "ref": collector.add_db(row.ref_id),
            "chat": row.chat_title,
            "official": row.chat_official,  # true only for chats an admin marked official
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
    """Search chats with Telegram's own search, through the userbot: the big chats that are NOT in the knowledge base (their
    titles are in the system prompt), and any other chat for old messages that search_chats does not have. It matches
    whole words and their forms, not meaning, and lists the newest first: give 1-4 queries of one or two words each, never a
    sentence. Results are unofficial chat messages: read their dates."""
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
        context = runtime.context
        owner = innohassle.token_telegram_id()
        # The personal schedule belongs to the token owner: never show it to someone else.
        if owner is None or (context and context.user_telegram_id not in (None, owner)):
            return {"error": "Personal schedule is not available for this user. Ask for their group, e.g. B26-DSAI-04."}
        source = "your personal schedule"
        ics = innohassle.my_schedule_ics()

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
            continue  # The personal calendar repeats some events once per source group.
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


TOOLS = [
    get_schedule,
    search_chats,
    query_db,
    get_clubs,
    get_university_events,
    find_room,
    search_userbot_chats,
]
