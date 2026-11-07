"""One internal MCP catalogue, generated independently from each reviewed API.

Only ``actions.execute`` talks to upstream APIs. The HTTP client used by FastMCP
is a policy transport, not a network client. Build explicitly with ``adapter``;
importing this module does not fetch API documentation.
"""

import argparse
import asyncio
import json
from contextlib import AsyncExitStack, asynccontextmanager, contextmanager
from contextvars import ContextVar
from typing import Any

import httpx2
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_request
from fastmcp.server.middleware import Middleware
from fastmcp.server.providers.openapi import MCPType, RouteMap
from fastmcp.server.transforms.search import BM25SearchTransform
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from catix.innohassle import actions, token as token_verifier

# Independent services share this startup window, not a serial total deadline.
COMPONENT_INIT_TIMEOUT = 8
_ORIGIN = "https://catix-policy.invalid"
_credential: ContextVar[str | None] = ContextVar("catix_mcp_credential", default=None)
_validated: ContextVar[str | None] = ContextVar("catix_mcp_validated", default=None)
_formats = FormatChecker()


@contextmanager
def credentials(token: str | None):
    """Trusted runtime only: wrap a fresh ``Client(root)`` session and its calls.

    A connected in-process Client runs its server in a child task, so establish
    this context BEFORE entering that Client. Never reuse a connected Client
    across users. Neither model arguments nor MCP ``_meta`` set this context.
    """
    handle = _credential.set(token)
    try:
        yield
    finally:
        _credential.reset(handle)


def _spec(service: str, definitions: dict[str, dict]) -> dict:
    paths, schemas = {}, {}
    for action_id, description in definitions.items():
        operation = action_id.split(".", 1)[1]
        parameters = description["parameters"]
        schema_name = operation + "Result"
        schemas[schema_name] = {
            "type": "object",
            "properties": {
                "action_id": {"type": "string"}, "data": description["returns"],
                "total": {"type": "integer"}, "truncated": {"type": "boolean"},
                "note": {"type": "string"},
            },
            "required": ["action_id", "data", "total", "truncated", "note"],
            "additionalProperties": False,
        }
        paths[description["path"]] = {"get": {
            "operationId": operation, "summary": description["description"],
            "description": "\n".join([
                description["description"], description["note"],
                "Sign-in required." if description["requires_sign_in"] else "Public read; no sign-in required.",
                actions.ACTIONS[action_id].keywords,
            ]),
            "parameters": [
                {"name": name, "in": "query", "required": name in parameters.get("required", []),
                 "schema": schema}
                for name, schema in parameters.get("properties", {}).items()
            ],
            "responses": {"200": {"description": "Reviewed, filtered response",
                "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{schema_name}"}}}}},
        }}
    return {"openapi": "3.1.0", "info": {"title": service, "version": "1"},
            "servers": [{"url": _ORIGIN}], "paths": paths, "components": {"schemas": schemas}}


class _PolicyTransport(httpx2.AsyncBaseTransport):
    def __init__(self, definitions: dict[str, dict]):
        self.definitions = {item["path"]: (key, item) for key, item in definitions.items()}

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        # Never consume headers: generated OpenAPI tools can forward inbound headers.
        if (request.url.scheme != "https" or request.url.host != "catix-policy.invalid"
                or request.url.port not in (None, 443) or request.method != "GET"
                or request.url.username or request.url.password or request.url.fragment
                or request.url.raw_path.split(b"?", 1)[0] != request.url.path.encode("utf-8")
                or request.content or request.url.path not in self.definitions):
            raise ToolError("This API request is not allowed; no request was sent.")
        action_id, description = self.definitions[request.url.path]
        pairs = list(request.url.params.multi_items())
        properties = description["parameters"].get("properties", {})
        if len({key for key, _ in pairs}) != len(pairs) or any(key not in properties for key, _ in pairs):
            raise ToolError("Invalid API parameters; no request was sent.")
        try:
            parameters = {
                key: value if Draft202012Validator(properties[key], format_checker=_formats).is_valid(value)
                else json.loads(value)
                for key, value in pairs
            }
            Draft202012Validator(description["parameters"], format_checker=_formats).validate(parameters)
        except (ValueError, ValidationError):
            raise ToolError("Invalid API parameters; no request was sent.") from None
        token = _validated.get() if description["requires_sign_in"] else None
        if description["requires_sign_in"] and not token:
            raise ToolError("This API action requires sign in on the site innohassle.ru.")
        try:
            result = await asyncio.to_thread(actions.execute, action_id, parameters, token)
        except actions.ActionError as error:
            raise ToolError(str(error)) from None
        except Exception:
            raise ToolError("InNoHassle API is unavailable; try again later.") from None
        return httpx2.Response(200, json=result)


class _RequestPolicy(Middleware):
    def __init__(self, definitions: dict[str, dict]):
        self.definitions = definitions

    async def on_call_tool(self, context, call_next):
        try:
            request = get_http_request()
        except RuntimeError:
            token = _credential.get()
        else:
            # HTTP callers never inherit the process's trusted runtime identity.
            token = request.headers.get("x-innohassle-token")
        if token and token != _validated.get():
            try:
                claims = await asyncio.to_thread(token_verifier.claims, token)
            except Exception:
                claims = None
            if not isinstance(claims, dict) or not claims.get("uid"):
                raise ToolError("InNoHassle sign-in is invalid; sign in on the site again.")
        description = self.definitions.get(context.message.name)
        if description is not None:
            try:
                Draft202012Validator(description["parameters"], format_checker=_formats).validate(context.message.arguments or {})
            except ValidationError:
                raise ToolError("Invalid API parameters; no request was sent.") from None
        handle = _validated.set(token)
        try:
            return await call_next(context)
        finally:
            _validated.reset(handle)


async def build_server(*, stack: AsyncExitStack) -> FastMCP:
    """Build now; the caller owns ``stack`` and must keep it open while serving."""
    root = FastMCP("cAtIx InNoHassle", strict_input_validation=True, mask_error_details=True)
    grouped: dict[str, list[str]] = {}
    for action_id, action in actions.ACTIONS.items():
        grouped.setdefault(action.service, []).append(action_id)
    status, tool_definitions = {}, {}
    root.add_middleware(_RequestPolicy(tool_definitions))
    async def prepare(service, action_ids, component_stack):
        try:
            # A component is all-or-nothing, including its document conversion.
            # Cancelling to_thread stops waiting, not the underlying HTTP work;
            # that work retains the upstream client's own network timeouts.
            async with asyncio.timeout(COMPONENT_INIT_TIMEOUT):
                definitions = {key: await asyncio.to_thread(actions.describe, key) for key in action_ids}
                for key, description in definitions.items():
                    action = actions.ACTIONS[key]
                    if (action.method != "GET" or description["method"] != "GET"
                            or description["path"] != action.prefix + action.path
                            or not description["read_only"]
                            or description["requires_sign_in"] != action.requires_token
                            or not set(description["parameters"].get("properties", {})) <= set(action.query_parameters)):
                        raise ValueError("Description does not match the reviewed operation policy.")
                client = await component_stack.enter_async_context(httpx2.AsyncClient(
                    base_url=_ORIGIN, transport=_PolicyTransport(definitions), follow_redirects=False, trust_env=False,
                ))
                component = FastMCP.from_openapi(
                    openapi_spec=_spec(service, definitions), client=client, name=service,
                    route_maps=[RouteMap(methods=["GET"], mcp_type=MCPType.TOOL)],
                    # FastMCP otherwise strips operationId suffixes after "__".
                    mcp_component_fn=lambda route, tool: setattr(tool, "name", route.operation_id),
                    strict_input_validation=True, mask_error_details=True,
                )
                expected_names = {key.split(".", 1)[1] for key in definitions}
                if {tool.name for tool in await component.list_tools()} != expected_names:
                    raise ValueError("Generated catalogue does not match the reviewed operations.")
                return component, definitions
        except Exception:
            # Upstream errors may carry URLs, response bodies or credentials.
            await component_stack.aclose()
            return None

    async with AsyncExitStack() as prepared_stack:
        tasks = []
        async with asyncio.TaskGroup() as group:
            for service, action_ids in grouped.items():
                component_stack = AsyncExitStack()
                # Own resources BEFORE starting tasks: a completed component may
                # otherwise be orphaned if the builder is cancelled before join.
                prepared_stack.push_async_callback(component_stack.aclose)
                tasks.append(group.create_task(prepare(service, action_ids, component_stack)))
        # Completion order must not change namespaces, catalogue or status order.
        for action_ids, task in zip(grouped.values(), tasks):
            namespace = actions.ACTIONS[action_ids[0]].namespace
            if task.result() is None:
                status[namespace] = {"available": False, "tools": 0,
                                     "message": "API component unavailable; try rebuilding later."}
                continue
            component, definitions = task.result()
            root.mount(component, namespace=namespace)
            tool_definitions.update({f"{namespace}_{key.split('.', 1)[1]}": value for key, value in definitions.items()})
            status[namespace] = {"available": True, "tools": len(definitions)}
        # Transfer every successful client's lifetime atomically, with no await.
        stack.push_async_callback(prepared_stack.pop_all().aclose)

    @root.tool
    def service_status() -> dict[str, Any]:
        """Availability of each reviewed API component; unavailable services are omitted from search."""
        return status

    root.add_transform(BM25SearchTransform(always_visible=["service_status"]))
    return root


@asynccontextmanager
async def adapter():
    """Own all generated clients for the lifetime of the yielded MCP server."""
    async with AsyncExitStack() as stack:
        yield await build_server(stack=stack)


def main():
    """Run a private internal HTTP adapter, not a public MCP OAuth service."""
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: loopback only)")
    parser.add_argument("--port", type=int, default=8010)
    options = parser.parse_args()

    async def serve():
        async with adapter() as root:
            await root.run_async(transport="http", host=options.host, port=options.port,
                                 path="/mcp", stateless_http=True, show_banner=False)

    asyncio.run(serve())


if __name__ == "__main__":
    main()
