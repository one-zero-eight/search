"""The user's personal calendar for InNoHassle and calendar apps: GET /users/my-calendar.ics.

The request carries the user's InNoHassle token (`Authorization: Bearer <JWT>`). It is checked against InNoHassle's
public keys, and its `telegram_id` says whose calendar it is: the events they added with "➕ В мой календарь" under an
answer (personal_calendar.py). The worker serves it on 127.0.0.1:FEED_PORT; an HTTPS reverse proxy exposes it.
"""

import contextlib
import logging

import jwt
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from catix import personal_calendar
from catix.settings import settings

log = logging.getLogger("catix.feed")

JWKS_URL = f"{str(settings.innohassle_api).rstrip('/')}/accounts/v0/.well-known/jwks.json"
_keys = jwt.PyJWKClient(JWKS_URL, cache_keys=True, lifespan=3600)

app = FastAPI(title="cAtIx calendar", docs_url=None, redoc_url=None, openapi_url=None)
bearer = HTTPBearer()


def user_key(token: str) -> str:
    """The user a valid InNoHassle token belongs to ('tg:<telegram id>'); 401 for a bad token, 403 without Telegram."""
    claims = None
    try:
        # InNoHassle's tokens name no key (no `kid`): try each of its signing keys.
        for key in _keys.get_signing_keys():
            with contextlib.suppress(jwt.InvalidSignatureError):
                claims = jwt.decode(token, key, algorithms=["RS256"])
                break
    except jwt.PyJWTError as e:
        raise HTTPException(401, "invalid token", headers={"WWW-Authenticate": "Bearer"}) from e
    if claims is None:
        raise HTTPException(401, "invalid token", headers={"WWW-Authenticate": "Bearer"})
    telegram_id = claims.get("telegram_id")
    if not isinstance(telegram_id, int):
        raise HTTPException(403, "no Telegram account is linked to this InNoHassle account")
    return f"tg:{telegram_id}"


@app.get("/users/my-calendar.ics")
def my_calendar(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> Response:
    return Response(personal_calendar.ics(user_key(credentials.credentials)), media_type="text/calendar; charset=utf-8")


class _Server(uvicorn.Server):
    @contextlib.contextmanager
    def capture_signals(self):  # The worker handles the signals, not the calendar inside it.
        yield


async def serve() -> None:
    log.info("calendar on 127.0.0.1:%s/users/my-calendar.ics", settings.feed_port)
    await _Server(uvicorn.Config(app, host="127.0.0.1", port=settings.feed_port, log_level="warning")).serve()
