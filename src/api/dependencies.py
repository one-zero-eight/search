__all__ = ["VerifiedDep"]

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.exceptions import IncorrectCredentialsException
from src.modules.inh_accounts_sdk import UserTokenData, inh_accounts

bearer_scheme = HTTPBearer(
    scheme_name="Bearer",
    description="Token from [InNoHassle Accounts](https://innohassle.ru/account/token)",
    bearerFormat="JWT",
    auto_error=False,  # We'll handle error manually
)


async def verify_user(
    bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> UserTokenData:
    token = bearer and bearer.credentials
    if not token:
        raise IncorrectCredentialsException(no_credentials=True)

    token_data = inh_accounts.decode_token(token)
    if token_data is None:
        raise IncorrectCredentialsException(no_credentials=False)
    return token_data


VerifiedDep = Annotated[UserTokenData, Depends(verify_user)]
