import datetime
from src.custom_pydantic import CustomModel

from pydantic import Field, HttpUrl

from src.config_schema import Accounts

class MusicRoomSlot(CustomModel):
    time_start: datetime.datetime
    time_end: datetime.datetime


class AvailabilityResponse(CustomModel):
    available: bool
    message: str = None


class BookingRequest(MusicRoomSlot):
    confirm: bool = Field(False, description="Confirm the booking.")


class BookingResponse(CustomModel):
    booking_id: int = Field(..., validation_alias="id")
    user_id: int
    user_alias: str
    time_start: datetime.datetime
    time_end: datetime.datetime
