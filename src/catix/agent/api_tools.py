"""Discover, inspect and execute allowlisted InNoHassle OpenAPI actions.

No arbitrary URL, headers, token or user id is accepted from the model. Authentication
comes only from the site's runtime context, like the existing account tools.
"""

from langchain.tools import ToolRuntime
from langchain_core.tools import StructuredTool, tool
from pydantic import BaseModel, Field

from catix.innohassle import actions, mcp_client


class FindApiActionsArgs(BaseModel):
    query: str = Field(min_length=1, max_length=200, description="What the user wants to do, in Russian or English.")


class DescribeApiActionArgs(BaseModel):
    action_id: str = Field(min_length=1, max_length=120, description="Exact action_id returned by find_api_actions.")


class ExecuteApiActionArgs(DescribeApiActionArgs):
    parameters: dict = Field(default_factory=dict, description="Parameters from describe_api_action; {} when none are needed. Never credentials.")


@tool(args_schema=FindApiActionsArgs)
def find_api_actions(query: str) -> dict:
    """Search the permitted InNoHassle API actions by intent. Only printer state is enabled in this read-only pilot.
    Returns action ids to inspect with describe_api_action; it neither calls those operations nor changes anything."""
    try:
        return actions.find(query)
    except actions.ActionError as e:
        return {"error": str(e)}


@tool(args_schema=DescribeApiActionArgs)
def describe_api_action(action_id: str) -> dict:
    """Read an allowed action's current OpenAPI parameters, visible response fields and access requirements.
    Inspect before execute_api_action; do not infer parameters from another service's documentation."""
    try:
        return actions.describe(action_id)
    except actions.ActionError as e:
        return {"error": str(e)}


@tool(args_schema=ExecuteApiActionArgs)
def execute_api_action(action_id: str, runtime: ToolRuntime, parameters: dict | None = None) -> dict:
    """Execute an allowed read-only API action with schema-validated parameters and the signed-in user's access.
    Take action_id from discovery and parameters from its description. No arbitrary endpoints or writes are supported.
    A service error is not an empty result. Tokens and internal response fields are never shown."""
    secret = getattr(getattr(runtime, "context", None), "innohassle_token", None)
    try:
        return actions.execute(action_id, {} if parameters is None else parameters, secret.get_secret_value() if secret else None)
    except actions.ActionError as e:
        return {"error": str(e)}


class SearchApiToolsArgs(BaseModel):
    query: str = Field(min_length=1, max_length=200, description="What to find in the shared API tool catalogue, in Russian or English.")


class CallApiToolArgs(BaseModel):
    name: str = Field(min_length=1, max_length=128, description="Exact namespaced tool name returned by search_api_tools.")
    arguments: dict = Field(default_factory=dict, description="Arguments from that tool's inputSchema; {} when none. Never credentials.")


def _token(runtime: ToolRuntime) -> str | None:
    secret = getattr(getattr(runtime, "context", None), "innohassle_token", None)
    return secret.get_secret_value() if secret else None


def _search(query: str, runtime: ToolRuntime) -> dict:
    return mcp_client.request_sync("search_tools", {"query": query}, _token(runtime))


async def _asearch(query: str, runtime: ToolRuntime) -> dict:
    return await mcp_client.request("search_tools", {"query": query}, _token(runtime))


def _call(name: str, runtime: ToolRuntime, arguments: dict | None = None) -> dict:
    return mcp_client.request_sync("call_tool", {"name": name, "arguments": {} if arguments is None else arguments}, _token(runtime))


async def _acall(name: str, runtime: ToolRuntime, arguments: dict | None = None) -> dict:
    return await mcp_client.request("call_tool", {"name": name, "arguments": {} if arguments is None else arguments}, _token(runtime))


search_api_tools = StructuredTool.from_function(
    func=_search, coroutine=_asearch, name="search_api_tools", args_schema=SearchApiToolsArgs,
    description="Search the InNoHassle MCP catalogue: maps, clubs, music-room bookings, published events and printer state. "
                "Returns namespaced tools with complete inputSchema; no separate describe call is needed. "
                "Inspect service availability in services; an unavailable service is not an empty result.",
)
call_api_tool = StructuredTool.from_function(
    func=_call, coroutine=_acall, name="call_api_tool", args_schema=CallApiToolArgs,
    description="Call a read-only MCP tool discovered by search_api_tools using its exact name and inputSchema. "
                "Public data needs no sign-in; printer state needs the signed-in user's access. "
                "No arbitrary URLs, credentials, writing, printing or scanning. Stop once the result answers the question.",
)

# The original direct wrappers remain import-compatible but are no longer offered to models.
API_TOOLS = [search_api_tools, call_api_tool]
