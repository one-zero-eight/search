"""Checks a user's InNoHassle token (`Authorization: Bearer <JWT>`) against InNoHassle's public keys."""

import contextlib

import jwt

from catix.settings import settings

JWKS_URL = f"{str(settings.innohassle_api).rstrip('/')}/accounts/v0/.well-known/jwks.json"
_keys = jwt.PyJWKClient(JWKS_URL, cache_keys=True, lifespan=3600)


def _decode(token: str, audience: str | None) -> dict | None:
    try:
        # InNoHassle's tokens name no key (no `kid`): try each of its signing keys.
        for key in _keys.get_signing_keys():
            with contextlib.suppress(jwt.InvalidSignatureError):
                return jwt.decode(token, key, algorithms=["RS256"], audience=audience)
    except jwt.PyJWTError:
        return None
    return None


def claims(token: str) -> dict | None:
    """The claims of a valid token (`uid`, `email`, `telegram_id`), or None for a bad one. (A token for one service, such as
    the Sport token, names its audience and is not one.)"""
    return _decode(token, None)


def sport_email(token: str) -> str | None:
    """The email of a valid InNoHassle Sport token (Accounts /tokens/generate-my-sport-token: audience `sport`, a day), or
    None for a bad or an expired one."""
    found = _decode(token, "sport")
    email = (found or {}).get("email")
    return email if isinstance(email, str) else None
