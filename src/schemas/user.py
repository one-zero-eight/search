from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class UserStatus(StrEnum):
    FREE = "free"
    MIDDLE = "middle"
    SENIOR = "senior"
    LORD = "lord"

    def max_hours_to_book_per_day(self) -> int | None:
        if self == UserStatus.FREE:
            return 2
        elif self == UserStatus.MIDDLE:
            return 3
        elif self == UserStatus.SENIOR:
            return 4
        elif self == UserStatus.LORD:
            return 15
        return None

    def max_hours_to_book_per_week(self) -> int | None:
        if self == UserStatus.FREE:
            return 4
        elif self == UserStatus.MIDDLE:
            return 8
        elif self == UserStatus.SENIOR:
            return 10
        elif self == UserStatus.LORD:
            return 150
        return None


class CreateUser(BaseModel):
    name: str | None = None
    alias: str | None = None
    email: str
    telegram_id: int
    status: UserStatus = UserStatus.FREE


class FillUserProfile(BaseModel):
    name: str
    alias: str


class ViewUser(BaseModel):
    id: int
    name: str | None = None
    alias: str | None = None
    email: str
    telegram_id: int
    status: UserStatus

    model_config = ConfigDict(from_attributes=True)
