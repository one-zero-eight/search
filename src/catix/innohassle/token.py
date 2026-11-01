"""Checks a user's InNoHassle token (`Authorization: Bearer <JWT>`) against InNoHassle's public keys."""

import contextlib

import jwt

from catix.settings import settings

JWKS_URL = f"{str(settings.innohassle_api).rstrip('/')}/accounts/v0/.well-known/jwks.json"
_keys = jwt.PyJWKClient(JWKS_URL, cache_keys=True, lifespan=3600)


def claims(token: str) -> dict | None:
    """The claims of a valid token (`uid`, `email`, `telegram_id`), or None for a bad one."""
    try:
        # InNoHassle's tokens name no key (no `kid`): try each of its signing keys.
        for key in _keys.get_signing_keys():
            with contextlib.suppress(jwt.InvalidSignatureError):
                return jwt.decode(token, key, algorithms=["RS256"])
    except jwt.PyJWTError:
        return None
    return None
