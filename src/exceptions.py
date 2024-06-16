from fastapi import HTTPException
from pydantic import BaseModel
from starlette import status


class ExceptionWithDetail(BaseModel):
    detail: str


class NoCredentialsException(HTTPException):
    """
    HTTP_401_UNAUTHORIZED
    """

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=self.responses[401]["description"],
            headers={"WWW-Authenticate": "Bearer"},
        )

    responses = {
        401: {
            "description": "No credentials provided",
            "headers": {"WWW-Authenticate": {"schema": {"type": "string"}}},
            "model": ExceptionWithDetail,
        }
    }


class IncorrectCredentialsException(HTTPException):
    """
    HTTP_401_UNAUTHORIZED
    """

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=self.responses[401]["description"],
        )

    responses = {
        401: {
            "description": "Could not validate credentials",
            "model": ExceptionWithDetail,
        }
    }


class ForbiddenException(HTTPException):
    """
    HTTP_403_FORBIDDEN
    """

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=self.responses[403]["description"],
        )

    responses = {403: {"description": "Not enough permissions", "model": ExceptionWithDetail}}


class UserExists(HTTPException):
    """
    HTTP_409_CONFLICT
    """

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this telegram id already exists",
        )


class UserDidNotConnectTelegram(HTTPException):
    """
    HTTP_400_BAD_REQUEST
    """

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User did not connect telegram in InNoHassle-Accounts",
        )
