import logging

import httpx

from src.config import settings
from src.modules.act.schemas import (
    AvailabilityResponse,
    BookingResponse,
    MusicRoomSlot,
)

from src.api.logging_ import logger

class ActRepository:
    def __init__(self):

        self.base_url = settings.ml_service.api_music_url

    async def check_availability(
        self,
        slot: MusicRoomSlot,
        token: str,
    ) -> AvailabilityResponse:
        logger.info(f"[ActRepository] check_availability: slot={slot!r}, token={token[:8]}…")
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "date": slot.date.isoformat(),
            "start": slot.start.strftime("%H:%M"),
            "end": slot.end.strftime("%H:%M"),
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/availability",
                headers=headers,
                params=params,
            )
            logger.info(f"[ActRepository] GET /availability → {resp.status_code}")
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"[ActRepository] availability response: {data}")
            return AvailabilityResponse(**data)

    async def create_booking(
        self,
        slot: MusicRoomSlot,
        token: str,
    ) -> BookingResponse:
<<<<<<< HEAD:src/modules/act/repository.py
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json", "Content-Type": "application/json"}
=======
        logger.info(f"[ActRepository] create_booking: slot={slot!r}, token={token[:8]}…")
        headers = {"Authorization": f"Bearer {token}"}
>>>>>>> a9bca5a (fix: fix function calling):src/modules/act/music_room/repository.py
        payload = {
           "time_start": slot.time_start.isoformat(),
           "time_end": slot.time_end.isoformat(),
        }
        async with httpx.AsyncClient() as client:
<<<<<<< HEAD:src/modules/act/repository.py
            resp = await client.post(f"{self.base_url}/bookings/", json=payload, headers=headers)
            if resp.status_code == 400:
                logger.error(f"Failed to book slot: {resp.json()}")
            elif resp.status_code == 409:
                logger.error(f"Failed to book slot: {resp.json()}") # exist overlap
            resp.raise_for_status()
            return BookingResponse.model_validate(resp.json())
=======
            resp = await client.post(
                f"{self.base_url}/book",
                json=payload,
                headers=headers,
            )
            logger.info(f"[ActRepository] POST /book → {resp.status_code}")
            resp.raise_for_status()
            data = resp.json()
            logger.info(f"[ActRepository] booking response: {data}")
            return BookingResponse(**data)
>>>>>>> a9bca5a (fix: fix function calling):src/modules/act/music_room/repository.py

    async def handle_booking(
        self,
        slot: MusicRoomSlot,
        token: str,
    ) -> dict:
        logger.info(f"[ActRepository] handle_booking start for slot={slot!r}")
        avail = await self.check_availability(slot, token)
        if not avail.available:
            logger.warning(f"[ActRepository] slot occupied: message={avail.message}")
            return {"available": False, "message": avail.message or "Room is occupied"}

        booking = await self.create_booking(slot, token)
        result = {"available": True, **booking.dict()}
        logger.info(f"[ActRepository] handle_booking success: {result}")
        return result
