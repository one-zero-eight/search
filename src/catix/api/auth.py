"""`Authorization: Bearer <InNoHassle token>`, as in the search service."""

from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from catix.innohassle import token as innohassle_token

bearer_scheme = HTTPBearer(
    scheme_name="Bearer",
    description="Token from [InNoHassle Accounts](https://innohassle.ru/account/token)",
    bearerFormat="JWT",
    auto_error=False,  # The 401 below carries the same text for a missing and for a bad token.
)


class UserTokenData(BaseModel):
    innohassle_id: str
    "InNoHassle Accounts ID"
    email: str
    "Innopolis email (@innopolis.university or @innopolis.ru)"
    telegram_id: int | None = None
    "User's Telegram ID connected to InNoHassle Accounts"


def verify_user(bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> UserTokenData:
    unauthorized = HTTPException(
        401, "Unable to verify credentials OR Credentials not provided", headers={"WWW-Authenticate": "Bearer"}
    )
    claims = innohassle_token.claims(bearer.credentials) if bearer and bearer.credentials else None
    if not claims or claims.get("uid") is None or claims.get("email") is None:
        raise unauthorized
    telegram_id = claims.get("telegram_id")
    return UserTokenData(
        innohassle_id=str(claims["uid"]),
        email=claims["email"],
        telegram_id=telegram_id if isinstance(telegram_id, int) else None,
    )


VerifiedDep = Annotated[UserTokenData, Depends(verify_user)]
