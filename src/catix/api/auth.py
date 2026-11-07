"""`Authorization: Bearer <InNoHassle token>`, as in the search service."""

import asyncio
from typing import Annotated

from fastapi import Depends, Header, HTTPException
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
    "The token itself: MCP account operations ask InNoHassle with it as the user (innohassle/mcp_account.py). Never kept."
    sport_token: SecretStr | None = Field(None, exclude=True, repr=False)
    "The user's InNoHassle Sport token (`X-Sport-Token`, verify_asker): the account helper reads their sport with it. Never kept."


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


async def verify_asker(
    user: VerifiedDep,
    sport_token: Annotated[
        str | None,
        Header(
            alias="X-Sport-Token",
            description="The user's InNoHassle Sport token ([InNoHassle Accounts](https://api.innohassle.ru/accounts/v0/tokens/"
            "generate-my-sport-token), as the site keeps it): the assistant reads their sport hours and trainings and checks "
            "them in to a training (after they approve it) with it. Without it, or with one of another user or expired, the "
            "assistant has no access to their sport.",
        ),
    ] = None,
) -> UserTokenData:
    """The user who asks the assistant, with their Sport token when it is valid and theirs (the same Innopolis email). (Async:
    a request without the header goes on at once, in the order the questions came.)"""
    if not sport_token:
        return user
    email = await asyncio.to_thread(innohassle_token.sport_email, sport_token)  # (the keys may be fetched)
    if email and email.lower() == user.email.lower():
        return user.model_copy(update={"sport_token": SecretStr(sport_token)})
    return user


AskerDep = Annotated[UserTokenData, Depends(verify_asker)]
