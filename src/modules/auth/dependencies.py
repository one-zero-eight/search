__all__ = ["verify_user", "verify_compute_service"]

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.exceptions import IncorrectCredentialsException
from src.modules.tokens.repository import TokenRepository

bearer_scheme = HTTPBearer(
    scheme_name="Bearer",
    description="Token from [InNoHassle Accounts](https://innohassle.ru/account/token)",
    bearerFormat="JWT",
    auto_error=False,  # We'll handle error manually
)


async def verify_user(
    bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    # Prefer header to cookie
    token = bearer and bearer.credentials
    if not token:
        raise IncorrectCredentialsException(no_credentials=True)
    token_data = await TokenRepository.verify_user_token(token, IncorrectCredentialsException())
    return token_data.innohassle_id


def verify_compute_service(
    bearer: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> bool:
    token = (bearer and bearer.credentials) or None
    if not token:
        raise IncorrectCredentialsException(no_credentials=True)
    return TokenRepository.verify_compute_service_token(token, IncorrectCredentialsException())
