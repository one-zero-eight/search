"""`Authorization: Bearer <InNoHassle token>`, as in the search service."""

from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, SecretStr

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
    token: SecretStr | None = Field(None, exclude=True, repr=False)
    "The token itself: the agent's account helper asks InNoHassle with it as the user (agent/account_tools.py). Never kept."


def _unauthorized() -> HTTPException:
    return HTTPException(401, "Unable to verify credentials OR Credentials not provided", headers={"WWW-Authenticate": "Bearer"})


def _claims(bearer: HTTPAuthorizationCredentials | None) -> dict:
    """The claims of a valid InNoHassle token; 401 for a missing or a bad one."""
    claims = innohassle_token.claims(bearer.credentials) if bearer and bearer.credentials else None
    if not claims:
        raise _unauthorized()
    return claims


def verify_user(bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> UserTokenData:
    claims = _claims(bearer)
    if claims.get("uid") is None or claims.get("email") is None:
        raise _unauthorized()
    telegram_id = claims.get("telegram_id")
    return UserTokenData(
        innohassle_id=str(claims["uid"]),
        email=claims["email"],
        telegram_id=telegram_id if isinstance(telegram_id, int) else None,
        token=SecretStr(bearer.credentials),  # type: ignore[union-attr]  # (valid claims: there is a token)
    )


class TokenAccount(BaseModel):
    innohassle_id: str
    "InNoHassle Accounts ID"
    telegram_id: int | None = None
    "User's Telegram ID connected to InNoHassle Accounts"


def verify_account(bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> TokenAccount:
    """The account of a valid token, without the email `verify_user` needs: the personal calendar of an account that has no
    Innopolis SSO opens too."""
    claims = _claims(bearer)
    if claims.get("uid") is None:
        raise _unauthorized()
    telegram_id = claims.get("telegram_id")
    return TokenAccount(innohassle_id=str(claims["uid"]), telegram_id=telegram_id if isinstance(telegram_id, int) else None)


VerifiedDep = Annotated[UserTokenData, Depends(verify_user)]
AccountDep = Annotated[TokenAccount, Depends(verify_account)]
