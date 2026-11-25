"""What the user may change in an action waiting for their approval, and how a change becomes the action to run.

The site draws the form from `fields()`; the user's changed values come back as `edit()`, which returns the arguments
of the edited tool call after the same validation the model's own arguments passed. Anything else stays as the model sent it."""

import json
from typing import Any, Literal

from pydantic import ValidationError

from catix.agent.api_preflight import PreflightError, _validate
from catix.agent.calendar_tools import AddToAiCalendarArgs, UpdateAiCalendarArgs
from catix.agent.feedback_tools import LeaveFeedbackArgs

Kind = Literal["text", "textarea", "date", "time", "number"]


class InvalidEdit(ValueError):
    """The user's change cannot be applied; the message is safe to show them."""


# tool -> (key, kind, max length, optional)
_CALENDAR = (("title", "text", 100, False), ("day", "date", None, False), ("start_time", "time", None, False),
             ("end_time", "time", None, True), ("room", "text", 200, True))
EDITABLE: dict[str, tuple[tuple[str, Kind, int | None, bool], ...]] = {
    "rooms_book_room": (("title", "text", 100, False), ("day", "date", None, False),
                        ("time_from", "time", None, False), ("time_to", "time", None, False)),
    "music_book_music_room": (("day", "date", None, False), ("time_from", "time", None, False), ("time_to", "time", None, False)),
    "events_create_draft": (("name", "text", None, False), ("description", "textarea", None, True),
                            ("starts_at", "text", None, True), ("location", "text", None, True),
                            ("duration_hours", "number", None, True)),
    "events_update_draft": (("name", "text", None, True), ("description", "textarea", None, True),
                            ("starts_at", "text", None, True), ("location", "text", None, True),
                            ("duration_hours", "number", None, True)),
    "when2meet_create_meeting": (("name", "text", None, False), ("description", "textarea", None, True)),
    "leave_feedback": (("subject", "text", 100, False), ("feedback", "textarea", 4000, False)),
    "add_to_ai_calendar": _CALENDAR,
    "update_ai_calendar": _CALENDAR,
}
_MODELS = {"add_to_ai_calendar": AddToAiCalendarArgs, "update_ai_calendar": UpdateAiCalendarArgs, "leave_feedback": LeaveFeedbackArgs}
_ALL_DAY_ONLY = {"title", "day", "room"}


def target_and_args(name: str, args: dict) -> tuple[str, dict]:
    """The operation and its business arguments: `call_api_tool` carries them one level down."""
    args = {key: value for key, value in (args or {}).items() if key != "runtime"}
    if name == "call_api_tool" and isinstance(args.get("name"), str) and isinstance(args.get("arguments"), dict):
        return args["name"], args["arguments"]
    return name, args


def fields(name: str, args: dict) -> list[dict]:
    """The form of one action: only the fields it has (or may have), with their current values as text."""
    target, business = target_and_args(name, args)
    result = []
    for key, kind, max_length, optional in EDITABLE.get(target, ()):
        if business.get("all_day") is True and key not in _ALL_DAY_ONLY and target.endswith("_ai_calendar"):
            continue
        if key not in business and not optional:
            continue
        value = business.get(key)
        result.append({"name": key, "kind": kind, "value": "" if value is None else str(value),
                       "required": not optional, "max_length": max_length})
    return result


def _property_type(schema: dict | None, key: str) -> str | None:
    field = ((schema or {}).get("properties") or {}).get(key)
    kind = field.get("type") if isinstance(field, dict) else None
    return kind if isinstance(kind, str) else None


def _number(text: str, kind: str | None):
    try:
        return int(text) if kind == "integer" else float(text)
    except ValueError:
        raise InvalidEdit("A number is expected.") from None


def edit(name: str, args: dict, values: dict[str, str], schema: dict | None = None) -> dict:
    """The arguments of the tool call `name` with the user's `values`, validated; InvalidEdit when they do not hold."""
    target, business = target_and_args(name, args)
    allowed = {key: kind for key, kind, _, _ in EDITABLE.get(target, ())}
    for key in values:
        if key not in allowed:
            raise InvalidEdit(f"The field {key} cannot be changed.")
    changed = dict(business)
    for key, text in values.items():
        text = text.strip()
        if text == "":
            if target in _MODELS:
                changed[key] = None
            elif isinstance(business.get(key), str):
                changed[key] = ""  # an empty text is a value of its own (clearing a description)
            else:
                changed.pop(key, None)
        elif allowed[key] == "number":
            changed[key] = _number(text, _property_type(schema, key))
        else:
            changed[key] = text
    if target in _MODELS:
        if changed.get("end_time"):
            changed.pop("proposed_duration_minutes", None)  # the user gave the end themselves
        try:
            _MODELS[target].model_validate(changed)
        except ValidationError as error:
            raise InvalidEdit("; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors())) from None
        return changed
    if schema is None:
        raise InvalidEdit("The action cannot be changed.")
    try:
        _validate(schema, changed)
    except PreflightError:
        raise InvalidEdit("The values do not fit the operation.") from None
    return {"name": target, "arguments": changed}


def prepared_schema(prepared: list[dict], name: str, args: dict) -> dict | None:
    """The input schema the preflight kept for this exact call, to validate its edit."""
    target, business = target_and_args(name, args)
    wanted = json.dumps(business, sort_keys=True, default=str)
    for item in prepared or ():
        if item.get("target") == target and json.dumps(item.get("arguments"), sort_keys=True, default=str) == wanted:
            return item.get("schema")
    return None


def decision(name: str, args: dict, values: dict[str, str], schema: dict | None) -> dict[str, Any]:
    """The `edit` decision of one action."""
    new = edit(name, args, values, schema)
    return {"type": "edit", "edited_action": {"name": name, "args": new}}
