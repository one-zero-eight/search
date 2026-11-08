"""One host-owned personal agenda, including the local AI Calendar.

MCP remains responsible only for external sources. Both model reads and scheduling
checks use read_my_schedule; the model never has to join two calendars itself.
"""

import asyncio
from datetime import date, datetime, time, timedelta

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from langgraph.errors import GraphBubbleUp
from pydantic import Field

from catix.agent import calendar_tools
from catix.innohassle import mcp_client
from catix.settings import settings

DEFAULT_DAYS = 7


class GetMyScheduleArgs(calendar_tools.GetAiCalendarArgs):
    date_to: date | None = Field(None, description="YYYY-MM-DD inclusive; default date_from + 6 days.")


def _event(row, source):
    item = dict(row)
    if (not item.get("starts_at") and not item.get("date")) or any(
            item.get(key) is not None and not isinstance(item[key], str) for key in ("title", "date", "time")):
        raise ValueError("Unreadable calendar event.")
    if "source" in item:
        item["source_url"] = item.pop("source")
    item["source"] = source
    item.setdefault("kind", item.get("service", "personal" if source == "ai_calendar" else "class"))
    for field in ("starts_at", "ends_at"):
        value = item.get(field)
        if value is not None:
            parsed = datetime.fromisoformat(value)
            if parsed.utcoffset() is None:
                raise ValueError("Calendar timestamp has no timezone.")
            item[field] = parsed.astimezone(settings.tz).isoformat()
        else:
            item[field] = None
    if source == "ai_calendar" and item.get("all_day") is True and item["starts_at"]:
        if item["ends_at"] and datetime.fromisoformat(item["ends_at"]) <= datetime.fromisoformat(item["starts_at"]):
            raise ValueError("Calendar end must be after its start.")
        start = datetime.combine(datetime.fromisoformat(item["starts_at"]).date(), time.min, settings.tz)
        end = datetime.combine(datetime.fromisoformat(item["ends_at"]).date(), time.min, settings.tz) if item["ends_at"] else start + timedelta(days=1)
        item.update(starts_at=start.isoformat(), ends_at=max(end, start + timedelta(days=1)).isoformat())
    return item


def merge_schedule(period, external, local, group=None):
    """Keep usable components when another source fails; never mistake partial for empty."""
    events, sources, not_read, source_errors = [], {}, [], {}
    parts = [("innohassle", external, ("schedule", "bookings")), ("ai_calendar", local, ("events",))]
    if group is not None:
        parts.append(("group_timetable", group, ("classes",)))
    for source, data, fields in parts:
        if (not isinstance(data, dict) or "error" in data or data.get("range") != period):
            sources[source] = {"status": "unavailable", "truncated": False}
            reason = "sign_in_required" if isinstance(data, dict) and data.get("sign_in_required") is True else "unavailable"
            if isinstance(data, dict) and "error" in data and data.get("code") in ("upstream_timeout", "mcp_timeout"):
                reason = data["code"]
                source_errors[source] = reason
            not_read.append(f"{source}: {reason}")
            continue
        problems = data.get("not_read", [])
        problems = list(problems) if isinstance(problems, list) and all(isinstance(p, str) for p in problems) else ["unreadable source status"]
        if source == "innohassle" and "source_errors" in data:
            failures = data["source_errors"]
            if not isinstance(failures, dict) or any(
                    key not in ("class", "sport", "event", "music_room", "rooms") or code != "upstream_timeout"
                    for key, code in failures.items()):
                problems.append("unreadable source status")
            else:
                for component, code in failures.items():
                    source_errors[f"{source}.{component}"] = code
                    problems.append(f"{component}: {code}")
        truncated = bool(data.get("truncated") or data.get("more") or (source != "ai_calendar" and data.get("note")))
        if source == "group_timetable":
            problems.append("Public group fallback, not selected personal calendars; English stream is unknown")
            if not isinstance(data.get("classes"), list) or type(data.get("total")) is not int or data["total"] < len(data["classes"]):
                problems.append("unreadable class count")
            else:
                truncated |= data["total"] > len(data["classes"])
        if source == "ai_calendar" and isinstance(data.get("events"), list):
            truncated |= len(data["events"]) >= calendar_tools.MAX_EVENTS and data.get("truncated") is not False
        if truncated:
            problems.append("truncated; narrow the dates")
        read = False
        for field in fields:
            rows = data.get(field)
            if not isinstance(rows, list):
                problems.append(f"{field}: unreadable")
                continue
            read = True
            for row in rows:
                try:
                    if not isinstance(row, dict):
                        raise ValueError
                    events.append(_event(row, source))
                except (TypeError, ValueError):
                    problems.append(f"{field}: unreadable event")
        sources[source] = {"status": "partial" if problems and read else "unavailable" if not read else "complete",
                           "truncated": truncated}
        not_read.extend(f"{source}: {problem}" for problem in dict.fromkeys(problems))
    events.sort(key=lambda item: (item.get("starts_at") or item.get("date", ""), item.get("title") or ""))
    return {"range": period, "timezone": str(settings.tz), "events": events, "total": len(events),
            "sources": sources, "complete": all(s["status"] == "complete" for s in sources.values()),
            "not_read": not_read, "source_errors": source_errors,
            "truncated": any(s["truncated"] for s in sources.values()),
            "checked_at": datetime.now(settings.tz).isoformat()}


def read_my_schedule(runtime, date_from: date | None = None, date_to: date | None = None) -> dict:
    """Read both sources for one period. Never accept identity or credentials as tool arguments."""
    context = getattr(runtime, "context", None)
    now = getattr(context, "asked_at", None) or datetime.now(settings.tz)
    start = date_from or now.astimezone(settings.tz).date()
    end = date_to or start + timedelta(days=DEFAULT_DAYS - 1)
    if end < start:
        return {"error": "date_to must not be before date_from."}
    period = {"date_from": start.isoformat(), "date_to": end.isoformat()}
    secret = getattr(context, "innohassle_token", None)
    try:
        external = (mcp_client.request_sync("call_tool", {"name": "account_get_my_schedule", "arguments": period},
                                            secret.get_secret_value()) if secret else {"error": "unavailable", "sign_in_required": True})
    except GraphBubbleUp:
        raise
    except Exception:
        external = {"error": "unavailable"}
    try:
        local = calendar_tools.read_calendar(runtime, start, end)
    except GraphBubbleUp:
        raise
    except Exception:
        local = {"error": "unavailable"}
    group = None
    profile_group = getattr(context, "study_group", None)
    if not secret and profile_group and profile_group != "all":
        try:
            group = mcp_client.request_sync("call_tool", {"name": "schedule_get_schedule",
                                            "arguments": {**period, "group": profile_group}})
        except GraphBubbleUp:
            raise
        except Exception:
            group = {"error": "unavailable"}
    return merge_schedule([start.isoformat(), end.isoformat()], external, local, group)


async def aread_my_schedule(runtime, date_from: date | None = None, date_to: date | None = None) -> dict:
    return await asyncio.to_thread(read_my_schedule, runtime, date_from, date_to)


@tool(args_schema=GetMyScheduleArgs)
def get_my_schedule(runtime: ToolRuntime, date_from: date | None = None, date_to: date | None = None) -> dict:
    """My complete personal agenda: selected class/English calendars, sport, enrolments, bookings AND AI Calendar.
    Моё расписание и календарь, что у меня завтра, мои занятия и личные события. One read includes all available sources.
    Defaults to seven days from the question's date. Use date_from/date_to, not day. Keep source IDs for changes.
    Report not_read/truncated and complete=false; partial or unavailable sources never establish free time.
    Use get_my_ai_calendar only when explicitly asked for the local AI Calendar alone. Not a public group timetable.
    """
    return read_my_schedule(runtime, date_from, date_to)
