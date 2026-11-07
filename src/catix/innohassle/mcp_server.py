"""One static, typed MCP catalogue, built once per internal HTTP server lifetime."""

import argparse
import asyncio
from collections.abc import Sequence
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_request
from fastmcp.server.middleware import Middleware
from fastmcp.server.transforms.search import BM25SearchTransform
from fastmcp.tools.base import Tool
from starlette.requests import Request
from starlette.responses import JSONResponse

from catix.innohassle import actions, mcp_domain
from catix.innohassle import token as token_verifier

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
    """Trusted runtime only: set BEFORE entering a fresh in-process Client(root).

    Never reuse a connected Client across users. Model arguments and MCP _meta
    cannot set this context. HTTP requests always use their own verified headers.
    """
    handle = _credential.set(token)
    sport_handle = _sport_credential.set(sport_token)

    try:
        yield
    finally:
        _sport_credential.reset(sport_handle)
        _credential.reset(handle)


class _RequestPolicy(Middleware):
    async def on_call_tool(self, context, call_next):
        # Check original JSON before FastMCP/Pydantic deserializes ClockTime or
        # coerces any other field. Leaf validation alone cannot recover lost input.
        name, arguments = context.message.name, context.message.arguments
        arguments = {} if arguments is None else arguments
        if name == "call_tool":
            # The SDK proxy accepts omitted/null arguments, but may only target
            # concrete declarations, never another proxy or discovery interface.
            if not isinstance(arguments, dict) or set(arguments) - {"name", "arguments"}:
                raise ToolError("Invalid account operation arguments; nothing was done.")
            name, arguments = arguments.get("name"), arguments.get("arguments")
            arguments = {} if arguments is None else arguments
        elif name == "preview_tool":
            if (
                not isinstance(arguments, dict)
                or set(arguments) - {"name", "arguments", "language"}
                or not isinstance(arguments.get("arguments"), dict)
                or arguments.get("language", "ru") not in ("ru", "en")
            ):
                raise ToolError("Invalid account operation arguments; nothing was done.")
            name, arguments = arguments.get("name"), arguments["arguments"]
        try:
            if context.message.name not in {"search_tools", "service_status"}:
                if not isinstance(name, str):
                    raise ValueError("Unknown API operation.")
                mcp_domain.validate(name, arguments)
        except ValueError as error:
            raise ToolError(str(error)) from None
        try:
            request = get_http_request()
        except RuntimeError:
            token = _credential.get()
            sport_token = _sport_credential.get()
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
        identity_handle = _identity.set(_Identity(token, sport_token, uid))
        try:
            return await call_next(context)
        finally:
            _identity.reset(identity_handle)


def _authorized(name: str):
    """Common verified-identity gate for execution and read-only previews."""
    operation = mcp_domain.policy(name)
    protected = operation["auth"] != "public"
    identity = _identity.get()
    if identity is None or (protected and (not identity.token or not identity.uid)):
        raise ToolError("This account operation requires sign in on innohassle.ru.")
    if operation["auth"] == "sport" and not identity.sport_token:
        raise ToolError("This operation requires the separate InNoHassle Sport sign-in.")
    return operation, identity


async def _dispatch(name: str, arguments: dict, *, execute) -> dict:
    """Guard every leaf: original JSON was validated before SDK coercion too."""
    try:
        normalized = mcp_domain.validate(name, mcp_domain._json(arguments))
    except ValueError as error:
        raise ToolError(str(error)) from None
    operation, identity = _authorized(name)
    protected = operation["auth"] != "public"

    try:
        result = await asyncio.to_thread(
            execute,
            normalized,
            token=identity.token if protected else None,
            sport_token=identity.sport_token if protected else None,
            uid=identity.uid if protected else None,
        )
        return mcp_domain._redact(result, (identity.token, identity.sport_token))
    except actions.ReadError as error:
        raise ToolError(str(error)) from None
    except Exception:
        if operation["write"]:
            return {
                "done": None,
                "outcome": "unknown",
                "error": "The action could not be confirmed; changes may have been applied. "
                "Read back the current state. Do not retry automatically.",
            }
        raise ToolError("InNoHassle API is unavailable; try again later.") from None


def _compact_search_results(tools: Sequence[Tool]) -> list[dict[str, Any]]:
    """One discovery format: retain callable inputs, omit output/schema metadata."""
    return [{"name": tool.name, "description": tool.description, "inputSchema": tool.parameters} for tool in tools]


async def build_server() -> FastMCP:
    """Register explicit typed functions without upstream schema I/O."""
    root = FastMCP("cAtIx InNoHassle", strict_input_validation=True, mask_error_details=True)
    root.add_middleware(_RequestPolicy())
    status: dict[str, dict[str, Any]] = {}
    for name, declared in mcp_domain.definitions().items():
        root.add_tool(declared)
        namespace = name.split("_", 1)[0]
        service = status.setdefault(namespace, {"registered": True, "tools": 0, "tool_names": []})
        service["tools"] += 1
        service["tool_names"].append(name)

    @root.tool
    def service_status() -> dict[str, Any]:
        """Complete concrete tool names/counts by namespace, not upstream health or search matches."""
        return status

    @root.tool(annotations={"readOnlyHint": True, "destructiveHint": False})
    async def preview_tool(name: str, arguments: dict, language: Literal["ru", "en"] = "ru") -> dict:
        """Authenticated read-only description of a proposed mutation."""
        try:
            normalized = mcp_domain.validate(name, arguments)
            operation, identity = _authorized(name)
            if not operation["write"]:
                raise ValueError("Only mutations have a preview.")
        except ValueError as error:
            raise ToolError(str(error)) from None
        try:
            description = await asyncio.to_thread(mcp_domain.describe_preview, name, normalized, identity, language)
        except Exception:
            raise ToolError("Preview details are unavailable; nothing was done.") from None
        return {
            "name": name,
            "arguments": normalized,
            "description": mcp_domain._redact(description, (identity.token, identity.sport_token)),
        }

    root.add_transform(BM25SearchTransform(
        always_visible=["service_status", "preview_tool"], search_result_serializer=_compact_search_results,
    ))

    @root.custom_route("/health", methods=["GET"])
    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return root


@asynccontextmanager
async def adapter():
    """Construct one catalogue for an HTTP-server lifetime or isolated test."""
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
                transport="http",
                host=options.host,
                port=options.port,
                path="/mcp",
                stateless_http=True,
                show_banner=False,
            )

    asyncio.run(serve())


if __name__ == "__main__":
    main()
