"""Validate discovered write schemas before entering host approval."""

import json
from copy import deepcopy
from types import SimpleNamespace
from typing import Any

from jsonschema import FormatChecker
from jsonschema.validators import validator_for
from langchain.agents.middleware import AgentMiddleware, AgentState
from langchain.agents.middleware.types import hook_config
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.errors import GraphBubbleUp
from referencing import Registry
from typing_extensions import NotRequired

from catix.agent import api_context
from catix.agent.api_descriptions import describe_action
from catix.agent.api_tools import _credential_mode, _credentials, _needs_approval, _reviewed_args
from catix.innohassle import mcp_client


class PreflightError(ValueError):
    """Safe argument feedback, never transport exception diagnostics."""

    def __init__(self, message, *, requires_user_input=False):
        super().__init__(message)
        self.requires_user_input = requires_user_input


def requires_user_input(messages):
    """Trusted, matched preflight/helper artifacts since the actual user's turn."""
    calls = {}
    pending = False
    for message in messages:
        if isinstance(message, HumanMessage):
            calls, pending = {}, False
        elif isinstance(message, AIMessage):
            calls.update((call["id"], call["name"]) for call in message.tool_calls)
        elif (isinstance(message, ToolMessage) and calls.get(message.tool_call_id) == message.name
              and isinstance(message.artifact, dict) and message.artifact.get("requires_user_input") is True):
            pending = True
    return pending


def _schema(result, target):
    if isinstance(result, dict) and "error" not in result:
        for item in result.get("tools", []):
            if isinstance(item, dict) and item.get("name") == target:
                schema = item.get("inputSchema")
                if isinstance(schema, dict):
                    return schema
    raise PreflightError("The operation's inputSchema is unavailable; no action was executed.")


def _validate(schema, arguments):
    validator = validator_for(schema)
    validator.check_schema(schema)
    # An empty Registry refuses remote retrieval, while local $defs still resolve.
    errors = list(validator(schema, format_checker=FormatChecker(), registry=Registry()).iter_errors(arguments))
    if errors:
        missing = sorted({field for error in errors if error.validator == "required"
                          and isinstance(error.validator_value, list) and isinstance(error.instance, dict)
                          for field in error.validator_value if field not in error.instance})
        if missing:
            raise PreflightError(
                "Missing required arguments: " + ", ".join(missing) + ". "
                "Use values explicitly provided by the user or established by tool results. "
                "Otherwise ask the user before retrying; do not invent defaults or placeholders. "
                "No action was executed.", requires_user_input=True,
            )
        raise PreflightError("Arguments do not satisfy inputSchema. No action was executed.")


def _discovered_schema(messages, target):
    """Only successful tool results paired to actual catalogue calls are metadata."""
    calls, found = {}, None
    for message in messages:
        if isinstance(message, AIMessage):
            calls.update((call["id"], call) for call in message.tool_calls)
        if (not isinstance(message, ToolMessage) or message.name != "search_api_tools"
                or not isinstance(message.content, str)
                or message.status != "success"
                or calls.get(message.tool_call_id, {}).get("name") != "search_api_tools"):
            continue
        try:
            found = _schema(json.loads(message.content), target)
        except (ValueError, TypeError):
            continue
    return found


def _language(state):
    question = next((str(message.content) for message in reversed(state["messages"])
                     if isinstance(message, HumanMessage)), "")
    letters = [char for char in question if char.isalpha()]
    return "ru" if not letters or sum("Ѐ" <= char <= "ӿ" for char in letters) * 2 >= len(letters) else "en"


def _prepared(call, args, state, schema):
    # Defaults are for display only; execution and consent stay bound to the original JSON.
    displayed = {key: deepcopy(field["default"]) for key, field in schema.get("properties", {}).items()
                 if isinstance(field, dict) and "default" in field}
    displayed.update(deepcopy(args.arguments))
    _validate(schema, displayed)
    return {"call_id": call["id"], "target": args.name, "arguments": deepcopy(args.arguments),
            "description": describe_action(args.name, displayed, _language(state))}


def _context_request(prepared, state):
    lookup = api_context.detail_request(prepared["target"], prepared["arguments"])
    if lookup is not None:
        details = api_context.from_messages(prepared["target"], prepared["arguments"], state["messages"], _language(state))
        if details is None:
            return lookup
        prepared["description"] += " " + details
    return None


def _add_context(prepared, lookup, result, state):
    details = api_context.from_result(prepared["target"], prepared["arguments"], lookup["name"], result, _language(state))
    if details is None:
        raise PreflightError("Could not obtain the action's name, date, time and location for confirmation. No action was executed.")
    prepared["description"] += " " + details


class ApiPreflightState(AgentState):
    api_prepared: NotRequired[list[dict]]


class ApiPreflightMiddleware(AgentMiddleware[ApiPreflightState, Any]):
    """Listed after HITL: after_model hooks run in reverse order.

    This separate node commits descriptions before HITL interrupts. Resuming only
    replays HITL's pure lookup, not schema I/O or formatting. Each new model batch replaces
    the prepared list; failures return paired results for the entire unexecuted batch.
    """

    state_schema = ApiPreflightState

    @staticmethod
    def _clarify(request):
        # Inspect checkpoint state, not request-only HumanMessage reminders.
        if not requires_user_input(request.state["messages"]):
            return request
        return request.override(tool_choice="none", messages=[*request.messages, HumanMessage(
            "Required action arguments are missing. Ask the user for the missing values now. "
            "Do not invent values, retry the action, or call other tools before the user replies."
        )])

    def wrap_model_call(self, request, handler):
        return handler(self._clarify(request))

    async def awrap_model_call(self, request, handler):
        return await handler(self._clarify(request))

    @staticmethod
    def _candidates(state, runtime):
        last = state["messages"][-1]
        return [call for call in last.tool_calls if call["name"] == "call_api_tool"
                and _needs_approval(SimpleNamespace(tool_call=call, runtime=runtime))] if isinstance(last, AIMessage) else []

    @staticmethod
    def _finish(state, prepared, errors):
        if errors:
            return {"api_prepared": [], "messages": [ToolMessage(
                content=json.dumps({"error": str(errors.get(call["id"], "Not executed: another call in this batch failed preflight."))}),
                name=call["name"], tool_call_id=call["id"], status="error",
                artifact={"requires_user_input": True} if getattr(errors.get(call["id"]), "requires_user_input", False) else None,
            ) for call in state["messages"][-1].tool_calls], "jump_to": "model"}
        return {"api_prepared": prepared}

    def _blocked(self, state):
        # Fail closed even if a provider ignores tool_choice="none". Do not
        # allow an invented repair, read, or helper delegation to reach tools.
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls and requires_user_input(state["messages"]):
            error = PreflightError("Ask the user for the missing arguments before calling tools.", requires_user_input=True)
            return self._finish(state, [], {call["id"]: error for call in last.tool_calls})
        return None

    @hook_config(can_jump_to=["model"])
    def after_model(self, state, runtime):
        if blocked := self._blocked(state):
            return blocked
        errors, prepared = {}, []
        for call in self._candidates(state, runtime):
            args = _reviewed_args(call)
            try:
                schema = _discovered_schema(state["messages"], args.name)
                if schema is None:
                    schema = _schema(mcp_client.request_sync("search_tools", {"query": args.name}), args.name)
                _validate(schema, args.arguments)
                item = _prepared(call, args, state, schema)
                if lookup := _context_request(item, state):
                    token, credentials = _credentials(_credential_mode(lookup["name"]), runtime)
                    _add_context(item, lookup, mcp_client.request_sync("call_tool", lookup, token, **credentials), state)
                prepared.append(item)
            except GraphBubbleUp:
                raise
            except PreflightError as error:
                errors[call["id"]] = error
                if error.requires_user_input:
                    break
            except Exception:
                errors[call["id"]] = "Preflight is unavailable. No action was executed."
        return self._finish(state, prepared, errors)

    @hook_config(can_jump_to=["model"])
    async def aafter_model(self, state, runtime):
        if blocked := self._blocked(state):
            return blocked
        errors, prepared = {}, []
        for call in self._candidates(state, runtime):
            args = _reviewed_args(call)
            try:
                schema = _discovered_schema(state["messages"], args.name)
                if schema is None:
                    schema = _schema(await mcp_client.request("search_tools", {"query": args.name}), args.name)
                _validate(schema, args.arguments)
                item = _prepared(call, args, state, schema)
                if lookup := _context_request(item, state):
                    token, credentials = _credentials(_credential_mode(lookup["name"]), runtime)
                    _add_context(item, lookup, await mcp_client.request("call_tool", lookup, token, **credentials), state)
                prepared.append(item)
            except GraphBubbleUp:
                raise
            except PreflightError as error:
                errors[call["id"]] = error
                if error.requires_user_input:
                    break
            except Exception:
                errors[call["id"]] = "Preflight is unavailable. No action was executed."
        return self._finish(state, prepared, errors)
