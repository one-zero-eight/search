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
