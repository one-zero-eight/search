"""Consent details from matched service reads, never assistant prose or display arguments."""

import json
import re
from datetime import date, datetime, timedelta

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from catix.settings import settings


def _text(value):
    return isinstance(value, str) and bool(value.strip()) and not any(ord(c) < 32 for c in value)


def _day(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?: [A-Za-z]{3})?", value):
        return None
    try:
        return date.fromisoformat(value[:10]).isoformat()
    except ValueError:
        return None


def _time(value):
    return isinstance(value, str) and re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d-(?:[01]\d|2[0-3]):[0-5]\d", value)


def detail_request(target, arguments):
    if target == "sport_sport_checkin":
        return {"name": "sport_get_training", "arguments": {"training_id": arguments["training_id"]}}
    if target == "events_enroll_in_event":
        return {"name": "events_get_event", "arguments": {"event_id": arguments["event_id"]}}
    if target == "account_cancel_booking":
        return {"name": "account_get_booking", "arguments": {
            "service": arguments["service"], "booking_id": arguments["booking_id"]}}
    return None


def _when(item, language):
    if "starts_at" in item or "ends_at" in item:
        try:
            start, end = (datetime.fromisoformat(item[key]) for key in ("starts_at", "ends_at"))
            if start.utcoffset() is None or end.utcoffset() is None or end <= start:
                return None
            start, end = start.astimezone(settings.tz), end.astimezone(settings.tz)
            # Keep both dates across midnight and seconds when the service uses them.
            clock_format = "%H:%M:%S.%f" if start.microsecond or end.microsecond else "%H:%M:%S" if start.second or end.second else "%H:%M"
            first, last = start.strftime(clock_format), end.strftime(clock_format)
            when = (f"{start:%Y-%m-%d} · {first}–{last}" if start.date() == end.date()
                    else f"{start:%Y-%m-%d} {first} – {end:%Y-%m-%d} {last}") + f" ({settings.tz})"
        except (KeyError, ValueError, TypeError):
            return None
    elif "start" in item:
        try:
            start, end = (datetime.strptime(item[key], "%Y-%m-%d %H:%M %a") for key in ("start", "end"))
            if end <= start:
                return None
            when = f"{start:%Y-%m-%d %H:%M} – {end:%Y-%m-%d %H:%M} ({settings.tz})"
        except (KeyError, ValueError, TypeError):
            return None
    else:
        day, clock = _day(item.get("date")), item.get("time")
        if not day or not _time(clock) or clock[:5] >= clock[6:]:
            return None
        when = f"{day} · {clock} ({settings.tz})"
    if item.get("all_day") is True:
        when += " (весь день)" if language == "ru" else " (all day)"
    return when


def from_result(target, arguments, read_name, data, language="en"):
    """Project only one exact target from a known read's wire shape."""
    if not isinstance(data, dict) or "error" in data:
        return None
    if target == "sport_sport_checkin" and read_name in {"sport_get_sport_trainings", "sport_get_training", "sport_get_my_sport", "get_my_available_trainings"}:
        rows = ([data.get("training")] if read_name == "sport_get_training" else
                data.get("checked_in") if read_name == "sport_get_my_sport" else data.get("trainings"))
        if read_name == "get_my_available_trainings":
            if not all(isinstance(data.get(key), list) for key in ("available", "excluded", "unverified")):
                return None
            rows = data["available"] + data["excluded"] + data["unverified"]
        if not isinstance(rows, list):
            return None
        matches = [row for row in rows if isinstance(row, dict) and type(row.get("training_id")) is int
                   and row["training_id"] == arguments["training_id"]]
        if len(matches) != 1:
            return None
        item = matches[0]
        title, place = item.get("name"), item.get("place")
    elif target == "events_enroll_in_event" and read_name in {"events_get_university_events", "events_get_event", "events_events_list_events"}:
        rows = ([data.get("event")] if read_name == "events_get_event" else
                data.get("data") if read_name == "events_events_list_events" else data.get("events"))
        if not isinstance(rows, list):
            return None
        matches = [row for row in rows if isinstance(row, dict) and row.get("id") == arguments["event_id"]]
        if len(matches) != 1:
            return None
        item = matches[0]
        if read_name == "events_events_list_events":
            if data.get("action_id") != "events.events_list_events" or not isinstance(item.get("data"), dict):
                return None
            raw = item["data"]
            try:
                start, duration = datetime.fromisoformat(raw["starts_at"]), raw["duration_hours"]
                if type(duration) not in (int, float) or duration <= 0:
                    return None
                item = {"title": raw.get("name"), "starts_at": start.isoformat(),
                        "ends_at": (start + timedelta(hours=duration)).isoformat(),
                        "location": (raw.get("location") or {}).get("display_name")}
            except (KeyError, TypeError, ValueError, OverflowError, AttributeError):
                return None
        names = item.get("names")
        title = names.get(language) if isinstance(names, dict) else None
        title, place = title or item.get("title"), item.get("location")
    elif target == "account_cancel_booking" and read_name in {"account_get_my_schedule", "account_get_booking"}:
        rows = [data.get("booking")] if read_name == "account_get_booking" else data.get("bookings")
        if not isinstance(rows, list):
            return None
        matches = [row for row in rows if isinstance(row, dict) and row.get("service") == arguments["service"]
                   and row.get("booking_id") == arguments["booking_id"]]
        if len(matches) != 1:
            return None
        item = matches[0]
        title = item.get("title")
        if arguments["service"] == "music_room":
            place = "Музыкальная комната, спорткомплекс" if language == "ru" else "Music room, sports complex"
        else:
            place = item.get("room")
    else:
        return None
    when = _when(item, language)
    if when and _text(title) and _text(place):
        return f"{title} · {when} · {place}."
    return None


def from_messages(target, arguments, messages, language="en"):
    """Current-turn reads only, paired by call ID and concrete service/tool name."""
    lookup = detail_request(target, arguments)
    if lookup is None:
        return None
    if target == "sport_sport_checkin":
        sources = {"sport_get_sport_trainings", "sport_get_my_sport", "sport_get_training", "get_my_available_trainings"}
    elif target == "events_enroll_in_event":
        sources = {"events_get_university_events", "events_get_event", "events_events_list_events"}
    else:
        sources = {"account_get_my_schedule", "account_get_booking"}
    calls, found = {}, None
    for message in messages:
        if isinstance(message, HumanMessage):
            calls, found = {}, None
        elif isinstance(message, AIMessage):
            calls.update((call["id"], call) for call in message.tool_calls)
        elif isinstance(message, ToolMessage) and message.name in {"call_api_tool", "get_my_available_trainings"}:
            call = calls.get(message.tool_call_id)
            if not call or call["name"] != message.name:
                continue
            name = message.name if message.name == "get_my_available_trainings" else call["args"].get("name")
            if name == "get_my_available_trainings" and call["name"] != name:
                continue
            if name == target:
                found = None  # An intervening mutation invalidates the earlier snapshot.
                continue
            if name not in sources:
                continue
            found = None  # Never fall back to older success after a failed or incomplete read.
            if (message.status != "success" or not isinstance(message.content, str)
                    or (name == lookup["name"] and json.dumps(call["args"].get("arguments"), sort_keys=True)
                        != json.dumps(lookup["arguments"], sort_keys=True))):
                continue
            try:
                data = json.loads(message.content)
            except (ValueError, TypeError):
                continue
            found = from_result(target, arguments, name, data, language)
    return found
