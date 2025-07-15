from datetime import date, time

from pydantic import HttpUrl

from src.config_schema import Accounts
from src.custom_pydantic import CustomModel


# Config-schemas
class BookingSettings(CustomModel):
    api_url: HttpUrl


class Settings(CustomModel):
    accounts: Accounts
    booking: BookingSettings


# HTTP-schemas
class MusicRoomSlot(CustomModel):
    date: date
    start: time
    end: time


class AvailabilityResponse(CustomModel):
    available: bool
    message: str | None = None


# class BookingRequest(MusicRoomSlot):
#    confirm: bool = Field(False, description="Confirm the booking.")


class BookingResponse(CustomModel):
    booking_id: str
    status: str
    date: date
    start: time
    end: time
