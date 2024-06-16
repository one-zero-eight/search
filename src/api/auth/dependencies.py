__all__ = ["verify_request"]


from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


# TODO
# from src.repositories.auth.repository import TokenRepository
from src.schemas.auth import SucceedVerificationResult

bearer_scheme = HTTPBearer(
    scheme_name="Bearer",
    description="Your JSON Web Token (JWT)",
    bearerFormat="JWT",
    auto_error=False,  # We'll handle error manually
)


async def get_access_token(
    bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str | None:
    # Prefer header to cookie
    if bearer:
        return bearer.credentials
    return None


async def verify_request(
    bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> SucceedVerificationResult:
    """
    Check one of the following:
    - Bearer token from header with BOT_TOKEN (or `user_id:bot_token`)
    - Bearer token from header with API_KEY
    :raises NoCredentialsException: if token is not provided
    :raises IncorrectCredentialsException: if token is invalid
    """

    # TODO
    pass

    # if not bearer:
    #     raise NoCredentialsException()
    #
    # api_verification_result = TokenRepository.verify_api_token(bearer.credentials)
    # if api_verification_result.success:
    #     return cast(SucceedVerificationResult, api_verification_result)
    #
    # bot_verification_result = TokenRepository.verify_bot_token(bearer.credentials)
    # if bot_verification_result.success:
    #     if bot_verification_result.telegram_id is not None:
    #         # add user_id to the result
    #         from src.repositories.users.repository import user_repository
    #
    #         bot_verification_result.user_id = await user_repository.get_user_id(
    #             telegram_id=bot_verification_result.telegram_id
    #         )
    #     return cast(SucceedVerificationResult, bot_verification_result)
    #
    # raise IncorrectCredentialsException()
