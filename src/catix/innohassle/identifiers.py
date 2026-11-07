"""Literal account identifiers, not caller-supplied URL syntax.

Never unquote, strip, or normalize an identifier. Percent escapes are not part
of these identifier formats, including nested escapes. Outlook's base64 IDs
may contain slashes; those are opaque data and must be quoted on the wire.
"""

import re


_SEGMENT = re.compile(r"[A-Za-z0-9._~@+=-]+")
_BASE64 = re.compile(r"(?:[A-Za-z0-9+/_-]{4})*(?:[A-Za-z0-9+/_-]{2}(?:==)?|[A-Za-z0-9+/_-]{3}=?)?")


def validate_room_id(value: str) -> str:
    """Room identifiers occupy one URL segment, without Outlook's base64 slashes."""
    if not isinstance(value, str) or value in {".", ".."} or not _SEGMENT.fullmatch(value):
        raise ValueError("Invalid room identifier.")
    return value


def validate_outlook_id(value: str) -> str:
    """Accept a literal segment or a base64 opaque ID, never a URL/path."""
    if not isinstance(value, str) or not value or value in {".", ".."}:
        raise ValueError("Invalid booking identifier.")
    if not _SEGMENT.fullmatch(value) and not _BASE64.fullmatch(value):
        raise ValueError("Invalid booking identifier.")
    return value
