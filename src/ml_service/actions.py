import datetime

import httpx
from pydantic import Field

from src.api.logging_ import logger
from src.config import settings
from src.custom_pydantic import CustomModel


class MusicRoomSlot(CustomModel):
    time_start: datetime.datetime
    time_end: datetime.datetime


class BookingResponse(CustomModel):
    booking_id: int = Field(..., validation_alias="id")
    user_id: int
    user_alias: str
    time_start: datetime.datetime
    time_end: datetime.datetime
    act_query_id: str | None = None


class MusicRoomActions:
    def __init__(self):
        self.base_url = settings.ml_service.api_music_url

    async def create_booking(
        self,
        slot: MusicRoomSlot,
        token: str,
    ) -> BookingResponse:
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json", "Content-Type": "application/json"}

        payload = {
            "time_start": slot.time_start.isoformat(),
            "time_end": slot.time_end.isoformat(),
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/bookings/", json=payload, headers=headers)
            if resp.status_code == 400:
                logger.error(f"Failed to book slot: {resp.json()}")
            elif resp.status_code == 409:
                logger.error(f"Failed to book slot: {resp.json()}")  # exist overlap
            resp.raise_for_status()
            return BookingResponse.model_validate(resp.json())

    async def list_my_bookings(self, token: str) -> list[dict]:
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json", "Content-Type": "application/json"}

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/bookings/my_bookings", headers=headers)
            if resp.status_code == 400:
                logger.error(f"Failed to get bookings: {resp.json()}")
            elif resp.status_code == 409:
                logger.error(f"Failed to get bookings: {resp.json()}")
            resp.raise_for_status()
            return resp.json()

    async def cancel_booking(self, booking_id: int, token: str) -> bool:
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json", "Content-Type": "application/json"}

        async with httpx.AsyncClient() as client:
            resp = await client.delete(f"{self.base_url}/bookings/{booking_id}", headers=headers)
            if resp.status_code == 400:
                logger.error(f"Failed to cancel booking: {resp.json()}")
            elif resp.status_code == 409:
                logger.error(f"Failed to cancel booking: {resp.json()}")
            resp.raise_for_status()
            return resp.status_code == 200


music_room_act: MusicRoomActions = MusicRoomActions()
