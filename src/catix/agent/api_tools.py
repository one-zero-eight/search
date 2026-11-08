"""Shared MCP calls with name-based host consent and per-request credentials.

Business rules belong to the server. Host preflight validates discovered JSON
schemas before approval; execution still sends the original business arguments.
"""

import json
from collections.abc import Mapping
from typing import Any

from langchain.tools import ToolRuntime
from langchain_core.tools import StructuredTool
from langgraph.runtime import Runtime
from pydantic import BaseModel, ConfigDict, Field, model_validator

from catix.innohassle import mcp_client
from catix.innohassle.mcp_access import CONFIRMATION_TOOLS, CREDENTIAL_MODES


class SearchApiToolsArgs(BaseModel):
    query: str = Field(min_length=1, max_length=200, description="What to find in the shared API tool catalogue, in Russian or English.")


class CallApiToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str = Field(min_length=1, max_length=128, description="Exact namespaced tool name returned by search_api_tools.")
    arguments: dict = Field(default_factory=dict, description="Arguments from that tool's inputSchema; {} when none. Never credentials.")

    @model_validator(mode="before")
    @classmethod
    def framework_runtime(cls, value):
        # ToolNode replaces outer runtime with this trusted object before validation.
        # All other outer fields remain forbidden, including role and credentials.
        if isinstance(value, dict) and isinstance(value.get("runtime"), ToolRuntime):
            return {key: item for key, item in value.items() if key != "runtime"}
        return value


def _token(runtime: ToolRuntime | Runtime[Any]) -> str | None:
    secret = getattr(getattr(runtime, "context", None), "innohassle_token", None)
    return secret.get_secret_value() if secret else None


def _sport_credentials(runtime: ToolRuntime | Runtime[Any]) -> dict:
    secret = getattr(getattr(runtime, "context", None), "sport_token", None)
    return {"sport_token": secret.get_secret_value()} if secret else {}


def _search(query: str, runtime: ToolRuntime) -> dict:
    # Tool metadata is public: do not trigger JWT/JWKS work for catalogue lookup.
    return mcp_client.request_sync("search_tools", {"query": query})


async def _asearch(query: str, runtime: ToolRuntime) -> dict:
    return await mcp_client.request("search_tools", {"query": query})


def _arguments(name: str, arguments: dict, runtime: ToolRuntime | None) -> dict:
    if name != "schedule_get_schedule" or runtime is None:
        return arguments
    from catix.agent.tools import GROUP_UNKNOWN, _named

    # The one host-specific argument: a group must be trusted or named by the user.
    # Dates, other fields and all business validation remain the server's concern.
    group = arguments.get("group")
    if group is not None:
        if not isinstance(group, str) or not _named(group, runtime):
            raise ValueError(GROUP_UNKNOWN)
    else:
        group = getattr(getattr(runtime, "context", None), "study_group", None)
    if not group:
        raise ValueError(GROUP_UNKNOWN)
    return {**arguments, "group": group}


def _credential_mode(name: str) -> str:
    if name not in CREDENTIAL_MODES:
        raise ValueError("Unknown API operation. Discover an exact operation with search_api_tools.")
    return CREDENTIAL_MODES[name]


def _credentials(mode: str, runtime: ToolRuntime | Runtime[Any]) -> tuple[str | None, dict]:
    if mode == "public":
        return None, {}
    token = _token(runtime)
    if not token:
        raise ValueError("Account operations require signing in on the site innohassle.ru.")
    credentials = _sport_credentials(runtime) if mode == "sport" else {}
    if mode == "sport" and not credentials:
        raise ValueError("This operation requires the separate InNoHassle Sport sign-in.")
    return token, credentials


def _reviewed_args(tool_call: Mapping[str, Any]) -> CallApiToolArgs:
    # ToolNode replaces ANY outer runtime. Apply the same canonicalization in the
    # consent gate so a model-supplied runtime can neither supply identity nor skip it.
    args = {key: value for key, value in tool_call["args"].items() if key != "runtime"}
    parsed = CallApiToolArgs.model_validate(args)
    _credential_mode(parsed.name)
    return parsed


def _needs_approval(request) -> bool:
    try:
        args = _reviewed_args(request.tool_call)
        if args.name not in CONFIRMATION_TOOLS:
            return False
        # Bots without user credentials should get the normal sign-in refusal,
        # not an interrupt they cannot meaningfully approve. This is not a role check.
        if getattr(request, "runtime", None) is not None:
            _credentials(_credential_mode(args.name), request.runtime)
        return True
    except (ValueError, TypeError, KeyError, AttributeError):
        return False


def _describe_mutation(tool_call, state, runtime) -> str:
    """Pure checkpoint lookup: HITL replays this callback when consuming a resume."""
    args = _reviewed_args(tool_call)
    if args.name not in CONFIRMATION_TOOLS:
        raise ValueError("Read operations do not require approval.")
    for prepared in state.get("api_prepared", []):
        if (prepared["call_id"] == tool_call.get("id") and prepared["target"] == args.name
                and json.dumps(prepared["arguments"], sort_keys=True) == json.dumps(args.arguments, sort_keys=True)):
            return prepared["description"]
    raise ValueError("No matching prepared approval description. Run preflight before HITL.")


def _prepare(name: str, arguments: dict | None, runtime: ToolRuntime):
    try:
        parsed = CallApiToolArgs(name=name, arguments={} if arguments is None else arguments)
        mode = _credential_mode(parsed.name)
        token, credentials = _credentials(mode, runtime)
        arguments = _arguments(parsed.name, parsed.arguments, runtime)
    except (ValueError, TypeError, KeyError) as error:
        return {"error": str(error)}
    return {"name": name, "arguments": arguments}, token, credentials


def _call(name: str, runtime: ToolRuntime, arguments: dict | None = None) -> dict:
    prepared = _prepare(name, arguments, runtime)
    if isinstance(prepared, dict):
        return prepared
    payload, token, credentials = prepared
    return mcp_client.request_sync("call_tool", payload, token, **credentials)


async def _acall(name: str, runtime: ToolRuntime, arguments: dict | None = None) -> dict:
    prepared = _prepare(name, arguments, runtime)
    if isinstance(prepared, dict):
        return prepared
    payload, token, credentials = prepared
    return await mcp_client.request("call_tool", payload, token, **credentials)


search_api_tools = StructuredTool.from_function(
    func=_search, coroutine=_asearch, name="search_api_tools", args_schema=SearchApiToolsArgs,
    description="Search the shared MCP catalogue: study-group timetables, courses and teachers, account schedules, rooms, music, "
                "events, Sport, maps, clubs and printer state. AI Calendar uses separate local tools. "
                "Returns top matching tools with description and complete inputSchema, not the whole catalogue. "
                "services includes every registered tool name: absence from top matches does not mean a tool is missing. "
                "Search an exact name from that list to get its arguments; no separate describe call is needed. "
                "Use call_api_tool; mutations require user approval. "
                "services reports the static catalogue, not upstream health; a failed API read is not an empty result.",
)


class _CallApiTool(StructuredTool):
    @property
    def tool_call_schema(self) -> type[BaseModel]:
        # Keep extra='forbid' when publishing the schema to the model.
        return CallApiToolArgs


call_api_tool = _CallApiTool.from_function(
    func=_call, coroutine=_acall, name="call_api_tool", args_schema=CallApiToolArgs,
    description="Call an MCP operation discovered by search_api_tools using its exact name and inputSchema. "
                "Mutations wait for the user's approval of the exact change. "
                "If a mutation outcome is unknown, never repeat it; use a fresh read to reconcile. "
                "Public data needs no sign-in; account reads and printer state need sign-in, Sport needs its separate token. "
                "For schedule_get_schedule only, omit group to use the trusted profile group; an explicit group must be "
                "the user's own or named in their question. If unknown, ask; never copy an example group. "
                "Never supply arbitrary URLs, credentials, identities or roles. No printing or scanning. "
                "Stop once the result answers the question.",
)

# Every graph exposing this common tool installs the same conditional gate.
API_APPROVAL = {"call_api_tool": {"allowed_decisions": ["approve", "reject"],
                                 "description": _describe_mutation, "when": _needs_approval}}
API_TOOLS = [search_api_tools, call_api_tool]
