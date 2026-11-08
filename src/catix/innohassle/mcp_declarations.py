"""Native credential dependencies and safe business-result boundaries."""

import logging
from functools import wraps
from time import perf_counter
from typing import Any

import httpx
from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult
from pydantic import BaseModel

from catix.innohassle import actions

log = logging.getLogger("catix.mcp.server")


def metadata(*, write: bool = False) -> dict:
    return {"annotations": {
        "readOnlyHint": not write,
        "destructiveHint": write,
        "idempotentHint": not write,
        "openWorldHint": True,
    }}


def require_innohassle() -> str:
    """Inject only the current request's verified InNoHassle credential."""
    from catix.innohassle.mcp_server import _identity

    identity = _identity.get()
    if identity is None or not identity.uid or not identity.token:
        raise ToolError("This account operation requires sign in on innohassle.ru.")
    return identity.token


def require_sport() -> str:
    """Sport needs both verified InNoHassle identity and its separate token."""
    from catix.innohassle.mcp_server import _identity

    require_innohassle()
    identity = _identity.get()
    if identity is None or not identity.sport_token:
        raise ToolError("This operation requires the separate InNoHassle Sport sign-in.")
    return identity.sport_token


def invalid_arguments(message: str = "Invalid account operation arguments; nothing was done.") -> dict:
    """Authored refusal, returned explicitly BEFORE any service I/O."""
    return {"done": False, "code": "invalid_arguments", "error": message}


def _redact(value: Any, secrets: tuple[str | None, ...]) -> Any:
    if isinstance(value, str):
        for secret in sorted((secret for secret in secrets if secret), key=len, reverse=True):
            value = value.replace(secret, "[redacted]")
        return value
    if isinstance(value, dict):
        return {_redact(key, secrets): _redact(item, secrets) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item, secrets) for item in value]
    if isinstance(value, BaseModel):
        return type(value).model_validate(_redact(value.model_dump(), secrets))
    return value


def result_boundary(*, write: bool = False):
    """Contain business failures before the SDK logs them; never validate inputs.

    FastMCP validates arguments and resolves dependencies before this body runs.
    No exception from inside a mutation is evidence that nothing was written.
    """
    def decorate(function):
        @wraps(function)
        def execute(*args, **kwargs):
            from catix.innohassle.mcp_server import _identity

            identity = _identity.get()
            secrets = (identity.token, identity.sport_token) if identity else ()
            started = perf_counter()
            try:
                return _redact(function(*args, **kwargs), secrets)
            except Exception as error:
                # Exception messages/tracebacks can contain tokens or upstream bodies.
                log.warning("MCP operation failed tool=%s exception=%s elapsed_ms=%.1f",
                            function.__name__, type(error).__name__, (perf_counter() - started) * 1000)
                if not write:
                    if isinstance(error, httpx.TimeoutException):
                        return ToolResult(is_error=True, structured_content={
                            "code": "upstream_timeout", "error": "The upstream API request timed out; no reliable result was obtained.",
                        })
                    if isinstance(error, actions.ReadError):
                        raise ToolError(_redact(str(error), secrets)) from None
                    raise ToolError("InNoHassle API is unavailable; try again later.") from None
                # Once a mutation body starts, even readback failures are ambiguous.
            return {
                "done": None,
                "outcome": "unknown",
                "error": "The action could not be confirmed; changes may have been applied. "
                "Read back the current state. Do not retry automatically.",
            }
        return execute
    return decorate
