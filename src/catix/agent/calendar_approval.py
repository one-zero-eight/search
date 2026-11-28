"""Native orchestrator approval for local AI Calendar actions, independent of MCP."""

from pydantic import ValidationError

from catix.agent.approval import WAITING_FOR_USER
from catix.agent.calendar_tools import AddToAiCalendarArgs, RemoveFromAiCalendarArgs, UpdateAiCalendarArgs, _mutation_key


def _calendar_business_args(args: dict) -> dict:
    """ToolNode overwrites runtime; normalize the same field before consent and execution."""
    return {key: value for key, value in args.items() if key != "runtime"}


def _valid(request) -> bool:
    schema = {"add_to_ai_calendar": AddToAiCalendarArgs, "update_ai_calendar": UpdateAiCalendarArgs,
              "remove_from_ai_calendar": RemoveFromAiCalendarArgs}[request.tool_call["name"]]
    try:
        schema.model_validate(_calendar_business_args(request.tool_call["args"]))
    except ValidationError:
        return False
    key, _ = _mutation_key(request.runtime)
    return key is not None


# The site shows the arguments itself and lets the user change them (approval_edit.EDITABLE).
LOCAL_CALENDAR_APPROVAL = {
    name: {"allowed_decisions": ["approve", "edit", "reject"], "description": WAITING_FOR_USER, "when": _valid}
    for name in ("add_to_ai_calendar", "update_ai_calendar", "remove_from_ai_calendar")
}
