import httpx

from src.config import settings
from src.modules.act.schemas import (
    AvailabilityResponse,
    BookingRequest,
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
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "date": slot.date.isoformat(),
            "start": slot.start.strftime("%H:%M"),
            "end": slot.end.strftime("%H:%M"),
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/availability", headers=headers, params=params)
            resp.raise_for_status()
            return AvailabilityResponse(**resp.json())

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
                logger.error(f"Failed to book slot: {resp.json()}") # exist overlap
            resp.raise_for_status()
            return BookingResponse.model_validate(resp.json())

    async def handle_booking(
        self,
        req: BookingRequest,
        token: str,
    ) -> dict:
        avail = await self.check_availability(req, token)
        if not avail.available:
            return {"available": False, "message": avail.message or "The room is occupied"}
        if req.confirm:
            booking = await self.create_booking(req, token)
            return {"available": True, "booked": True, **booking.dict()}
        return {"available": True, "booked": False, "message": avail.message}
