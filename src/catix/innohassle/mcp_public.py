"""Explicit MCP public integrations. Business rules execute here, not in the agent."""

import json
import re
from datetime import date, datetime, timedelta
from typing import Annotated, Literal

import icalendar
import recurring_ical_events
from fastmcp.tools import tool
from pydantic import Field

from catix.innohassle.mcp_declarations import metadata, result_boundary
from catix.settings import settings

MAX_CLUBS = 10


MAX_CLUBS_LISTING = 40


MAX_EVENTS = 30


MAX_AREAS = 8


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
    haystack = " ".join((f for f in fields if f)).lower()
    return all((word in haystack for word in query.lower().split()))


def _fmt(dt: date | datetime) -> str:
    if isinstance(dt, datetime):
        return dt.astimezone(settings.tz).strftime("%Y-%m-%d %H:%M %a")
    return dt.isoformat()


EVENT_PAGE = "https://innohassle.ru/events/p/{id}"


def _event_item(item: dict) -> dict:
    """An event of InNoHassle Events as the model sees it: its names and description in each language it has, when, where,
    who hosts it and how to enrol (`id` is what enroll_in_event takes)."""
    from catix.innohassle import client as innohassle

    data = item["data"]
    begin = datetime.fromisoformat(data["starts_at"])
    locales = (innohassle.event(item["id"]).get("data") or {}).get("locales") or {}
    names = {lang: loc.get("name") for lang, loc in locales.items() if loc.get("name")}
    texts = [_doc_to_text(loc.get("description") or "") for loc in locales.values()]
    enrollment = data.get("enrollment") or {}
    if enrollment.get("type") == "external":
        enrol = f"on the organisers' page: {enrollment.get('url')}" if enrollment.get("url") else "with the organisers"
    else:
        capacity = enrollment.get("capacity")
        enrol = f"on InNoHassle, {item.get('enrolled_count', 0)} enrolled" + (
            f" of {capacity} places" if capacity else ""
        )
    location = data.get("location") or {}
    event = {
        "id": item["id"],
        "title": data.get("name") or next(iter(names.values()), ""),
        "names": names if len(set(names.values())) > 1 else None,
        "start": _fmt(begin),
        "end": _fmt(begin + timedelta(hours=data.get("duration_hours") or 0)) if data.get("duration_hours") else None,
        "location": location.get("display_name") or None,
        "map": location.get("url") or None,
        "hosts": [h["display_name"] for h in data.get("hosts") or []] or None,
        "enrollment": enrol,
        "page": EVENT_PAGE.format(id=item["id"]),
        "description": "\n\n".join((t for t in texts if t))[:600] or None,
    }
    return {k: v for k, v in event.items() if v}


MAX_CLASSES = 40


DEFAULT_SCHEDULE_DAYS = 7


def _norm(text: str) -> str:
    return re.sub("[\\W_]+", "", text.casefold())


def _find_group(query: str) -> list[dict]:
    """Event groups matching a group code ("B26-DSAI-04", "dsai 04") or an elective name."""
    from catix.innohassle import client as innohassle

    groups = innohassle.event_groups()
    key = _norm(query)
    exact = [g for g in groups if key in (_norm(g["name"]), _norm(g["alias"]))]
    if exact:
        return exact
    by_suffix = [g for g in groups if _norm(g["alias"]).endswith(key)]
    return by_suffix or [g for g in groups if key in _norm(g["name"])]


def _instructor(description: str) -> str | None:
    match = re.search("Instructors?:\\s*([^\\n]+?)(?:\\s+Groups?:|\\n|$)", description)
    return match.group(1).strip() if match else None


@tool(**metadata())
@result_boundary()
def schedule_get_schedule(
    group: Annotated[str, Field(pattern="\\S")],
    date_from: date | None = None,
    date_to: date | None = None,
    query: str | None = None,
) -> dict:
    """Public class schedule for an explicitly selected study group, with date/title filters.

    Never guess a group. The client resolves trusted profile defaults before calling.
    Returns deduplicated classes, dates, rooms and instructors, not personal bookings.
    """
    from catix.innohassle import client as innohassle

    start = date_from or datetime.now(settings.tz).date()
    end = date_to or start + timedelta(days=DEFAULT_SCHEDULE_DAYS - 1)
    matches = _find_group(group)
    if not matches:
        return {"error": f"No schedule group matches {group!r}. Ask the user for the exact group, e.g. B26-DSAI-04."}
    if len(matches) > 1:
        return {
            "error": "Several groups match, ask the user which one.",
            "candidates": [g["name"] for g in matches[:15]],
        }
    source = matches[0]["name"]
    ics = innohassle.group_schedule_ics(matches[0]["alias"])
    calendar = icalendar.Calendar.from_ical(ics)
    now = datetime.now(settings.tz)
    classes, seen = ([], set())
    for ev in recurring_ical_events.of(calendar).between(start, end + timedelta(days=1)):
        title = str(ev.get("SUMMARY", ""))
        if query and (not _matches(query, title)):
            continue
        begin = ev.decoded("DTSTART")
        if not isinstance(begin, datetime):
            continue
        key = (begin, title, str(ev.get("LOCATION", "")))
        if key in seen:
            continue
        seen.add(key)
        local = begin.astimezone(settings.tz)
        finish = ev.decoded("DTEND") if "DTEND" in ev else begin
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


@tool(**metadata())
@result_boundary()
def maps_find_room(query: str) -> dict:
    """Public campus map search with room descriptions, people and booking capability.

    Find a room, place, printer or a person's office; combines matching areas and scenes.
    """
    from catix.innohassle import client as innohassle

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


@tool(**metadata())
@result_boundary()
def clubs_get_clubs(
    query: str | None = None, type: Literal["tech", "sport", "hobby", "art"] | None = None,
    include_inactive: bool = False,
) -> dict:
    """Public university clubs: list/filter clubs or search their details, leaders and links.

    Defaults to active clubs. Query selects detailed matching clubs rather than an inventory.
    """
    from catix.innohassle import client as innohassle

    leaders = innohassle.club_leaders()
    found = []
    for club in innohassle.clubs():
        if not include_inactive and (not club["is_active"]):
            continue
        if type and club["type"] != type:
            continue
        description = _doc_to_text(club["description"])
        if query and (not _matches(query, club["title"], club["short_description"], description)):
            continue
        if not query:
            found.append(
                {"title": club["title"], "type": club["type"], "short_description": club["short_description"][:200]}
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


@tool(**metadata())
@result_boundary()
def events_get_university_events(
    date_from: date | None = None, date_to: date | None = None, query: str | None = None
) -> dict:
    """Public university events for a date range, optionally filtered by title."""
    from catix.innohassle import client as innohassle

    start = date_from or datetime.now(settings.tz).date()
    end = date_to or start + timedelta(days=DEFAULT_EVENTS_WINDOW_DAYS)
    listed = innohassle.events(
        datetime.combine(start, datetime.min.time(), settings.tz),
        datetime.combine(end + timedelta(days=1), datetime.min.time(), settings.tz),
    )
    events = []
    for item in sorted(listed, key=lambda i: i["data"]["starts_at"]):
        event = _event_item(item)
        if query and (
            not _matches(
                query,
                event["title"],
                *(event.get("names") or {}).values(),
                event.get("description"),
                event.get("location"),
                *(event.get("hosts") or []),
            )
        ):
            continue
        events.append(event)
    result = {"range": [start.isoformat(), end.isoformat()], "total": len(events), "events": events[:MAX_EVENTS]}
    if not listed:
        result["note"] = (
            "InNoHassle Events has no published event in this period, so absence of events here proves nothing."
        )
    return result
