"""MCP client used by cAtIx: HTTP only, with an independently running adapter.

A fresh protocol client and HTTP session belong to each invocation. No user token
is held on a process-wide client, cached with tool results, or sent as a model argument.
"""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from contextvars import copy_context
from http.cookiejar import CookieJar, DefaultCookiePolicy
from urllib.parse import urlsplit

import httpx2
# MCP lazily imports this on the first result. Load its format parsers at startup,
# not inside the first user request; keep SDK output validation fully enabled.
import jsonschema  # noqa: F401
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from catix.settings import settings
from catix.innohassle.mcp_access import CONFIRMATION_TOOLS

log = logging.getLogger("catix.mcp.client")
TIMEOUT = 40
MAX_OUTPUT_CHARS = 40_000


def _unknown_outcome() -> dict:
    return {"done": None, "outcome": "unknown",
            "error": "The operation may have completed, but its result could not be confirmed. "
                     "Do not retry automatically; use a fresh read to check the outcome."}


def validate_url(url: str) -> None:
    parsed = urlsplit(url)
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or "?" in url or "#" in url
            or (parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
                and url != "http://mcp:8010/mcp")):
        raise ValueError("MCP requires HTTPS, loopback HTTP or http://mcp:8010/mcp, "
                         "without credentials, query or fragment in its URL.")


async def _reject_redirect(response: httpx2.Response) -> None:
    # MCP SDK 2 follows same-origin redirects itself, ignoring the client's follow_redirects flag.
    if 300 <= response.status_code < 400:
        raise httpx2.HTTPStatusError("MCP redirects are refused.", request=response.request, response=response)


def _http_client(**kwargs):
    # The transport may suggest redirects/cookies: delegated credentials must never follow them.
    hooks = {key: list(value) for key, value in kwargs.pop("event_hooks", {}).items()}
    hooks["response"] = [_reject_redirect, *hooks.get("response", [])]
    kwargs["event_hooks"] = hooks
    kwargs.update(follow_redirects=False, cookies=CookieJar(policy=DefaultCookiePolicy(allowed_domains=[])))
    return httpx2.AsyncClient(**kwargs)


@asynccontextmanager
async def _connection(token: str | None, *, sport_token: str | None = None):
    url = str(settings.innohassle_mcp_url)
    validate_url(url)
    headers = {key: value for key, value in {"X-Innohassle-Token": token, "X-Sport-Token": sport_token}.items() if value}
    transport = StreamableHttpTransport(url, headers=headers, httpx_client_factory=_http_client)
    async with Client(transport, timeout=TIMEOUT, cache=False) as client:
        yield client


def _data(result):
    if result.is_error:
        # Our adapter produces safe errors. Do not echo arbitrary transport/server diagnostics.
        structured = result.structured_content
        if isinstance(structured, dict) and structured.get("code") == "upstream_timeout":
            return {"code": "upstream_timeout", "error": "The upstream API request timed out; no reliable result was obtained."}
        text = " ".join(getattr(block, "text", "") for block in result.content).casefold()
        if "sign in" in text or "authentication" in text or "401" in text:
            return {"error": "This API operation requires signing in on innohassle.ru with a valid account."}
        return {"error": "The MCP operation was refused or is unavailable. No reliable result was obtained."}
    value = result.data
    if len(json.dumps(value, ensure_ascii=False)) > MAX_OUTPUT_CHARS:
        return {"error": "The MCP response is too large to use safely."}
    return value


async def request(method: str, arguments: dict, token: str | None = None, *,
                  sport_token: str | None = None) -> dict:
    """Call one of the adapter's fixed interface tools; the model never chooses a URL or transport."""
    if method not in {"search_tools", "call_tool"}:
        return {"error": "Unsupported MCP interface operation."}
    mutation = method == "call_tool" and isinstance(arguments.get("name"), str) and arguments["name"] in CONFIRMATION_TOOLS
    try:
        async with asyncio.timeout(TIMEOUT):
            # Keep the original single-argument connection seam for ordinary reads.
            connection = _connection(token, sport_token=sport_token) if sport_token else _connection(token)
            async with connection as client:
                result = await client.call_tool(method, arguments, raise_on_error=False)
                # Protocol errors/oversized responses do not prove a write never happened.
                value = _data(result)
                if mutation and (result.is_error or not isinstance(value, dict)
                                 or not (type(value.get("done")) is bool
                                         or (value.get("done") is None and value.get("outcome") == "unknown"))):
                    return _unknown_outcome()
                if method == "search_tools":
                    if isinstance(value, dict) and "error" in value:
                        return value
                    if not isinstance(value, list):
                        return {"error": "The MCP server returned an invalid tool catalogue."}
                    status = _data(await client.call_tool("service_status", {}, raise_on_error=False))
                    return {"tools": value, "services": status}
                return value if isinstance(value, dict) else {"result": value}
    except Exception as e:  # Transport/protocol errors can contain credentials or private backend diagnostics.
        log.warning("MCP request failed (%s)", type(e).__name__)
        if mutation:
            return _unknown_outcome()
        return {"error": "The InNoHassle MCP adapter could not answer. Try again later."}


def request_sync(method: str, arguments: dict, token: str | None = None, *,
                 sport_token: str | None = None) -> dict:
    """Bridge sync callers; native async callers use request instead.

    A synchronous caller may run on an event-loop thread. Run its request in a
    context-preserving worker rather than nesting loops.
    """
    kwargs = {"sport_token": sport_token} if sport_token else {}

    def run():
        return asyncio.run(request(method, arguments, token, **kwargs))

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return run()
    with ThreadPoolExecutor(max_workers=1) as worker:
        return worker.submit(copy_context().run, run).result()
