"""Host-side personal-calendar checks. Sport eligibility is not personal availability.

Only matched tool results supply facts; never assistant text or model-supplied
conflict flags. This policy belongs to cAtIx, which owns the local AI Calendar,
not to the standalone MCP server.
"""

import json
from copy import deepcopy
from datetime import date, datetime, time, timedelta

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.errors import GraphBubbleUp

from catix.agent import schedule_tools
from catix.innohassle import mcp_client
from catix.innohassle.mcp_access import CONFIRMATION_TOOLS
from catix.settings import settings


class ScheduleCheckError(ValueError):
    requires_user_input = False

    def __init__(self, code, message, **details):
        super().__init__(message)
        self.result = {"done": False, "code": code, "error": message, **details}


def _unknown(message):
    return ScheduleCheckError("schedule_unverified", message + " Nothing was written; do not claim the time is free.")


def _interval(item):
    try:
        start = datetime.fromisoformat(item["starts_at"])
        if start.utcoffset() is None:
            raise ValueError
        # Local all-day entries have no end and may store the display default hour.
        # Their calendar semantics are one entire local day, not an unknown timed event.
        if item.get("all_day") is True and item.get("ends_at") is None:
            start = datetime.combine(start.astimezone(settings.tz).date(), time.min, settings.tz)
            return start, start + timedelta(days=1)
        end = datetime.fromisoformat(item["ends_at"])
        if start.utcoffset() is None or end.utcoffset() is None or end <= start:
            raise ValueError
        return start.astimezone(settings.tz), end.astimezone(settings.tz)
    except (KeyError, TypeError, ValueError, AttributeError):
        raise _unknown("Missing or invalid timezone-aware starts_at/ends_at; read the full event duration.") from None


def _period(item):
    start, end = _interval(item)
    return {"date_from": start.date().isoformat(),
            "date_to": (end - timedelta(microseconds=1)).date().isoformat()}


def _covers(data, period):
    try:
        first, last = data["range"]
        return date.fromisoformat(first) <= date.fromisoformat(period["date_from"]) <= date.fromisoformat(period["date_to"]) <= date.fromisoformat(last)
    except (KeyError, TypeError, ValueError):
        return False


def _reads(messages):
    """Latest result per exact source since the last real user turn, including failures."""
    calls, reads = {}, {}
    for message in messages:
        if isinstance(message, HumanMessage):
            calls, reads = {}, {}
        elif isinstance(message, AIMessage):
            calls.update((call["id"], call) for call in message.tool_calls)
        elif isinstance(message, ToolMessage):
            call = calls.get(message.tool_call_id)
            if not call or message.name != call["name"]:
                continue
            name = call["args"].get("name") if call["name"] == "call_api_tool" else call["name"]
            if message.name in {"ask_docs", "ask_chats"} and isinstance(message.artifact, dict):
                receipts = message.artifact.get("action_receipts", [])
                if isinstance(receipts, list) and any(
                        isinstance(receipt, dict) and receipt.get("outcome") in {"confirmed", "unknown"}
                        and receipt.get("name") in CONFIRMATION_TOOLS | {"add_to_ai_calendar", "update_ai_calendar", "remove_from_ai_calendar"}
                        for receipt in receipts):
                    reads["get_my_schedule"] = None
                continue
            if (call["name"] == "call_api_tool" and name in CONFIRMATION_TOOLS
                    or call["name"] in {"add_to_ai_calendar", "update_ai_calendar", "remove_from_ai_calendar"}):
                # Even an uncertain write may have changed personal availability.
                reads["get_my_schedule"] = None
                continue
            if message.name == "get_my_available_music_windows":
                reads["get_my_schedule"] = None
                if message.status == "success" and isinstance(message.artifact, dict):
                    source = message.artifact.get("music_arguments")
                    agenda = message.artifact.get("agenda")
                    arguments = {key: value for key, value in call["args"].items() if value is not None}
                    if (isinstance(source, dict) and isinstance(agenda, dict)
                            and json.dumps(source, sort_keys=True) == json.dumps(arguments, sort_keys=True)
                            and agenda.get("range") == [arguments.get("day"), arguments.get("day")]):
                        reads["get_my_schedule"] = agenda
                continue
            if message.name == "get_my_available_trainings":
                # Native host artifacts hold the exact read snapshot without repeating
                # the whole agenda in the model-visible recommendation list.
                reads["sport_get_sport_trainings"] = reads["get_my_schedule"] = None
                reads["training_arguments"] = {}
                if message.status == "success" and isinstance(message.artifact, dict):
                    reads["sport_get_sport_trainings"] = message.artifact.get("trainings")
                    reads["get_my_schedule"] = message.artifact.get("agenda")
                    reads["training_arguments"] = message.artifact.get("training_arguments", {})
                continue
            if name not in {"sport_get_sport_trainings", "get_my_schedule"}:
                continue
            if (name == "get_my_schedule" and call["name"] != "get_my_schedule"
                    or name == "sport_get_sport_trainings" and call["name"] != "call_api_tool"):
                continue
            try:
                data = json.loads(message.content) if message.status == "success" and isinstance(message.content, str) else None
            except (TypeError, ValueError):
                data = None
            if name == "get_my_schedule" and isinstance(data, dict):
                period = data.get("range")
                if (not isinstance(period, list) or len(period) != 2
                        or any(call["args"].get(key) is not None and call["args"][key] != period[index]
                               for index, key in enumerate(("date_from", "date_to")))):
                    data = None
            reads[name] = data
            if name == "sport_get_sport_trainings":
                reads["training_arguments"] = call["args"].get("arguments") or {}
    return reads


def _training(data, training_id):
    if not isinstance(data, dict) or "error" in data or not isinstance(data.get("trainings"), list):
        raise _unknown("Read sport_get_sport_trainings for the chosen date before signing up.")
    matches = [row for row in data["trainings"] if isinstance(row, dict)
               and type(row.get("training_id")) is int and row["training_id"] == training_id]
    if len(matches) != 1:
        raise _unknown("The exact training was not uniquely found. Read sport_get_sport_trainings again.")
    item = matches[0]
    period = _period(item)
    if not _covers(data, period):
        raise _unknown("The Sport read does not cover the entire training.")
    if item.get("checked_in") is not False or item.get("can_check_in") is not True:
        raise ScheduleCheckError("training_unavailable", "The training is already selected or signup is not available. Nothing was written.")
    return item


def _busy(agenda, period):
    if (not isinstance(agenda, dict) or "error" in agenda or not _covers(agenda, period)
            or agenda.get("complete") is not True or agenda.get("truncated") is not False
            or agenda.get("not_read") != [] or not isinstance(agenda.get("events"), list)
            or type(agenda.get("total")) is not int or agenda["total"] != len(agenda["events"])):
        raise _unknown(f"Read complete get_my_schedule with date_from={period['date_from']}, date_to={period['date_to']}.")
    sources = agenda.get("sources")
    if (not isinstance(sources, dict) or set(sources) != {"innohassle", "ai_calendar"}
            or any(not isinstance(value, dict) or value.get("status") != "complete" or value.get("truncated") is not False
                   for value in sources.values())):
        raise _unknown("Both personal external calendars and AI Calendar must be fully read.")
    for item in agenda["events"]:
        _interval(item)  # Unknown durations cannot silently become free time.
    return agenda["events"]


def _overlaps(a, b):
    start, end = _interval(a)
    other_start, other_end = _interval(b)
    return start < other_end and other_start < end


def training_conflicts(training_id, trainings, agenda):
    """The shared eligibility/interval check for recommendations and signup."""
    item = _training(trainings, training_id)
    period = _period(item)
    busy = _busy(agenda, period)
    return item, [event for event in busy if _overlaps(item, event)]


def check_training(training_id, trainings, agenda):
    """Return the exact checked target or structured refusal, without I/O."""
    item, conflicts = training_conflicts(training_id, trainings, agenda)
    if conflicts:
        alternatives = []
        for candidate in trainings["trainings"]:
            try:
                candidate, overlaps = training_conflicts(candidate["training_id"], trainings, agenda)
                if not overlaps:
                    alternatives.append(candidate)
            except (ScheduleCheckError, KeyError, TypeError):
                continue
        raise ScheduleCheckError(
            "schedule_conflict", "The selected training overlaps the personal calendar. Do not request ordinary approval "
            "for this slot. Offer non-overlapping alternatives; never write or move events automatically.",
            conflicts=conflicts, alternatives=alternatives,
        )
    return {"training": deepcopy(item), "period": _period(item)}


def prepare_training(arguments, messages, runtime=None):
    reads = _reads(messages)
    if "get_my_schedule" not in reads and runtime is not None:
        training = _training(reads.get("sport_get_sport_trainings"), arguments["training_id"])
        period = _period(training)
        reads["get_my_schedule"] = schedule_tools.read_my_schedule(
            runtime, date.fromisoformat(period["date_from"]), date.fromisoformat(period["date_to"]))
    checked = check_training(arguments["training_id"], reads.get("sport_get_sport_trainings"),
                             reads.get("get_my_schedule"))
    # Preserve the source query, not the training's display name. The unfiltered
    # read can truncate the approved target even when its eligibility is unchanged.
    source_arguments = reads.get("training_arguments", {})
    checked["training_filters"] = {key: deepcopy(source_arguments[key]) for key in ("sport",) if key in source_arguments}
    return checked


def batch_conflicts(prepared):
    """Parallel proposals are not in either calendar yet; compare them to each other."""
    errors = {}
    checked = [item for item in prepared if "schedule_check" in item]
    for index, item in enumerate(checked):
        for other in checked[index + 1:]:
            first = item["schedule_check"].get("booking", item["schedule_check"].get("training"))
            second = other["schedule_check"].get("booking", other["schedule_check"].get("training"))
            if _overlaps(first, second):
                error = ScheduleCheckError("schedule_conflict", "These booking or signup requests overlap each other. "
                                           "Choose non-overlapping times; nothing was written.")
                errors[item["call_id"]] = errors[other["call_id"]] = error
    return errors


def _approved_training(arguments, runtime):
    state = getattr(runtime, "state", None) or {}
    for prepared in state.get("api_prepared", []):
        if (prepared.get("call_id") == getattr(runtime, "tool_call_id", None)
                and prepared.get("target") == "sport_sport_checkin"
                and json.dumps(prepared.get("arguments"), sort_keys=True) == json.dumps(arguments, sort_keys=True)
                and isinstance(prepared.get("schedule_check"), dict)):
            return prepared["schedule_check"]
    raise _unknown("No matching calendar-checked approval. Read calendars and request approval again.")


def _unchanged(approved, trainings, arguments):
    current = _training(trainings, arguments["training_id"])
    previous = approved["training"]
    if (_interval(current) != _interval(previous)
            or any(current.get(field) != previous.get(field) for field in ("name", "place"))):
        raise ScheduleCheckError("training_changed", "The training's time, name or location changed after approval. "
                                 "Nothing was written; read it again and ask for a new approval.")


def recheck_training(arguments, runtime, token, credentials):
    """Read-only checks after consent. Exceptions here cannot mean an unknown write."""
    try:
        approved = _approved_training(arguments, runtime)
        period = approved["period"]
        read_arguments = {**period, **approved.get("training_filters", {})}
        trainings = mcp_client.request_sync("call_tool", {"name": "sport_get_sport_trainings", "arguments": read_arguments},
                                           token, **credentials)
        _unchanged(approved, trainings, arguments)
        agenda = schedule_tools.read_my_schedule(runtime, date.fromisoformat(period["date_from"]), date.fromisoformat(period["date_to"]))
        check_training(arguments["training_id"], trainings, agenda)
    except GraphBubbleUp:
        raise
    except ScheduleCheckError as error:
        return error.result
    except Exception:
        return _unknown("The fresh calendar check failed.").result
    return None


async def arecheck_training(arguments, runtime, token, credentials):
    try:
        approved = _approved_training(arguments, runtime)
        period = approved["period"]
        read_arguments = {**period, **approved.get("training_filters", {})}
        trainings = await mcp_client.request("call_tool", {"name": "sport_get_sport_trainings", "arguments": read_arguments},
                                            token, **credentials)
        _unchanged(approved, trainings, arguments)
        agenda = await schedule_tools.aread_my_schedule(runtime, date.fromisoformat(period["date_from"]), date.fromisoformat(period["date_to"]))
        check_training(arguments["training_id"], trainings, agenda)
    except GraphBubbleUp:
        raise
    except ScheduleCheckError as error:
        return error.result
    except Exception:
        return _unknown("The fresh calendar check failed.").result
    return None
