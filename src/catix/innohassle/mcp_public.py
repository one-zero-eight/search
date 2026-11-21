"""Explicit MCP public integrations. Business rules execute here, not in the agent."""

import json
import math
import re
from datetime import date, datetime, time, timedelta
from difflib import SequenceMatcher
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


_RU_TO_LAT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "zh", "з": "z", "и": "i",
    "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
    "у": "u", "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "",
    "э": "e", "ю": "yu", "я": "ya",
}  # Cyrillic -> Latin, close to the `transliteration` library the website uses


_RU_KEYBOARD = {  # a Russian word typed with the English layout still on: the Cyrillic letter -> the Latin key
    "й": "q", "ц": "w", "у": "e", "к": "r", "е": "t", "н": "y", "г": "u", "ш": "i", "щ": "o", "з": "p",
    "ф": "a", "ы": "s", "в": "d", "а": "f", "п": "g", "р": "h", "о": "j", "л": "k", "д": "l", "я": "z",
    "ч": "x", "с": "c", "м": "v", "и": "b", "т": "n", "ь": "m",
}


# Weight of each club field in the ranking, as on the website (its `description` is not indexed there).
_CLUB_WEIGHTS = {"title": 5, "slug": 4, "short_description": 3, "leader": 2, "telegram": 2, "type": 1, "description": 1}


_FUZZY_MIN_LENGTH = 5  # shorter words match only as a word prefix/substring: one typo in 4 letters is already ratio 0.75 ("robo" ~ "room")


_FUZZY_MIN_RATIO = 0.7  # difflib ratio equivalent to the website's Fuse threshold 0.3 (score = 1 - ratio)


def _query_variants(query: str) -> list[list[str]]:
    """The query as typed, transliterated to Latin and with the Russian layout mapped to Latin keys, as words."""
    lowered = query.lower()
    variants = [
        lowered,
        "".join(_RU_TO_LAT.get(c, c) for c in lowered),
        "".join(_RU_KEYBOARD.get(c, c) for c in lowered),
    ]
    return [words for i, v in enumerate(variants) if (words := v.split()) and v not in variants[:i]]


def _word_quality(word: str, text: str, tokens: list[str]) -> float | None:
    """How well one query word matches a field: 0 is a whole word, up to 0.3 the weakest accepted; None is no match."""
    if word in tokens:
        return 0.0
    if any(t.startswith(word) for t in tokens):
        return 0.05
    if len(word) >= 3 and word in text:
        return 0.1
    if len(word) < _FUZZY_MIN_LENGTH:
        return None
    best = 0.0
    for token in tokens:
        for candidate in {token, token[: len(word)]}:
            matcher = SequenceMatcher(None, word, candidate)
            if matcher.real_quick_ratio() >= _FUZZY_MIN_RATIO and matcher.quick_ratio() >= _FUZZY_MIN_RATIO:
                best = max(best, matcher.ratio())
    return 1 - best if best >= _FUZZY_MIN_RATIO else None


def _club_score(variants: list[list[str]], fields: dict[str, str]) -> float | None:
    """Weighted match score of a club for a query (lower is better), None when it does not match.

    Every word of a variant must match some field (a word-prefix, substring or, for words of 5+ characters, a similar
    word); a word costs (quality + 0.05) / field weight at its best field, so title hits beat slug, short description,
    leader and type hits. `description` is only searched for the word as a substring, at the worst quality, so a club
    found only there ranks after any name hit. The best variant wins.
    """
    prepared = {name: (text.lower(), re.findall(r"\w+", text.lower())) for name, text in fields.items() if text}
    best = None
    for words in variants:
        total = 0.0
        for word in words:
            costs = []
            for name, (text, tokens) in prepared.items():
                if name == "description":
                    quality = 0.3 if word in text else None
                else:
                    quality = _word_quality(word, text, tokens)
                if quality is not None:
                    costs.append((quality + 0.05) / _CLUB_WEIGHTS[name])
            if not costs:
                break
            total += min(costs)
        else:
            score = total / len(words)
            best = score if best is None else min(best, score)
    return best


def _fmt(dt: date | datetime) -> str:
    if isinstance(dt, datetime):
        return dt.astimezone(settings.tz).strftime("%Y-%m-%d %H:%M %a")
    return dt.isoformat()


EVENT_PAGE = "https://innohassle.ru/events/p/{id}"


def _event_item(item: dict) -> dict:
    """An event of InNoHassle Events as the model sees it: its names and description in each language it has, when, where,
    who hosts it and how to enrol (`id` is what enroll_in_event takes)."""
    from catix.innohassle import client as innohassle

    event_id = item['id']
    item = innohassle.event(event_id, fresh=True)
    result = _event_details(item, event_id)
    data = item['data']
    locales = data['locales']
    texts = [_doc_to_text(loc.get('description') or '') for loc in locales.values()]
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
        **result,
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


@tool(**metadata(usage="The PUBLIC timetable of a study group, not the asker's selected streams or calendar; it may hold several English streams and cannot tell which is theirs. Omit group to use the trusted profile group, or pass a group the user named; if neither is known, ask."))
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
    for ev in recurring_ical_events.of(calendar).between(
            datetime.combine(start, time.min, settings.tz), datetime.combine(end + timedelta(days=1), time.min, settings.tz)):
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
            "calendar_uid": str(ev.get("UID", "")),
            "starts_at": local.isoformat(),
            "ends_at": finish.astimezone(settings.tz).isoformat() if finish > begin else None,
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


@tool(**metadata(usage=(
    "Club names and descriptions are in English: search with English keywords (robotics, chess, music). Russian words "
    "match only by transliteration of names (робо -> Robotics), not by meaning. If total is 0, retry with English "
    "keywords or filter by type instead of concluding that no such club exists. A `note` about truncation means the "
    "list is NOT complete."
)))
@result_boundary()
def clubs_get_clubs(
    query: str | None = None, type: Literal["tech", "sport", "hobby", "art"] | None = None,
    include_inactive: bool = False,
) -> dict:
    """Public university clubs: list/filter clubs or search their details, leaders and links.

    Defaults to active clubs. Query selects detailed matching clubs, best match first, rather than an inventory; it is
    matched to English names and descriptions (typos and Russian transliteration tolerated).

    Club names and descriptions are in English: write the query in English keywords (robotics, chess, music), not in
    Russian; Russian words are matched only by transliteration of names (робо -> Robotics). If total is 0, retry with
    English keywords or filter by type.
    """
    from catix.innohassle import client as innohassle

    leaders = innohassle.club_leaders()
    variants = _query_variants(query) if query else []
    ranked = []
    for club in innohassle.clubs():
        if not include_inactive and (not club["is_active"]):
            continue
        if type and club["type"] != type:
            continue
        leader = leaders.get(club["leader_innohassle_id"] or "")
        description = _doc_to_text(club["description"])
        if not variants:
            ranked.append((0.0, {"title": club["title"], "type": club["type"],
                                 "short_description": club["short_description"][:200]}))
            continue
        score = _club_score(variants, {
            "title": club["title"], "slug": club.get("slug"), "short_description": club["short_description"],
            "leader": leader and leader["name"], "telegram": leader and leader["telegram_alias"],
            "type": club["type"], "description": description,
        })
        if score is None:
            continue
        ranked.append((score, {
            "title": club["title"],
            "type": club["type"],
            "active": club["is_active"],
            "short_description": club["short_description"],
            "description": description[:1200],
            "leader": leader and {"name": leader["name"], "telegram": leader["telegram_alias"]},
            "links": [{"label": l.get("label"), "url": l["link"]} for l in club["links"]],
        }))
    ranked.sort(key=lambda scored: scored[0])
    found = [item for _, item in ranked]
    limit = MAX_CLUBS if variants else MAX_CLUBS_LISTING
    result = {"total": len(found), "clubs": found[:limit]}
    if len(found) > limit:
        result["note"] = f"Only the first {limit} of {len(found)} are shown; narrow the query or filter by type."
    return result


def _event_details(item: dict, event_id: str) -> dict:
    """One snapshot for exact/list reads; typed enrollment is never parsed from prose."""
    if not isinstance(item, dict) or item.get("id") != event_id:
        raise ValueError("Unreadable event details.")
    data = item["data"]
    locales = data["locales"]
    if not isinstance(locales, dict) or any(
        not isinstance(lang, str) or not isinstance(loc, dict)
        or not isinstance(loc.get("name"), str) for lang, loc in locales.items()
    ):
        raise ValueError("Unreadable event names.")
    names = {lang: loc["name"] for lang, loc in sorted(locales.items()) if loc["name"].strip()}
    title = names.get("en") or names.get("ru") or next(iter(names.values()))
    start = datetime.fromisoformat(data["starts_at"])
    if start.tzinfo is None:
        raise ValueError("Unreadable event timezone.")
    start = start.astimezone(settings.tz)
    location = data.get("location")
    if location is not None and (not isinstance(location, dict)
            or not isinstance(location.get("display_name"), str)):
        raise ValueError("Unreadable event location.")
    duration = data.get("duration_hours")
    if duration is not None and (type(duration) not in (int, float)
            or not math.isfinite(duration) or duration <= 0):
        raise ValueError("Unreadable event duration.")
    result = {"id": item["id"], "title": title, "start": _fmt(start),
              "starts_at": start.isoformat(), "timezone": str(settings.tz),
              "location": (data.get("location") or {}).get("display_name"),
              "page": EVENT_PAGE.format(id=item["id"])}
    if len(set(names.values())) > 1:
        result["names"] = names
    if duration is not None:
        end = start + timedelta(hours=duration)
        result.update(end=_fmt(end), ends_at=end.isoformat())
    enrollment = data.get('enrollment')
    if (isinstance(enrollment, dict) and enrollment.get('type') in {'internal', 'external'}
            and (enrollment.get('capacity') is None or type(enrollment['capacity']) is int and enrollment['capacity'] >= 0)
            and (enrollment.get('url') is None or isinstance(enrollment['url'], str))
            and type(item.get('enrolled_count')) is int and item['enrolled_count'] >= 0):
        result['enrollment_info'] = {key: enrollment.get(key) for key in ('type', 'capacity', 'url')}
        result['enrollment_info']['enrolled_count'] = item['enrolled_count']
    return result


@tool(**metadata())
@result_boundary()
def events_get_event(event_id: Annotated[str, Field(pattern="^[0-9a-f]{24}$")]) -> dict:
    """Read one exact published event: title, interval, location, page and typed enrollment.

    Public fresh read by event_id; does not enroll anyone or return participants.
    """
    from catix.innohassle import client as innohassle

    return {'event': _event_details(innohassle.event(event_id, fresh=True), event_id)}


@tool(**metadata(usage="Each event's id and how to enrol. An event taking place in a period is not registration being open then."))
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
