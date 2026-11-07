"""Offline policy/schema lookup derived solely from explicit MCP functions.

Only pure model validation is shared with the host. Implementations execute in
MCP service functions; preview callbacks run on the authenticated server.
"""

from copy import deepcopy
from datetime import date, datetime, time
from functools import cache
from types import MappingProxyType
from typing import Any

from fastmcp.tools.function_tool import FunctionTool
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from pydantic import ValidationError as ModelValidationError


@cache
def definitions():
    """Compile SDK function tools once, offline, from locally declared functions."""
    from catix.innohassle import mcp_tools

    tools = {}
    for function in vars(mcp_tools).values():
        metadata = getattr(function, "__fastmcp__", None)
        if metadata is None:
            continue
        declared = FunctionTool.from_function(function, metadata=metadata)
        if declared.name in tools:
            raise ValueError("Duplicate MCP tool declaration.")
        local = (declared.meta or {}).get("catix", {})
        if local.get("auth") not in {"public", "innohassle", "sport"} or type(local.get("write")) is not bool:
            raise ValueError("MCP tool is missing trusted policy metadata.")
        if local["write"] and not callable(getattr(function, "_preview", None)):
            raise ValueError("Mutation is missing its preview.")
        tools[declared.name] = declared
    return MappingProxyType(tools)


def _definition(name: str):
    try:
        return definitions()[name]
    except (KeyError, TypeError):
        raise ValueError("Unknown API operation.") from None


def policy(name: str) -> dict:
    """Security authority comes from local declarations, never MCP search results."""
    local = _definition(name).meta["catix"]
    return {"auth": local["auth"], "write": local["write"]}


def schema(name: str) -> dict:
    return deepcopy(_definition(name).parameters)


def _json(value: Any) -> Any:
    if isinstance(value, time):
        # Never erase forbidden seconds/fractions/offsets before validation.
        if value.second or value.microsecond or value.tzinfo is not None:
            return value.isoformat()
        return value.isoformat(timespec="minutes")
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json(item) for item in value]
    return value


def validate(name: str, arguments: dict) -> dict:
    """Validate original JSON, then shared pure rules; normalize business arguments."""
    definition = _definition(name)
    declared = definition.parameters
    model = getattr(definition.fn, "_args_model", None)
    try:
        Draft202012Validator(declared, format_checker=FormatChecker()).validate(arguments)
        if model is not None:
            model_schema = deepcopy(model.model_json_schema())
            model_schema["additionalProperties"] = False
            Draft202012Validator(model_schema, format_checker=FormatChecker()).validate(arguments)
            return _json(model.model_validate(arguments).model_dump())
        normalized = {
            key: deepcopy(value["default"]) for key, value in declared["properties"].items() if "default" in value
        }
        normalized.update(arguments)
        return normalized
    except ModelValidationError as error:
        # Only authored validator messages; never include Pydantic input/context,
        # which can contain credentials supplied as malicious extra arguments.
        message = error.errors(include_input=False, include_context=False)[0]["msg"]
        raise ValueError(f"Invalid account operation arguments; nothing was done. {message}") from None
    except (ValidationError, TypeError):
        raise ValueError("Invalid account operation arguments; nothing was done.") from None


def describe_preview(name: str, arguments: dict, identity, language: str = "ru") -> str:
    """Server-only read-only preview callback; identity already verified by middleware."""
    normalized = validate(name, arguments)
    if not policy(name)["write"]:
        raise ValueError("Only mutations have a preview.")
    callback: Any = getattr(_definition(name).fn, "_preview", None)
    if not callable(callback):
        raise ValueError("Mutation is missing its preview.")
    return callback(normalized, identity, language)


def _redact(value: Any, secrets: tuple[str | None, ...]) -> Any:
    """Upstream refusals may reflect credentials; keep them out of tool results."""
    if isinstance(value, str):
        for secret in sorted((secret for secret in secrets if secret), key=len, reverse=True):
            value = value.replace(secret, "[redacted]")
        return value
    if isinstance(value, dict):
        return {_redact(key, secrets): _redact(item, secrets) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item, secrets) for item in value]
    return value
