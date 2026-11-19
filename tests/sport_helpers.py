"""Shared synthetic Sport and agenda fixtures."""

import json

from langchain_core.messages import AIMessage, ToolMessage
from pydantic import SecretStr

from catix.agent.tools import AgentContext

DAY = "2026-11-09"
PERIOD = {"date_from": DAY, "date_to": DAY}
SCHEMA = {"type": "object", "additionalProperties": False,
          "properties": {"training_id": {"type": "integer", "minimum": 1},
                         "cancel": {"type": "boolean", "default": False}}, "required": ["training_id"]}
CONTEXT = AgentContext(innohassle_id="synthetic-owner", innohassle_token=SecretStr("synthetic-ih"),
                       sport_token=SecretStr("synthetic-sport"))


def interval(start, end, **fields):
    return {"starts_at": f"{DAY}T{start}:00+03:00", "ends_at": f"{DAY}T{end}:00+03:00", **fields}


FRISBEE = interval("08:00", "10:00", training_id=48591, name="Frisbee", date=DAY + " Mon",
                   time="08:00-10:00", place="[SC] Big Hall", checked_in=False, can_check_in=True)
BASKETBALL = interval("17:00", "18:30", training_id=46975, name="Basketball", date=DAY + " Mon",
                      time="17:00-18:30", place="[SC] Big Hall", checked_in=False, can_check_in=True)
CLASS = interval("09:00", "10:30", title="Logic and Discrete Math (lec)", kind="class")


def read_messages(name, data, ident, arguments=None):
    local = name in {"get_my_ai_calendar", "get_my_schedule"}
    return [AIMessage(content="", tool_calls=[{
        "name": name if local else "call_api_tool", "id": ident,
        "args": (arguments or PERIOD) if local else {"name": name, "arguments": arguments or PERIOD},
    }]), ToolMessage(content=json.dumps(data), name=name if local else "call_api_tool", tool_call_id=ident)]


def action(training_id=48591, cancel=None, ident="write"):
    args = {"training_id": training_id}
    if cancel is not None:
        args["cancel"] = cancel
    return {"name": "call_api_tool", "id": ident,
            "args": {"name": "sport_sport_checkin", "arguments": args}}


def agenda_data(classes=None, events=None):
    from catix.agent.schedule_tools import merge_schedule

    return merge_schedule([DAY, DAY], {"range": [DAY, DAY], "schedule": [CLASS] if classes is None else classes, "bookings": []},
                          {"range": [DAY, DAY], "events": events or []})
