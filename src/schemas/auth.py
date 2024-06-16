__all__ = ["VerificationResult", "VerificationSource", "SucceedVerificationResult", "VerificationResultWithUserId"]

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel


class VerificationSource(StrEnum):
    BOT = "bot"
    API = "api"


class VerificationResult(BaseModel):
    success: bool
    user_id: int | None = None
    telegram_id: int | None = None
    innohassle_id: int | None = None
    source: VerificationSource | None = None


class SucceedVerificationResult(VerificationResult):
    success: Literal[True] = True


class VerificationResultWithUserId(VerificationResult):
    success: Literal[True] = True
    user_id: int
