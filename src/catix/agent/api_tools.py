"""Shared MCP calls with name-based host consent and per-request credentials.

Business arguments belong to the server. The host only checks its generic call
shape, known names and trusted identity, and supplies the profile's schedule group.
"""

import json

from langchain.tools import ToolRuntime
from langchain_core.messages import HumanMessage
from langchain_core.tools import StructuredTool
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


def _token(runtime: ToolRuntime) -> str | None:
    secret = getattr(getattr(runtime, "context", None), "innohassle_token", None)
    return secret.get_secret_value() if secret else None


def _sport_credentials(runtime: ToolRuntime) -> dict:
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


def _credentials(mode: str, runtime: ToolRuntime) -> tuple[str | None, dict]:
    if mode == "public":
        return None, {}
    token = _token(runtime)
    if not token:
        raise ValueError("Account operations require signing in on the site innohassle.ru.")
    credentials = _sport_credentials(runtime) if mode == "sport" else {}
    if mode == "sport" and not credentials:
        raise ValueError("This operation requires the separate InNoHassle Sport sign-in.")
    return token, credentials


def _reviewed_args(tool_call: dict) -> CallApiToolArgs:
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
    args = _reviewed_args(tool_call)
    if args.name not in CONFIRMATION_TOOLS:
        raise ValueError("Read operations do not require approval.")
    question = next((str(message.content) for message in state.get("messages", [])
                     if isinstance(message, HumanMessage)), "")
    letters = [char for char in question if char.isalpha()]
    language = "ru" if not letters or sum("Ѐ" <= char <= "ӿ" for char in letters) * 2 >= len(letters) else "en"
    try:
        token, credentials = _credentials(_credential_mode(args.name), runtime)
        preview = mcp_client.request_sync("preview_tool", {
            "name": args.name, "arguments": args.arguments, "language": language,
        }, token, **credentials)
        echoed = preview.get("arguments") if isinstance(preview, dict) else None
        # The server may fill defaults, but must preserve every explicitly supplied
        # value. Only the description is used; execution still sends the raw intent.
        if (isinstance(preview, dict) and "error" not in preview and preview.get("name") == args.name
                and isinstance(echoed, dict)
                and all(key in echoed and json.dumps(echoed[key], sort_keys=True) == json.dumps(value, sort_keys=True)
                        for key, value in args.arguments.items())
                and isinstance(preview.get("description"), str) and preview["description"].strip()):
            return preview["description"]
    except Exception:
        # A failed preview must never suppress consent or disclose diagnostics.
        pass
    details = f"{args.name}: {json.dumps(args.arguments, ensure_ascii=False, sort_keys=True)}"
    return (("Не удалось получить подробности из MCP. Подтвердите действие с указанными параметрами: "
             if language == "ru" else "MCP details could not be read. Confirm the action with these exact arguments: ")
            + details)


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
