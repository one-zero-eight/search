from typing import Any, ClassVar

from fastapi import HTTPException
from pydantic import BaseModel
from starlette import status


class Detail(BaseModel):
    detail: str


class ExceptionBase(HTTPException):
    responses: ClassVar[dict[int | str, dict[str, Any]]]


class IncorrectCredentialsException(ExceptionBase):
    """
    HTTP_401_UNAUTHORIZED
    """

    def __init__(self, no_credentials: bool = False):
        if no_credentials:
            super().__init__(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=self.responses[401]["description"],
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            super().__init__(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=self.responses[401]["description"],
            )

    responses = {
        401: {
            "description": "Unable to verify credentials OR Credentials not provided",
            "model": Detail,
        }
    }


class ForbiddenException(ExceptionBase):
    """
    HTTP_403_FORBIDDEN
    """

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=self.responses[403]["description"],
        )

    responses = {403: {"description": "Not enough permissions", "model": Detail}}


class UserExists(ExceptionBase):
    """
    HTTP_409_CONFLICT
    """

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this telegram id already exists",
        )


class UserDidNotConnectTelegram(ExceptionBase):
    """
    HTTP_400_BAD_REQUEST
    """

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User did not connect telegram in InNoHassle-Accounts",
        )
