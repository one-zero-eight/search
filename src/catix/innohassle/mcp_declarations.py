"""Private callable attachments and the common guarded MCP function boundary."""

from functools import wraps
from inspect import signature


def metadata(auth: str, *, write: bool = False) -> dict:
    return {
        "meta": {"catix": {"auth": auth, "write": write}},
        "annotations": {
            "readOnlyHint": not write,
            "destructiveHint": write,
            "idempotentHint": not write,
            "openWorldHint": True,
        },
    }


def guarded(*, args_model=None, preview=None):
    """Keep signature/policy on a real function; no implementation registry.

    Validation and authorization precede the function body. ContextVars propagate
    through asyncio.to_thread, so credentials are never business arguments.
    """

    def decorate(function):
        parameters = signature(function)

        @wraps(function)
        async def entry(*args, **kwargs):
            from catix.innohassle import mcp_server

            bound = parameters.bind(*args, **kwargs)
            bound.apply_defaults()

            def execute(normalized, **credentials):
                parsed = args_model.model_validate(normalized).model_dump() if args_model else bound.arguments
                return function(**parsed)

            return await mcp_server._dispatch(function.__name__, dict(bound.arguments), execute=execute)

        setattr(entry, "_args_model", args_model)
        setattr(entry, "_preview", preview)
        return entry

    return decorate


def credential(*, sport: bool = False) -> str:
    """Only the request middleware can supply verified, request-local identity."""
    from catix.innohassle.mcp_server import _identity

    identity = _identity.get()
    if identity is None or not identity.uid or not identity.token:
        raise ValueError("Verified InNoHassle identity required.")
    value = identity.sport_token if sport else identity.token
    if not value:
        raise ValueError("Service credential required.")
    return value
