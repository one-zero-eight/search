"""Typed MCP server with native registration, validation and dependencies."""

import argparse
import asyncio
from collections.abc import Sequence
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError, ValidationError
from fastmcp.server.dependencies import get_http_request, resolve_dependencies
from fastmcp.server.middleware import Middleware
from fastmcp.server.transforms.search import BM25SearchTransform
from fastmcp.tools.base import Tool, ToolResult
from fastmcp.tools.function_tool import FunctionTool
from pydantic import ValidationError as ModelValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse

from catix.innohassle import token as token_verifier
from catix.innohassle.mcp_declarations import invalid_arguments

_credential: ContextVar[str | None] = ContextVar("catix_mcp_credential", default=None)
_sport_credential: ContextVar[str | None] = ContextVar("catix_mcp_sport_credential", default=None)


@dataclass(frozen=True)
class _Identity:
    token: str | None
    sport_token: str | None
    uid: str | None


_identity: ContextVar[_Identity | None] = ContextVar("catix_mcp_identity", default=None)


@contextmanager
def credentials(token: str | None, *, sport_token: str | None = None):
    """Trusted in-process test/client context; HTTP always uses its own headers.

    Set before entering a fresh Client(root). Do not reuse it across users.
    """
    handle = _credential.set(token)
    sport_handle = _sport_credential.set(sport_token)
    try:
        yield
    finally:
        _sport_credential.reset(sport_handle)
        _credential.reset(handle)


class _RequestBoundary(Middleware):
    async def _invalid_call(
        self, declared: FunctionTool, arguments: Any, error: ModelValidationError | None = None,
    ) -> ToolResult:
        # SDK input validation precedes DI. Resolve the same credential dependencies
        # on a rejected call too, without invoking its body or revalidating arguments.
        # Business inputs never feed these dependencies.
        async with resolve_dependencies(declared.fn, {}):
            pass
        message = "Invalid account operation arguments; nothing was done."
        if error is not None:
            # Custom field validators MUST NOT put private input in ValueError
            # messages: excluding input/context does not sanitize msg itself.
            # Keep built-in diagnostics and extra-key locations out of replies.
            authored = [detail["msg"] for detail in error.errors(include_input=False, include_context=False)
                        if detail["type"] == "value_error"]
            if authored:
                message += f" {authored[0]}"
        if isinstance(arguments, dict):
            missing = [key for key in declared.parameters.get("required", []) if key not in arguments]
            if missing:
                message += f" Missing required fields: {', '.join(missing)}."
        if declared.annotations and declared.annotations.read_only_hint is False:
            return ToolResult(structured_content=invalid_arguments(message))
        raise ToolError(message)

    async def on_call_tool(self, context, call_next):
        name, arguments = context.message.name, context.message.arguments
        arguments = {} if arguments is None else arguments
        if name in {"search_tools", "service_status"}:
            return await call_next(context)
        if name == "call_tool":
            if not isinstance(arguments, dict) or set(arguments) - {"name", "arguments"}:
                raise ToolError("Invalid account operation arguments; nothing was done.")
            name, arguments = arguments.get("name"), arguments.get("arguments")
            arguments = {} if arguments is None else arguments
        if not isinstance(name, str) or name in {"call_tool", "search_tools", "service_status"}:
            raise ToolError("Unknown API operation.")
        declared = await context.fastmcp_context.fastmcp.get_tool(name)
        if not isinstance(declared, FunctionTool):
            raise ToolError("Unknown API operation.")
        try:
            request = get_http_request()
        except RuntimeError:
            token, sport_token = _credential.get(), _sport_credential.get()
        else:
            token = request.headers.get("x-innohassle-token")
            sport_token = request.headers.get("x-sport-token")
        uid = None
        if token:
            try:
                claims = await asyncio.to_thread(token_verifier.claims, token)
            except Exception:
                claims = None
            if not isinstance(claims, dict) or not isinstance(claims.get("uid"), str) or not claims["uid"].strip():
                raise ToolError("InNoHassle sign-in is invalid; sign in on the site again.")
            uid = claims["uid"]
        handle = _identity.set(_Identity(token, sport_token, uid))
        try:
            if not isinstance(arguments, dict):
                return await self._invalid_call(declared, arguments)
            try:
                return await call_next(context)
            except ValidationError as error:
                # Only the SDK's tagged argument failure proves execution did not
                # start. Body/output/dependency failures must never enter this path.
                if not isinstance(error.__cause__, ModelValidationError):
                    raise ToolError("The operation could not be completed.") from None
                return await self._invalid_call(declared, arguments, error.__cause__)
        finally:
            _identity.reset(handle)


def _compact_search_results(tools: Sequence[Tool]) -> list[dict[str, Any]]:
    """One discovery format: retain callable inputs, omit output/schema metadata."""
    return [{"name": tool.name, "description": tool.description, "inputSchema": tool.parameters} for tool in tools]


async def build_server() -> FastMCP:
    """Register decorated functions directly; the server owns their tool objects."""
    from catix.innohassle import mcp_tools

    root = FastMCP("cAtIx InNoHassle", strict_input_validation=True, mask_error_details=True, on_duplicate="error")
    root.add_middleware(_RequestBoundary())
    status: dict[str, dict[str, Any]] = {}
    for function in vars(mcp_tools).values():
        if getattr(function, "__fastmcp__", None) is None:
            continue
        declared = root.add_tool(function)
        namespace = declared.name.split("_", 1)[0]
        service = status.setdefault(namespace, {"registered": True, "tools": 0, "tool_names": []})
        service["tools"] += 1
        service["tool_names"].append(declared.name)

    @root.tool
    def service_status() -> dict[str, Any]:
        """Complete concrete tool names/counts by namespace, not upstream health or search matches."""
        return status

    root.add_transform(BM25SearchTransform(
        always_visible=["service_status"], search_result_serializer=_compact_search_results,
    ))

    @root.custom_route("/health", methods=["GET"])
    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return root


@asynccontextmanager
async def adapter():
    """Construct one server for an HTTP-server lifetime or isolated test."""
    yield await build_server()


def main():
    """Run a private internal HTTP adapter, not a public MCP OAuth service."""
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: loopback only)")
    parser.add_argument("--port", type=int, default=8010)
    options = parser.parse_args()

    async def serve():
        async with adapter() as root:
            await root.run_async(
                transport="http", host=options.host, port=options.port,
                path="/mcp", stateless_http=True, show_banner=False,
            )

    asyncio.run(serve())


if __name__ == "__main__":
    main()
